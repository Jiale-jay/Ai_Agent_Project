# AI Agent — ReAct Agent with Memory & Tools

A production-ready AI agent system built from scratch, featuring a custom ReAct loop, multi-tool execution, and a dual-layer memory system. Built to demonstrate end-to-end AI application engineering.

**[Live Demo](https://your-demo-url.railway.app)** · **[API Docs](https://your-demo-url.railway.app/docs)**

---

## What it does

Ask it anything. It reasons, picks the right tools, executes them, and synthesizes a final answer — all streamed in real time.

```
User:  What's the current Bitcoin price, and what's 37% of it?

Agent: 🔧 web_search({"query": "Bitcoin price USD 2025"})
       🔧 calculator({"expression": "43250 * 0.37"})

       Bitcoin is currently $43,250. 37% of that is $16,002.50.
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Streamlit Frontend :8501                  │
│         Chat UI  │  Tool Chain View  │  Memory Explorer     │
└──────────────────────────┬──────────────────────────────────┘
                           │  HTTP + SSE (streaming)
┌──────────────────────────▼──────────────────────────────────┐
│                   FastAPI Backend :8000                      │
│   POST /chat/    GET /history/{id}    GET /memory/search     │
└──────────────────────────┬──────────────────────────────────┘
                           │
         ┌─────────────────▼──────────────────────┐
         │              Agent Core                │
         │                                        │
         │   ┌─────────────────────────────────┐  │
         │   │         ReAct Loop              │  │
         │   │                                 │  │
         │   │  1. Call Claude with tools      │  │
         │   │  2. tool_use → execute tool     │  │
         │   │  3. Return result to Claude     │  │
         │   │  4. Repeat until end_turn       │  │
         │   └──────────────┬──────────────────┘  │
         │                  │                     │
         │   ┌──────────────┼──────────────────┐  │
         │   │  Tool Router │  Memory Manager  │  │
         │   └──────┬───────┘  └──────┬─────────┘  │
         └──────────┼─────────────────┼────────────┘
                    │                 │
          ┌─────────▼──────┐   ┌──────▼──────┐
          │     Tools      │   │   Qdrant    │
          │                │   │             │
          │ • web_search   │   │  Long-term  │
          │ • calculator   │   │  Memory     │
          │ • python_repl  │   │  (vectors)  │
          │ • web_fetch    │   │             │
          │ • memory_store │   └─────────────┘
          │ • memory_recall│
          └────────────────┘
```

### Memory Architecture

```
Short-term Memory (in-process)          Long-term Memory (Qdrant)
─────────────────────────────           ─────────────────────────
session_id → [messages]                 content → BGE embedding
                                        semantic search on recall
• Full conversation history             • Persists across sessions
• Auto-cleared on session end           • User-controlled via tools
```

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| LLM | Claude claude-sonnet-4-6 (Anthropic) | Native `tool_use` API, best reasoning |
| Backend | FastAPI + async/await | Async-native, ideal for SSE streaming |
| Vector DB | Qdrant | Fast cosine search, easy Docker deploy |
| Embeddings | BGE-small-en-v1.5 | Lightweight, runs CPU-only |
| Frontend | Streamlit | Fast to build, good for demos |
| Search | Tavily API | Purpose-built for LLM search pipelines |
| Deployment | Docker Compose + Railway | One-command local + public URL |

---

## Key Design Decisions

**1. Custom ReAct loop, not LangChain**

The agent loop in `agent/core.py` is ~60 lines of plain Python using the Anthropic SDK directly. This makes the reasoning trace fully transparent, avoids framework magic, and is easier to debug and extend.

**2. Claude's native `tool_use` API**

Rather than parsing `Thought: ... Action: ...` strings from raw LLM output, the agent uses Anthropic's structured `tool_use` content blocks. This is more reliable, handles edge cases automatically, and produces clean JSON inputs to every tool.

**3. Dual-layer memory**

Short-term memory (in-process dict) keeps the conversation fast and cheap. Long-term memory (Qdrant) persists facts across sessions via semantic search — the agent decides what to store using the `memory_store` tool.

**4. Sandboxed Python execution**

The `python_repl` tool blocks `os`, `subprocess`, `socket`, and other dangerous imports via AST inspection before execution. No Docker-in-Docker or subprocess isolation needed for a demo.

---

## Features

- **ReAct reasoning loop** — iterative Thought → Action → Observation cycles
- **6 built-in tools** — web search, calculator, Python REPL, web fetch, memory store/recall
- **Dual-layer memory** — short-term conversation + long-term semantic vector memory
- **Real-time streaming** — SSE-based token streaming from Claude to the UI
- **Tool chain visualization** — each tool call shown as an expandable block in the UI
- **Session management** — multiple independent sessions, history clear per session
- **REST API** — fully documented at `/docs`, ready for integration

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Anthropic API key ([get one](https://console.anthropic.com))
- Tavily API key (optional, [free tier](https://tavily.com))

### Run locally

```bash
git clone https://github.com/your-username/ai-agent.git
cd ai-agent

# 1. Configure
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 2. Start everything
docker compose up

# 3. Open
# Frontend:  http://localhost:8501
# API docs:  http://localhost:8000/docs
```

### Run backend only (for development)

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

---

## API Reference

### `POST /chat/`

Stream a response from the agent.

```bash
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Search for the latest AI news", "session_id": "demo"}' \
  --no-buffer
```

Response: SSE stream, each event is a text chunk. Final event is `data: [DONE]`.

### `GET /history/{session_id}`

Retrieve conversation history for a session.

### `DELETE /history/{session_id}`

Clear conversation history.

### `GET /memory/search?q={query}`

Semantic search over long-term memory.

### `POST /memory/`

Manually store a memory entry.

```json
{ "content": "User prefers concise answers", "tags": ["preference"] }
```

---

## Project Structure

```
ai-agent/
├── backend/
│   ├── agent/
│   │   ├── core.py          # ReAct loop (the heart of the system)
│   │   ├── memory.py        # Short-term + long-term memory manager
│   │   └── tools/
│   │       ├── base.py      # Abstract BaseTool + ToolResult
│   │       ├── search.py    # Tavily web search
│   │       ├── calculator.py # AST-based safe math evaluator
│   │       ├── python_repl.py # Sandboxed Python executor
│   │       ├── web_fetch.py  # Async HTML → text extractor
│   │       └── memory_tool.py # memory_store + memory_recall
│   ├── api/routes/
│   │   ├── chat.py          # SSE streaming endpoint
│   │   ├── history.py       # Conversation history CRUD
│   │   └── memory.py        # Long-term memory endpoints
│   ├── config.py            # Pydantic settings from .env
│   └── main.py              # FastAPI app + CORS
├── frontend/
│   └── app.py               # Streamlit UI
├── scripts/
│   └── init_qdrant.py       # One-time collection setup
└── docker-compose.yml
```

---

## Extending the Agent

Adding a new tool takes ~20 lines:

```python
# backend/agent/tools/my_tool.py
from .base import BaseTool, ToolResult

class MyTool(BaseTool):
    name = "my_tool"
    description = "Does something useful."

    async def run(self, input: str) -> ToolResult:
        result = do_something(input)
        return ToolResult(success=True, output=result)

    def to_claude_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {"input": {"type": "string"}},
                "required": ["input"],
            },
        }
```

Then register it in `agent/core.py`:

```python
from agent.tools.my_tool import MyTool
# Add MyTool() to the list in _register_default_tools()
```

---

## Roadmap

- [ ] Token-level streaming (currently chunk-level)
- [ ] Conversation summarization when history exceeds token limit
- [ ] Tool execution timeout & retry
- [ ] Authentication (API key per user)
- [ ] Evaluation harness (correctness + tool selection accuracy)

---

## License

MIT
