"""Views for the user-facing cabinet application."""

import logging
from datetime import timedelta
from decimal import Decimal
from decimal import InvalidOperation
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F
from django.db.models import Q
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.timezone import now
from django.views.generic import CreateView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import TemplateView
from django.views.generic import UpdateView

from src.building.models import Apartment
from src.financials.models import CashBox
from src.financials.models import Invoice
from src.financials.models import InvoiceItem

from .form import CreateOwnerFlatForm1
from .form import TicketUserForm
from .models import Message
from .models import Ticket
from .models import User
from src.core.export_exel import fill_invoice_to_excel, excel_to_html_openpyxl, html_to_pdf

logger = logging.getLogger(__name__)


class StatisticView(TemplateView):
    """Display financial statistics for a user's apartment."""

    template_name = "statistic_1.html"

    def get_context_data(self, **kwargs):
        """Generate context with apartment balance, invoices, and charts."""
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")

        apartment = get_object_or_404(
            Apartment.objects.select_related("house", "user", "account"), pk=pk
        )
        account = apartment.account

        if not account:
            context.update(
                {
                    "apartment": apartment,
                    "account": None,
                    "balance": Decimal("0.00"),
                    "avg_month_expense": Decimal("0.00"),
                    "invoices": [],
                    "chart_labels": [],
                    "chart_data": [],
                    "apartments": Apartment.objects.filter(user=self.request.user),
                }
            )
            return context

        # Calculate incoming payments
        incoming = CashBox.objects.filter(
            personal_account=account,
            is_conducted=True,
            payment_articles__record_type="in",
        ).aggregate(total=Sum("suma"))["total"] or Decimal("0.00")

        invoices = Invoice.objects.filter(personal_account=account, conducted=True)

        # Paid and unpaid totals
        paid_total = invoices.filter(status="paid").aggregate(
            total=Sum("items__total")
        )["total"] or Decimal("0.00")
        unpaid_total = invoices.exclude(status="paid").aggregate(
            total=Sum("items__total")
        )["total"] or Decimal("0.00")

        balance = incoming + paid_total - unpaid_total

        # Average monthly expense
        monthly_totals = (
            invoices.annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(month_sum=Sum("items__total"))
        )
        avg_month_expense = (
            sum(item["month_sum"] or 0 for item in monthly_totals) / len(monthly_totals)
            if monthly_totals
            else Decimal("0.00")
        )

        # Expenses by month and category for charts
        today = now().date()
        start_of_this_month = today.replace(day=1)
        start_of_last_month = (start_of_this_month - timedelta(days=1)).replace(day=1)
        end_of_last_month = start_of_this_month - timedelta(days=1)

        expenses_this_month = (
            InvoiceItem.objects.filter(
                invoice__personal_account=account,
                invoice__conducted=True,
                invoice__date__gte=start_of_this_month,
                invoice__date__lte=today,
            )
            .values(service_name=F("tariff_service__service__name"))
            .annotate(total=Sum("total"))
            .order_by("-total")
        )

        expenses_last_month = (
            InvoiceItem.objects.filter(
                invoice__personal_account=account,
                invoice__conducted=True,
                invoice__date__gte=start_of_last_month,
                invoice__date__lte=end_of_last_month,
            )
            .values(service_name=F("tariff_service__service__name"))
            .annotate(total=Sum("total"))
            .order_by("-total")
        )

        chart_labels_this = [e["service_name"] for e in expenses_this_month]
        chart_data_this = [float(e["total"]) for e in expenses_this_month]
        chart_labels_last = [e["service_name"] for e in expenses_last_month]
        chart_data_last = [float(e["total"]) for e in expenses_last_month]

        monthly_totals = list(monthly_totals)[-12:]
        chart_labels_year = [item["month"].strftime("%b %Y") for item in monthly_totals]
        chart_data_year = [float(item["month_sum"]) for item in monthly_totals]

        context.update(
            {
                "apartment": apartment,
                "account": account,
                "balance": balance,
                "invoices": invoices.annotate(total_sum=Sum("items__total")).order_by(
                    "-date"
                ),
                "apartments": Apartment.objects.filter(user=self.request.user),
                "avg_month_expense": avg_month_expense,
                "chart_labels_this": chart_labels_this,
                "chart_data_this": chart_data_this,
                "chart_labels_last": chart_labels_last,
                "chart_data_last": chart_data_last,
                "chart_labels_year": chart_labels_year,
                "chart_data_year": chart_data_year,
                "active_section": "statistic",
            }
        )
        return context


