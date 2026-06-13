from datetime import date, datetime, timedelta
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

def resolve_time_range(tr) -> tuple[datetime | None, datetime | None]:
    """Map an AI TimeRange (schemas.ai_commands) to [start, end) IL-tz bounds; None = unbounded."""
    from app.schemas.ai_commands import TimePreset  # local import: utils must not import schemas at module load

    preset = tr.preset or TimePreset.ALL_TIME
    now = now_il()
    today = datetime(now.year, now.month, now.day, tzinfo=IL_TZ)
    if preset == TimePreset.TODAY:
        return today, today + timedelta(days=1)
    if preset == TimePreset.THIS_WEEK:                       # Israeli week starts Sunday
        start = today - timedelta(days=(now.weekday() + 1) % 7)
        return start, start + timedelta(days=7)
    if preset == TimePreset.THIS_MONTH:
        return month_bounds(now.year, now.month)
    if preset == TimePreset.THIS_YEAR:
        return year_bounds(now.year)
    if preset == TimePreset.LAST_YEAR:
        return year_bounds(now.year - 1)
    if preset == TimePreset.CUSTOM:
        start_d, end_d = parse_iso_date(tr.start_date), parse_iso_date(tr.end_date)
        start = datetime(start_d.year, start_d.month, start_d.day, tzinfo=IL_TZ) if start_d else None
        end = (datetime(end_d.year, end_d.month, end_d.day, tzinfo=IL_TZ) + timedelta(days=1)) if end_d else None
        return start, end
    return None, None                                        # ALL_TIME
