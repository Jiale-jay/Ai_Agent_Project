import pytest

from agent.tools.calculator import CalculatorTool
from agent.tools.memory_tool import MemoryRecallTool, MemoryStoreTool
from agent.tools.python_repl import PythonReplTool
from agent.tools.search import SearchTool


@pytest.mark.asyncio
async def test_calculator_evaluates_safe_expression():
    result = await CalculatorTool().run(expression="(10 + 5) * 3")

    assert result.success is True
    assert result.output == "45"


@pytest.mark.asyncio
async def test_calculator_rejects_unsupported_expression():
    result = await CalculatorTool().run(expression="max(1, 2)")

    assert result.success is False
    assert "Unsupported expression" in result.error


@pytest.mark.asyncio
async def test_python_repl_blocks_demo_unsafe_imports():
    result = await PythonReplTool().run(code="import os\nprint(os.getcwd())")

    assert result.success is False
    assert "not allowed" in result.error


@pytest.mark.asyncio
async def test_python_repl_runs_small_data_processing_snippet():
    result = await PythonReplTool().run(code="values = [1, 2, 3]\nprint(sum(values))")

    assert result.success is True
    assert result.output.strip() == "6"


@pytest.mark.asyncio
async def test_search_without_key_returns_clear_error(monkeypatch):
    monkeypatch.setattr("agent.tools.search.settings.tavily_api_key", "")

    result = await SearchTool().run(query="latest AI news")

    assert result.success is False
    assert "TAVILY_API_KEY not set" in result.error


class FakeMemory:
    def __init__(self):
        self.stored = []

    async def store(self, content, tags=None):
        self.stored.append((content, tags))

    async def search(self, query, limit=5):
        return [{
            "content": "Expense claims over EUR 1,000 require manager approval.",
            "metadata": {"filename": "expense-policy.md", "chunk_index": 1},
        }]


@pytest.mark.asyncio
async def test_memory_tools_store_and_recall():
    memory = FakeMemory()

    stored = await MemoryStoreTool(memory).run("Remember approval policy", ["policy"])
    recalled = await MemoryRecallTool(memory).run("approval", limit=1)

    assert stored.success is True
    assert memory.stored == [("Remember approval policy", ["policy"])]
    assert recalled.success is True
    assert "manager approval" in recalled.output
    assert "expense-policy.md" in recalled.output
