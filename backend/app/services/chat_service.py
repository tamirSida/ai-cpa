import uuid
from enum import Enum
from datetime import timedelta
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from app.schemas.ai_commands import (IntentType, ParsedUserCommand, ParserFailure, QueryPayload,
                                     QueryType, TimePreset, TimeRange)
from app.schemas.business import Business
from app.schemas.chat import ActionView, ChatTurnResult, ExecutionResult
from app.schemas.client import ClientCreate
from app.schemas.receipt import ReceiptDraftCreate
from app.services import aggregation_service as agg
from app.services import client_service, receipt_service, report_service
from app.utils.dates import now_il, resolve_time_range, today_il, year_bounds
from app.utils.hebrew import (CANCEL_WORDS, CONFIRM_WORDS, build_confirmation_message,
                              build_followup_question, normalize, render_precheck_summary,
                              render_query_answer)
from app.utils.money import round_ils
from app.core.errors import api_error

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
        if payload.get("payment_method") == "check":
            for f in ("check_number", "check_bank", "check_branch", "check_due_date"):
                if not payload.get(f):
                    missing.append(f)
    elif intent == IntentType.CREATE_CONTACT:
        if not payload.get("name"): missing.append("name")
    elif intent == IntentType.CREATE_EXPENSE:
        amount = payload.get("amount")
        if not isinstance(amount, (int, float)) or isinstance(amount, bool) or amount <= 0:
            missing.append("amount")
    return missing

FALLBACK = "לא הצלחתי להבין, אפשר לנסח שוב?"
ACTIVE_STATUSES = ("collecting_fields", "pending_confirmation")
STALE_AFTER = timedelta(hours=24)
CREATE_INTENTS = {IntentType.CREATE_RECEIPT, IntentType.CREATE_CONTACT,
                  IntentType.CREATE_EXPENSE, IntentType.GENERATE_ANNUAL_REPORT}

def _biz_ref(db, bid): return db.collection("businesses").document(bid)
def _actions_col(db, bid): return _biz_ref(db, bid).collection("pendingActions")
def _msgs_col(db, bid, tid): return _biz_ref(db, bid).collection("chatThreads").document(tid).collection("messages")

def save_message(db, business_id, thread_id, role, text, action_id=None, parsed_intent=None) -> str:
    _biz_ref(db, business_id).collection("chatThreads").document(thread_id).set({"updatedAt": now_il()}, merge=True)
    ref = _msgs_col(db, business_id, thread_id).document()
    ref.set({"businessId": business_id, "threadId": thread_id, "role": role, "text": text,
             "actionId": action_id, "parsedIntent": parsed_intent, "createdAt": now_il()})
    return ref.id

def _load_active_action(db, business_id, thread_id):
    q = _actions_col(db, business_id).where(filter=FieldFilter("threadId", "==", thread_id)) \
                                     .where(filter=FieldFilter("status", "in", list(ACTIVE_STATUSES)))
    now = now_il()
    fresh = []
    for doc in q.stream():
        data = doc.to_dict()
        # Missing updatedAt (malformed/manually-edited doc) is treated as stale, never a 500.
        updated_at = data.get("updatedAt")
        if updated_at is None or now - updated_at > STALE_AFTER:
            doc.reference.update({"status": "cancelled", "cancellationReason": "expired", "updatedAt": now})
            continue
        fresh.append((doc.id, data))
    if not fresh:
        return None
    # A thread is single-active by design. If a race (concurrent sends) left duplicates,
    # self-heal: keep the most-recently-updated, cancel the rest so state converges.
    fresh.sort(key=lambda pair: pair[1]["updatedAt"], reverse=True)
    for dup_id, _ in fresh[1:]:
        _actions_col(db, business_id).document(dup_id).update(
            {"status": "cancelled", "cancellationReason": "superseded", "updatedAt": now})
    return fresh[0]

def _action_view(action_id, data) -> ActionView:
    return ActionView(id=action_id, type=data["type"], status=data["status"],
                      payload=data["payload"], missing_fields=data["missingFields"])

def _current_question(data) -> str:
    intent = IntentType(data["type"])
    if data["status"] == "pending_confirmation":
        return build_confirmation_message(intent, data["payload"])
    return build_followup_question(intent, data["missingFields"])

