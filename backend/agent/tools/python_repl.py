import ast
import sys
import textwrap
from io import StringIO

from .base import BaseTool, ToolResult

_BLOCKED_IMPORTS = {"os", "subprocess", "shutil", "socket", "importlib", "pathlib", "sys"}
_BLOCKED_CALLS = {"eval", "exec", "compile", "open", "__import__", "input"}
_SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "print": print,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}


def _validate_demo_code(code: str) -> str | None:
    """Demo guard only: blocks common risky operations, not a production sandbox."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return f"Syntax error: {exc}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _BLOCKED_IMPORTS:
                    return f"Importing '{root}' is not allowed in the demo Python tool."
        if isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in _BLOCKED_IMPORTS:
                return f"Importing '{root}' is not allowed in the demo Python tool."
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in _BLOCKED_CALLS:
                return f"Calling '{node.func.id}' is not allowed in the demo Python tool."

    return None


class PythonReplTool(BaseTool):
    name = "python_repl"
    description = "Execute small Python snippets for demo data processing. Uses guardrails, not a production sandbox."

    async def run(self, code: str) -> ToolResult:
        if len(code) > 3000:
            return ToolResult(success=False, error="Code is too long for the demo Python tool.")

        validation_error = _validate_demo_code(code)
        if validation_error:
            return ToolResult(success=False, error=validation_error)

        stdout = StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = stdout
            local_ns: dict = {}
            exec(textwrap.dedent(code), {"__builtins__": _SAFE_BUILTINS}, local_ns)  # noqa: S102
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
