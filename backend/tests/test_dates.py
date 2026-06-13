from datetime import datetime
from app.utils.dates import IL_TZ, now_il, today_il, year_bounds, month_bounds, parse_iso_date

def test_now_il_is_jerusalem():
    assert now_il().tzinfo is IL_TZ and now_il().utcoffset() is not None

def test_year_bounds():
    start, end = year_bounds(2026)
    assert start == datetime(2026, 1, 1, tzinfo=IL_TZ) and end == datetime(2027, 1, 1, tzinfo=IL_TZ)

def test_month_bounds_december_wraps():
    assert month_bounds(2026, 12)[1] == datetime(2027, 1, 1, tzinfo=IL_TZ)

def test_parse_iso_date():
    assert parse_iso_date("2026-06-13").isoformat() == "2026-06-13"
    assert parse_iso_date("13/06/2026") is None and parse_iso_date(None) is None

from app.schemas.ai_commands import TimePreset, TimeRange
from app.utils.dates import resolve_time_range

def test_resolve_this_year_matches_year_bounds():
    start, end = resolve_time_range(TimeRange(preset=TimePreset.THIS_YEAR))
    assert (start, end) == year_bounds(start.year)

def test_resolve_all_time_unbounded():
    assert resolve_time_range(TimeRange(preset=TimePreset.ALL_TIME)) == (None, None)

def test_resolve_custom_dates_end_exclusive():
    start, end = resolve_time_range(TimeRange(preset=TimePreset.CUSTOM,
                                              start_date="2026-01-01", end_date="2026-06-30"))
    assert start == datetime(2026, 1, 1, tzinfo=IL_TZ) and end == datetime(2026, 7, 1, tzinfo=IL_TZ)

def test_resolve_custom_bad_dates_unbounded():
    assert resolve_time_range(TimeRange(preset=TimePreset.CUSTOM, start_date="junk")) == (None, None)
