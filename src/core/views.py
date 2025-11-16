"""Defines all the views for the Django project's core application."""

import contextlib
import datetime
import json
import logging
from contextlib import suppress
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from urllib.parse import quote
from urllib.parse import urlencode
from django.db.models import Case, When, Value, IntegerField
import pandas as pd
from dal import autocomplete
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.forms import inlineformset_factory
from django.forms import modelformset_factory
from django.http import FileResponse
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.timezone import localtime
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic import ListView
from django.views.generic import TemplateView
from django.views.generic import UpdateView
from django.views.generic import View
from django.views.generic.edit import FormMixin
from openpyxl import load_workbook

from src.building.forms import ApartmentForm
from src.building.forms import FloorFormSet
from src.building.forms import HouseForm
from src.building.forms import SectionFormSet
from src.building.forms import StaffFormSet
from src.building.models import Apartment
from src.building.models import Floor
from src.building.models import House
from src.building.models import Section
from src.core.forms import UserSendMessage
from src.core.generator import generate_id_with_random_number
from src.core.permission import RolePermissionRequiredMixin
from src.core.tasks import send_invitation_task
from src.core.tasks import send_user_message
from src.financials.forms import CashBoxForm
from src.financials.forms import ExpenseReportForm
from src.financials.forms import InvoiceFilterForm
from src.financials.forms import InvoiceForm
from src.financials.forms import PaymentArticlesForm
from src.financials.forms import PersonalAccount
from src.financials.forms import PersonalAccountForm
from src.financials.forms import ReceiptStatementForm
from src.financials.forms import TarifServiceItem_inlinformset
from src.financials.forms import TemplateFormSet
from src.financials.models import CashBox
from src.financials.models import Invoice
from src.financials.models import InvoiceItem
from src.financials.models import PaymentArticles
from src.financials.models import Template
from src.services.models import Counter
from src.services.models import PaymentDetail
from src.services.models import Service
from src.services.models import Tariff
from src.services.models import TariffService
from src.services.models import Unit
from src.users.form import CreateOwnerFlatForm
from src.users.form import SendInvitationForm
from src.users.form import SendMessage
from src.users.form import StaffForms
from src.users.form import TicketAdminForm
from src.users.form import TicketFilterForm
from src.users.models import Message
from src.users.models import Role
from src.users.models import Ticket
from src.users.models import User
from src.web_site.forms import AdditionalGalleryFormSet
from src.web_site.forms import ContactForm
from src.web_site.forms import DocumentFormSet
from src.web_site.forms import FormAboutUs
from src.web_site.forms import FormBlock
from src.web_site.forms import FormMain
from src.web_site.forms import FormSEO
from src.web_site.forms import MainGalleryFormSet
from src.web_site.forms import ServiceFormSet
from src.web_site.forms import TariffFormSet
from src.web_site.models import SEO
from src.web_site.models import AboutUs
from src.web_site.models import Block
from src.web_site.models import Contact
from src.web_site.models import Gallery
from src.web_site.models import Main
from src.web_site.models import ServiceStr

from .export_exel import excel_to_html_openpyxl
from .export_exel import fill_invoice_to_excel
from .export_exel import html_to_pdf
from .forms import CounterFilterForm
from .forms import CounterForm
from .forms import FilterApartment
from .forms import FilterForm
from .forms import FilterOwnerForm
from .forms import MeterReadingForm
from .forms import PaymentDetailsForm
from .forms import PersonalAccountFilterForm
from .forms import RoleForm
from .forms import ServiceFormSet1
from .forms import TariffForm
from .forms import TariffServiceFormSet
from .forms import UnitFormSet
from .tasks import send_broadcast_email
from .tasks import send_invoice_pdf_email

logger = logging.getLogger(__name__)


# 1
class StatisticView(LoginRequiredMixin, RolePermissionRequiredMixin, TemplateView):
    """Display detailed financial and operational statistics for the user's houses.

    Requires the user to be logged in and have the 'has_statistic' role permission.
    Renders statistics including ticket counts, invoice summaries, and cash flow charts.
    """

    template_name = "statistic.html"
    role_permission = "has_statistic"

    def get_context_data(self, **kwargs):
        """Return context data for the statistics page.

        Adds user-specific house, financial, and ticket statistics to the context
        for rendering the 'statistic.html' template.
        """
        context = super().get_context_data(**kwargs)
        user = self.request.user

        user_houses = self._get_user_houses(user)
        context.update(self._get_basic_stats(user_houses))
        context.update(self._get_financial_stats(user_houses))
        context.update(self._get_cashbox_stats(user_houses))
        context.update(self._get_invoice_chart_data(user_houses))

        context["page_title"] = "Статистика"
        context["active_section"] = "statistic"
        return context

    # --- Helper methods below ---

    def _get_user_houses(self, user):
        """Return all houses accessible to the user (as owner or staff)."""
        return House.objects.filter(
            Q(apartment__user=user) | Q(staff__user=user)
        ).distinct()

    def _get_basic_stats(self, user_houses):
        """Return basic statistics about houses, owners, and tickets."""
        return {
            "user_house_count": user_houses.count(),
            "active_owners_count": User.objects.filter(
                apartments__house__in=user_houses, status="work"
            )
            .distinct()
            .count(),
            "total_apartments": Apartment.objects.filter(house__in=user_houses).count(),
            "total_personal_accounts": PersonalAccount.objects.filter(
                apartment__house__in=user_houses
            )
            .distinct()
            .count(),
            "total_ticket": Ticket.objects.filter(
                apartment__house__in=user_houses, status__in=["new"]
            )
            .distinct()
            .count(),
            "total_tickets_work": Ticket.objects.filter(
                apartment__house__in=user_houses, status__in=["work"]
            )
            .distinct()
            .count(),
        }

    def _get_financial_stats(self, user_houses):
        """Return invoice-related financial statistics."""
        unpaid_sum = (
            Invoice.objects.filter(
                personal_account__apartment__house__in=user_houses,
                status__in=["zero", "counted"],
            ).aggregate(total=Sum("items__total"))["total"]
            or 0
        )
        paid_sum = (
            Invoice.objects.filter(
                personal_account__apartment__house__in=user_houses, status="new"
            ).aggregate(total=Sum("items__total"))["total"]
            or 0
        )
        total_debt = unpaid_sum or 0
        balance = paid_sum - unpaid_sum
        return {"total_debt": total_debt, "balance": balance}

    def _get_cashbox_stats(self, user_houses):
        """Return cashbox-related statistics and chart data."""
        accounts = PersonalAccount.objects.filter(apartment__house__in=user_houses)
        managers = User.objects.filter(staff_houses__house__in=user_houses)

        qs = CashBox.objects.filter(
            Q(personal_account__in=accounts) | Q(manager__in=managers),
            is_conducted=True,
        )

        incoming = (
            qs.filter(payment_articles__record_type="in").aggregate(total=Sum("suma"))[
                "total"
            ]
            or 0
        )
        outgoing = (
            qs.filter(payment_articles__record_type="out").aggregate(total=Sum("suma"))[
                "total"
            ]
            or 0
        )

        chart_data = self._prepare_monthly_chart(qs)

        return {
            "cash_balance": incoming - outgoing,
            "chart_labels": chart_data["labels"],
            "chart_incoming": chart_data["incoming"],
            "chart_outgoing": chart_data["outgoing"],
        }

    def _prepare_monthly_chart(self, cashbox_qs):
        """Prepare monthly incoming/outgoing sums for chart display."""
        monthly_data = (
            cashbox_qs.annotate(month=TruncMonth("date"))
            .values("month", "payment_articles__record_type")
            .annotate(total=Sum("suma"))
            .order_by("month")
        )

        totals = {}
        for entry in monthly_data:
            month_str = entry["month"].strftime("%Y-%m")
            totals.setdefault(month_str, {"in": 0, "out": 0})
            totals[month_str][entry["payment_articles__record_type"]] += float(
                entry["total"]
            )

        labels = sorted(totals.keys())
        incoming = [totals[m]["in"] for m in labels]
        outgoing = [totals[m]["out"] for m in labels]

        return {"labels": labels, "incoming": incoming, "outgoing": outgoing}

    def _get_invoice_chart_data(self, user_houses):
        """Return monthly invoice totals for chart display."""
        qs = Invoice.objects.filter(personal_account__apartment__house__in=user_houses)
        monthly = (
            qs.annotate(month=TruncMonth("date"))
            .values("month", "status")
            .annotate(total=Sum("items__total"))
            .order_by("month")
        )

        totals = {}
        for entry in monthly:
            month_str = entry["month"].strftime("%Y-%m")
            totals.setdefault(month_str, {"all": 0, "paid": 0})
            totals[month_str]["all"] += entry["total"]
            if entry["status"] == "new":
                totals[month_str]["paid"] += entry["total"]

        labels = sorted(totals.keys())
        total_sum = [float(totals[m]["all"]) for m in labels]
        paid_sum = [float(totals[m]["paid"]) for m in labels]

        return {
            "invoice_chart_labels": labels,
            "invoice_chart_total": total_sum,
            "invoice_chart_paid": paid_sum,
        }


# 2
class ApartmentView(
    LoginRequiredMixin, RolePermissionRequiredMixin, FormView, ListView
):
    """View for listing apartments with filtering."""

    model = Apartment
    form_class = FilterApartment
    template_name = "apartment/apartment.html"
    context_object_name = "apartments"
    success_url = reverse_lazy("admin:flat")
    role_permission = "has_apartment"

    def get_context_data(self, **kwargs):
        """Provide context data for the Apartment view.

        Adds page title, active section, and other relevant context variables
        used in the template rendering.

        Args:
            **kwargs: Arbitrary keyword arguments passed to the superclass.

        Returns:
            dict: Context data for template rendering.

        """
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Квартиры"
        context["filter_form"] = self.get_form()
        context["active_section"] = "apartment"
        return context


