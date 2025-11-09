"""AJAX views for datatables in the core application."""

import logging
from contextlib import suppress
from decimal import Decimal
from decimal import InvalidOperation

from ajax_datatable.views import AjaxDatatableView
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import CharField
from django.db.models import F
from django.db.models import OuterRef
from django.db.models import Q
from django.db.models import Subquery
from django.db.models import Sum
from django.db.models import Value
from django.db.models.functions import Coalesce
from django.db.models.functions import Concat
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils.html import format_html

from src.building.models import Apartment
from src.building.models import House
from src.building.models import Section
from src.financials.models import CashBox
from src.financials.models import Invoice
from src.financials.models import PersonalAccount
from src.services.models import Counter
from src.users.models import Ticket

logger = logging.getLogger(__name__)
User = get_user_model()

MONTHS_RU = [
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
]


class InvoiceBoxListAjax(AjaxDatatableView):
    """AjaxDatatableView for displaying a list of invoices in the admin panel.

    Key features:
    - Filtering by:
    * invoice_number — invoice number
    * date — creation date
    * mount — month
    * status — payment status
    * apartment — apartment
    * owner — account owner
    * total — amount
    - Sorting and pagination
    - Displaying related objects:
    * personal_account__apartment — apartment and house
    * personal_account__user — user (full name or username)
    - The "select" column adds a checkbox for selecting a row
    - The "actions" column generates edit and delete buttons
    - The "mount" column displays the month and year in the format "September 2025"
    - Adds row attributes for DataTables (DT_RowId, row_url)
    """

    model = Invoice

    def get_initial_queryset(self, request):
        """Form a queryset annotated with total_sum and apply filters from GET or POST.

        Filter by invoice_number, date, mount, status, apartment, owner, and total.
        """
        qs = (
            super()
            .get_initial_queryset(request)
            .annotate(total_sum=Sum("items__total"))
        )

        def get_param(key):
            """Return the parameter value from GET or POST."""
            return request.GET.get(key) or request.POST.get(key)

        params = {
            "invoice_number": get_param("invoice_number"),
            "date": get_param("date"),
            "mount": get_param("mount"),
            "status": get_param("status"),
            "apartment": get_param("apartment"),
            "owner": get_param("owner"),
            "total": get_param("total"),
        }

        if params["invoice_number"]:
            qs = qs.filter(invoice_number__icontains=params["invoice_number"])
        if params["date"]:
            qs = qs.filter(date=params["date"])
        if params["mount"]:
            qs = qs.filter(mount=params["mount"])
        if params["status"]:
            qs = qs.filter(status=params["status"])
        if params["apartment"]:
            with suppress(ValueError):
                qs = qs.filter(personal_account__apartment_id=int(params["apartment"]))
        if params["owner"]:
            qs = qs.filter(owner__name__icontains=params["owner"])
        if params["total"]:
            with suppress(ValueError):
                qs = qs.filter(total_sum__gte=float(params["total"]))

        return qs

    column_defs = [
        {
            "name": "select",
            "title": "",
            "orderable": False,
            "searchable": False,
            "className": "text-center",
            "width": "30px",
        },
        {
            "name": "invoice_number",
            "title": "№ счета",
            "orderable": True,
            "searchable": True,
        },
        {
            "name": "status",
            "title": "Статус оплаты",
            "orderable": False,
            "choices": True,
        },
        {"name": "date", "title": "Дата", "orderable": True},
        {"name": "mount", "title": "Месяц", "orderable": True},
        {
            "name": "personal_account__apartment__apartment_number",
            "title": "Квартира",
            "orderable": False,
        },
        {
            "name": "personal_account__user",
            "title": "Пользователь",
            "orderable": False,
            "choices": True,
        },
        {
            "name": "conducted",
            "title": "Проведена",
            "orderable": False,
            "choices": True,
        },
        {"name": "total_sum", "title": "Сумма", "orderable": True},
        {
            "name": "actions",
            "title": "Действия",
            "orderable": False,
            "searchable": False,
            "className": "text-end",
        },
    ]

    def _render_select(self, obj):
        """Render a checkbox to select the row."""
        return format_html(
            '<input type="checkbox" class="row-select" value="{}">', obj.pk
        )

    def _render_conducted(self, obj):
        """Return the transaction status as 'Conducted' or 'Not conducted'."""
        return "Проведена" if obj.conducted else "Не проведена"

    def _render_status(self, obj):
        """Return the display value of the payment status."""
        return obj.get_status_display()

    def _render_mount(self, obj):
        """Return the month and year in 'September 2025' format."""
        if obj.mount:
            month_name = MONTHS_RU[obj.mount.month - 1]
            return f"{month_name} {obj.mount.year}"
        return "-"

    def _render_personal_account_apartment(self, obj):
        """Return the apartment number and the house title."""
        account = getattr(obj, "personal_account", None)
        if account and account.apartment:
            apartment = account.apartment
            house_title = apartment.house.title if apartment.house else "-"
            return f"{apartment.apartment_number} ({house_title})"
        return "-"

    def _render_personal_account_user(self, obj):
        """Return the full name or username of the user."""
        account = getattr(obj, "personal_account", None)
        if account and account.user:
            return account.user.get_full_name() or account.user.username
        return "-"

    def _render_total_sum(self, obj):
        """Return the formatted total sum."""
        return f"{obj.total_sum:,.2f}" if obj.total_sum else "0.00"

    def _render_actions(self, obj):
        """Render edit and delete buttons for the invoice."""
        edit_url = reverse("admin:invoice_update", args=[obj.pk])
        delete_url = reverse("admin:invoice-delete", args=[obj.pk])
        csrf_token = get_token(self.request)
        return format_html(
            '<a class="btn btn-default btn-sm" href="{}" title="Edit">'
            '<i class="fa fa-pencil"></i></a> '
            '<form method="post" action="{}" style="display:inline;">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
            '<button type="submit" class="btn btn-default btn-sm" '
            "onclick=\"return confirm('Are you sure you "
            "want to delete this invoice?');\">"
            '<i class="fa fa-trash"></i>'
            "</button>"
            "</form>",
            edit_url,
            delete_url,
            csrf_token,
        )

    # -------------------------
    # Main render_column method
    # -------------------------

    def render_column(self, obj, column_name):
        """Render the value of a specific column for DataTables."""
        column_map = {
            "select": self._render_select,
            "conducted": self._render_conducted,
            "status": self._render_status,
            "mount": self._render_mount,
            "personal_account__apartment__apartment_number": (
                self._render_personal_account_apartment
            ),
            "personal_account__user": self._render_personal_account_user,
            "total_sum": self._render_total_sum,
            "actions": self._render_actions,
        }

        renderer = column_map.get(column_name)
        if renderer:
            return renderer(obj)
        return super().render_column(obj, column_name)

    def customize_row(self, row, obj):
        """Add additional row attributes to DataTables.

        - DT_RowId: unique row ID
        - row_url: link to the account card
        """
        row["DT_RowId"] = f"row_{obj.pk}"
        row["row_url"] = reverse("admin:invoice_card", args=[obj.pk])
        return row