def _build_context(db, business: Business, thread_id, text, active) -> dict:
    matched = client_service.find_clients_by_name(db, business.id, text)
    recent = client_service.list_clients(db, business.id)[:10]
    clients, seen = [], set()
    for c in matched + recent:
        if c.id not in seen:
            seen.add(c.id); clients.append({"id": c.id, "name": c.name})
    msgs = [d.to_dict() for d in _msgs_col(db, business.id, thread_id)
            .order_by("createdAt", direction="DESCENDING").limit(10).stream()][::-1]
    year = today_il().year
    return {"business": {"business_type": "osek_patur", "currency": "ILS", "current_year": year},
            "known_clients": clients[:20],
            # doc §8 step 2: current-year summary travels with every chat turn
            "current_year_summary": {"total_revenue": agg.total_revenue(db, business.id, *year_bounds(year)),
                                     "total_expenses": agg.total_expenses(db, business.id, *year_bounds(year))},
            "pending_action": ({"type": active[1]["type"], "missing_fields": active[1]["missingFields"],
                                "payload": active[1]["payload"]} if active else None),
            "recent_messages": [{"role": m["role"], "text": m["text"]} for m in msgs]}

def _payload_for(intent, cmd: ParsedUserCommand) -> dict:
    if intent == IntentType.CREATE_RECEIPT and cmd.receipt: return cmd.receipt.model_dump(mode="json")
    if intent == IntentType.CREATE_CONTACT and cmd.contact: return cmd.contact.model_dump(mode="json")
    if intent == IntentType.CREATE_EXPENSE and cmd.expense: return cmd.expense.model_dump(mode="json")
    if intent == IntentType.GENERATE_ANNUAL_REPORT: return {"year": today_il().year}
    return {}

def _upsert_action(db, business_id, thread_id, action_id, intent, status, payload, missing) -> str:
    if action_id is None:
        ref = _actions_col(db, business_id).document(uuid.uuid4().hex)
        ref.set({"businessId": business_id, "threadId": thread_id, "type": intent.value, "status": status,
                 "payload": payload, "missingFields": missing, "createdAt": now_il(), "updatedAt": now_il()})
        return ref.id
    _actions_col(db, business_id).document(action_id).update(
        {"status": status, "payload": payload, "missingFields": missing, "updatedAt": now_il()})
    return action_id

def _flip_to_confirmed(db, action_ref) -> dict:
    # Known limitation: a process crash between this confirmed-flip commit and executor
    # completion strands the action in "confirmed" — the stale-cleanup only sweeps
    # collecting_fields/pending_confirmation, so it won't recover it. Acceptable for the
    # single-user MVP; a future sweep could re-drive or revert stuck "confirmed" actions.
    # max_attempts widened: under contention the emulator's pessimistic lock can raise a transient
    # Aborted ("lock timeout") instead of letting the loser read the committed status. Retrying lets
    # the loser acquire the lock, see "confirmed", and return the deterministic 409 (HTTPException is
    # not Aborted, so it propagates without burning retries). Also helps real-Firestore contention.
    tx = db.transaction(max_attempts=25)
    @firestore.transactional
    def flip(transaction):
        snap = action_ref.get(transaction=transaction)
        if not snap.exists:
            api_error(404, "action_not_found", "הפעולה לא נמצאה")
        data = snap.to_dict()
        if data["status"] != "pending_confirmation":
            api_error(409, "action_not_confirmable", "הפעולה כבר טופלה או אינה ממתינה לאישור")
        transaction.update(action_ref, {"status": "confirmed", "updatedAt": now_il()})
        return data
    return flip(tx)

def _execute_receipt(db, business: Business, payload: dict, action_ref):
    existing_draft_id = payload.get("_draftId")
    if existing_draft_id:
        # retry after a prior issue failure: re-issue the SAME draft (issue_receipt is
        # idempotent on a draft -> issued, and repairs an issued-without-pdf receipt),
        # so a confirm-retry never mints a second receipt number.
        receipt = receipt_service.issue_receipt(db, business.id, existing_draft_id)
    else:
        name = payload["client_name"].strip()
        # create_draft builds the clientSnapshot itself: full client doc when client_id
        # resolves, name-only otherwise (Task 2.3) — ReceiptDraftCreate has no snapshot field
        exact = [c for c in client_service.find_clients_by_name(db, business.id, name) if c.name.strip() == name]
        client_id = exact[0].id if len(exact) == 1 else None
        draft = receipt_service.create_draft(db, business, ReceiptDraftCreate(
            client_id=client_id, client_name=name, amount=round_ils(payload["amount"]), currency="ILS",
            payment_method=payload.get("payment_method") or "unknown",
            description=payload["description"]))
        # persist the draft id BEFORE issuing, so a crash/throw during issue lets the retry
        # re-issue this same draft instead of creating a new one.
        action_ref.update({"payload._draftId": draft.id})
        payload["_draftId"] = draft.id
        receipt = receipt_service.issue_receipt(db, business.id, draft.id)
    return (f"נוצרה קבלה מספר {receipt.receipt_number}.",
            {"receiptId": receipt.id, "receiptNumber": receipt.receipt_number, "pdfUrl": receipt.pdf_url})

