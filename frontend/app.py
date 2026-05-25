import json
import os
import re

import requests
import sseclient
import streamlit as st
import streamlit.components.v1 as components

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
MODE_LABELS = {
    "Direct Chat": "direct",
    "RAG Assistant": "rag",
    "Agent Workflow": "agent",
}

st.set_page_config(page_title="Enterprise GenAI Automation Assistant", page_icon="AI", layout="wide")
components.html(
    """
    <script>
    const css = `
    <style>
    :root {
        --ai-cursor: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='28' height='28' viewBox='0 0 28 28'%3E%3Cpath d='M6 4 L21 14 L14 16 L11 23 L6 4 Z' fill='%2338bdf8' stroke='%230f172a' stroke-width='1.5' stroke-linejoin='round'/%3E%3Ccircle cx='18.5' cy='8.5' r='3.5' fill='%23f97316' stroke='%230f172a' stroke-width='1.2'/%3E%3C/svg%3E") 6 4, auto;
    }

    html,
    body,
    [data-testid="stAppViewContainer"] {
        cursor: var(--ai-cursor);
    }

    button,
    [role="button"],
    [role="tab"],
    label,
    a,
    summary {
        cursor: pointer;
    }

    textarea,
    input {
        cursor: text;
    }

    [data-testid="stAppViewContainer"] .main .block-container {
        padding-bottom: 7rem;
    }

    [data-testid="stChatInput"] {
        position: fixed;
        left: calc(21rem + 1rem);
        right: 1rem;
        bottom: 0.75rem;
        z-index: 1000;
    }

    @media (max-width: 800px) {
        [data-testid="stChatInput"] {
            left: 1rem;
        }
    }
    </style>
    `;
    const styleId = "enterprise-ai-cursor-style";
    const existing = window.parent.document.getElementById(styleId);
    if (existing) {
        existing.remove();
    }
    const style = window.parent.document.createElement("style");
    style.id = styleId;
    style.textContent = css.replace(/<\/?style>/g, "");
    window.parent.document.head.appendChild(style);
    </script>
    """,
    height=0,
)
st.title("Enterprise GenAI Automation Assistant")
st.caption("Direct LLM · RAG Knowledge Assistant · Agent Workflow · Power Platform API Demo")


def _api_get(path: str, **kwargs):
    return requests.get(f"{BACKEND_URL}{path}", timeout=10, **kwargs)


def _api_post(path: str, **kwargs):
    return requests.post(f"{BACKEND_URL}{path}", timeout=120, **kwargs)


def _api_delete(path: str, **kwargs):
    return requests.delete(f"{BACKEND_URL}{path}", timeout=30, **kwargs)


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
    uploaded_doc = st.file_uploader("Upload enterprise document", type=["txt", "md", "pdf"])
    upload_tags = st.text_input("Upload tags", value="policy,enterprise")
    if uploaded_doc and st.button("Upload Document"):
        try:
            files = {
                "file": (
                    uploaded_doc.name,
                    uploaded_doc.getvalue(),
                    uploaded_doc.type or "text/plain",
                )
            }
            r = _api_post(
                "/memory/upload",
                files=files,
                data={"tags": upload_tags, "session_id": session_id},
            )
            if r.ok:
                result = r.json()
                if result.get("stored"):
                    st.success(
                        f"Stored {result['chunks']} chunks from {result['filename']} "
                        f"({result.get('document_id', 'document')})"
                    )
                else:
                    st.error(result.get("error", "Upload failed"))
            else:
                st.error(r.json().get("detail", f"Upload failed: {r.status_code}"))
        except Exception as exc:
            st.error(f"Upload failed: {exc}")

    st.subheader("Documents")
    document_filter = st.text_input("Filter documents", value="")
    try:
        r = _api_get("/memory/documents", params={"session_id": session_id})
        if r.ok:
            data = r.json()
            if data.get("error"):
                st.warning(data["error"])
            documents = data.get("documents", [])
            if document_filter:
                needle = document_filter.lower()
                documents = [
                    doc for doc in documents
                    if needle in doc.get("filename", "").lower()
                    or any(needle in tag.lower() for tag in doc.get("tags", []))
                ]

            if not documents:
                st.caption("No uploaded documents yet.")

            for doc in documents:
                label = f"{doc.get('filename', 'document')} · {doc.get('chunk_count', 0)} chunks"
                with st.expander(label, expanded=False):
                    st.caption(doc.get("document_id", ""))
                    if doc.get("tags"):
                        st.write(", ".join(doc["tags"]))
                    if doc.get("uploaded_at"):
                        st.write(f"Uploaded: {doc['uploaded_at']}")

                    detail = _api_get(
                        f"/memory/documents/{doc['document_id']}",
                        params={"session_id": session_id},
                    )
                    if detail.ok:
                        chunks = detail.json().get("document", {}).get("chunks", [])
                        for chunk in chunks[:3]:
                            metadata = chunk.get("metadata", {})
                            source = f"chunk {metadata.get('chunk_index')}"
                            if metadata.get("page"):
                                source = f"p.{metadata['page']} · {source}"
                            st.caption(source)
                            st.write(chunk.get("content", "")[:500])
                    if st.button("Delete document", key=f"delete-doc-{doc['document_id']}"):
                        deleted = _api_delete(
                            f"/memory/documents/{doc['document_id']}",
                            params={"session_id": session_id},
                        )
                        if deleted.ok and deleted.json().get("deleted"):
                            st.success("Document deleted")
                            st.rerun()
                        else:
                            st.error("Delete failed")
        else:
            st.warning(f"Could not load documents: {r.status_code}")
    except Exception as exc:
        st.warning(f"Could not load documents: {exc}")

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
            for result in data.get("items", []):
                metadata = result.get("metadata", {})
                filename = metadata.get("filename") or metadata.get("source", "manual")
                chunk_index = metadata.get("chunk_index")
                page = metadata.get("page")
                score = result.get("score")
                label = filename
                if page:
                    label += f" · p.{page}"
                if chunk_index:
                    label += f" · chunk {chunk_index}"
                if score is not None:
                    label += f" · score {score:.2f}"
                with st.expander(label, expanded=False):
                    st.write(result.get("content", ""))


if "messages" not in st.session_state:
    st.session_state.messages = []

tab_chat, tab_automation = st.tabs(["AI Assistant", "Automation Demo"])

with tab_chat:
    st.subheader(selected_mode)
    if mode == "direct":
        st.caption("Simple GenAI response without tools or retrieval.")
    elif mode == "rag":
        st.caption("Grounded response from Qdrant knowledge snippets to reduce hallucination.")
    else:
        st.caption("ReAct workflow with tool calls for multi-step tasks.")

    chat_history = st.container()
    with chat_history:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                _render_content(msg["content"]) if msg["role"] == "assistant" else st.write(msg["content"])


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


if prompt := st.chat_input("Ask an enterprise AI question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with chat_history:
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
