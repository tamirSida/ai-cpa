"""Live OpenAI smokes — exercise the real prompt + Responses structured-output contract
that StubCommandParser bypasses in the main suite."""

import os

import pytest

import app.schemas.ai_commands as ac


def test_parse_hebrew_receipt_command(parser):
    res, usage, model = parser.parse_user_command(
        {
            "business": {"current_year": 2026},
            "known_clients": ["נועה"],
            "current_year_summary": {},
            "pending_action": None,
            "recent_messages": [],
        },
        "קיבלתי 2800 מנועה על עיצוב לוגו בביט",
    )
    assert isinstance(res, ac.ParsedUserCommand), getattr(res, "detail", res)
    assert usage is not None and isinstance(model, str)
    assert res.intent == ac.IntentType.CREATE_RECEIPT
    assert res.receipt is not None
    assert res.receipt.amount == 2800
    assert res.receipt.client_name and "נועה" in res.receipt.client_name
    assert res.receipt.payment_method == ac.PaymentMethod.BIT


def test_extract_expense_from_real_receipt_image(parser):
    # Vision quality depends on a real receipt image, so this is opt-in: point
    # LIVE_RECEIPT_IMAGE_URL at a publicly fetchable receipt photo to run it.
    url = os.getenv("LIVE_RECEIPT_IMAGE_URL")
    if not url:
        pytest.skip("set LIVE_RECEIPT_IMAGE_URL to a real receipt image URL to run the vision smoke")
    res, usage, model = parser.extract_expense(url)
    assert isinstance(res, ac.ExpenseExtraction), getattr(res, "detail", res)
    assert usage is not None and isinstance(model, str)
    assert res.amount is not None and res.amount > 0
    assert res.currency in (None, "ILS")
