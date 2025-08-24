"""Views for authentication in cabinet and admin panel."""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse

from .forms import AdminLoginForm
from .forms import CabinetLoginForm


class CustomLoginView(LoginView):
    """Unified login view for cabinet and admin panel with staff check."""

    template_name = "registration/login.html"
    redirect_authenticated_user = True
    authentication_form = None  # отключаем дефолтную форму

    def get_context_data(self, **kwargs):
        """Add cabinet and admin login forms to the context."""
        context = super().get_context_data(**kwargs)
        context.setdefault("cabinet_form", CabinetLoginForm())
        context.setdefault("admin_form", AdminLoginForm())
        context.setdefault("active_tab", "cabinet")
        return context

    def post(self, request, *args, **kwargs):
        """Handle POST requests for cabinet and admin login forms."""
        active_tab = "cabinet"

        cabinet_form = CabinetLoginForm(request, data=request.POST)
        admin_form = AdminLoginForm(request, data=request.POST)

        # Вход в кабинет
        if "cabinet_login" in request.POST:
            active_tab = "cabinet"

            if cabinet_form.is_valid():
                user = cabinet_form.get_user()
                login(request, user)
                return redirect(reverse("cabinet"))

        # Вход в админку
        elif "admin_login" in request.POST:
            active_tab = "admin"

            if admin_form.is_valid():
                user = admin_form.get_user()

                if not user.is_staff:
                    messages.error(
                        request, "Доступ запрещён: только для администраторов."
                    )
                    return redirect(reverse("login"))

                login(request, user)
                return redirect(reverse("admin:dashboard"))

        # Рендер формы с ошибками
        return render(
            request,
            self.template_name,
            {
                "cabinet_form": cabinet_form,
                "admin_form": admin_form,
                "active_tab": active_tab,
            },
        )
