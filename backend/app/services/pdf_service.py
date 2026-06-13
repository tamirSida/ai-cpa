import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.utils.money import format_ils

os.environ.setdefault("XDG_CACHE_HOME", "/tmp/cache")  # fontconfig cache for non-root containers
APP_DIR = Path(__file__).resolve().parent.parent
_env = Environment(loader=FileSystemLoader(APP_DIR / "templates"), autoescape=select_autoescape(["html"]))
_env.filters["ils"] = format_ils
_env.globals["payment_labels"] = {"cash": "מזומן", "bank_transfer": "העברה בנקאית", "bit": "ביט",
                                  "paybox": "פייבוקס", "credit_card": "כרטיס אשראי", "check": "צ'ק",
                                  "other": "אחר", "unknown": "לא צוין"}

def render_pdf(template_name: str, context: dict) -> bytes:
    from weasyprint import HTML  # lazy: keeps non-PDF test imports fast
    html = _env.get_template(template_name).render(**context)
    return HTML(string=html, base_url=str(APP_DIR / "templates")).write_pdf()
