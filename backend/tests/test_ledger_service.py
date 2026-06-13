from google.cloud import firestore

from app.services.ledger_service import record_event


def test_record_event_with_client(db, make_business):
    biz = make_business()
    event_id = record_event(
        db, biz["id"], type="receipt_issued", entity_type="receipt",
        entity_id="r1", amount=2800.456, metadata={"receiptNumber": "2026-0001"},
    )
    raw = (db.collection("businesses").document(biz["id"])
           .collection("ledgerEvents").document(event_id).get().to_dict())
    assert raw["type"] == "receipt_issued" and raw["entityType"] == "receipt"
    assert raw["amount"] == 2800.46 and raw["currency"] == "ILS"
    assert raw["metadata"] == {"receiptNumber": "2026-0001"}
    assert raw["businessId"] == biz["id"] and "createdAt" in raw


def test_record_event_inside_transaction(db, make_business):
    biz = make_business()
    tx = db.transaction()

    @firestore.transactional
    def run(tx):
        return record_event(tx, biz["id"], type="expense_created", entity_type="expense", entity_id="e1")

    event_id = run(tx)
    snap = (db.collection("businesses").document(biz["id"])
            .collection("ledgerEvents").document(event_id).get())
    assert snap.exists and "amount" not in snap.to_dict()