def _execute_contact(db, business, payload, action_ref):
    client = client_service.create_client(db, business.id, ClientCreate(
        name=payload["name"], phone=payload.get("phone"), email=payload.get("email"),
        company_name=payload.get("company_name"), tax_id=payload.get("tax_id"), address=payload.get("address")))
    return f"איש הקשר {client.name} נוסף בהצלחה.", {"clientId": client.id}

def _execute_expense(db, business, payload, action_ref):
    from app.services import expense_service          # Phase 4 module — imported lazily on purpose
    from app.schemas.expense import ExpenseCreate
    expense = expense_service.create_expense(db, business.id, ExpenseCreate(
        supplier_name=payload.get("supplier_name"), amount=round_ils(payload["amount"]),
        category=payload.get("category"), description=payload.get("description"),
        business_use_percent=payload.get("business_use_percent") or 100,
        expense_date=payload.get("expense_date")), source="chat")
    note = " היא ממתינה לבדיקה כי חסרה קטגוריה." if expense.status == "needs_review" else ""
    return f"ההוצאה נשמרה.{note}", {"expenseId": expense.id}

_EXECUTORS = {"CREATE_RECEIPT": _execute_receipt, "CREATE_CONTACT": _execute_contact,
              "CREATE_EXPENSE": _execute_expense,
              "GENERATE_ANNUAL_REPORT": lambda db, business, payload, action_ref:
                  (f"מעולה. אפשר להפיק את הדוח השנתי לשנת {payload['year']} בעמוד הדוח השנתי.",
                   {"year": payload["year"], "link": "/annual-report"})}

def confirm_action(db, parser_or_none, business: Business, action_id: str) -> ExecutionResult:
    action_ref = _actions_col(db, business.id).document(action_id)
    data = _flip_to_confirmed(db, action_ref)
    thread_id, payload = data["threadId"], data["payload"]
    try:
        reply, result = _EXECUTORS[data["type"]](db, business, payload, action_ref)
    except Exception as exc:                          # revert: user can confirm again
        action_ref.update({"status": "pending_confirmation", "errorNote": str(exc), "updatedAt": now_il()})
        reply = "אירעה שגיאה בביצוע הפעולה. אפשר לנסות לאשר שוב."
        save_message(db, business.id, thread_id, "assistant", reply, action_id=action_id)
        return ExecutionResult(assistant_text=reply, action=ActionView(
            id=action_id, type=data["type"], status="pending_confirmation", payload=payload, missing_fields=[]))
    action_ref.update({"status": "executed", "result": result, "updatedAt": now_il()})
    save_message(db, business.id, thread_id, "assistant", reply, action_id=action_id)
    return ExecutionResult(assistant_text=reply, action=ActionView(
        id=action_id, type=data["type"], status="executed", payload=payload, missing_fields=[]), result=result)

def cancel_action(db, business_id: str, action_id: str, reason: str = "user_cancelled") -> str:
    """Cancel an active action; returns its threadId so callers needn't re-read the doc."""
    ref = _actions_col(db, business_id).document(action_id)
    snap = ref.get()
    if not snap.exists:
        api_error(404, "action_not_found", "הפעולה לא נמצאה")
    data = snap.to_dict()
    if data["status"] not in ACTIVE_STATUSES:
        api_error(409, "action_not_cancellable", "הפעולה כבר בוצעה או בוטלה")
    ref.update({"status": "cancelled", "cancellationReason": reason, "updatedAt": now_il()})
    return data.get("threadId", "main")

