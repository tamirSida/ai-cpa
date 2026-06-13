# backend/tests/test_report_generate.py
import io, zipfile
from tests.test_report_precheck import seed_expense, seed_receipt

def test_generate_zip_members_csv_metadata_and_ledger(api, db, make_business, monkeypatch):
    biz = make_business()
    db.collection("businesses").document(biz["id"]).collection("clients").document("c1").set(
        {"businessId": biz["id"], "name": "נועה"})
    seed_receipt(db, biz["id"])
    eid = seed_expense(db, biz["id"])
    fetched = []
    def fake_fetch(url, client):
        fetched.append(url); return b"%PDF-fake-bytes"
    monkeypatch.setattr("app.services.report_service.fetch_asset", fake_fetch)
    resp = api.post(f"/api/businesses/{biz['id']}/reports/annual/2026/generate")
    assert resp.status_code == 200 and resp.headers["content-type"] == "application/zip"
    assert 'filename="annual_report_2026.zip"' in resp.headers["content-disposition"]
    assert "filename*=UTF-8''" in resp.headers["content-disposition"]
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    assert {"income.csv", "expenses.csv", "clients.csv", "summary.pdf", "missing_items.pdf",
            "receipt_pdfs/2026-0001.pdf", f"expense_images/{eid}.jpg"} <= set(zf.namelist())
    income = zf.read("income.csv")
    assert income.startswith(b"\xef\xbb\xbf") and "נועה" in income.decode("utf-8-sig")
    assert len(fetched) == 2
    meta = db.collection("businesses").document(biz["id"]).collection("annualReports").document("2026").get()
    assert meta.exists and meta.to_dict()["totalIncome"] == 2800.0
    events = [e.to_dict() for e in db.collection("businesses").document(biz["id"])
              .collection("ledgerEvents").stream()]
    assert any(e["type"] == "annual_report_generated" for e in events)

def test_generate_tolerates_fetch_failure_into_missing_items(api, db, make_business, monkeypatch):
    biz = make_business()
    seed_receipt(db, biz["id"])
    def boom(url, client): raise RuntimeError("cloudinary down")
    monkeypatch.setattr("app.services.report_service.fetch_asset", boom)
    resp = api.post(f"/api/businesses/{biz['id']}/reports/annual/2026/generate")
    assert resp.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    assert "receipt_pdfs/2026-0001.pdf" not in zf.namelist() and "missing_items.pdf" in zf.namelist()
