"""Defines all the views for the Django project's core application."""

import json

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.contrib.auth.views import redirect_to_login
from django.db import transaction
from django.forms import modelformset_factory
from django.http import HttpResponseForbidden
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic import ListView
from django.views.generic import TemplateView
from django.views.generic import UpdateView
from django.views.generic import View
from django.views.generic.edit import FormMixin
from django_filters.views import FilterView

from src.building.forms import FloorFormSet
from src.building.forms import HouseForm
from src.building.forms import SectionFormSet
from src.building.forms import StaffForm
from src.building.forms import StaffFormSet
from src.building.models import House
from src.financials.forms import PaymentArticlesForm
from src.financials.models import PaymentArticles
from src.services.models import PaymentDetail
from src.services.models import Service
from src.services.models import Tariff
from src.services.models import TariffService
from src.services.models import Unit
from src.users.form import CreateOwnerFlatForm
from src.users.models import Role
from src.users.models import User

from .filters import UserFilter
from .forms import AdminLoginForm
from .forms import PaymentDetailsForm
from .forms import RoleForm
from .forms import ServiceFormSet
from .forms import TariffForm
from .forms import TariffServiceFormSet
from .forms import UnitFormSet


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
class HouseView(FilterView, ListView):
    """View for managing buildings or houses."""

    model = House
    template_name = "house/house_list.html"
    filterset_class = UserFilter
    paginate_by = 20

    def get_context_data(self, **kwargs):
        """Add  the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Дома"
        return context


class HouseAddView(FormView):
    """View for adding a new House, including related sections, floors, and staff."""

    template_name = "house/new_house.html"
    form_class = HouseForm
    success_url = reverse_lazy("admin:house")

    def get_context_data(self, **kwargs):
        """Prepare context data for HouseAddView."""
        context = super().get_context_data(**kwargs)

        # Только пользователи с is_staff=True
        users_qs = User.objects.filter(is_staff=True).select_related("role")
        user_roles = {user.pk: user.role.name if user.role else "" for user in users_qs}

        context["user_roles_json"] = json.dumps(user_roles)
        context["users"] = users_qs

        if self.request.POST:
            context["section_set"] = SectionFormSet(self.request.POST, prefix="section")
            context["floor_set"] = FloorFormSet(self.request.POST, prefix="floor")
            context["staff_set"] = StaffFormSet(
                self.request.POST,
                prefix="staff",
                form_kwargs={"user_roles": user_roles},
            )
        else:
            context["section_set"] = SectionFormSet(prefix="section")
            context["floor_set"] = FloorFormSet(prefix="floor")
            context["staff_set"] = StaffFormSet(
                prefix="staff", form_kwargs={"user_roles": user_roles}
            )

        return context

    def form_valid(self, form):
        """Save the House and related formsets."""
        context = self.get_context_data()
        section_set = context["section_set"]
        floor_set = context["floor_set"]
        staff_set = context["staff_set"]

        if section_set.is_valid() and floor_set.is_valid() and staff_set.is_valid():
            with transaction.atomic():
                self.object = form.save()
                section_set.instance = self.object
                staff_set.instance = self.object

                sections = section_set.save()
                staff_set.save()

                floors = floor_set.save(commit=False)
                for floor in floors:
                    floor.house = self.object
                    if sections:
                        floor.section = sections[0]
                    floor.save()

            return super().form_valid(form)
        return self.form_invalid(form)


class HouseUpdateView(UpdateView):
    """View for updating an existing House, including sections, floors, and staff."""

    model = House
    template_name = "house/new_house.html"
    form_class = HouseForm
    success_url = reverse_lazy("admin:house")

    def get_context_data(self, **kwargs):
        """Prepare context data for HouseUpdateView."""
        context = super().get_context_data(**kwargs)
        user_roles = {
            user.pk: user.role.name if user.role else ""
            for user in User.objects.select_related("role").all()
        }
        context["user_roles_json"] = json.dumps(user_roles)

        if self.request.POST:
            context["section_set"] = SectionFormSet(
                self.request.POST, prefix="section", instance=self.object
            )
            context["floor_set"] = FloorFormSet(self.request.POST, prefix="floor")
            context["staff_set"] = StaffFormSet(
                self.request.POST,
                prefix="staff",
                instance=self.object,
                form_kwargs={"user_roles": user_roles},
            )
        else:
            context["section_set"] = SectionFormSet(
                prefix="section", instance=self.object
            )
            context["floor_set"] = FloorFormSet(prefix="floor")
            context["staff_set"] = StaffFormSet(
                prefix="staff",
                instance=self.object,
                form_kwargs={"user_roles": user_roles},
            )

        return context

    def form_valid(self, form):
        """Save the House and related formsets."""
        context = self.get_context_data()
        section_set = context["section_set"]
        floor_set = context["floor_set"]
        staff_set = context["staff_set"]

        if section_set.is_valid() and floor_set.is_valid() and staff_set.is_valid():
            self.object = form.save()
            section_set.instance = self.object
            staff_set.instance = self.object

            sections = section_set.save()
            staff_set.save()

            floors = floor_set.save(commit=False)
            for floor in floors:
                if sections:
                    floor.section = sections.first()
                floor.save()
            floor_set.save_m2m()

            return super().form_valid(form)
        return self.form_invalid(form)


class HouseDeleteView(DeleteView):
    """View for deleting a House."""

    model = House
    template_name = "house/delete_house.html"
    success_url = reverse_lazy("admin:house")

    def get_context_data(self, **kwargs):
        """Add custom context for delete template."""
        context = super().get_context_data(**kwargs)
        context["title"] = f"Удаление дома: {self.object.name}"
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
class UsersView(FilterView, ListView):
    """View for listing system users (owners)."""

    model = User
    template_name = "owner_flat/owner_list.html"
    context_object_name = "users"
    filterset_class = UserFilter
    paginate_by = 20

    def get_queryset(self):
        """Return a queryset with prefetch_related for apartments and houses."""
        return (
            super()
            .get_queryset()
            .prefetch_related("apartment_set", "apartment_set__floor__section__house")
        )

    def get_context_data(self, **kwargs):
        """Add page title to context."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Владельцы"
        return context


