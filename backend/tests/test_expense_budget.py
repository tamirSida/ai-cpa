"""Receipt-OCR (vision /extract) AI dollar-budget hard block + cost recording.

Mirrors the chat-path budget tests. Uses the HTTP layer (api fixture) so the
router's user dependency wiring is exercised end-to-end. The plain photo
/upload endpoint is FREE and must NEVER be metered.
"""
from app.schemas.ai_commands import ExpenseExtraction
from app.schemas.expense import ExpenseCreate
from app.services import cloudinary_service, expense_service
from app.services.openai_service import ParserFailure

VALID_EXTRACTION = ExpenseExtraction(
    supplier_name="Canva", amount=120.0, currency="ILS", category="software",
    description="מנוי חודשי", expense_date="2026-05-03",
    ocr_text="Canva Pro 120.00 ILS", confidence=0.92)

FAKE_JPG = b"\xff\xd8\xff" + b"0" * 64


def _usage_micro(db) -> int:
    snap = db.collection("users").document("test-uid").collection("usage").document("2026-06").get()
    return int(snap.to_dict().get("aiCostMicroUsd") or 0) if snap.exists else 0


def _usage_exists(db) -> bool:
    return db.collection("users").document("test-uid").collection("usage").document("2026-06").get().exists


def _seed_over_budget(db, _seed):
    """Re-seed test-uid with a tiny cap and an already-over-cap usage bucket."""
    _seed(db, uid="test-uid", email="owner@example.com", displayName="Owner",
          role="user", status="active", aiBudgetUsd=0.000001)
    db.collection("users").document("test-uid").collection("usage").document("2026-06") \
      .set({"month": "2026-06", "aiCostMicroUsd": 10})


def _image_expense(db, biz_id):
    """An image-source expense in needs_review with a cloudinaryPublicId."""
    return expense_service.create_expense(db, biz_id, ExpenseCreate(
        image_url="https://res.cloudinary.com/demo/image/upload/expenses/abc.jpg",
        cloudinary_public_id="expenses/abc"), source="image")


def test_over_budget_hard_blocks_and_skips_vision(api, db, stub_parser, freeze_month, make_business):
    from tests.conftest import _seed_user
    _seed_over_budget(db, _seed_user)
    biz = make_business()
    exp = _image_expense(db, biz["id"])
    stub_parser.extract_result = VALID_EXTRACTION  # would be returned only if vision were called

    resp = api.post(f"/api/businesses/{biz['id']}/expenses/{exp.id}/extract")

    assert resp.status_code == 429
    assert resp.json()["detail"]["code"] == "ai_budget_exceeded"
    assert stub_parser.last_image_url is None  # vision was NOT called


def test_under_budget_records_cost(api, db, stub_parser, freeze_month, make_business, monkeypatch):
    # Default seed: Unlimited budget.
    biz = make_business()
    exp = _image_expense(db, biz["id"])
    monkeypatch.setattr(expense_service, "build_jpg_delivery_url", lambda pid: "https://x/f_jpg/y")
    stub_parser.extract_result = VALID_EXTRACTION

    resp = api.post(f"/api/businesses/{biz['id']}/expenses/{exp.id}/extract")

    assert resp.status_code == 200
    assert _usage_micro(db) > 0  # FakeUsage(100,50) cost recorded


def test_upload_is_not_metered(api, db, stub_parser, freeze_month, make_business, monkeypatch):
    # Even with an exhausted budget, the plain photo upload must succeed and never touch usage.
    from tests.conftest import _seed_user
    _seed_over_budget(db, _seed_user)
    biz = make_business()
    monkeypatch.setattr(cloudinary_service, "upload_image", lambda data, folder: cloudinary_service.UploadResult(
        secure_url="https://res.cloudinary.com/demo/image/upload/expenses/abc.jpg", public_id="expenses/abc"))

    resp = api.post(f"/api/businesses/{biz['id']}/expenses/upload",
                    files={"file": ("r.jpg", FAKE_JPG, "image/jpeg")})

    assert resp.status_code == 201
    # upload pre-set the bucket to 10 (via _seed_over_budget), but must not increment it
    assert _usage_micro(db) == 10
    assert stub_parser.last_image_url is None  # upload never calls vision


def test_parser_failure_not_charged(api, db, stub_parser, freeze_month, make_business, monkeypatch):
    # Comfortable/Unlimited budget so assert_budget passes; the 502 must NOT be charged.
    biz = make_business()
    exp = _image_expense(db, biz["id"])
    monkeypatch.setattr(expense_service, "build_jpg_delivery_url", lambda pid: "https://x/f_jpg/y")
    stub_parser.usage = None
    stub_parser.extract_result = ParserFailure(reason="timeout")

    resp = api.post(f"/api/businesses/{biz['id']}/expenses/{exp.id}/extract")

    assert resp.status_code == 502
    assert resp.json()["detail"]["code"] == "extraction_failed"
    assert not _usage_exists(db)  # ParserFailure -> no cost recorded, bucket never created
