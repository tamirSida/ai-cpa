from app.core.errors import api_error
from app.schemas.client import Client, ClientCreate, ClientPatch
from app.utils.dates import now_il


def _col(db, business_id: str):
    return db.collection("businesses").document(business_id).collection("clients")


def create_client(db, business_id: str, payload: ClientCreate) -> Client:
    ref = _col(db, business_id).document()
    now = now_il()
    data = payload.model_dump(by_alias=True, exclude_none=True)
    data.update(id=ref.id, businessId=business_id, nameLower=payload.name.strip().lower(),
                createdAt=now, updatedAt=now)
    ref.set(data)
    return Client.model_validate(data)


def list_clients(db, business_id: str) -> list[Client]:
    return [Client.model_validate(d.to_dict()) for d in _col(db, business_id).order_by("nameLower").stream()]


def get_client(db, business_id: str, client_id: str) -> Client | None:
    snap = _col(db, business_id).document(client_id).get()
    return Client.model_validate(snap.to_dict()) if snap.exists else None


def update_client(db, business_id: str, client_id: str, patch: ClientPatch) -> Client:
    ref = _col(db, business_id).document(client_id)
    if not ref.get().exists:
        api_error(404, "client_not_found", "לקוח לא נמצא")
    # exclude_none means {"phone": null} is ignored, not a field-clear; clearing
    # a field would need an explicit sentinel — out of MVP scope.
    data = patch.model_dump(by_alias=True, exclude_none=True)
    if "name" in data:
        data["nameLower"] = data["name"].strip().lower()
    data["updatedAt"] = now_il()
    ref.update(data)
    return Client.model_validate(ref.get().to_dict())


def find_clients_by_name(db, business_id: str, name: str) -> list[Client]:
    needle = name.strip().lower()  # client-side contains; fine at MVP scale (≤ hundreds of clients)
    return [c for c in list_clients(db, business_id) if needle in c.name.strip().lower()]
