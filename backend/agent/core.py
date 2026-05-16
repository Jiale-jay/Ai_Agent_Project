from __future__ import annotations

import json
from collections.abc import AsyncGenerator

import anthropic

from agent.memory import MemoryManager
from agent.tools.base import BaseTool
from agent.tools.memory_tool import MemoryRecallTool, MemoryStoreTool
from config import settings

SYSTEM_PROMPT = """You are a helpful AI assistant with access to tools.
Use tools when you need current information, need to calculate, run code, or recall/save information.
Think step by step. Be concise and accurate."""

DIRECT_SYSTEM_PROMPT = """You are an enterprise GenAI assistant.
Answer directly and concisely. Do not claim to have checked internal documents or tools."""

RAG_SYSTEM_PROMPT = """You are an enterprise RAG assistant.
Use only the supplied knowledge snippets as grounding context. If the snippets do not answer the question, say what is missing and suggest a safe next step. Cite snippets as [1], [2], etc."""

_SUMMARY_PROMPT = "Summarize the following conversation history in 2-3 sentences, preserving key facts, decisions, and context the assistant should remember."


class Agent:
    def __init__(self, memory: MemoryManager):
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._memory = memory
        self._tools: dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        from agent.tools import CalculatorTool, PythonReplTool, SearchTool, WebFetchTool

        for tool in [
            SearchTool(),
            CalculatorTool(),
            PythonReplTool(),
            WebFetchTool(),
            MemoryStoreTool(self._memory),
            MemoryRecallTool(self._memory),
        ]:
            self._tools[tool.name] = tool

    @property
    def _claude_tools(self) -> list[dict]:
        return [t.to_claude_schema() for t in self._tools.values()]

    async def _stream_text_response(
        self,
        messages: list[dict],
        system_prompt: str,
        save_to_session: tuple[str, list[dict]] | None = None,
    ) -> AsyncGenerator[str, None]:
        chunks: list[str] = []
        async with self._client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system_prompt,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                chunks.append(text)
                yield text
            await stream.get_final_message()

        if save_to_session:
            session_id, history = save_to_session
            history.append({"role": "assistant", "content": "".join(chunks)})
            self._memory.save_history(session_id, history)

    async def run_direct(self, user_message: str, session_id: str) -> AsyncGenerator[str, None]:
        messages = self._memory.get_history(session_id)
        messages.append({"role": "user", "content": user_message})
        messages = await self._maybe_compress(messages)
        async for chunk in self._stream_text_response(
            messages,
            DIRECT_SYSTEM_PROMPT,
            save_to_session=(session_id, messages),
        ):
            yield chunk

    async def run_rag(self, user_message: str, session_id: str) -> AsyncGenerator[str, None]:
        messages = self._memory.get_history(session_id)
        messages.append({"role": "user", "content": user_message})
        messages = await self._maybe_compress(messages)

        try:
            snippets = await self._memory.search(user_message, limit=5)
        except Exception as exc:
            yield f"RAG retrieval is unavailable: {exc}"
            self._memory.save_history(session_id, messages)
            return

        if not snippets:
            yield "I could not find relevant enterprise knowledge for this question. Please add a policy, FAQ, or process note to the knowledge base first."
            self._memory.save_history(session_id, messages)
            return

        context = "\n\n".join(f"[{i}] {snippet}" for i, snippet in enumerate(snippets, start=1))
        rag_messages = [
            {
                "role": "user",
                "content": (
                    f"Enterprise knowledge snippets:\n{context}\n\n"
                    f"User question:\n{user_message}"
                ),
            }
        ]
        async for chunk in self._stream_text_response(
            rag_messages,
            RAG_SYSTEM_PROMPT,
            save_to_session=(session_id, messages),
        ):
            yield chunk

    async def _maybe_compress(self, messages: list[dict]) -> list[dict]:
        """Summarize old messages when history exceeds max_history_tokens (est. chars/4)."""
        keep_recent = 6  # always keep last 3 exchanges
        if len(messages) <= keep_recent:
            return messages

        estimated_tokens = sum(len(str(m)) for m in messages) // 4
        if estimated_tokens <= settings.max_history_tokens:
            return messages

        old = messages[:-keep_recent]
        recent = messages[-keep_recent:]

        # Extract text content for summarization, skip tool_use / tool_result blocks
        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}"
            for m in old
            if isinstance(m.get("content"), str)
        )

        resp = await self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": f"{_SUMMARY_PROMPT}\n\n{history_text}"}],
        )
        summary = resp.content[0].text

        return [
            {"role": "user", "content": f"[Earlier conversation summary: {summary}]"},
            {"role": "assistant", "content": "Understood, I have the context from our earlier conversation."},
            *recent,
        ]

    async def run_agent(self, user_message: str, session_id: str) -> AsyncGenerator[str, None]:
        messages = self._memory.get_history(session_id)
        messages.append({"role": "user", "content": user_message})
        messages = await self._maybe_compress(messages)

        for _ in range(settings.max_iterations):
            # Real token-level streaming: yield text as it arrives, then inspect final message
            async with self._client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=self._claude_tools,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
                response = await stream.get_final_message()

            if response.stop_reason == "end_turn":
                assistant_text = "".join(
                    block.text for block in response.content if hasattr(block, "text")
                )
                messages.append({"role": "assistant", "content": assistant_text})
                self._memory.save_history(session_id, messages)
                return

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []

                for block in response.content:
                    if block.type == "tool_use":
                        yield f"\n```tool\n🔧 {block.name}({json.dumps(block.input, ensure_ascii=False)})\n```\n"

                        tool = self._tools.get(block.name)
                        if tool:
                            result = await tool.run(**block.input)
                            output = result.output if result.success else f"Error: {result.error}"
                        else:
                            output = f"Unknown tool: {block.name}"

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": output,
                        })

                messages.append({"role": "user", "content": tool_results})

        yield "\n⚠️ Reached max iterations without a final answer."

    async def run(self, user_message: str, session_id: str, mode: str = "agent") -> AsyncGenerator[str, None]:
        if mode == "direct":
            async for chunk in self.run_direct(user_message, session_id):
                yield chunk
            return
        if mode == "rag":
            async for chunk in self.run_rag(user_message, session_id):
                yield chunk
            return
        async for chunk in self.run_agent(user_message, session_id):
            yield chunk
