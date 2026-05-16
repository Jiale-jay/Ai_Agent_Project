# Enterprise GenAI Automation Assistant

A portfolio-grade enterprise GenAI system built to match a **GenAI & Automation Developer** role: direct LLM chat, RAG over enterprise knowledge, ReAct-style agent workflows, and Power Platform-friendly automation APIs.

The local demo uses FastAPI, Streamlit, Anthropic, and Qdrant. The architecture is intentionally mapped to Azure AI Foundry, Azure OpenAI, Copilot Studio, and Power Automate for enterprise deployment discussions.

**[Live Demo](https://your-demo-url.railway.app)** · **[API Docs](https://your-demo-url.railway.app/docs)**

---

## JD Capability Mapping

| JD requirement | Project capability |
|---|---|
| GenAI application design | Three modes: Direct Chat, RAG Assistant, Agent Workflow |
| Azure + Foundry | Local services map cleanly to Azure App Service, Azure OpenAI, Azure AI Search / vector DB, and Foundry evaluation |
| RAG | Qdrant-backed enterprise knowledge base with grounded answers |
| Agent systems | Custom ReAct loop using Anthropic `tool_use` and pluggable tools |
| Power Automate / Power Apps | `/automation/run` returns low-code friendly structured JSON |
| REST API integration | FastAPI endpoints for chat, memory, history, health, and automation |
| Responsible AI | Human-review flags, demo sandbox limits, privacy notes, and grounding behavior |
| MLOps / evaluation | Pytest suite plus `evals/jd_demo_cases.jsonl` for demo acceptance scenarios |

---

## What it does

The assistant supports three enterprise AI patterns:

1. **Direct Chat** — simple LLM responses for low-risk questions.
2. **RAG Assistant** — retrieves enterprise policy / FAQ snippets from Qdrant before answering.
3. **Agent Workflow** — reasons through multi-step tasks and calls tools such as search, calculator, web fetch, Python demo REPL, and memory.

```
User:  What's the current Bitcoin price, and what's 37% of it?

Agent: 🔧 web_search({"query": "Bitcoin price USD 2025"})
       🔧 calculator({"expression": "43250 * 0.37"})

Agent: Uses web_search + calculator, then synthesizes the answer.
```

Automation example:

```bash
curl -X POST http://localhost:8000/automation/run \
  -H "Content-Type: application/json" \
  -d '{"workflow_type":"invoice_exception","input_text":"Invoice has a bank detail mismatch","requester":"finance-demo"}'
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Streamlit Frontend :8501                  │
│ Direct/RAG/Agent │ Automation Demo │ Knowledge Explorer    │
└──────────────────────────┬──────────────────────────────────┘
                           │  HTTP + SSE (streaming)
┌──────────────────────────▼──────────────────────────────────┐
│                   FastAPI Backend :8000                      │
│ POST /chat/ GET /memory/search POST /automation/run /health  │
└──────────────────────────┬──────────────────────────────────┘
                           │
         ┌─────────────────▼──────────────────────┐
         │              Agent Core                │
         │                                        │
         │   ┌─────────────────────────────────┐  │
         │   │         ReAct Loop              │  │
         │   │                                 │  │
│   │  Direct: LLM response           │  │
│   │  RAG: retrieve → grounded answer│  │
│   │  Agent: tool_use loop           │  │
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
| Automation | FastAPI JSON endpoint | Easy for Power Automate / Power Apps to consume |
| Deployment | Docker Compose + Railway/Azure path | One-command local + cloud migration story |

---

## Key Design Decisions

**1. Custom ReAct loop, not LangChain**

The agent loop in `agent/core.py` is ~60 lines of plain Python using the Anthropic SDK directly. This makes the reasoning trace fully transparent, avoids framework magic, and is easier to debug and extend.

**2. Claude's native `tool_use` API**

Rather than parsing `Thought: ... Action: ...` strings from raw LLM output, the agent uses Anthropic's structured `tool_use` content blocks. This is more reliable, handles edge cases automatically, and produces clean JSON inputs to every tool.

**3. Dual-layer memory**

Short-term memory (in-process dict) keeps the conversation fast and cheap. Long-term memory (Qdrant) persists facts across sessions via semantic search — the agent decides what to store using the `memory_store` tool.

**4. Demo-guarded Python execution**

The `python_repl` tool uses AST checks and restricted builtins for demo data processing. It is deliberately documented as a **demo guard**, not a production sandbox. A production enterprise deployment should isolate code execution in a container, disable it, or replace it with approved deterministic tools.

**5. Power Platform integration contract**

`POST /automation/run` returns `summary`, `recommended_action`, `confidence`, `requires_human_review`, and `audit_notes`, which are intentionally easy for Power Automate or Power Apps to parse.

---

## Features

- **ReAct reasoning loop** — iterative Thought → Action → Observation cycles
- **6 built-in tools** — web search, calculator, Python REPL, web fetch, memory store/recall
- **Dual-layer memory** — short-term conversation + long-term semantic vector memory
- **Real-time streaming** — SSE-based token streaming from Claude to the UI
- **Tool chain visualization** — each tool call shown as an expandable block in the UI
- **Session management** — multiple independent sessions, history clear per session
- **REST API** — fully documented at `/docs`, ready for integration
- **Power Platform-style automation endpoint** — structured JSON for workflow orchestration
- **JD-focused evaluation cases** — small eval set for RAG, agent, and automation scenarios

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

Stream a response from the assistant.

```bash
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Search for the latest AI news", "session_id": "demo", "mode": "agent"}' \
  --no-buffer
```

`mode` can be `direct`, `rag`, or `agent`. Response is an SSE stream; each event is a JSON-encoded text chunk. Final event is `data: "[DONE]"`.

### `POST /automation/run`

Power Automate / Power Apps friendly workflow endpoint.

```json
{
  "workflow_type": "invoice_exception",
  "input_text": "Invoice has a bank detail mismatch and may contain personal data.",
  "requester": "finance-demo"
}
```

Response:

```json
{
  "summary": "Invoice has a bank detail mismatch...",
  "recommended_action": "Summarize the exception, check likely causes, and route to finance operations.",
  "confidence": 0.72,
  "requires_human_review": true,
  "audit_notes": ["workflow_type=invoice_exception", "requester=finance-demo"]
}
```

### `GET /history/{session_id}`

Retrieve conversation history for a session.

### `DELETE /history/{session_id}`

Clear conversation history.

### `GET /memory/search?q={query}`

Semantic search over long-term memory.

### `POST /memory/`

Manually store a memory entry.

```json
{
  "content": "Expense claims over EUR 1,000 require manager approval and finance review.",
  "tags": ["policy", "finance"],
  "metadata": {"source": "demo_policy"}
}
```

### `GET /health`

Returns backend status and Qdrant readiness so the UI or an automation flow can detect degraded knowledge-base behavior.

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
│   │       ├── python_repl.py # Demo-guarded Python executor
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

## Responsible AI & Privacy Notes

- Do not store real client confidential data in the demo Qdrant collection.
- API keys are read from `.env`; never commit real keys.
- RAG mode should say when internal knowledge is missing instead of inventing a policy answer.
- Automation responses include `requires_human_review` for sensitive terms such as GDPR, bank details, legal, tax, or complaints.
- The Python REPL is for portfolio demonstration only and should be disabled or container-isolated in production.

---

## Evaluation

Run tests:

```bash
pytest
```

Demo acceptance cases live in `evals/jd_demo_cases.jsonl` and cover:

- Direct LLM answer behavior
- RAG grounding against enterprise knowledge
- Agent tool-selection behavior
- Power Platform automation response shape

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

- [x] Token-level streaming
- [x] Conversation summarization when history exceeds token limit
- [x] Direct / RAG / Agent modes
- [x] Power Platform-style automation endpoint
- [ ] Azure AI Foundry deployment guide
- [ ] Authentication and per-user audit logs
- [ ] Expanded evaluation harness for RAG faithfulness and tool selection accuracy

---

## License

MIT
