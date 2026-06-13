from app.schemas.common import CamelModel  # shared base — don't redefine (would silently drift)


class DashboardTotals(CamelModel):
    income_this_year: float
    income_this_month: float
    expenses_this_year: float
    estimated_profit: float  # income_this_year - expenses_this_year, round_ils'd


class DashboardCounts(CamelModel):
    receipts_count: int            # issued receipts this year
    approved_expenses_count: int   # approved expenses this year
    needs_review_count: int        # needs_review expenses, all time


class ThresholdOut(CamelModel):
    total: float
    limit: int
    pct: float
    warning: bool


class MonthlyIncomeEntry(CamelModel):
    month: int   # 1..12
    total: float


class RecentReceipt(CamelModel):
    id: str
    receipt_number: str
    client_name: str
    amount: float
    issue_date: str
    pdf_url: str | None = None


class RecentExpense(CamelModel):
    id: str
    supplier_name: str | None = None
    amount: float | None = None
    category: str | None = None
    expense_date: str | None = None
    status: str


class DashboardResponse(CamelModel):
    totals: DashboardTotals
    counts: DashboardCounts
    threshold: ThresholdOut
    monthly_income: list[MonthlyIncomeEntry]
    expenses_by_category: dict[str, float]
    recent_receipts: list[RecentReceipt]
    recent_expenses: list[RecentExpense]
    warnings: list[str]
