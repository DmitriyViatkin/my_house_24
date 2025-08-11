"""Forms for user authentication within the cabinet (personal account)."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm


class CabinetLoginForm(AuthenticationForm):
    """A custom authentication form for the user cabinet login page.

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
