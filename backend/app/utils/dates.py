from datetime import date, datetime
from zoneinfo import ZoneInfo

IL_TZ = ZoneInfo("Asia/Jerusalem")

def now_il() -> datetime:
    return datetime.now(IL_TZ)
