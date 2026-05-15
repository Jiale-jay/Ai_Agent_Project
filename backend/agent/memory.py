from __future__ import annotations

import uuid
from datetime import datetime

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

from config import settings


class MemoryManager:
    """Short-term (in-process dict) + long-term (Qdrant) memory."""

    _VECTOR_DIM = 384  # bge-small-en-v1.5

    def __init__(self):
        self._client = AsyncQdrantClient(url=settings.qdrant_url)
        self._encoder = SentenceTransformer(settings.embedding_model)
        # session_id → list of message dicts
        self._short_term: dict[str, list[dict]] = {}

    async def init_collection(self) -> None:
        collections = await self._client.get_collections()
        names = [c.name for c in collections.collections]
        if settings.qdrant_collection not in names:
            await self._client.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(size=self._VECTOR_DIM, distance=Distance.COSINE),
            )

    # ── Short-term (conversation history) ──────────────────────────────────

    def get_history(self, session_id: str) -> list[dict]:
        return list(self._short_term.get(session_id, []))

    def save_history(self, session_id: str, messages: list[dict]) -> None:
        self._short_term[session_id] = messages

    def clear_history(self, session_id: str) -> None:
        self._short_term.pop(session_id, None)

    def all_sessions(self) -> list[str]:
        return list(self._short_term.keys())

    # ── Long-term (Qdrant) ──────────────────────────────────────────────────

    async def store(self, content: str, tags: list[str] | None = None) -> None:
        vector = self._encoder.encode(content).tolist()
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={
                "content": content,
                "tags": tags or [],
                "created_at": datetime.utcnow().isoformat(),
            },
        )
        await self._client.upsert(
            collection_name=settings.qdrant_collection,
            points=[point],
        )

    async def search(self, query: str, limit: int = 5) -> list[str]:
        vector = self._encoder.encode(query).tolist()
        results = await self._client.search(
            collection_name=settings.qdrant_collection,
            query_vector=vector,
            limit=limit,
            score_threshold=0.5,
        )
        return [r.payload["content"] for r in results]

    async def list_all(self, limit: int = 50) -> list[dict]:
        result, _ = await self._client.scroll(
            collection_name=settings.qdrant_collection,
            limit=limit,
            with_payload=True,
        )
        return [p.payload for p in result]
