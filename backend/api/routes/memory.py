from fastapi import APIRouter

from api.models import MemoryStoreRequest

router = APIRouter()


def _get_memory():
    from api.routes.chat import _memory
    return _memory


@router.get("/")
async def list_memories():
    memory = _get_memory()
    items = await memory.list_all()
    return {"count": len(items), "items": items}


@router.post("/")
async def store_memory(request: MemoryStoreRequest):
    memory = _get_memory()
    await memory.store(request.content, request.tags)
    return {"stored": True}


@router.get("/search")
async def search_memory(q: str, limit: int = 5):
    memory = _get_memory()
    results = await memory.search(q, limit=limit)
    return {"query": q, "results": results}
