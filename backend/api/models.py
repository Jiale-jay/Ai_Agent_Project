from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str = Field(default="default")


class MemoryStoreRequest(BaseModel):
    content: str
    tags: list[str] = []
