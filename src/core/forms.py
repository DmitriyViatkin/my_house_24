"""Forms for the core application."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm


class AdminLoginForm(AuthenticationForm):
    """A custom authentication form for the admin login page.

    This form uses a text input widget for the username field.
    """

    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "id": "loginform-username",
                "class": "form-control",
                "placeholder": "E-mail",
                "aria-required": "true",
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "id": "loginform-password",
                "class": "form-control",
                "placeholder": "Пароль",
                "aria-required": "true",
            }
        )
    )