class CashBoxListAjax(AjaxDatatableView):
    """AjaxDatatableView for displaying and filtering cash register (CashBox)  .

    Key features:
    - Filtering by:
    * cash_box_number — cash register number
    * date — record date
    * is_conducted — whether the record was conducted
    * payment_article — payment item
    * owner — cash register owner
    * record_type — record type (receipt/expense)
    * suma — record amount
    - Sorting and pagination
    - Displaying related objects:
    * owner — owner's full name or email
    * personal_account — personal account
    * payment_articles — payment item name and record type
    - The actions column generates edit and delete buttons
    - Adds row attributes for DataTables (DT_RowId, DT_RowAttr)
    """

    model = CashBox
    initial_order = [["date", "asc"]]
    length_menu = [[50, 100, 200], [50, 100, 200]]

    def get_initial_queryset(self, request=None):
        """Return a basic queryset with filters applied from GET or POST parameters.

        Used for server-side processing of DataTables.

        Logs all applied filters.
        """
        qs = CashBox.objects.prefetch_related(
            "manager", "owner", "personal_account", "payment_articles"
        )

        params = request.GET if request.method == "GET" else request.POST

        # Фильтры
        cash_box_number = params.get("cash_box_number")
        if cash_box_number:
            qs = qs.filter(cash_box_number__icontains=cash_box_number)

        date = params.get("date")
        if date:
            qs = qs.filter(date=date)

        is_conducted = params.get("is_conducted")
        if is_conducted:
            is_conducted_val = is_conducted.lower() in ("true", "1")
            qs = qs.filter(is_conducted=is_conducted_val)

        payment_article = params.get("payment_article")
        if payment_article:
            qs = qs.filter(payment_articles_id=payment_article)

        owner = params.get("owner")
        if owner:
            qs = qs.filter(owner_id=owner)

        record_type = params.get("record_type")
        if record_type:
            qs = qs.filter(payment_articles__record_type=record_type)

        suma = params.get("suma")
        if suma:
            try:
                suma_val = Decimal(suma.replace(",", "."))
                qs = qs.filter(
                    suma__gte=suma_val - Decimal("0.01"),
                    suma__lte=suma_val + Decimal("0.01"),
                )
            except InvalidOperation:
                logger.warning("Invalid suma filter: %s", suma)

        return qs

    column_defs = [
        {
            "name": "cash_box_number",
            "title": "№",
            "orderable": False,
            "searchable": False,
        },
        {"name": "date", "title": "Дата", "orderable": True, "searchable": False},
        {
            "name": "is_conducted",
            "title": "Статус",
            "orderable": False,
            "searchable": False,
        },
        {
            "name": "payment_articles__name",
            "title": "Статья платежа",
            "orderable": False,
            "searchable": False,
        },
        {
            "name": "payment_articles__record_type",
            "title": "Тип (приход/расход)",
            "orderable": False,
            "searchable": False,
        },
        {
            "name": "owner_full_name",
            "title": "ФИО владельца",
            "searchable": False,
            "orderable": False,
        },
        {
            "name": "personal_account__account_number",
            "title": "Лицевой счёт",
            "orderable": False,
            "searchable": False,
        },
        {"name": "suma", "title": "Сумма", "orderable": False, "searchable": False},
        {
            "name": "comment",
            "title": "Комментарий",
            "orderable": False,
            "searchable": False,
        },
        {
            "name": "actions",
            "title": "Действия",
            "searchable": False,
            "orderable": False,
            "className": "text-end",
        },
    ]

    def render_column(self, obj, column_name):
        """Render the value of a specific column for display in DataTables.

        Handle columns such as owner name, account number, payment articles,
        conduction status, and actions (edit/delete). Return formatted HTML
        or text for the table row.

        Args:
            obj (Invoice): The model instance for the current row.
            column_name (str): The name of the column to render.

        Returns:
            str: Formatted HTML or text for the column.

        """

        def owner_full_name(o):
            """Return the owner's full name or email."""
            return o.owner.full_name or o.owner.email if o.owner else "-"

        def personal_account_account_number(o):
            """Return the personal account number."""
            return o.personal_account.account_number if o.personal_account else "-"

        def payment_articles_name(o):
            """Return the payment article's name."""
            return o.payment_articles.name

        def payment_articles_record_type(o):
            """Return the display value of the payment article's record type."""
            return o.payment_articles.get_record_type_display()

        def is_conducted(o):
            """Return 'Conducted' if conducted, otherwise 'Not conducted'."""
            return "Проведен" if o.is_conducted else "Не проведен"

        def actions(o):
            """Generate HTML for edit and delete action buttons."""
            if o.payment_articles.record_type == "in":
                edit_url = reverse("admin:update_receipt_statement", args=[o.pk])
            elif o.payment_articles.record_type == "out":
                edit_url = reverse("admin:update_expense_report", args=[o.pk])
            else:
                edit_url = "#"
            delete_url = reverse("admin:cashbox_delete", args=[o.pk])
            csrf_token = get_token(self.request)
            return format_html(
                '<a class="btn btn-default btn-sm" href="{}" '
                'title="Редактировать">'
                '<i class="fa fa-pencil"></i></a> '
                '<form method="post" action="{}" style="display:inline;">'
                '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
                '<button type="submit" class="btn btn-default btn-sm" '
                "onclick=\"return confirm('Вы уверены, что "
                "хотите удалить этот элемент?');\">"
                '<i class="fa fa-trash"></i></button></form>',
                edit_url,
                delete_url,
                csrf_token,
            )

        # Map column names to handler functions
        handlers = {
            "owner_full_name": owner_full_name,
            "personal_account__account_number": personal_account_account_number,
            "payment_articles__name": payment_articles_name,
            "payment_articles__record_type": payment_articles_record_type,
            "is_conducted": is_conducted,
            "actions": actions,
        }

        # Render the column using the corresponding handler
        if column_name in handlers:
            return handlers[column_name](obj)

        # Fallback to the parent method for unhandled columns
        return super().render_column(obj, column_name)

    def customize_row(self, row, obj):
        """Add additional row attributes to DataTables."""
        row["id"] = obj.pk
        row["pk"] = obj.pk
        row["row_url"] = reverse("admin:cashbox_card", args=[obj.pk])
        row["DT_RowId"] = f"row_{obj.pk}"
        row["DT_RowAttr"] = {"data-row-url": row["row_url"]}
        return row

    def get_filter_queryset(self, request, qs):
        """Save the IDs of all records after applying filters and sorting for."""
        super().get_filter_queryset(request, qs)
        self.filtered_ids = list(qs.values_list("id", flat=True))
        return qs

    def get_response(self, *args, **kwargs):
        """Add an `all_ids` field to the JSON of all records after filtering."""
        response = super().get_response(*args, **kwargs)
        response["all_ids"] = self.filtered_ids
        return response


