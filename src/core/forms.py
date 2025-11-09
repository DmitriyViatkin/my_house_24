"""Forms for the core application."""

from django import forms
from django.forms import inlineformset_factory
from django.forms import modelformset_factory
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from src.building.models import Apartment
from src.building.models import Floor
from src.building.models import House
from src.building.models import Section
from src.core.generator import generate_id_with_random_number
from src.services.models import Counter
from src.services.models import PaymentDetail
from src.services.models import Service
from src.services.models import Tariff
from src.services.models import TariffService
from src.services.models import Unit
from src.users.models import STATUS_TYPE_CHOICES
from src.users.models import Role
from src.users.models import User


class UserSendMessage(forms.Form):
    """Create a form to send a message to a user with a  recipient."""

    title = forms.CharField(
        label="Заголовок",
        widget=forms.TextInput(attrs={"class": "form-control"}),
        # Можно добавить класс для стилей
    )

    description = forms.CharField(
        label="Описание",
        widget=forms.Textarea(attrs={"class": "wysihtml5 form-control", "rows": 7}),
    )

    full_name = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        empty_label="Все",
        widget=forms.Select(attrs={"class": "form-control select2"}),
        label="Пользователь",
    )


STATUS_CHOICES = [
    ("", "Все"),
    ("work", "Активный"),
    ("done", "Отключен"),
    ("new", "Новый"),
]


class PersonalAccountFilterForm(forms.Form):
    """Create a form to filter personal accounts by   user, and balance."""

    account_number = forms.CharField(label="№", required=False)

    status = forms.ChoiceField(
        choices=STATUS_CHOICES, required=False, widget=forms.Select(), label="Статус"
    )

    apartment_number = forms.ModelChoiceField(
        queryset=Apartment.objects.all(),
        required=False,
        empty_label="Все",
        widget=forms.Select(),
        label="Квартира",
    )

    house_title = forms.ModelChoiceField(
        queryset=House.objects.all(),
        required=False,
        empty_label="Все",
        widget=forms.Select(),
        label="Дом",
    )

    house_section = forms.ModelChoiceField(
        queryset=Section.objects.none(),
        required=False,
        empty_label="Все",
        widget=forms.Select(),
        label="Секция",
    )

    full_name = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        empty_label="Все",
        widget=forms.Select(),
        label="Пользователь",
    )

    cashbox_sum = forms.DecimalField(
        label="Баланс", required=False, max_digits=12, decimal_places=2
    )

    def __init__(self, *args, **kwargs):
        """Initialize the form and populate sections based on the selected house."""
        house_id = kwargs.pop("house_id", None)
        super().__init__(*args, **kwargs)

        if house_id:
            self.fields["house_section"].queryset = Section.objects.filter(
                house_id=house_id
            )
        else:
            self.fields["house_section"].queryset = Section.objects.none()


