"""Forms for the building app: Apartment, House, Section, Floor, and Staff."""

from django import forms
from django.contrib.auth import get_user_model
from django.forms import inlineformset_factory

from src.building.models import Apartment
from src.building.models import Floor
from src.building.models import House
from src.building.models import Section
from src.building.models import Staff
from src.financials.models import PersonalAccount

User = get_user_model()


class ApartmentForm(forms.ModelForm):
    """Form for creating and updating Apartment instances."""

    account_uid = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "flatform-account_uid",
                "placeholder": "Personal account",
            }
        ),
    )

    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.Select(
            attrs={
                "class": "form-control select2",
                "id": "flatform-user_id",
            }
        ),
        label="Owner",
    )

    class Meta:
        """Meta options for ApartmentForm."""

        model = Apartment
        fields = [
            "apartment_number",
            "area",
            "house",
            "section",
            "floor",
            "tariff",
            "user",
        ]
        widgets = {
            "apartment_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "id": "flatform-flat",
                    "placeholder": "Apartment number",
                }
            ),
            "area": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "id": "flatform-square",
                    "placeholder": "Area (sq.m.)",
                }
            ),
            "house": forms.Select(
                attrs={"class": "form-control", "id": "flatform-house_id"}
            ),
            "section": forms.Select(
                attrs={"class": "form-control", "id": "flatform-section_id"}
            ),
            "floor": forms.Select(
                attrs={"class": "form-control", "id": "flatform-floor_id"}
            ),
            "tariff": forms.Select(
                attrs={"class": "form-control", "id": "flatform-tariff_id"}
            ),
        }

    def __init__(self, *args, **kwargs):
        """Initialize ApartmentForm with dynamic section and floor queryset."""
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.account:
            self.fields["account_uid"].initial = self.instance.account.account_number

        self.fields["user"].label_from_instance = (
            lambda obj: f"{obj.last_name} {obj.first_name} {obj.second_name}".strip()
        )

        self.fields["section"].queryset = Section.objects.none()
        self.fields["floor"].queryset = Floor.objects.none()

        if "house" in self.data:
            try:
                house_id = int(self.data.get("house"))
                self.fields["section"].queryset = Section.objects.filter(
                    house_id=house_id
                )
                self.fields["floor"].queryset = Floor.objects.filter(house_id=house_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.house:
            self.fields["section"].queryset = Section.objects.filter(
                house=self.instance.house
            )
            self.fields["floor"].queryset = Floor.objects.filter(
                house=self.instance.house
            )

    def save(self, *, commit: bool = True) -> Apartment:
        """Save Apartment and create or link PersonalAccount if provided."""
        apartment = super().save(commit=False)
        account_uid = self.cleaned_data.get("account_uid")
        if account_uid:
            account, _ = PersonalAccount.objects.get_or_create(
                account_number=account_uid
            )
            apartment.account = account
        if commit:
            apartment.save()
        return apartment


class HouseForm(forms.ModelForm):
    """Form for creating and updating House instances."""

    class Meta:
        """Meta options for HouseForm."""

        model = House
        fields = ["title", "address", "image1", "image2", "image3", "image4", "image5"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "image1": forms.FileInput(attrs={"class": "form-control-file"}),
            "image2": forms.FileInput(attrs={"class": "form-control-file"}),
            "image3": forms.FileInput(attrs={"class": "form-control-file"}),
            "image4": forms.FileInput(attrs={"class": "form-control-file"}),
            "image5": forms.FileInput(attrs={"class": "form-control-file"}),
        }
        labels = {
            "title": "Title",
            "address": "Address",
            "image1": "Image #1 (522x350)",
            "image2": "Image #2 (248x160)",
            "image3": "Image #3 (248x160)",
            "image4": "Image #4 (248x160)",
            "image5": "Image #5 (248x160)",
        }


class SectionForm(forms.ModelForm):
    """Form for creating and updating Section instances."""

    class Meta:
        """Meta options for SectionForm."""

        model = Section
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Name"}
            )
        }
        labels = {"name": "Name"}


class FloorForm(forms.ModelForm):
    """Form for creating and updating Floor instances."""

    class Meta:
        """Meta options for FloorForm."""

        model = Floor
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Name"}
            )
        }
        labels = {"name": "Name"}


class StaffForm(forms.ModelForm):
    """Form for creating and updating Staff instances."""

    user_role = forms.CharField(
        label="Role",
        required=False,
        disabled=True,
        widget=forms.TextInput(
            attrs={"class": "form-control useradmin-role", "readonly": "readonly"}
        ),
    )

    class Meta:
        """Meta options for StaffForm."""

        model = Staff
        fields = ["user"]
        widgets = {
            "user": forms.Select(attrs={"class": "form-control useradmin-select"})
        }
        labels = {"user": "Full Name"}

    def __init__(self, *args, user_roles=None, **kwargs):
        """Initialize StaffForm with filtered users and prefill roles."""
        super().__init__(*args, **kwargs)

        self.fields["user"].queryset = User.objects.filter(
            is_staff=True, is_superuser=False
        ).select_related("role")

        self.fields["user"].label_from_instance = (
            lambda obj: f"{obj.get_full_name()} "
            f"({obj.role.name if obj.role else 'No role'})"
        )

        if getattr(self.instance, "user_id", None):
            role_name = getattr(self.instance.user.role, "name", "")
            self.fields["user_role"].initial = role_name

        if user_roles and getattr(self.instance, "user_id", None):
            role = user_roles.get(self.instance.user_id)
            if role:
                self.fields["user_role"].initial = role

    def clean(self):
        """Add user's role to cleaned_data."""
        cleaned_data = super().clean()
        user = cleaned_data.get("user")
        if user:
            cleaned_data["user_role"] = getattr(user.role, "name", "")
        return cleaned_data


# --- Inline formsets ---
SectionFormSet = inlineformset_factory(
    House, Section, form=SectionForm, extra=1, can_delete=True
)
FloorFormSet = inlineformset_factory(
    House, Floor, form=FloorForm, extra=1, can_delete=True
)
StaffFormSet = inlineformset_factory(
    House, Staff, form=StaffForm, extra=1, can_delete=True
)
