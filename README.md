# Enterprise GenAI Automation Assistant

A portfolio-grade enterprise GenAI system built to match a **GenAI & Automation Developer** role: direct LLM chat, RAG over enterprise knowledge, ReAct-style agent workflows, and Power Platform-friendly automation APIs.

The local demo uses FastAPI, Streamlit, Anthropic, and Qdrant. The architecture is intentionally mapped to Azure AI Foundry, Azure OpenAI, Copilot Studio, and Power Automate for enterprise deployment discussions.

**[GitHub](https://github.com/Jiale-jay/Ai_Agent_Project)** · **[API Docs](http://localhost:8000/docs)** *(Live Demo URL added after deployment)*

---

## Demo Preview

The README is prepared for interview demo evidence. Screenshots are intentionally tracked as local repo assets once recorded, rather than linking to temporary external files.

| Demo evidence | Planned asset | What it proves in an interview |
|---|---|---|
| RAG grounded answer | `docs/assets/demo-chat-rag.png` | The assistant retrieves uploaded enterprise knowledge and answers with citations instead of guessing |
| Agent tool trace | `docs/assets/demo-agent-tools.png` | The ReAct loop selects tools, shows traceable actions, and synthesizes the final answer |
| Power Platform JSON | `docs/assets/demo-automation.png` | `/automation/run` returns low-code friendly JSON with confidence, audit notes, and human-review flags |
| 30-second walkthrough | `docs/assets/demo-flow.gif` | End-to-end flow across Direct, RAG, Agent, and Automation modes |

> TODO before publishing: capture these assets from the local Streamlit demo and replace this note with inline images.

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

## Azure AI Foundry Mapping

This project runs locally with open-source components. Every layer maps 1-to-1 to Microsoft Azure for enterprise deployment:

| Local component | Azure equivalent | Notes |
|---|---|---|
| Anthropic Claude claude-sonnet-4-6 | Azure OpenAI GPT-4o | Swap 5 lines in `agent/core.py` — same `tool_use` pattern |
| Qdrant vector DB | Azure AI Search | Replace `AsyncQdrantClient` with `SearchClient`; same embedding interface |
| BGE-small embedding | Azure OpenAI `text-embedding-3-small` | Drop-in replacement |
| FastAPI on Docker | Azure Container Apps | Add `azd up` deployment config |
| `.env` API keys | Azure Key Vault + Managed Identity | No code change; read secrets from environment |
| `/automation/run` | Azure Logic Apps / Power Automate HTTP connector | API contract is already Power Automate-compatible |
| Streamlit frontend | Power Apps custom page or Copilot Studio topic | The REST API is the integration surface |
| Docker Compose | Azure AI Foundry project + deployments | Foundry wraps models, search, and evaluation in one workspace |

---

## How I Would Deploy This on Azure AI Foundry

This repo is a local demo, not a claimed production Azure deployment. The production path would keep the same API contracts while replacing local services with managed Azure components.

1. **Provision the Azure workspace**
   - Create an Azure AI Foundry project with Azure OpenAI model deployments for chat and embeddings.
   - Deploy the FastAPI backend to Azure Container Apps or App Service.
   - Create Azure AI Search for vector retrieval and Application Insights for traces, latency, and failures.

2. **Swap model, embedding, and search clients**
   - Replace Anthropic chat calls with Azure OpenAI chat completions or responses API calls using the same structured tool schema.
   - Replace BGE embeddings with Azure OpenAI `text-embedding-3-small`.
   - Replace Qdrant calls in `MemoryManager` with Azure AI Search vector indexing and metadata filters.

3. **Secure the enterprise integration surface**
   - Move secrets from `.env` to Azure Key Vault and use Managed Identity where possible.
   - Put authentication in front of the FastAPI routes and isolate memory by user or tenant.
   - Connect Power Automate through the existing `/automation/run` HTTP contract.

4. **Add production monitoring and evaluation**
   - Track retrieval hit rate, answer latency, tool failures, human-review volume, and cost per workflow.
   - Run the RAG and automation acceptance set in CI before deployment.
   - Use Foundry evaluation for faithfulness, groundedness, and safety regression checks.

---

## What it does

The assistant supports three enterprise AI patterns:

1. **Direct Chat** — simple LLM responses for low-risk questions.
2. **RAG Assistant** — retrieves uploaded enterprise document chunks from Qdrant before answering with citations.
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
                                        • Stores filename, chunk, tags, source
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

## Architecture Trade-offs

| Choice | Trade-off |
|---|---|
| Custom ReAct loop instead of LangChain | More explainable and interview-friendly, but fewer framework integrations out of the box |
| Streamlit instead of React or Power Apps | Faster portfolio demo delivery, but less control over enterprise-grade UI polish and state management |
| Qdrant + BGE locally instead of Azure AI Search + Azure OpenAI embeddings | Cheap and portable for local development, but production should use managed search, identity, and governance |
| In-process short-term memory instead of Redis or a database | Simple to inspect during the demo, but not horizontally scalable or durable across restarts |
| Claude native `tool_use` now, Azure OpenAI target architecture later | Strong structured tool calling for the local build, with a clear migration path for Azure-native deployment |

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
- **Enterprise document RAG upload** — `.txt` / `.md` document ingestion with chunk-level source metadata
- **JD-focused evaluation cases** — small eval set for RAG, agent, and automation scenarios

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Anthropic API key ([get one](https://console.anthropic.com))
- Tavily API key (optional, [free tier](https://tavily.com))

### Run locally

```bash
git clone https://github.com/Jiale-jay/Ai_Agent_Project.git
cd Ai_Agent_Project

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

### `GET /memory/`

List long-term memory entries. Supports optional filters: `user_id`, `session_id`, `tag`, `metadata_key`, `metadata_value`, and `limit`.

### `GET /memory/search?q={query}`

Semantic search over long-term memory. Returns both `results` for backwards-compatible text snippets and `items` with ids, tags, metadata, scope, timestamps, scores, and PII redaction status.

### `POST /memory/`

Manually store a memory entry. Content is lightly redacted for common PII before storage.

```json
{
  "content": "Expense claims over EUR 1,000 require manager approval and finance review.",
  "tags": ["policy", "finance"],
  "metadata": {"source": "demo_policy"},
  "user_id": "demo-user",
  "session_id": "default"
}
```

### `GET /memory/{memory_id}`

Retrieve one memory entry scoped by optional `user_id` and `session_id`.

### `PATCH /memory/{memory_id}`

Update `content`, `tags`, or `metadata`. Updating content regenerates the embedding and refreshes `updated_at`.

### `DELETE /memory/{memory_id}`

Delete one memory entry after validating the same optional `user_id` and `session_id` scope.

### `POST /memory/upload`

Upload a UTF-8 `.txt` or `.md` enterprise document. The backend chunks it, stores each chunk in Qdrant, and keeps source metadata for citations.

```bash
curl -X POST http://localhost:8000/memory/upload \
  -F "file=@expense-policy.md" \
  -F "tags=policy,finance"
```

Response:

```json
{
  "stored": true,
  "filename": "expense-policy.md",
  "chunks": 3,
  "tags": ["policy", "finance"]
}
```

Search results now include chunk-level source metadata:

```json
{
  "query": "approval for expenses over EUR 1,000",
  "results": [
    "Expense claims over EUR 1,000 require manager approval and finance review."
  ],
  "items": [
    {
      "id": "8fb6f2a4-2b6d-4d0c-9a0b-5b3af2d66f12",
      "content": "Expense claims over EUR 1,000 require manager approval and finance review.",
      "tags": ["policy", "finance"],
      "metadata": {
        "source": "document_upload",
        "filename": "expense-policy.md",
        "chunk_index": 1,
        "page": null
      },
      "user_id": "demo-user",
      "session_id": "default",
      "pii_redacted": false,
      "score": 0.82
    }
  ]
}
```

### `GET /health`

Returns backend status and Qdrant readiness so the UI or an automation flow can detect degraded knowledge-base behavior.

---

## Project Structure

```
Ai_Agent_Project/
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

## Responsible AI Design Choices

| Design choice | Current implementation | Production direction |
|---|---|---|
| Grounding-first RAG | RAG mode retrieves Qdrant snippets and should say when knowledge is missing instead of inventing a policy answer | Add stricter citation validation, retrieval confidence thresholds, and refusal tests |
| Traceable sources | Uploaded demo documents are split into chunks with filename, chunk index, tags, and source metadata | Add document IDs, owners, version history, retention policy, and access-aware retrieval |
| Human-in-the-loop | Automation responses include `requires_human_review` for sensitive topics such as GDPR, bank details, legal, tax, or complaints | Route flagged workflows to Power Automate approval steps with audit trails |
| Tool safety | `python_repl` uses AST checks and restricted builtins as a demo guard | Disable arbitrary code execution or isolate it in locked-down ephemeral containers |
| Privacy | Demo guidance says not to store real client confidential data in Qdrant and never commit `.env` keys | Add authentication, RBAC, PII redaction, Key Vault, and per-user memory isolation |
| Operational fallback | `/automation/run` returns a deterministic fallback if the LLM call fails | Monitor fallback rate and alert when model, search, or tool dependencies degrade |

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

### RAG Evaluation Approach

The current evaluation set is a lightweight acceptance suite for demo readiness. In production, I would expand it into a regression gate with:

- **Retrieval recall** — the expected document chunk appears in the top-k results.
- **Answer faithfulness** — the response only uses retrieved context for policy claims.
- **Citation correctness** — citations point to chunks that actually support the answer.
- **Refusal correctness** — the assistant says what is missing when the knowledge base lacks an answer.
- **Workflow reliability** — automation outputs preserve the JSON contract and set `requires_human_review` correctly.
- **Operational metrics** — latency, token cost, retrieval hit rate, and fallback rate are tracked per release.

Minimum CI flow:

```text
seed demo knowledge -> run fixed queries -> assert citations / grounding / review flags -> record regression results
```

---

## What I Would Improve in Production

- Add authentication, RBAC, tenant-aware sessions, per-user memory isolation, and audit logs.
- Move retrieval to Azure AI Search with metadata filters, document ACLs, richer chunking, and ingestion jobs for PDF / Office documents.
- Replace or isolate the demo Python REPL with approved deterministic tools or ephemeral sandbox containers.
- Add prompt/version tracking, rate limits, cost controls, structured traces, and Application Insights dashboards.
- Add CI evaluation gates for RAG faithfulness, tool-selection accuracy, automation JSON validity, and safety refusals.
- Add infrastructure-as-code with `azd` or Terraform so Azure Foundry resources can be recreated consistently.

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
- [x] Enterprise document RAG upload with chunk-level source metadata
- [x] Power Platform-style automation endpoint
- [ ] PDF ingestion for document RAG
- [ ] Azure AI Foundry deployment guide
- [ ] Authentication and per-user audit logs
- [ ] Expanded evaluation harness for RAG faithfulness and tool selection accuracy

---

## Interview Demo Guide

**One-sentence pitch:**
> "This is an end-to-end enterprise GenAI assistant I built from scratch — it supports direct LLM chat, RAG over company knowledge, a ReAct agent with six tools, and a Power Automate-compatible automation endpoint. The architecture maps directly to Azure AI Foundry, Azure OpenAI, and Azure AI Search."

**Recommended demo flow (5 minutes):**

1. **Direct mode** — ask a general question, show clean LLM response, no retrieval
2. **Enterprise Document RAG** — upload `expense-policy.md`, switch to RAG mode, ask "What approval is needed for expenses over EUR 1,000?", then show the answer cites `[1]` and the Knowledge Base search displays `expense-policy.md · chunk 1`
3. **Agent mode** — ask "What is 37% of the current Bitcoin price?" — show tool trace: `web_search` → `calculator` → synthesised answer
4. **Automation tab** — submit an invoice exception, show structured JSON with `requires_human_review: true` and `audit_notes`

**Common interview questions and answers:**

| Question | Answer pointer |
|---|---|
| Why not LangChain? | Self-implemented 60-line ReAct loop in `agent/core.py` — every line is explainable |
| How do you reduce hallucination? | RAG mode cites sources and explicitly states what knowledge is missing |
| How would you deploy to Azure? | See Azure AI Foundry Mapping table above — 5-line LLM swap, same API contract |
| How does Power Automate connect? | `POST /automation/run` returns deterministic JSON; HTTP connector needs no code |
| How do you handle sensitive data? | `requires_human_review` flag, GDPR policy in knowledge base, no real data in demo |
| How would you evaluate this in production? | `evals/jd_demo_cases.jsonl` shows the pattern; extend with RAG faithfulness scoring |

---

## License

MIT
