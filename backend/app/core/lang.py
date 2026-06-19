"""`get_lang` FastAPI dependency: resolves the response language from the
`Accept-Language` header. Returns "en" when the header starts with "en"
(case-insensitive), else "he". Header-less requests default to "he"."""
from fastapi import Header

from app.core.i18n import Lang


def get_lang(accept_language: str | None = Header(default=None)) -> Lang:
    if accept_language and accept_language.strip().lower().startswith("en"):
        return "en"
    return "he"
