import os

import firebase_admin
from firebase_admin import credentials
from google.cloud import firestore

from app.core.config import get_settings

_db: firestore.Client | None = None


def init_firebase() -> None:
    if firebase_admin._apps:
        return
    if os.environ.get("FIRESTORE_EMULATOR_HOST"):
        # Tests/emulator: no service account; project id from env (demo-* = offline).
        # Also force firebase-admin auth into emulator mode so verify_id_token never
        # tries to load ADC credentials (malformed tokens fail locally with ValueError/
        # InvalidIdTokenError before any network call).
        os.environ.setdefault("FIREBASE_AUTH_EMULATOR_HOST", "localhost:9099")
        firebase_admin.initialize_app(
            options={"projectId": os.environ.get("GOOGLE_CLOUD_PROJECT", "demo-tax-test")}
        )
        return
    settings = get_settings()
    cred = credentials.Certificate(settings.google_application_credentials)
    firebase_admin.initialize_app(cred, {"projectId": settings.firebase_project_id})


def get_db() -> firestore.Client:
    """Module-cached SYNC Firestore client. With FIRESTORE_EMULATOR_HOST set,
    google-cloud-firestore auto-applies AnonymousCredentials."""
    global _db
    if _db is None:
        if os.environ.get("FIRESTORE_EMULATOR_HOST"):
            _db = firestore.Client(project=os.environ.get("GOOGLE_CLOUD_PROJECT", "demo-tax-test"))
        else:
            settings = get_settings()
            _db = firestore.Client.from_service_account_json(
                settings.google_application_credentials, project=settings.firebase_project_id
            )
    return _db