class TicketListAjax(AjaxDatatableView):
    """AjaxDatatableView for displaying and filtering the ticket list  .

    Allows:
    - Filtering by parameters:
    * role (handler type)
    * worker (assigned handler)
    * status (ticket status)
    * owner (user owner)
    * user_full_name (user full name)
    * phone (user phone number)
    * comment (ticket description)
    * user_apartments (apartment number)
    * time_from (ticket time from)
    - Supports sorting and pagination
    - Generates dynamic HTML links for columns:
    * user_apartments — link to the apartment page
    * worker — link to the handyman page
    * user_full_name — link to the user page
    * actions — edit and delete buttons
    - Adds additional row attributes (DT_RowId, DT_RowAttr)
    for correct operation of DataTables.
    """

    model = Ticket
    initial_order = [["time", "asc"]]
    length_menu = [[50, 100, 200], [50, 100, 200]]

    def get_initial_queryset(self, request=None):
        """Return the base queryset with filters applied from GET or POST parameters.

        Used for server-side processing in DataTables.
        """
        params = request.GET if request.method == "GET" else request.POST
        qs = Ticket.objects.select_related("worker", "role").all()

        applied_filters = {}
        role = request.POST.get("role") or request.GET.get("role")

        if role:
            qs = qs.filter(role_id=role)

        if params.get("worker"):
            qs = qs.filter(worker_id=params["worker"])
            applied_filters["worker_id"] = params["worker"]

        if params.get("status"):
            qs = qs.filter(status=params["status"])
            applied_filters["status"] = params["status"]

        if params.get("owner"):
            qs = qs.filter(user__id=params["owner"])
            applied_filters["owner"] = params["owner"]

        if params.get("user_full_name"):
            value = params["user_full_name"].strip()
            qs = qs.filter(user__full_name__icontains=value)
            applied_filters["user_full_name"] = value

        if params.get("phone"):
            value = params["phone"].strip()
            qs = qs.filter(user__phone__icontains=value)
            applied_filters["phone"] = value

        if params.get("comment"):
            value = params["comment"].strip()
            qs = qs.filter(comment__icontains=value)
            applied_filters["comment"] = value

        if params.get("user_apartments"):
            value = params["user_apartments"].strip()
            qs = qs.filter(user__apartments__apartment_number__icontains=value)
            applied_filters["user_apartments"] = value

        if params.get("time_from"):
            qs = qs.filter(time__gte=params["time_from"])
            applied_filters["time_from"] = params["time_from"]

        return qs

    column_defs = [
        {"name": "id", "title": "№ заявки", "orderable": True, "searchable": False},
        {
            "name": "time",
            "title": "Удобное время",
            "orderable": True,
            "searchable": False,
        },
        {
            "name": "role",
            "title": "Тип мастера",
            "orderable": False,
            "searchable": False,
        },
        {
            "name": "comment",
            "title": "Описание",
            "orderable": False,
            "searchable": False,
        },
        {
            "name": "user_apartments",
            "title": "Квартира / Дом",
            "orderable": False,
            "searchable": False,
        },
        {
            "name": "user_full_name",
            "title": "ФИО",
            "searchable": False,
            "orderable": False,
        },
        {"name": "phone", "title": "Телефон", "searchable": False, "orderable": False},
        {"name": "worker", "title": "Мастер", "searchable": False, "orderable": False},
        {"name": "status", "title": "Статус", "searchable": False, "orderable": False},
        {
            "name": "actions",
            "title": "Действия",
            "searchable": False,
            "orderable": False,
            "className": "text-end",
        },
    ]

    def render_column(self, obj, column_name):
        """Return the base queryset with filters applied from GET or POST parameters.

        Used for server-side processing in DataTables.
        """
        if column_name == "user_apartments":
            apartments = obj.user.apartments.select_related("house").all()
            links = [
                format_html(
                    '<a href="{}">кв. {} - {}</a>',
                    reverse("admin:card_flat", args=[apt.pk]),
                    apt.apartment_number,
                    apt.house.title,
                )
                for apt in apartments
            ]
            return format_html(", ".join(links))

        if column_name == "worker":
            if obj.worker:
                url = reverse("admin:card_staff", args=[obj.worker.pk])
                full_name = (
                    f"{obj.worker.first_name} {obj.worker.last_name}".strip()
                    or obj.worker.email
                )
                return format_html('<a href="{}">{}</a>', url, full_name)
            return "-"

        if column_name == "user_full_name":
            url = reverse("admin:card_user", args=[obj.pk])
            full_name = (
                f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
            )
            return format_html('<a href="{}">{}</a>', url, full_name)

        if column_name == "actions":
            edit_url = reverse("admin:edit_ticket", args=[obj.pk])
            delete_url = reverse("admin:delete_flat", args=[obj.pk])
            csrf_token = get_token(self.request)
            return format_html(
                '<a class="btn btn-default btn-sm" href="{}" '
                'title="Редактировать">'
                '<i class="fa fa-pencil"></i></a> '
                '<form method="post" action="{}" style="display:inline;">'
                '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
                '<button type="submit" class="btn btn-default btn-sm" '
                'onclick="return confirm'
                "('Вы уверены, что хотите удалить этот элемент?');\">"
                '<i class="fa fa-trash"></i>'
                "</button>"
                "</form>",
                edit_url,
                delete_url,
                csrf_token,
            )

        return super().render_column(obj, column_name)

    def customize_row(self, row, obj):
        """Add additional row attributes to DataTables.

        - DT_RowId: unique row ID
        - DT_RowAttr: clickable link
        """
        row["pk"] = obj.pk
        row["row_url"] = reverse("admin:card_task", args=[obj.pk])
        row["DT_RowId"] = f"row_{obj.pk}"
        row["DT_RowAttr"] = {"data-row-url": row["row_url"]}
        return row


class PersonalAccountList(AjaxDatatableView):
    """Ajax DataTable view for displaying the list of tenants' personal accounts.

    Supports filtering, annotating related data (house, section, apartment, user),
    and computing the current balance for each account (based on paid and unpaid  ).
    """

    model = PersonalAccount
    length_menu = [[50], [50]]

    def get_initial_queryset(self, request=None):
        """Return the initial QuerySet of personal accounts with filters and .

        Annotations add related data:
        - `apartment_number` — apartment number;
        - `house_title` — house name;
        - `house_section` — section name;
        - `full_name` — user's full name.

        Supported filters:
        - account_number — account number;
        - status — account status;
        - apartment_number — filter by apartment ID;
        - house_title — filter by house ID;
        - house_section — filter by section ID;
        - full_name — filter by user ID.
        """
        request = self.request
        qs = self.model.objects.all()

        qs = qs.annotate(
            apartment_number=Subquery(
                Apartment.objects.filter(account=OuterRef("pk")).values_list(
                    "apartment_number", flat=True
                )[:1]
            ),
            house_title=Subquery(
                Apartment.objects.filter(account=OuterRef("pk"))
                .select_related("house")
                .values_list("house__title", flat=True)[:1]
            ),
            house_section=Subquery(
                Apartment.objects.filter(account=OuterRef("pk"))
                .select_related("section")
                .values_list("section__name", flat=True)[:1]
            ),
            full_name=Subquery(
                User.objects.filter(pk=OuterRef("user_id"))
                .annotate(
                    full_name=Concat(
                        Coalesce(F("last_name"), Value("")),
                        Value(" "),
                        Coalesce(F("first_name"), Value("")),
                        Value(" "),
                        Coalesce(F("second_name"), Value("")),
                        output_field=CharField(),
                    )
                )
                .values_list("full_name", flat=True)[:1]
            ),
        )

        filters = {
            "account_number": request.POST.get("account_number")
            or request.GET.get("account_number"),
            "status": request.POST.get("status") or request.GET.get("status"),
            "apartment_number": request.POST.get("apartment_number")
            or request.GET.get("apartment_number"),
            "house_title": request.POST.get("house_title")
            or request.GET.get("house_title"),
            "house_section": request.POST.get("house_section")
            or request.GET.get("house_section"),
            "full_name": request.POST.get("full_name") or request.GET.get("full_name"),
        }

        if filters["account_number"]:
            qs = qs.filter(account_number__icontains=filters["account_number"])
        if filters["status"]:
            qs = qs.filter(status=filters["status"])
        if filters["apartment_number"]:
            qs = qs.filter(apartment__id=filters["apartment_number"])
        if filters["house_title"]:
            qs = qs.filter(apartment__house_id=filters["house_title"])
        if filters["house_section"]:
            qs = qs.filter(apartment__section_id=filters["house_section"])
        if filters["full_name"]:
            qs = qs.filter(user_id=filters["full_name"])

        return qs

    column_defs = [
        {
            "name": "account_number",
            "title": "№",
            "searchable": False,
            "orderable": False,
        },
        {"name": "status", "title": "Статус", "searchable": False},
        {
            "name": "apartment_number",
            "title": "Квартира",
            "searchable": False,
            "orderable": False,
        },
        {
            "name": "house_title",
            "title": "Дом",
            "searchable": False,
            "orderable": False,
        },
        {
            "name": "house_section",
            "title": "Секция",
            "searchable": False,
            "orderable": False,
        },
        {
            "name": "full_name",
            "title": "Пользователь",
            "searchable": False,
            "orderable": False,
        },
        {
            "name": "cashbox_sum",
            "title": "Баланс",
            "searchable": False,
            "orderable": False,
        },
        {
            "name": "actions",
            "title": "Действия",
            "searchable": False,
            "orderable": False,
            "className": "text-end",
        },
    ]

    def render_apartment_number(self, record, **kwargs):
        """Return the apartment number for the table row or '-' if not found."""
        return getattr(record, "apartment_number", "-")

    def render_house_title(self, record, **kwargs):
        """Return the house name for the table row or '-' if missing."""
        return getattr(record, "house_title", "-")

    def render_house_section(self, record, **kwargs):
        """Return the house name for the table row or '-' if missing."""
        return getattr(record, "house_section", "-")

    def render_full_name(self, record, **kwargs):
        """Return the user's full name or '-' if not provided."""
        return getattr(record, "full_name", "-") or "-"

    def customize_row(self, row, obj):
        """Add additional data to a table row, including the balance.

        Calculate the balance as:
        - Total paid invoices (status='new').
        - Total unpaid or partially paid invoices (status='zero' or 'counted').
        - Balance = paid - unpaid.

        Add the following fields to the row:
        - `user`: User full name or placeholder if not set.
        - `cashbox_sum`: Calculated balance (0.00 on error).
        - `id`: Record ID.
        """
        row["user"] = (
            getattr(obj.user, "full_name", "(не задано)") if obj.user else "(не задано)"
        )

        try:
            paid_total = Invoice.objects.filter(
                personal_account_id=obj.id,
                conducted=True,
                status__in=["new"],
            ).aggregate(total=Sum("items__total"))["total"]

            unpaid_total = Invoice.objects.filter(
                personal_account_id=obj.id,
                conducted=True,
                status__in=["zero", "counted"],
            ).aggregate(total=Sum("items__total"))["total"]

            paid_total = paid_total or Decimal("0.00")
            unpaid_total = unpaid_total or Decimal("0.00")

            balance = round(float(paid_total - unpaid_total), 2)
            row["cashbox_sum"] = balance

        except (TypeError, ValueError, Decimal.InvalidOperation) as e:
            logger.warning(
                "Error calculating balance for personal_account_id=%s: %s", obj.id, e
            )
            row["cashbox_sum"] = 0.00

        row["id"] = obj.id
        return row

    def render_column(self, obj, column_name):
        """Render the contents of a table column.

        - Return HTML action buttons (edit/delete) with a CSRF token and confirmation
          for the `actions` column.

        Args:
            obj (Model): The model instance for the current row.
            column_name (str): The name of the column to render.

        Returns:
            str: Formatted HTML or text for the column.

        """
        if column_name == "actions":
            edit_url = reverse("admin:update_account", args=[obj.pk])
            delete_url = reverse("admin:delete_account", args=[obj.pk])
            csrf_token = get_token(self.request)
            return format_html(
                '<a class="btn btn-default btn-sm" href="{}">'
                '<i class="fa fa-pencil"></i></a>'
                '<form method="post" action="{}" style="display:inline;">'
                '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
                '<button type="submit" class="btn btn-default btn-sm" '
                "onclick=\"return confirm('Вы уверены?');\">"
                '<i class="fa fa-trash"></i></button></form>',
                edit_url,
                delete_url,
                csrf_token,
            )

        return super().render_column(obj, column_name)

    def render_to_response(self, context, **response_kwargs):
        """Return a JSON response for DataTables with the correct Content-Type header.

        Set the content type to `application/json; charset=utf-8`  processing.

        Args:
            context (dict): The data context to serialize.
            **response_kwargs: Additional parameters for the HTTP response.

        Returns:
            HttpResponse: Response with JSON content and correct Content-Type.

        """
        response_kwargs.setdefault("content_type", "application/json; charset=utf-8")
        return super().render_to_response(context, **response_kwargs)