class AddApartmentView(LoginRequiredMixin, RolePermissionRequiredMixin, FormView):
    """View for creating a new apartment.

    Provides a form for adding apartment information. Requires the user to be
    logged in and have the 'has_apartment' permission.
    """

    template_name = "apartment/new_flat.html"
    form_class = ApartmentForm
    success_url = reverse_lazy("admin:flat")
    role_permission = "has_apartment"

    def form_valid(self, form):
        """Handle valid form submission.

        Saves the new apartment instance and redirects to the success URL.
        """
        form.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Return context data for the apartment creation page.

        Adds the list of personal accounts and sets the active section in the
        context for template rendering.
        """
        context = super().get_context_data(**kwargs)
        context["accounts"] = PersonalAccount.objects.all()
        context["active_section"] = "apartment"
        return context


class UpdateApartmentView(LoginRequiredMixin, RolePermissionRequiredMixin, UpdateView):
    """View for updating existing apartment information.

    Allows users with the 'has_apartment' permission to edit apartment data
    using the ApartmentForm.
    """

    model = Apartment
    form_class = ApartmentForm
    template_name = "apartment/new_flat.html"
    success_url = reverse_lazy("admin:flat")
    role_permission = "has_apartment"

    def get_context_data(self, **kwargs):
        """Return context data for the apartment update page.

        Adds the active section to the context for template rendering.
        """
        context = super().get_context_data(**kwargs)
        context["active_section"] = "apartment"
        return context

    def form_valid(self, form):
        """Handle valid form submission.

        Saves the updated apartment instance and redirects to the success URL.
        """
        form.save()
        return super().form_valid(form)


class DeleteApartmentView(LoginRequiredMixin, RolePermissionRequiredMixin, DeleteView):
    """View for deleting an apartment.

    Displays a confirmation page before deleting the selected apartment.
    Requires the user to have the 'has_apartment' permission.
    """

    model = Apartment
    template_name = "apartment/confirm_delete.html"
    success_url = reverse_lazy("admin:flat")
    role_permission = "has_apartment"

    def get_context_data(self, **kwargs):
        """Return context data for the apartment deletion confirmation page.

        Adds the active section to the context for template rendering.
        """
        context = super().get_context_data(**kwargs)
        context["active_section"] = "apartment"
        return context


class ApartmentDetailView(LoginRequiredMixin, RolePermissionRequiredMixin, DetailView):
    """View for displaying detailed information about a specific apartment.

    Shows all related information including the house, section, floor,
    owner, account, tariff, and assigned staff.
    """

    model = Apartment
    template_name = "apartment/flat_card.html"
    context_object_name = "Apartment"
    role_permission = "has_apartment"

    def get_context_data(self, **kwargs):
        """Return detailed context data for the apartment detail page.

        Includes related objects such as the house, section, floor, owner,
        account, tariff, and staff assigned to the apartment's house.
        """
        context = super().get_context_data(**kwargs)
        apartment = self.get_object()
        context["apartment"] = apartment
        context["house"] = apartment.house
        context["section"] = apartment.section
        context["floor"] = apartment.floor
        context["account"] = apartment.account
        context["owner"] = apartment.user
        context["tariff"] = apartment.tariff
        context["active_section"] = "apartment"
        context["staff"] = apartment.house.staff.select_related("user")
        return context


class SendInvitation(LoginRequiredMixin, RolePermissionRequiredMixin, FormView):
    """View for sending invitations to apartment owners.

    Allows users with the 'has_owner' permission to send invitation emails or
    SMS messages to potential owners.
    """

    template_name = "apartment/send_invitations.html"
    form_class = SendInvitationForm
    success_url = reverse_lazy("admin:dashboard")
    role_permission = "has_owner"

    def get_context_data(self, **kwargs):
        """Return context data for the invitation form page.

        Adds the active navigation section to the context.
        """
        context = super().get_context_data(**kwargs)
        context["active_section"] = "owners"
        return context

    def form_valid(self, form):
        """Handle valid form submission.

        Launches an asynchronous Celery task for sending invitations and
        displays a success message to the user.
        """
        data = form.cleaned_data
        task = send_invitation_task.delay(
            email=data.get("email"),
            phone=data.get("phone"),
        )

        messages.success(
            self.request,
            f"✅ Отправка приглашения запущена. ID задачи: {task.id}",
        )
        return super().form_valid(form)


class CashboxView(
    LoginRequiredMixin, RolePermissionRequiredMixin, FormView, TemplateView
):
    """View for managing cashbox transactions and financial statistics.

    Provides filtering, summary statistics, and DataTables-compatible AJAX
    responses for all cashbox operations.
    """

    form_class = CashBoxForm
    template_name = "cashbox/account_transaction.html"
    role_permission = "has_cashbox"

    def get_queryset(self):
        """Return filtered queryset based on form parameters.

        Applies date, payment article, and record type filters from the form.
        """
        queryset = CashBox.objects.all()
        form = self.get_form()
        if form.is_valid():
            if form.cleaned_data.get("date_from"):
                queryset = queryset.filter(date__gte=form.cleaned_data["date_from"])
            if form.cleaned_data.get("date_to"):
                queryset = queryset.filter(date__lte=form.cleaned_data["date_to"])
            if form.cleaned_data.get("payment_article"):
                queryset = queryset.filter(
                    payment_articles=form.cleaned_data["payment_article"]
                )
            if form.cleaned_data.get("record_type"):
                queryset = queryset.filter(
                    payment_articles__record_type=form.cleaned_data["record_type"]
                )
        return queryset

    def get_context_data(self, **kwargs):
        """Return context data for rendering the cashbox page.

        Includes form filters, transaction statistics, total balances, and
        personal account summaries.
        """
        context = super().get_context_data(**kwargs)
        form = self.get_form()
        queryset = self.get_queryset()

        # --- Общая статистика по всем операциям ---
        total_income = queryset.filter(payment_articles__record_type="in").aggregate(
            total=Sum("suma")
        )["total"] or Decimal(0)
        total_expense = queryset.filter(payment_articles__record_type="out").aggregate(
            total=Sum("suma")
        )["total"] or Decimal(0)
        balance = total_income - total_expense

        # --- Баланс всей кассы ---
        cashbox_income = CashBox.objects.filter(
            is_conducted=True, payment_articles__record_type="in"
        ).aggregate(total=Sum("suma"))["total"] or Decimal(0)
        cashbox_expense = CashBox.objects.filter(
            is_conducted=True, payment_articles__record_type="out"
        ).aggregate(total=Sum("suma"))["total"] or Decimal(0)
        cashbox_balance = cashbox_income - cashbox_expense

        # --- Персональный счёт ---
        total_paid_invoices = Invoice.objects.filter(status="new").aggregate(
            total=Sum("items__total")
        )["total"] or Decimal(0)

        total_unpaid_invoices = Invoice.objects.filter(
            status__in=["zero", "counted"]
        ).aggregate(total=Sum("items__total"))["total"] or Decimal(0)

        debt = Invoice.objects.filter(status="zero").aggregate(
            total=Sum("items__total")
        )["total"] or Decimal(0)

        personal_balance = total_paid_invoices - total_unpaid_invoices

        context.update(
            {
                "filter_form": form,
                "transactions": queryset,
                "total_income": total_income,
                "total_expense": total_expense,
                "balance": balance,
                "cashbox_balance": cashbox_balance,
                "debt": debt,
                "personal_balance": personal_balance,
                "total_paid_invoices": total_paid_invoices,
                "total_unpaid_invoices": total_unpaid_invoices,
                "page_title": "Касса",
                "active_section": "cashbox",
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        """Handle AJAX POST requests for DataTables.

        Applies filters, computes per-account statistics, paginates the
        results, and returns JSON data for DataTables rendering.
        """
        queryset = CashBox.objects.all()

        # --- Фильтры ---
        cash_box_number = request.POST.get("cash_box_number")
        if cash_box_number:
            queryset = queryset.filter(cash_box_number__icontains=cash_box_number)

        personal_account_id = request.POST.get("personal_account_number")
        if personal_account_id:
            queryset = queryset.filter(personal_account__id=personal_account_id)

        date = request.POST.get("date")
        if date:
            queryset = queryset.filter(date=date)

        is_conducted = request.POST.get("is_conducted")
        if is_conducted:
            queryset = queryset.filter(is_conducted=is_conducted == "True")

        payment_article = request.POST.get("payment_article")
        if payment_article:
            queryset = queryset.filter(payment_articles__id=payment_article)

        owner = request.POST.get("owner")
        if owner:
            queryset = queryset.filter(owner__id=owner)

        record_type = request.POST.get("record_type")
        if record_type:
            queryset = queryset.filter(payment_articles__record_type=record_type)

        # --- Статистика по персональному счёту ---
        total_paid_invoices = Decimal(0)
        total_unpaid_invoices = Decimal(0)
        debt = Decimal(0)
        personal_balance = Decimal(0)

        if personal_account_id:
            total_paid_invoices = Invoice.objects.filter(
                personal_account_id=personal_account_id, status="new"
            ).aggregate(total=Sum("items__total"))["total"] or Decimal(0)

            total_unpaid_invoices = Invoice.objects.filter(
                personal_account_id=personal_account_id, status__in=["zero", "counted"]
            ).aggregate(total=Sum("items__total"))["total"] or Decimal(0)

            debt = Invoice.objects.filter(
                personal_account_id=personal_account_id, status="zero"
            ).aggregate(total=Sum("items__total"))["total"] or Decimal(0)

            personal_balance = total_paid_invoices - total_unpaid_invoices

        # --- Пагинация ---
        start = int(request.POST.get("start", 0))
        length = int(request.POST.get("length", 50))
        data_page = queryset[start : start + length]

        # --- Формирование JSON ---
        data = [
            {
                "id": obj.id,
                "cash_box_number": obj.cash_box_number,
                "date": obj.date.strftime("%d.%m.%Y"),
                "is_conducted": "Да" if obj.is_conducted else "Нет",
                "payment_articles__name": obj.payment_articles.name,
                "owner_full_name": str(obj.owner) if obj.owner else "",
                "personal_account__account_number": (
                    obj.personal_account.account_number if obj.personal_account else ""
                ),
                "payment_articles__record_type": (
                    obj.payment_articles.get_record_type_display()
                ),
                "suma": f"{obj.suma:.2f}",
                "actions": (
                    f'<a href="/admin/cashbox/cashbox_card/{obj.id}/" '
                    f'class="btn btn-sm btn-primary">Открыть</a>'
                ),
            }
            for obj in data_page
        ]

        return JsonResponse(
            {
                "data": data,
                "recordsTotal": queryset.count(),
                "recordsFiltered": queryset.count(),
                "total_paid_invoices": float(total_paid_invoices),
                "total_unpaid_invoices": float(total_unpaid_invoices),
                "personal_balance": float(personal_balance),
                "debt": float(debt),
            }
        )


class ExpenseReportView(LoginRequiredMixin, RolePermissionRequiredMixin, CreateView):
    """View for creating a new expense report in the cashbox system."""

    template_name = "cashbox/expense_report.html"
    form_class = ExpenseReportForm
    success_url = reverse_lazy("admin:cashbox")
    role_permission = "has_cashbox"

    def get_context_data(self, **kwargs):
        """Add additional context data for the template."""
        context = super().get_context_data(**kwargs)
        context["active_section"] = "cashbox"
        return context

    def form_valid(self, form):
        """Handle valid form submission.

        Args:
            form (ExpenseReportForm): Validated form instance.

        Returns:
            HttpResponse: Redirect to success URL after saving.

        """
        return super().form_valid(form)

    def form_invalid(self, form):
        """Handle invalid form submission.

        Logs form validation errors for debugging purposes.

        Args:
            form (ExpenseReportForm): Invalid form instance.

        Returns:
            HttpResponse: Render the form again with validation errors.

        """
        logger.warning("[FORM INVALID] Ошибки формы: %s", form.errors.as_json())
        return super().form_invalid(form)


class UpdateExpenseReportView(
    LoginRequiredMixin, RolePermissionRequiredMixin, UpdateView
):
    """View for editing an existing expense report in the cashbox system."""

    template_name = "cashbox/expense_report.html"
    form_class = ExpenseReportForm
    success_url = reverse_lazy("admin:cashbox")
    model = CashBox
    role_permission = "has_cashbox"

    def get_context_data(self, **kwargs):
        """Add additional context data for the template."""
        context = super().get_context_data(**kwargs)
        context["active_section"] = "cashbox"
        return context

    def get_object(self, queryset=None):
        """Retrieve the CashBox instance to be updated.

        Returns:
            CashBox: The CashBox object retrieved by its primary key.

        """
        pk = self.kwargs.get("pk")
        return CashBox.objects.get(pk=pk)

    def form_valid(self, form):
        """Handle valid form submission for expense report update.

        Args:
            form (ExpenseReportForm): Validated form instance.

        Returns:
            HttpResponse: Redirect to success URL after saving.

        """
        return super().form_valid(form)

    def form_invalid(self, form):
        """Handle invalid form submission.

        Logs validation errors for debugging.

        Args:
            form (ExpenseReportForm): Invalid form instance.

        Returns:
            HttpResponse: Render the form again with validation errors.

        """
        logger.debug("[FORM INVALID] Ошибки формы: %s", form.errors.as_json())
        return super().form_invalid(form)


class ExpenseReportCopyView(LoginRequiredMixin, RolePermissionRequiredMixin, View):
    """View for copying an existing expense report (CashBox record)."""

    role_permission = "has_cashbox"

    def get_context_data(self, **kwargs):
        """Add context data for the view template.

        Returns:
            dict: Context dictionary containing active section data.

        """
        context = super().get_context_data(**kwargs)
        context["active_section"] = "cashbox"
        return context

    def get(self, request, pk):
        """Copy an existing CashBox record and redirect to its update view.

        Args:
            request (HttpRequest): The current HTTP request.
            pk (int): Primary key of the CashBox record to copy.

        Returns:
            HttpResponseRedirect: Redirect to the update view of the copied report.

        """
        original = get_object_or_404(CashBox, pk=pk)

        # Create a new CashBox copy
        copy = CashBox.objects.create(
            cash_box_number=generate_id_with_random_number(),
            date=original.date,
            is_conducted=original.is_conducted,
            payment_articles=original.payment_articles,
            personal_account=original.personal_account,
            suma=original.suma,
            comment=original.comment,
            manager=original.manager,
            owner=original.owner,
        )

        return redirect("admin:update_expense_report", pk=copy.pk)

class ReceiptStatementPcView(LoginRequiredMixin, RolePermissionRequiredMixin, CreateView):
    """Создание приходного ордера (ReceiptStatement) по лицевому счёту."""

    model = CashBox
    template_name = "cashbox/income_statement.html"
    form_class = ReceiptStatementForm
    success_url = reverse_lazy("admin:cashbox")
    role_permission = "has_cashbox"

    def get_context_data(self, **kwargs):
        """Добавляем лицевой счёт в контекст."""
        context = super().get_context_data(**kwargs)
        context["active_section"] = "cashbox"

        account_id = self.kwargs.get("pk")
        if account_id:
            account = PersonalAccount.objects.select_related("apartment", "user").get(pk=account_id)
            context["account"] = account
        return context

    def get_initial(self):
        """Автозаполнение формы по лицевому счёту."""
        initial = super().get_initial()
        account_id = self.kwargs.get("pk")

        if account_id:
            account = PersonalAccount.objects.select_related("apartment", "user").get(pk=account_id)

            # пробуем найти статью с названием "Коммунальный платеж"
            payment_article = (
                PaymentArticles.objects.filter(name__icontains="коммун")
                .filter(record_type="in")
                .first()
            )

            initial.update({
                "owner": account.user,
                "personal_account": account,
                "suma": 0,
                "manager": self.request.user,  # текущий пользователь
                "payment_articles": payment_article,  # если найдена статья
            })
        else:
            # даже если нет pk — менеджер всё равно текущий
            initial["manager"] = self.request.user
        return initial

    def form_valid(self, form):
        """При сохранении также привязываем платёж к счёту."""
        account_id = self.kwargs.get("pk")
        if account_id:
            account = PersonalAccount.objects.get(pk=account_id)
            form.instance.account = account
            form.instance.user = account.user
        return super().form_valid(form)

class ReceiptStatementView(LoginRequiredMixin, RolePermissionRequiredMixin, CreateView):
    """View for creating a new income (receipt) statement in the cashbox."""

    model = CashBox
    template_name = "cashbox/income_statement.html"
    form_class = ReceiptStatementForm
    success_url = reverse_lazy("admin:cashbox")
    role_permission = "has_cashbox"

    def get_context_data(self, **kwargs):
        """Add extra context data for the template.

        Args:
            **kwargs: Additional context keyword arguments.

        Returns:
            dict: Template context including active section.

        """
        context = super().get_context_data(**kwargs)
        context["active_section"] = "cashbox"
        return context

    def form_valid(self, form):
        """Handle valid form submission for creating a receipt statement.

        Args:
            form (ReceiptStatementForm): The validated form instance.

        Returns:
            HttpResponse: Redirect to the success URL after saving.

        """
        return super().form_valid(form)

    def form_invalid(self, form):
        """Handle invalid form submission and log validation errors.

        Args:
            form (ReceiptStatementForm): The invalid form instance.

        Returns:
            HttpResponse: Renders the form again with validation errors.

        """
        logger.warning("[FORM INVALID] Ошибки формы: %s", form.errors.as_json())
        return super().form_invalid(form)


class UpdateReceiptStatementView(
    LoginRequiredMixin, RolePermissionRequiredMixin, UpdateView
):
    """View for updating an existing income (receipt) statement in the cashbox."""

    template_name = "cashbox/income_statement.html"
    form_class = ReceiptStatementForm
    success_url = reverse_lazy("admin:cashbox")
    model = CashBox
    role_permission = "has_cashbox"

    def get_context_data(self, **kwargs):
        """Add extra context data for the template.

        Args:
            **kwargs: Additional context keyword arguments.

        Returns:
            dict: Template context including active section.

        """
        context = super().get_context_data(**kwargs)
        context["active_section"] = "cashbox"
        return context

    def get_object(self, queryset=None):
        """Retrieve the CashBox object to be edited.

        Args:
            queryset (QuerySet, optional): The base queryset. Defaults to None.

        Returns:
            CashBox: The CashBox instance retrieved by primary key.

        """
        pk = self.kwargs.get("pk")
        return CashBox.objects.get(pk=pk)

    def form_valid(self, form):
        """Handle valid form submission for updating a receipt statement.

        Args:
            form (ReceiptStatementForm): The validated form instance.

        Returns:
            HttpResponse: Redirect to the success URL after saving.

        """
        logger.info("[FORM VALID] Обновление приходной ведомости: %s", form.instance)
        return super().form_valid(form)

    def form_invalid(self, form):
        """Handle invalid form submission and log validation errors.

        Args:
            form (ReceiptStatementForm): The invalid form instance.

        Returns:
            HttpResponse: Renders the form again with validation errors.

        """
        logger.warning("[FORM INVALID] Ошибки формы: %s", form.errors.as_json())
        return super().form_invalid(form)


class ReceiptStatementCopyView(LoginRequiredMixin, RolePermissionRequiredMixin, View):
    """View for copying an existing income (receipt) statement (CashBox)."""

    role_permission = "has_cashbox"

    def get_context_data(self, **kwargs):
        """Add additional context data for the template.

        Args:
            **kwargs: Additional keyword arguments passed to the context.

        Returns:
            dict: Template context including active section data.

        """
        context = super().get_context_data(**kwargs)
        context["active_section"] = "cashbox"
        return context

    def get(self, request, pk):
        """Create a copy of an existing CashBox income statement.

        This method retrieves the original `CashBox` object by its primary key,
        creates an identical copy with a new ID and unique number,
        logs the action, and redirects the user to the update page
        for the new receipt statement.

        Args:
            request (HttpRequest): The current HTTP request object.
            pk (int): Primary key of the `CashBox` record to be copied.

        Returns:
            HttpResponseRedirect: Redirects to the update view for  .

        """
        # Retrieve the original CashBox object
        original = get_object_or_404(CashBox, pk=pk)

        # Create a new copy
        copy = CashBox.objects.create(
            cash_box_number=generate_id_with_random_number(),
            date=original.date,
            is_conducted=original.is_conducted,
            payment_articles=original.payment_articles,
            personal_account=original.personal_account,
            suma=original.suma,
            comment=original.comment,
            manager=original.manager,
            owner=original.owner,
        )

        # Log the successful creation of the copy
        logger.info(
            "[COPY] Копия приходной ведомости создана из %s → %s",
            original.pk,
            copy.pk,
        )

        # Redirect to the edit page of the copied record
        return redirect("admin:update_receipt_statement", pk=copy.pk)


class CashBoxDeleteView(LoginRequiredMixin, RolePermissionRequiredMixin, DeleteView):
    """View for deleting a CashBox record (income/expense statement)."""

    model = CashBox
    template_name = "cashbox/receipt_statement_confirm_delete.html"
    success_url = reverse_lazy("admin:cashbox")
    role_permission = "has_cashbox"

    def get_context_data(self, **kwargs):
        """Add additional context data for the deletion confirmation template.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            dict: Template context including the active section.

        """
        context = super().get_context_data(**kwargs)
        context["active_section"] = "cashbox"
        return context

    def delete(self, request, *args, **kwargs):
        """Handle deletion of the CashBox record and log the action.

        Args:
            request (HttpRequest): The current HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            HttpResponse: Redirect to the success URL after deletion.

        """
        obj = self.get_object()
        logger.info("[DELETE] Удаление приходной ведомости: %s", obj)
        return super().delete(request, *args, **kwargs)


class CardCashBoxView(LoginRequiredMixin, RolePermissionRequiredMixin, DetailView):
    """View for displaying detailed information about a CashBox record."""

    model = CashBox
    template_name = "cashbox/card_cash_box.html"
    context_object_name = "CashBox"
    role_permission = "has_cashbox"

    def get_context_data(self, **kwargs):
        """Add additional context data for the CashBox detail page.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            dict: Template context including the active section and the CashBox object.

        """
        context = super().get_context_data(**kwargs)
        cashbox = self.get_object()
        context["active_section"] = "cashbox"
        context["cashbox"] = cashbox
        return context


def export_user_cash_box_to_excel(request, cashbox_id):
    """Export cash box data of a user to an Excel file.

    Args:
        request (HttpRequest): HTTP request object.
        cashbox_id (int): ID of the cash box to export.

    Returns:
        HttpResponse: Excel file with cash box data.

    """
    cash_boxes = CashBox.objects.select_related(
        "personal_account", "payment_articles", "manager", "owner"
    ).filter(id=cashbox_id)

    rows = []
    for cash_box in cash_boxes:
        row = {
            "#": cash_box.cash_box_number,
            "Дата": cash_box.date,
            "Приход/Расход": cash_box.payment_articles.record_type,
            "Статус": "Проведен" if cash_box.is_conducted else "Не проведен",
            "Статья": cash_box.payment_articles.name,
            "Квитанция": "",
            "Услуга": "",
            "Сума": cash_box.suma,
            "Валюта": "грн",
            "Владелец": cash_box.owner.full_name if cash_box.owner else "",
            "Лицевой счёт": cash_box.personal_account.account_number
            if cash_box.personal_account
            else "",
        }
        rows.append(row)

    df_export = pd.DataFrame(rows)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_export.to_excel(writer, index=False, sheet_name="CashBox")

    output.seek(0)
    wb = load_workbook(output)
    ws = wb.active
    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            if cell.value:
                try:
                    max_length = max(max_length, len(str(cell.value)))
                except (TypeError, AttributeError) as e:
                    logger.warning("Error measuring cell %s: %s", cell.coordinate, e)
        ws.column_dimensions[col_letter].width = max_length + 2

    output_stream = BytesIO()
    wb.save(output_stream)
    output_stream.seek(0)

    response = HttpResponse(
        output_stream.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    filename = f"cash_box_user_{cashbox_id}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


class CounterView(
    LoginRequiredMixin, RolePermissionRequiredMixin, FormView, TemplateView
):
    """View for displaying and managing meter readings.

    Provides filtering and apartment context.
    Access restricted by role permission.
    """

    template_name = "counter/counter_lists.html"
    form_class = MeterReadingForm
    success_url = reverse_lazy("admin:counters")
    role_permission = "has_counter"

    def get_context_data(self, **kwargs):
        """Add extra context for template rendering.

        Returns:
            dict: Context with page title, active section, and optional apartment.

        """
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Счётчики"
        context["filter_form"] = self.get_form()
        context["apartment"] = None
        context["active_section"] = "counters"

        apartment_id = self.kwargs.get("apartment_id")
        if apartment_id:
            try:
                apartment = Apartment.objects.get(pk=apartment_id)
                context["apartment"] = apartment
            except Apartment.DoesNotExist:
                context["apartment_error"] = (
                    f"Апартаменты с ID={apartment_id} не найдены."
                )

        return context

    def post(self, request, *args, **kwargs):
        """Handle POST requests without redirecting.

        This allows AjaxDatatable to update data dynamically.
        """
        form = self.get_form()
        if form.is_valid():
            pass

        return self.get(request, *args, **kwargs)


class AddCounterView(LoginRequiredMixin, RolePermissionRequiredMixin, FormView):
    """View for adding a new Counter with detailed logging."""

    template_name = "counter/new_reading.html"
    form_class = CounterForm
    role_permission = "has_counter"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_section"] = "counters"
        logger.debug("Context data prepared: %s", context)
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        logger.debug("Form kwargs: %s", kwargs)
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        params = self.request.GET
        logger.debug("GET params: %s", params)
        if params.get("house"):
            initial["house"] = params["house"]
        if params.get("section"):
            initial["section"] = params["section"]
        if params.get("apartment"):
            initial["apartment"] = params["apartment"]
        logger.debug("Initial form data: %s", initial)
        return initial

    def form_valid(self, form):
        logger.debug("Form is valid: %s", form.cleaned_data)
        instance = form.save(commit=False)

        if not instance.date:
            instance.date = timezone.now().date()
            logger.debug("Date not provided, set to now: %s", instance.date)

        try:
            instance.save()
            logger.info("[FORM SAVE] Counter saved: %s (ID=%s)", instance, instance.pk)
        except Exception as e:
            logger.error("[FORM SAVE] Error saving counter: %s", e)
            raise

        self.object = instance

        if "action_save_add" in self.request.POST:
            query = urlencode(
                {
                    "house": instance.apartment.section.house.id,
                    "section": instance.apartment.section.id,
                    "apartment": instance.apartment.id,
                }
            )
            logger.debug("Redirecting to add another counter with query: %s", query)
            return redirect(f"{reverse('admin:counters_add')}?{query}")

        return super().form_valid(form)

    def form_invalid(self, form):
        logger.warning("[FORM INVALID] Form errors: %s", form.errors)
        return super().form_invalid(form)

    def get_success_url(self):
        url = reverse("admin:counters", args=[self.object.apartment.id])
        logger.debug("Success URL: %s", url)
        return url


class UpdateCounterView(LoginRequiredMixin, RolePermissionRequiredMixin, UpdateView):
    """Update a Counter object.

    If a primary key (pk) is provided in the URL, edits an existing Counter.
    Otherwise, creates a new Counter object with a default date.
    Access is restricted by user role.
    """

    model = Counter
    template_name = "counter/new_reading.html"
    form_class = CounterForm
    role_permission = "has_counter"

    def get_context_data(self, **kwargs):
        """Add context data for the Counter update view."""
        context = super().get_context_data(**kwargs)
        context["active_section"] = "counters"
        logger.debug("[CONTEXT DATA] Context prepared: %s", context)
        return context

    def get_object(self, queryset=None):
        """Retrieve the Counter object to edit, or create a new one."""
        pk = self.kwargs.get("pk")
        if pk:
            obj = get_object_or_404(Counter, pk=pk)
            logger.debug("[GET OBJECT] Editing Counter: %s (ID=%s)", obj, obj.pk)
            return obj
        # Create new object with default date
        obj = Counter(date=timezone.now())
        obj.counter_number = generate_id_with_random_number()
        logger.debug("[GET OBJECT] Creating new Counter: %s", obj)
        return obj

    def get_form_kwargs(self):
        """Pass request to the form and log kwargs."""
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        logger.debug("[FORM KWARGS] %s", kwargs)
        return kwargs

    def form_valid(self, form):
        """Handle valid form submission and save the Counter instance."""
        instance = form.save(commit=False)

        if not instance.counter_number:
            instance.counter_number = generate_id_with_random_number()
            logger.debug(
                "[FORM VALID] Generated new counter_number: %s", instance.counter_number
            )

        if not instance.date:
            instance.date = timezone.now()
            logger.debug("[FORM VALID] Set current date: %s", instance.date)

        instance.save()
        self.object = instance  # нужно для get_success_url
        logger.debug(
            "[FORM SAVE] Counter saved or updated: %s (ID=%s)", instance, instance.pk
        )

        if "action_save_add" in self.request.POST:
            logger.debug("[FORM VALID] User clicked 'save and add'. Redirecting...")
            return redirect("admin:counters_add")

        return super().form_valid(form)

    def form_invalid(self, form):
        """Handle invalid form submission with detailed debug."""
        logger.debug("[FORM INVALID] Form errors: %s", form.errors.as_json())
        logger.debug("[FORM INVALID] Bound data: %s", form.data)
        logger.debug(
            "[FORM INVALID] Form field querysets: %s",
            {f: getattr(form.fields[f], "queryset", "N/A") for f in form.fields},
        )
        return super().form_invalid(form)

    def get_success_url(self):
        """Redirect to the list of counters for the apartment."""
        if hasattr(self, "object") and self.object.apartment:
            url = reverse("admin:counters", args=[self.object.apartment.id])
            logger.debug("[SUCCESS URL] Redirecting to: %s", url)
            return url
        url = reverse("admin:counters_add")
        logger.debug("[SUCCESS URL] Fallback redirect to: %s", url)
        return url


class CounterlistView(
    LoginRequiredMixin, RolePermissionRequiredMixin, FormView, TemplateView
):
    """Display a list of Counter objects with optional form handling.

    This view allows viewing all counters and supports form
    interactions if needed. Access is restricted based on user roles.
    """

    template_name = "counter/counters.html"
    form_class = CounterFilterForm
    success_url = reverse_lazy("admin:counters")
    role_permission = "has_counter"

    def get_context_data(self, **kwargs):
        """Add extra context data for rendering the counter list template.

        Populates:
        - 'page_title': the title of the page shown in the UI

        Args:
            **kwargs: Arbitrary keyword arguments.

        Returns:
            dict: Context dictionary for the template.

        """
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Счётчики"
        context["filter_form"] = self.get_form()
        # Получаем apartment_id из kwargs
        apartment_id = self.kwargs.get("apartment_id")
        context["apartment"] = None
        context["active_section"] = "counters"
        if apartment_id:
            try:
                apartment = Apartment.objects.get(pk=apartment_id)
                context["apartment"] = apartment
            except Apartment.DoesNotExist:
                # Можно логировать или показывать кастомное сообщение
                context["apartment_error"] = (
                    f"Апартаменты с ID={apartment_id} не найдены."
                )

        return context


class CardCounterView(LoginRequiredMixin, RolePermissionRequiredMixin, DetailView):
    """Display details of a Counter object.

    This view shows information about a single Counter, including
    related tariff services. Access is restricted by user role.
    """

    model = Counter
    template_name = "counter/counter_card.html"
    context_object_name = "Counter"
    role_permission = "has_counter"

    def get_context_data(self, **kwargs):
        """Display details of a Counter object.

        This view shows information about a single Counter, including
        related tariff services. Access is restricted by user role.
        """
        context = super().get_context_data(**kwargs)
        counter = self.get_object()
        context["active_section"] = "counters"
        # Получаем все услуги тарифа
        context["counter"] = counter

        return context


# 5
class HouseView(LoginRequiredMixin, RolePermissionRequiredMixin, ListView, FormView):
    """View for managing buildings or houses."""

    model = House
    template_name = "house/house_list2.html"
    form_class = FilterForm
    success_url = reverse_lazy("admin:house")
    role_permission = "has_house"

    def get_queryset(self):
        """Return all houses for superuser, otherwise filter by user's permissions."""
        user = self.request.user
        if user.is_superuser:
            return House.objects.all()

        return House.objects.filter(staff__user=user).distinct()

    def get_context_data(self, **kwargs):
        """Add page title and filter form to the context."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Дома"
        context["filter_form"] = self.get_form()
        context["active_section"] = "house"
        return context

    def post(self, request, *args, **kwargs):
        """Handle a POST request without redirecting.

        This allows AjaxDatatable to refresh the data.
        """
        form = self.get_form()
        if form.is_valid():
            pass  # Дополнительно можно использовать данные формы для фильтрации

        return self.get(request, *args, **kwargs)


class HouseAddView(LoginRequiredMixin, RolePermissionRequiredMixin, FormView):
    """View for adding a new House, including related sections, floors, and staff."""

    template_name = "house/new_house.html"
    form_class = HouseForm
    success_url = reverse_lazy("admin:house")
    role_permission = "has_house"

    def get_context_data(self, **kwargs):
        """Prepare context data for HouseAddView with debug logging."""
        context = super().get_context_data(**kwargs)

        # Только пользователи с is_staff=True
        users_qs = User.objects.filter(is_staff=True).select_related("role")
        user_roles = {user.pk: user.role.name if user.role else "" for user in users_qs}

        logger.debug(
            "HouseAddView.get_context_data(): found %d staff users", users_qs.count()
        )
        logger.debug("HouseAddView.get_context_data(): user_roles=%s", user_roles)

        context["user_roles_json"] = json.dumps(user_roles)
        context["users"] = users_qs
        context["active_section"] = "house"

        if self.request.method == "POST":
            logger.debug("HouseAddView.get_context_data(): rendering with POST data")
            context["section_set"] = SectionFormSet(self.request.POST, prefix="section")
            context["floor_set"] = FloorFormSet(self.request.POST, prefix="floor")
            context["staff_set"] = StaffFormSet(
                self.request.POST,
                prefix="staff",
                form_kwargs={"user_roles": user_roles},
            )
        else:
            logger.debug(
                "HouseAddView.get_context_data(): rendering initial empty formsets"
            )
            context["section_set"] = SectionFormSet(prefix="section")
            context["floor_set"] = FloorFormSet(prefix="floor")
            context["staff_set"] = StaffFormSet(
                prefix="staff", form_kwargs={"user_roles": user_roles}
            )

        return context

    def form_valid(self, form):
        """Save the House and related formsets with debug logging."""
        context = self.get_context_data()
        section_set = context["section_set"]
        floor_set = context["floor_set"]
        staff_set = context["staff_set"]

        logger.debug("=== HouseAddView.form_valid() called ===")
        logger.debug("Main form valid: %s | errors: %s", form.is_valid(), form.errors)
        logger.debug(
            "Section set valid: %s | errors: %s",
            section_set.is_valid(),
            section_set.errors,
        )
        logger.debug(
            "Floor set valid: %s | errors: %s", floor_set.is_valid(), floor_set.errors
        )
        logger.debug(
            "Staff set valid: %s | errors: %s", staff_set.is_valid(), staff_set.errors
        )

        if section_set.is_valid() and floor_set.is_valid() and staff_set.is_valid():
            with transaction.atomic():
                # Сохраняем дом
                self.object = form.save()
                logger.debug(
                    "✅ House saved successfully: id=%s, title=%s",
                    self.object.id,
                    self.object.title,
                )

                # Привязываем и сохраняем связанные формы
                section_set.instance = self.object
                staff_set.instance = self.object

                sections = section_set.save()
                logger.debug("✅ Sections saved: %s", [s.name for s in sections])

                staff_set.save()
                logger.debug("✅ Staff formset saved successfully")

                # Сохраняем этажи
                floors = floor_set.save(commit=False)
                for floor in floors:
                    floor.house = self.object
                    if sections:
                        floor.section = sections[0]
                    floor.save()
                    logger.debug("✅ Floor saved: id=%s, name=%s", floor.id, floor.name)
                for deleted in floor_set.deleted_objects:
                    logger.debug("🗑️ Floor deleted: %s", deleted)

            logger.debug("=== HouseAddView.form_valid() finished successfully ===")
            return super().form_valid(form)

        if hasattr(section_set, "management_form"):
            logger.debug(
                "Section management form errors: %s", section_set.management_form.errors
            )
        if hasattr(floor_set, "management_form"):
            logger.debug(
                "Floor management form errors: %s", floor_set.management_form.errors
            )
        if hasattr(staff_set, "management_form"):
            logger.debug(
                "Staff management form errors: %s", staff_set.management_form.errors
            )

        logger.debug("===========================================")
        return self.form_invalid(form)


class HouseUpdateView(LoginRequiredMixin, RolePermissionRequiredMixin, UpdateView):
    """Update a House along with its sections, floors, and staff members.

    This view allows editing the main House object and handles inline formsets
    for related Sections, Staff, and Floors. It validates all formsets and
    saves or deletes related objects atomically.
    """

    model = House
    template_name = "house/new_house.html"
    form_class = HouseForm
    success_url = reverse_lazy("admin:house")
    role_permission = "has_house"

    def get_context_data(self, **kwargs):
        """Add context data for rendering the house update template.

        Populates context with:
        - JSON of user roles
        - Section, Staff, and Floor formsets
        - Active section identifier for navigation

        Args:
            **kwargs: Arbitrary keyword arguments.

        Returns:
            dict: Context dictionary with formsets and extra data.

        """
        context = super().get_context_data(**kwargs)

        user_roles = {
            user.pk: user.role.name if user.role else ""
            for user in User.objects.select_related("role").all()
        }
        context["user_roles_json"] = json.dumps(user_roles)

        data = self.request.POST if self.request.method == "POST" else None

        context["section_set"] = SectionFormSet(
            data, prefix="section", instance=self.object
        )
        context["staff_set"] = StaffFormSet(
            data,
            prefix="staff",
            instance=self.object,
            form_kwargs={"user_roles": user_roles},
        )
        context["floor_set"] = FloorFormSet(data, prefix="floor", instance=self.object)
        context["active_section"] = "house"
        return context

    def form_valid(self, form):
        """Save the main House form along with its related formsets.

        Validates all formsets (sections, staff, floors). If all are valid,
        saves objects in a transaction; otherwise, returns form_invalid.

        Args:
            form: Main House form.

        Returns:
            HttpResponse: Redirects on success or re-renders the form on failure.

        """
        context = self.get_context_data()
        section_set = context["section_set"]
        staff_set = context["staff_set"]
        floor_set = context["floor_set"]

        logger.debug("=== HouseUpdateView.form_valid() called ===")
        logger.debug("Main form valid: %s | errors: %s", form.is_valid(), form.errors)
        logger.debug(
            "Section valid: %s | errors: %s", section_set.is_valid(), section_set.errors
        )
        logger.debug(
            "Staff valid: %s | errors: %s", staff_set.is_valid(), staff_set.errors
        )
        logger.debug(
            "Floor valid: %s | errors: %s", floor_set.is_valid(), floor_set.errors
        )

        if section_set.is_valid() and staff_set.is_valid() and floor_set.is_valid():
            with transaction.atomic():
                self.object = form.save()
                logger.debug("House saved: %s", self.object)

                section_set.instance = self.object
                staff_set.instance = self.object
                floor_set.instance = self.object

                # Save Sections
                for section in section_set.save(commit=False):
                    section.house = self.object
                    section.save()
                    logger.debug("Section saved: %s", section)
                for section in section_set.deleted_objects:
                    logger.debug("Section deleted: %s", section)
                    section.delete()

                # Save Staff
                for staff in staff_set.save(commit=False):
                    staff.house = self.object
                    staff.save()
                    logger.debug("Staff saved: %s", staff)
                for staff in staff_set.deleted_objects:
                    logger.debug("Staff deleted: %s", staff)
                    staff.delete()

                logger.debug("Staff formset saved successfully.")

                # Save Floors
                for floor in floor_set.save(commit=False):
                    floor.house = self.object
                    floor.save()
                    logger.debug("Floor saved: %s", floor)
                for floor in floor_set.deleted_objects:
                    logger.debug("Floor deleted: %s", floor)
                    floor.delete()

            logger.debug("=== HouseUpdateView.form_valid() finished successfully ===")
            return super().form_valid(form)

        logger.debug(
            "=== HouseUpdateView.form_valid() failed due to invalid formsets ==="
        )
        return self.form_invalid(form)

    def form_invalid(self, form):
        """Handle invalid form submissions.

        Logs errors and re-renders the form with validation messages.

        Args:
            form: Main House form.

        Returns:
            HttpResponse: Rendered response with form errors.

        """
        logger.debug("=== HouseUpdateView.form_invalid() called ===")
        logger.debug("POST data: %s", self.request.POST.dict())
        logger.debug("Main form errors: %s", form.errors)
        logger.debug("===========================================")
        return super().form_invalid(form)


class CardHouseView(LoginRequiredMixin, RolePermissionRequiredMixin, TemplateView):
    """View for displaying the user's personal cabinet page."""

    template_name = "house/house_card.html"
    role_permission = "has_house"

    def get_context_data(self, **kwargs):
        """Add additional context for the House detail template.

        Populates context with page title, staff list, and other related data.

        Args:
            **kwargs: Arbitrary keyword arguments passed to the context.

        Returns:
            dict: Context dictionary including page title, staff list, and other
                  relevant information for rendering the template.

        """
        context = super().get_context_data(**kwargs)
        context["page_title"] = "House"
        context["active_section"] = "house"
        house_id = self.kwargs.get("pk")
        house = get_object_or_404(House, pk=house_id)
        num_floors = house.floors.count()
        staff_list = house.staff.all()

        context["house"] = house

        context["num_floors"] = num_floors
        context["staff_list"] = staff_list

        logger.debug("Context data for CardUserView: %s", context)
        return context


