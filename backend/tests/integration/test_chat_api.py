# backend/tests/integration/test_chat_api.py
import pytest
from app.schemas.business import Business
from app.services.cloudinary_service import UploadResult
from tests.integration.test_chat_flow import FULL_RECEIPT, PARTIAL_RECEIPT, FOLLOWUP_AMOUNT


@pytest.fixture(autouse=True)
def fake_pdf_and_cloudinary(monkeypatch):
    monkeypatch.setattr("app.services.pdf_service.render_pdf", lambda template_name, context: b"%PDF-1.4 fake")
    monkeypatch.setattr("app.services.cloudinary_service.upload_pdf",
        lambda data, public_id: UploadResult(secure_url=f"https://res.test/{public_id}", public_id=public_id))


def test_post_message_returns_turn_result(api, stub_parser, make_business):
    stub_parser.queue_command(FULL_RECEIPT)
    biz = make_business()
    biz_id = biz["id"]

    resp = api.post(
        f"/api/businesses/{biz_id}/chat/message",
        json={"text": "קיבלתי 2800 מנועה על עיצוב לוגו בביט"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["assistantText"].startswith("לאשר יצירת קבלה")
    assert data["action"]["status"] == "pending_confirmation"
    assert data["action"]["missingFields"] == []


def test_empty_message_422(api, stub_parser, make_business):
    biz = make_business()
    biz_id = biz["id"]

    resp = api.post(
        f"/api/businesses/{biz_id}/chat/message",
        json={"text": "   "},
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "empty_message"


def test_confirm_endpoint_executes(api, stub_parser, make_business):
    stub_parser.queue_command(FULL_RECEIPT)
    biz = make_business()
    biz_id = biz["id"]

    # create the pending action
    msg_resp = api.post(
        f"/api/businesses/{biz_id}/chat/message",
        json={"text": "קיבלתי 2800 מנועה על עיצוב לוגו בביט"},
    )
    assert msg_resp.status_code == 200
    action_id = msg_resp.json()["action"]["id"]

    # first confirm → 200, receipt number ends with "-0001"
    confirm_resp = api.post(f"/api/businesses/{biz_id}/chat/actions/{action_id}/confirm")
    assert confirm_resp.status_code == 200
    result = confirm_resp.json()["result"]
    assert result["receiptNumber"].endswith("-0001")

    # second identical confirm → 409 action_not_confirmable
    confirm_resp2 = api.post(f"/api/businesses/{biz_id}/chat/actions/{action_id}/confirm")
    assert confirm_resp2.status_code == 409
    assert confirm_resp2.json()["detail"]["code"] == "action_not_confirmable"


def test_cancel_endpoint(api, stub_parser, make_business, db):
    stub_parser.queue_command(FULL_RECEIPT)
    biz = make_business()
    biz_id = biz["id"]

    # create the pending action
    msg_resp = api.post(
        f"/api/businesses/{biz_id}/chat/message",
        json={"text": "קיבלתי 2800 מנועה על עיצוב לוגו בביט"},
    )
    assert msg_resp.status_code == 200
    action_id = msg_resp.json()["action"]["id"]

    # cancel it → 200 {"status": "cancelled"}
    cancel_resp = api.post(f"/api/businesses/{biz_id}/chat/actions/{action_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json() == {"status": "cancelled"}

    # Firestore pendingActions doc has cancellationReason == "user_cancelled"
    action_doc = (
        db.collection("businesses")
        .document(biz_id)
        .collection("pendingActions")
        .document(action_id)
        .get()
    )
    assert action_doc.exists
    assert action_doc.to_dict()["cancellationReason"] == "user_cancelled"

    # an assistant message "הפעולה בוטלה." exists in the thread
    msgs = list(
        db.collection("businesses")
        .document(biz_id)
        .collection("chatThreads")
        .document("main")
        .collection("messages")
        .stream()
    )
    texts = [m.to_dict()["text"] for m in msgs]
    assert "הפעולה בוטלה." in texts


def test_get_messages_returns_history_and_active_action(api, stub_parser, make_business):
    stub_parser.queue_command(PARTIAL_RECEIPT).queue_command(FOLLOWUP_AMOUNT)
    biz = make_business()
    biz_id = biz["id"]

    # two-turn §14.2 flow
    api.post(
        f"/api/businesses/{biz_id}/chat/message",
        json={"text": "תוציא קבלה לנועה על עיצוב לוגו"},
    )
    api.post(
        f"/api/businesses/{biz_id}/chat/message",
        json={"text": "2800 בביט"},
    )

    # GET messages
    resp = api.get(f"/api/businesses/{biz_id}/chat/messages?threadId=main")
    assert resp.status_code == 200
    data = resp.json()
    messages = data["messages"]
    # 4 messages: user1, assistant1, user2, assistant2
    assert len(messages) == 4
    # oldest-first: first message is the user's first message
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"
    assert messages[3]["role"] == "assistant"
    # active action should be pending_confirmation after the two-turn merge
    assert data["activeAction"]["status"] == "pending_confirmation"


def test_confirm_unknown_action_404(api, make_business):
    biz = make_business()
    biz_id = biz["id"]

    resp = api.post(f"/api/businesses/{biz_id}/chat/actions/nonexistent-action-id-xyz/confirm")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "action_not_found"


def test_cancel_already_executed_action_409(api, make_business, stub_parser):
    from tests.integration.test_chat_flow import FULL_RECEIPT
    biz = make_business()
    stub_parser.queue_command(FULL_RECEIPT)
    base = f"/api/businesses/{biz['id']}/chat"
    action_id = api.post(f"{base}/message", json={"text": "קיבלתי 2800 מנועה על עיצוב לוגו בביט"}).json()["action"]["id"]
    assert api.post(f"{base}/actions/{action_id}/confirm").status_code == 200
    r = api.post(f"{base}/actions/{action_id}/cancel")  # already executed
    assert r.status_code == 409 and r.json()["detail"]["code"] == "action_not_cancellable"
