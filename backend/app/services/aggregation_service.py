# backend/app/services/aggregation_service.py
from datetime import date
from typing import Optional

from pydantic import BaseModel
from google.cloud.firestore_v1.base_query import FieldFilter

from app.core.config import get_settings
from app.utils.money import round_ils


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _issued_receipts(db, business_id: str, start: Optional[date], end: Optional[date]) -> list[dict]:
    """Return all issued receipts for a business, optionally bounded by issueDate range.

    start / end are datetime.date objects (or None for unbounded / ALL_TIME).
    issueDate is stored as an ISO "YYYY-MM-DD" string; comparison uses .isoformat().
    """
    col = db.collection("businesses").document(business_id).collection("receipts")
    q = col.where(filter=FieldFilter("status", "==", "issued"))
    if start is not None:
        q = q.where(filter=FieldFilter("issueDate", ">=", start.isoformat()))
    if end is not None:
        q = q.where(filter=FieldFilter("issueDate", "<=", end.isoformat()))
    return [doc.to_dict() for doc in q.stream()]


def _approved_expenses(db, business_id: str, start: Optional[date], end: Optional[date]) -> list[dict]:
    """Return all approved expenses for a business, optionally bounded by expenseDate range."""
    col = db.collection("businesses").document(business_id).collection("expenses")
    q = col.where(filter=FieldFilter("status", "==", "approved"))
    if start is not None:
        q = q.where(filter=FieldFilter("expenseDate", ">=", start.isoformat()))
    if end is not None:
        q = q.where(filter=FieldFilter("expenseDate", "<=", end.isoformat()))
    return [doc.to_dict() for doc in q.stream()]


# ---------------------------------------------------------------------------
# Revenue aggregations
# ---------------------------------------------------------------------------

def total_revenue(db, business_id: str, start: Optional[date], end: Optional[date]) -> float:
    """Sum of issued receipt amounts in the given date range."""
    issued = _issued_receipts(db, business_id, start, end)
    return round_ils(sum(r["amount"] for r in issued))


def monthly_income(db, business_id: str, year: int) -> dict[int, float]:
    """Dict {1..12: total ILS} of issued receipts bucketed by month for the given year."""
    result: dict[int, float] = {m: 0.0 for m in range(1, 13)}
    issued = _issued_receipts(db, business_id, date(year, 1, 1), date(year, 12, 31))
    for r in issued:
        month = int(r["issueDate"][5:7])
        result[month] += r["amount"]
    return {m: round_ils(v) for m, v in result.items()}


def client_revenue(db, business_id: str, client_name: str) -> float:
    """Total revenue from a specific client (all-time, by exact clientSnapshot.name match).

    Pushes the name match into Firestore (status + clientSnapshot.name composite index)
    instead of a Python full-scan, so cost stays bounded as receipt volume grows.
    """
    col = db.collection("businesses").document(business_id).collection("receipts")
    q = (col.where(filter=FieldFilter("status", "==", "issued"))
            .where(filter=FieldFilter("clientSnapshot.name", "==", client_name)))
    return round_ils(sum(doc.to_dict()["amount"] for doc in q.stream()))


def receipts_count(db, business_id: str, year: int) -> int:
    """Count of issued receipts in the given year."""
    return len(_issued_receipts(db, business_id, date(year, 1, 1), date(year, 12, 31)))


# ---------------------------------------------------------------------------
# Expense aggregations
# ---------------------------------------------------------------------------

def total_expenses(db, business_id: str, start: Optional[date], end: Optional[date]) -> float:
    """Sum of approved expense amounts in the given date range. Empty → 0.0."""
    approved = _approved_expenses(db, business_id, start, end)
    if not approved:
        return 0.0
    return round_ils(sum(e["amount"] for e in approved))


def expenses_by_category(db, business_id: str, year: int) -> dict[str, float]:
    """Approved expenses in the given year grouped by category. Empty → {}."""
    approved = _approved_expenses(db, business_id, date(year, 1, 1), date(year, 12, 31))
    if not approved:
        return {}
    totals: dict[str, float] = {}
    for e in approved:
        cat = e.get("category") or "other"
        totals[cat] = totals.get(cat, 0.0) + e["amount"]
    return {cat: round_ils(v) for cat, v in totals.items()}


# ---------------------------------------------------------------------------
# Threshold status
# ---------------------------------------------------------------------------

class ThresholdStatus(BaseModel):
    total: float
    limit: float
    pct: float
    warning: bool


def threshold_status(db, business, year: int) -> ThresholdStatus:
    """Revenue threshold status for a business in the given year.

    business is a Business model with .annual_limit (Optional[int]) and .id.
    limit falls back to get_settings().annual_limit_ils only when business.annual_limit is
    None (an explicit 0 is honored, not silently replaced). warning is True when pct >= 90.
    """
    total = total_revenue(db, business.id, date(year, 1, 1), date(year, 12, 31))
    limit = float(business.annual_limit if business.annual_limit is not None else get_settings().annual_limit_ils)
    pct = round(total / limit * 100, 1) if limit != 0 else 0.0
    return ThresholdStatus(total=total, limit=limit, pct=pct, warning=pct >= 90)