class CreateOwnerFlat(FormView):
    """View for creating a new apartment owner."""

    template_name = "owner_flat/new_owner.html"
    form_class = CreateOwnerFlatForm
    success_url = reverse_lazy("admin:users")

    def form_valid(self, form):
        """Save the form and redirect to the users list."""
        form.save()
        return redirect("admin:users")


# 9
class HoumeView(TemplateView):
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
class ContactView(TemplateView):
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
    """A view for managing and displaying services and units.

    This view uses formsets to handle the creation and editing of service
     and unit objects.
    """

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
        """Handle GET requests to display the role management form."""
        context = super().get_context_data(**kwargs)

        units_queryset = Unit.objects.order_by("id")
        context["units"] = units_queryset

        context["formset1"] = kwargs.get("formset1") or self.get_formset(
            ServiceFormSet,
            queryset=Service.objects.select_related("unit").all(),
            prefix="services",
            form_kwargs={"unit_queryset": units_queryset},
        )

        context["formset2"] = kwargs.get("formset2") or self.get_formset(
            UnitFormSet, queryset=units_queryset, prefix="units"
        )

        return context

    def post(self, request, *args, **kwargs):
        """Handle POST requests for unit formset submission."""
        units_queryset = Unit.objects.order_by("id")

        formset1 = self.get_formset(
            ServiceFormSet,
            queryset=Service.objects.select_related("unit").all(),
            data=request.POST,
            prefix="services",
            form_kwargs={"unit_queryset": units_queryset},
        )
        formset2 = self.get_formset(
            UnitFormSet, queryset=units_queryset, data=request.POST, prefix="units"
        )

        if formset1.is_valid() and formset2.is_valid():
            with transaction.atomic():
                formset1.save()
                formset2.save()
            return redirect("admin:service")
        # Re-render the page with the invalid formsets
        context = {
            "formset1": formset1,
            "formset2": formset2,
            "units_formset_name": "Unit",  # Or whatever variable name you use
            "services_formset_name": "Service",  # Or whatever variable name you use
        }
        return render(request, "your_template.html", context)


# 17
class TariffView(ListView):
    """View for managing tariffs within system settings."""

    model = Tariff
    template_name = "system_settings/tariff/tariffs.html"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Тарифы"
        return context


class TariffDeleteView(DeleteView):
    """View for deleting a Tariff object.

    This view handles the deletion of a specific tariff instance and redirects
    the user to the tariff list page upon success.
    """

    model = Tariff
    success_url = reverse_lazy("admin:tariff")