class OwnerAjaxDatetableView(AjaxDatatableView):
    """A view for displaying a list of users (owners) in Ajax DataTable format.

    Displays users, filters them by various parameters (name, phone number, email,
     house, apartment, status, etc.) and returns the result in JSON format
     for dynamically updating the table in the admin panel.
    """

    model = User
    initial_order = [["email", "asc"]]
    length_menu = [[50], [50]]

    column_defs = [
        {"name": "user_id", "title": "ID", "searchable": False, "orderable": False},
        {
            "name": "full_name",
            "title": "Пользователь",
            "searchable": False,
            "orderable": False,
        },
        {"name": "phone", "title": "Телефон", "searchable": False},
        {"name": "email", "title": "Email (логин)", "searchable": False},
        {
            "name": "house_title",
            "title": "Дом",
            "searchable": False,
            "orderable": False,
        },
        {
            "name": "apartment_number",
            "title": "Квартира",
            "searchable": False,
            "orderable": False,
        },
        {"name": "date_joined", "title": "Дата добавления", "searchable": False},
        {
            "name": "status",
            "title": "Статус",
            "searchable": False,
            "choices": (("work", "Активный"), ("done", "Отключен"), ("new", "Новый")),
        },
        {
            "name": "actions",
            "title": "Действия",
            "searchable": False,
            "orderable": False,
            "className": "text-end",
        },
        {"name": "row_url", "visible": False, "searchable": False, "orderable": False},
    ]

    def get_initial_queryset(self, request=None):
        """Return the original QuerySet of users with applied filters.

        Apply filters based on the following parameters:
        - user_id
        - full_name (search by first, last, or middle name)
        - phone
        - email
        - house (house ID)
        - apartment (apartment number)
        - date_added (registration date)
        - status (user status)

        Annotate the QuerySet with `house_title` and `apartment_number` for display.

        Args:
            request (HttpRequest, optional): Incoming request to read filter parameters.

        Returns:
            QuerySet: Filtered and annotated set of users.

        """
        qs = self.model.objects.filter(is_staff=False)

        params = request.GET if request.method == "GET" else request.POST

        if params.get("user_id"):
            qs = qs.filter(user_id=params.get("user_id"))

        if params.get("full_name"):
            qs = qs.filter(
                models.Q(first_name__icontains=params.get("full_name"))
                | models.Q(last_name__icontains=params.get("full_name"))
                | models.Q(second_name__icontains=params.get("full_name"))
            )

        if params.get("phone"):
            qs = qs.filter(phone__icontains=params.get("phone"))

        if params.get("email"):
            qs = qs.filter(email__icontains=params.get("email"))

        if params.get("house"):
            qs = qs.filter(apartment__house_id=params.get("house"))

        if params.get("apartment"):
            qs = qs.filter(
                apartment__apartment_number__icontains=params.get("apartment")
            )

        if params.get("date_added"):
            qs = qs.filter(date_joined__date=params.get("date_added"))

        if params.get("status"):
            qs = qs.filter(status=params.get("status"))

        return qs.annotate(
            house_title=Subquery(
                Apartment.objects.filter(user=OuterRef("pk"))
                .select_related("house")
                .values("house__title")[:1]
            ),
            apartment_number=Subquery(
                Apartment.objects.filter(user=OuterRef("pk")).values(
                    "apartment_number"
                )[:1]
            ),
        )

    def render_column(self, row, column):
        """Process and format the contents of individual table columns.

        - Add a visual label with color for the `status` column.
        - Create action buttons for the `actions` column, such as message or edit.

        Args:
            row (User): The User instance for the current row.
            column (str): The name of the column to render.

        Returns:
            str: Formatted HTML or text for the column.

        """
        if column == "status":
            if row.status == "new":
                return format_html('<span class="label label-warning">Новый</span>')
            if row.status == "work":
                return format_html('<span class="label label-success">Активный</span>')
            if row.status == "done":
                return format_html('<span class="label label-danger">Отключен</span>')
            return ""

        if column == "actions":
            message_url = reverse("admin:user_send_message", args=[row.pk])
            update_url = reverse("admin:owner_update", args=[row.pk])
            delete_url = reverse("admin:user_delete", args=[row.pk])
            return format_html(
                """
                <div class="btn-group pull-right">
                    <a class="btn btn-default btn-sm"
                       href="{}"
                       title="Отправить сообщение" data-toggle="tooltip">
                        <i class="fa fa-envelope"></i>
                    </a>
                    <a class="btn btn-default btn-sm" href="{}"
                       title="Редактировать" data-toggle="tooltip">
                        <i class="fa fa-pencil"></i>
                    </a>
                    <a class="btn btn-default btn-sm" href="{}"
                       title="Удалить" data-toggle="tooltip"
                       data-method="post"
                       data-confirm="Вы уверены, что хотите удалить этот элемент?">
                        <i class="fa fa-trash"></i>
                    </a>
                </div>
                """,
                message_url,
                update_url,
                delete_url,
            )

        return super().render_column(row, column)

    def customize_row(self, row, obj):
        """Add additional data to a table row.

        - Set `DT_RowId` for DataTables to identify the row.
        - Set `row_url` as a link to the user's card.

        Args:
            row (dict): Table row data.
            obj (User): The User instance for the current row.

        Returns:
            dict: Updated row data with additional attributes.

        """
        row["DT_RowId"] = f"row-{obj.pk}"
        row["row_url"] = reverse("admin:card_user", args=[obj.pk])

    def render_to_response(self, context, **response_kwargs):
        """Return a JSON response with the correct Content-Type header.

        Set `application/json; charset=utf-8` to ensure proper DataTables operation.

        Args:
            context (dict): The data context to serialize.
            **response_kwargs: Additional parameters for the HTTP response.

        Returns:
            HttpResponse: Response with JSON content and the correct Content-  header.

        """
        response_kwargs.setdefault("content_type", "application/json; charset=utf-8")
        return super().render_to_response(context, **response_kwargs)


