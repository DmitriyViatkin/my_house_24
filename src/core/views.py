"""Defines all the views for the Django project's core application."""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.shortcuts import render
from django.views.generic import TemplateView

from .forms import AdminLoginForm


# 1
class StatisticView(UserPassesTestMixin, TemplateView):
    """View for displaying website statistics and a dashboard."""

    template_name = "index.html"

    def test_func(self):
        """Check if the current user is a staff member."""
        return self.request.user.is_staff  # или is_superuser

    def handle_no_permission(self):
        """Handle cases where the user does not have permission.

        Redirects unauthenticated users to the login page and returns
        a 403 Forbidden error for authenticated users without staff status.
        """
        if self.request.user.is_authenticated:
            return HttpResponseForbidden("Доступ запрещён")

        return redirect_to_login(self.request.get_full_path())

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Статистика"
        return context


# 2
class ApartmentView(TemplateView):
    """View for managing apartments within the system."""

    template_name = "apartment/apartment.html"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Квартиры"
        return context


# 3
class CashboxView(TemplateView):
    """View for managing cashbox and financial transactions."""

    template_name = "cashbox/account_transaction.html"

    def get_context_data(self, **kwargs):
        """Add  the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Касса"
        return context


# 4
class CounterView(TemplateView):
    """View for displaying and managing meter readings."""

    template_name = "counter/counter_lists.html"

    def get_context_data(self, **kwargs):
        """Add  the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Счётчики"
        return context


# 5
class HouseView(TemplateView):
    """View for managing buildings or houses."""

    template_name = "house/house_list.html"

    def get_context_data(self, **kwargs):
        """Add  the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Дома"
        return context


# 6
class InvoiceView(TemplateView):
    """View for managing invoices and receipts."""

    template_name = "invoice/invoice_list.html"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Квитанции"  # Corrected typo
        return context


# 7
class MessagesView(TemplateView):
    """View for displaying and managing messages."""

    template_name = "messages/message_list.html"

    def get_context_data(self, **kwargs):
        """Add  the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Сообщения"
        return context


# 8
class UsersView(TemplateView):
    """View for managing user accounts and owners."""

    template_name = "owner_flat/owner_list.html"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Владельцы"  # Corrected typo
        return context


# 9
class HoumeView(TemplateView):  # Corrected class name from 'HoumeView'
    """View for the main homepage of the website."""

    template_name = "site_management/houm.html"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Главная"
        return context


# 10
class AboutView(TemplateView):
    """View for the "About Us" page."""

    template_name = "site_management/about_us.html"

    def get_context_data(self, **kwargs):
        """Add  the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "О нас"  # Corrected page title
        return context


# 11
class TicketView(TemplateView):
    """View for managing support tickets and requests."""

    template_name = "tasks/tasks_list.html"

    def get_context_data(self, **kwargs):
        """Add  the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Заявки"  # Corrected page title
        return context


# 12
class ServicesView(TemplateView):
    """View for displaying a list of services."""

    template_name = "site_management/services.html"

    def get_context_data(self, **kwargs):
        """Add  the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Услуги"
        return context


# 13
class TariffsView(TemplateView):
    """View for displaying and managing service tariffs."""

    template_name = "site_management/tariffs.html"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Тарифы"
        return context


# 14
class ContactView(TemplateView):  # Corrected class name from 'СontactView'
    """View for the website's contact page."""

    template_name = "site_management/contact.html"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Контакты"
        return context


# 15
class PersonalaccountView(TemplateView):
    """View for the user's personal account page."""

    template_name = "page.html"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Личный кабинет"  # Corrected page title
        return context


# 16
class ServiceView(TemplateView):
    """View for managing services within system settings."""

    template_name = "system_settings/services.html"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Услуги"
        return context


# 17
class TariffView(TemplateView):
    """View for managing tariffs within system settings."""

    template_name = "system_settings/tariff/tariff.html"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Тарифы"
        return context


# 18
class RoleView(TemplateView):
    """View for managing user roles within system settings."""

    template_name = "system_settings/roles.html"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Роли"
        return context


# 19
class UserAdminView(TemplateView):
    """View for managing user accounts by an administrator."""

    template_name = "system_settings/user_list.html"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Администратор пользователей"  # Corrected page title
        return context


# 20
class PaymentArticlesView(TemplateView):
    """View for managing payment articles and details."""

    template_name = "system_settings/payment_details.html"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Платежные статьи"  # Corrected page title
        return context


# 21
class AdminLoginView(LoginView):
    """A custom view for the admin login page."""

    template_name = "registration/login.html"
    redirect_authenticated_user = True
    authentication_form = AdminLoginForm  # 🔹 ключове — вказати свою форму

    def get_context_data(self, **kwargs):
        """Add the custom admin form to the template context."""
        context = super().get_context_data(**kwargs)
        context["admin_form"] = context.get("form", self.authentication_form())
        context["cabinet_form"] = AdminLoginForm()  # якщо теж з атрибутами
        context["active_tab"] = "admin"
        return context

    def post(self, request, *args, **kwargs):
        """Handle POST requests to the login view."""
        form = self.authentication_form(
            request, data=request.POST
        )  # 🔹 тепер своя форма
        if form.is_valid():
            login(request, form.get_user())
            return redirect("/admin/")
        messages.error(request, "Неверный логин или пароль")
        context = {
            "admin_form": form,
            "cabinet_form": AdminLoginForm(),
            "active_tab": "admin",
        }
        return render(request, self.template_name, context)
