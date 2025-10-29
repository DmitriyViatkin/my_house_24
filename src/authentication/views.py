"""Views for authentication: registration, login for cabinet and admin panel.

Provide all authentication-related views, including registration, login,
and privacy policy page.
"""

import logging

from django.contrib.auth import authenticate
from django.contrib.auth import get_backends
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.urls import reverse_lazy
from django.views.generic import FormView
from django.views.generic import TemplateView

from .forms import AdminLoginForm
from .forms import CabinetLoginForm
from .forms import RegistrationForm

logger = logging.getLogger(__name__)


class RegistrationView(FormView):
    """Register a new user and login immediately after registration."""

    template_name = "registration/registration.html"
    form_class = RegistrationForm
    success_url = reverse_lazy("cabinet")

    def get_context_data(self, **kwargs):
        """Add the active tab to the template context."""
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "user"
        return context

    def form_valid(self, form):
        """Save the user and login immediately after registration.

        Log all registration steps.
        """
        try:
            logger.debug("[RegistrationView] Attempt to register a new user...")

            # Save the user
            user = form.save()

            backend = get_backends()[0]
            user.backend = f"{backend.__module__}.{backend.__class__.__name__}"

            # Login the user
            login(self.request, user)
            logger.info(
                "[RegistrationView] User registered: %s (user_id=%s)",
                user.email,
                user.user_id,
            )
            logger.debug(
                "[RegistrationView] User %s successfully logged in.", user.email
            )

            return super().form_valid(form)

        except Exception:
            logger.exception("[RegistrationView] Error occurred during registration")
            form.add_error(
                None, "An error occurred during registration. Please try again."
            )
            return super().form_invalid(form)

    def form_invalid(self, form):
        """Log form errors (validation errors, duplicates, etc.)."""
        logger.warning("[RegistrationView] Form errors: %s", form.errors.as_json())
        return super().form_invalid(form)


class PrivatePolicy(TemplateView):
    """Display the privacy policy page."""

    template_name = "registration/private_policy.html"


class CustomLoginView(LoginView):
    """Provide a unified login view for cabinet and admin panel."""

    template_name = "registration/login.html"
    redirect_authenticated_user = True
    authentication_form = None

    def get_context_data(self, **kwargs):
        """Add custom forms and reCAPTCHA key to the context."""
        context = super().get_context_data(**kwargs)
        context.setdefault("cabinet_form", CabinetLoginForm(prefix="cabinet"))
        context.setdefault("admin_form", AdminLoginForm(prefix="admin"))
        context.setdefault("active_tab", "cabinet")
        context["recaptcha_site_key"] = "6Les2q8rAAAAAOvjjcz_-ninog2x-5IyRVKGrp3G"
        logger.debug("Set RECAPTCHA_SITE_KEY = %s", context["recaptcha_site_key"])
        return context

    def post(self, request, *args, **kwargs):
        """Handle login for cabinet or admin panel and render errors if any."""
        logger.debug("POST data: %s", request.POST.dict())

        # Determine which form was submitted
        if "cabinet_login" in request.POST:
            return self._handle_cabinet_login(request)
        if "admin_login" in request.POST:
            return self._handle_admin_login(request)
        return self._render_empty_forms(request)

    def _handle_cabinet_login(self, request):
        """Process cabinet login."""
        active_tab = "cabinet"
        logger.debug("Handle cabinet login")
        cabinet_form = CabinetLoginForm(request, data=request.POST, prefix="cabinet")
        admin_form = AdminLoginForm(prefix="admin")  # empty admin form

        if cabinet_form.is_valid():
            user = self._authenticate_user(
                cabinet_form.cleaned_data["username"],
                cabinet_form.cleaned_data["password"],
            )
            if user:
                if user.is_staff:
                    cabinet_form.add_error(None, "Access denied for administrators.")
                else:
                    login(request, user)
                    logger.debug("Redirect cabinet user to 'cabinet'")
                    return redirect(reverse("cabinet"))
            else:
                cabinet_form.add_error(None, "Incorrect email or password")
        else:
            logger.debug("Cabinet form contains errors: %s", cabinet_form.errors)

        return render(
            request,
            self.template_name,
            {
                "cabinet_form": cabinet_form,
                "admin_form": admin_form,
                "active_tab": active_tab,
            },
        )

    def _handle_admin_login(self, request):
        """Process admin login."""
        active_tab = "admin"
        logger.debug("Handle admin login")
        admin_form = AdminLoginForm(request, data=request.POST, prefix="admin")
        cabinet_form = CabinetLoginForm(prefix="cabinet")  # empty cabinet form

        if admin_form.is_valid():
            user = self._authenticate_user(
                admin_form.cleaned_data["username"], admin_form.cleaned_data["password"]
            )
            if user:
                if not user.is_staff:
                    admin_form.add_error(None, "Access denied: administrators only.")
                else:
                    login(request, user)
                    logger.debug("Redirect admin user to 'admin:dashboard'")
                    return redirect(reverse("admin:dashboard"))
            else:
                admin_form.add_error(None, "Incorrect email or password")
        else:
            logger.debug("Admin form contains errors: %s", admin_form.errors)

        return render(
            request,
            self.template_name,
            {
                "cabinet_form": cabinet_form,
                "admin_form": admin_form,
                "active_tab": active_tab,
            },
        )

    def _render_empty_forms(self, request):
        """Render empty forms when POST contains no explicit choice."""
        logger.debug("POST request without explicit form choice")
        cabinet_form = CabinetLoginForm(prefix="cabinet")
        admin_form = AdminLoginForm(prefix="admin")
        active_tab = "cabinet"
        return render(
            request,
            self.template_name,
            {
                "cabinet_form": cabinet_form,
                "admin_form": admin_form,
                "active_tab": active_tab,
            },
        )

    @staticmethod
    def _authenticate_user(username, password):
        """Authenticate user with given credentials."""
        return authenticate(username=username, password=password)