class InvoiceCounterAjax(AjaxDatatableView):
    """AJAX submission for displaying healthcare related to patients.

    Vikorist is used to filter and filter data from the DataTables table.
    Maintains filtering for apartment (`flat_id`), booth, section, service,
    by indications and by one vimiryuvannya.
    """

    model = Counter
    length_menu = [[50, 100, 200], [50, 100, 200]]
    search_values_separator = "+"

    column_defs = [
        {
            "name": "counter_number",
            "title": "№",
            "orderable": True,
            "searchable": False,
        },
        {"name": "status", "title": "Статус", "orderable": True, "searchable": False},
        {"name": "date", "title": "Дата", "orderable": True, "searchable": False},
        {
            "name": "month_year",
            "title": "Месяц/Год",
            "orderable": False,
            "searchable": False,
        },
        {
            "name": "house",
            "title": "Дом",
            "foreign_field": "apartment__house__title",
            "orderable": True,
            "searchable": False,
        },
        {
            "name": "section",
            "title": "Секция",
            "foreign_field": "apartment__section__name",
            "orderable": True,
            "searchable": False,
        },
        {
            "name": "apartment_number",
            "title": "№ квартиры",
            "foreign_field": "apartment__apartment_number",
            "orderable": True,
            "searchable": False,
        },
        {
            "name": "service",
            "title": "Счетчик",
            "foreign_field": "service__name",
            "orderable": True,
            "searchable": False,
        },
        {
            "name": "meter_reading",
            "title": "Показания",
            "orderable": True,
            "searchable": False,
        },
        {
            "name": "service_unit",
            "title": "Единица изменения",
            "foreign_field": "service__unit__name",
            "orderable": False,
            "searchable": False,
        },
        {
            "name": "actions",
            "title": "Действия",
            "orderable": False,
            "searchable": False,
            "className": "text-end",
        },
    ]

    @staticmethod
    def with_suppress(func):
        """Suppress ValueError raised by the given function."""
        with suppress(ValueError):
            return func()
        return None

    def get_initial_queryset(self, request=None):
        """Form a filtered set of Counter objects for DataTables.

        Args:
            request (HttpRequest, optional): Incoming request.

        Returns:
            QuerySet: Filtered set of Counter objects.

        """
        queryset = super().get_initial_queryset(request)
        params = request.GET.copy()
        params.update(request.POST)

        # Словарь фильтров: ключ — имя параметра, значение — функция фильтрации
        filters = {
            "flat_id": lambda qs, v: self.with_suppress(
                lambda: qs.filter(apartment_id=int(v))
            ),
            "house": lambda qs, v: self.with_suppress(
                lambda: qs.filter(apartment__house_id=int(v))
            ),
            "section": lambda qs, v: self.with_suppress(
                lambda: qs.filter(apartment__section_id=int(v))
            ),
            "apartment_number": lambda qs, v: qs.filter(apartment__apartment_number=v),
            "service": lambda qs, v: qs.filter(service_id=int(v))
            if str(v).isdigit()
            else qs,
            "meter_reading": lambda qs, v: self.with_suppress(
                lambda: qs.filter(meter_reading=float(v))
            ),
            "service_unit": lambda qs, v: qs.filter(service__unit__name__icontains=v),
        }

        for param, func in filters.items():
            value = params.get(param)
            if value not in (None, ""):
                queryset = func(queryset, value)

        return queryset

    def render_column(self, obj, column_name):
        """Format the value of a specific column for display in DataTables.

        Use handlers for columns such as month/year, house, section, apartment number,
        service, service unit, and actions.

        Args:
            obj (Counter): The Counter model instance for the current row.
            column_name (str): The name of the column to format.

        Returns:
            str: Formatted HTML or text for rendering in the table.

        """

        def month_year(r):
            """Return the month/year string for the Counter's date."""
            return r.date.strftime("%m/%Y") if r.date else ""

        def house(r):
            """Return the house title of the associated apartment."""
            return (
                r.apartment.house.title if (r.apartment and r.apartment.house) else ""
            )

        def section(r):
            """Return the section name of the associated apartment."""
            return (
                r.apartment.section.name if r.apartment and r.apartment.section else ""
            )

        def apartment_number(r):
            """Return the apartment number of the associated apartment."""
            return r.apartment.apartment_number if r.apartment else ""

        def service(r):
            """Return the name of the associated service."""
            return r.service.name if r.service else ""

        def service_unit(r):
            """Return the unit name of the associated service."""
            return r.service.unit.name if r.service and r.service.unit else ""

        def actions(r):
            """Return HTML action buttons for editing and deleting the Counter."""
            edit_url = reverse("admin:update_flat", args=[r.pk])
            delete_url = reverse("admin:delete_flat", args=[r.pk])
            csrf_token = get_token(self.request)
            return format_html(
                '<a class="btn btn-default btn-sm" href="{}">'
                '<i class="fa fa-pencil"></i></a>'
                '<form method="post" action="{}" style="display:inline;">'
                '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
                '<button type="submit" class="btn btn-default btn-sm" '
                "onclick=\"return confirm('Вы уверены?');\">"
                '<i class="fa fa-trash"></i></button></form>',
                edit_url,
                delete_url,
                csrf_token,
            )

        handlers = {
            "month_year": month_year,
            "house": house,
            "section": section,
            "apartment_number": apartment_number,
            "service": service,
            "service_unit": service_unit,
            "actions": actions,
        }

        if column_name in handlers:
            return handlers[column_name](obj)

        return super().render_column(obj, column_name)


