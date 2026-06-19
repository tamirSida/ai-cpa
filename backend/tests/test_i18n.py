# backend/tests/test_i18n.py
import pytest

from app.core.i18n import tr
from app.core.lang import get_lang
from app.services.cloudinary_service import UploadResult
from tests.integration.test_chat_flow import FULL_RECEIPT


@pytest.fixture(autouse=True)
def fake_pdf_and_cloudinary(monkeypatch):
    monkeypatch.setattr("app.services.pdf_service.render_pdf", lambda template_name, context: b"%PDF-1.4 fake")
    monkeypatch.setattr("app.services.cloudinary_service.upload_pdf",
        lambda data, public_id: UploadResult(secure_url=f"https://res.test/{public_id}", public_id=public_id))


def test_tr_en_differs_from_he_and_is_english():
    he = tr("he", "chat.cancelled")
    en = tr("en", "chat.cancelled")
    assert he == "הפעולה בוטלה."
    assert en != he
    assert en == "Action cancelled."
    # ASCII-only => a real English translation, not the Hebrew literal
    assert en.isascii()


def test_tr_falls_back_to_hebrew_for_unknown_lang():
    assert tr("fr", "chat.cancelled") == tr("he", "chat.cancelled")


def test_get_lang_resolution():
    assert get_lang(None) == "he"          # header absent -> default he
    assert get_lang("he") == "he"
    assert get_lang("en") == "en"
    assert get_lang("EN-US") == "en"       # case-insensitive, prefix match
    assert get_lang("en-GB,en;q=0.9") == "en"
    assert get_lang("fr") == "he"          # unknown -> he


def _create_pending_action(api, biz_id):
    resp = api.post(
        f"/api/businesses/{biz_id}/chat/message",
        json={"text": "קיבלתי 2800 מנועה על עיצוב לוגו בביט"},
    )
    assert resp.status_code == 200
    return resp.json()["action"]["id"]


def _last_assistant_text(db, biz_id):
    msgs = (db.collection("businesses").document(biz_id).collection("chatThreads")
            .document("main").collection("messages").order_by("createdAt").stream())
    return [m.to_dict() for m in msgs if m.to_dict()["role"] == "assistant"][-1]["text"]


def test_cancel_endpoint_english_header_returns_english_reply(api, stub_parser, make_business, db):
    stub_parser.queue_command(FULL_RECEIPT)
    biz_id = make_business()["id"]
    action_id = _create_pending_action(api, biz_id)

    resp = api.post(f"/api/businesses/{biz_id}/chat/actions/{action_id}/cancel",
                    headers={"Accept-Language": "en"})
    assert resp.status_code == 200
    assert _last_assistant_text(db, biz_id) == "Action cancelled."


def test_cancel_endpoint_no_header_returns_hebrew_reply(api, stub_parser, make_business, db):
    stub_parser.queue_command(FULL_RECEIPT)
    biz_id = make_business()["id"]
    action_id = _create_pending_action(api, biz_id)

    resp = api.post(f"/api/businesses/{biz_id}/chat/actions/{action_id}/cancel")
    assert resp.status_code == 200
    assert _last_assistant_text(db, biz_id) == "הפעולה בוטלה."
