from fastapi import APIRouter

from api.models import AutomationRequest, AutomationResponse

router = APIRouter()


_WORKFLOW_ACTIONS = {
    "client_email": "Draft a client-safe response and route complex or sensitive items to a human reviewer.",
    "invoice_exception": "Summarize the exception, check likely causes, and route to finance operations.",
    "it_request": "Classify the request, suggest first-line troubleshooting, and create an IT ticket.",
    "compliance_question": "Answer only from approved policy context and require review for regulated advice.",
}


@router.post("/run", response_model=AutomationResponse)
async def run_automation(request: AutomationRequest):
    """Power Automate / Power Apps friendly workflow endpoint.

    This deterministic response shape is intentionally easy for low-code tools to parse.
    A production version could call the Agent in direct/rag/agent mode before returning.
    """
    text = request.input_text.strip()
    summary = text[:220] + ("..." if len(text) > 220 else "")
    sensitive_terms = ["confidential", "gdpr", "personal data", "bank", "tax", "legal", "complaint"]
    requires_review = any(term in text.lower() for term in sensitive_terms)

    return AutomationResponse(
        summary=summary,
        recommended_action=_WORKFLOW_ACTIONS[request.workflow_type],
        confidence=0.72 if requires_review else 0.86,
        requires_human_review=requires_review,
        audit_notes=[
            f"workflow_type={request.workflow_type}",
            f"requester={request.requester}",
            "Designed as a Power Platform integration contract for demo and PoC use.",
        ],
    )