def handle_message(db, parser, business: Business, thread_id: str, text: str) -> ChatTurnResult:
    save_message(db, business.id, thread_id, "user", text)
    active = _load_active_action(db, business.id, thread_id)
    if active and active[1]["status"] == "pending_confirmation":          # fast path: NO LLM call
        norm = normalize(text)
        if norm in CONFIRM_WORDS:
            res = confirm_action(db, parser, business, active[0])
            return ChatTurnResult(assistant_text=res.assistant_text, action=res.action, result=res.result)
        if norm in CANCEL_WORDS:
            cancel_action(db, business.id, active[0])
            reply = "הפעולה בוטלה."
            save_message(db, business.id, thread_id, "assistant", reply, action_id=active[0])
            return ChatTurnResult(assistant_text=reply, action=None)
    cmd = parser.parse_user_command(_build_context(db, business, thread_id, text, active), text)
    if isinstance(cmd, ParserFailure) or cmd.intent == IntentType.UNKNOWN:
        reply = FALLBACK + (("\n" + _current_question(active[1])) if active else "")
        # store what the parser returned (failure reason or UNKNOWN) for auditability
        parsed = cmd.model_dump(mode="json") if hasattr(cmd, "model_dump") else None
        save_message(db, business.id, thread_id, "assistant", reply, parsed_intent=parsed)
        return ChatTurnResult(assistant_text=reply, action=_action_view(*active) if active else None)
    if cmd.intent == IntentType.QUERY:                                     # queries never create actions
        reply = _answer_query(db, business, cmd.query)
        if active: reply = f"{reply}\n\n{_current_question(active[1])}"
        save_message(db, business.id, thread_id, "assistant", reply,
                     action_id=active[0] if active else None, parsed_intent=cmd.model_dump(mode="json"))
        return ChatTurnResult(assistant_text=reply, action=_action_view(*active) if active else None)
    if cmd.intent == IntentType.GENERATE_ANNUAL_REPORT:                    # answers immediately, no pending action
        result = report_service.precheck(db, business, now_il().year)
        reply = render_precheck_summary(result)
        save_message(db, business.id, thread_id, "assistant", reply,
                     parsed_intent=cmd.model_dump(mode="json"))
        return ChatTurnResult(assistant_text=reply, action=None)
    incoming = _payload_for(cmd.intent, cmd)
    if active and active[1]["type"] == cmd.intent.value:
        payload, action_id = merge_payload(active[1]["payload"], incoming, cmd.intent), active[0]
    else:
        if active: cancel_action(db, business.id, active[0], reason="superseded")
        payload, action_id = merge_payload({}, incoming, cmd.intent), None
    missing = compute_missing_fields(cmd.intent, payload)
    status = "collecting_fields" if missing else "pending_confirmation"
    reply = build_followup_question(cmd.intent, missing) if missing else build_confirmation_message(cmd.intent, payload)
    action_id = _upsert_action(db, business.id, thread_id, action_id, cmd.intent, status, payload, missing)
    save_message(db, business.id, thread_id, "assistant", reply, action_id=action_id,
                 parsed_intent=cmd.model_dump(mode="json"))
    return ChatTurnResult(assistant_text=reply, action=ActionView(
        id=action_id, type=cmd.intent.value, status=status, payload=payload, missing_fields=missing))

def _answer_query(db, business: Business, qp) -> str:
    qp = qp or QueryPayload(); qtype = qp.type or QueryType.UNKNOWN
    tr = qp.time_range or TimeRange(preset=TimePreset.THIS_YEAR)
    if tr.preset is None: tr.preset = TimePreset.THIS_YEAR                 # server default
    start, end = resolve_time_range(tr); period = tr.preset.value; bid = business.id
    year = start.year if start else today_il().year
    if qtype == QueryType.TOTAL_REVENUE:
        return render_query_answer(qtype, {"period": period, "total": agg.total_revenue(db, bid, start, end)})
    if qtype == QueryType.TOTAL_EXPENSES:
        return render_query_answer(qtype, {"period": period, "total": agg.total_expenses(db, bid, start, end)})
    if qtype == QueryType.ESTIMATED_PROFIT:
        rev, exp = agg.total_revenue(db, bid, start, end), agg.total_expenses(db, bid, start, end)
        return render_query_answer(qtype, {"period": period, "profit": round_ils(rev - exp), "revenue": rev, "expenses": exp})
    if qtype == QueryType.CLIENT_REVENUE:
        if not qp.client_name: return "לאיזה לקוח הכוונה?"
        return render_query_answer(qtype, {"client_name": qp.client_name,
                                           "total": agg.client_revenue(db, bid, qp.client_name)})
    if qtype == QueryType.CONTACT_EXISTS:
        if not qp.client_name: return "לאיזה איש קשר הכוונה?"
        exists = any(c.name.strip() == qp.client_name.strip()
                     for c in client_service.find_clients_by_name(db, bid, qp.client_name))
        return render_query_answer(qtype, {"client_name": qp.client_name, "exists": exists})
    if qtype == QueryType.RECEIPTS_COUNT:
        return render_query_answer(qtype, {"period": period, "count": agg.receipts_count(db, bid, year)})
    if qtype == QueryType.EXPENSES_BY_CATEGORY:
        return render_query_answer(qtype, {"period": period, "by_category": agg.expenses_by_category(db, bid, year)})
    if qtype == QueryType.OSEK_PATUR_LIMIT_STATUS:
        ts = agg.threshold_status(db, business, today_il().year)
        return render_query_answer(qtype, {"total": ts.total, "limit": ts.limit, "pct": ts.pct,
                                           "remaining": round_ils(max(ts.limit - ts.total, 0.0)), "warning": ts.warning})
    return render_query_answer(QueryType.UNKNOWN, {})
