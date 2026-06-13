# backend/tests/integration/test_chat_check_execute.py
from app.schemas.business import Business
from app.services import chat_service, receipt_service

def test_executor_persists_check_details(db, make_business, stub_receipt_assets):
    # stub_receipt_assets stubs render_pdf + upload_pdf so the happy PDF path runs without
    # hitting real WeasyPrint/Cloudinary; without it issue_receipt would swallow a real
    # upload failure and never exercise the success path.
    business = Business.model_validate(make_business())
    action_ref = db.collection("businesses").document(business.id).collection("pendingActions").document()
    action_ref.set({"id": action_ref.id})
    payload = {"client_name": "נועה", "amount": 500.0, "description": "שיעור", "payment_method": "check",
               "check_number": "55", "check_bank": "דיסקונט", "check_branch": "125", "check_due_date": "2026-07-01"}
    msg, result = chat_service._execute_receipt(db, business, payload, action_ref)
    assert result["pdfUrl"]  # PDF actually attached (success path, not the swallowed-error path)
    r = receipt_service.get_receipt(db, business.id, result["receiptId"])
    assert r.check_details and r.check_details.number == "55" and r.check_details.due_date == "2026-07-01"