class HouseDeleteView(LoginRequiredMixin, RolePermissionRequiredMixin, DeleteView):
    """View for deleting a house."""

    model = House
    template_name = "house/house_confirm_delete.html"
    success_url = reverse_lazy("admin:house")
    role_permission = "has_house"

    def delete(self, request, *args, **kwargs):
        """Add success message after deletion."""
        house = self.get_object()
        messages.success(request, f"Дом '{house.title}' был успешно удалён.")
        return super().delete(request, *args, **kwargs)


# ToDo Квитанции
class InvoiceView(LoginRequiredMixin, RolePermissionRequiredMixin, ListView, FormView):
    """View for managing invoices and receipts."""

    model = Invoice
    form_class = InvoiceFilterForm
    template_name = "invoice/invoice_list.html"
    role_permission = "has_invoice"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        # Баланс всей кассы
        cashbox_income = CashBox.objects.filter(
            is_conducted=True, payment_articles__record_type="in"
        ).aggregate(total=Sum("suma"))["total"] or Decimal(0)
        cashbox_expense = CashBox.objects.filter(
            is_conducted=True, payment_articles__record_type="out"
        ).aggregate(total=Sum("suma"))["total"] or Decimal(0)
        cashbox_balance = cashbox_income - cashbox_expense

        debt = Decimal(0)
        total_paid_invoices = Decimal(0)
        total_unpaid_invoices = Decimal(0)
        personal_balance = Decimal(0)

        total_paid_invoices = Invoice.objects.filter(status="new").aggregate(
            total=Sum("items__total")
        )["total"] or Decimal(0)

        total_unpaid_invoices = Invoice.objects.filter(
            status__in=["zero", "counted"]
        ).aggregate(total=Sum("items__total"))["total"] or Decimal(0)

        debt = Invoice.objects.filter(status="zero").aggregate(
            total=Sum("items__total")
        )["total"] or Decimal(0)

        personal_balance = total_paid_invoices - total_unpaid_invoices

        context = super().get_context_data(**kwargs)
        context["debt"] = debt
        context["personal_balance"] = personal_balance
        context["cashbox_balance"] = cashbox_balance
        context["page_title"] = "Квитанции"
        context["filter_form"] = self.get_form()
        context["active_section"] = "invoice"
        return context


class InvoiceDetailView(LoginRequiredMixin, RolePermissionRequiredMixin, DetailView):
    """View to display detailed information about a single Invoice.

    Only users with the appropriate role permission can access this view.
    Renders the invoice detail template with additional context.
    """

    model = Invoice
    template_name = "invoice/card_invoice.html"
    context_object_name = "invoice"
    role_permission = "has_invoice"

    def get_context_data(self, **kwargs):
        """Add additional context to the invoice detail template.

        Args:
            **kwargs: Arbitrary keyword arguments.

        Returns:
            dict: Context dictionary including the invoice instance and
                  any additional related data.

        """
        context = super().get_context_data(**kwargs)
        invoice = self.get_object()

        invoice_items = InvoiceItem.objects.filter(invoice=invoice)
        context["items"] = invoice_items
        context["total_sum"] = invoice_items.aggregate(Sum("total"))["total__sum"] or 0

        # безопасное обращение к пользователю
        personal_account = invoice.personal_account
        context["invoice_user"] = personal_account.user if personal_account else None

        # чтобы меню работало
        context["active_section"] = "invoice"

        return context


