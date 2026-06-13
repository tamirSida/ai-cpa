"""Live integration smoke tests — run against REAL services (OpenAI, Cloudinary, real
Firestore + Firebase Auth), not the emulator/stubs the main suite uses.

Gating (two layers, so the default suite stays hermetic and CI stays offline):
  1. Master switch: every test skips unless RUN_LIVE_SMOKE=1 is set.
  2. Per-service: each fixture skips if its credential is missing.

Credentials are read from the gitignored backend/.env (via app settings) and
backend/secrets/firebase-sa.json — nothing is hardcoded here.

Run them:  RUN_LIVE_SMOKE=1 .venv/bin/python -m pytest tests/live -v   (from backend/)
"""

import os

import pytest
from google.cloud import firestore

_HERE = os.path.dirname(os.path.abspath(__file__))
SA_PATH = os.path.abspath(os.path.join(_HERE, "..", "..", "secrets", "firebase-sa.json"))


def _truthy(v: str) -> bool:
    return str(v).lower() in ("1", "true", "yes", "on")


def _settings():
    from app.core.config import get_settings
    return get_settings()


# ---------------------------------------------------------------------------
# Override the parent conftest's emulator-only autouse fixtures so the live
# suite is self-contained and never requires (or wipes) the Firestore emulator.
# A same-named fixture in this conftest shadows the parent's for tests/live/*.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def clear_db():  # shadows parent: no emulator wipe, no emulator requirement
    yield


@pytest.fixture(autouse=True, scope="session")
def _patch_firebase_db():  # shadows parent: don't point firebase.get_db() at the emulator
    yield


@pytest.fixture(scope="session")
def db():  # shadows parent: live tests build their own real clients
    pytest.skip("live suite uses real clients, not the emulator 'db' fixture")


# ---------------------------------------------------------------------------
# Master opt-in gate.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _require_live_optin():
    if not _truthy(os.getenv("RUN_LIVE_SMOKE", "")):
        pytest.skip("live smoke: set RUN_LIVE_SMOKE=1 to run (hits real OpenAI/Cloudinary/Firestore)")


# ---------------------------------------------------------------------------
# Per-service fixtures — each skips cleanly when its credential is absent.
# ---------------------------------------------------------------------------
@pytest.fixture
def parser():
    if not _settings().openai_api_key:
        pytest.skip("OPENAI_API_KEY not configured")
    from app.services.openai_service import OpenAICommandParser
    return OpenAICommandParser()


@pytest.fixture
def cloudinary_cfg():
    if not _settings().cloudinary_url:
        pytest.skip("CLOUDINARY_URL not configured")
    return True


@pytest.fixture
def real_project():
    pid = _settings().firebase_project_id
    if not pid or pid.startswith("demo-"):
        pytest.skip("FIREBASE_PROJECT_ID is not a real (non-demo) project")
    if not os.path.isfile(SA_PATH):
        pytest.skip(f"service-account JSON not found at {SA_PATH}")
    return pid


@pytest.fixture
def live_db(real_project, monkeypatch):
    # Defend against a FIRESTORE_EMULATOR_HOST exported in the shell — we want REAL Firestore.
    monkeypatch.delenv("FIRESTORE_EMULATOR_HOST", raising=False)
    return firestore.Client.from_service_account_json(SA_PATH, project=real_project)


@pytest.fixture
def firebase_live_app(real_project):
    import firebase_admin
    from firebase_admin import credentials
    name = "live-smoke"  # named app so we never clobber the default app the main API uses
    try:
        return firebase_admin.get_app(name)
    except ValueError:
        return firebase_admin.initialize_app(
            credentials.Certificate(SA_PATH), {"projectId": real_project}, name=name
        )


@pytest.fixture
def web_api_key():
    # Public Firebase web API key (not a secret) — read from frontend/.env.local or env override.
    path = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "frontend", ".env.local"))
    key = ""
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("NEXT_PUBLIC_FIREBASE_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    break
    key = key or os.getenv("FIREBASE_WEB_API_KEY", "")
    if not key:
        pytest.skip("no Firebase web API key (frontend/.env.local or FIREBASE_WEB_API_KEY)")
    return key
