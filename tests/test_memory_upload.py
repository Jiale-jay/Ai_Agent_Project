from io import BytesIO

import pytest
from starlette.datastructures import UploadFile

from fastapi import HTTPException

from api.routes import memory as memory_route


class FakeMemory:
    def __init__(self):
        self.stored = []

    async def store(self, content, tags=None, metadata=None, **kwargs):
        self.stored.append((content, tags, metadata, kwargs))
        return f"mem-{len(self.stored)}"


@pytest.mark.asyncio
async def test_upload_document_stores_text_chunks(monkeypatch):
    fake_memory = FakeMemory()
    monkeypatch.setattr(memory_route, "_get_memory", lambda: fake_memory)
    content = b"Expense claims over EUR 1,000 require manager approval and finance review."
    upload = UploadFile(filename="expense-policy.md", file=BytesIO(content))

    result = await memory_route.upload_document(upload, tags="policy, finance")

    assert result["stored"] is True
    assert result["filename"] == "expense-policy.md"
    assert result["chunks"] == 1
    assert fake_memory.stored[0][1] == ["policy", "finance"]
    assert fake_memory.stored[0][2]["filename"] == "expense-policy.md"


@pytest.mark.asyncio
async def test_upload_document_rejects_empty_file(monkeypatch):
    monkeypatch.setattr(memory_route, "_get_memory", lambda: FakeMemory())
    upload = UploadFile(filename="empty.md", file=BytesIO(b""))

    with pytest.raises(HTTPException) as exc_info:
        await memory_route.upload_document(upload, tags="policy")

    assert "Uploaded document is empty" in str(exc_info.value)


@pytest.mark.asyncio
async def test_upload_document_rejects_unsupported_file_type(monkeypatch):
    monkeypatch.setattr(memory_route, "_get_memory", lambda: FakeMemory())
    upload = UploadFile(filename="policy.pdf", file=BytesIO(b"%PDF-1.4"))

    with pytest.raises(HTTPException) as exc_info:
        await memory_route.upload_document(upload, tags="policy")

    assert exc_info.value.status_code == 400
    assert "Unsupported file type" in exc_info.value.detail
