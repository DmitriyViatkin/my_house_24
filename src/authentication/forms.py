"""Forms for authentication in admin panel and cabinet (personal account)."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _
from snowpenguin.django.recaptcha3.fields import ReCaptchaField


class AdminLoginForm(AuthenticationForm):
    """Authentication form for admin panel login (staff only)."""

    captcha = ReCaptchaField()

    username = forms.CharField(
        label="E-mail",
        widget=forms.TextInput(
            attrs={
                "id": "loginform-username",
                "class": "form-control",
                "placeholder": "E-mail",
                "aria-required": "true",
            }
        ),
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

    def __init__(self, request=None, *args, **kwargs):
        """Initialize form and configure username field dynamically."""
        super().__init__(request, *args, **kwargs)
        # Используем public API вместо приватного _meta
        self.username_field = get_user_model().USERNAME_FIELD

    def confirm_login_allowed(self, user):
        """Allow login only for active staff users."""
        if not user.is_staff:
            raise forms.ValidationError(
                _("Доступ запрещён: только для администраторов."),
                code="invalid_login",
            )
        if not user.is_active:
            raise forms.ValidationError(
                _("Аккаунт не активен."),
                code="inactive",
            )


class CabinetLoginForm(AuthenticationForm):
    """Authentication form for cabinet login page (non-staff only)."""

    captcha = ReCaptchaField()

    username = forms.CharField(
        label="E-mail",
        widget=forms.TextInput(
            attrs={
                "id": "loginform-username",
                "class": "form-control",
                "placeholder": "E-mail",
                "aria-required": "true",
            }
        ),
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

    def confirm_login_allowed(self, user):
        """Запрещаем вход staff пользователям в кабинет."""
        if user.is_staff:
            raise forms.ValidationError(
                _("Доступ в кабинет запрещён для администраторов."),
                code="invalid_login",
            )
        if not user.is_active:
            raise forms.ValidationError(
                _("Аккаунт не активен."),
                code="inactive",
            )

    def clean(self):
        """Validate form and return cleaned data without debug prints."""
        return super().clean()
