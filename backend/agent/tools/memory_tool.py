from __future__ import annotations

from typing import TYPE_CHECKING

from .base import BaseTool, ToolResult

if TYPE_CHECKING:
    from agent.memory import MemoryManager


class MemoryStoreTool(BaseTool):
    name = "memory_store"
    description = "Save an important piece of information to long-term memory."

    def __init__(self, memory_manager: MemoryManager):
        self._memory = memory_manager

    async def run(self, content: str, tags: list[str] | None = None) -> ToolResult:
        try:
            memory_id = await self._memory.store(content, tags or [])
            suffix = f" (id: {memory_id})" if memory_id else ""
            return ToolResult(success=True, output=f"Stored{suffix}: {content[:80]}...")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def to_claude_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Information to remember"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags for categorization",
                    },
                },
                "required": ["content"],
            },
        }


class MemoryRecallTool(BaseTool):
    name = "memory_recall"
    description = "Search long-term memory for relevant stored information."

    def __init__(self, memory_manager: MemoryManager):
        self._memory = memory_manager

    async def run(self, query: str, limit: int = 5) -> ToolResult:
        try:
            results = await self._memory.search(query, limit=limit)
            if not results:
                return ToolResult(success=True, output="No relevant memories found.")
            output = "\n\n".join(f"[{i+1}] {self._format_result(r)}" for i, r in enumerate(results))
            return ToolResult(success=True, output=output)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    @staticmethod
    def _format_result(result) -> str:
        if isinstance(result, str):
            return result
        metadata = result.get("metadata", {})
        filename = metadata.get("filename") or metadata.get("source")
        chunk_index = metadata.get("chunk_index")
        source = ""
        if filename:
            source = f" ({filename}"
            if chunk_index:
                source += f", chunk {chunk_index}"
            source += ")"
        return f"{result.get('content', '')}{source}"

    def to_claude_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for"},
                    "limit": {"type": "integer", "description": "Max results", "default": 5},
                },
                "required": ["query"],
            },
        }
