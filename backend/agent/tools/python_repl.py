import asyncio
import sys
import textwrap
from io import StringIO

from .base import BaseTool, ToolResult

_BLOCKED = {"os", "subprocess", "shutil", "socket", "importlib", "__import__"}


class PythonReplTool(BaseTool):
    name = "python_repl"
    description = "Execute Python code snippets. Good for data processing, calculations, and transformations."

    async def run(self, code: str) -> ToolResult:
        # Block dangerous imports
        for blocked in _BLOCKED:
            if blocked in code:
                return ToolResult(
                    success=False,
                    error=f"Use of '{blocked}' is not allowed.",
                )

        stdout = StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = stdout
            local_ns: dict = {}
            exec(textwrap.dedent(code), {"__builtins__": __builtins__}, local_ns)  # noqa: S102
            output = stdout.getvalue()
            # Also capture last expression value if no print
            if not output and local_ns:
                last = list(local_ns.values())[-1]
                output = repr(last)
            return ToolResult(success=True, output=output or "(no output)")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
        finally:
            sys.stdout = old_stdout

    def to_claude_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute",
                    }
                },
                "required": ["code"],
            },
        }
