"""Forms for the core application."""

from django import forms

from .models import PaymentArticles


class PaymentArticlesForm(forms.ModelForm):
    """Form for creating or editing PaymentArticles entries."""

    class Meta:
        """Meta information for PaymentArticlesForm."""

        model = PaymentArticles
        fields = ["name", "record_type"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            # если record_type — ChoiceField в модели (in/out, income/expense)
            "record_type": forms.Select(attrs={"class": "form-control"}),
        }
        labels = {
            "name": "Название",
            "record_type": "Приход/расход",
        }