class CreateInvoiceView(LoginRequiredMixin, RolePermissionRequiredMixin, CreateView):
    """View to create a new Invoice instance.

    Only users with the appropriate role permission can access this view.
    Handles both the main invoice form and its related formset.
    """

    model = Invoice
    form_class = InvoiceForm
    template_name = "invoice/invoice_create.html"
    success_url = reverse_lazy("admin:invoice")
    role_permission = "has_invoice"

    def get_context_data(self, **kwargs):
        """Add formset and additional context for rendering the create template.

        Args:
            **kwargs: Arbitrary keyword arguments.

        Returns:
            dict: Context dictionary for the template.

        """
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formset"] = TarifServiceItem_inlinformset(
                self.request.POST, prefix="items"
            )
        else:
            context["formset"] = TarifServiceItem_inlinformset(prefix="items")
        context["active_section"] = "invoice"
        return context

    def post(self, request, *args, **kwargs):
        """Handle POST requests: validate main form and its formset.

        Args:
            request (HttpRequest): The current request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: Redirect on success or re-rendered template with errors.

        """
        self.object = None
        form = self.get_form()
        formset = TarifServiceItem_inlinformset(self.request.POST, prefix="items")

        logger.debug("POST received for CreateInvoiceView")
        logger.debug("Form data: %s", request.POST)

        if form.is_valid() and formset.is_valid():
            logger.info("Invoice form and formset are valid")
            return self.forms_valid(form, formset)
        logger.warning("Invoice form or formset invalid")
        logger.warning("Form errors: %s", form.errors)
        logger.warning("Formset errors: %s", formset.errors)
        return self.forms_invalid(form, formset)

    def forms_valid(self, form, formset):
        """Save the main form and its formset if both are valid.

        Automatically fills missing date fields with today's date.

        Args:
            form (InvoiceForm): The validated invoice form.
            formset (InvoiceItemFormSet): The validated formset.

        Returns:
            HttpResponse: Redirect to success_url after saving.

        """
        self.object = form.save(commit=True)

        if not self.object.tariff_id:
            form.add_error("tariff", "Не выбран тариф")
            return self.forms_invalid(form, formset)

        # Проверяем и преобразуем даты
        for field_name in ["mount", "date", "start_date", "end_date"]:
            value = getattr(self.object, field_name, None)
            if isinstance(value, str):
                try:
                    setattr(self.object, field_name, datetime.date.fromisoformat(value))
                except ValueError:
                    form.add_error(field_name, "Некорректный формат даты")
                    return self.forms_invalid(form, formset)
            elif value is None:
                setattr(self.object, field_name, timezone.now().date())

        formset.instance = self.object
        formset.save()

        return redirect(self.success_url)

    def forms_invalid(self, form, formset):
        """Render the form and formset with validation errors.

        Args:
            form (InvoiceForm): The invalid invoice form.
            formset (InvoiceItemFormSet): The invalid formset.

        Returns:
            HttpResponse: Rendered template with form errors.

        """
        logger.error("Rendering form with errors")
        return self.render_to_response(
            self.get_context_data(form=form, formset=formset)
        )
class CreateInvoicePcView(LoginRequiredMixin, RolePermissionRequiredMixin, CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "invoice/invoice_create.html"
    success_url = reverse_lazy("admin:invoice")
    role_permission = "has_invoice"

    def get_initial(self):
        initial = super().get_initial()
        account_id = self.kwargs.get("account_id")
        if account_id:
            try:
                account = PersonalAccount.objects.select_related(
                    "apartment",
                    "user",
                    "apartment__house",
                    "apartment__section"
                ).get(pk=account_id)
                apartment = account.apartment
                initial["personal_account"] = account
                initial["flat"] = apartment
                initial["section"] = apartment.section
                initial["house"] = apartment.house
                initial["tariff"] = apartment.tariff
                if apartment.user:
                    initial["owner"] = apartment.user.full_name
                    initial["phone"] = apartment.user.phone
            except PersonalAccount.DoesNotExist:
                pass
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        account_id = self.kwargs.get("account_id")
        if account_id:
            account = PersonalAccount.objects.select_related("apartment", "user").get(pk=account_id)
            context["account"] = account
        return context

    def form_valid(self, form):
        account_id = self.kwargs.get("account_id")

        if account_id:
            account = PersonalAccount.objects.select_related(
                "apartment",
                "user",
                "apartment__tariff"
            ).get(pk=account_id)

            form.instance.personal_account = account
            form.instance.flat = account.apartment
            form.instance.tariff = account.apartment.tariff  # ✅ Правильно

        form.instance.manager = self.request.user

        if not form.instance.invoice_number:
            form.instance.invoice_number = generate_id_with_random_number()

        return super().form_valid(form)


class UpdateInvoiceView(LoginRequiredMixin, RolePermissionRequiredMixin, UpdateView):
    """View to update an existing Invoice instance.

    Only users with the appropriate role permission can access this view.
    Handles both the main invoice form and its related formset.
    """

    model = Invoice
    form_class = InvoiceForm
    template_name = "invoice/invoice_create.html"  # Можно оставить тот же шаблон
    success_url = reverse_lazy("admin:invoice")
    role_permission = "has_invoice"

    def get_object(self, queryset=None):
        """Retrieve the Invoice object based on the 'pk' URL parameter.

        Args:
            queryset (QuerySet, optional): Not used. Defaults to None.

        Returns:
            Invoice: The invoice instance to update.

        """
        # Получаем объект по pk из URL
        pk = self.kwargs.get("pk")
        return get_object_or_404(Invoice, pk=pk)

    def get_context_data(self, **kwargs):
        """Add formset and additional context for rendering the update template.

        Args:
            **kwargs: Arbitrary keyword arguments.

        Returns:
            dict: Context dictionary for the template.

        """
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formset"] = TarifServiceItem_inlinformset(
                self.request.POST, instance=self.object, prefix="items"
            )
        else:
            context["formset"] = TarifServiceItem_inlinformset(
                instance=self.object, prefix="items"
            )
        context["active_section"] = "invoice"
        return context

    def post(self, request, *args, **kwargs):
        """Handle POST requests: validate main form and its formset.

        Args:
            request (HttpRequest): The current request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: Redirect on success or re-rendered template with errors.

        """
        self.object = self.get_object()
        form = self.get_form()
        formset = TarifServiceItem_inlinformset(
            self.request.POST, instance=self.object, prefix="items"
        )

        logger.debug("POST received for UpdateInvoiceView")
        logger.debug("Form data: %s", request.POST)

        if form.is_valid() and formset.is_valid():
            logger.info("Invoice form and formset are valid")
            return self.forms_valid(form, formset)
        logger.warning("Invoice form or formset invalid")
        logger.warning("Form errors: %s", form.errors)
        logger.warning("Formset errors: %s", formset.errors)
        return self.forms_invalid(form, formset)

    def forms_valid(self, form, formset):
        """Save the main form and its formset if both are valid.

        Args:
            form (InvoiceForm): The validated invoice form.
            formset (InvoiceItemFormSet): The validated formset.

        Returns:
            HttpResponse: Redirect to success_url after saving.

        """
        self.object = form.save(commit=True)

        service_id = self.request.POST.get("tariff")
        if service_id:
            self.object.service_id = service_id
        else:
            form.add_error("tariff", "Не выбран сервис")
            return self.forms_invalid(form, formset)

        # Приведение дат
        for field_name in ["mount", "date", "start_date", "end_date"]:
            value = getattr(self.object, field_name, None)
            if isinstance(value, str):
                try:
                    setattr(self.object, field_name, datetime.date.fromisoformat(value))
                except ValueError:
                    form.add_error(field_name, "Некорректный формат даты")
                    return self.forms_invalid(form, formset)
            elif value is None:
                setattr(self.object, field_name, timezone.now().date())

        self.object.save()

        formset.instance = self.object
        formset.save()

        logger.info("Invoice %s успешно обновлён", self.object.id)
        return redirect(self.success_url)

    def forms_invalid(self, form, formset):
        """Render the form and formset with validation errors.

        Args:
            form (InvoiceForm): The invalid invoice form.
            formset (InvoiceItemFormSet): The invalid formset.

        Returns:
            HttpResponse: Rendered template with form errors.

        """
        logger.error("Rendering form with errors")
        return self.render_to_response(
            self.get_context_data(form=form, formset=formset)
        )


class DeleteInvoiceView(LoginRequiredMixin, RolePermissionRequiredMixin, DeleteView):
    """View to delete an Invoice instance.

    Only users with the appropriate role permission can access this view.
    Logs the deletion of an invoice with the current user.
    """

    model = Invoice
    template_name = (
        "invoice/invoice_confirm_delete.html"  # Шаблон подтверждения удаления
    )
    success_url = reverse_lazy("admin:invoice")
    role_permission = "has_invoice"

    def delete(self, request, *args, **kwargs):
        """Handle deletion of an invoice.

        Retrieves the invoice object, deletes it, logs the deletion,
        and returns the standard DeleteView response.

        Args:
            request (HttpRequest): The current request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: Redirect or response after deletion.

        """
        self.object = self.get_object()
        invoice_number = self.object.invoice_number
        response = super().delete(request, *args, **kwargs)

        logger.info("Invoice %s удален пользователем %s", invoice_number, request.user)
        return response


class TemplateListView(LoginRequiredMixin, RolePermissionRequiredMixin, ListView):
    """View to display a list of invoice templates.

    Accessible only to users with the 'has_invoice' role permission.
    """

    model = Template
    template_name = "invoice/list_template.html"
    context_object_name = "templates"
    role_permission = "has_invoice"

    def get_context_data(self, **kwargs):
        """Get context data for rendering the template list.

        Adds the 'invoice_id' from URL kwargs to the context.

        Returns:
            dict: Context dictionary for rendering the template.

        """
        context = super().get_context_data(**kwargs)
        invoice_id = self.kwargs.get("invoice_id")
        if invoice_id:
            context["invoice"] = get_object_or_404(Invoice, pk=invoice_id)

        context["active_section"] = "invoice"
        return context


class AddTemplateView(LoginRequiredMixin, RolePermissionRequiredMixin, View):
    """View for managing invoice templates.

    Provides the ability to list, add, and update templates.
    Only accessible to users with the 'has_invoice' role permission.
    """

    template_name = "invoice/add_template.html"
    success_url = "admin:add_template"
    role_permission = "has_invoice"

    def get_context_data(self, **kwargs):
        """Add active section info for highlighting."""
        context = super().get_context_data(**kwargs)
        context["active_section"] = "invoice"
        return context

    def get(self, request):
        """Display all invoice templates."""
        formset = TemplateFormSet(queryset=Template.objects.all())
        return render(request, self.template_name, {"formset": formset})

    def post(self, request):
        """Создание или обновление шаблонов."""
        logger.debug("Received POST data: %s", request.POST.dict())

        formset = TemplateFormSet(
            request.POST,
            request.FILES,
            queryset=Template.objects.all()
        )

        self._allow_empty_forms(formset)

        # 🔹 Определяем, какой шаблон выбран по радио
        selected_default_id = request.POST.get("default_template")
        logger.debug("Selected default template ID: %s", selected_default_id)

        if formset.is_valid():
            instances = formset.save(commit=False)

            # 🔹 Сбрасываем флаг is_default у всех
            Template.objects.update(is_default=False)

            # 🔹 Присваиваем is_default=True выбранному
            if selected_default_id:
                try:
                    selected_template = Template.objects.get(pk=selected_default_id)
                    selected_template.is_default = True
                    selected_template.save(update_fields=["is_default"])
                    logger.info("Template '%s' назначен по умолчанию",
                                selected_template.name)
                except Template.DoesNotExist:
                    logger.warning("Выбранный шаблон (ID=%s) не найден",
                                   selected_default_id)

            # 🔹 Сохраняем остальные шаблоны
            for instance in instances:
                instance.save()
            formset.save_m2m()

            # 🔹 Удаляем отмеченные
            for deleted in formset.deleted_objects:
                deleted.delete()

            return redirect(self.success_url)

        # Если невалидно — логируем ошибки
        self._log_form_errors(formset)
        return render(request, self.template_name, {"formset": formset})

    def _allow_empty_forms(self, formset):
        """Allow empty forms for new templates."""
        for form in formset.forms:
            if not form.instance.pk:
                form.empty_permitted = True

    def _save_formset_with_default_check(self, formset):
        """Save formset and ensure only one template is default."""
        instances = formset.save(commit=False)
        logger.debug("Saving %d instances...", len(instances))

        # Проверяем наличие дефолтного шаблона
        default_templates = [inst for inst in instances if
                             getattr(inst, "is_default", False)]
        if default_templates:
            logger.debug("Found default template(s): %s",
                         [t.name for t in default_templates])
            Template.objects.exclude(pk__in=[t.pk for t in default_templates]).update(
                is_default=False)
        else:
            logger.debug("No default template marked among saved instances.")

        for instance in instances:
            file_field = getattr(instance, "file", None)
            if file_field:
                logger.debug("Template '%s': file name before save — %s", instance.name,
                             file_field.name)
            instance.save()
            if file_field:
                logger.debug("Template '%s' saved. File path: %s", instance.name,
                             instance.file.path if instance.file else "None")

        formset.save_m2m()

        for deleted in formset.deleted_objects:
            logger.info("Deleting template id=%s, name=%s", deleted.pk, deleted.name)
            deleted.delete()

    def _log_form_errors(self, formset):
        """Detailed formset error logging."""
        logger.warning("Template formset invalid — total errors: %d",
                       len(formset.errors))
        for i, form in enumerate(formset.forms):
            if form.errors:
                logger.warning("Form #%d errors: %s", i, form.errors)
            if form.non_field_errors():
                logger.warning("Form #%d non-field errors: %s", i,
                               form.non_field_errors())


def download_invoice(request, invoice_id):
    """Download an invoice as an Excel file."""
    template_name = request.GET.get("template", "Шаблон Квитанции.xlsm")

    try:
        output_path = Path(fill_invoice_to_excel(invoice_id, template_name))

        if not output_path.exists():
            raise Http404("Файл не найден")

        # Открываем файл и передаём в FileResponse без закрытия
        file_handle = output_path.open("rb")
        filename = quote(output_path.name)

        response = FileResponse(file_handle, as_attachment=True)
        response["Content-Disposition"] = f"attachment; filename*=UTF-8''{filename}"
        response["Content-Type"] = "application/vnd.ms-excel.sheet.macroEnabled.12"

        return response

    except (FileNotFoundError, OSError) as e:
        return HttpResponse(f"Ошибка при формировании квитанции: {e}", status=500)

from django.http import FileResponse
from urllib.parse import quote

def download_invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)

    default_template = Template.objects.filter(is_default=True).first()
    if not default_template:
        return HttpResponse("Нет шаблона по умолчанию для квитанции!", status=500)

    paths = []  # список временных файлов для последующей очистки

    try:
        # Формируем все временные файлы
        xlsx_path = Path(fill_invoice_to_excel(invoice_id, template_name=default_template.file.name))
        paths.append(xlsx_path)

        html_path = Path(excel_to_html_openpyxl(xlsx_path))
        paths.append(html_path)

        pdf_path = Path(html_to_pdf(html_path))
        paths.append(pdf_path)

        # Открываем PDF через контекстный менеджер, чтобы гарантированно закрыть файл
        with pdf_path.open("rb") as file_handle:
            filename = quote(f"invoice_{invoice.invoice_number}.pdf")
            response = FileResponse(file_handle, as_attachment=True)
            response["Content-Disposition"] = f"attachment; filename*=UTF-8''{filename}"
            response["Content-Type"] = "application/pdf"
            return response

    except (OSError, ValueError) as e:
        logger.exception("Ошибка при формировании PDF для счёта %s", invoice_id)
        return HttpResponse(f"Ошибка при формировании PDF: {e}", status=500)

    finally:
        # Очистка всех временных файлов
        for path in paths:
            if path.exists():
                try:
                    path.unlink()
                except OSError as cleanup_e:
                    logger.warning("Ошибка удаления временного файла %s: %s", path, cleanup_e)

def send_invoice_email_view(request, invoice_id):
    """Send an invoice email for the given invoice ID.

    Args:
        request: HttpRequest object.
        invoice_id: ID of the invoice to send.

    Returns:
        JsonResponse indicating success or failure.

    """
    invoice = get_object_or_404(Invoice, id=invoice_id)

    recipient_email = (
        invoice.personal_account.user.email
        if invoice.personal_account and invoice.personal_account.user
        else None
    )
    if not recipient_email:
        messages.error(request, "Email получателя не найден.")
        return redirect(request.headers.get("referer", "/admin/invoice/"))

    send_invoice_pdf_email.delay(invoice.id, recipient_email)

    messages.success(
        request, f"Квитанция #{invoice.invoice_number} отправлена на {recipient_email}."
    )
    return redirect(request.headers.get("referer", "/admin/invoice/"))


def get_tariff_service_info(request):
    """Retrieve detailed information for a TariffService.

    Args:
        request: HttpRequest with GET parameter 'id' for TariffService.

    Returns:
        JsonResponse containing tariff service data.

    """
    ts_id = request.GET.get("id")
    ts = TariffService.objects.select_related("unit").get(id=ts_id)
    return JsonResponse(
        {
            "unit": ts.unit.name,
            "price": str(ts.price),
            "currency": ts.currency,
        }
    )


# 7


