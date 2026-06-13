import re
from app.schemas.ai_commands import IntentType
from app.utils.money import format_ils

_PUNCT = re.compile(r"[!?,.;:׳״'\"()\[\]{}\-]+")
def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", _PUNCT.sub(" ", text)).strip().lower()

CONFIRM_WORDS = {"אישור", "כן", "אשר", "מאשר", "מאשרת", "אוקיי", "אוקי", "סבבה", "ok", "yes", "y", "confirm"}
CANCEL_WORDS = {"בטל", "ביטול", "לא", "עזוב", "תבטל", "cancel", "no"}

PAYMENT_HE = {"cash": "מזומן", "bank_transfer": "העברה בנקאית", "bit": "ביט", "paybox": "פייבוקס",
              "credit_card": "כרטיס אשראי", "check": "צ'ק", "other": "אחר"}
PERIOD_HE = {"TODAY": "היום", "THIS_WEEK": "השבוע", "THIS_MONTH": "החודש", "THIS_YEAR": "השנה",
             "LAST_YEAR": "בשנה שעברה", "ALL_TIME": 'סה"כ', "CUSTOM": "בתקופה שביקשת"}
CATEGORY_HE = {"software": "תוכנה", "equipment": "ציוד", "travel": "נסיעות", "office": "משרד",
               "marketing": "שיווק", "professional_services": "שירותים מקצועיים",
               "meals": "אוכל", "parking": "חניה", "other": "אחר"}

_FIELD_Q = {
    (IntentType.CREATE_RECEIPT, "client_name"): "ממי התקבל התשלום?",
    (IntentType.CREATE_RECEIPT, "amount"): "מה הסכום ששולם ובאיזה אמצעי תשלום?",
    (IntentType.CREATE_RECEIPT, "description"): "עבור מה התשלום?",
    (IntentType.CREATE_RECEIPT, "payment_received_confirmation"): "האם התשלום כבר התקבל?",
    (IntentType.CREATE_RECEIPT, "check_number"): "מהם פרטי ההמחאה (מספר, בנק, סניף ותאריך פירעון)?",
    (IntentType.CREATE_RECEIPT, "check_bank"): "מהם פרטי ההמחאה (מספר, בנק, סניף ותאריך פירעון)?",
    (IntentType.CREATE_RECEIPT, "check_branch"): "מהם פרטי ההמחאה (מספר, בנק, סניף ותאריך פירעון)?",
    (IntentType.CREATE_RECEIPT, "check_due_date"): "מהם פרטי ההמחאה (מספר, בנק, סניף ותאריך פירעון)?",
    (IntentType.CREATE_CONTACT, "name"): "מה שם איש הקשר?",
    (IntentType.CREATE_EXPENSE, "amount"): "מה סכום ההוצאה?",
}
def build_followup_question(intent: IntentType, missing_fields: list[str]) -> str:
    seen: set[str] = set()
    qs = []
    for f in missing_fields:
        q = _FIELD_Q.get((intent, f))
        if q and q not in seen:
            seen.add(q); qs.append(q)
    return " ".join(qs) or "חסרים לי כמה פרטים, אפשר לפרט?"

def build_confirmation_message(intent: IntentType, payload: dict) -> str:
    if intent == IntentType.CREATE_RECEIPT:
        base = f"לאשר יצירת קבלה על {format_ils(payload['amount'])} ל{payload['client_name']} עבור {payload['description']}"
        pm = payload.get("payment_method")
        if pm and pm != "unknown":
            return f"{base}, תשלום ב{PAYMENT_HE.get(pm, pm)}?"  # .get: never KeyError on an off-enum value
        return f"{base}? (אמצעי תשלום לא צוין)"
    if intent == IntentType.CREATE_CONTACT:
        return f"לאשר יצירת איש קשר בשם {payload['name']}?"
    if intent == IntentType.CREATE_EXPENSE:
        target = payload.get("supplier_name") or payload.get("description") or "הוצאה"
        return f"לאשר הוצאה של {format_ils(payload['amount'])} על {target}?"
    return f"לאשר יצירת דוח שנתי לשנת {payload['year']}?"

def render_query_answer(query_type, data: dict) -> str:
    qt = getattr(query_type, "value", query_type)
    p = PERIOD_HE.get(data.get("period", "THIS_YEAR"), "השנה")
    if qt == "TOTAL_REVENUE": return f"ההכנסות שלך {p} הן {format_ils(data['total'])}."
    if qt == "TOTAL_EXPENSES": return f"ההוצאות שלך {p} הן {format_ils(data['total'])}."
    if qt == "ESTIMATED_PROFIT":
        return (f"הרווח המשוער שלך {p} הוא {format_ils(data['profit'])} "
                f"(הכנסות {format_ils(data['revenue'])} פחות הוצאות {format_ils(data['expenses'])}).")
    if qt == "CLIENT_REVENUE": return f"{data['client_name']} שילם/ה לך סה\"כ {format_ils(data['total'])}."
    if qt == "CONTACT_EXISTS":
        return (f"כן, {data['client_name']} נמצא/ת באנשי הקשר." if data["exists"]
                else f"לא מצאתי איש קשר בשם {data['client_name']}.")
    if qt == "RECEIPTS_COUNT": return f"הוצאת {data['count']} קבלות {p}."
    if qt == "EXPENSES_BY_CATEGORY":
        if not data["by_category"]: return f"אין הוצאות מאושרות {p}."
        lines = [f"• {CATEGORY_HE.get(c, c)}: {format_ils(t)}"
                 for c, t in sorted(data["by_category"].items(), key=lambda kv: -kv[1])]
        return f"הוצאות לפי קטגוריה {p}:\n" + "\n".join(lines)
    if qt == "OSEK_PATUR_LIMIT_STATUS":
        msg = (f"ההכנסות שלך השנה הן {format_ils(data['total'])} מתוך תקרה של {format_ils(data['limit'])} "
               f"({data['pct']}%). נותרו {format_ils(data['remaining'])}.")
        return msg + (" שים/י לב: את/ה מתקרב/ת לתקרת עוסק פטור." if data["warning"] else "")
    return "לא הצלחתי להבין את השאלה, אפשר לנסח שוב?"

def render_precheck_summary(result) -> str:
    parts = []
    if result.expenses_needing_review:
        parts.append(f"{len(result.expenses_needing_review)} הוצאות שדורשות בדיקה")
    if result.expenses_missing_images:
        parts.append(f"{len(result.expenses_missing_images)} הוצאות ללא קבלה מצולמת")
    if result.uncategorized_expenses:
        parts.append(f"{len(result.uncategorized_expenses)} הוצאות ללא קטגוריה")
    if result.receipts_missing_pdf:
        parts.append(f"{len(result.receipts_missing_pdf)} קבלות ללא PDF")
    if result.missing_business_fields:
        parts.append("פרטי עסק חסרים: " + ", ".join(result.missing_business_fields))
    total = format_ils(result.total_revenue)
    if not parts:
        return (f"הכל מוכן! סך ההכנסות לשנת {result.year}: {total}. "
                "להורדת החבילה לרואה החשבון: /annual-report")
    return ("לפני הפקת הדוח כדאי לטפל ב: " + "; ".join(parts) +
            f". סך ההכנסות עד כה: {total}. להמשך ולהורדה: /annual-report")
