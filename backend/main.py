from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.chat import router as chat_router
from api.routes.history import router as history_router
from api.routes.memory import router as memory_router

app = FastAPI(title="AI Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(history_router, prefix="/history", tags=["history"])
app.include_router(memory_router, prefix="/memory", tags=["memory"])


@app.get("/health")
async def health():
    return {"status": "ok"}
