"""Views for the user-facing cabinet application."""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from .form import CabinetLoginForm


class CabinetLoginView(LoginView):
    """Custom view for user login to the cabinet.

    This view uses a custom authentication form and redirects
    authenticated users to the cabinet page.
    """

    template_name = "registration/login.html"
    redirect_authenticated_user = True
    form_class = CabinetLoginForm
    success_url = reverse_lazy("cabinet")

    def get_context_data(self, **kwargs):
        """Add the custom cabinet form to the template context."""
        context = super().get_context_data(**kwargs)
        context["cabinet_form"] = context.get("form", self.form_class())
        context["admin_form"] = CabinetLoginForm()
        context["active_tab"] = "cabinet"
        return context

    def post(self, request, *args, **kwargs):
        """Handle the POST request for user login."""
        form = self.form_class(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("cabinet/")
        messages.error(request, "Неверный логин или пароль")
        context = {
            "cabinet_form": form,
            "admin_form": CabinetLoginForm(),
            "active_tab": "cabinet",
        }
        return render(request, self.template_name, context)


class CabinetView(TemplateView):
    """View for displaying the user's personal cabinet page."""

    template_name = "profile.html"

    def get_context_data(self, **kwargs):
        """Add the page title to the template context."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Cabinet"
        return context
