from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from app.core.errors import api_error
from app.schemas.business import Business, BusinessCreate, BusinessUpdate
from app.utils.dates import now_il

MUTABLE_FIELDS = {"businessName", "ownerName", "address", "phone", "email", "receiptPrefix"}


def get_business_by_owner(db: firestore.Client, uid: str) -> Business | None:
    # Single-field equality query: no composite index required.
    docs = list(
        db.collection("businesses").where(filter=FieldFilter("ownerUserId", "==", uid)).limit(1).stream()
    )
    if not docs:
        return None
    return Business.model_validate({**docs[0].to_dict(), "id": docs[0].id})


def create_business(db: firestore.Client, uid: str, payload: BusinessCreate) -> Business:
    # Check-then-create is not transactional; acceptable for MVP (single human
    # clicking one onboarding form — no concurrent-create vector).
    if get_business_by_owner(db, uid) is not None:
        api_error(409, "business_exists", "User already has a business")
    now = now_il()
    data = {
        "ownerUserId": uid,
        "businessName": payload.business_name,
        "ownerName": payload.owner_name,
        "businessIdNumber": payload.business_id_number,
        "businessType": "osek_patur",
        "address": payload.address,
        "phone": payload.phone,
        "email": payload.email,
        "receiptPrefix": payload.receipt_prefix or str(now.year),
        "nextReceiptNumber": 1,
        "createdAt": now,
        "updatedAt": now,
    }
    data = {k: v for k, v in data.items() if v is not None}
    ref = db.collection("businesses").document()
    ref.set(data)
    return Business.model_validate({**data, "id": ref.id})


def update_business(db: firestore.Client, business_id: str, patch: BusinessUpdate) -> Business:
    updates = {
        k: v for k, v in patch.model_dump(by_alias=True, exclude_none=True).items()
        if k in MUTABLE_FIELDS
    }
    if not updates:
        api_error(400, "no_updatable_fields", "No mutable fields provided")
    updates["updatedAt"] = now_il()
    ref = db.collection("businesses").document(business_id)
    if not ref.get().exists:
        api_error(404, "business_not_found", "Business not found")
    ref.update(updates)
    snap = ref.get()
    return Business.model_validate({**snap.to_dict(), "id": snap.id})
