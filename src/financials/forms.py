"""Forms for the core application."""

import decimal

from dal import autocomplete
from django import forms
from django.forms import inlineformset_factory
from django.forms import modelformset_factory
from django.utils import timezone

from src.building.models import Apartment
from src.building.models import House
from src.building.models import Section
from src.core.generator import generate_id_with_random_number
from src.services.models import Tariff
from src.services.models import TariffService
from src.users.models import User

from .models import CashBox
from .models import Invoice
from .models import InvoiceItem
from .models import PaymentArticles
from .models import PersonalAccount
from .models import Template


class TemplateForm(forms.ModelForm):
    """Form for creating or editing a Template instance.

    This form is based on the Template model and includes
    all fields defined in the Meta class. It can be used
    in views or admin for template management.
    """

    class Meta:
        """Metadata for the TemplateForm: specifies the model and included fields."""

        model = Template
        fields = ["name", "file", "is_default"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Введите название шаблона",
                }
            ),
            "file": forms.FileInput(attrs={"class": "form-control-file"}),
            "is_default": forms.RadioSelect(
                choices=[(True, "Да"), (False, "Нет")],
                attrs={"class": "form-check-input"},
            ),
        }
        labels = {
            "name": "Название шаблона",
            "file": "Файл шаблона",
            "is_default": "Использовать по умолчанию",
        }

    def __init__(self, *args, **kwargs):
        """Initialize the form instance.

        Sets up initial values or custom queryset filters
        based on the provided instance or other parameters.
        """
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["file"].required = False


TemplateFormSet = modelformset_factory(
    Template, form=TemplateForm, can_delete=True, extra=1
)

STATUS_CHOICES = [
    ("draft", "Черновик"),
    ("counted", "Рассчитан"),
    ("zero", "Обнулен"),
]


