import firebase_admin
from google.cloud import firestore

from app.core.config import get_settings

_db: firestore.Client | None = None


def init_firebase() -> None:
    """Idempotent firebase-admin init. Wired into app startup in Phase 1."""
    if not firebase_admin._apps:
        firebase_admin.initialize_app()


def get_db() -> firestore.Client:
    """Module-cached sync client. Honors FIRESTORE_EMULATOR_HOST automatically
    (google-cloud-firestore switches to AnonymousCredentials when it is set)."""
    global _db
    if _db is None:
        _db = firestore.Client(project=get_settings().firebase_project_id)
    return _db
