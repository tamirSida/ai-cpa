"""Lightweight i18n for backend user-facing CANNED chat/dashboard replies.

Only the strings the frontend renders verbatim live here. `api_error` codes,
PDF/HTML report content and LLM prompts are intentionally NOT localized here:
error codes are localized client-side by code, and PDF/report content stays Hebrew.

Default language is Hebrew everywhere — every caller that does not pass a language
(every existing test, every header-less request) gets the original Hebrew literals
unchanged. `tr()` falls back to Hebrew for an unknown language or key.
"""
from typing import Literal

Lang = Literal["he", "en"]

MESSAGES: dict[str, dict[str, str]] = {
    "he": {
        # chat_service replies
        "chat.fallback": "לא הצלחתי להבין, אפשר לנסח שוב?",
        "chat.receipt_created": "נוצרה קבלה מספר {n}.",
        "chat.contact_added": "איש הקשר {name} נוסף בהצלחה.",
        "chat.expense_saved": "ההוצאה נשמרה.{note}",
        "chat.expense_needs_review_note": " היא ממתינה לבדיקה כי חסרה קטגוריה.",
        "chat.annual_report_ready": "מעולה. אפשר להפיק את הדוח השנתי לשנת {year} בעמוד הדוח השנתי.",
        "chat.execution_error": "אירעה שגיאה בביצוע הפעולה. אפשר לנסות לאשר שוב.",
        "chat.cancelled": "הפעולה בוטלה.",
        "chat.which_client": "לאיזה לקוח הכוונה?",
        "chat.which_contact": "לאיזה איש קשר הכוונה?",
        # dashboard_service warnings + profile-field labels
        "dashboard.field.address": "כתובת",
        "dashboard.field.phone": "טלפון",
        "dashboard.field.email": "אימייל",
        "dashboard.warning.needs_review": "{count} הוצאות ממתינות לבדיקה",
        "dashboard.warning.missing_profile": "חסרים פרטים בפרופיל העסק: {fields}",
        "dashboard.warning.threshold": "הגעת ל-{pct}% מתקרת עוסק פטור ({total} מתוך {limit})",
        "dashboard.warning.missing_pdf": "{count} קבלות ללא קובץ PDF",
    },
    "en": {
        # chat_service replies
        "chat.fallback": "I didn't quite catch that, could you rephrase?",
        "chat.receipt_created": "Receipt number {n} was created.",
        "chat.contact_added": "Contact {name} was added successfully.",
        "chat.expense_saved": "The expense was saved.{note}",
        "chat.expense_needs_review_note": " It is pending review because it has no category.",
        "chat.annual_report_ready": "Great. You can generate the {year} annual report on the annual report page.",
        "chat.execution_error": "An error occurred while performing the action. You can try confirming again.",
        "chat.cancelled": "Action cancelled.",
        "chat.which_client": "Which client do you mean?",
        "chat.which_contact": "Which contact do you mean?",
        # dashboard_service warnings + profile-field labels
        "dashboard.field.address": "Address",
        "dashboard.field.phone": "Phone",
        "dashboard.field.email": "Email",
        "dashboard.warning.needs_review": "{count} expenses pending review",
        "dashboard.warning.missing_profile": "Missing business profile details: {fields}",
        "dashboard.warning.threshold": "You've reached {pct}% of the exempt-dealer ceiling ({total} of {limit})",
        "dashboard.warning.missing_pdf": "{count} receipts without a PDF file",
    },
}


def tr(lang: str, key: str, **vars) -> str:
    """Translate `key` into `lang`, formatting `{placeholder}` vars.

    Falls back to Hebrew for an unknown language, and to the Hebrew value for a
    key missing in the requested language. Hebrew is the source of truth.
    """
    table = MESSAGES.get(lang, MESSAGES["he"])
    template = table.get(key, MESSAGES["he"][key])
    return template.format(**vars)
