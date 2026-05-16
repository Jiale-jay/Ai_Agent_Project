# 项目进度记录

> 最后更新：2026-05-15（本地跑通 ✅）
> 目标：AI 应用工程师求职作品集项目

---

## 项目概况

**项目名称：** AI Agent — ReAct Agent with Memory & Tools
**GitHub：** https://github.com/Jiale-jay/Ai_Agent_Project
**核心目标：** 展示端到端 AI 应用工程能力，包括自实现 ReAct 循环、多工具集成、双层记忆系统

---

## 当前状态：本地完整跑通 ✅

### 已完成

| 模块 | 文件 | 状态 |
|------|------|------|
| 项目结构 | 全部目录和文件 | ✅ 完成 |
| 配置管理 | `backend/config.py` | ✅ 完成 |
| FastAPI 入口 | `backend/main.py` | ✅ 完成 |
| **ReAct 循环** | `backend/agent/core.py` | ✅ 骨架完成，待测试 |
| **记忆管理** | `backend/agent/memory.py` | ✅ 骨架完成，待测试 |
| 工具基类 | `backend/agent/tools/base.py` | ✅ 完成 |
| 工具：搜索 | `backend/agent/tools/search.py` | ✅ 完成（需 Tavily key）|
| 工具：计算器 | `backend/agent/tools/calculator.py` | ✅ 完成（AST 安全实现）|
| 工具：Python | `backend/agent/tools/python_repl.py` | ✅ 完成（沙盒实现）|
| 工具：网页抓取 | `backend/agent/tools/web_fetch.py` | ✅ 完成 |
| 工具：记忆存取 | `backend/agent/tools/memory_tool.py` | ✅ 完成 |
| API 路由 | `backend/api/routes/` | ✅ 骨架完成，待测试 |
| Streamlit 前端 | `frontend/app.py` | ✅ 骨架完成，待测试 |
| Docker Compose | `docker-compose.yml` | ✅ 完成 |
| README + 架构图 | `README.md` | ✅ 完成 |

### 尚未完成（优先级排序）

- [x] **P0 — 本地跑通**：2026-05-15 验证通过，计算器工具返回正确结果
- [x] **P0 — Bug 修复**：共修复 7 个 Bug（见下方已修复问题）
- [x] **P1 — 流式输出**：改用 `messages.stream()`，真正 token 级别 SSE
- [x] **P1 — 对话摘要压缩**：超过 `MAX_HISTORY_TOKENS` 时用 claude-haiku 自动摘要
- [ ] **P2 — Demo GIF**：录制 30 秒演示，放到 README 顶部
- [ ] **P2 — Railway 部署**：部署到公网，把 Live Demo URL 更新到 README
- [ ] **P3 — 评估体系**：对 tool 选择准确率、回答质量做基础评测

---

## 已知问题 / 需要注意的地方

### 1. `frontend/app.py` 函数定义顺序问题
`_render_content` 和 `_render_content_streaming` 在被调用后才定义，Python 会报 `NameError`。
**修复方法**：把这两个函数移到文件顶部（`st.set_page_config` 之后）。

### 2. `api/routes/chat.py` startup 事件写法过时
FastAPI 新版本（0.93+）推荐用 `lifespan` 替代 `@app.on_event("startup")`。
**修复方法**：改用 lifespan context manager，或暂时忽略 deprecation warning。

### 3. `agent/core.py` 流式输出不完整
`run()` 方法是 `AsyncGenerator`，但实际上对 Claude 的调用是等待完整响应再 yield，不是真正的 token 流式。
**修复方法**：改用 `client.messages.stream()` 替代 `client.messages.create()`。

### 4. Qdrant 冷启动
第一次运行时 Qdrant 容器需要几秒初始化，`backend` 可能比它先启动并报连接错误。
**修复方法**：`docker-compose.yml` 加 `healthcheck` 或在 `memory.py` 加重试逻辑。

---

## 下次继续开发的步骤

