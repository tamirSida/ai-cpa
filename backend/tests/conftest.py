import os
from datetime import datetime, timezone

import pytest
import requests
from fastapi.testclient import TestClient
from google.cloud import firestore

PROJECT_ID = "demo-tax-test"  # 'demo-' prefix = emulator-only, guaranteed offline


def _emulator_host() -> str:
    host = os.environ.get("FIRESTORE_EMULATOR_HOST")
    if not host:
        pytest.exit(
            "FIRESTORE_EMULATOR_HOST is not set. Start the emulator with "
            "'docker compose up -d firestore' and run: "
            "FIRESTORE_EMULATOR_HOST=localhost:8080 GOOGLE_CLOUD_PROJECT=demo-tax-test pytest",
            returncode=1,
        )
    return host


@pytest.fixture(scope="session")
def db() -> firestore.Client:
    _emulator_host()
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", PROJECT_ID)
    return firestore.Client(project=PROJECT_ID)


@pytest.fixture(autouse=True, scope="session")
def _patch_firebase_db(db):
    # Keep firebase.get_db()'s module cache pointing at the emulator client so any
    # future direct call (outside Depends) can never hit a real project during tests.
    import app.core.firebase as firebase_mod

    firebase_mod._db = db


@pytest.fixture(autouse=True)
def clear_db():
    host = _emulator_host()
    requests.delete(
        f"http://{host}/emulator/v1/projects/{PROJECT_ID}/databases/(default)/documents",
        timeout=10,
    ).raise_for_status()
    yield


@pytest.fixture()
def api(db):
    from app.core import auth, firebase
    from app.main import app

    saved = dict(app.dependency_overrides)
    app.dependency_overrides[auth.get_current_uid] = lambda: "test-uid"
    app.dependency_overrides[firebase.get_db] = lambda: db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)


@pytest.fixture()
def make_business(db):
    def _make(**overrides) -> dict:
        now = datetime.now(timezone.utc)
        doc = {
            "ownerUserId": "test-uid",
            "businessName": "עסק בדיקה",
            "ownerName": "ישראל ישראלי",
            "businessIdNumber": "123456789",
            "businessType": "osek_patur",
            "address": "תל אביב",
            "phone": "0501234567",
            "email": "owner@example.com",
            "receiptPrefix": "2026",
            "nextReceiptNumber": 1,
            # explicit per-business override — tests assert against this 120000, exercising
            # the business.annualLimit-overrides-config path (config default is 122833 for 2026)
            "annualLimit": 120000,
            "createdAt": now,
            "updatedAt": now,
        }
        doc.update(overrides)
        ref = db.collection("businesses").document()
        doc["id"] = ref.id
        ref.set(doc)
        return doc

    return _make
