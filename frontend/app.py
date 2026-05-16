import json
import os
import re

import requests
import sseclient
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
MODE_LABELS = {
    "Direct Chat": "direct",
    "RAG Assistant": "rag",
    "Agent Workflow": "agent",
}

st.set_page_config(page_title="Enterprise GenAI Automation Assistant", page_icon="AI", layout="wide")
st.title("Enterprise GenAI Automation Assistant")
st.caption("Direct LLM · RAG Knowledge Assistant · Agent Workflow · Power Platform API Demo")


def _api_get(path: str, **kwargs):
    return requests.get(f"{BACKEND_URL}{path}", timeout=10, **kwargs)


def _api_post(path: str, **kwargs):
    return requests.post(f"{BACKEND_URL}{path}", timeout=120, **kwargs)


def _render_content(content: str):
    parts = re.split(r"(```tool\n.*?```)", content, flags=re.DOTALL)
    for part in parts:
        if part.startswith("```tool\n"):
            tool_line = part[8:-3].strip()
            with st.expander(tool_line[:80], expanded=False):
                st.code(tool_line)
        elif part.strip():
            st.markdown(part)


def _render_content_streaming(placeholder, content: str):
    placeholder.markdown(
        content.replace("```tool\n", "> `").replace("```\n", "`\n"),
        unsafe_allow_html=False,
    )


def _show_health():
    try:
        r = _api_get("/health")
        if r.ok:
            data = r.json()
            memory = data.get("memory", {})
            status = "online" if memory.get("ready") else "degraded"
            st.metric("Backend", data.get("status", "unknown"))
            st.metric("Knowledge DB", status)
            if memory.get("error"):
                st.warning(memory["error"])
        else:
            st.error(f"Backend health check failed: {r.status_code}")
    except Exception as exc:
        st.error(f"Backend unavailable: {exc}")


with st.sidebar:
    st.header("Demo Control")
    selected_mode = st.radio("AI pattern", list(MODE_LABELS), index=2)
    mode = MODE_LABELS[selected_mode]
    session_id = st.text_input("Session ID", value="default")

    if st.button("Clear Session"):
        requests.delete(f"{BACKEND_URL}/history/{session_id}", timeout=10)
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.header("System Status")
    _show_health()

    st.divider()
    st.header("Knowledge Base")
    with st.form("knowledge_form"):
        knowledge = st.text_area(
            "Add enterprise knowledge",
            placeholder="Example: Expense claims over EUR 1,000 require manager approval and finance review.",
            height=100,
        )
        tags = st.text_input("Tags", value="policy,faq")
        submitted = st.form_submit_button("Store Knowledge")
        if submitted and knowledge.strip():
            payload = {
                "content": knowledge.strip(),
                "tags": [tag.strip() for tag in tags.split(",") if tag.strip()],
                "metadata": {"source": "streamlit_demo"},
            }
            r = _api_post("/memory/", json=payload)
            st.success("Stored" if r.json().get("stored") else r.json().get("error", "Store failed"))

    memory_search = st.text_input("Search knowledge")
    if memory_search:
        r = _api_get("/memory/search", params={"q": memory_search})
        if r.ok:
            data = r.json()
            if data.get("error"):
                st.warning(data["error"])
            for result in data.get("results", []):
                st.info(result)


tab_chat, tab_automation = st.tabs(["AI Assistant", "Automation Demo"])

with tab_chat:
    st.subheader(selected_mode)
    if mode == "direct":
        st.caption("Simple GenAI response without tools or retrieval.")
    elif mode == "rag":
        st.caption("Grounded response from Qdrant knowledge snippets to reduce hallucination.")
    else:
        st.caption("ReAct workflow with tool calls for multi-step tasks.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            _render_content(msg["content"]) if msg["role"] == "assistant" else st.write(msg["content"])

    if prompt := st.chat_input("Ask an enterprise AI question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""

            try:
                with requests.post(
                    f"{BACKEND_URL}/chat/",
                    json={"message": prompt, "session_id": session_id, "mode": mode},
                    stream=True,
                    timeout=120,
                ) as r:
                    r.raise_for_status()
                    client = sseclient.SSEClient(r)
                    for event in client.events():
                        chunk = json.loads(event.data)
                        if chunk == "[DONE]":
                            break
                        full_response += chunk
                        _render_content_streaming(response_placeholder, full_response)
            except Exception as exc:
                full_response = f"Error: {exc}"
                response_placeholder.error(full_response)

            st.session_state.messages.append({"role": "assistant", "content": full_response})


with tab_automation:
    st.subheader("Power Platform Integration Contract")
    st.caption("This endpoint returns structured JSON that Power Automate or Power Apps can consume.")
    workflow_type = st.selectbox(
        "Workflow type",
        ["client_email", "invoice_exception", "it_request", "compliance_question"],
    )
    input_text = st.text_area(
        "Business input",
        value="Client asks whether their invoice can be expedited because payment is blocking project delivery.",
        height=140,
    )
    requester = st.text_input("Requester", value="demo-user")

    if st.button("Run Automation"):
        try:
            r = _api_post(
                "/automation/run",
                json={
                    "workflow_type": workflow_type,
                    "input_text": input_text,
                    "requester": requester,
                },
            )
            r.raise_for_status()
            st.json(r.json())
        except Exception as exc:
            st.error(f"Automation failed: {exc}")