class MessagesView(LoginRequiredMixin, RolePermissionRequiredMixin, ListView):
    """View for displaying and managing messages."""

    model = Message
    template_name = "messages/message_list.html"
    context_object_name = "messages"
    role_permission = "has_message"

    def get_context_data(self, **kwargs):
        """Add additional context data for Messages view.

        Returns:
            dict: Context including page title and other required data.

        """
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Сообщения"
        context["active_section"] = "message"
        messages_data = []
        for message in context["messages"]:
            recipients_display = self.get_recipients_display(message)
            messages_data.append(
                {
                    "id": message.id,
                    "title": message.title,
                    "text": message.text,
                    "created_at": localtime(message.created_at),
                    "recipients_display": recipients_display,
                }
            )

        context["messages_data"] = messages_data
        return context

    def get_recipients_display(self, message):
        """Return a human-readable string of message recipients.

        Builds a readable representation of all recipients associated with
        the given message, including details about their apartments
        (house, section, floor, and apartment number).

        Args:
            message (Message): The message instance whose recipients are displayed.

        Returns:
            str: A semicolon-separated list of recipient information. If no
            recipients are found, returns "Всем".

        """
        recipients = message.recipients.all()

        recipients_info = [
            f"{u.get_full_name() or u.username} ({u.email})" for u in recipients
        ]
        logger.info(
            "[MessagesView] Message ID=%s — получатели: %s",
            message.id,
            recipients_info,
        )

        if not recipients.exists():
            return "Всем"

        display_list = []
        for user in recipients:
            apartments = user.apartments.select_related("house", "section", "floor")
            if apartments.exists():
                for apt in apartments:
                    s = (
                        f'ЖК "{apt.house.title}", Секция {apt.section.name},'
                        f" Этаж {apt.floor.name}"
                    )
                    if apt.apartment_number:
                        s += f", кв.{apt.apartment_number}"
                    display_list.append(s)
            else:
                display_list.append(user.get_full_name() or user.username)

        return "; ".join(display_list)


class MessagesDetailView(LoginRequiredMixin, RolePermissionRequiredMixin, DetailView):
    """View for displaying and managing messages."""

    model = Message
    template_name = "messages/message_detail.html"
    role_permission = "has_message"

    def get_context_data(self, **kwargs):
        """Add  the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Сообщенния"
        context["active_section"] = "message"
        return context


class MessagesDeleteView(LoginRequiredMixin, RolePermissionRequiredMixin, DeleteView):
    """View для подтверждения и выполнения удаления сообщения."""

    role_permission = "has_message"
    model = Message
    template_name = "messages/message_confirm_delete.html"
    success_url = reverse_lazy("admin:message")

    def get_context_data(self, **kwargs):
        """Добавляет заголовок страницы в контекст."""
        context = super().get_context_data(**kwargs)
        context["active_section"] = "message"
        context["page_title"] = "Удаление сообщения"
        return context


class MessageDeleteManyView(LoginRequiredMixin, RolePermissionRequiredMixin, View):
    """Обрабатывает POST-запрос для массового удаления сообщений."""

    # Куда перенаправлять после успешного удаления
    success_url = reverse_lazy("admin:message")
    role_permission = "has_message"

    def post(self, request, *args, **kwargs):
        """Handle POST requests to delete selected messages.

        Retrieves the list of selected message IDs from the POST data,
        deletes the corresponding Message objects, and provides feedback
        via Django messages.

        Args:
            request (HttpRequest): The current request object containing POST data.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponseRedirect: Redirects to `success_url` after processing.

        """
        selected_ids = request.POST.getlist("selection")

        if not selected_ids:
            messages.warning(request, "Не выбрано ни одно сообщение для удаления.")
            return redirect(self.success_url)

        count, _ = Message.objects.filter(id__in=selected_ids).delete()

        messages.success(request, f"✅ Успешно удалено {count} сообщений.")

        return redirect(self.success_url)


class SendMessageView(LoginRequiredMixin, RolePermissionRequiredMixin, FormView):
    """View for creating a new message and triggering bulk sending via Celery."""

    template_name = "messages/send_message_form.html"
    form_class = SendMessage
    success_url = reverse_lazy("admin:message")
    role_permission = "has_message"

    def get_context_data(self, **kwargs):
        """Добавляет заголовок страницы в контекст."""
        context = super().get_context_data(**kwargs)
        context["active_section"] = "message"

        return context

    def get_initial(self):
        """Automatically check the 'only_debtors' checkbox if ?only_debtors=1 ."""
        initial = super().get_initial()
        only_debtors_param = self.request.GET.get("only_debtors")
        if only_debtors_param == "1":
            initial["only_debtors"] = True
        return initial

    def form_valid(self, form):
        """Process the form and start the bulk message sending task asynchronously.

        Args:
            form: Valid form instance containing message data.

        Returns:
            HttpResponse: Redirect or render response after starting the task.

        """
        message_obj = form.save(commit=False)
        message_obj.sender = self.request.user
        message_obj.save()
        form.save_m2m()

        data = form.cleaned_data

        task = send_broadcast_email.delay(
            message_obj.pk,
            house_id=data.get("house").pk if data.get("house") else None,
            section_id=data.get("section").pk if data.get("section") else None,
            floor_id=data.get("floor").pk if data.get("floor") else None,
            flat_id=data.get("flat").pk if data.get("flat") else None,
            only_debtors=data.get("only_debtors", False),
        )

        messages.success(
            self.request,
            f"✅ Рассылка сообщений запущена асинхронно! "
            f"ID задачи: {task.id}. Результаты будут видны позже.",
        )
        return super().form_valid(form)


# 8
class UsersView(FormView, ListView):
    """View for managing user accounts by an administrator."""

    model = User
    template_name = "owner_flat/owner_list2.html"
    form_class = FilterOwnerForm
    role_permission = "has_user"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.get_form()
        context["page_title"] = "Администратор пользователей"
        context["active_section"] = "owners"
        return context


class CreateOwnerFlat(LoginRequiredMixin, RolePermissionRequiredMixin, CreateView):
    """View for creating a new apartment owner."""

    role_permission = "has_user"
    template_name = "owner_flat/new_owner.html"
    form_class = CreateOwnerFlatForm
    success_url = reverse_lazy("admin:owners")

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)

        context["active_section"] = "owners"
        return context

    def form_valid(self, form):
        """Save the form and redirect to the users list."""
        form.save()
        return redirect(self.success_url)


class UpdateOwnerFlat(LoginRequiredMixin, RolePermissionRequiredMixin, UpdateView):
    """View for editing an existing apartment owner."""

    template_name = "owner_flat/new_owner.html"
    model = User
    form_class = CreateOwnerFlatForm
    role_permission = "has_user"

    def get_success_url(self):
        """Redirect to the owner's card after saving."""
        return reverse("admin:card_user", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["active_section"] = "owners"
        return context

    def form_valid(self, form):
        """Save form with password hashing and redirect."""
        self.object = form.save()
        return redirect(self.get_success_url())


class CardUserView(LoginRequiredMixin, RolePermissionRequiredMixin, TemplateView):
    """View for displaying the selected user's profile page."""

    template_name = "owner_flat/card_user.html"

    def get_context_data(self, **kwargs):
        """Add additional context data for rendering the template.

        Sets the active section for template highlighting and includes
        any other necessary context variables.

        Args:
            **kwargs: Additional keyword arguments passed to the context.

        Returns:
            dict: Context data for template rendering.

        """
        context = super().get_context_data(**kwargs)
        context["active_section"] = "owners"
        context["page_title"] = "Profile"

        user_id = self.kwargs.get("pk")
        card_user = get_object_or_404(User, pk=user_id)


        apartments = card_user.apartments.prefetch_related(
            "house", "section", "floor", "account"
        )

        context["card_user"] = card_user
        context["apartments"] = apartments
        context["houses"] = {apt.house for apt in apartments}
        context["sections"] = {apt.section for apt in apartments}
        return context


# ToDo User Send Massage
class UserSendMessageView(FormView):
    """View to allow sending messages to a specific user.

    Uses a form to collect message title and description, then processes
    the submission when the form is valid.
    """

    template_name = "owner_flat/user_send_message.html"
    form_class = UserSendMessage
    success_url = reverse_lazy("admin:owners")

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)

        context["active_section"] = "owner"
        return context

    def get_initial(self):
        """Provide initial data for the form.

        Retrieves the user ID from the URL kwargs and sets it in the initial
        form data.

        Returns:
            dict: Initial form data with the user ID.

        """
        initial = super().get_initial()
        user_id = self.kwargs.get("user_id")
        if user_id:
            initial["full_name"] = get_object_or_404(User, id=user_id)
        return initial

    def form_valid(self, form):
        """Provide initial data for the form.

        Retrieves the user ID from the URL kwargs and sets it in the initial
        form data.

        Returns:
            dict: Initial form data with the user ID.

        """
        title = form.cleaned_data["title"]
        description = form.cleaned_data["description"]
        user = form.cleaned_data["full_name"]

        user_id = user.id if user else None
        sender_id = self.request.user.id  # 👈 добавили

        send_user_message.delay(title, description, user_id, sender_id)

        messages.success(self.request, "Сообщения поставлены в очередь на отправку.")
        return super().form_valid(form)


# 9


class HomeView(LoginRequiredMixin, RolePermissionRequiredMixin, UpdateView):
    """View for updating the main homepage content including blocks and SEO."""

    model = Main
    form_class = FormMain
    template_name = "site_management/home.html"
    success_url = reverse_lazy("admin:home")
    role_permission = "has_managment"

    def get_object(self, queryset=None):
        """Retrieve the single Main object to update.

        Returns the first Main instance in the database, or None if none exist.

        Args:
            queryset: Optional queryset (unused).

        Returns:
            Main or None: The Main instance to update.

        """
        logger.debug("get_object: called")
        obj = Main.objects.first()
        logger.debug("get_object: Main.objects.first() -> %s", obj)
        if obj:
            logger.debug(
                "get_object: returning object id=%s title=%s",
                getattr(obj, "id", None),
                getattr(obj, "title", None),
            )
            return obj
        logger.warning(
            "get_object: No Main object found (Main.objects.first() is None)"
        )
        return None

    def get_context_data(self, **kwargs):
        """Add additional context data required for rendering the homepage form.

        Initializes the SEO form and the block formset, and sets the active section.

        Args:
            **kwargs: Additional keyword arguments passed to the parent method.

        Returns:
            dict: Context data for rendering the template.

        """
        logger.debug("get_context_data: called, request.method=%s", self.request.method)
        context = super().get_context_data(**kwargs)
        context["active_section"] = "managment"

        # Create block formset factory
        block_formset_cls = inlineformset_factory(
            Main, Block, form=FormBlock, extra=0, can_delete=True
        )
        obj = self.object

        if self.request.method == "POST":
            context["formset"] = block_formset_cls(
                self.request.POST, self.request.FILES, instance=obj
            )
            context["seo_form"] = FormSEO(
                self.request.POST, instance=getattr(obj, "seo", None), prefix="seo"
            )
        else:
            context["formset"] = block_formset_cls(instance=obj)
            context["seo_form"] = FormSEO(
                instance=getattr(obj, "seo", None), prefix="seo"
            )

        return context

    def form_valid(self, form):
        """Process the submitted homepage form and associated SEO and block formset.

        Initialize and validate the SEO form and the block formset. Save all valid data
        and redirect to the success URL. If validation fails,  orm with errors.

        Args:
            form (Form): The validated main form instance for the homepage.

        Returns:
            HttpResponse: Redirect on success or rendered template with errors.

        """
        self.object = form.save(commit=False)

        # SEO form
        seo_form = FormSEO(
            self.request.POST, instance=getattr(self.object, "seo", None), prefix="seo"
        )
        if seo_form.is_valid():
            seo = seo_form.save()
            self.object.seo = seo
        else:
            logger.warning("SEO form invalid: %s", seo_form.errors)

        # Save main object
        self.object.save()
        form.save_m2m()

        # Block formset
        block_formset_cls = inlineformset_factory(
            Main, Block, form=FormBlock, extra=0, can_delete=True
        )
        formset = block_formset_cls(
            self.request.POST, self.request.FILES, instance=self.object
        )
        if formset.is_valid():
            formset.save()
            return redirect(self.success_url)

        return self.render_to_response(
            self.get_context_data(form=form, formset=formset, seo_form=seo_form)
        )

    def form_invalid(self, form):
        """Handle an invalid form submission by re-rendering the form with errors.

        Initializes the SEO form and block formset with POST data and files,
        then returns a rendered response containing validation errors.

        Args:
            form: The invalid form instance.

        Returns:
            HttpResponse: Rendered response with form errors.

        """
        seo_form = FormSEO(
            self.request.POST,
            instance=getattr(self.object, "seo", None),
            prefix="seo",
        )

        block_formset_cls = inlineformset_factory(
            Main, Block, form=FormBlock, extra=0, can_delete=True
        )
        formset = block_formset_cls(
            self.request.POST, self.request.FILES, instance=self.object
        )

        return self.render_to_response(
            self.get_context_data(form=form, formset=formset, seo_form=seo_form)
        )


class AboutView(LoginRequiredMixin, RolePermissionRequiredMixin, UpdateView):
    """View for updating the 'About Us' page content.

    Allows editing the AboutUs model using FormAboutUs and restricts access
    based on management role permissions.
    """

    model = AboutUs
    form_class = FormAboutUs
    template_name = "site_management/about_us.html"
    success_url = reverse_lazy("admin:about")
    role_permission = "has_managment"

    def get_object(self, queryset=None):
        """Retrieve the AboutUs object to update.

        Returns the first AboutUs instance if it exists, otherwise None.

        Args:
            queryset: Optional queryset (unused).

        Returns:
            AboutUs or None: The object to update.

        """
        obj = AboutUs.objects.first()
        if obj:
            return obj

        seo = SEO.objects.create(
            title="Default Title",
            description="Default Description",
            keyword="Default Keywords",
        )
        obj = AboutUs.objects.create(
            image="",
            title="Default Title",
            description="",
            title2="Default Title2",
            description2="",
            seo=seo,
        )
        Gallery.objects.create(about_us=obj, name="main")
        Gallery.objects.create(about_us=obj, name="additional")
        return obj

    def get_context_data(self, **kwargs):
        """Add extra context for rendering the template.

        Adds the current AboutUs object and sets the active section for the UI.

        Args:
            **kwargs: Additional keyword arguments for context.

        Returns:
            dict: Context dictionary for template rendering.

        """
        context = super().get_context_data(**kwargs)
        obj = self.object

        context["seo_form"] = kwargs.get("seo_form") or FormSEO(
            instance=obj.seo, prefix="seo"
        )
        context["document_formset"] = kwargs.get("document_formset") or DocumentFormSet(
            instance=obj, prefix="doc"
        )

        main_gallery, _ = Gallery.objects.get_or_create(about_us=obj, name="main")
        additional_gallery, _ = Gallery.objects.get_or_create(
            about_us=obj, name="additional"
        )

        context["main_gallery_formset"] = kwargs.get(
            "main_gallery_formset"
        ) or MainGalleryFormSet(instance=main_gallery, prefix="main_gallery")
        context["additional_gallery_formset"] = kwargs.get(
            "additional_gallery_formset"
        ) or AdditionalGalleryFormSet(
            instance=additional_gallery, prefix="additional_gallery"
        )
        context["active_section"] = "managment"
        return context

    def form_valid(self, form):
        """Handle valid form submission.

        Saves the form data and logs the start of processing.

        Args:
            form: The submitted form instance.

        Returns:
            HttpResponse: Response after processing the form.

        """
        logger.debug("=== form_valid старт ===")

        seo_form = FormSEO(self.request.POST, instance=self.object.seo, prefix="seo")
        document_formset = DocumentFormSet(
            self.request.POST, self.request.FILES, instance=self.object, prefix="doc"
        )

        main_gallery, _ = Gallery.objects.get_or_create(
            about_us=self.object, name="main"
        )
        additional_gallery, _ = Gallery.objects.get_or_create(
            about_us=self.object, name="additional"
        )

        main_gallery_formset = MainGalleryFormSet(
            self.request.POST,
            self.request.FILES,
            instance=main_gallery,
            prefix="main_gallery",
        )

        additional_gallery_formset = AdditionalGalleryFormSet(
            self.request.POST,
            self.request.FILES,
            instance=additional_gallery,
            prefix="additional_gallery",
        )

        logger.debug(
            "SEO form valid=%s, errors=%s", seo_form.is_valid(), seo_form.errors
        )
        logger.debug(
            "Document formset valid=%s, errors=%s",
            document_formset.is_valid(),
            document_formset.errors,
        )
        logger.debug(
            "Main gallery formset valid=%s, errors=%s",
            main_gallery_formset.is_valid(),
            main_gallery_formset.errors,
        )
        logger.debug(
            "Additional gallery formset valid=%s, errors=%s",
            additional_gallery_formset.is_valid(),
            additional_gallery_formset.errors,
        )

        if all(
            [
                seo_form.is_valid(),
                document_formset.is_valid(),
                main_gallery_formset.is_valid(),
                additional_gallery_formset.is_valid(),
            ]
        ):
            seo = seo_form.save()
            logger.debug("SEO сохранён: id=%s title=%s", seo.id, seo.title)

            self.object = form.save(commit=False)
            self.object.seo = seo
            self.object.save()
            form.save_m2m()
            logger.debug(
                "AboutUs сохранён: id=%s title=%s", self.object.id, self.object.title
            )

            docs = document_formset.save()
            logger.debug(
                "Документы сохранены: %s", [f"id={d.id}, title={d.title}" for d in docs]
            )

            main_imgs = main_gallery_formset.save()
            logger.debug(
                "Main Gallery сохранена (%s): %s",
                main_gallery.id,
                [f"id={img.id}, file={img.image.name}" for img in main_imgs],
            )

            add_imgs = additional_gallery_formset.save()
            logger.debug(
                "Additional Gallery сохранена (%s): %s",
                additional_gallery.id,
                [f"id={img.id}, file={img.image.name}" for img in add_imgs],
            )

            return redirect(self.success_url)

        logger.warning("=== Ошибки при сохранении AboutUs ===")
        if not seo_form.is_valid():
            logger.warning("SEO ошибки: %s", seo_form.errors)
        if not document_formset.is_valid():
            logger.warning("Документы ошибки: %s", document_formset.errors)
        if not main_gallery_formset.is_valid():
            logger.warning("Main Gallery ошибки: %s", main_gallery_formset.errors)
        if not additional_gallery_formset.is_valid():
            logger.warning(
                "Additional Gallery ошибки: %s", additional_gallery_formset.errors
            )

        return self.form_invalid(
            form,
            seo_form,
            document_formset,
            main_gallery_formset,
            additional_gallery_formset,
        )

    def form_invalid(
        self,
        form,
        seo_form=None,
        document_formset=None,
        main_gallery_formset=None,
        additional_gallery_formset=None,
    ):
        """Handle invalid form submissions for the view.

        This method is triggered when one or more forms or formsets
        in the combined create/update view fail validation.
        It re-renders the page with all forms and formsets containing errors.

        Args:
            form (Form):
                The main form that failed validation.

            seo_form (Form, optional):
                The SEO form associated with the entity. Defaults to None.

            document_formset (BaseFormSet, optional):
                Formset for documents related to the object. Defaults to None.

            main_gallery_formset (BaseInlineFormSet, optional):
                Formset for the main gallery of the object. Defaults to None.

            additional_gallery_formset (BaseInlineFormSet, optional):
                Formset for additional galleries attached to the object.
                Defaults to None.

        Returns:
            HttpResponse:
                The rendered template containing all forms with validation errors.

        """
        seo_form = seo_form or FormSEO(self.request.POST, instance=self.object.seo)
        document_formset = document_formset or DocumentFormSet(
            self.request.POST, self.request.FILES, instance=self.object
        )

        main_gallery, _ = Gallery.objects.get_or_create(
            about_us=self.object, name="main"
        )
        additional_gallery, _ = Gallery.objects.get_or_create(
            about_us=self.object, name="additional"
        )

        main_gallery_formset = main_gallery_formset or MainGalleryFormSet(
            self.request.POST, self.request.FILES, instance=main_gallery
        )
        additional_gallery_formset = (
            additional_gallery_formset
            or AdditionalGalleryFormSet(
                self.request.POST, self.request.FILES, instance=additional_gallery
            )
        )

        context = self.get_context_data(
            form=form,
            seo_form=seo_form,
            document_formset=document_formset,
            main_gallery_formset=main_gallery_formset,
            additional_gallery_formset=additional_gallery_formset,
        )
        return self.render_to_response(context)


