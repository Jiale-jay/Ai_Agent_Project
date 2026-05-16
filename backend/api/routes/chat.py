import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from agent import Agent, MemoryManager
from api.models import ChatRequest

router = APIRouter()

_memory = MemoryManager()
_agent = Agent(_memory)


@router.post("/")
async def chat(request: ChatRequest):
    async def _stream():
        async for chunk in _agent.run(request.message, request.session_id, mode=request.mode):
            # JSON-encode to safely handle newlines in chunk content
            yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: \"[DONE]\"\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")