class CounterAjax(AjaxDatatableView):
    """AJAX view for displaying patient data in the DataTables table.

    Maintains filtering for booth, section, apartment, service, displays
    and some vimiryuvannya. Data is collected asynchronously via DataTables
    With the support of pagination and dynamic generation of HTML for the activity.
    """

    model = Counter
    length_menu = [[50, 100, 200], [50, 100, 200]]
    search_values_separator = "+"

    column_defs = [
        {
            "name": "counter_number",
            "title": "№",
            "orderable": True,
            "searchable": False,
        },
        {"name": "status", "title": "Статус", "orderable": True, "searchable": False},
        {"name": "date", "title": "Дата", "orderable": True, "searchable": False},
        {
            "name": "month_year",
            "title": "Месяц/Год",
            "orderable": False,
            "searchable": False,
        },
        {
            "name": "house",
            "title": "Дом",
            "foreign_field": "apartment__house__title",
            "orderable": True,
            "searchable": False,
        },
        {
            "name": "section",
            "title": "Секция",
            "foreign_field": "apartment__section__name",
            "orderable": True,
            "searchable": False,
        },
        {
            "name": "apartment_number",
            "title": "№ квартиры",
            "foreign_field": "apartment__apartment_number",
            "orderable": True,
            "searchable": False,
        },
        {
            "name": "service",
            "title": "Счетчик",
            "foreign_field": "service__name",
            "orderable": True,
            "searchable": False,
        },
        {
            "name": "meter_reading",
            "title": "Показания",
            "orderable": True,
            "searchable": False,
        },
        {
            "name": "service_unit",
            "title": "Единица изменения",
            "foreign_field": "service__unit__name",
            "orderable": False,
            "searchable": False,
        },
        {
            "name": "actions",
            "title": "Действия",
            "orderable": False,
            "searchable": False,
            "className": "text-end",
        },
    ]

    @staticmethod
    def with_suppress(func):
        """Suppress ValueError raised by the given function."""
        with suppress(ValueError):
            return func()
        return None

    def get_initial_queryset(self, request=None):
        """Form a filtered QuerySet for DataTables based on transmitted parameters."""
        queryset = super().get_initial_queryset(request)
        params = request.GET.copy()
        params.update(request.POST)

        filters = {
            "apartment_id": lambda qs, v: self.with_suppress(
                lambda: qs.filter(apartment_id=int(v))
            ),
            "house": lambda qs, v: self.with_suppress(
                lambda: qs.filter(apartment__house_id=int(v))
            ),
            "section": lambda qs, v: self.with_suppress(
                lambda: qs.filter(apartment__section_id=int(v))
            ),
            "apartment_number": lambda qs, v: qs.filter(apartment__apartment_number=v),
            "service": lambda qs, v: qs.filter(service_id=int(v))
            if str(v).isdigit()
            else qs,
            "meter_reading": lambda qs, v: self.with_suppress(
                lambda: qs.filter(meter_reading=float(v))
            ),
            "service_unit": lambda qs, v: qs.filter(service__unit__name__icontains=v),
        }

        for param, func in filters.items():
            value = params.get(param)
            if value not in (None, ""):
                queryset = func(queryset, value)

        return queryset

    def render_column(self, obj, column_name):
        """Render the value for a specific column in the table."""

        def month_year(r):
            return r.date.strftime("%m/%Y") if r.date else ""

        def house(r):
            return r.apartment.house.title if r.apartment and r.apartment.house else ""

        def section(r):
            return (
                r.apartment.section.name if r.apartment and r.apartment.section else ""
            )

        def apartment_number(r):
            return r.apartment.apartment_number if r.apartment else ""

        def service(r):
            return r.service.name if r.service else ""

        def service_unit(r):
            return r.service.unit.name if r.service and r.service.unit else ""

        def actions(r):
            edit_url = reverse("admin:counters_update", args=[r.pk])
            delete_url = reverse("admin:delete_flat", args=[r.pk])
            csrf_token = get_token(self.request)
            return format_html(
                '<a class="btn btn-default btn-sm" href="{}">'
                '<i class="fa fa-pencil"></i></a>'
                '<form method="post" action="{}" style="display:inline;">'
                '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
                '<button type="submit" class="btn btn-default btn-sm" '
                "onclick=\"return confirm('Вы уверены?');\">"
                '<i class="fa fa-trash"></i></button></form>',
                edit_url,
                delete_url,
                csrf_token,
            )

        handlers = {
            "month_year": month_year,
            "house": house,
            "section": section,
            "apartment_number": apartment_number,
            "service": service,
            "service_unit": service_unit,
            "actions": actions,
        }

        handler = handlers.get(column_name)
        if handler:
            return handler(obj)

        return super().render_column(obj, column_name)

    def customize_row(self, row, obj):
        """Add additional HTML attributes and service data to each row of the table.

        Args:
            row (dict): Dictionary of data for the current row.
            obj (Counter): The Counter model object representing this row.

        Returns:
            dict: Updated data dictionary with additional attributes.

        """
        row["DT_RowId"] = f"row_{obj.pk}"
        row["DT_RowAttr"] = {"data-counter-id": obj.pk}
        row["row_number"] = (
            int(self.request.GET.get("start", 0)) + getattr(self, "_index", 0) + 1
        )
        self._index = getattr(self, "_index", 0) + 1
        return row


class CounteerListAjax(AjaxDatatableView):
    """AJAX-view for displaying doctors (Counter) in DataTables.

    Ensures filtration, sorting and dynamic forming of actions
    (revisiting history, taking new evidence) for a skin healer.
    """

    model = Counter
    length_menu = [[50, 100, 200], [50, 100, 200]]
    initial_order = [["apartment__apartment_number", "desc"]]

    column_defs = [
        {
            "name": "house",
            "title": "Дом",
            "foreign_field": "apartment__house__title",
            "orderable": True,
            "searchable": False,
        },
        {
            "name": "section",
            "title": "Секция",
            "foreign_field": "apartment__section__name",
            "orderable": True,
            "searchable": False,
        },
        {
            "name": "apartment_number",
            "title": "№ квартиры",
            "foreign_field": "apartment__apartment_number",
            "orderable": True,
            "searchable": False,
        },
        {
            "name": "service",
            "title": "Счетчик",
            "foreign_field": "service__name",
            "orderable": True,
            "searchable": False,
        },
        {
            "name": "meter_reading",
            "title": "Показания",
            "orderable": True,
            "searchable": False,
        },
        {
            "name": "service_unit",
            "title": "Единица изменения",
            "foreign_field": "service__unit__name",
            "searchable": True,
            "orderable": False,
        },
        {
            "name": "actions",
            "title": "Действия",
            "searchable": False,
            "orderable": False,
            "className": "text-end",
        },
    ]

    def get_initial_queryset(self, request=None):
        """Generate and return a queryset of doctors with filters and sorting.

        Supports filtering for:
            - house (`house`)
            - section (`section`)
            - apartment number (`apartment_number`)
            - service (`service`)

        Sorting parameters are also applied as passed from DataTables.

        Args:
            request (HttpRequest, optional): Streaming HTTP request.

        Returns:
            QuerySet: Filtered and sorted set of Counter objects.

        Raises:
            PermissionDenied: If the user is not authenticated.

        """
        if not request.user.is_authenticated:
            raise PermissionDenied

        params = request.GET if request.method == "GET" else request.POST

        queryset = self.model.objects.select_related(
            "service",
            "service__unit",
            "apartment",
            "apartment__house",
            "apartment__section",
        )

        # --- Фільтри ---
        house_id = params.get("house")
        if house_id:
            queryset = queryset.filter(apartment__house_id=house_id)

        section_id = params.get("section")
        if section_id:
            queryset = queryset.filter(apartment__section_id=section_id)

        apartment_number = params.get("apartment_number")
        if apartment_number:
            queryset = queryset.filter(apartment__apartment_number=apartment_number)

        service_id = params.get("service")
        if service_id:
            queryset = queryset.filter(service_id=service_id)

        # --- Сортування ---
        order_col = params.get("order[0][column]")
        order_dir = params.get("order[0][dir]", "asc")

        columns_map = {
            0: "counter_number",
            1: "status",
            2: "date",
            3: "date",
            4: "apartment__house__title",
            5: "apartment__section__name",
            6: "apartment__apartment_number",
            7: "service__name",
            8: "meter_reading",
            9: "service__unit__name",
        }

        order_field = "apartment__apartment_number"
        if order_col is not None:
            try:
                order_col = int(order_col)
                order_field = columns_map.get(order_col, "apartment__apartment_number")
                if order_dir == "desc":
                    order_field = f"-{order_field}"
            except ValueError:
                pass

        return queryset.order_by(order_field)

    def render_column(self, obj, column_name):
        """Forms HTML-instead to add to the table.

        For the `actions` column I create buttons:
        - taking a new reading (`take_reading_url`)
        - view history display (`history_url`)

        Args:
        obj (Counter): Current object of the doctor.
        column_name (str): Column name.

        Returns:
        str: HTML code or standard column values.

        """
        if column_name == "actions":
            take_reading_url = (
                reverse("admin:counters_add")
                + f"?house={obj.apartment.house_id}&section={obj.apartment.section_id}"
                f"&apartment={obj.apartment.pk}"
            )

            if obj.apartment and obj.service:
                history_url = reverse(
                    "admin:counters2", args=[obj.apartment.pk, obj.service.pk]
                )
            elif obj.apartment:
                history_url = reverse("admin:counters", args=[obj.apartment.pk])
            else:
                history_url = "#"

            return format_html(
                '<a class="btn btn-primary btn-sm" href="{}'
                '" title="Снять новое показание" '
                'target="_blank" data-toggle="tooltip" '
                'onclick="event.stopPropagation();">'
                '<i class="fa fa-dashboard"></i></a> '
                '<a class="btn btn-default btn-sm" href="{}" title="История показаний" '
                'data-toggle="tooltip" onclick="event.stopPropagation();">'
                '<i class="fa fa-eye"></i></a>',
                take_reading_url,
                history_url,
            )

        return super().render_column(obj, column_name)

    def customize_row(self, row, obj):
        """Adjust the JSON sequence for DataTables before sending it to the client.

        Adds:
            • Unique row ID (`DT_RowId`)
            • Apartment ID (`apartment_id`)
            • Ordinal number (`row_number`)

        Args:
            row (dict):
                Table row data.

            obj (Counter):
                Current object of the model.

        Returns:
            dict:
                Updated series with additional data.

        """
        row["DT_RowId"] = f"row-{obj.pk}"
        row["apartment_id"] = obj.apartment.pk if obj.apartment else None
        row["row_number"] = (
            int(self.request.GET.get("start", 0)) + getattr(self, "_index", 0) + 1
        )
        self._index = getattr(self, "_index", 0) + 1
        return row


