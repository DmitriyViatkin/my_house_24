"""Define authentication forms for user registration and login.

This module provides:
- RegistrationForm: Register a new user with full name, email, password,
  logging, and unique ID generation.
- AdminLoginForm: Authenticate admin users with CAPTCHA.
- CabinetLoginForm: Authenticate regular cabinet users with CAPTCHA.
"""

import logging

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _
from snowpenguin.django.recaptcha3.fields import ReCaptchaField

from src.core.generator import generate_id_with_random_number
from src.users.models import User

MIN_FULL_NAME_PARTS = 2  # Minimum parts in full name
SECOND_NAME_INDEX = 2  # Index for second_name in full name parts
MAX_USER_ID_ATTEMPTS = 10
logger = logging.getLogger(__name__)


# Define constant for minimum parts in full name
MIN_FULL_NAME_PARTS = 2


class RegistrationForm(UserCreationForm):
    """Register a new user with logging and unique ID generation."""

    full_name = forms.CharField(
        label="Full Name",
        max_length=255,
        widget=forms.TextInput(attrs={"placeholder": "Ivanov Ivan Ivanovich"}),
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"placeholder": "example@mail.com"}),
    )
    agree_privacy = forms.BooleanField(
        label="Agree with privacy policy",
        required=True,
        error_messages={"required": "You must agree with the privacy policy."},
    )

    class Meta:
        """Specify model and fields for registration form."""

        model = User
        fields = ("full_name", "email", "password1", "password2", "agree_privacy")

    def clean_full_name(self):
        """Validate full name has at least two parts."""
        full_name = self.cleaned_data["full_name"].strip()
        parts = full_name.split()
        if len(parts) < MIN_FULL_NAME_PARTS:
            error_message = "Enter at least surname and first name (e.g., Ivanov Ivan)."
            raise forms.ValidationError(error_message)
        return full_name

    def save(self, *, commit: bool = True):
        """Save the user, generate unique user_id, and log actions."""
        user = super().save(commit=False)

        # Split full name and assign fields
        full_name = self.cleaned_data["full_name"].strip()
        parts = full_name.split()
        user.last_name = parts[0]
        user.first_name = parts[1] if len(parts) > 1 else ""
        user.second_name = (
            parts[SECOND_NAME_INDEX] if len(parts) > SECOND_NAME_INDEX else ""
        )
        user.email = self.cleaned_data["email"]

        logger.debug("[RegistrationForm] Start saving user: %s", user.email)

        # Generate unique user_id manually
        for i in range(MAX_USER_ID_ATTEMPTS):
            candidate_id = generate_id_with_random_number()
            logger.debug(
                "[RegistrationForm] Attempt %d: user_id=%s", i + 1, candidate_id
            )
            if not User.objects.filter(user_id=candidate_id).exists():
                user.user_id = candidate_id
                logger.debug(
                    "[RegistrationForm] Successfully assigned user_id=%s", candidate_id
                )
                break
        else:
            error_log = (
                f"[RegistrationForm] Failed to generate unique user_id after "
                f"{MAX_USER_ID_ATTEMPTS} attempts."
            )
            logger.error(error_log)
            error_message = "Failed to generate a unique user ID."
            raise forms.ValidationError(error_message)

        # Save user if commit is True
        if commit:
            try:
                user.save()
                logger.info(
                    "[RegistrationForm] User %s successfully saved with ID=%s",
                    user.email,
                    user.user_id,
                )
            except Exception:
                logger.exception("[RegistrationForm] Error occurred while saving user")
                raise

        return user


class AdminLoginForm(AuthenticationForm):
    """Authenticate admin users with CAPTCHA."""

    captcha = ReCaptchaField()
    username = forms.CharField(
        label="E-mail or User ID",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "E-mail or User ID"}
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Password"}
        )
    )

    def confirm_login_allowed(self, user):
        """Prevent non-staff users from logging in."""
        if not user.is_staff:
            raise forms.ValidationError(
                _("Access denied: only administrators allowed."), code="invalid_login"
            )
        if not user.is_active:
            raise forms.ValidationError(_("Account is inactive."), code="inactive")


class CabinetLoginForm(AuthenticationForm):
    """Authenticate cabinet users with CAPTCHA."""

    captcha = ReCaptchaField()
    username = forms.CharField(
        label="E-mail or User ID",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "E-mail or User ID"}
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Password"}
        )
    )

    def confirm_login_allowed(self, user):
        """Prevent staff users from accessing cabinet."""
        if user.is_staff:
            raise forms.ValidationError(
                _("Cabinet access is forbidden for administrators."),
                code="invalid_login",
            )
        if not user.is_active:
            raise forms.ValidationError(_("Account is inactive."), code="inactive")
