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

    async def run(self, user_message: str, session_id: str) -> AsyncGenerator[str, None]:
        messages = self._memory.get_history(session_id)
        messages.append({"role": "user", "content": user_message})

        for _ in range(settings.max_iterations):
            response = await self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=self._claude_tools,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                assistant_text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        assistant_text += block.text

                messages.append({"role": "assistant", "content": assistant_text})
                self._memory.save_history(session_id, messages)
                yield assistant_text
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
