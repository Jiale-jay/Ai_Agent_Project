import os
from types import MethodType

import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from agent.core import Agent  # noqa: E402
from config import settings  # noqa: E402


class FakeMemory:
    def __init__(self, search_results=None):
        self.history = {}
        self.saved = {}
        self.search_results = search_results or []

    def get_history(self, session_id):
        return list(self.history.get(session_id, []))

    def save_history(self, session_id, messages):
        self.saved[session_id] = messages

    async def search(self, query, limit=5):
        return self.search_results


async def fake_stream_text_response(self, messages, system_prompt, save_to_session=None):
    yield "grounded answer"
    if save_to_session:
        session_id, history = save_to_session
        history.append({"role": "assistant", "content": "grounded answer"})
        self._memory.save_history(session_id, history)


def make_agent(memory):
    agent = Agent.__new__(Agent)
    agent._memory = memory
    agent._tools = {}
    agent._stream_text_response = MethodType(fake_stream_text_response, agent)
    return agent


@pytest.mark.asyncio
async def test_direct_mode_saves_plain_response():
    memory = FakeMemory()
    agent = make_agent(memory)

    chunks = [chunk async for chunk in agent.run("hello", "s1", mode="direct")]

    assert chunks == ["grounded answer"]
    assert memory.saved["s1"][-1]["content"] == "grounded answer"


@pytest.mark.asyncio
async def test_rag_mode_requires_knowledge_when_search_empty():
    memory = FakeMemory(search_results=[])
    agent = make_agent(memory)

    chunks = [chunk async for chunk in agent.run("What is the policy?", "s1", mode="rag")]

    assert "could not find relevant enterprise knowledge" in "".join(chunks)


@pytest.mark.asyncio
async def test_rag_mode_uses_retrieved_knowledge():
    memory = FakeMemory(search_results=["Expense claims over EUR 1,000 require review."])
    agent = make_agent(memory)

    chunks = [chunk async for chunk in agent.run("What is the expense policy?", "s1", mode="rag")]

    assert chunks == ["grounded answer"]
    assert memory.saved["s1"][-1]["content"] == "grounded answer"


@pytest.mark.asyncio
async def test_agent_mode_reports_max_iterations(monkeypatch):
    memory = FakeMemory()
    agent = make_agent(memory)
    monkeypatch.setattr(settings, "max_iterations", 0)

    chunks = [chunk async for chunk in agent.run("use a tool", "s1", mode="agent")]

    assert "Reached max iterations" in "".join(chunks)
