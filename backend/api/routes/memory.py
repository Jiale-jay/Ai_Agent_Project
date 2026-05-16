from fastapi import APIRouter

from api.models import MemoryStoreRequest

router = APIRouter()


def _get_memory():
    from api.routes.chat import _memory
    return _memory


@router.get("/")
async def list_memories():
    memory = _get_memory()
    try:
        items = await memory.list_all()
        return {"count": len(items), "items": items}
    except Exception as exc:
        return {"count": 0, "items": [], "error": str(exc)}


@router.post("/")
async def store_memory(request: MemoryStoreRequest):
    memory = _get_memory()
    try:
        await memory.store(request.content, request.tags, request.metadata)
        return {"stored": True}
    except Exception as exc:
        return {"stored": False, "error": str(exc)}


@router.get("/search")
async def search_memory(q: str, limit: int = 5):
    memory = _get_memory()
    try:
        results = await memory.search(q, limit=limit)
        return {"query": q, "results": results}
    except Exception as exc:
        return {"query": q, "results": [], "error": str(exc)}
