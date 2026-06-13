from google.cloud import firestore

from app.utils.dates import now_il
from app.utils.money import round_ils


def record_event(
    db_or_tx,
    business_id: str,
    type: str,
    entity_type: str,
    entity_id: str,
    amount: float | None = None,
    metadata: dict | None = None,
) -> str:
    """Append a LedgerEvent (doc §5.5). Accepts a Client (standalone write) or a
    Transaction (joins the caller's atomic batch, e.g. receipt issuing in Phase 2)."""
    if isinstance(db_or_tx, firestore.Transaction):
        client, tx = db_or_tx._client, db_or_tx
    else:
        client, tx = db_or_tx, None
    ref = (client.collection("businesses").document(business_id)
           .collection("ledgerEvents").document())
    data: dict = {
        "businessId": business_id,
        "type": type,
        "entityType": entity_type,
        "entityId": entity_id,
        "createdAt": now_il(),
    }
    if amount is not None:
        data["amount"] = round_ils(amount)
        data["currency"] = "ILS"
    if metadata:
        data["metadata"] = metadata
    if tx is not None:
        tx.set(ref, data)
    else:
        ref.set(data)
    return ref.id
