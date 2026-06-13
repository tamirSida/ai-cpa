import pytest
from fastapi import HTTPException

from app.schemas.business import BusinessCreate, BusinessUpdate
from app.services import business_service
from app.utils.dates import now_il

PAYLOAD = BusinessCreate(
    business_name="עיצובים של נועה", owner_name="נועה לוי",
    business_id_number="123456789", address="הרצל 1, תל אביב", phone="050-1234567",
)


def test_create_business_defaults_and_camelcase_persistence(db):
    biz = business_service.create_business(db, "test-uid", PAYLOAD)
    assert biz.owner_user_id == "test-uid"
    assert biz.business_type == "osek_patur"
    assert biz.next_receipt_number == 1
    assert biz.receipt_prefix == str(now_il().year)
    raw = db.collection("businesses").document(biz.id).get().to_dict()
    assert raw["ownerUserId"] == "test-uid" and raw["nextReceiptNumber"] == 1
    assert "email" not in raw  # None optionals are not persisted


def test_second_business_409(db):
    business_service.create_business(db, "test-uid", PAYLOAD)
    with pytest.raises(HTTPException) as exc:
        business_service.create_business(db, "test-uid", PAYLOAD)
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "business_exists"


def test_get_business_by_owner_none(db):
    assert business_service.get_business_by_owner(db, "nobody") is None


def test_update_business_mutable_fields_only(db):
    biz = business_service.create_business(db, "test-uid", PAYLOAD)
    updated = business_service.update_business(
        db, biz.id, BusinessUpdate(business_name="סטודיו נועה", receipt_prefix="2027")
    )
    assert updated.business_name == "סטודיו נועה"
    assert updated.receipt_prefix == "2027"
    assert updated.next_receipt_number == 1  # untouched


def test_update_nonexistent_business_404(db):
    with pytest.raises(HTTPException) as exc:
        business_service.update_business(db, "does-not-exist", BusinessUpdate(business_name="X"))
    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "business_not_found"
