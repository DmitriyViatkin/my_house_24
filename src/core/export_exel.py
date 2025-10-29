import re
from contextlib import suppress
from decimal import Decimal
from html import escape
from pathlib import Path

import django
import pandas as pd
from django.conf import settings
from django.db.models import Sum
from openpyxl import load_workbook
from openpyxl.styles import Border
from openpyxl.styles import Side
from weasyprint import HTML

# Setup Django
BASE_DIR = Path(settings.BASE_DIR)
django.setup()

from src.financials.models import CashBox
from src.financials.models import Invoice
from src.financials.models import PersonalAccount
from src.services.models import PaymentDetail


def export_accounts_to_excel(filename="personal_accounts.xlsx"):
    """Export personal accounts to Excel and adjust column widths."""
    accounts = PersonalAccount.objects.select_related(
        "apartment__user", "apartment__house", "apartment__section", "apartment__floor"
    ).all()

    data = []
    for account in accounts:
        apartment = getattr(account, "apartment", None)
        cash_sum = (
            CashBox.objects.filter(personal_account=account).aggregate(
                total=Sum("sum")
            )["total"]
            or 0
        )
        row = {
            "Лицевой счет": account.account_number,
            "Статус": account.status,
            "Дом": apartment.house.title if apartment and apartment.house else "",
            "Секция": apartment.section.name if apartment and apartment.section else "",
            "Квартира": apartment.apartment_number if apartment else "",
            "Владелец": account.user.full_name if account.user else "",
            "Остаток": cash_sum,
        }
        data.append(row)

    df = pd.DataFrame(data)
    df.to_excel(filename, index=False, engine="openpyxl")

    wb = load_workbook(filename)
    ws = wb.active

    for col in ws.columns:
        max_length = max(
            (len(str(cell.value)) for cell in col if cell.value), default=0
        )
        ws.column_dimensions[col[0].column_letter].width = max_length + 2

    wb.save(filename)


def export_cash_box_to_excel(filename="cash.xlsx"):
    """Export cashbox records to Excel and adjust column widths."""
    cash_boxes = CashBox.objects.select_related(
        "personal_account", "payment_articles", "manager", "owner"
    ).filter(owner_id=15)

    data = []
    for cash_box in cash_boxes:
        row = {
            "# ": cash_box.cash_box_number,
            "Дата": cash_box.date,
            "Приход/Расход": cash_box.payment_articles.record_type,
            "Статус": "Проведен" if cash_box.is_conducted else "Не проведен",
            "Статья ": cash_box.payment_articles.name,
            "КвитанцияУслугаСума": cash_box.suma,
            "Валюта": "грн",
            "Владелец": cash_box.owner.full_name if cash_box.owner else "",
            "Лицевой счёт": cash_box.personal_account.account_number
            if cash_box.personal_account
            else "",
            "Сума": cash_box.suma,
        }
        data.append(row)

    df = pd.DataFrame(data)
    df.to_excel(filename, index=False, engine="openpyxl")

    wb = load_workbook(filename)
    ws = wb.active

    for col in ws.columns:
        max_length = max(
            (len(str(cell.value)) for cell in col if cell.value), default=0
        )
        ws.column_dimensions[col[0].column_letter].width = max_length + 2

    wb.save(filename)


class InvoiceTemplate:
    """Store invoice template workbook and worksheet objects."""

    def __init__(self, template_path: str, invoice_obj):
        self._template_path = template_path
        self._invoice_obj = invoice_obj
        self._wb = None
        self._ws = None


def get_invoice_data(invoice_id):
    """Return invoice data merged into a single dictionary."""
    invoice = Invoice.objects.select_related(
        "personal_account__apartment__house", "tariff"
    ).get(id=invoice_id)

    payment_detail = PaymentDetail.objects.first()

    owner_name = (
        invoice.personal_account.user.get_full_name()
        if invoice.personal_account and invoice.personal_account.user
        else ""
    )
    house_address = (
        invoice.personal_account.apartment.house.address
        if invoice.personal_account and invoice.personal_account.apartment
        else ""
    )
    apartment_num = (
        invoice.personal_account.apartment.apartment_number
        if invoice.personal_account and invoice.personal_account.apartment
        else ""
    )
    full_address_line = ", ".join(
        part
        for part in [
            owner_name,
            house_address,
            f"кв. {apartment_num}" if apartment_num else "",
        ]
        if part
    )

    data = {
        "Inv_Number": invoice.invoice_number,
        "Status": invoice.get_status_display(),
        "Inv_Date": invoice.date.strftime("%d.%m.%Y") if invoice.date else "",
        "Inv_Period": f"{invoice.start_date:%d.%m.%Y} - {invoice.end_date:%d.%m.%Y}"
        if invoice.start_date and invoice.end_date
        else "",
        "Проведена": "Проведена" if invoice.conducted else "Не проведена",
        "Владелец": owner_name,
        "Дом": house_address,
        "Квартира": apartment_num,
        "full_address_line": full_address_line,
        "Client_Acc": invoice.personal_account.account_number
        if invoice.personal_account
        else "",
        "Телефон": getattr(invoice.personal_account.user, "phone", "")
        if invoice.personal_account and invoice.personal_account.user
        else "",
        "Секция": (
            invoice.personal_account.apartment.section.name
            if invoice.personal_account
            and invoice.personal_account.apartment
            and invoice.personal_account.apartment.section
            else ""
        ),
        "Payee_Name": payment_detail.description if payment_detail else "",
        "Тариф": invoice.tariff.title if invoice.tariff else "",
    }

    total = Decimal("0")
    for idx, item in enumerate(
        invoice.items.select_related("tariff_service__service", "tariff_service__unit"),
        start=1,
    ):
        service = item.tariff_service
        row = {
            f"Услуга_{idx}": service.service.name
            if service and service.service
            else "",
            f"Количество_{idx}": item.count,
            f"Тариф_{idx}": item.tariff_service.tariff.title,
            f"Ед._изм_{idx}": service.unit.name if service and service.unit else "",
            f"Цена_{idx}": service.price if service else "",
            f"Сумма_{idx}": item.total,
        }
        total += item.total
        data.update(row)

    personal_account_id = (
        invoice.personal_account.id if invoice.personal_account else None
    )
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
            "invoices_total": invoices_total,
            "Оплачено_всего": payments_total,
            "Client_Balance": payments_total - invoices_total,
            "Total_Amount": total,
        }
    )

    return data


