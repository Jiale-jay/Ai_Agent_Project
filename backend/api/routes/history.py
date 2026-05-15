from fastapi import APIRouter

from agent import MemoryManager

router = APIRouter()
_memory: MemoryManager | None = None


def _get_memory() -> MemoryManager:
    from api.routes.chat import _memory as m
    return m


@router.get("/{session_id}")
async def get_history(session_id: str):
    memory = _get_memory()
    return {"session_id": session_id, "messages": memory.get_history(session_id)}


@router.delete("/{session_id}")
async def clear_history(session_id: str):
    memory = _get_memory()
    memory.clear_history(session_id)
    return {"cleared": session_id}


@router.get("/")
async def list_sessions():
    memory = _get_memory()
    return {"sessions": memory.all_sessions()}
