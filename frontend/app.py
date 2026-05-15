import os
import re

import requests
import sseclient
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="AI Agent", page_icon="🤖", layout="wide")
st.title("🤖 AI Agent")
st.caption("ReAct Agent · Web Search · Python REPL · Long-term Memory")

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Session")
    session_id = st.text_input("Session ID", value="default")

    if st.button("Clear History"):
        requests.delete(f"{BACKEND_URL}/history/{session_id}")
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.header("Long-term Memory")
    if st.button("View Memories"):
        r = requests.get(f"{BACKEND_URL}/memory/")
        if r.ok:
            data = r.json()
            st.write(f"**{data['count']} memories stored**")
            for item in data["items"]:
                st.text(item.get("content", "")[:100])

    memory_search = st.text_input("Search memory")
    if memory_search:
        r = requests.get(f"{BACKEND_URL}/memory/search", params={"q": memory_search})
        if r.ok:
            for result in r.json().get("results", []):
                st.info(result)

# ── Chat history ───────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        _render_content(msg["content"]) if msg["role"] == "assistant" else st.write(msg["content"])


def _render_content(content: str):
    """Render tool calls in expanders and plain text normally."""
    parts = re.split(r"(```tool\n.*?```)", content, flags=re.DOTALL)
    for part in parts:
        if part.startswith("```tool\n"):
            tool_line = part[8:-3].strip()
            with st.expander(f"🔧 {tool_line[:60]}", expanded=False):
                st.code(tool_line)
        elif part.strip():
            st.markdown(part)


# ── Input ──────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask me anything…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""

        try:
            with requests.post(
                f"{BACKEND_URL}/chat/",
                json={"message": prompt, "session_id": session_id},
                stream=True,
                timeout=120,
            ) as r:
                client = sseclient.SSEClient(r)
                for event in client.events():
                    if event.data == "[DONE]":
                        break
                    full_response += event.data
                    _render_content_streaming(response_placeholder, full_response)
        except Exception as e:
            full_response = f"❌ Error: {e}"
            response_placeholder.error(full_response)

        st.session_state.messages.append({"role": "assistant", "content": full_response})


def _render_content_streaming(placeholder, content: str):
    """Simplified streaming render — tool blocks shown inline."""
    placeholder.markdown(
        content.replace("```tool\n", "> 🔧 `").replace("```\n", "`\n"),
        unsafe_allow_html=False,
    )
