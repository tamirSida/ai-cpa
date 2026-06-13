from enum import Enum
from app.schemas.ai_commands import IntentType

def merge_payload(existing: dict, incoming: dict, intent: IntentType) -> dict:
    merged = dict(existing)
    for key, value in incoming.items():
        if value is None: continue                     # not provided -> keep existing
        if isinstance(value, Enum): value = value.value
        if key == "payment_method" and value == "unknown": continue  # unknown enum = not provided
        merged[key] = value                            # provided value always wins (user corrections)
    return merged

def compute_missing_fields(intent: IntentType, payload: dict) -> list[str]:
    missing: list[str] = []                            # doc §15, NEVER taken from the LLM
    if intent == IntentType.CREATE_RECEIPT:
        if not payload.get("client_name"): missing.append("client_name")
        amount = payload.get("amount")
        if not isinstance(amount, (int, float)) or isinstance(amount, bool) or amount <= 0:
            missing.append("amount")
        if not payload.get("description"): missing.append("description")
        # `is not True` is deliberate identity, not falsiness: 1/"yes" must NOT satisfy the
        # payment confirmation; only an explicit boolean True (received) or issue_receipt request does.
        if payload.get("payment_received") is not True and payload.get("issue_receipt") is not True:
            missing.append("payment_received_confirmation")  # doc §10 rule
    elif intent == IntentType.CREATE_CONTACT:
        if not payload.get("name"): missing.append("name")
    elif intent == IntentType.CREATE_EXPENSE:
        amount = payload.get("amount")
        if not isinstance(amount, (int, float)) or isinstance(amount, bool) or amount <= 0:
            missing.append("amount")
    return missing
