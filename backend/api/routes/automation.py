import json

import anthropic
from fastapi import APIRouter

from api.models import AutomationRequest, AutomationResponse
from config import settings

router = APIRouter()

_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

_WORKFLOW_PROMPTS = {
    "client_email": (
        "You are an enterprise AI assistant handling client communications. "
        "Analyse the input and respond with a JSON object only (no markdown). "
        "Fields: summary (str), recommended_action (str), confidence (float 0-1), "
        "requires_human_review (bool), audit_notes (list[str])."
    ),
    "invoice_exception": (
        "You are an enterprise finance AI. Analyse this invoice exception. "
        "Respond with JSON only. "
        "Fields: summary (str), recommended_action (str), confidence (float 0-1), "
        "requires_human_review (bool), audit_notes (list[str])."
    ),
    "it_request": (
        "You are an IT service desk AI. Classify and triage this IT request. "
        "Respond with JSON only. "
        "Fields: summary (str), recommended_action (str), confidence (float 0-1), "
        "requires_human_review (bool), audit_notes (list[str])."
    ),
    "compliance_question": (
        "You are a compliance AI assistant. Answer only from known policy context. "
        "Flag anything requiring legal/human review. "
        "Respond with JSON only. "
        "Fields: summary (str), recommended_action (str), confidence (float 0-1), "
        "requires_human_review (bool), audit_notes (list[str])."
    ),
}

_FALLBACK_ACTIONS = {
    "client_email": "Route to client relationship manager for review.",
    "invoice_exception": "Escalate to finance operations team.",
    "it_request": "Assign to IT service desk for manual triage.",
    "compliance_question": "Refer to compliance officer for authoritative guidance.",
}


@router.post("/run", response_model=AutomationResponse)
async def run_automation(request: AutomationRequest):
    """LLM-powered workflow endpoint compatible with Power Automate / Power Apps.

    Returns structured JSON that low-code platforms can consume directly.
    Maps to Azure Logic Apps / Power Automate HTTP connector in production.
    """
    system_prompt = _WORKFLOW_PROMPTS[request.workflow_type]
    user_content = (
        f"Requester: {request.requester}\n"
        f"Input:\n{request.input_text}"
    )

    try:
        response = await _client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        raw = response.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        return AutomationResponse(
            summary=data.get("summary", request.input_text[:200]),
            recommended_action=data.get("recommended_action", _FALLBACK_ACTIONS[request.workflow_type]),
            confidence=float(data.get("confidence", 0.75)),
            requires_human_review=bool(data.get("requires_human_review", False)),
            audit_notes=data.get("audit_notes", []) + [
                f"workflow_type={request.workflow_type}",
                f"requester={request.requester}",
                "Powered by Claude Haiku — maps to Azure OpenAI GPT-4o in production.",
            ],
        )
    except Exception as exc:
        # Graceful degradation: return deterministic fallback if LLM fails
        sensitive_terms = ["confidential", "gdpr", "personal data", "bank", "tax", "legal", "complaint"]
        requires_review = any(term in request.input_text.lower() for term in sensitive_terms)
        return AutomationResponse(
            summary=request.input_text[:220] + ("..." if len(request.input_text) > 220 else ""),
            recommended_action=_FALLBACK_ACTIONS[request.workflow_type],
            confidence=0.5,
            requires_human_review=True,
            audit_notes=[
                f"workflow_type={request.workflow_type}",
                f"requester={request.requester}",
                f"LLM call failed — deterministic fallback used: {exc}",
            ],
        )
