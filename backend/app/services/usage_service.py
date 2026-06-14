from google.cloud import firestore

from app.core.config import Settings, get_settings
from app.core.errors import api_error
from app.schemas.user import UsageSummary, User
from app.utils.dates import now_il

MICRO = 1_000_000  # micro-dollars per USD: integer accounting, floats only at the API edge.


def _month_key(now=None) -> str:
    """Israel-local 'YYYY-MM' bucket key; derives from now_il() when now is None."""
    now = now or now_il()
    return f"{now.year:04d}-{now.month:02d}"


def _usage_ref(db, uid: str, month: str):
    return db.collection("users").document(uid).collection("usage").document(month)


def _price_for(settings: Settings, model: str) -> tuple[float, float]:
    """(input, output) per-token price; falls back to the 'default' row for unknown models."""
    table = settings.openai_pricing
    row = table.get(model) or table["default"]
    return row["input"], row["output"]


def estimate_cost_micro(settings: Settings, model: str, usage) -> int:
    """usage: object with .input_tokens / .output_tokens (ints), or None.
    None or missing/zero tokens -> 0. Returns rounded integer micro-dollars."""
    if usage is None:
        return 0
    in_tokens = getattr(usage, "input_tokens", None) or 0
    out_tokens = getattr(usage, "output_tokens", None) or 0
    in_price, out_price = _price_for(settings, model)
    cost_usd = in_tokens * in_price + out_tokens * out_price
    return round(cost_usd * MICRO)


def current_month_cost_micro(db, uid: str) -> int:
    """Read the current month's accumulated cost in micro-dollars; 0 if the bucket is absent."""
    snap = _usage_ref(db, uid, _month_key()).get()
    if not snap.exists:
        return 0
    return int(snap.to_dict().get("aiCostMicroUsd") or 0)


def assert_budget(db, user: User) -> None:
    """Hard block: raise 429 if this month's actual AI cost has reached the user's cap.
    Unlimited (ai_budget_usd is None) never raises."""
    if user.ai_budget_usd is None:
        return
    cap_micro = round(user.ai_budget_usd * MICRO)
    if current_month_cost_micro(db, user.uid) >= cap_micro:
        api_error(429, "ai_budget_exceeded", "Monthly AI budget reached. Contact your administrator.")


def record_cost(db, uid: str, model: str, usage) -> None:
    """Atomically accumulate the call's actual cost into the current month's bucket.
    No-op when the computed cost is zero (e.g. usage is None)."""
    micro = estimate_cost_micro(get_settings(), model, usage)
    if micro <= 0:
        return
    key = _month_key()
    _usage_ref(db, uid, key).set(
        {"month": key, "aiCostMicroUsd": firestore.Increment(micro), "updatedAt": now_il()},
        merge=True,  # creates the bucket on first write
    )


def usage_summary(db, user: User) -> UsageSummary:
    micro = current_month_cost_micro(db, user.uid)
    cost = micro / MICRO
    over = user.ai_budget_usd is not None and cost >= user.ai_budget_usd
    return UsageSummary(
        month=_month_key(),
        ai_cost_usd=round(cost, 6),
        ai_budget_usd=user.ai_budget_usd,
        over_budget=over,
    )
