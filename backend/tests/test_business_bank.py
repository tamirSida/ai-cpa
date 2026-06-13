from app.schemas.business import BusinessCreate, BusinessUpdate
from app.services import business_service


def test_create_persists_bank_fields(db):
    biz = business_service.create_business(db, "uid-bank", BusinessCreate(
        business_name="עסק", owner_name="תמיר", business_id_number="300123456", address="ת״א",
        bank_name="דיסקונט", bank_branch="125", bank_account="118863403"))
    assert biz.bank_name == "דיסקונט" and biz.bank_branch == "125" and biz.bank_account == "118863403"


def test_update_can_change_bank_account(db):
    biz = business_service.create_business(db, "uid-bank2", BusinessCreate(
        business_name="עסק", owner_name="תמיר", business_id_number="300123456", address="ת״א"))
    out = business_service.update_business(db, biz.id, BusinessUpdate(bank_account="999"))
    assert out.bank_account == "999"
