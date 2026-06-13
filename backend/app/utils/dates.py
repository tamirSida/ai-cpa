from datetime import date, datetime
from zoneinfo import ZoneInfo

IL_TZ = ZoneInfo("Asia/Jerusalem")

def now_il() -> datetime:
    return datetime.now(IL_TZ)

def today_il() -> date:
    return now_il().date()

def year_bounds(year: int) -> tuple[datetime, datetime]:
    return datetime(year, 1, 1, tzinfo=IL_TZ), datetime(year + 1, 1, 1, tzinfo=IL_TZ)

def month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=IL_TZ)
    end = datetime(year + 1, 1, 1, tzinfo=IL_TZ) if month == 12 else datetime(year, month + 1, 1, tzinfo=IL_TZ)
    return start, end

def parse_iso_date(s: str | None) -> date | None:
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError):
        return None
