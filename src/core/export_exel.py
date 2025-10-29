"""Export Django model data to Excel and prepare invoice data."""

from decimal import Decimal

import django
import pandas as pd
from django.db.models import Sum
from openpyxl import load_workbook

from src.financials.models import CashBox
from src.financials.models import Invoice
from src.financials.models import PersonalAccount
from src.services.models import PaymentDetail

# Initialize Django
django.setup()


def export_accounts_to_excel(filename: str = "personal_accounts.xlsx") -> None:
    """Export personal accounts to Excel and adjust column widths."""
    # Fetch accounts with related apartment, user, house, section, and floor
    accounts = PersonalAccount.objects.select_related(
        "apartment__user",
        "apartment__house",
        "apartment__section",
        "apartment__floor",
    ).all()

    # Transform accounts into list of dictionaries
    account_data = [
        {
            "Account_Number": account.account_number,
            "Status": account.status,
            "House": getattr(account.apartment.house, "title", "")
            if getattr(account, "apartment", None)
            else "",
            "Section": getattr(account.apartment.section, "name", "")
            if getattr(account, "apartment", None)
            else "",
            "Apartment": getattr(account.apartment, "apartment_number", ""),
            "Owner": getattr(account.user, "full_name", ""),
            "Balance": CashBox.objects.filter(personal_account=account).aggregate(
                total=Sum("sum")
            )["total"]
            or 0,
        }
        for account in accounts
    ]

    # Convert to DataFrame and save to Excel
    accounts_df = pd.DataFrame(account_data)
    accounts_df.to_excel(filename, index=False, engine="openpyxl")

    # Adjust column widths
    wb = load_workbook(filename)
    ws = wb.active
    _adjust_column_widths(ws)
    wb.save(filename)


def export_cash_box_to_excel(filename: str = "cash.xlsx") -> None:
    """Export cash box records to Excel and adjust column widths."""
    # Fetch cash boxes for owner_id 15
    cash_boxes = CashBox.objects.select_related(
        "personal_account", "payment_articles", "manager", "owner"
    ).filter(owner_id=15)

    # Transform cash boxes into list of dictionaries
    cash_data = [
        {
            "Number": box.cash_box_number,
            "Date": box.date,
            "Type": box.payment_articles.record_type,
            "Status": "Conducted" if box.is_conducted else "Not conducted",
            "Article": box.payment_articles.name,
            "Service_Amount": box.suma,
            "Currency": "UAH",
            "Owner": getattr(box.owner, "full_name", ""),
            "Account": getattr(box.personal_account, "account_number", ""),
            "Amount": box.suma,
        }
        for box in cash_boxes
    ]

    # Convert to DataFrame and save to Excel
    cashboxes_df = pd.DataFrame(cash_data)
    cashboxes_df.to_excel(filename, index=False, engine="openpyxl")

    # Adjust column widths
    wb = load_workbook(filename)
    ws = wb.active
    _adjust_column_widths(ws)
    wb.save(filename)


def _adjust_column_widths(ws) -> None:
    """Adjust column widths in the Excel worksheet."""
    for col in ws.columns:
        max_length = max(
            (len(str(cell.value)) for cell in col if cell.value), default=0
        )
        ws.column_dimensions[col[0].column_letter].width = max_length + 2


class InvoiceTemplate:
    """Store workbook and worksheet objects for invoice template."""

    def __init__(self, template_path: str, invoice_obj) -> None:
        """Initialize the invoice template."""
        self._template_path = template_path
        self._invoice_obj = invoice_obj
        self._wb = None
        self._ws = None


def get_invoice_data(invoice_id: int) -> dict:
    """Return a dictionary with invoice data including services and payments."""
    # Fetch invoice and related objects
    invoice = Invoice.objects.select_related(
        "personal_account__apartment__house", "tariff"
    ).get(id=invoice_id)

    payment_detail = PaymentDetail.objects.first()

    # Extract owner, house, apartment info
    owner_name = (
        invoice.personal_account.user.get_full_name()
        if invoice.personal_account and invoice.personal_account.user
        else ""
    )
    house_address = (
        getattr(invoice.personal_account.apartment.house, "address", "")
        if invoice.personal_account and invoice.personal_account.apartment
        else ""
    )
    apartment_num = (
        getattr(invoice.personal_account.apartment, "apartment_number", "")
        if invoice.personal_account and invoice.personal_account.apartment
        else ""
    )
    full_address = ", ".join(
        part
        for part in [
            owner_name,
            house_address,
            f"Apt {apartment_num}" if apartment_num else "",
        ]
        if part
    )

    data = {
        "Inv_Number": invoice.invoice_number,
        "Status": invoice.get_status_display(),
        "Inv_Date": invoice.date.strftime("%d.%m.%Y") if invoice.date else "",
        "Inv_Period": (
            f"{invoice.start_date:%d.%m.%Y} - {invoice.end_date:%d.%m.%Y}"
            if invoice.start_date and invoice.end_date
            else ""
        ),
        "Conducted": "Yes" if invoice.conducted else "No",
        "Owner": owner_name,
        "House": house_address,
        "Apartment": apartment_num,
        "Full_Address": full_address,
        "Client_Acc": getattr(invoice.personal_account, "account_number", ""),
        "Phone": getattr(getattr(invoice.personal_account, "user", None), "phone", ""),
        "Section": getattr(
            getattr(
                getattr(invoice.personal_account, "apartment", None), "section", None
            ),
            "name",
            "",
        ),
        "Payee": getattr(payment_detail, "description", ""),
        "Tariff": getattr(invoice.tariff, "title", ""),
    }

    # Add services
    total = Decimal("0")
    for idx, item in enumerate(
        invoice.items.select_related("tariff_service__service", "tariff_service__unit"),
        start=1,
    ):
        service = item.tariff_service
        row = {
            f"Service_{idx}": getattr(getattr(service, "service", None), "name", ""),
            f"Quantity_{idx}": item.count,
            f"Tariff_{idx}": getattr(getattr(service, "tariff", None), "title", ""),
            f"Unit_{idx}": getattr(getattr(service, "unit", None), "name", ""),
            f"Price_{idx}": getattr(service, "price", ""),
            f"Amount_{idx}": item.total,
        }
        total += item.total
        data.update(row)

    # Calculate totals
    personal_account_id = getattr(invoice.personal_account, "id", None)
    invoices_total = payments_total = Decimal("0")
    if personal_account_id:
        invoices = Invoice.objects.filter(
            personal_account_id=personal_account_id, conducted=True
        ).prefetch_related("items")
        invoices_total = sum(
            sum(item.total for item in inv.items.all())
            for inv in invoices
            if inv.status in ("zero", "counted")
        )
        payments_total = CashBox.objects.filter(
            personal_account_id=personal_account_id, is_conducted=True
        ).aggregate(total=Sum("suma"))["total"] or Decimal("0")

    data.update(
        {
            "Invoices_Total": invoices_total,
            "Paid_Total": payments_total,
            "Client_Balance": payments_total - invoices_total,
            "Total_Amount": total,
        }
    )

    return data