class FlathAjax(AjaxDatatableView):
    """AJAX representation for displaying a list of Apartments in DataTables.

     Supports filtering based on a number of parameters (booth, section, over,
     background, balance)

    and the image of the current situation will become the skin area.
    """

    model = Apartment
    initial_order = [["apartment_number", "asc"]]
    length_menu = [[50, 100, 200], [50, 100, 200]]

    def get_initial_queryset(self, request=None):
        """Forms a queryset of apartments according to the role of the user  filters.

        Supports filtering by:
            - apartment_number
            - house
            - section
            - floor
            - user
            - balance (positive or negative)
            - extra_data[*] (any additional filters)

        Args:
            request (HttpRequest, optional): The incoming HTTP request.

        Returns:
            QuerySet: Filtered set of apartments.

        """
        user = request.user
        params = request.GET if request.method == "GET" else request.POST
        extra = self._extract_extra_data(params)

        # Access control
        if user.is_superuser or getattr(user.role, "is_worker_role", False):
            qs = Apartment.objects.all()
        else:
            qs = Apartment.objects.filter(house__staff__user=user).distinct()
            if not qs.exists():
                return Apartment.objects.none()

        # Apply filters
        qs = self._apply_field_filters(
            qs, extra, ["apartment_number", "house", "section", "floor", "user"]
        )

        # Apply balance filter
        balance = extra.get("balance")
        if balance:
            qs = self._apply_balance_filter(qs, balance)

        return qs

    def _extract_extra_data(self, params):
        """Extract extra_data[*] fields from request parameters."""
        extra = {}
        for key in params:
            if key.startswith("extra_data[") and key.endswith("]"):
                clean_key = key[len("extra_data[") : -1]
                extra[clean_key] = params.get(key, "").strip()
        return extra

    def _apply_field_filters(self, qs, extra, fields):
        """Apply basic field filters dynamically."""
        for field in fields:
            value = extra.get(field)
            if value:
                qs = qs.filter(
                    **{f"{field}_id" if field != "apartment_number" else field: value}
                )
        return qs

    def _apply_balance_filter(self, qs, balance_value):
        """Apply balance filtering."""
        qs = qs.annotate(
            incomes=models.Sum(
                "account__cashbox__suma",
                filter=models.Q(account__cashbox__payment_articles__record_type="in"),
            ),
            expenses=models.Sum(
                "account__cashbox__suma",
                filter=models.Q(account__cashbox__payment_articles__record_type="out"),
            ),
        ).annotate(balance=models.F("incomes") - models.F("expenses"))

        if balance_value == "yes":
            return qs.filter(balance__gte=0)
        if balance_value == "no":
            return qs.filter(balance__lt=0)
        return qs

    column_defs = [
        {
            "name": "apartment_number",
            "title": "№ квартиры",
            "orderable": True,
            "searchable": False,
        },
        {
            "name": "house",
            "title": "Дом",
            "foreign_field": "house__title",
            "orderable": True,
            "searchable": False,
        },
        {
            "name": "section",
            "title": "Секция",
            "foreign_field": "section__name",
            "orderable": True,
            "searchable": False,
        },
        {
            "name": "floor",
            "title": "Этаж",
            "foreign_field": "floor__name",
            "orderable": True,
            "searchable": False,
        },
        {"name": "user", "title": "Владелец", "orderable": True, "searchable": False},
        {
            "name": "balance",
            "title": "Остаток",
            "searchable": False,
            "orderable": False,
        },
        {
            "name": "actions",
            "title": "Действия",
            "searchable": False,
            "orderable": False,
            "className": "text-end",
        },
        {"name": "id", "visible": False, "searchable": False},
    ]

    def customize_row(self, row, obj):
        """Add additional data about the apartment to the row of the table.

        Check the balance sheet (incomes - expenses) and display it.

        Args:
            row (dict): Table row data.
            obj (Apartment): The Apartment object corresponding to this row.

        Returns:
            dict: Updated row with balance and other information.

        """
        row["id"] = obj.pk
        row["user"] = obj.user.full_name if obj.user else "(не задано)"

        if obj.account:
            incomes = (
                obj.account.cashbox_set.filter(
                    payment_articles__record_type="in"
                ).aggregate(models.Sum("suma"))["suma__sum"]
                or 0
            )
            expenses = (
                obj.account.cashbox_set.filter(
                    payment_articles__record_type="out"
                ).aggregate(models.Sum("suma"))["suma__sum"]
                or 0
            )
            balance = incomes - expenses
        else:
            balance = 0

        row["balance"] = balance
        return row

    def render_column(self, obj, column_name):
        """Forms HTML for the `actions` column.

        Creates edit and delete buttons with action confirmations.

        Args:
        obj (Apartment): Apartment object.
        column_name (str): Column name.

        Returns:
        str: HTML code or standard column values.

        """
        if column_name == "actions":
            edit_url = reverse("admin:update_flat", args=[obj.pk])
            delete_url = reverse("admin:delete_flat", args=[obj.pk])
            csrf_token = get_token(self.request)

            return format_html(
                '<a class="btn btn-default btn-sm" href="{}" '
                'title="Редактировать">'
                '<i class="fa fa-pencil"></i></a> '
                '<form method="post" action="{}" style="display:inline;">'
                '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
                '<button type="submit" class="btn btn-default btn-sm" '
                'onclick="return confirm('
                "'Вы уверены, что хотите удалить этот элемент?');\">"
                '<i class="fa fa-trash"></i>'
                "</button></form>",
                edit_url,
                delete_url,
                csrf_token,
            )

        return super().render_column(obj, column_name)


class HouseListAjax(AjaxDatatableView):
    """Representation for AJAX-incorporation of the list of boxes in DataTables.

    Displays the flow of booths, which can be accessed by a current customer.
    Supports filtering by name and address, as well as dynamic generation
    action buttons (edit, view).
    """

    model = House

    initial_order = [["title", "asc"]]

    length_menu = [[50], [50]]

    column_defs = [
        {
            "name": "row_number",
            "title": "#",
            "placeholder": True,
            "searchable": False,
            "orderable": False,
        },
        {"name": "title", "title": "Назва", "searchable": False, "orderable": True},
        {"name": "address", "title": "Адреса", "searchable": False, "orderable": True},
        {
            "name": "actions",
            "title": "Дії",
            "placeholder": True,
            "searchable": False,
            "orderable": False,
        },
    ]

    def get_initial_queryset(self, request=None):
        """Rotates the initial queryset to display the table.

        Selects only those booths that are associated with the exact accountant  .
        If the user does not authenticate, he rotates the empty queryset.
        It also prevents filtering behind the name and address, as is the  .

        Args:
        request (HttpRequest, optional): Streaming HTTP request.

        Returns:
        QuerySet: A filtered set of House objects.

        """
        user = request.user  # текущий пользователь

        # Если пользователь — персонал, показываем только его дома
        if user.is_authenticated:
            queryset = self.model.objects.filter(staff__user=user).distinct()
        else:
            queryset = self.model.objects.none()

        # Применяем фильтрацию по названию и адресу, если указано
        title = request.GET.get("title") or request.POST.get("title")
        address = request.GET.get("address") or request.POST.get("address")

        if title:
            queryset = queryset.filter(title__icontains=title)
        if address:
            queryset = queryset.filter(address__icontains=address)

        return queryset

    def customize_row(self, row, obj):
        """Adjust the appearance of each table row before passing it to the JSON output.

        Adds:
            • Unique row identifier (DT_RowId).
            • Serial number.
            • HTML buttons for editing and viewing the booth.

        Args:
            row (dict): Row data for serialization.
            obj (House): The House object corresponding to this row.

        Returns:
            dict: Updated dictionary of row data.

        """
        row["DT_RowId"] = f"row_{obj.pk}"  # очень важно!
        row["row_number"] = (
            int(self.request.GET.get("start", 0)) + getattr(self, "_index", 0) + 1
        )

        row["actions"] = f"""
            <a href="{reverse("admin:update_house", args=[obj.pk])}"
            class="btn btn-primary btn-xs" title="Редагувати">
                <i class="fa fa-pencil"></i>
            </a>
            <a href="{reverse("admin:delete_house", args=[obj.pk])}"
            class="btn btn-danger btn-xs" title="Видалити">
                <i class="fa fa-trash"></i>
            </a>
        """

        self._index = getattr(self, "_index", 0) + 1
        return row


