from io import BytesIO

import pytest
from starlette.datastructures import UploadFile

from fastapi import HTTPException

from api.routes import memory as memory_route


class FakeMemory:
    def __init__(self):
        self.stored = []
        self.documents = [
            {
                "document_id": "doc-1",
                "filename": "policy.md",
                "tags": ["policy"],
                "uploaded_at": "2026-05-01T00:00:00",
                "chunk_count": 1,
            }
        ]

    async def store(self, content, tags=None, metadata=None, **kwargs):
        self.stored.append((content, tags, metadata, kwargs))
        return f"mem-{len(self.stored)}"

    async def list_documents(self, **kwargs):
        return self.documents

    async def get_document(self, document_id, **kwargs):
        if document_id != "doc-1":
            return None
        return {"document_id": "doc-1", "filename": "policy.md", "chunk_count": 1, "chunks": []}

    async def delete_document(self, document_id, **kwargs):
        return 1 if document_id == "doc-1" else 0


@pytest.mark.asyncio
async def test_upload_document_stores_text_chunks(monkeypatch):
    fake_memory = FakeMemory()
    monkeypatch.setattr(memory_route, "_get_memory", lambda: fake_memory)
    content = b"Expense claims over EUR 1,000 require manager approval and finance review."
    upload = UploadFile(filename="expense-policy.md", file=BytesIO(content))

    result = await memory_route.upload_document(upload, tags="policy, finance")

    assert result["stored"] is True
    assert result["filename"] == "expense-policy.md"
    assert result["document_id"]
    assert result["chunks"] == 1
    assert fake_memory.stored[0][1] == ["policy", "finance"]
    assert fake_memory.stored[0][2]["document_id"] == result["document_id"]
    assert fake_memory.stored[0][2]["filename"] == "expense-policy.md"


@pytest.mark.asyncio
async def test_upload_document_rejects_empty_file(monkeypatch):
    monkeypatch.setattr(memory_route, "_get_memory", lambda: FakeMemory())
    upload = UploadFile(filename="empty.md", file=BytesIO(b""))

    with pytest.raises(HTTPException) as exc_info:
        await memory_route.upload_document(upload, tags="policy")

    assert "Uploaded document is empty" in str(exc_info.value)


@pytest.mark.asyncio
async def test_upload_document_rejects_unparseable_pdf(monkeypatch):
    monkeypatch.setattr(memory_route, "_get_memory", lambda: FakeMemory())
    upload = UploadFile(filename="policy.pdf", file=BytesIO(b"%PDF-1.4"))

    with pytest.raises(HTTPException) as exc_info:
        await memory_route.upload_document(upload, tags="policy")

    assert exc_info.value.status_code == 400
    assert "PDF could not be parsed" in exc_info.value.detail


@pytest.mark.asyncio
async def test_document_routes_manage_documents(monkeypatch):
    monkeypatch.setattr(memory_route, "_get_memory", lambda: FakeMemory())

    listed = await memory_route.list_documents(session_id="s1")
    detail = await memory_route.get_document("doc-1", session_id="s1")
    deleted = await memory_route.delete_document("doc-1", session_id="s1")

    assert listed["count"] == 1
    assert listed["documents"][0]["document_id"] == "doc-1"
    assert detail["document"]["filename"] == "policy.md"
    assert deleted == {"deleted": True, "document_id": "doc-1", "chunks": 1}
