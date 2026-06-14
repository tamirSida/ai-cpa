"""Pure unit test for the Firestore composite index file.

The emulator does NOT enforce composite indexes, so this asserts the shape of
``firestore.indexes.json`` directly (the only place the prod ordering contract
lives) plus that the admin routes are wired into the app.
"""

import json
from pathlib import Path

INDEX_FILE = Path(__file__).resolve().parents[2] / "firestore.indexes.json"

USERS_FIELDS = [
    {"fieldPath": "status", "order": "ASCENDING"},
    {"fieldPath": "createdAt", "order": "DESCENDING"},
]


def _load_indexes() -> list[dict]:
    assert INDEX_FILE.exists(), f"missing index file: {INDEX_FILE}"
    data = json.loads(INDEX_FILE.read_text())
    return data["indexes"]


def test_users_composite_index_present():
    indexes = _load_indexes()
    users_indexes = [i for i in indexes if i.get("collectionGroup") == "users"]
    assert len(users_indexes) == 1, "expected exactly one users composite index"
    idx = users_indexes[0]
    assert idx["queryScope"] == "COLLECTION"
    assert idx["fields"] == USERS_FIELDS


def test_preexisting_indexes_not_clobbered():
    indexes = _load_indexes()
    collection_groups = [i.get("collectionGroup") for i in indexes]
    assert "receipts" in collection_groups, "receipts indexes were clobbered"
    assert "expenses" in collection_groups, "expenses indexes were clobbered"


def test_app_exposes_admin_routes():
    from app.main import app

    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/api/users/me" in paths
    assert "/api/admin/users" in paths
    assert "/api/admin/invites" in paths