### Step 1：跑通验证（预计 30 分钟）

```bash
git clone https://github.com/Jiale-jay/Ai_Agent_Project.git
cd Ai_Agent_Project

# 填入 API key
cp .env.example .env
# 编辑 .env，填写 ANTHROPIC_API_KEY 和 TAVILY_API_KEY

# 启动
docker compose up

# 访问
# http://localhost:8501  (前端)
# http://localhost:8000/docs  (API 文档)
```

### Step 2：修复已知问题（预计 1 小时）

1. 修复 `frontend/app.py` 函数顺序
2. 修复 FastAPI startup 写法
3. 添加 Qdrant 健康检查

### Step 3：实现真正的流式输出（预计 2 小时）

`backend/agent/core.py` 改造目标：

```python
# 现在：等完整响应
response = await self._client.messages.create(...)

# 目标：token 级别流式
async with self._client.messages.stream(...) as stream:
    async for text in stream.text_stream:
        yield text
```

难点：tool_use 和 text 混合时需要区分处理。

### Step 4：对话摘要压缩（预计 3 小时）

在 `memory.py` 里实现：当 `messages` token 数超过 `MAX_HISTORY_TOKENS` 时，
调用 Claude 对历史做摘要，替换掉旧消息，保留最近 N 轮。

### Step 5：部署到 Railway（预计 1 小时）

1. 注册 Railway（免费额度够 Demo 用）
2. 新建 3 个 Service：qdrant、backend、frontend
3. 设置环境变量
4. 更新 README 的 Live Demo 链接

---

## 技术决策备忘

| 决策 | 选择 | 原因 |
|------|------|------|
| 不用 LangChain | 自实现 ReAct | 展示理解底层原理，面试时说得清楚 |
| LLM 选型 | Claude claude-sonnet-4-6 | 原生 tool_use，reasoning 强 |
| 向量库 | Qdrant | Docker 部署简单，性能够用 |
| Embedding | BGE-small-en-v1.5 | 轻量，CPU 可跑，中英文都支持 |
| 前端 | Streamlit | 1天能搭完，Demo 效果好，不需要写 JS |
| 搜索工具 | Tavily | 专为 LLM 设计，有免费 tier |

---

## 面试时的讲解思路

**一句话介绍：**
> "这是一个从零实现的 ReAct Agent 系统，没有用 LangChain，用 Anthropic 的 tool_use API 直接管理工具调用循环，支持 6 种工具和双层记忆（短期对话 + 长期 Qdrant 向量存储），FastAPI 后端 + Streamlit 前端，Docker 一键部署。"

**可能被问到的技术问题：**

1. **ReAct 是什么？你怎么实现的？**
   → Reasoning + Acting，在 `core.py` 里是一个 for 循环：调 Claude → 如果有 tool_use 就执行工具 → 把结果喂回去 → 直到 end_turn

2. **为什么不用 LangChain？**
   → LangChain 封装太多，不适合演示时解释清楚；自实现 60 行代码，每一行都说得清楚

3. **记忆系统怎么设计的？**
   → 短期：in-process dict，按 session_id 存对话历史；长期：Qdrant 向量库，agent 主动调用 memory_store 工具存重要信息，需要时用 memory_recall 语义搜索

4. **Python REPL 安全怎么处理的？**
   → AST 解析检查，黑名单阻断 os/subprocess/socket 等危险模块，没有用 Docker 沙盒（演示项目够用）

5. **流式输出怎么实现的？**
   → FastAPI StreamingResponse + SSE 格式，前端用 sseclient 消费（目前是 chunk 级别，计划改成 token 级别）

---

## 资源链接

- [Anthropic tool_use 文档](https://docs.anthropic.com/en/docs/tool-use)
- [Qdrant Python Client](https://python-client.qdrant.tech/)
- [Tavily API](https://docs.tavily.com/)
- [FastAPI SSE](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
- [Railway 部署文档](https://docs.railway.app/)
