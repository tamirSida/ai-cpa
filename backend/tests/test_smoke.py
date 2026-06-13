def test_healthz(api):
    r = api.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_emulator_roundtrip(db, make_business):
    biz = make_business(businessName="חנות בדיקה")
    snap = db.collection("businesses").document(biz["id"]).get()
    assert snap.exists
    assert snap.get("businessName") == "חנות בדיקה"
    assert snap.get("ownerUserId") == "test-uid"


def test_clear_db_wipes_between_tests(db):
    # Runs after test_emulator_roundtrip; autouse clear_db must have wiped its writes.
    assert list(db.collection("businesses").limit(1).stream()) == []
