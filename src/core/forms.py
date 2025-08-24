"""Forms for the core application."""

from django import forms
from django.forms import inlineformset_factory
from django.forms import modelformset_factory

from src.services.models import PaymentDetail
from src.services.models import Service
from src.services.models import Tariff
from src.services.models import TariffService
from src.services.models import Unit
from src.users.models import Role


class PaymentDetailsForm(forms.ModelForm):
    """Form for creating or updating PaymentDetail instances."""

    class Meta:
        """Meta options for PaymentDetailsForm."""

        model = PaymentDetail
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }
        labels = {
            "name": "Название компании",
            "description": "Информация",
        }


class TariffForm(forms.ModelForm):
    """Form for creating or updating Tariff instances."""

    class Meta:
        """Meta options for TariffForm."""

        model = Tariff
        fields = ["title", "description"]

    def __init__(self, *args, **kwargs):
        """Initialize the TariffForm and add Bootstrap classes."""
        super().__init__(*args, **kwargs)
        if "title" in self.fields:
            self.fields["title"].label = "Название тарифа"
            self.fields["title"].widget.attrs.update({"class": "form-control"})
        if "description" in self.fields:
            self.fields["description"].widget.attrs.update({"class": "form-control"})


class TariffServiceForm(forms.ModelForm):
    """Form for creating or updating TariffService instances."""

    class Meta:
        """Meta options for TariffServiceForm."""

        model = TariffService
        fields = ["tariff", "service", "price", "currency", "unit"]

    def __init__(self, *args, **kwargs):
        """Initialize the TariffServiceForm and add Bootstrap classes."""
        super().__init__(*args, **kwargs)
        self.fields["currency"].disabled = True
        if "tariff" in self.fields:
            self.fields["tariff"].widget = forms.HiddenInput()
        self.fields["service"].widget.attrs.update(
            {"class": "form-control service-select"}
        )
        self.fields["price"].widget.attrs.update({"class": "form-control"})
        self.fields["currency"].widget.attrs.update({"class": "form-control"})
        self.fields["unit"].widget.attrs.update(
            {"class": "form-control serviceunit-name"}
        )


# Inline formset for TariffService
TariffServiceFormSet = inlineformset_factory(
    Tariff, TariffService, form=TariffServiceForm, extra=1, can_delete=True
)


class UnitForm(forms.ModelForm):
    """Form for creating or updating Unit instances."""

    class Meta:
        """Meta options for UnitForm."""

        model = Unit
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "id": forms.HiddenInput(),
        }


UnitFormSet = modelformset_factory(Unit, form=UnitForm, can_delete=True, extra=0)


class ServiceForm(forms.ModelForm):
    """Form for creating or updating Service instances."""

    class Meta:
        """Meta options for ServiceForm."""

        model = Service
        fields = ["name", "unit", "id", "is_show"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "unit": forms.Select(attrs={"class": "form-control"}),
            "id": forms.HiddenInput(),
            "is_show": forms.CheckboxInput(),
        }

    def __init__(self, *args, unit_queryset=None, **kwargs):
        """Initialize the ServiceForm and set a custom queryset for the 'unit' field.

        Args:
            *args: Variable length argument list passed to the parent form.
            unit_queryset (QuerySet, optional): Custom queryset for the 'unit' field.
            **kwargs: Arbitrary keyword arguments passed to the parent form.

        """
        super().__init__(*args, **kwargs)
        if unit_queryset is not None:
            self.fields["unit"].queryset = unit_queryset
        else:
            self.fields["unit"].queryset = Unit.objects.order_by("id")


ServiceFormSet = modelformset_factory(
    Service, form=ServiceForm, can_delete=True, extra=1
)


class RoleForm(forms.ModelForm):
    """Form for managing Role model instances."""

    class Meta:
        """Meta options for RoleForm."""

        model = Role
        fields = [
            "name",
            "has_statistic",
            "has_cashbox",
            "has_invoice",
            "has_personal_account",
            "has_user",
            "has_owner",
            "has_message",
            "has_applications",
            "has_managment",
            "has_service",
            "has_role",
            "has_tariff",
            "has_payment_details",
            "has_counter",
        ]
