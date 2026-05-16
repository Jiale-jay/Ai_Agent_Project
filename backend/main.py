from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.automation import router as automation_router
from api.routes.chat import router as chat_router, _memory
from api.routes.history import router as history_router
from api.routes.memory import router as memory_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await _memory.init_collection()
    except RuntimeError as exc:
        app.state.memory_startup_error = str(exc)
    yield


app = FastAPI(title="AI Agent API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(history_router, prefix="/history", tags=["history"])
app.include_router(memory_router, prefix="/memory", tags=["memory"])
app.include_router(automation_router, prefix="/automation", tags=["automation"])


@app.get("/health")
async def health():
    memory = await _memory.health()
    return {
        "status": "ok",
        "memory": memory,
    }
