# backend/tests/test_expense_upload_extract.py
from app.schemas.ai_commands import ExpenseExtraction
from app.schemas.expense import ExpenseCreate
from app.services import cloudinary_service, expense_service
from app.services.openai_service import ParserFailure

FAKE_JPG = b"\xff\xd8\xff" + b"0" * 64

def _fake_upload(monkeypatch):
    monkeypatch.setattr(cloudinary_service, "upload_image", lambda data, folder: cloudinary_service.UploadResult(
        secure_url="https://res.cloudinary.com/demo/image/upload/expenses/abc.jpg", public_id="expenses/abc"))

def test_upload_creates_needs_review_with_image_refs(api, db, make_business, monkeypatch):
    biz = make_business(); _fake_upload(monkeypatch)
    r = api.post(f"/api/businesses/{biz['id']}/expenses/upload",
                 files={"file": ("r.jpg", FAKE_JPG, "image/jpeg")})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "needs_review" and body["cloudinaryPublicId"] == "expenses/abc"
    assert body["imageUrl"].endswith("expenses/abc.jpg") and body["amount"] is None

def test_upload_bad_content_type_400(api, db, make_business):
    biz = make_business()
    r = api.post(f"/api/businesses/{biz['id']}/expenses/upload",
                 files={"file": ("r.pdf", b"%PDF", "application/pdf")})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "unsupported_file_type"

def test_upload_oversize_413(api, db, make_business):
    biz = make_business()
    r = api.post(f"/api/businesses/{biz['id']}/expenses/upload",
                 files={"file": ("r.png", b"0" * (10 * 1024 * 1024 + 1), "image/png")})
    assert r.status_code == 413 and r.json()["detail"]["code"] == "file_too_large"

def _image_expense(db, biz_id):
    return expense_service.create_expense(db, biz_id, ExpenseCreate(
        image_url="https://res.cloudinary.com/demo/image/upload/expenses/abc.jpg",
        cloudinary_public_id="expenses/abc"), source="image")

def test_extract_merges_fields_via_fjpg_url(api, db, make_business, stub_parser, monkeypatch):
    biz = make_business(); exp = _image_expense(db, biz["id"])
    monkeypatch.setattr(expense_service, "build_jpg_delivery_url",
                        lambda pid: f"https://res.cloudinary.com/demo/image/upload/f_jpg/{pid}")
    stub_parser.extract_result = ExpenseExtraction(
        supplier_name="Canva", amount=120.0, currency="ILS", category="software",
        description="מנוי חודשי", expense_date="2026-05-03", ocr_text="Canva Pro 120.00 ILS", confidence=0.92)
    r = api.post(f"/api/businesses/{biz['id']}/expenses/{exp.id}/extract")
    assert r.status_code == 200
    assert stub_parser.last_image_url == "https://res.cloudinary.com/demo/image/upload/f_jpg/expenses/abc"
    body = r.json()
    assert body["supplierName"] == "Canva" and body["amount"] == 120.0 and body["category"] == "software"
    assert body["ocrText"].startswith("Canva") and body["extractionConfidence"] == 0.92
    assert body["status"] == "needs_review"   # extraction NEVER auto-approves

def test_extract_invalid_llm_category_dropped(api, db, make_business, stub_parser, monkeypatch):
    biz = make_business(); exp = _image_expense(db, biz["id"])
    monkeypatch.setattr(expense_service, "build_jpg_delivery_url", lambda pid: "https://x/f_jpg/y")
    # category="hardware" is out of ExpenseCategory's strict enum; model_construct bypasses validation
    # to simulate an out-of-vocabulary LLM value reaching the service, where it must be DROPPED.
    stub_parser.extract_result = ExpenseExtraction.model_construct(supplier_name="KSP", amount=350.0, currency="ILS",
        category="hardware", description=None, expense_date=None, ocr_text=None, confidence=0.5)
    r = api.post(f"/api/businesses/{biz['id']}/expenses/{exp.id}/extract")
    assert r.status_code == 200 and r.json()["category"] is None

def test_extract_parser_failure_502(api, db, make_business, stub_parser, monkeypatch):
    biz = make_business(); exp = _image_expense(db, biz["id"])
    monkeypatch.setattr(expense_service, "build_jpg_delivery_url", lambda pid: "https://x/f_jpg/y")
    stub_parser.extract_result = ParserFailure(reason="timeout")
    r = api.post(f"/api/businesses/{biz['id']}/expenses/{exp.id}/extract")
    assert r.status_code == 502 and r.json()["detail"]["code"] == "extraction_failed"

def test_extract_without_image_400(api, db, make_business, stub_parser):
    biz = make_business()
    exp = expense_service.create_expense(db, biz["id"], ExpenseCreate(amount=10.0), source="manual")
    r = api.post(f"/api/businesses/{biz['id']}/expenses/{exp.id}/extract")
    assert r.status_code == 400 and r.json()["detail"]["code"] == "no_image"