class MessageView(LoginRequiredMixin, ListView):
    """Display a list of messages for the current user."""

    model = Message
    template_name = "message_list.html"
    context_object_name = "messages_data"
    paginate_by = 25

    def get_queryset(self):
        """Return filtered queryset of messages based on user and search."""
        user = self.request.user
        qs = Message.objects.filter(Q(sender=user) | Q(recipients=user))

        search = self.request.GET.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(text__icontains=search)
                | Q(sender__email__icontains=search)
                | Q(sender__first_name__icontains=search)
                | Q(sender__last_name__icontains=search)
                | Q(sender__second_name__icontains=search)
            )
        return (
            qs.select_related("sender")
            .prefetch_related("recipients")
            .distinct()
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        """Add search and section data to context."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Мои сообщения"
        context["search"] = self.request.GET.get("search", "")
        context["active_section"] = "message"
        return context


class MessagesDetailView(DetailView):
    """Display details of a specific message."""

    model = Message
    template_name = "messages/message_detail.html"

    def get_context_data(self, **kwargs):
        """Add page title and active section to context."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Сообщениe"
        context["active_section"] = "message"
        return context


class CabinetView(LoginRequiredMixin, TemplateView):
    """Display the user's main cabinet dashboard."""

    template_name = "hello.html"

    def get_context_data(self, **kwargs):
        """Add page title and user data to context."""
        user = self.request.user
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Cabinet"
        context["user"] = user
        return context


class ProfileView(LoginRequiredMixin, TemplateView):
    """Display the user's (or another user's) profile page."""

    template_name = "profile.html"

    def get_user_object(self):
        """Return either the user from URL or current user."""
        pk = self.kwargs.get("pk")
        if pk:
            # показываем пользователя по pk
            return get_object_or_404(User, pk=pk)
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.get_user_object()

        context["page_title"] = "Profile"
        context["user"] = user

        apartments = user.apartments.select_related(
            "house", "section", "floor", "account"
        )

        context["apartments"] = apartments
        context["houses"] = {apt.house for apt in apartments}
        context["sections"] = {apt.section for apt in apartments}
        context["active_section"] = "profile"

        return context

class TariffView(LoginRequiredMixin, TemplateView):
    """Display tariff details for a specific apartment."""

    template_name = "tariff.html"

    def get_context_data(self, **kwargs):
        """Add apartment, tariff, and services to context."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Tariff"
        user = self.request.user
        flat_id = self.kwargs.get("pk")
        apartments = user.apartments.select_related(
            "house", "section", "floor", "account"
        )
        apartment = get_object_or_404(
            user.apartments.select_related(
                "house", "section", "floor", "account", "tariff"
            ).prefetch_related("tariff__services__service", "tariff__services__unit"),
            pk=flat_id,
        )
        services = apartment.tariff.services.all() if apartment.tariff else []
        context.update(
            {
                "user": user,
                "apartment": apartment,
                "houses": {apt.house for apt in apartments},
                "services": services,
                "house": apartment.house,
                "tariff": apartment.tariff,
                "active_section": "tariff",
            }
        )
        return context


class InvoiceListView(LoginRequiredMixin, TemplateView):
    """Display a list of invoices for a user's apartment."""

    template_name = "invoice/invoice.html"

    def get_context_data(self, **kwargs):
        """Add apartments, invoices, and house data to context."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Квитанции"
        user = self.request.user
        flat_id = self.kwargs.get("pk")
        apartments = user.apartments.select_related(
            "house", "section", "floor", "account"
        )
        apartment = get_object_or_404(apartments, pk=flat_id)
        invoices = (
            Invoice.objects.filter(personal_account=apartment.account)
            .select_related("tariff")
            .order_by("-date")
        )
        context.update(
            {
                "user": user,
                "apartments": apartments,
                "apartment": apartment,
                "house": apartment.house,
                "invoices": invoices,
                "active_section": "invoice",
            }
        )
        return context


class InvoiceDetailView(DetailView):
    """Display detailed information about a specific invoice."""

    model = Invoice
    template_name = "invoice/invoice_detail.html"
    context_object_name = "invoice"

    def get_context_data(self, **kwargs):
        """Add related apartment, items, and totals to context."""
        context = super().get_context_data(**kwargs)
        invoice = self.object
        apartment = getattr(invoice.personal_account, "apartment", None)
        house = apartment.house if apartment else None
        invoices_by_house = (
            Invoice.objects.filter(personal_account__apartment__house=house)
            .select_related("personal_account", "personal_account__apartment")
            .order_by("-date")
            if house
            else Invoice.objects.none()
        )
        items = invoice.items.select_related(
            "tariff_service", "tariff_service__service"
        ).all()
        context.update(
            {
                "apartment": apartment,
                "house": house,
                "invoices_by_house": invoices_by_house,
                "items": items,
                "total": invoice.total_amount,
                "active_section": "invoice",
            }
        )
        return context


class PayInvoice(LoginRequiredMixin, TemplateView):
    """Step 1 — choose a payment method."""

    template_name = "invoice/pay_page.html"

    def get_context_data(self, **kwargs):
        """Add invoice and section info to context."""
        context = super().get_context_data(**kwargs)
        invoice = get_object_or_404(Invoice, pk=self.kwargs["pk"])
        context["invoice"] = invoice
        context["active_section"] = "invoice"
        return context


class PayInvoiceStep2(LoginRequiredMixin, TemplateView):
    """Step 2 — enter payment details."""

    template_name = "invoice/pay_page_2.html"

    def get_context_data(self, **kwargs):
        """Add invoice data to context."""
        context = super().get_context_data(**kwargs)
        invoice = get_object_or_404(Invoice, pk=self.kwargs["pk"])
        context["invoice"] = invoice
        context["active_section"] = "invoice"
        return context

    def post(self, request, *args, **kwargs):
        """Handle invoice payment submission."""
        invoice = get_object_or_404(Invoice, pk=self.kwargs["pk"])
        amount_str = request.POST.get("amount")
        try:
            amount = Decimal(amount_str)
        except (TypeError, InvalidOperation):
            messages.error(request, "Введите корректную сумму оплаты.")
            return redirect("step2", pk=invoice.pk)

        total_amount = invoice.total_amount or Decimal("0.00")
        if amount <= 0:
            messages.error(request, "Сумма оплаты должна быть больше нуля.")
            return redirect("step2", pk=invoice.pk)
        if amount < total_amount:
            invoice.status = "counted"
        else:
            invoice.status = "new"
        invoice.save(update_fields=["status"])
        messages.success(
            request, f"Оплата успешно проведена. Статус: {invoice.get_status_display()}"
        )
        return redirect("invoice_detail", pk=invoice.pk)


class InvoicePrintView(DetailView):
    """Generate invoice PDF on the fly and return it in browser."""
    model = Invoice
    pk_url_kwarg = "pk"

    def get(self, request, *args, **kwargs):
        invoice = self.get_object()

        # 1️⃣ Генерация Excel в памяти
        excel_io = fill_invoice_to_excel(invoice_id=invoice.id)

        # 2️⃣ Конвертация Excel в HTML (возвращает строку)
        html_string = excel_to_html_openpyxl(excel_io)

        # 3️⃣ Конвертация HTML в PDF в памяти
        pdf_io = html_to_pdf(html_string)

        # 4️⃣ Отправка PDF в браузер
        pdf_bytes = pdf_io.getvalue()
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="Invoice_{invoice.id}.pdf"'
        return response

class ListTicketsView(LoginRequiredMixin, ListView):
    """Display list of maintenance requests (tickets)."""

    model = Ticket
    template_name = "master_request.html"
    context_object_name = "tickets"

    def get_queryset(self):
        """Return tickets belonging to the current user."""
        return Ticket.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        """Add page title and section info to context."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Мои заявки"
        context["active_section"] = "ticket"
        return context


class AddTicketsView(LoginRequiredMixin, CreateView):
    """Allow users to create a new maintenance request (ticket)."""

    model = Ticket
    template_name = "add_ticket.html"
    form_class = TicketUserForm
    success_url = reverse_lazy("tickets_list")

    def get_context_data(self, **kwargs):
        """Add apartments and houses for selection."""
        context = super().get_context_data(**kwargs)
        user = self.request.user
        apartments = user.apartments.select_related(
            "house", "section", "floor", "account"
        )
        context.update(
            {
                "page_title": "Ticket",
                "user": user,
                "apartments": apartments,
                "houses": {apt.house for apt in apartments},
                "sections": {apt.section for apt in apartments},
                "active_section": "ticket",
            }
        )
        return context

    def get_form_kwargs(self):
        """Inject the current user into form kwargs."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Save the ticket with the current user as owner."""
        form.save(user=self.request.user)
        return super().form_valid(form)


class UpdateProfile(LoginRequiredMixin, UpdateView):
    """View for editing the user's own profile."""

    template_name = "update_profile.html"
    model = User
    form_class = CreateOwnerFlatForm1
    success_url = reverse_lazy("cabinet")

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["active_section"] = "owners"
        return context

    def form_valid(self, form):
        """Save form with password hashing and redirect."""
        form.save()
        return redirect(self.success_url)
