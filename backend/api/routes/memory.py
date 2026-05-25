from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from agent.documents import build_document_chunks, decode_document_pages
from api.models import MemoryStoreRequest, MemoryUpdateRequest

router = APIRouter()


def _get_memory():
    from api.routes.chat import _memory
    return _memory


@router.get("/")
async def list_memories(
    user_id: str = "demo-user",
    session_id: str | None = None,
    tag: str | None = None,
    metadata_key: str | None = None,
    metadata_value: str | None = None,
    limit: int = 50,
):
    memory = _get_memory()
    try:
        items = await memory.list_all(
            limit=limit,
            user_id=user_id,
            session_id=session_id,
            tag=tag,
            metadata_key=metadata_key,
            metadata_value=metadata_value,
        )
        return {"count": len(items), "items": items}
    except Exception as exc:
        return {"count": 0, "items": [], "error": str(exc)}


@router.post("/")
async def store_memory(request: MemoryStoreRequest):
    memory = _get_memory()
    try:
        memory_id = await memory.store(
            request.content,
            request.tags,
            request.metadata,
            user_id=request.user_id,
            session_id=request.session_id,
        )
        item = await memory.get(memory_id, user_id=request.user_id, session_id=request.session_id)
        return {"stored": True, "id": memory_id, "item": item}
    except Exception as exc:
        return {"stored": False, "error": str(exc)}


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    tags: str = Form(default="policy,enterprise"),
    user_id: str = Form(default="demo-user"),
    session_id: str = Form(default="default"),
):
    memory = _get_memory()
    raw_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded document is empty.")

    try:
        pages = decode_document_pages(file.filename or "uploaded.txt", data)
        chunks = build_document_chunks(file.filename or "uploaded.txt", pages, raw_tags)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not chunks:
        raise HTTPException(status_code=400, detail="Uploaded document contains no text.")

    try:
        memory_ids = []
        for chunk in chunks:
            memory_id = await memory.store(
                chunk.content,
                raw_tags,
                chunk.metadata,
                user_id=user_id,
                session_id=session_id,
            )
            memory_ids.append(memory_id)
    except Exception as exc:
        return {"stored": False, "chunks": 0, "filename": file.filename, "error": str(exc)}

    return {
        "stored": True,
        "filename": file.filename,
        "document_id": chunks[0].metadata["document_id"],
        "chunks": len(chunks),
        "tags": raw_tags,
        "ids": memory_ids,
    }


@router.get("/documents")
async def list_documents(
    user_id: str = "demo-user",
    session_id: str | None = None,
    limit: int = 200,
):
    memory = _get_memory()
    try:
        documents = await memory.list_documents(limit=limit, user_id=user_id, session_id=session_id)
        return {"count": len(documents), "documents": documents}
    except Exception as exc:
        return {"count": 0, "documents": [], "error": str(exc)}


@router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    user_id: str = "demo-user",
    session_id: str | None = None,
):
    memory = _get_memory()
    try:
        document = await memory.get_document(document_id, user_id=user_id, session_id=session_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found.")
        return {"document": document}
    except HTTPException:
        raise
    except Exception as exc:
        return {"document": None, "error": str(exc)}


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    user_id: str = "demo-user",
    session_id: str | None = None,
):
    memory = _get_memory()
    try:
        deleted_chunks = await memory.delete_document(document_id, user_id=user_id, session_id=session_id)
        if deleted_chunks == 0:
            raise HTTPException(status_code=404, detail="Document not found.")
        return {"deleted": True, "document_id": document_id, "chunks": deleted_chunks}
    except HTTPException:
        raise
    except Exception as exc:
        return {"deleted": False, "document_id": document_id, "error": str(exc)}


@router.get("/search")
async def search_memory(
    q: str,
    limit: int = 5,
    user_id: str = "demo-user",
    session_id: str | None = None,
    tag: str | None = None,
    metadata_key: str | None = None,
    metadata_value: str | None = None,
):
    memory = _get_memory()
    try:
        items = await memory.search_records(
            q,
            limit=limit,
            user_id=user_id,
            session_id=session_id,
            tag=tag,
            metadata_key=metadata_key,
            metadata_value=metadata_value,
        )
        return {"query": q, "results": [item["content"] for item in items], "items": items}
    except Exception as exc:
        return {"query": q, "results": [], "items": [], "error": str(exc)}


@router.get("/{memory_id}")
async def get_memory(memory_id: str, user_id: str = "demo-user", session_id: str | None = None):
    memory = _get_memory()
    try:
        item = await memory.get(memory_id, user_id=user_id, session_id=session_id)
        if not item:
            raise HTTPException(status_code=404, detail="Memory not found.")
        return {"item": item}
    except HTTPException:
        raise
    except Exception as exc:
        return {"item": None, "error": str(exc)}


@router.patch("/{memory_id}")
async def update_memory(
    memory_id: str,
    request: MemoryUpdateRequest,
    user_id: str = "demo-user",
    session_id: str | None = None,
):
    memory = _get_memory()
    try:
        item = await memory.update(
            memory_id,
            content=request.content,
            tags=request.tags,
            metadata=request.metadata,
            user_id=user_id,
            session_id=session_id,
        )
        if not item:
            raise HTTPException(status_code=404, detail="Memory not found.")
        return {"updated": True, "id": memory_id, "item": item}
    except HTTPException:
        raise
    except Exception as exc:
        return {"updated": False, "id": memory_id, "error": str(exc)}


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str, user_id: str = "demo-user", session_id: str | None = None):
    memory = _get_memory()
    try:
        deleted = await memory.delete(memory_id, user_id=user_id, session_id=session_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Memory not found.")
        return {"deleted": True, "id": memory_id}
    except HTTPException:
        raise
    except Exception as exc:
        return {"deleted": False, "id": memory_id, "error": str(exc)}
