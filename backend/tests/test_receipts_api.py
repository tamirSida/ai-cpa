# backend/tests/test_receipts_api.py
def test_full_draft_issue_cancel_flow(api, db, make_business, stub_receipt_assets):
    biz = make_business()
    base = f"/api/businesses/{biz['id']}/receipts"
    r = api.post(f"{base}/draft", json={"clientName": "נועה", "amount": 2800, "description": "עיצוב לוגו", "paymentMethod": "bit"})
    assert r.status_code == 201 and r.json()["status"] == "draft"
    rid = r.json()["id"]
    issued = api.post(f"{base}/{rid}/issue")
    assert issued.status_code == 200
    assert issued.json()["receiptNumber"] == "2026-0001" and issued.json()["pdfUrl"]
    assert api.get(f"{base}?status=issued").json()[0]["id"] == rid
    assert api.get(f"{base}/{rid}").json()["clientSnapshot"]["name"] == "נועה"
    cancelled = api.post(f"{base}/{rid}/cancel", json={"reason": "סכום שגוי"})
    assert cancelled.json()["status"] == "cancelled" and cancelled.json()["cancellationReason"] == "סכום שגוי"

def test_issue_unknown_receipt_404_and_bad_draft_422(api, db, make_business):
    biz = make_business()
    base = f"/api/businesses/{biz['id']}/receipts"
    assert api.post(f"{base}/nope/issue").status_code == 404
    bad = api.post(f"{base}/draft", json={"clientName": "נועה", "amount": -1, "description": "x"})
    assert bad.status_code == 422 and bad.json()["detail"]["code"] == "invalid_amount"

def test_year_filter(api, db, make_business, stub_receipt_assets):
    biz = make_business()
    base = f"/api/businesses/{biz['id']}/receipts"
    rid = api.post(f"{base}/draft", json={"clientName": "נ", "amount": 1, "description": "x", "issueDate": "2025-12-31"}).json()["id"]
    api.post(f"{base}/{rid}/issue")
    assert len(api.get(f"{base}?year=2025").json()) == 1 and api.get(f"{base}?year=2026").json() == []
