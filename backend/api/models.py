from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str = Field(default="default")
    mode: Literal["direct", "rag", "agent"] = Field(default="agent")


class MemoryStoreRequest(BaseModel):
    content: str
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    user_id: str = Field(default="demo-user")
    session_id: str = Field(default="default")


class MemoryUpdateRequest(BaseModel):
    content: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class AutomationRequest(BaseModel):
    workflow_type: Literal["client_email", "invoice_exception", "it_request", "compliance_question"] = "client_email"
    input_text: str = Field(..., min_length=1, max_length=5000)
    requester: str = Field(default="demo-user")


class AutomationResponse(BaseModel):
    summary: str
    recommended_action: str
    confidence: float
    requires_human_review: bool
    audit_notes: list[str]
