import pytest

from api.models import AutomationRequest
from api.routes.automation import run_automation


@pytest.mark.asyncio
async def test_automation_returns_power_platform_friendly_shape():
    response = await run_automation(
        AutomationRequest(
            workflow_type="invoice_exception",
            input_text="Invoice 123 has a bank detail mismatch and should be reviewed.",
            requester="finance-demo",
        )
    )

    assert response.summary.startswith("Invoice 123")
    assert response.requires_human_review is True
    assert 0 <= response.confidence <= 1
    assert response.audit_notes[0] == "workflow_type=invoice_exception"