class ServicesView(LoginRequiredMixin, RolePermissionRequiredMixin, UpdateView):
    """View for managing site services SEO and related settings.

    This view allows updating SEO information for service pages and
    handling a related formset of non-tariff ServiceStr instances.

    Attributes:
        template_name (str): Template used to render the view.
        model (Model): The model associated with this view (SEO).

    """

    template_name = "site_management/services.html"
    model = SEO
    form_class = FormSEO
    role_permission = "has_managment"
    success_url = reverse_lazy("admin:services")

    def get_object(self, queryset=None):
        """Retrieve the object to update.

        This method returns the first ServiceStr instance where is_tariff=False.
        If no such object exists, None is returned.

        Args:
            queryset: Optional queryset (not used).

        Returns:
            ServiceStr or None: The first non-tariff service instance.

        """
        service = ServiceStr.objects.filter(is_tariff=False).first()

        if service and service.seo:
            return service.seo

        return SEO.objects.create(title="", description="", keyword="")

    def get_context_data(self, **kwargs):
        """Provide context data for the template.

        Adds the active section and a formset for editing tariffs.
        Formset is initialized with POST data if available, otherwise with
        all tariff objects with is_tariff=True.

        Returns:
            dict: Context data for the template rendering.

        """
        context = super().get_context_data(**kwargs)
        context["active_section"] = "managment"
        if self.request.method == "POST":
            context["formset"] = ServiceFormSet(
                self.request.POST,
                self.request.FILES,
                queryset=ServiceStr.objects.filter(is_tariff=False),
            )
        else:
            context["formset"] = ServiceFormSet(
                queryset=ServiceStr.objects.filter(is_tariff=False)
            )

        return context

    def form_valid(self, form):
        """Process the valid FormSEO and its related tariff formset."""
        context = self.get_context_data()
        formset = context["formset"]

        if formset.is_valid():
            # SEO для страницы — сохраняем отдельно
            page_seo = form.save()

            # Обрабатываем услуги
            instances = formset.save(commit=False)
            for instance in instances:
                # Если у услуги нет своего SEO — создаём
                if not instance.seo_id:
                    instance.seo = SEO.objects.create(
                        title=page_seo.title,
                        description=page_seo.description,
                        keyword=page_seo.keyword,
                    )
                else:
                    # Если SEO уже есть — можно обновить при необходимости
                    instance.seo.title = page_seo.title
                    instance.seo.description = page_seo.description
                    instance.seo.keyword = page_seo.keyword
                    instance.seo.save()

                instance.save()

            # Удалённые — удаляем
            for obj in formset.deleted_objects:
                obj.delete()

            return redirect(self.success_url)

        return self.render_to_response(self.get_context_data(form=form))


class TariffsView(LoginRequiredMixin, RolePermissionRequiredMixin, UpdateView):
    """View for managing SEO settings related to tariff services.

    Inherits from UpdateView with login and role permission checks.
    Uses FormSEO to edit SEO metadata.
    """

    model = SEO
    form_class = FormSEO
    role_permission = "has_managment"
    template_name = "site_management/tariffs2.html"
    success_url = reverse_lazy("admin:tariffs")

    def get_object(self, queryset=None):
        """Retrieve the SEO object to update.

        If no SEO object exists, create a default one.
        Uses the first ServiceStr instance with is_tariff=True.

        Args:
            queryset: Optional queryset (unused).

        Returns:
            SEO: SEO instance to update.

        """
        service = ServiceStr.objects.filter(is_tariff=True).first()

        if service and service.seo:
            return service.seo

        # Если такого SEO нет, создаем новый пустой
        return SEO.objects.create(title="", description="", keyword="")

    def get_context_data(self, **kwargs):
        """Get context data for rendering the tariff SEO form and associated formset.

        Adds the active section for template highlighting and initializes
        a TariffFormSet either from POST data or from the current queryset
        of tariffs (ServiceStr objects with is_tariff=True).

        Args:
            **kwargs: Additional keyword arguments passed to the context.

        Returns:
            dict: Context dictionary with 'formset' and 'active_section' keys.

        """
        context = super().get_context_data(**kwargs)
        tariff_queryset = ServiceStr.objects.filter(is_tariff=True)
        context["active_section"] = "managment"
        if self.request.method == "POST":
            context["formset"] = TariffFormSet(self.request.POST, self.request.FILES)
        else:
            context["formset"] = TariffFormSet(queryset=tariff_queryset)
        return context

    def form_valid(self, form):
        """Process the submitted form when it is valid."""
        context = self.get_context_data()
        formset = context["formset"]

        if formset.is_valid():
            # Сохраняем SEO страницы "Услуги" (главный SEO объекта)
            self.object = form.save()

            # Обрабатываем связанные ServiceStr
            instances = formset.save(commit=False)
            for instance in instances:
                # Если у услуги ещё нет SEO — создаём новый
                if not instance.seo_id:
                    instance.seo = SEO.objects.create(
                        title=instance.title or "",
                        description="",
                        keyword=""
                    )
                else:
                    # Если SEO уже есть — можем обновить (опционально)
                    instance.seo.title = instance.title
                    instance.seo.save()

                instance.save()

            # Удаляем отмеченные записи
            for obj in formset.deleted_objects:
                if obj.seo_id:
                    obj.seo.delete()  # удаляем связанный SEO, чтобы не было "мусора"
                obj.delete()

            return redirect(self.success_url)

        # Если ошибки — просто перерисовываем форму
        return self.render_to_response(
            self.get_context_data(form=form, formset=formset))
class TicketView(
    LoginRequiredMixin, RolePermissionRequiredMixin, FormView, TemplateView
):
    """View for managing support tickets and requests."""

    role_permission = "has_applications"
    template_name = "tasks/tasks_list.html"
    form_class = TicketFilterForm

    def get_context_data(self, **kwargs):
        """Add  the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.get_form()
        context["page_title"] = "Заявки"
        context["active_section"] = "ticket"
        return context


class AddTicketsAdminView(LoginRequiredMixin, RolePermissionRequiredMixin, CreateView):
    """Admin view for creating a new Ticket.

    Inherits from Django's CreateView and includes login and role-based
    permission checks for 'has_applications'.
    """

    model = Ticket
    role_permission = "has_applications"
    template_name = "tasks/new_tasks.html"
    form_class = TicketAdminForm
    success_url = reverse_lazy("admin:ticket")

    def get_context_data(self, **kwargs):
        """Add extra context for rendering the ticket creation form.

        Populates page title, active section, current user, apartments,
        houses, and sections for use in the template.

        Args:
            **kwargs: Arbitrary keyword arguments.

        Returns:
            dict: Context data for template rendering.

        """
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Ticket"
        context["active_section"] = "ticket"

        user = self.request.user
        apartments = user.apartments.select_related(
            "house", "section", "floor", "account"
        )

        context["user"] = user
        context["apartments"] = apartments
        context["houses"] = {apt.house for apt in apartments}
        context["sections"] = {apt.section for apt in apartments}

        logger.debug(
            "Context data for AddTicketsView: %s", context
        )  # избегаем f-string
        return context

    def get_form_kwargs(self):
        """Pass additional keyword arguments to the form.

        If 'user_id' is provided in GET parameters, include the User instance
        in the form kwargs.

        Returns:
            dict: Keyword arguments for the form.

        """
        kwargs = super().get_form_kwargs()
        if self.request.method == "GET" and "user_id" in self.request.GET:
            with contextlib.suppress(User.DoesNotExist):
                kwargs["user"] = User.objects.get(pk=self.request.GET["user_id"])
        return kwargs

    def form_valid(self, form):
        """Process the submitted form when it is valid.

        Passes the current user to the form's save() method if supported,
        then proceeds with default form_valid processing.

        Args:
            form: The validated form instance.

        Returns:
            HttpResponse: The response from super().form_valid().

        """
        form.save(user=self.request.user)
        return super().form_valid(form)


class EditTicketsAdminView(LoginRequiredMixin, RolePermissionRequiredMixin, UpdateView):
    """Admin view for editing a Ticket.

    Inherits from Django's UpdateView and includes login and role-based
    permission checks for 'has_applications'.
    """

    model = Ticket
    role_permission = "has_applications"
    template_name = "tasks/new_tasks.html"  # можешь оставить тот же шаблон
    form_class = TicketAdminForm
    success_url = reverse_lazy("admin:ticket")

    def get_context_data(self, **kwargs):
        """Add extra context for rendering the ticket edit form.

        Populates page title, active section, current user, apartments,
        houses, and sections for use in the template.

        Args:
            **kwargs: Arbitrary keyword arguments.

        Returns:
            dict: Context data for template rendering.

        """
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Редактирование заявки"
        context["active_section"] = "ticket"
        user = self.request.user
        apartments = user.apartments.select_related(
            "house", "section", "floor", "account"
        )

        context["user"] = user
        context["apartments"] = apartments
        context["houses"] = {apt.house for apt in apartments}
        context["sections"] = {apt.section for apt in apartments}

        logger.debug("Context data for EditTicketsAdminView: %s", context)
        return context

    def get_form_kwargs(self):
        """Pass additional keyword arguments to the form.

        If 'user_id' is provided in GET parameters, include the User instance
        in the form kwargs.
        """
        kwargs = super().get_form_kwargs()
        if self.request.method == "GET" and "user_id" in self.request.GET:
            user_id = self.request.GET["user_id"]
            with suppress(User.DoesNotExist):
                kwargs["user"] = User.objects.get(pk=user_id)
        return kwargs

    def form_valid(self, form):
        """Process the submitted form when it is valid.

        Passes the current user to the form's save() method if supported,
        then proceeds with default form_valid processing.

        Args:
            form: The validated form instance.

        Returns:
            HttpResponse: The response from super().form_valid().

        """
        form.save(user=self.request.user)
        return super().form_valid(form)


class CardTaskView(LoginRequiredMixin, RolePermissionRequiredMixin, DetailView):
    """Detail view for displaying a single Ticket (task) in the system.

    Inherits from Django's DetailView and includes login and role-based
    permission checks for 'has_applications'.
    """

    model = Ticket
    template_name = "tasks/card_tasks.html"
    context_object_name = "tasks"
    role_permission = "has_applications"

    def get_context_data(self, **kwargs):
        """Add extra context for rendering the task card template.

        Retrieves the Ticket object and its related data to pass to the template.

        Args:
            **kwargs: Arbitrary keyword arguments.

        Returns:
            dict: Context data for the template.

        """
        context = super().get_context_data(**kwargs)
        tasks = self.get_object()
        context["active_section"] = "ticket"

        context["tasks"] = tasks
        context["users"] = tasks.user

        return context


# 14
class ContactView(LoginRequiredMixin, RolePermissionRequiredMixin, UpdateView):
    """View to manage the Contact model.

    Inherits from Django's UpdateView and includes login and role-based
    permission checks. Always operates on the first Contact object.
    """

    model = Contact
    form_class = ContactForm
    template_name = "site_management/contact.html"
    success_url = reverse_lazy("admin:contact")
    role_permission = "has_managment"

    def get_object(self, queryset=None):
        """Retrieve the object to be edited.

        Always returns the first Contact instance in the database.

        Args:
            queryset (QuerySet, optional): Base queryset to use. Defaults to None.

        Returns:
            Contact: The first Contact object.

        """
        # всегда возвращаем первый объект
        return Contact.objects.first()

    def get_context_data(self, **kwargs):
        """Add extra context for rendering the template.

        Sets 'active_section' to 'contact' for UI highlighting.

        Returns:
            dict: Context data for the template.

        """
        context = super().get_context_data(**kwargs)
        context["active_section"] = "contact"
        if self.request.method == "POST":
            context["contact_form"] = ContactForm(
                self.request.POST, prefix="contact", instance=self.object
            )
            context["seo_form"] = FormSEO(
                self.request.POST, prefix="seo", instance=self.object.seo
            )
        else:
            context["contact_form"] = ContactForm(
                prefix="contact", instance=self.object
            )
            context["seo_form"] = FormSEO(prefix="seo", instance=self.object.seo)

        return context

    def post(self, request, *args, **kwargs):
        """Handle POST requests to update the Contact instance.

        Retrieves the object, processes the form, and returns the response.

        Args:
            request (HttpRequest): The incoming request object.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            HttpResponse: Response after processing the form.

        """
        self.object = self.get_object()
        context = self.get_context_data()

        contact_form = context["contact_form"]
        seo_form = context["seo_form"]

        if contact_form.is_valid() and seo_form.is_valid():
            seo = seo_form.save()
            contact = contact_form.save(commit=False)
            contact.seo = seo
            contact.save()
            return redirect(self.get_success_url())

        return self.render_to_response(context)


# 15
class PersonalaccountView(
    LoginRequiredMixin, RolePermissionRequiredMixin, FormView, ListView
):
    """View for the user's personal account page."""

    model = PersonalAccount
    form_class = PersonalAccountFilterForm
    template_name = "account/page.html"
    role_permission = "has_personal_account"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        # Баланс всей кассы
        cashbox_income = CashBox.objects.filter(
            is_conducted=True, payment_articles__record_type="in"
        ).aggregate(total=Sum("suma"))["total"] or Decimal(0)
        cashbox_expense = CashBox.objects.filter(
            is_conducted=True, payment_articles__record_type="out"
        ).aggregate(total=Sum("suma"))["total"] or Decimal(0)
        cashbox_balance = cashbox_income - cashbox_expense

        # ----------------------------
        #   Персональный счёт
        # ----------------------------
        debt = Decimal(0)
        total_paid_invoices = Decimal(0)
        total_unpaid_invoices = Decimal(0)
        personal_balance = Decimal(0)

        # ✅ Оплаченные квитанции (status="new")
        total_paid_invoices = Invoice.objects.filter(status="new").aggregate(
            total=Sum("items__total")
        )["total"] or Decimal(0)
        # ✅ Неоплаченные и частично оплаченные (status in ["zero", "counted"])
        total_unpaid_invoices = Invoice.objects.filter(
            status__in=["zero", "counted"]
        ).aggregate(total=Sum("items__total"))["total"] or Decimal(0)

        # ✅ Задолженность (только полностью неоплаченные)
        debt = Invoice.objects.filter(status="zero").aggregate(
            total=Sum("items__total")
        )["total"] or Decimal(0)

        # ✅ Баланс = оплачено - начислено
        personal_balance = total_paid_invoices - total_unpaid_invoices

        context = super().get_context_data(**kwargs)
        context["debt"] = debt
        context["personal_balance"] = personal_balance
        context["cashbox_balance"] = cashbox_balance
        context["page_title"] = "Личный кабинет"
        context["filter_form"] = self.get_form()
        context["active_section"] = "account"
        return context


class AddPersonalAccountView(
    LoginRequiredMixin, RolePermissionRequiredMixin, CreateView
):
    """View for creating a new PersonalAccount.

    Inherits from Django's CreateView and mixins for login and
    role-based permissions. Handles form display and creation logic.
    """

    model = PersonalAccount
    template_name = "account/add_account.html"
    form_class = PersonalAccountForm
    success_url = reverse_lazy("admin:account")
    role_permission = "has_personal_account"

    def get_context_data(self, **kwargs):
        """Add additional context for template rendering.

        Sets 'active_section' to 'account' for UI highlighting.

        Returns:
            dict: Context data for the template.

        """
        context = super().get_context_data(**kwargs)
        context["active_section"] = "account"
        return context

    def form_valid(self, form):
        """Add additional context for template rendering.

        Sets 'active_section' to 'account' for UI highlighting.

        Returns:
            dict: Context data for the template.

        """
        apt = form.cleaned_data["apartment"]
        owner_user = None

        for attr in ("owner", "user", "owner_user"):
            owner_user = getattr(apt, attr, None)
            if owner_user:
                break

        if owner_user:
            form.instance.user = owner_user  # свяжем аккаунт с владельцем квартиры
        else:
            form.add_error(
                "apartment",
                "У квартиры не найден владелец, задайте связь в модели Apartment.",
            )
            return self.form_invalid(form)

        return super().form_valid(form)


class UpdatePersonalAccountView(
    LoginRequiredMixin, RolePermissionRequiredMixin, UpdateView
):
    """View for updating an existing PersonalAccount.

    Inherits from Django's UpdateView and mixins for login and
    role-based permissions. Handles form display and update logic.
    """

    model = PersonalAccount
    template_name = "account/add_account.html"  # можно оставить тот же шаблон
    form_class = PersonalAccountForm
    success_url = reverse_lazy("admin:account")  # куда перенаправлять после сохранения
    role_permission = "has_personal_account"

    def get_context_data(self, **kwargs):
        """Add additional context for template rendering.

        Sets 'active_section' to 'account' for UI highlighting.

        Returns:
            dict: Context data for the template.

        """
        context = super().get_context_data(**kwargs)
        context["active_section"] = "account"
        return context

    def form_valid(self, form):
        """Process the valid form and save the updated PersonalAccount instance.

        Can perform additional actions such as updating the apartment
        relationship or owner data.

        Args:
            form (ModelForm): The validated form instance.

        Returns:
            HttpResponse: Redirect or rendered response after updating.

        """
        apt = form.cleaned_data.get("apartment")
        owner_user = None

        for attr in ("owner", "user", "owner_user"):
            owner_user = getattr(apt, attr, None)
            if owner_user:
                break

        if owner_user:
            form.instance.user = owner_user  # свяжем аккаунт с владельцем квартиры
        else:
            form.add_error(
                "apartment",
                "У квартиры не найден владелец, задайте связь в модели Apartment.",
            )
            return self.form_invalid(form)

        return super().form_valid(form)


