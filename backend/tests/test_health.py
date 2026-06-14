def test_healthz_is_ok(api):
    r = api.get("/healthz")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_readyz_reaches_firestore(api):
    # `api` runs against the emulator; readyz does a real (bounded) Firestore read.
    r = api.get("/readyz")
    assert r.status_code == 200 and r.json() == {"status": "ready"}