class TariffServiceFormView(FormView):
    """View for creating a new tariff with its related services.

    This class uses a main form for the tariff and a formset for its services.
    """

    template_name = "system_settings/tariff/new_tariffs.html"
    form_class = TariffForm  # головна форма — Tariff

    def get_context_data(self, **kwargs):
        """Handle GET requests to display the role management form."""
        context = super().get_context_data(**kwargs)
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


class TariffUpdateView(UpdateView):
    """View for updating an existing Tariff and its related services."""

    model = Tariff
    form_class = TariffForm
    template_name = "system_settings/tariff/new_tariffs.html"
    pk_url_kwarg = "pk"  # ожидаем, что в URL будет параметр pk

    def get_context_data(self, **kwargs):
        """Handle GET requests to display the role management form."""
        context = super().get_context_data(**kwargs)
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


class TariffCopyView(View):
    """A view to copy an existing tariff and its related services.

    This class handles the logic for duplicating a tariff object.
    """

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


# 18
class RoleView(FormView):
    """A view for managing user roles.

    This view uses a model formset to display and edit a list of roles.
    """

    RoleFormSet = modelformset_factory(Role, form=RoleForm, extra=0)

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
class UserAdminView(TemplateView):
    """View for managing user accounts by an administrator."""

    template_name = "system_settings/users/table.html"

    def get_context_data(self, **kwargs):
        """Add the page title to the context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Администратор пользователей"  # Corrected page title
        return context


# 20
class PaymentDetailView(UpdateView):
    """View for updating a single fixed payment article."""

    model = PaymentDetail
    template_name = "system_settings/payment_details.html"
    form_class = PaymentDetailsForm
    success_url = reverse_lazy("admin:payment_detail")

    def get_object(self, queryset=None):
        """Return the first PaymentDetail object."""
        return PaymentDetail.objects.first()

    def form_valid(self, form):
        """Handle valid form submission."""
        return super().form_valid(form)


class PaymentArticlesView(ListView):
    """View for updating a single fixed payment article."""

    model = PaymentArticles
    template_name = "system_settings/payment_articles.html"
    queryset = PaymentArticles.objects.all()


class EditPaymentArticlesView(FormMixin, DetailView):
    """View for updating a single fixed payment article."""

    model = PaymentArticles
    form_class = PaymentArticlesForm
    template_name = "system_settings/edit_payment_article.html"

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


class CreatePaymentArticlesView(CreateView):
    """View for creating a new payment article."""

    model = PaymentArticles
    form_class = PaymentArticlesForm
    template_name = "system_settings/edit_payment_article.html"

    def get_success_url(self):
        """Return the URL to redirect to after successfully creating the article."""
        return reverse_lazy("admin:payment-articles")  # URL для перенаправления после
        # сохранения

    def form_valid(self, form):
        """Save the form and redirect on successful validation."""
        form.save()
        return super().form_valid(form)


class PaymentArticlesDeleteView(DeleteView):
    """View for deleting a Tariff object.

    This view handles the deletion of a specific tariff instance and redirects
    the user to the tariff list page upon success.
    """

    model = PaymentArticles
    success_url = reverse_lazy("admin:payment-articles")


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


class UserAjaxDatatableView(View):
    """AJAX view to provide user data for datatables."""

    def get(self, request, *args, **kwargs):
        """Return JSON data for datatables."""
        return JsonResponse({"data": []})


class UserCreateStaff(CreateView):
    """User creation view."""

    template_name = "system_settings/users/new_user.html"
    model = User
    form_class = StaffForm
    success_url = reverse_lazy("admin:user-admin")


class UserUpdateStaff(UpdateView):
    """User update view."""

    template_name = "system_settings/users/new_user.html"
    model = User
    form_class = StaffForm
    success_url = reverse_lazy("admin:user-admin")

    def form_valid(self, form):
        """Save the updated staff user and redirect."""
        return super().form_valid(form)


class UserDeleteStaff(DeleteView):
    """User deletion view."""

    template_name = "admin/user_confirm_delete.html"
    model = User
    success_url = reverse_lazy("admin:user-admin")

    def get_context_data(self, **kwargs):
        """Add custom context for the delete confirmation template."""
        context = super().get_context_data(**kwargs)
        context["title"] = f"Удаление пользователя: {self.object.username}"
        return context
