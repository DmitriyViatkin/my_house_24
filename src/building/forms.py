"""Forms for the building app, including House, Section, Floor, and Staff."""

from django import forms
from django.contrib.auth import get_user_model
from django.forms import inlineformset_factory

from src.building.models import Floor
from src.building.models import House
from src.building.models import Section
from src.building.models import Staff

User = get_user_model()


class HouseForm(forms.ModelForm):
    """Form for creating and updating House instances."""

    class Meta:
        """Meta options for HouseForm."""

        model = House
        fields = ["title", "address", "image1", "image2", "image3", "image4", "image5"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "image1": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
            "image2": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
            "image3": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
            "image4": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
            "image5": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
        }
        labels = {
            "title": "Название",
            "address": "Адрес",
            "image1": "Изображение #1. Размер: (522x350)",
            "image2": "Изображение #2. Размер: (248x160)",
            "image3": "Изображение #3. Размер: (248x160)",
            "image4": "Изображение #4. Размер: (248x160)",
            "image5": "Изображение #5. Размер: (248x160)",
        }


class SectionForm(forms.ModelForm):
    """Form for creating and updating Section instances."""

    class Meta:
        """Meta options for SectionForm."""

        model = Section
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Название секции",
                }
            ),
        }
        labels = {
            "name": "Название секции",
        }


class FloorForm(forms.ModelForm):
    """Form for creating and updating Floor instances."""

    class Meta:
        """Meta options for FloorForm."""

        model = Floor
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Название этажа",
                }
            ),
        }
        labels = {
            "name": "Название",
        }


class StaffForm(forms.ModelForm):
    """Form for creating and updating Staff instances."""

    full_name = forms.ModelChoiceField(
        queryset=User.objects.select_related("role").all(),
        label="ФИО",
        required=True,
        widget=forms.Select(
            attrs={
                "class": "form-control useradmin-select",
            }
        ),
    )
    user_role = forms.CharField(
        label="Роль",
        required=False,
        disabled=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control useradmin-role",
                "readonly": "readonly",
            }
        ),
    )

    class Meta:
        """Meta options for StaffForm."""

        model = Staff
        fields = ["full_name", "user_role"]

    def __init__(self, *args, user_roles: dict | None = None, **kwargs):
        """Initialize the form and set custom labels and initial values.

        Args:
            *args: Positional arguments passed to the parent form.
            user_roles (dict | None): Optional mapping of user IDs to role names.
            **kwargs: Keyword arguments passed to the parent form.

        """
        super().__init__(*args, **kwargs)

        # Customize the display of the full_name field
        self.fields["full_name"].label_from_instance = (
            lambda obj: f"{obj.get_full_name()}"
            f" ({obj.role.name if obj.role else 'Без роли'})"
        )

        # Set initial value for user_role if instance exists
        if self.instance and self.instance.pk and self.instance.user:
            self.fields["user_role"].initial = (
                self.instance.user.role.name if self.instance.user.role else ""
            )

        # Override initial value from user_roles mapping
        if user_roles and self.instance and self.instance.user_id:
            role = user_roles.get(self.instance.user_id)
            if role:
                self.fields["user_role"].initial = role

    def clean(self) -> dict:
        """Ensure the `user_role` field is populated.

        Returns:
            dict: The cleaned form data.

        """
        cleaned_data = super().clean()
        user = cleaned_data.get("full_name")
        if user and user.role:
            cleaned_data["user_role"] = user.role.name
        return cleaned_data

    def save(self, *, commit: bool = True) -> Staff:
        """Save the Staff instance, assigning the user from cleaned_data.

        Args:
            commit (bool): Whether to commit the save to the database.

        Returns:
            Staff: The saved Staff instance.

        """
        staff = super().save(commit=False)
        staff.user = self.cleaned_data.get("full_name")
        if commit:
            staff.save()
        return staff


# --- Inline formsets ---
SectionFormSet = inlineformset_factory(
    House, Section, form=SectionForm, extra=1, can_delete=True
)

FloorFormSet = inlineformset_factory(
    Section, Floor, form=FloorForm, extra=1, can_delete=True
)

StaffFormSet = inlineformset_factory(
    House, Staff, form=StaffForm, extra=1, can_delete=True
)
