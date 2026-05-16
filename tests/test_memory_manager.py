from types import SimpleNamespace

import pytest

from agent.memory import MemoryManager


class FakeVector:
    def __init__(self, text):
        self.text = text

    def tolist(self):
        return [float(len(self.text)), 0.0, 1.0]


class FakeEncoder:
    def __init__(self):
        self.encoded = []

    def encode(self, text):
        self.encoded.append(text)
        return FakeVector(text)


class FakeQdrantClient:
    def __init__(self):
        self.points = {}
        self.deleted = []
        self.last_query_filter = None
        self.last_scroll_filter = None

    async def upsert(self, collection_name, points):
        for point in points:
            self.points[str(point.id)] = SimpleNamespace(
                id=str(point.id),
                vector=point.vector,
                payload=point.payload,
            )

    async def retrieve(self, collection_name, ids, with_payload=True, with_vectors=False):
        return [self.points[str(point_id)] for point_id in ids if str(point_id) in self.points]

    async def delete(self, collection_name, points_selector):
        for point_id in points_selector.points:
            self.deleted.append(str(point_id))
            self.points.pop(str(point_id), None)

    async def query_points(self, collection_name, query, query_filter=None, limit=5, score_threshold=0.5):
        self.last_query_filter = query_filter
        points = [
            SimpleNamespace(id=point.id, payload=point.payload, score=0.9)
            for point in self.points.values()
            if self._matches_filter(point.payload, query_filter)
        ]
        return SimpleNamespace(points=points[:limit])

    async def scroll(self, collection_name, limit=50, scroll_filter=None, with_payload=True):
        self.last_scroll_filter = scroll_filter
        points = [
            point
            for point in self.points.values()
            if self._matches_filter(point.payload, scroll_filter)
        ]
        return points[:limit], None

    def _matches_filter(self, payload, qdrant_filter):
        if not qdrant_filter:
            return True
        for condition in qdrant_filter.must:
            actual = self._payload_value(payload, condition.key)
            expected = condition.match.value if hasattr(condition.match, "value") else None
            expected_any = condition.match.any if hasattr(condition.match, "any") else None
            if expected_any is not None:
                if actual not in expected_any and not (
                    isinstance(actual, list) and any(item in expected_any for item in actual)
                ):
                    return False
            elif actual != expected:
                return False
        return True

    @staticmethod
    def _payload_value(payload, key):
        current = payload
        for part in key.split("."):
            current = current.get(part)
            if current is None:
                return None
        return current


@pytest.fixture
def memory():
    manager = MemoryManager.__new__(MemoryManager)
    manager._client = FakeQdrantClient()
    manager._encoder = FakeEncoder()
    manager._short_term = {}
    manager._ready = True
    return manager


@pytest.mark.asyncio
async def test_store_returns_id_and_redacts_pii(memory):
    memory_id = await memory.store(
        "Email jane@example.com or call +353 87 123 4567",
        tags=["contact"],
        metadata={"source": "test"},
        user_id="u1",
        session_id="s1",
    )

    item = await memory.get(memory_id, user_id="u1", session_id="s1")

    assert item["id"] == memory_id
    assert "jane@example.com" not in item["content"]
    assert "+353 87 123 4567" not in item["content"]
    assert item["pii_redacted"] is True
    assert item["user_id"] == "u1"
    assert item["session_id"] == "s1"
    assert item["created_at"]
    assert item["updated_at"]
    assert memory._encoder.encoded == [item["content"]]


@pytest.mark.asyncio
async def test_list_and_search_apply_scope_and_metadata_filters(memory):
    await memory.store("Alpha finance policy", ["policy"], {"source": "handbook"}, user_id="u1", session_id="s1")
    await memory.store("Beta HR policy", ["policy"], {"source": "handbook"}, user_id="u2", session_id="s1")
    await memory.store("Gamma finance FAQ", ["faq"], {"source": "faq"}, user_id="u1", session_id="s2")

    listed = await memory.list_all(
        user_id="u1",
        session_id="s1",
        tag="policy",
        metadata_key="source",
        metadata_value="handbook",
    )
    searched = await memory.search_records(
        "finance",
        user_id="u1",
        session_id="s1",
        tag="policy",
        metadata_key="source",
        metadata_value="handbook",
    )

    assert [item["content"] for item in listed] == ["Alpha finance policy"]
    assert [item["content"] for item in searched] == ["Alpha finance policy"]
    assert await memory.search("finance", user_id="u1", session_id="s1") == ["Alpha finance policy"]


@pytest.mark.asyncio
async def test_update_rewrites_payload_and_preserves_created_at(memory):
    memory_id = await memory.store("Old content", ["old"], {"source": "draft"}, user_id="u1", session_id="s1")
    before = await memory.get(memory_id, user_id="u1", session_id="s1")

    updated = await memory.update(
        memory_id,
        content="New card 4111 1111 1111 1111",
        tags=["new"],
        metadata={"source": "final"},
        user_id="u1",
        session_id="s1",
    )

    assert updated["id"] == memory_id
    assert updated["created_at"] == before["created_at"]
    assert updated["updated_at"] >= before["updated_at"]
    assert updated["content"] == "New card [REDACTED_CARD]"
    assert updated["tags"] == ["new"]
    assert updated["metadata"] == {"source": "final"}
    assert updated["pii_redacted"] is True


@pytest.mark.asyncio
async def test_delete_respects_user_and_session_scope(memory):
    memory_id = await memory.store("Scoped memory", user_id="u1", session_id="s1")

    assert await memory.delete(memory_id, user_id="u2", session_id="s1") is False
    assert memory_id in memory._client.points

    assert await memory.delete(memory_id, user_id="u1", session_id="s1") is True
    assert memory_id not in memory._client.points
