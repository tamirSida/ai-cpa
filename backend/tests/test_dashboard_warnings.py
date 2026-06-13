# backend/tests/test_dashboard_warnings.py
from datetime import datetime, timezone
from app.schemas.business import Business
from app.schemas.dashboard import ThresholdOut
from app.services.dashboard_service import build_warnings

NOW = datetime(2026, 6, 13, tzinfo=timezone.utc)


def _biz(**over):
    base = dict(id="b1", owner_user_id="test-uid", business_name="עיצוב תמיר",
                owner_name="תמיר", business_id_number="123456789", business_type="osek_patur",
                address="הרצל 1, תל אביב", phone="0501234567", email="t@x.co",
                receipt_prefix="2026", next_receipt_number=3, created_at=NOW, updated_at=NOW)
    base.update(over)
    return Business(**base)


def test_all_warnings_in_order():
    ws = build_warnings(_biz(address=None, phone=None), needs_review_count=2,
                        threshold=ThresholdOut(total=110000.0, limit=120000, pct=91.7, warning=True),
                        missing_pdf_count=1)
    assert ws[0] == "2 הוצאות ממתינות לבדיקה"
    assert ws[1] == "חסרים פרטים בפרופיל העסק: כתובת, טלפון"
    assert ws[2].startswith("הגעת ל-92% מתקרת עוסק פטור")
    assert ws[3] == "1 קבלות ללא קובץ PDF"
    assert len(ws) == 4


def test_no_warnings_when_clean():
    assert build_warnings(_biz(), 0, ThresholdOut(total=0.0, limit=120000, pct=0.0, warning=False), 0) == []
