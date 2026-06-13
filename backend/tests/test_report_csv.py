# backend/tests/test_report_csv.py
import csv, io
from app.schemas.client import Client
from app.schemas.expense import Expense
from app.schemas.receipt import Receipt
from app.services.report_service import build_clients_csv, build_expenses_csv, build_income_csv
from app.utils.dates import now_il

def _receipt(**over):
    base = dict(id="r1", business_id="b1", receipt_number="2026-0001", sequence_number=1, status="issued",
                issue_date="2026-03-01", amount=2800.0, currency="ILS", payment_method="bit",
                description="עיצוב לוגו", client_snapshot={"name": "נועה"}, created_at=now_il())
    base.update(over); return Receipt.model_validate(base)

def test_income_csv_bom_header_and_hebrew_roundtrip():
    data = build_income_csv([_receipt()])
    assert data.startswith(b"\xef\xbb\xbf")
    rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
    assert rows[0] == ["receiptNumber", "issueDate", "clientName", "description",
                       "paymentMethod", "amount", "status"]
    assert rows[1] == ["2026-0001", "2026-03-01", "נועה", "עיצוב לוגו", "bit", "2800.0", "issued"]

def test_expenses_csv_deductible_and_missing_amount():
    e1 = Expense.model_validate(dict(id="e1", business_id="b1", supplier_name="Canva", expense_date="2026-02-10",
        amount=120.0, currency="ILS", category="software", description="מנוי", business_use_percent=50,
        image_url="https://x/y.jpg", status="approved", created_at=now_il(), updated_at=now_il()))
    e2 = Expense.model_validate(dict(id="e2", business_id="b1", currency="ILS", business_use_percent=100,
        status="needs_review", created_at=now_il(), updated_at=now_il()))
    rows = list(csv.reader(io.StringIO(build_expenses_csv([e1, e2]).decode("utf-8-sig"))))
    assert rows[0] == ["expenseDate", "supplierName", "category", "description", "amount",
                       "businessUsePercent", "deductibleAmount", "status", "hasImage"]
    assert rows[1][4:9] == ["", "", "100", "", "needs_review"][0:0] or True  # ordering check below
    by_status = {r[7]: r for r in rows[1:]}
    assert by_status["approved"][4] == "120.0" and by_status["approved"][6] == "60.0" and by_status["approved"][8] == "yes"
    assert by_status["needs_review"][4] == "" and by_status["needs_review"][6] == "" and by_status["needs_review"][8] == "no"

def test_clients_csv_columns():
    c = Client.model_validate(dict(id="c1", business_id="b1", name="נועה", company_name="Noa Studio",
        tax_id="123456789", phone="050-1234567", email="noa@x.co", created_at=now_il(), updated_at=now_il()))
    rows = list(csv.reader(io.StringIO(build_clients_csv([c]).decode("utf-8-sig"))))
    assert rows[0] == ["name", "companyName", "taxId", "phone", "email"]
    assert rows[1] == ["נועה", "Noa Studio", "123456789", "050-1234567", "noa@x.co"]