class DeletePersonalAccountView(
    LoginRequiredMixin, RolePermissionRequiredMixin, DeleteView
):
    """View to delete a PersonalAccount instance.

    Inherits from Django's DeleteView and mixins for login and role-based permissions.
    Handles confirmation and deletion of a personal account.
    """

    role_permission = "personal_account"
    model = PersonalAccount
    template_name = "account/delete_account.html"
    success_url = reverse_lazy("admin:account")


# ToDo добавить ссылки на связаные страницы
class PersonalAccountDetailView(
    LoginRequiredMixin, RolePermissionRequiredMixin, DetailView
):
    """View to display detailed information about a PersonalAccount.

    Provides context data for the template and ensures
    that the user has the required permissions.
    """

    model = PersonalAccount
    template_name = "account/account_card.html"
    context_object_name = "account"
    role_permission = "has_personal_account"

    def get_context_data(self, **kwargs):
        """View to display detailed information about a PersonalAccount.

        Provides context data for the template and ensures
        that the user has the required permissions.
        """
        context = super().get_context_data(**kwargs)
        context["active_section"] = "account"
        # Баланс по счету
        incomes = (
            self.object.cashbox_set.filter(
                payment_articles__record_type="in"
            ).aggregate(Sum("suma"))["suma__sum"]
            or 0
        )

        expenses = (
            self.object.cashbox_set.filter(
                payment_articles__record_type="out"
            ).aggregate(Sum("suma"))["suma__sum"]
            or 0
        )

        context["balance"] = incomes - expenses
        return context


class ServiceView(LoginRequiredMixin, RolePermissionRequiredMixin, TemplateView):
    """A view for managing and displaying services and units.

    This view uses formsets to handle the creation and editing of service
     and unit objects.
    """

    role_permission = "has_service"
    template_name = "system_settings/services.html"
    success_url = "/"  # или reverse_lazy('admin:service')

    def get_formset(
        self, formset_class, queryset=None, data=None, prefix=None, form_kwargs=None
    ):
        """Handle GET requests to display the role management form."""
        if form_kwargs is None:
            form_kwargs = {}
        return formset_class(
            data=data, queryset=queryset, prefix=prefix, form_kwargs=form_kwargs
        )

    def get_context_data(self, **kwargs):
        """Add additional context for rendering the template.

        Updates the context dictionary with the 'active_section'
        key to highlight the appropriate section in the UI.

        Returns:
            dict: Context data for the template.

        """
        context = super().get_context_data(**kwargs)
        context["active_section"] = "setings"
        units_queryset = Unit.objects.order_by("id")
        context["units"] = units_queryset

        context["formset1"] = kwargs.get("formset1") or self.get_formset(
            ServiceFormSet1,
            queryset=Service.objects.select_related("unit").all(),
            prefix="services",
        )

        context["formset2"] = kwargs.get("formset2") or self.get_formset(
            UnitFormSet,
            queryset=units_queryset,
            prefix="units",
        )

        return context

    def post(self, request, *args, **kwargs):
        """Handle POST requests for the view.

        This method processes form submissions or other POST actions
        and updates the related data accordingly.

        Args:
            request (HttpRequest): The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: The response after processing the POST request.

        """
        units_queryset = Unit.objects.order_by("id")

        formset1 = self.get_formset(
            ServiceFormSet1,
            queryset=Service.objects.select_related("unit").all(),
            data=request.POST,
            prefix="services",
        )
        formset2 = self.get_formset(
            UnitFormSet,
            queryset=units_queryset,
            data=request.POST,
            prefix="units",
        )

        if formset1.is_valid() and formset2.is_valid():
            with transaction.atomic():
                formset1.save()
                formset2.save()
            return redirect("admin:service")

        context = {
            "formset1": formset1,
            "formset2": formset2,
        }
        return render(request, "system_settings/services.html", context)


# 17
class TariffView(LoginRequiredMixin, RolePermissionRequiredMixin, ListView):
    """View for managing tariffs within system settings."""

    role_permission = "has_tariff"
    model = Tariff
    template_name = "system_settings/tariff/tariffs.html"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Тарифы"
        context["active_section"] = "setings"
        return context


class TariffDeleteView(LoginRequiredMixin, RolePermissionRequiredMixin, DeleteView):
    """View for deleting a Tariff object.

    This view handles the deletion of a specific tariff instance and redirects
    the user to the tariff list page upon success.
    """

    role_permission = "has_tariff"
    model = Tariff
    success_url = reverse_lazy("admin:tariff")


class TariffServiceFormView(LoginRequiredMixin, RolePermissionRequiredMixin, FormView):
    """View for creating a new tariff with its related services.

    This class uses a main form for the tariff and a formset for its services.
    """

    role_permission = "has_tariff"
    template_name = "system_settings/tariff/new_tariffs.html"
    form_class = TariffForm  # головна форма — Tariff

    def get_context_data(self, **kwargs):
        """Handle GET requests to display the role management form."""
        context = super().get_context_data(**kwargs)
        context["active_section"] = "setings"
        if self.request.method == "POST":
            context["formset"] = TariffServiceFormSet(
                self.request.POST, self.request.FILES
            )
        else:
            # порожній formset для нового тарифу
            context["formset"] = TariffServiceFormSet(
                queryset=TariffService.objects.none()
            )
        return context

    def post(self, request, *args, **kwargs):
        """Handle POST requests to create a new tariff and its services."""
        main_form = self.get_form()
        formset = TariffServiceFormSet(request.POST, request.FILES)

        if main_form.is_valid() and formset.is_valid():
            return self.forms_valid(main_form, formset)
        return self.forms_invalid(main_form, formset)

    def forms_valid(self, main_form, formset):
        """Render the form with errors when either the main form or formset is valid."""
        # Зберігаємо головну форму (Tariff)
        tariff = main_form.save()

        # Зберігаємо послуги та підставляємо тариф
        instances = formset.save(commit=False)
        for instance in instances:
            instance.tariff = tariff
            instance.save()

        # Видаляємо позначені на видалення
        for obj in formset.deleted_objects:
            obj.delete()

        # Після збереження можна перенаправити на сторінку тарифів
        return redirect("admin:tariff")  # заміни на свій URL

    def forms_invalid(self, main_form, formset):
        """Render the form with errors when the main form or formset is invalid."""
        context = self.get_context_data(form=main_form, formset=formset)
        return self.render_to_response(context)


class TariffUpdateView(LoginRequiredMixin, RolePermissionRequiredMixin, UpdateView):
    """View for updating an existing Tariff and its related services."""

    role_permission = "has_tariff"
    model = Tariff
    form_class = TariffForm
    template_name = "system_settings/tariff/new_tariffs.html"
    pk_url_kwarg = "pk"  # ожидаем, что в URL будет параметр pk

    def get_context_data(self, **kwargs):
        """Handle GET requests to display the role management form."""
        context = super().get_context_data(**kwargs)
        context["active_section"] = "setings"
        if self.request.method == "POST":
            context["formset"] = TariffServiceFormSet(
                self.request.POST, self.request.FILES, instance=self.object
            )
        else:
            context["formset"] = TariffServiceFormSet(instance=self.object)
        return context

    def post(self, request, *args, **kwargs):
        """Handle POST requests to save data from the tariff_service_form."""
        self.object = self.get_object()  # получаем существующий тариф
        main_form = self.get_form()
        formset = TariffServiceFormSet(
            request.POST, request.FILES, instance=self.object
        )

        if main_form.is_valid() and formset.is_valid():
            return self.forms_valid(main_form, formset)
        return self.forms_invalid(main_form, formset)

    def forms_valid(self, main_form, formset):
        """Render the form with errors when either the main form or formset is valid."""
        main_form.save()
        formset.save()
        return redirect("admin:tariff")

    def forms_invalid(self, main_form, formset):
        """Render the form with errors when the main form or formset is invalid."""
        return self.render_to_response(
            self.get_context_data(form=main_form, formset=formset)
        )


# ToDo  Copy
class TariffCopyView(LoginRequiredMixin, RolePermissionRequiredMixin, View):
    """A view to copy an existing tariff and its related services.

    This class handles the logic for duplicating a tariff object.
    """

    role_permission = "has_tariff"

    def get_context_data(self, **kwargs):
        """Handle GET requests to display the role management form."""
        context = super().get_context_data(**kwargs)
        context["active_section"] = "setings"

        return context

    def get(self, request, pk):
        """Handle GET requests to display the role management form."""
        original = get_object_or_404(Tariff, pk=pk)

        # Сохраняем id оригинала, чтобы скопировать услуги
        original_id = original.pk

        # Клонируем тариф
        original.pk = None
        original.id = None
        # Если есть поле с названием — пометим как копию
        if hasattr(original, "title"):
            original.title = f"{original.title} (Копия)"
        elif hasattr(original, "name"):
            original.name = f"{original.name} (Копия)"
        original.save()

        # Копируем услуги тарифа
        services = TariffService.objects.filter(tariff=original_id)
        for service in services:
            service.pk = None
            service.id = None
            service.tariff = original
            service.save(force_insert=True)

        # Перенаправляем куда нужно
        return redirect("admin:update_tariff", pk=original.pk)


class CardTariffView(LoginRequiredMixin, RolePermissionRequiredMixin, DetailView):
    """Display detailed information about a specific Tariff.

    This view requires the user to be logged in and to have the
    'has_tariff' permission. It uses Django's `DetailView` to
    render the details of a single `Tariff` instance.

    Attributes:
        role_permission (str): Permission string required to access the view.
        model (Model): The Django model associated with this view (`Tariff`).

    """

    role_permission = "has_tariff"
    model = Tariff
    template_name = "system_settings/tariff/tariff_card.html"
    context_object_name = "tariff"  # лучше в нижнем регистре без пробела

    def get_context_data(self, **kwargs):
        """Extend context data for the template rendering.

        Adds additional context variables required by the template,
        while preserving the default context provided by the parent class.

        Args:
            **kwargs: Arbitrary keyword arguments passed to the method.

        Returns:
            dict: Updated context dictionary containing additional data.

        """
        context = super().get_context_data(**kwargs)
        tariff = self.get_object()
        context["active_section"] = "setings"

        context["services"] = tariff.services.select_related("service", "unit")

        return context


# 18
class RoleView(LoginRequiredMixin, RolePermissionRequiredMixin, FormView):
    """A view for managing user roles.

    This view uses a model formset to display and edit a list of roles.
    """

    role_permission = "has_role"
    RoleFormSet = modelformset_factory(Role, form=RoleForm, extra=0)

    def get_context_data(self, **kwargs):
        """Extend context data for the template rendering.

        Adds additional context variables required by the template,
        while preserving the default context provided by the parent class.

        Args:
            **kwargs: Arbitrary keyword arguments passed to the method.

        Returns:
            dict: Updated context dictionary containing additional data.

        """
        context = super().get_context_data(**kwargs)

        context["active_section"] = "setings"
        return context

    def get(self, request, *args, **kwargs):
        """Handle GET requests to display the role management form."""
        formset = self.RoleFormSet(queryset=Role.objects.all())
        return render(request, "system_settings/roles.html", {"formset": formset})

    def post(self, request, *args, **kwargs):
        """Handle POST requests to save data from the roles form."""
        formset = self.RoleFormSet(request.POST, queryset=Role.objects.all())
        if formset.is_valid():
            formset.save()
            return redirect("admin:role")
        return render(request, "system_settings/roles.html", {"formset": formset})


# 19
class UserAdminView(LoginRequiredMixin, RolePermissionRequiredMixin, TemplateView):
    """View for managing user accounts by an administrator."""

    role_permission = "has_user"
    template_name = "system_settings/users/table.html"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Администратор пользователей"
        context["active_section"] = "setings"
        return context


# 20
class PaymentDetailView(LoginRequiredMixin, RolePermissionRequiredMixin, UpdateView):
    """View for updating a single fixed payment article."""

    model = PaymentDetail
    template_name = "system_settings/payment_details.html"
    form_class = PaymentDetailsForm
    success_url = reverse_lazy("admin:payment_detail")
    role_permission = "has_user"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Администратор пользователей"
        context["active_section"] = "setings"
        return context

    def get_object(self, queryset=None):
        """Return the first PaymentDetail object."""
        return PaymentDetail.objects.first()

    def form_valid(self, form):
        """Handle valid form submission."""
        return super().form_valid(form)


class PaymentArticlesView(LoginRequiredMixin, RolePermissionRequiredMixin, ListView):
    """View for updating a single fixed payment article and handling sorting."""

    role_permission = "has_payment_details"
    model = PaymentArticles
    template_name = "system_settings/payment_articles.html"
    queryset = PaymentArticles.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        sort_by = self.request.GET.get('sort', None)
        order = self.request.GET.get('order', 'asc')

        if sort_by == 'record_type':

            queryset = queryset.annotate(
                record_type_order=Case(
                    When(record_type='in', then=Value(0)),
                    When(record_type='out', then=Value(1)),
                    output_field=IntegerField(),
                )
            )
            prefix = '-' if order == 'desc' else ''
            queryset = queryset.order_by(f'{prefix}record_type_order')

        return queryset

    def get_context_data(self, **kwargs):
        """Add the page title and current sort parameters to the context."""
        context = super().get_context_data(**kwargs)

        context["active_section"] = "setings"
        # Передаємо поточні параметри сортування в шаблон для правильного формування посилань
        context["current_sort"] = self.request.GET.get('sort', '')
        context["current_order"] = self.request.GET.get('order', 'asc')

        return context


class EditPaymentArticlesView(
    LoginRequiredMixin, RolePermissionRequiredMixin, FormMixin, DetailView
):
    """View for updating a single fixed payment article."""

    role_permission = "has_payment_details"
    model = PaymentArticles
    form_class = PaymentArticlesForm
    template_name = "system_settings/edit_payment_article.html"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)

        context["active_section"] = "setings"
        return context

    def get_success_url(self):
        """Return the URL to redirect to after successfully updating the article."""
        return reverse_lazy("admin:payment-articles")

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.get_object()
        return kwargs

    def post(self, request, *args, **kwargs):
        """Handle POST requests for updating the article."""
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        """Save the form and redirect on successful validation."""
        form.save()
        return super().form_valid(form)


class CreatePaymentArticlesView(
    LoginRequiredMixin, RolePermissionRequiredMixin, CreateView
):
    """View for creating a new payment article."""

    model = PaymentArticles
    form_class = PaymentArticlesForm
    template_name = "system_settings/edit_payment_article.html"
    role_permission = "has_payment_details"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)

        context["active_section"] = "setings"
        return context

    def get_success_url(self):
        """Return the URL to redirect to after successfully creating the article."""
        return reverse_lazy("admin:payment-articles")  # URL для перенаправления после
        # сохранения

    def form_valid(self, form):
        """Save the form and redirect on successful validation."""
        form.save()
        return super().form_valid(form)


class PaymentArticlesDeleteView(
    LoginRequiredMixin, RolePermissionRequiredMixin, DeleteView
):
    """View for deleting a Tariff object.

    This view handles the deletion of a specific tariff instance and redirects
    the user to the tariff list page upon success.
    """

    role_permission = "has_payment_details"
    model = PaymentArticles
    success_url = reverse_lazy("admin:payment-articles")

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)

        context["active_section"] = "payment_articles"
        return context


# 21
class OwnerAjaxDatatableView(LoginRequiredMixin, RolePermissionRequiredMixin, View):
    """AJAX view to provide user data for datatables."""

    def get(self, request, *args, **kwargs):
        """Return JSON data for datatables."""
        return JsonResponse({"data": []})


class UserAjaxDatatableView(View):
    """AJAX view to provide user data for datatables."""

    def get(self, request, *args, **kwargs):
        """Return JSON data for datatables."""
        return JsonResponse({"data": []})


class UserCreateStaff(LoginRequiredMixin, RolePermissionRequiredMixin, FormView):
    """View for creating a new staff user.

    Requires login and the appropriate role permissions.
    Uses StaffForms to validate and save the new user.
    Renders 'system_settings/users/new_user.html' template.
    """

    template_name = "system_settings/users/new_user.html"
    form_class = StaffForms
    success_url = reverse_lazy("admin:user-admin")
    role_permission = "has_user"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)

        context["active_section"] = "setings"
        return context

    def form_valid(self, form):
        """Handle a valid form submission.

        Saves the new staff user via the form (password is hashed automatically)
        and redirects to the success URL.
        """
        form.save()
        return super().form_valid(form)

    def form_invalid(self, form):
        """Handle an invalid form submission.

        Returns the form with errors rendered in the template.
        """
        return self.render_to_response(self.get_context_data(form=form))


class UserUpdateStaff(LoginRequiredMixin, RolePermissionRequiredMixin, UpdateView):
    """User update view."""

    template_name = "system_settings/users/new_user.html"
    model = User
    form_class = StaffForms
    success_url = reverse_lazy("admin:user-admin")
    role_permission = "has_user"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)

        context["active_section"] = "setings"
        return context

    def form_valid(self, form):
        """Save the updated staff user and redirect."""
        return super().form_valid(form)


class UserDeleteStaff(LoginRequiredMixin, RolePermissionRequiredMixin, DeleteView):
    """User deletion view."""

    template_name = "system_settings/users/user_confirm_delete.html"
    model = User
    success_url = reverse_lazy("admin:user-admin")
    role_permission = "has_user"

    def get_context_data(self, **kwargs):
        """Add custom context for the delete confirmation template."""
        context = super().get_context_data(**kwargs)
        context["title"] = f"Удаление пользователя: {self.object.username}"
        context["active_section"] = "user"
        return context


