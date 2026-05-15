from abc import ABC, abstractmethod
from pydantic import BaseModel


class ToolResult(BaseModel):
    success: bool
    output: str
    error: str = ""


class BaseTool(ABC):
    name: str
    description: str

    @abstractmethod
    async def run(self, **kwargs) -> ToolResult:
        pass

    @abstractmethod
    def to_claude_schema(self) -> dict:
        """Return Anthropic tool_use compatible schema."""
        pass
