from __future__ import annotations

import asyncio
import re
import uuid
from datetime import datetime
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointIdsList,
    PointStruct,
    VectorParams,
)
from sentence_transformers import SentenceTransformer

from config import settings


class MemoryManager:
    """Short-term (in-process dict) + long-term (Qdrant) memory."""

    _VECTOR_DIM = 384  # bge-small-en-v1.5
    _DEFAULT_USER_ID = "demo-user"
    _DEFAULT_SESSION_ID = "default"
    _EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
    _PHONE_RE = re.compile(
        r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)\d{3,4}[\s.-]?\d{3,4}(?!\w)"
    )
    _CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

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
        metadata: dict[str, Any] | None = None,
        user_id: str = _DEFAULT_USER_ID,
        session_id: str = _DEFAULT_SESSION_ID,
    ) -> str:
        clean_content, pii_redacted = self._redact_pii(content)
        try:
            vector = await asyncio.to_thread(self._encoder.encode, clean_content)
            vector = vector.tolist()
        except Exception as exc:
            raise RuntimeError(f"Embedding generation failed: {exc}") from exc

        memory_id = str(uuid.uuid4())
        now = self._utc_now()
        point = PointStruct(
            id=memory_id,
            vector=vector,
            payload={
                "content": clean_content,
                "tags": tags or [],
                "metadata": metadata or {},
                "user_id": user_id,
                "session_id": session_id,
                "created_at": now,
                "updated_at": now,
                "pii_redacted": pii_redacted,
            },
        )
        try:
            await self._client.upsert(
                collection_name=settings.qdrant_collection,
                points=[point],
            )
        except Exception as exc:
            raise RuntimeError(f"Qdrant upsert failed: {exc}") from exc
        return memory_id

    async def get(
        self,
        memory_id: str,
        user_id: str = _DEFAULT_USER_ID,
        session_id: str | None = None,
    ) -> dict[str, Any] | None:
        try:
            points = await self._client.retrieve(
                collection_name=settings.qdrant_collection,
                ids=[memory_id],
                with_payload=True,
                with_vectors=False,
            )
        except Exception as exc:
            raise RuntimeError(f"Qdrant retrieve failed: {exc}") from exc

        if not points:
            return None

        item = self._point_to_record(points[0])
        if not self._record_matches_scope(item, user_id=user_id, session_id=session_id):
            return None
        return item

    async def update(
        self,
        memory_id: str,
        content: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        user_id: str = _DEFAULT_USER_ID,
        session_id: str | None = None,
    ) -> dict[str, Any] | None:
        existing = await self.get(memory_id, user_id=user_id, session_id=session_id)
        if not existing:
            return None

        next_content = existing["content"] if content is None else content
        clean_content, pii_redacted = self._redact_pii(next_content)

        try:
            vector = await asyncio.to_thread(self._encoder.encode, clean_content)
            vector = vector.tolist()
        except Exception as exc:
            raise RuntimeError(f"Embedding generation failed: {exc}") from exc

        payload = {
            "content": clean_content,
            "tags": existing.get("tags", []) if tags is None else tags,
            "metadata": existing.get("metadata", {}) if metadata is None else metadata,
            "user_id": existing.get("user_id", user_id),
            "session_id": existing.get("session_id", self._DEFAULT_SESSION_ID),
            "created_at": existing.get("created_at"),
            "updated_at": self._utc_now(),
            "pii_redacted": existing.get("pii_redacted", False) or pii_redacted,
        }
        point = PointStruct(id=memory_id, vector=vector, payload=payload)

        try:
            await self._client.upsert(
                collection_name=settings.qdrant_collection,
                points=[point],
            )
        except Exception as exc:
            raise RuntimeError(f"Qdrant update failed: {exc}") from exc

        return {"id": memory_id, **payload}

    async def delete(
        self,
        memory_id: str,
        user_id: str = _DEFAULT_USER_ID,
        session_id: str | None = None,
    ) -> bool:
        existing = await self.get(memory_id, user_id=user_id, session_id=session_id)
        if not existing:
            return False

        try:
            await self._client.delete(
                collection_name=settings.qdrant_collection,
                points_selector=PointIdsList(points=[memory_id]),
            )
        except Exception as exc:
            raise RuntimeError(f"Qdrant delete failed: {exc}") from exc
        return True

    async def search_records(
        self,
        query: str,
        limit: int = 5,
        user_id: str = _DEFAULT_USER_ID,
        session_id: str | None = None,
        tag: str | None = None,
        metadata_key: str | None = None,
        metadata_value: Any | None = None,
    ) -> list[dict[str, Any]]:
        try:
            vector = await asyncio.to_thread(self._encoder.encode, query)
            vector = vector.tolist()
            results = await self._client.query_points(
                collection_name=settings.qdrant_collection,
                query=vector,
                query_filter=self._build_filter(
                    user_id=user_id,
                    session_id=session_id,
                    tag=tag,
                    metadata_key=metadata_key,
                    metadata_value=metadata_value,
                ),
                limit=limit,
                score_threshold=0.5,
            )
        except Exception as exc:
            raise RuntimeError(f"Qdrant search failed: {exc}") from exc
        return [self._point_to_record(r, score=r.score) for r in results.points if r.payload]

    async def search(
        self,
        query: str,
        limit: int = 5,
        user_id: str = _DEFAULT_USER_ID,
        session_id: str | None = None,
        tag: str | None = None,
        metadata_key: str | None = None,
        metadata_value: Any | None = None,
    ) -> list[str]:
        results = await self.search_records(
            query,
            limit=limit,
            user_id=user_id,
            session_id=session_id,
            tag=tag,
            metadata_key=metadata_key,
            metadata_value=metadata_value,
        )
        return [r["content"] for r in results]

    async def search_text(self, query: str, limit: int = 5) -> list[str]:
        return await self.search(query, limit=limit)

    async def list_all(
        self,
        limit: int = 50,
        user_id: str = _DEFAULT_USER_ID,
        session_id: str | None = None,
        tag: str | None = None,
        metadata_key: str | None = None,
        metadata_value: Any | None = None,
    ) -> list[dict[str, Any]]:
        try:
            result, _ = await self._client.scroll(
                collection_name=settings.qdrant_collection,
                limit=limit,
                scroll_filter=self._build_filter(
                    user_id=user_id,
                    session_id=session_id,
                    tag=tag,
                    metadata_key=metadata_key,
                    metadata_value=metadata_value,
                ),
                with_payload=True,
            )
        except Exception as exc:
            raise RuntimeError(f"Qdrant scroll failed: {exc}") from exc
        return [self._point_to_record(p) for p in result if p.payload]

    @classmethod
    def _utc_now(cls) -> str:
        return datetime.utcnow().isoformat()

    @classmethod
    def _redact_pii(cls, content: str) -> tuple[str, bool]:
        redacted = content
        redacted = cls._EMAIL_RE.sub("[REDACTED_EMAIL]", redacted)
        redacted = cls._CARD_RE.sub("[REDACTED_CARD]", redacted)
        redacted = cls._PHONE_RE.sub("[REDACTED_PHONE]", redacted)
        return redacted, redacted != content

    @classmethod
    def _build_filter(
        cls,
        user_id: str = _DEFAULT_USER_ID,
        session_id: str | None = None,
        tag: str | None = None,
        metadata_key: str | None = None,
        metadata_value: Any | None = None,
    ) -> Filter:
        conditions: list[FieldCondition] = [
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
        ]
        if session_id is not None:
            conditions.append(FieldCondition(key="session_id", match=MatchValue(value=session_id)))
        if tag:
            conditions.append(FieldCondition(key="tags", match=MatchAny(any=[tag])))
        if metadata_key and metadata_value is not None:
            conditions.append(
                FieldCondition(key=f"metadata.{metadata_key}", match=MatchValue(value=metadata_value))
            )
        return Filter(must=conditions)

    @classmethod
    def _point_to_record(cls, point: Any, score: float | None = None) -> dict[str, Any]:
        payload = point.payload or {}
        record = {
            "id": str(point.id),
            "content": payload.get("content", ""),
            "tags": payload.get("tags", []),
            "metadata": payload.get("metadata", {}),
            "user_id": payload.get("user_id", cls._DEFAULT_USER_ID),
            "session_id": payload.get("session_id", cls._DEFAULT_SESSION_ID),
            "created_at": payload.get("created_at"),
            "updated_at": payload.get("updated_at"),
            "pii_redacted": payload.get("pii_redacted", False),
        }
        if score is not None:
            record["score"] = score
        return record

    @classmethod
    def _record_matches_scope(
        cls,
        record: dict[str, Any],
        user_id: str,
        session_id: str | None = None,
    ) -> bool:
        if record.get("user_id", cls._DEFAULT_USER_ID) != user_id:
            return False
        if session_id is not None and record.get("session_id", cls._DEFAULT_SESSION_ID) != session_id:
            return False
        return True
