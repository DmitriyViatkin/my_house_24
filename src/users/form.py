"""Forms for  authentication and management within the cabinet (personal account)."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

from src.core.generator import generate_id_with_random_number

User = get_user_model()


class CreateOwnerFlatForm(forms.ModelForm):
    """Form to create a flat owner user."""

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control pass-value"})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )

    class Meta:
        """Meta information for the form."""

        model = User
        fields = [
            "first_name",
            "last_name",
            "second_name",
            "user_id",
            "viber",
            "telegram",
            "phone",
            "email",
            "image",
            "date_birthday",
            "password",
            "status",
            "description",
        ]
        labels = {
            "user_id": "ID",
            "first_name": "First Name",
            "second_name": "Middle Name",
            "last_name": "Last Name",
            "email": "Email (login)",
            "password": "Password",
            "phone": "Phone",
            "description": "Notes about the owner",
            "status": "Status",
            "is_staff": "Admin Access",
            "is_active": "Active",
        }
        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": "form-control", "maxlength": "255"}
            ),
            "second_name": forms.TextInput(
                attrs={"class": "form-control", "maxlength": "255"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control", "maxlength": "255"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "maxlength": "255"}
            ),
            "telegram": forms.TextInput(
                attrs={"class": "form-control", "maxlength": "255"}
            ),
            "viber": forms.TextInput(
                attrs={"class": "form-control", "maxlength": "255"}
            ),
            "description": forms.Textarea(attrs={"rows": 6, "class": "form-control"}),
            "user_id": forms.TextInput(
                attrs={"class": "form-control", "maxlength": "255"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "maxlength": "255"}
            ),
            "password": forms.PasswordInput(
                attrs={"class": "form-control pass-value", "maxlength": "255"}
            ),
            "role": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "date_birthday": forms.DateInput(
                attrs={"class": "form-control datepicker", "type": "date"}
            ),
        }

    def __init__(self, *args, **kwargs):
        """Initialize the form and set default values."""
        super().__init__(*args, **kwargs)
        self.initial["is_staff"] = False
        if not self.instance.pk:
            self.initial["user_id"] = generate_id_with_random_number()

    def clean(self):
        """Validate that password and password2 match."""
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password2 = cleaned_data.get("password2")
        if password and password2 and password != password2:
            self.add_error("password2", "Passwords do not match")
        return cleaned_data

    def save(self, *, commit=True):
        """Save the user instance with hashed password."""
        user = super().save(commit=False)
        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        user.is_staff = True
        if commit:
            user.save()
        return user


class StaffForm(forms.ModelForm):
    """Form for creating or editing staff users."""

    password2 = forms.CharField(
        label="Repeat Password",
        widget=forms.PasswordInput(
            attrs={"class": "form-control pass-value", "maxlength": "255"}
        ),
        required=True,
    )

    class Meta:
        """Meta information for the form."""

        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "password",
            "phone",
            "role",
            "status",
            "is_staff",
            "is_active",
        ]
        labels = {
            "first_name": "First Name",
            "last_name": "Last Name",
            "email": "Email (login)",
            "password": "Password",
            "phone": "Phone",
            "role": "Role",
            "status": "Status",
            "is_staff": "Admin Access",
            "is_active": "Active",
        }
        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": "form-control", "maxlength": "255"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control", "maxlength": "255"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "maxlength": "255"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "maxlength": "16"}
            ),
            "password": forms.PasswordInput(
                attrs={"class": "form-control pass-value", "maxlength": "255"}
            ),
            "role": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        """Initialize the form and set default staff flag."""
        super().__init__(*args, **kwargs)
        self.initial["is_staff"] = True

    def save(self, *, commit=True):
        """Save the staff user with hashed password."""
        user = super().save(commit=False)
        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        user.is_staff = True
        if commit:
            user.save()
        return user

    def clean(self):
        """Validate that password and password2 match."""
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password2 = cleaned_data.get("password2")
        if password and password2 and password != password2:
            self.add_error("password2", "Passwords do not match")
        return cleaned_data


class CabinetLoginForm(AuthenticationForm):
    """authentication form for cabinet login page using text input for username."""

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
                "placeholder": "Password",
                "aria-required": "true",
            }
        )
    )
