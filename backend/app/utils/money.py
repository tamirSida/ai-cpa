from decimal import Decimal, ROUND_HALF_UP

def round_ils(x: float) -> float:
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def format_ils(x: float) -> str:
    s = f"{round_ils(x):,.2f}"
    if s.endswith(".00"):
        s = s[:-3]
    return f"₪{s}"