class UserAjaxDatatableView(AjaxDatatableView):
    """AjaxDatatable view for displaying staff users.

    Provides server-side processing for a datatable of staff users,
    including searching by name, email, role, and displaying actions
    like edit and delete. Supports row numbering and links to edit pages.

    Attributes:
        model (Model): The Django model to query (User).
        title (str): The title of the datatable.
        initial_order (list): Default ordering of the datatable.
        length_menu (list): Pagination options.
        column_defs (list): Definitions for each column in the datatable.

    """

    model = User
    title = "Список персонала"
    initial_order = [["email", "asc"]]
    length_menu = [[50], [50]]

    # 🔹 Определяем колонки
    column_defs = [
        {
            "name": "row_number",
            "title": "#",
            "placeholder": True,
            "searchable": False,
            "orderable": True,
        },
        {"name": "id", "visible": False},
        {
            "name": "full_name",
            "title": "Пользователь",
            "searchable": True,
            "orderable": False,
        },  # виртуальная
        {"name": "role", "title": "Роль", "searchable": True},
        {"name": "phone", "title": "Телефон", "searchable": True},
        {"name": "email", "title": "Email (логин)", "searchable": True},
        {"name": "status", "title": "Статус", "searchable": True},
        {
            "name": "actions",
            "title": "Действия",
            "searchable": False,
            "orderable": False,
        },
        {"name": "row_url", "visible": False, "searchable": False},
    ]

    # 🔹 Базовый queryset
    def get_initial_queryset(self, request=None):
        """Return the initial queryset of staff users.

        Args:
            request (HttpRequest, optional): The incoming request object .

        Returns:
            QuerySet: Queryset of User objects with is_staff=True.

        """
        return User.objects.filter(is_staff=True)

    def render_column(self, row, column):
        """Render the value for a specific column in the datatable.

        Args:
            row (User): The User instance for the current row.
            column (str): The name of the column to render.

        Returns:
            str: Rendered HTML or value for the column.

        """

        def full_name_handler(r):
            """Return a clickable username linking to the edit page.

            Args:
                r (User): Current user row.

            Returns:
                str: HTML link with the user's full name or email.

            """
            url = reverse("admin:user_update", args=[r.pk])
            name = r.full_name or r.email
            return format_html('<a href="{}">{}</a>', url, name)

        def role_handler(r):
            """Return the user's role name.

            Args:
                r (User): Current user row.

            Returns:
                str: Role name or empty string if not assigned.

            """
            return r.role.name if r.role else ""

        def status_handler(r):
            """Return formatted HTML badge for the user's status.

            Args:
                r (User): Current user row.

            Returns:
                str: HTML span representing the status badge.

            """
            status_map = {
                "new": '<span class="label label-warning">Новый</span>',
                "work": '<span class="label label-success">Активный</span>',
                "done": '<span class="label label-danger">Отключен</span>',
            }
            return format_html(status_map.get(r.status, ""))

        def actions_handler(r):
            edit_url = reverse("admin:user_update", args=[r.pk])
            csrf_token = get_token(self.request)

            # Если это текущий пользователь — редактировать можно, удалить нельзя
            if r.pk == self.request.user.pk:
                return format_html(
                    '<a class="btn btn-default btn-sm" href="{}" title="Редактировать">'
                    '<i class="fa fa-pencil"></i></a> '
                    '<button class="btn btn-default btn-sm disabled" title="Нельзя удалить самого себя">'
                    '<i class="fa fa-trash"></i></button>',
                    edit_url
                )


            delete_url = reverse("admin:user_delete", args=[r.pk])
            return format_html(
                '<a class="btn btn-default btn-sm" href="{}" title="Редактировать">'
                '<i class="fa fa-pencil"></i></a> '
                '<form method="post" action="{}" style="display:inline;">'
                '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
                '<button type="submit" class="btn btn-default btn-sm" '
                'onclick="return confirm('
                "'Вы уверены, что хотите удалить этот элемент?');\">"
                '<i class="fa fa-trash"></i>'
                "</button>"
                "</form>",
                edit_url,
                delete_url,
                csrf_token,
            )
        def row_url_handler(r):
            """Return the URL used when clicking the row.

            Args:
                r (User): Current user row.

            Returns:
                str: URL of the edit page for the user.

            """
            return reverse("admin:user_update", args=[r.pk])

        handlers = {
            "full_name": full_name_handler,
            "role": role_handler,
            "status": status_handler,
            "actions": actions_handler,
            "row_url": row_url_handler,
        }

        handler = handlers.get(column)
        if handler:
            return handler(row)

        return super().render_column(row, column)

    def customize_row(self, row, obj):
        """Customize the datatable row with row number and edit URL.

        Args:
            row (dict): The dictionary representing the row data.
            obj (User): The User instance for the current row.

        Returns:
            dict: Updated row dictionary with 'row_number' and 'row_url'.

        """
        start = int(self.request.GET.get("start", 0))
        row["row_number"] = start + getattr(self, "_index", 0) + 1
        row["row_url"] = reverse("admin:user_update", args=[obj.pk])
        self._index = getattr(self, "_index", 0) + 1
        return row

    # 🔹 Поиск по имени + фамилии + email
    def filter_queryset(self, params, qs):
        """Фильтрует queryset пользователей по имени, фамилии или email.

        Args:
            params (dict): Параметры запроса, содержащие значение поиска.
            qs (QuerySet): Исходный queryset пользователей.

        Returns:
            QuerySet: Отфильтрованный queryset, если указано значение поиска;
                      иначе — исходный queryset без изменений.

        """
        search_value = params.get("search[value]", None)
        if search_value:
            qs = qs.filter(
                Q(first_name__icontains=search_value)
                | Q(last_name__icontains=search_value)
                | Q(email__icontains=search_value)
            )
        return qs

    # 🔹 Возврат JSON
    def render_to_response(self, context, **response_kwargs):
        """Return an HTTP response in JSON format.

        Args:
        context (dict):
            The data context to be serialized.

        **response_kwargs:
            Additional parameters passed to the HTTP response.

        Returns:
        HttpResponse:
            Response with JSON content and a valid content-type header.

        """
        response_kwargs.setdefault("content_type", "application/json; charset=utf-8")
        return super().render_to_response(context, **response_kwargs)


def get_sections(request):
    """Return a list of sections for a given house as JSON.

    Args:
        request (HttpRequest): The HTTP GET request containing 'house_id'.

    Returns:
        JsonResponse: A JSON object with a list of sections, each containing
                      'id' and 'name'.

    """
    house_id = request.GET.get("house_id")
    sections = Section.objects.filter(house_id=house_id).values("id", "name")
    return JsonResponse({"sections": list(sections)})


def get_apartments(request):
    """Return a list of apartments for a given section as JSON.

    Args:
        request (HttpRequest): The HTTP GET request containing 'section_id'.

    Returns:
        JsonResponse: A JSON object with a list of apartments, each containing
                      'id' and 'apartment_number'.

    """
    section_id = request.GET.get("section_id")
    apartments = Apartment.objects.filter(floor__section_id=section_id).values(
        "id", "apartment_number"
    )
    return JsonResponse({"apartments": list(apartments)})


def get_apartment_owner(request):
    """Return JSON data for the owner of a given apartment.

    Args:
        request (HttpRequest): The HTTP GET request containing 'apartment_id'.

    Returns:
        JsonResponse: A JSON object with the owner's 'full_name' and 'phone',
                      or empty strings if the apartment or owner is not found.

    """
    apt_id = request.GET.get("apartment_id")
    apt = Apartment.objects.filter(id=apt_id).select_related("user").first()
    if apt and apt.user:
        return JsonResponse(
            {
                "owner": apt.user.get_full_name() or apt.user.username,
                "phone": getattr(apt.user, "phone", "")
                or getattr(apt.user, "phone_number", ""),
            }
        )
    return JsonResponse({"owner": "", "phone": ""})
