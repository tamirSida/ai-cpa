# backend/app/schemas/report.py
from datetime import datetime

from app.schemas.common import CamelModel  # shared base — don't redefine (would silently drift)


class PrecheckResult(CamelModel):
    year: int
    expenses_needing_review: list[str]   # expense ids, status == needs_review
    expenses_missing_images: list[str]   # expense ids (approved/needs_review, no imageUrl)
    uncategorized_expenses: list[str]    # expense ids (non-rejected, no category)
    receipts_missing_pdf: list[str]      # receipt numbers (issued, no pdfUrl)
    receipts_missing_payer_address: list[str] = []  # receipt numbers (issued, no client address)
    cancelled_receipts: list[str]        # receipt numbers
    missing_business_fields: list[str]   # camelCase business field names
    total_revenue: float
    threshold_warning: bool
    issues_count: int


class AnnualReport(CamelModel):          # doc §5.8
    id: str
    business_id: str
    year: int
    total_income: float
    total_expenses: float
    estimated_profit: float
    warnings: list[str]
    generated_at: datetime
