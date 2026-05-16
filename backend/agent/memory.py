from __future__ import annotations

import asyncio
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
        self._ready = False

    async def init_collection(self) -> None:
        try:
            collections = await self._client.get_collections()
            names = [c.name for c in collections.collections]
            if settings.qdrant_collection not in names:
                await self._client.create_collection(
                    collection_name=settings.qdrant_collection,
                    vectors_config=VectorParams(size=self._VECTOR_DIM, distance=Distance.COSINE),
                )
            self._ready = True
        except Exception as exc:
            self._ready = False
            raise RuntimeError(f"Qdrant memory initialization failed: {exc}") from exc

    async def health(self) -> dict:
        try:
            await self._client.get_collections()
            return {"ready": True, "collection": settings.qdrant_collection}
        except Exception as exc:
            return {"ready": False, "collection": settings.qdrant_collection, "error": str(exc)}

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

    async def store(
        self,
        content: str,
        tags: list[str] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> None:
        try:
            vector = await asyncio.to_thread(self._encoder.encode, content)
            vector = vector.tolist()
        except Exception as exc:
            raise RuntimeError(f"Embedding generation failed: {exc}") from exc

        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={
                "content": content,
                "tags": tags or [],
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat(),
            },
        )
        try:
            await self._client.upsert(
                collection_name=settings.qdrant_collection,
                points=[point],
            )
        except Exception as exc:
            raise RuntimeError(f"Qdrant upsert failed: {exc}") from exc

    async def search(self, query: str, limit: int = 5) -> list[str]:
        try:
            vector = await asyncio.to_thread(self._encoder.encode, query)
            vector = vector.tolist()
            results = await self._client.search(
                collection_name=settings.qdrant_collection,
                query_vector=vector,
                limit=limit,
                score_threshold=0.5,
            )
        except Exception as exc:
            raise RuntimeError(f"Qdrant search failed: {exc}") from exc
        return [r.payload["content"] for r in results]

    async def list_all(self, limit: int = 50) -> list[dict]:
        try:
            result, _ = await self._client.scroll(
                collection_name=settings.qdrant_collection,
                limit=limit,
                with_payload=True,
            )
        except Exception as exc:
            raise RuntimeError(f"Qdrant scroll failed: {exc}") from exc
        return [p.payload for p in result]