class CounterFilterForm(forms.Form):
    """Create a form to filter counter readings   unit, and month."""

    counter_number = forms.CharField(
        label="№",
        required=False,
        widget=forms.TextInput(
            attrs={"placeholder": "№ лічильника", "class": "form-control"}
        ),
    )

    status = forms.ChoiceField(
        label="Статус",
        required=False,
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    date = forms.DateField(
        label="Дата",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )

    house = forms.ChoiceField(
        label="Дом",
        required=False,
        choices=[],
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    section = forms.ChoiceField(
        label="Секция",
        required=False,
        choices=[],
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    apartment_number = forms.CharField(
        label="№ квартиры",
        required=False,
        widget=forms.TextInput(
            attrs={"placeholder": "№ квартиры", "class": "form-control"}
        ),
    )

    service = forms.ChoiceField(
        label="Счётчик",
        required=False,
        choices=[],
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    meter_reading = forms.CharField(
        label="Показания",
        required=False,
        widget=forms.TextInput(
            attrs={"placeholder": "Показания", "class": "form-control"}
        ),
    )

    service_unit = forms.CharField(
        label="Единица измерения",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    month = forms.CharField(
        label="Месяц",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Месяц", "class": "form-control"}),
    )

    def __init__(self, *args, **kwargs):
        """Initialize the form and populate service, house, and   dynamically."""
        super().__init__(*args, **kwargs)

        services = Service.objects.all()
        self.fields["service"].choices = [("", "Все услуги")] + [
            (str(s.id), s.name) for s in services
        ]

        houses = House.objects.all()
        self.fields["house"].choices = [("", "Все дома")] + [
            (str(h.id), h.title) for h in houses
        ]

        self.fields["section"].choices = [("", "Все секции")]


class MeterReadingForm(forms.Form):
    """Create a form to display and edit meter   eading, unit, and actions."""

    house = forms.ChoiceField(
        label="Дом",
        required=False,
        choices=[],
    )

    section = forms.ChoiceField(
        label="Секция",
        required=False,
        choices=[],
        widget=forms.Select(
            attrs={"class": "form-control select2", "id": "id_section"}
        ),
    )

    apartment_number = forms.CharField(
        label="№ квартиры",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    service = forms.ChoiceField(
        label="Счетчик",
        required=False,
        choices=[],
    )

    meter_reading = forms.DecimalField(
        label="Показания",
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    service_unit = forms.CharField(
        label="Единица измерения",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    actions = forms.CharField(
        label="Действия",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, **kwargs):
        """Initialize the form and populate service and house choices dynamically."""
        super().__init__(*args, **kwargs)

        services = Service.objects.all()
        self.fields["service"].choices = [("", "Все услуги")] + [
            (str(s.id), s.name) for s in services
        ]
        houses = House.objects.all()
        house_choices = [("", "Все дома")] + [(str(h.id), h.title) for h in houses]
        self.fields["house"].choices = house_choices
        self.fields["section"].choices = [("", "Все секции")]


class CounterForm(forms.ModelForm):
    """Create a form to add or edit a Counter instance , and apartment selection."""

    house = forms.ModelChoiceField(
        queryset=House.objects.all(),
        widget=forms.Select(attrs={"class": "form-control select2"}),
        label="Дом",
    )
    section = forms.ModelChoiceField(
        queryset=Section.objects.none(),
        widget=forms.Select(attrs={"class": "form-control select2"}),
        label="Секция",
    )
    apartment = forms.ModelChoiceField(
        queryset=Apartment.objects.none(),
        widget=forms.Select(attrs={"class": "form-control select2"}),
        label="Квартира",
    )

    class Meta:
        """Meta class for CounterForm, defining model and fields."""

        model = Counter
        fields = [
            "counter_number",
            "meter_reading",
            "service",
            "house",
            "section",
            "apartment",
            "status",
            "date",
        ]
        labels = {
            "counter_number": "Номер счётчика",
            "meter_reading": "Показания",
            "service": "Услуга",
            "house": "Дом",
            "section": "Секция",
            "apartment": "Квартира",
            "status": "Статус",
            "date": "Дата",
        }
        widgets = {
            "counter_number": forms.TextInput(attrs={"class": "form-control"}),
            "meter_reading": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.1"}
            ),
            "service": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Если редактирование существующего объекта
        if self.instance and self.instance.pk:
            house = self.instance.apartment.section.house
            section = self.instance.apartment.section
            self.fields["house"].initial = house.id
            self.fields["section"].queryset = Section.objects.filter(house=house)
            self.fields["section"].initial = section.id
            self.fields["apartment"].queryset = Apartment.objects.filter(
                section=section)
            self.fields["apartment"].initial = self.instance.apartment.id

        else:
            data = kwargs.get("data")
            house_id = None
            section_id = None

            if data:
                # POST
                house_id = data.get("house")
                section_id = data.get("section")

            elif self.request:
                # GET
                house_id = self.request.GET.get("house")
                section_id = self.request.GET.get("section")
                apartment_id = self.request.GET.get("apartment")

                if house_id and house_id.isdigit():
                    self.fields["house"].initial = int(house_id)
                if section_id and section_id.isdigit():
                    self.fields["section"].initial = int(section_id)
                if apartment_id and apartment_id.isdigit():
                    self.fields["apartment"].initial = int(apartment_id)

            # Устанавливаем queryset для секций
            if house_id and str(house_id).isdigit():
                self.fields["section"].queryset = Section.objects.filter(
                    house_id=int(house_id))
            else:
                self.fields["section"].queryset = Section.objects.none()

            # Устанавливаем queryset для квартир
            if section_id and str(section_id).isdigit():
                self.fields["apartment"].queryset = Apartment.objects.filter(
                    section_id=int(section_id))
            else:
                self.fields["apartment"].queryset = Apartment.objects.none()

            # Для GET и POST: генерация начальных значений
            self.initial.setdefault("counter_number", generate_id_with_random_number())
            self.initial.setdefault("date", now())


class FilterApartment(forms.Form):
    """Create a form to filter apartments by number,  owner, and balance."""

    apartment_number = forms.CharField(
        max_length=255, label="№ квартиры", required=False
    )
    house = forms.ChoiceField(label="Дом", required=False, choices=[])
    section = forms.ChoiceField(label="Секция", required=False, choices=[])
    floor = forms.ChoiceField(label="Этаж", required=False, choices=[])
    user = forms.ChoiceField(label="Владелец", required=False, choices=[])
    balance = forms.ChoiceField(label="Баланс", required=False, choices=[])

    def __init__(self, *args, **kwargs):
        """Initialize the form and populate house,  and balance choices."""
        super().__init__(*args, **kwargs)

        houses = House.objects.all()
        self.fields["house"].choices = [("", "Все дома")] + [
            (str(h.id), h.title) for h in houses
        ]

        sections = Section.objects.all()
        self.fields["section"].choices = [("", "Все секции")] + [
            (str(s.id), s.name) for s in sections
        ]

        floors = Floor.objects.all()
        self.fields["floor"].choices = [("", "Все этажи")] + [
            (str(f.id), f.name) for f in floors
        ]

        users = User.objects.all()
        self.fields["user"].choices = [("", "Все владельцы")] + [
            (str(u.id), u.full_name or u.email) for u in users
        ]

        balance_choices = [
            ("", "Все"),
            ("yes", "Нет долга"),
            ("no", "Есть долг"),
        ]
        self.fields["balance"].choices = balance_choices


class FilterOwnerForm(forms.Form):
    """Create a form to filter owners by ID, name, date added, and status."""

    user_id = forms.CharField(max_length=255, label="ID", required=False)
    full_name = forms.CharField(max_length=255, label="ФИО", required=False)
    phone = forms.CharField(max_length=255, label="Телефон", required=False)
    email = forms.CharField(max_length=255, label="Email", required=False)

    house = forms.ChoiceField(
        label="Дом",
        required=False,
        choices=[],
    )

    apartment = forms.CharField(max_length=255, label="Квартира", required=False)
    date_added = forms.CharField(
        max_length=255, label="Дата добавления", required=False
    )
    status = forms.ChoiceField(
        label="Статус",
        required=False,
        choices=[("", "Все")] + STATUS_TYPE_CHOICES,  # noqa: RUF005
    )

    def __init__(self, *args, **kwargs):
        """Initialize the form and populate house choices."""
        super().__init__(*args, **kwargs)
        houses = House.objects.all()
        house_choices = [("", "Все дома")] + [(str(h.id), h.title) for h in houses]
        self.fields["house"].choices = house_choices


class FilterForm(forms.Form):
    """Create a form to filter buildings by title and address."""

    title = forms.CharField(max_length=255, label="Назва будинку", required=False)
    address = forms.CharField(max_length=255, label="Адреса будинку", required=False)


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

class BaseUnitFormSet(forms.BaseModelFormSet):
    """Custom validation to prevent deleting Units used in Services."""

    def clean(self):
        """Prevent deletion of Units that are used in Services."""
        if any(self.errors):
            return

        for form in self.forms:
            # Проверяем только формы, отмеченные на удаление
            if self.can_delete and self._should_delete_form(form):
                unit = form.instance
                # Если единица используется — выдаём ошибку
                if unit.service_set.exists():
                    raise ValidationError(
                        f"Невозможно удалить единицу '{unit.name}', "
                        "так как она используется в услугах."
                    )

UnitFormSet = modelformset_factory(
    Unit,
    form=UnitForm,
    formset=BaseUnitFormSet,
    can_delete=True,
    extra=0,
)

class ServiceForm1(forms.ModelForm):
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
        """Initialize the form and optionally set a custom queryset  field."""
        super().__init__(*args, **kwargs)
        if unit_queryset is not None:
            self.fields["unit"].queryset = unit_queryset
        else:
            self.fields["unit"].queryset = Unit.objects.order_by("id")


ServiceFormSet1 = modelformset_factory(
    Service, form=ServiceForm1, can_delete=True, extra=1
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
            "has_house",
            "has_invoice",
            "has_apartment",
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