class InvoiceFilterForm(forms.Form):
    """Form for filtering invoices based on various criteria.

    Fields:
        - invoice_number: filter by invoice number
        - date: filter by specific date
        - mount: filter by month
        - status: filter by invoice status
        - tariff: filter by tariff
        - apartment: filter by apartment
        - total: filter by total amount
        - owner: filter by owner's full name
    """

    invoice_number = forms.CharField(
        label="Номер счёта",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    date = forms.DateField(
        label="Дата",
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    mount = forms.DateField(
        label="Месяц",
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "month"}),
    )

    status_choices = [("", "---------"), *STATUS_CHOICES]

    status = forms.ChoiceField(
        choices=status_choices,
        label="Статус",
        required=False,
        widget=forms.Select(attrs={"class": "form-control select2"}),
    )

    tariff = forms.ModelChoiceField(
        queryset=Tariff.objects.all(),
        label="Тариф",
        required=False,
        widget=forms.Select(attrs={"class": "form-control select2"}),
    )

    apartment = forms.ModelChoiceField(
        queryset=Apartment.objects.all(),
        label="Квартира",
        required=False,
        widget=forms.Select(attrs={"class": "form-control select2"}),
    )

    total = forms.DecimalField(
        label="Сумма",
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    owner = forms.CharField(
        label="ФИО владельца",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )


class InvoiceItemWithTariffForm(forms.ModelForm):
    """Form for creating or editing an InvoiceItem with selectable tariff services."""

    tariff_service = forms.ModelChoiceField(
        queryset=TariffService.objects.select_related("service", "unit"),
        label="Тарифная услуга",
        required=True,
    )
    total = forms.DecimalField(
        label="Стоимость",
        max_digits=10,
        decimal_places=2,
        required=False,
        localize=False,
    )

    unit = forms.CharField(label="Единица", required=False, disabled=True)
    price = forms.DecimalField(
        label="Цена", max_digits=10, decimal_places=2, required=False
    )
    currency = forms.CharField(label="Валюта", max_length=10, required=False)

    class Meta:
        """Metadata for the InvoiceItem form: specifies the model ."""

        model = InvoiceItem
        fields = [
            "tariff_service",
            "unit",
            "price",
            "currency",
            "count",
            "total",
        ]

    def __init__(self, *args, **kwargs):
        """Initialize the form and set custom queryset or initial values."""
        super().__init__(*args, **kwargs)

        # ✅ правильный способ кастомизировать отображение
        self.fields["tariff_service"].label_from_instance = (
            lambda obj: f"{obj.service.name}"
        )
        self.fields["tariff_service"].widget.attrs["class"] = "tariff-service-select"

        # Если редактируем существующую строку
        if self.instance and self.instance.tariff_service_id:
            ts = self.instance.tariff_service
            self.fields["unit"].initial = ts.unit.name
            self.fields["price"].initial = ts.price
            self.fields["currency"].initial = ts.currency

    def clean(self):
        """Validate form data and ensure tariff service and currency are consistent."""
        cleaned_data = super().clean()
        tariff_service = cleaned_data.get("tariff_service")
        count = cleaned_data.get("count") or 0
        price = cleaned_data.get("price") or 0  # Получаем price из формы или 0

        if tariff_service:
            # Обновляем цену, если изменили услугу
            price = tariff_service.price
            cleaned_data["price"] = price
            cleaned_data["currency"] = tariff_service.currency
            cleaned_data["unit"] = tariff_service.unit.name

        calculated_total = (price or 0) * count

        # Преобразуем результат обратно в Decimal с нужной точностью

        cleaned_data["total"] = calculated_total.quantize(decimal.Decimal("0.01"))

        return cleaned_data

    def save(self, *, commit=True):
        """Save the Invoice instance.

        Updates the instance before saving. By default, `commit=True`
        will save the instance to the database. Set `commit=False`
        to get the instance without saving immediately.
        """
        instance = super().save(commit=False)
        cd = self.cleaned_data
        if cd.get("tariff_service"):
            instance.price = cd["price"]
            instance.currency = cd["currency"]
            instance.unit_display = cd[
                "unit"
            ]  # если в модели нет поля unit_display — убери эту строчку
            instance.total = cd["total"]
        if commit:
            instance.save()
        return instance


TarifServiceItem_inlinformset = inlineformset_factory(
    parent_model=Invoice,
    model=InvoiceItem,
    form=InvoiceItemWithTariffForm,
    extra=0,
    can_delete=True,
)


STATUS_TYPE_CHOICES = [
    ("new", "Оплачено"),
    ("zero", "Неоплачено"),
    ("counted", "Частично оплачено"),
]


class InvoiceForm(forms.ModelForm):
    """Form for creating or updating an Invoice instance.

    Provides fields for selecting the house, section, apartment, and
    other invoice-related data. Can be used in admin or custom views.
    """

    house = forms.ModelChoiceField(
        queryset=House.objects.all(),
        label="Дом",
        widget=autocomplete.ModelSelect2(
            url="admin:house-autocomplete", attrs={"class": "form-control"}
        ),
    )
    section = forms.ModelChoiceField(
        queryset=Section.objects.all(),
        label="Секция",
        widget=autocomplete.ModelSelect2(
            url="admin:section-autocomplete",
            attrs={"class": "form-control"},
            forward=["house"],
        ),
    )
    flat = forms.ModelChoiceField(
        queryset=Apartment.objects.all(),
        label="Квартира",
        widget=autocomplete.ModelSelect2(
            url="admin:flat-autocomplete",
            attrs={"class": "form-control"},
            forward=["section"],
        ),
    )
    tariff = forms.ModelChoiceField(
        queryset=Tariff.objects.all(),
        label="Тариф",
        widget=autocomplete.ModelSelect2(
            url="admin:tariff-autocomplete",
            attrs={"class": "form-control"},
            forward=["flat"],
        ),
    )
    personal_account = forms.ModelChoiceField(
        queryset=PersonalAccount.objects.all(),
        label="Личный счет",
        widget=autocomplete.ModelSelect2(
            url="admin:account-autocomplete",
            attrs={"class": "form-control"},
            forward=["flat"],
        ),
    )
    owner = forms.CharField(label="ФИО владельца", required=False, disabled=True)
    phone = forms.CharField(label="Телефон", required=False, disabled=True)

    class Meta:
        """Meta class for InvoiceForm.

        Specifies the model and the fields that should be included in the form.
        """

        model = Invoice
        fields = [
            "conducted",
            "status",
            "invoice_number",
            "start_date",
            "end_date",
            "mount",
            "date",
            "owner",
            "phone",
            "house",
            "section",
            "flat",
            "personal_account",
            "tariff",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "start_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "end_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "mount": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instance = self.instance

        # --- При создании ---
        if not instance.pk:
            self.initial["invoice_number"] = generate_id_with_random_number()
            self.initial["mount"] = timezone.now().date()
        else:
            self.fields["invoice_number"].disabled = True

        # --- Связанная сущность ---
        personal_account = getattr(instance, "personal_account", None)
        apartment = personal_account.apartment if personal_account else None

        # --- Owner & Phone ---
        if apartment and apartment.user:
            self.initial["owner"] = apartment.user.full_name
            self.initial["phone"] = apartment.user.phone

        # --- ✅ ВАЖНО: initial ТОЛЬКО ЧЕРЕЗ self.initial ---
        if apartment:
            self.initial["house"] = apartment.house
            self.initial["section"] = apartment.section
            self.initial["flat"] = apartment

        if personal_account:
            self.initial["personal_account"] = personal_account

        if instance.tariff_id:
            self.initial["tariff"] = instance.tariff

    def save(self, *, commit=True):
        """Save the CashBox instance with optional commit.

        Fills additional fields like owner and phone based on the associated
        personal account before saving. The commit flag determines whether
        the instance is actually saved to the database immediately.

        Args:
            commit (bool): Whether to save the instance to the database immediately.

        Returns:
            CashBox: The saved or unsaved CashBox instance.

        """
        instance = super().save(commit=False)
        # Заполняем owner и phone по персональному аккаунту
        if commit:
            instance.save()
        return instance


PAYMENT_TYPE_CHOICES = (
    ("", "Все"),
    ("in", "Приход"),
    ("out", "Расход"),
)

CONDUCTED_CHOICES = (
    ("", "Все"),
    (True, "Проведен"),
    (False, "Не проведен"),
)


class CashBoxForm(forms.Form):
    """Form for entering and managing CashBox information."""

    cash_box_number = forms.IntegerField(
        label="№", widget=forms.NumberInput(attrs={"class": "form-control"})
    )
    date = forms.DateField(
        label="Дата",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    is_conducted = forms.ChoiceField(
        label="Статус",
        choices=CONDUCTED_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    # Поле для "Статьи платежа"
    payment_article = forms.ModelChoiceField(
        label="Тип платежа",
        queryset=PaymentArticles.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    # Поле для "Тип (приход/расход)"
    record_type = forms.ChoiceField(
        label="Тип (приход/расход)",
        choices=PAYMENT_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    # Поле для "ФИО владельца"
    owner = forms.ModelChoiceField(
        queryset=User.objects.all(),
        label="ФИО владельца",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    # Поле для "Лицевой счёт"
    personal_account_number = forms.CharField(
        label="Лицевой счёт",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    suma = forms.DecimalField(
        label="Сумма",
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    comment = forms.CharField(
        label="Комментарий",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
    )


class ExpenseReportForm(forms.ModelForm):
    """Form for creating or editing an expense report."""

    manager = forms.ModelChoiceField(
        queryset=User.objects.all(),
        label="Менеджер",
        widget=autocomplete.ModelSelect2(url="admin:manager-autocomplete"),
    )

    class Meta:
        """Metadata for the CashBox form: model and fields configuration."""

        model = CashBox
        fields = [
            "manager",
            "cash_box_number",
            "suma",
            "comment",
            "is_conducted",
            "date",
            "payment_articles",
        ]
        widgets = {
            "manager": forms.Select(attrs={"class": "form-control"}),
            "cash_box_number": forms.TextInput(
                attrs={"class": "form-control", "readonly": "readonly"}
            ),
            "suma": forms.NumberInput(attrs={"class": "form-control"}),
            "comment": forms.Textarea(attrs={"class": "form-control"}),
            "is_conducted": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "payment_articles": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        """Initialize the form and filter payment articles for this instance."""
        super().__init__(*args, **kwargs)
        self.fields["payment_articles"].queryset = PaymentArticles.objects.filter(
            record_type="out"
        )
        if not self.instance.pk:
            self.initial["cash_box_number"] = generate_id_with_random_number()


class ReceiptStatementForm(forms.ModelForm):
    """Form for creating or editing a receipt statement."""

    owner = forms.ModelChoiceField(
        queryset=User.objects.all(),
        label="Владелец",
        widget=autocomplete.ModelSelect2(url="admin:user-autocomplete"),
    )

    personal_account = forms.ModelChoiceField(
        queryset=PersonalAccount.objects.all(),
        label="Лицевой счет",
        widget=autocomplete.ModelSelect2(
            url="admin:personal-account-autocomplete", forward=["owner"]
        ),
    )
    manager = forms.ModelChoiceField(
        queryset=User.objects.all(),
        label="Менеджер",
        widget=autocomplete.ModelSelect2(url="admin:manager-autocomplete"),
    )

    class Meta:
        """Meta class specifying model and fields for the CashBox form."""

        model = CashBox
        fields = [
            "owner",
            "manager",
            "cash_box_number",
            "personal_account",
            "suma",
            "comment",
            "is_conducted",
            "date",
            "payment_articles",
        ]
        widgets = {
            "manager": forms.Select(attrs={"class": "form-control"}),
            "cash_box_number": forms.TextInput(
                attrs={"class": "form-control", "readonly": "readonly"}
            ),
            "suma": forms.NumberInput(attrs={"class": "form-control"}),
            "comment": forms.Textarea(attrs={"class": "form-control"}),
            "is_conducted": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "payment_articles": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        """Initialize the form and filter payment_articles queryset dynamically."""
        super().__init__(*args, **kwargs)
        self.fields["payment_articles"].queryset = PaymentArticles.objects.filter(
            record_type="in"
        )

        if not self.instance.pk:  # только при создании
            self.initial["cash_box_number"] = generate_id_with_random_number()


class PersonalAccountForm(forms.ModelForm):
    """Form for creating or updating a PersonalAccount."""

    house = forms.ModelChoiceField(
        label="Дом",
        queryset=House.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    section = forms.ModelChoiceField(
        label="Секция",
        queryset=Section.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    apartment = forms.ModelChoiceField(
        label="Квартира",
        queryset=Apartment.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    owner = forms.CharField(
        label="Хозяин квартиры",
        required=False,
        disabled=True,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    phone = forms.CharField(
        label="Телефон",
        required=False,
        disabled=True,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    class Meta:
        """Metadata for the PersonalAccountForm: specifies model and fields."""

        model = PersonalAccount
        fields = ["house", "section", "apartment", "account_number", "status"]
        widgets = {
            "account_number": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }
        labels = {
            "account_number": "Лицевой счёт",
            "status": "Статус",
        }

    def __init__(self, *args, **kwargs):
        """Initialize the form with custom behavior or widget attributes."""
        super().__init__(*args, **kwargs)

        # Генерация account_number для новых экземпляров
        if not self.instance.pk:
            self.initial["account_number"] = generate_id_with_random_number()

        # Подтягиваем queryset для section и apartment при POST
        if "house" in self.data:
            try:
                house_id = int(self.data.get("house"))
                self.fields["section"].queryset = Section.objects.filter(
                    house_id=house_id
                )
            except (ValueError, TypeError):
                self.fields["section"].queryset = Section.objects.none()
        elif self.instance.pk and getattr(self.instance, "apartment", None):
            apt = self.instance.apartment
            self.fields["section"].queryset = Section.objects.filter(house=apt.house)

        if "section" in self.data:
            try:
                section_id = int(self.data.get("section"))
                self.fields["apartment"].queryset = Apartment.objects.filter(
                    section_id=section_id
                )
            except (ValueError, TypeError):
                self.fields["apartment"].queryset = Apartment.objects.none()
        elif self.instance.pk and getattr(self.instance, "apartment", None):
            apt = self.instance.apartment
            self.fields["apartment"].queryset = Apartment.objects.filter(
                section=apt.section
            )

        # Если у экземпляра есть квартира, заполняем initial
        apt = getattr(self.instance, "apartment", None)
        if apt:
            self.fields["house"].initial = apt.house
            self.fields["section"].initial = apt.section
            self.fields["apartment"].initial = apt

            if getattr(apt, "user", None):
                full_name = apt.user.get_full_name() or apt.user.username
                phone = getattr(apt.user, "phone", "") or getattr(
                    apt.user, "phone_number", ""
                )
                self.fields["owner"].initial = full_name
                self.fields["phone"].initial = phone

    def save(self, *, commit=True):
        """Save the PersonalAccount and link it to the apartment."""
        account = super().save(commit=False)

        apartment = self.cleaned_data.get("apartment")
        if apartment:
            # Link account to the apartment
            apartment.account = account
            # Optionally, set the account user to the apartment owner
            account.user = apartment.user

            if commit:
                account.save()
                apartment.save()
        elif commit:
            account.save()

        return account


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