def fill_invoice_to_excel(invoice_id=11, template_name="Шаблон Квитанции.xlsm"):
    """Fill invoice data into Excel template and save to file."""
    data = get_invoice_data(invoice_id)

    template_path = (
        Path(settings.BASE_DIR) / "media/templates" / Path(template_name).name
    )
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    wb = load_workbook(template_path, keep_vba=True)
    ws = wb.active

    service_row_idx = None
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and re.search(
                r"\{\{Услуга(_\d+)?\}\}", cell.value
            ):
                service_row_idx = cell.row
                break
        if service_row_idx:
            break

    if service_row_idx is None:
        raise ValueError("Template row with {{Услуга}} not found")

    template_row = [cell.value for cell in ws[service_row_idx]]
    merged_ranges = [r for r in ws.merged_cells.ranges if r.min_row == service_row_idx]

    # Unmerge using contextlib.suppress
    for m in merged_ranges:
        with suppress(KeyError):
            ws.unmerge_cells(str(m))
    ws.delete_rows(service_row_idx, 1)

    thin_border = Border(
        left=Side("thin"), right=Side("thin"), top=Side("thin"), bottom=Side("thin")
    )

    services = sorted(
        [k for k in data if k.startswith("Услуга_")], key=lambda x: int(x.split("_")[1])
    )

    for idx, _ in enumerate(services):
        row_num = service_row_idx + idx
        ws.insert_rows(row_num, 1)
        for col, template_val in enumerate(template_row, start=1):
            cell = ws.cell(row=row_num, column=col)
            cell_value = template_val
            if isinstance(template_val, str):
                new_val = re.sub(
                    r"\{\{([\w\.\-А-Яа-яЁёІіЇїЄє]+)\}\}",
                    lambda m: f"{{{{{m.group(1)}_{idx + 1}}}}}",
                    template_val,
                )
                for key, val in data.items():
                    new_val = new_val.replace(
                        f"{{{{{key}}}}}", str(val) if val is not None else ""
                    )
                cell_value = new_val.strip() or None
            if cell_value is not None:
                cell.value = cell_value
            cell.border = thin_border
        for m in merged_ranges:
            ws.merge_cells(
                start_row=row_num,
                start_column=m.min_col,
                end_row=row_num,
                end_column=m.max_col,
            )

    wb.save(Path(__file__).parent / f"Квитанция_{invoice_id}.xlsm")
    return Path(__file__).parent / f"Квитанция_{invoice_id}.xlsm"


def excel_to_html_openpyxl(xlsx_path, html_path=None, sheet_name=None):
    """Convert Excel sheet to HTML table and save to file."""
    xlsx_path = Path(xlsx_path)
    html_path = html_path or xlsx_path.with_suffix(".html")

    wb = load_workbook(xlsx_path, read_only=False, data_only=True)
    ws = wb[sheet_name] if sheet_name else wb.active

    merged_cells_map = {}
    for merged in ws.merged_cells.ranges:
        min_col, min_row, max_col, max_row = merged.bounds
        rowspan, colspan = max_row - min_row + 1, max_col - min_col + 1
        for r in range(min_row, max_row + 1):
            for c in range(min_col, max_col + 1):
                merged_cells_map[(r, c)] = (
                    (rowspan, colspan) if (r, c) == (min_row, min_col) else None
                )

    rows_html = []
    for r in range(ws.min_row, ws.max_row + 1):
        cells_html = []
        for c in range(ws.min_column, ws.max_column + 1):
            key = (r, c)
            if key in merged_cells_map and merged_cells_map[key] is None:
                continue
            cell = ws.cell(row=r, column=c)
            value = escape(str(cell.value)) if cell.value is not None else ""
            attrs = ""
            if merged_cells_map.get(key):
                rowspan, colspan = merged_cells_map[key]
                if rowspan > 1:
                    attrs += f' rowspan="{rowspan}"'
                if colspan > 1:
                    attrs += f' colspan="{colspan}"'
            style_inline = ""
            try:
                if cell.font and cell.font.bold:
                    style_inline += "font-weight:bold;"
                if style_inline:
                    attrs += f' style="{style_inline}"'
            except Exception:
                pass
            cells_html.append(f"<td{attrs}>{value}</td>")
        rows_html.append("<tr>" + "".join(cells_html) + "</tr>")

    html_table = "<table>\n" + "\n".join(rows_html) + "\n</table>"

    page = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{xlsx_path.name}</title>
<style>
  table {{ border-collapse: collapse; width: 100%; }}
  td {{ border: 1px solid #ddd; padding: 6px; vertical-align: top; }}
</style>
</head>
<body>
{html_table}
</body>
</html>"""

    html_path.open("w", encoding="utf-8").write(page)
    return html_path


def html_to_pdf(html_path, pdf_path=None):
    """Convert HTML file to PDF and save to file."""
    html_path = Path(html_path)
    pdf_path = Path(pdf_path) if pdf_path else html_path.with_suffix(".pdf")
    HTML(str(html_path)).write_pdf(str(pdf_path))
    return pdf_path