class CardStaffView(LoginRequiredMixin, RolePermissionRequiredMixin, DetailView):
    """Detail view for displaying a staff member's card.

    Requires user to be logged in and have the 'has_user' permission.
    Renders staff details in 'system_settings/users/staff_card.html'.
    """

    model = User
    template_name = "system_settings/users/staff_card.html"
    context_object_name = "Staff"
    role_permission = "has_user"

    def get_context_data(self, **kwargs):
        """Add additional context for the staff card template.

        Includes the staff object retrieved by get_object().
        """
        context = super().get_context_data(**kwargs)
        staff = self.get_object()
        context["active_section"] = "setings"
        # Получаем все услуги тарифа
        context["staff"] = staff

        return context


def export_cash_box_to_excel(request):
    """Export selected CashBox records to an Excel file.

    Retrieves CashBox entries (filtered by IDs if provided) and exports
    them to an Excel spreadsheet with auto-adjusted column widths.

    Args:
        request: The HTTP request object containing optional `ids` query parameter.

    Returns:
        HttpResponse: An Excel file containing the exported CashBox data.

    """
    ids_param = request.GET.get("ids")
    qs = CashBox.objects.select_related(
        "personal_account", "payment_articles", "manager", "owner"
    )

    if ids_param:
        ids = [int(x) for x in ids_param.split(",") if x.isdigit()]
        qs = qs.filter(id__in=ids)

    data = []
    for cash_box in qs:
        row = {
            "#": cash_box.cash_box_number,
            "Дата": cash_box.date,
            "Приход/Расход": cash_box.payment_articles.record_type,
            "Статус": "Проведен" if cash_box.is_conducted else "Не проведен",
            "Статья": cash_box.payment_articles.name,
            "Квитанция": "",
            "Услуга": "",
            "Сума": cash_box.suma,
            "Валюта": "грн",
            "Владелец": cash_box.owner.full_name if cash_box.owner else "",
            "Лицевой счёт": (
                cash_box.personal_account.account_number
                if cash_box.personal_account
                else ""
            ),
        }
        data.append(row)

    # Use a descriptive name instead of generic "df"
    cashbox_dataframe = pd.DataFrame(data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        cashbox_dataframe.to_excel(writer, index=False, sheet_name="CashBox")

    output.seek(0)
    workbook = load_workbook(output)
    worksheet = workbook.active

    # Auto-adjust column widths
    for col in worksheet.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        worksheet.column_dimensions[col_letter].width = max_length + 2

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="cash_box_list.xlsx"'
    return response


def export_accounts_view(request):
    """Export personal accounts to an Excel file.

    Includes account number, status, house, section, apartment number,
    owner full name, and current balance. Returns an Excel file as HTTP response.
    """
    accounts = PersonalAccount.objects.select_related(
        "apartment__user", "apartment__house", "apartment__section", "apartment__floor"
    ).all()

    data = []
    for account in accounts:
        apartment = getattr(account, "apartment", None)

        cash_sum = (
            CashBox.objects.filter(personal_account=account).aggregate(
                total=Sum("suma")
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

    accounts_df = pd.DataFrame(
        data,
        columns=[
            "Лицевой счет",
            "Статус",
            "Дом",
            "Секция",
            "Квартира",
            "Владелец",
            "Остаток",
        ],
    )

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        accounts_df.to_excel(writer, index=False, sheet_name="Лицевые счета")

        # Автоподгонка ширины колонок
        ws = writer.sheets["Лицевые счета"]
        for col in ws.columns:
            max_length = 0
            col_letter = col[0].column_letter
            for cell in col:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = max_length + 2

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="personal_accounts.xlsx"'
    response.write(output.getvalue())
    return response


def get_sections_by_house(request):
    """Возвращает JSON-список секций для выбранного дома."""
    house_id = request.GET.get("house_id")
    sections = (
        Section.objects.filter(house_id=house_id).order_by("name").values("id", "name")
    )
    return JsonResponse(list(sections), safe=False)


def get_apartments_by_section(request):
    """Возвращает JSON-список квартир для выбранной секции."""
    section_id = request.GET.get("section_id")

    apartments = (
        Apartment.objects.filter(section_id=section_id)
        .order_by("apartment_number")
        .values("id", "apartment_number")
    )

    return JsonResponse(list(apartments), safe=False)


def get_apartment_owner(request):
    """Return JSON data for the owner and phone number of the selected apartment.

    GET parameters:
    - apartment_id: Apartment ID

    Returns:
        JSON with the "owner" and "phone" fields.

    """
    apartment_id = request.GET.get("apartment_id")
    owner_data = {"owner": "", "phone": ""}

    logger.debug("Запрос на apartment_id: %s", apartment_id)

    if apartment_id:
        try:
            # Подтягиваем пользователя вместе с квартирой
            apartment = Apartment.objects.select_related("user").get(id=apartment_id)
            logger.debug(
                "Найдена квартира: %s, пользователь: %s", apartment, apartment.user
            )

            if apartment.user:
                full_name = apartment.user.get_full_name() or apartment.user.username
                phone = getattr(apartment.user, "phone", "") or getattr(
                    apartment.user, "phone_number", ""
                )
                owner_data["owner"] = full_name
                owner_data["phone"] = phone
                logger.debug("owner: %s, phone: %s", full_name, phone)

        except Apartment.DoesNotExist:
            logger.debug("Квартира с id %s не найдена", apartment_id)
    else:
        logger.debug("apartment_id не передан в GET-параметрах")

    logger.debug("Возвращаем JSON: %s", owner_data)
    return JsonResponse(owner_data)


def get_user_apartments(request):
    """Return a list of apartments belonging to a specific user.

    Expects a 'user_id' parameter in the GET request. Retrieves all
    Apartment objects linked to that user and returns them in JSON
    format for use in dependent dropdowns or AJAX calls.
    """
    user_id = request.GET.get("user_id")
    data = {"apartments": []}

    if user_id:
        apartments = Apartment.objects.filter(user_id=user_id).select_related("house")
        data["apartments"] = [
            {"id": apt.id, "title": f"{apt.house.title} - кв. {apt.apartment_number}"}
            for apt in apartments
        ]

    return JsonResponse(data)


def get_sections_by_house2(request):
    """Return an HTML dropdown list of sections for a given house.

    Expects a 'house_id' parameter in the GET request. Retrieves all
    Section objects related to that house, ordered by name, and returns
    them as <option> elements inside an HttpResponse.
    """
    house_id = request.GET.get("house_id")
    sections = Section.objects.filter(house_id=house_id).order_by("name")
    html_options = '<option value="">---------</option>'
    for section in sections:
        html_options += f'<option value="{section.id}">{section.name}</option>'
    return HttpResponse(html_options)


def get_floors(request):
    """Return an HTML dropdown list of floors for a given house.

    Expects a 'house_id' parameter in the GET request. Retrieves all floors
    associated with that house, ordered by name, and returns them as
    <option> elements in an HttpResponse for use in a select field.
    """
    house_id = request.GET.get("house_id")
    floors = Floor.objects.filter(house_id=house_id).order_by("name")
    html_options = '<option value="">---------</option>'
    for floor in floors:
        html_options += f'<option value="{floor.id}">{floor.name}</option>'
    return HttpResponse(html_options)


def get_user_account(request):
    """Возвращает личный счет пользователя для выбранного user_id."""
    user_id = request.GET.get("user_id")
    account_number = ""
    if user_id:
        try:
            account = PersonalAccount.objects.filter(user_id=user_id).first()
            if account:
                account_number = account.account_number
        except PersonalAccount.DoesNotExist:
            pass
    return JsonResponse({"account_number": account_number})


def get_house_workers(request):
    """Return workers associated with a house based on apartment and role filters.

    Retrieves the house ID from the apartment, if provided, and filters
    users based on the given role and house. Returns a JSON response
    with the matching workers.
    """
    apartment_id = request.GET.get("apartment_id")
    role_id = request.GET.get("role_id")

    house_id = None
    if apartment_id:
        with contextlib.suppress(Apartment.DoesNotExist):
            house_id = Apartment.objects.get(id=apartment_id).house_id

    qs = User.objects.none()
    if house_id:
        qs = User.objects.filter(staff_houses__house_id=house_id)
        if role_id:
            qs = qs.filter(role_id=role_id)

    workers = [{"id": u.id, "name": u.full_name or u.email} for u in qs.distinct()]
    return JsonResponse({"workers": workers})


class UserAutocomplete(autocomplete.Select2QuerySetView):
    """Autocomplete view for the User model."""

    def get_queryset(self):
        """Return queryset for user autocomplete."""
        # Логика для поиска пользователей
        qs = User.objects.all()
        if self.q:
            qs = qs.filter(
                Q(first_name__icontains=self.q)
                | Q(last_name__icontains=self.q)
                | Q(email__icontains=self.q)
            )
        return qs


class PersonalAccountAutocomplete(autocomplete.Select2QuerySetView):
    """Autocomplete view for the PersonalAccount model."""

    def get_queryset(self):
        """Return queryset for PersonalAccount autocomplete  ."""
        qs = PersonalAccount.objects.all()

        owner_id = self.forwarded.get("owner")
        qs = qs.filter(user_id=owner_id) if owner_id else PersonalAccount.objects.none()

        if self.q:
            qs = qs.filter(
                Q(number__icontains=self.q) | Q(account_number__icontains=self.q)
            )

        return qs


class ManagerAutocomplete(autocomplete.Select2QuerySetView):
    """Autocomplete view for User (manager) model."""

    def get_queryset(self):
        """Return queryset for manager autocomplete."""
        qs = User.objects.all()
        if self.q:
            qs = qs.filter(
                Q(first_name__icontains=self.q)
                | Q(last_name__icontains=self.q)
                | Q(email__icontains=self.q)
            )
        return qs


class HouseAutocomplete(autocomplete.Select2QuerySetView):
    """Autocomplete view for House model."""

    def get_queryset(self):
        """Return queryset for house autocomplete."""
        qs = House.objects.all()

        if self.q:
            qs = qs.filter(title__icontains=self.q)
        return qs


class SectionAutocomplete(autocomplete.Select2QuerySetView):
    """Autocomplete view for the Section model."""

    def get_queryset(self):
        """Return queryset for Section autocomplete."""
        qs = Section.objects.all()

        # Фильтрация по дому (если передали forward)
        house_id = self.forwarded.get("house", None)
        if house_id:
            qs = qs.filter(house_id=house_id)

        if self.q:
            qs = qs.filter(name__icontains=self.q)
        return qs


class FloorAutocomplete(autocomplete.Select2QuerySetView):
    """Autocomplete view for the Floor model."""

    def get_queryset(self):
        """Return queryset for Floor autocomplete."""
        qs = Floor.objects.all()

        # Фильтрация по дому (если передали forward)
        house_id = self.forwarded.get("house", None)
        if house_id:
            qs = qs.filter(house_id=house_id)

        if self.q:
            qs = qs.filter(name__icontains=self.q)
        return qs


class ApartmentAutocomplete(autocomplete.Select2QuerySetView):
    """Autocomplete view for the Apartment model."""

    def get_queryset(self):
        qs = Apartment.objects.all()

        # Фильтрация по дому
        house_id = self.forwarded.get("house", None)
        if house_id:
            qs = qs.filter(house_id=house_id)

        # Фильтрация по секции
        section_id = self.forwarded.get("section", None)
        if section_id:
            qs = qs.filter(section_id=section_id)

        # Фильтрация по номеру квартиры (поиск)
        if self.q:
            qs = qs.filter(apartment_number__icontains=self.q)

        return qs

    def get_result_label(self, item):
        owner = item.user.get_full_name() if item.user else "—"
        return f"Кв. {item.apartment_number} ({owner})"


class TariffAutocomplete(autocomplete.Select2QuerySetView):
    """Autocomplete view for the Tariff model.

    Provides a queryset of Tariff objects to populate
    the Select2 dropdown in forms or search fields.
    """

    def get_queryset(self):
        """Return the queryset for Tariff autocomplete.

        Filters and returns all Tariff objects. You can
        extend this method to add filtering based on user input.
        """
        qs = Tariff.objects.all()

        # Получаем id квартиры из forwarded
        apartment_id = self.forwarded.get("flat", None)
        if apartment_id:
            qs = qs.filter(apartment__id=apartment_id).distinct()

        # Поиск по названию тарифа
        if self.q:
            qs = qs.filter(title__icontains=self.q)

        return qs


class AccountAutocomplete(autocomplete.Select2QuerySetView):
    """Autocomplete view for selecting PersonalAccount instances.

    Uses Django Select2.
    """

    def get_queryset(self):
        """Return a queryset of PersonalAccount objects filtered.

        The queryset is filtered according to the search query provided   widget.
        """
        qs = PersonalAccount.objects.all()

        # Получаем id квартиры из forwarded
        apartment_id = self.forwarded.get("flat", None)
        if apartment_id:
            qs = qs.filter(apartment__id=apartment_id).distinct()

        # Поиск по названию тарифа
        if self.q:
            qs = qs.filter(account_number__icontains=self.q)

        return qs


def get_owner(request):
    """Retrieve the owner details based on the provided account and flat IDs.

    This information is extracted from the request GET parameters.

    :param request: The HTTP request object.
    :return: An HTTP response containing the owner information (or an error).
    """
    account_id = request.GET.get("account")
    flat_id = request.GET.get("flat")

    user = None
    if account_id:
        account = get_object_or_404(PersonalAccount, pk=account_id)
        user = (
            getattr(account.apartment.user, "full_name", None)
            if account.apartment and account.apartment.user
            else None
        )
        phone = (
            getattr(account.apartment.user, "phone", None)
            if account.apartment and account.apartment.user
            else None
        )
    elif flat_id:
        flat = get_object_or_404(Apartment, pk=flat_id)
        user = getattr(flat.user, "full_name", None) if flat.user else None
        phone = getattr(flat.user, "phone", None) if flat.user else None
    else:
        phone = None

    return JsonResponse({"owner": user or "", "phone": phone or ""})


def get_apartment_counters(request, apartment_id):
    """Retrieve all counters associated with a given apartment.

    Args:
        request: The HTTP request object.
        apartment_id: ID of the apartment for which counters are requested.

    Returns:
        JsonResponse containing a list of counters.

    """
    apartment = Apartment.objects.get(id=apartment_id)
    counters = Counter.objects.filter(apartment=apartment)

    return JsonResponse(
        {
            "counters": [
                {
                    "id": c.id,
                    "name": c.name,
                    "service_id": c.service.id,
                    "last_value": c.last_value,
                }
                for c in counters
            ]
        }
    )


def get_tariff_services(request, tariff_id):
    """Retrieve all services associated with a given tariff.

    Args:
        request: The HTTP request object.
        tariff_id: ID of the tariff for which services are requested.

    Returns:
        JsonResponse containing a list of serialized services.

    """
    services = TariffService.objects.filter(tariff_id=tariff_id)
    data = []
    for s in services:
        try:
            data.append(
                {
                    "id": s.id,
                    "name": s.service.name if s.service else "",
                    "unit": s.unit.name if s.unit else "",
                    "price": float(s.price) if s.price else 0.0,
                }
            )
        except Exception:
            logging.exception("Ошибка при сериализации услуги %s", s.id)
    return JsonResponse({"services": data})


def trigger_mass_email(request):
    """Handle the sending of mass email messages to users.

    Processes the SendMessage form submission. If the request method is POST,
    validates the form and triggers the asynchronous email broadcast task.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: The response rendering the form page or redirecting after sending.

    """
    if request.method == "POST":
        form = SendMessage(request.POST)

        if form.is_valid():
            data = form.cleaned_data

            task = send_broadcast_email.delay(
                subject=data["title"],
                message=data["text"],
                flat_id=data.get("flat").pk if data.get("flat") else None,
                floor_id=data.get("floor").pk if data.get("floor") else None,
                section_id=data.get("section").pk if data.get("section") else None,
                house_id=data.get("house").pk if data.get("house") else None,
                only_debtors=data.get("only_debtors", False),
            )

            success_message = (
                f"Рассылка запущена! ID задачи Celery: {task.id}. Ожидайте выполнения."
            )
            messages.success(request, success_message)

            # Перенаправление на список сообщений
            return redirect(reverse("admin:message"))

    else:
        # GET-запрос: отобразить пустую форму
        form = SendMessage()

    # Путь к вашему HTML-шаблону
    context = {"form": form, "title": "Новое сообщение"}
    # Здесь используется имя шаблона, которое вы предоставили
    return render(request, "admin/send_message_form.html", context)


def get_sections_ajax(request):
    """Возвращает список секций для выбранного дома."""
    house_id = request.GET.get("house_id")
    sections = Section.objects.filter(house_id=house_id).values("id", "name")
    return JsonResponse(list(sections), safe=False)


def get_apartments_ajax(request):
    """Возвращает список квартир для выбранной секции."""
    section_id = request.GET.get("section_id")
    apartments = Apartment.objects.filter(section_id=section_id).values(
        "id", "apartment_number"
    )
    return JsonResponse(list(apartments), safe=False)


def get_apartment_owner_ajax(request):
    """Возвращает владельца квартиры."""
    apartment_id = request.GET.get("apartment_id")
    apartment = (
        Apartment.objects.filter(id=apartment_id).select_related("owner").first()
    )
    if apartment and apartment.owner:
        return JsonResponse({"owner": apartment.owner.get_full_name()})
    return JsonResponse({"owner": ""})
def check_unit_delete(request):
    unit_id = request.GET.get("unit_id")
    if not unit_id:
        return JsonResponse({"error": "Unit ID не указан"}, status=400)

    try:
        unit = Unit.objects.get(pk=unit_id)
    except Unit.DoesNotExist:
        return JsonResponse({"error": "Единица не найдена"}, status=404)

    if unit.service_set.exists():
        return JsonResponse({
            "can_delete": False,
            "message": f"Невозможно удалить единицу '{unit.name}', так как она используется в услугах."
        })
    else:
        return JsonResponse({"can_delete": True})

def get_account_info(request):
    account_id = request.GET.get("id")
    if not account_id:
        return JsonResponse({"error": "no id"}, status=400)

    try:
        account = (
            PersonalAccount.objects
            .select_related("apartment", "user", "apartment__house", "apartment__section")
            .get(pk=account_id)
        )
    except PersonalAccount.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)

    apartment = account.apartment
    user = account.user

    return JsonResponse({
        "house": apartment.house.pk,
        "section": apartment.section.pk,
        "flat": apartment.pk,
        "tariff": apartment.tariff.pk if apartment.tariff else "",
        "owner": user.full_name if user else "",
        "phone": user.phone if user else "",
    })