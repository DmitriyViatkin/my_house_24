"""Forms for authentication and management within the cabinet (personal account)."""

from dal import autocomplete
from django import forms
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator

from src.building.models import Apartment
from src.building.models import Floor
from src.building.models import House
from src.building.models import Section
from src.core.generator import generate_id_with_random_number

from .models import Message
from .models import Role
from .models import Ticket

phone_regex = RegexValidator(
    regex=r"^\+?1?\d{9,15}$",
    message="Phone number must be in the format: '+999999999'. Up to 15 digits.",
)

User = get_user_model()
STATUS_TYPE_CHOICES_TICKET = [
    ("new", "Новый"),
    ("work", "В работе"),
    ("done", "Выполнено"),
]


class SendInvitationForm(forms.Form):
    """Form for collecting contact data (email or phone) to send an invitation.

    At least one of the fields (email or phone) must be provided.
    """

    email = forms.EmailField(
        label="Email",
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter email"}
        ),
    )

    phone = forms.CharField(
        label="Phone",
        max_length=17,
        required=False,
        validators=[phone_regex],
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter phone"}
        ),
    )

    def clean(self):
        """Ensure that at least one contact method (email or phone) is provided."""
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        phone = cleaned_data.get("phone")

        if not email and not phone:
            error_message = (
                "You must provide either Email or Phone to send an invitation."
            )
            raise forms.ValidationError(error_message)


class SendMessage(forms.ModelForm):
    """Form for sending messages within the building system.

    Allows filtering by house, section, floor, and apartment.
    Can optionally send messages only to debtors.
    """

    house = forms.ModelChoiceField(
        queryset=House.objects.all(),
        label="House",
        required=False,
        widget=autocomplete.ModelSelect2(
            url="admin:house-autocomplete", attrs={"class": "form-control"}
        ),
    )
    section = forms.ModelChoiceField(
        queryset=Section.objects.all(),
        label="Section",
        required=False,
        widget=autocomplete.ModelSelect2(
            url="admin:section-autocomplete",
            attrs={"class": "form-control"},
            forward=["house"],
        ),
    )
    floor = forms.ModelChoiceField(
        queryset=Floor.objects.all(),
        label="Floor",
        required=False,
        widget=autocomplete.ModelSelect2(
            url="admin:floor-autocomplete",
            attrs={"class": "form-control"},
            forward=["section"],
        ),
    )
    flat = forms.ModelChoiceField(
        queryset=Apartment.objects.all(),
        label="Apartment",
        required=False,
        widget=autocomplete.ModelSelect2(
            url="admin:flat-autocomplete",
            attrs={"class": "form-control"},
            forward=["section"],
        ),
    )

    only_debtors = forms.BooleanField(
        required=False,
        label="Send only to debtors",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        """Meta configuration for SendMessage form."""

        model = Message
        fields = ["title", "text"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "text": forms.Textarea(
                attrs={"class": "wysihtml5 form-control", "rows": 7}
            ),
        }


class TicketAdminForm(forms.ModelForm):
    """Admin form for managing tickets with role, apartment, and worker fields.

    Filters apartments and available workers based on the selected apartment and role.
    """

    class Meta:
        """Meta configuration for TicketAdminForm."""

        model = Ticket
        fields = [
            "role",
            "user",
            "apartment",
            "summary",
            "comment",
            "date",
            "time",
            "worker",
            "status",
        ]
        labels = {
            "role": "Роль мастера",
            "apartment": "Квартира",
            "status": "",
            "summary": "Описание",
            "comment": "Комментарий",
            "date": "Дата",
            "time": "Время",
            "worker": "Мастер",
        }
        widgets = {
            "status": forms.Select(attrs={"class": "form-control"}),
            "user": forms.Select(attrs={"class": "form-control"}),
            "role": forms.Select(attrs={"class": "form-control"}),
            "apartment": forms.Select(attrs={"class": "form-control"}),
            "summary": forms.Textarea(attrs={"rows": 6, "class": "form-control"}),
            "comment": forms.Textarea(attrs={"rows": 6, "class": "form-control"}),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "worker": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        """Initialize the form and filter apartments and workers based on user and role.

        Args:
            *args: Positional arguments passed to the parent form.
            **kwargs: Keyword arguments passed to the parent form.

        """
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        self.fields["role"].queryset = Role.objects.filter(is_worker_role=True)

        # Filter apartments
        if self.is_bound:
            apartment_id = self.data.get("apartment") or getattr(
                self.instance, "apartment_id", None
            )
            if apartment_id:
                try:
                    Apartment.objects.get(pk=apartment_id)
                    self.fields["apartment"].queryset = Apartment.objects.filter(
                        pk=apartment_id
                    )
                except Apartment.DoesNotExist:
                    self.fields["apartment"].queryset = Apartment.objects.none()
            else:
                self.fields["apartment"].queryset = Apartment.objects.none()
        elif user:
            user_apartments = user.apartments.select_related("house").all()
            self.fields["apartment"].queryset = user_apartments
            if user_apartments.exists():
                self.fields["apartment"].initial = user_apartments.first()
        else:
            self.fields["apartment"].queryset = Apartment.objects.none()

        # Filter workers
        apartment_id = (
            self.data.get("apartment")
            if self.is_bound
            else getattr(self.instance, "apartment_id", None)
        )
        role_id = (
            self.data.get("role")
            if self.is_bound
            else getattr(self.instance, "role_id", None)
        )

        if apartment_id:
            try:
                house = Apartment.objects.get(pk=apartment_id).house
                staff_users = User.objects.filter(
                    staff_houses__house=house, role__is_worker_role=True
                )
                if role_id:
                    staff_users = staff_users.filter(role_id=role_id)
                self.fields["worker"].queryset = staff_users.distinct()
            except Apartment.DoesNotExist:
                self.fields["worker"].queryset = User.objects.none()
        else:
            self.fields["worker"].queryset = User.objects.none()

    def save(self, *, commit=True, user=None):
        """Save the TicketAdminForm instance.

        Args:
            commit (bool): Whether to save to the database immediately.
            user (User, optional): Assign this user as the ticket creator.

        Returns:
            Ticket: The saved ticket instance.

        """
        instance = super().save(commit=False)
        if user is not None:
            instance.user = user
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class TicketFilterForm(forms.Form):
    """Form for filtering tickets based on multiple criteria."""

    time = forms.TimeField(
        label="Время", required=False, widget=forms.TimeInput(attrs={"type": "time"})
    )
    role = forms.ModelChoiceField(
        label="Тип мастера",
        queryset=Role.objects.filter(is_worker_role=False),
        required=False,
        empty_label="Все",
    )
    worker = forms.ModelChoiceField(
        label="Мастер",
        queryset=User.objects.filter(role__is_worker_role=False),
        required=False,
        empty_label="Все",
    )
    status = forms.ChoiceField(
        label="Статус",
        choices=[("", "Все"), *STATUS_TYPE_CHOICES_TICKET],
        required=False,
    )
    owner = forms.ModelChoiceField(
        label="Владелец",
        queryset=User.objects.filter(role__has_owner=True),
        required=False,
        empty_label="Все",
    )
    comment = forms.CharField(
        label="Описание",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Поиск по описанию"}),
    )
    user_apartments = forms.CharField(
        label="Квартира / Дом",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "№ квартиры или название дома"}),
    )
    phone = forms.CharField(
        label="Телефон",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Номер телефона"}),
    )


class TicketUserForm(forms.ModelForm):
    """Form for users to create tickets (non-admin)."""

    class Meta:
        """Meta configuration for TicketUserForm."""

        model = Ticket
        fields = ["role", "apartment", "comment", "date", "time"]
        labels = {
            "role": "Роль мастера",
            "apartment": "Квартира",
            "comment": "Комментарий",
            "date": "Дата",
            "time": "Время",
        }
        widgets = {
            "role": forms.Select(attrs={"class": "form-control"}),
            "apartment": forms.Select(attrs={"class": "form-control"}),
            "comment": forms.Textarea(attrs={"rows": 6, "class": "form-control"}),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        """Initialize TicketUserForm and filter apartments for the current user."""
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        self.fields["role"].queryset = Role.objects.filter(is_worker_role=True)
        if user:
            user_apartments = user.apartments.select_related("house").all()
            self.fields["apartment"].queryset = user_apartments
            if user_apartments.exists():
                self.fields["apartment"].initial = user_apartments.first()
        else:
            self.fields["apartment"].queryset = Apartment.objects.none()

    def save(self, *, commit=True, user=None):
        """Save ticket instance and auto-fill related fields (worker and house)."""
        ticket = super().save(commit=False)
        if user:
            ticket.user = user
            ticket.phone = user.phone
        ticket.status = "new"

        if ticket.apartment and ticket.role:
            staff = User.objects.filter(
                staff_houses__house=ticket.apartment.house,
                role__is_worker_role=True,
                role=ticket.role,
            ).first()
            if staff:
                ticket.worker = staff

        if ticket.apartment:
            ticket.house = ticket.apartment.house

        if commit:
            ticket.save()
        return ticket


class CreateOwnerFlatForm(forms.ModelForm):
    date_birthday = forms.DateField(
        label="Дата рождения",
        required=False,
        input_formats=["%d.%m.%Y"],
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "placeholder": "дд.мм.гггг",
                "autocomplete": "off",
            },
            format="%d.%m.%Y",
        ),
    )

    # Эти поля не связаны с моделью напрямую!
    password = forms.CharField(
        label="Пароль",
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control pass-value"}),
        help_text="Оставьте пустым, чтобы не менять пароль",
    )
    password2 = forms.CharField(
        label="Повторите пароль",
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        help_text="Повторите новый пароль",
    )

    class Meta:
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
            "status",
            "description",
        ]
        widgets = {
            "image": forms.FileInput(attrs={"class": "form-control-file"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            # Новый пользователь
            self.initial["user_id"] = generate_id_with_random_number()
        else:
            # Редактирование существующего — обнуляем поля пароля
            self.fields["password"].initial = ""
            self.fields["password2"].initial = ""

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password2 = cleaned_data.get("password2")

        if password or password2:
            if password != password2:
                self.add_error("password2", "Пароли не совпадают.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class CreateOwnerFlatForm1(forms.ModelForm):
    date_birthday = forms.DateField(
        label="Дата рождения",
        required=False,
        input_formats=["%d.%m.%Y"],
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "placeholder": "дд.мм.гггг",
                "autocomplete": "off",
            },
            format="%d.%m.%Y",
        ),
    )

    password = forms.CharField(
        label="Пароль",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control pass-value",
                "autocomplete": "new-password",
            }
        ),
        help_text="Оставьте пустым, чтобы не менять пароль",
    )

    password2 = forms.CharField(
        label="Повторите пароль",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "autocomplete": "new-password",
            }
        ),
        help_text="Повторите новый пароль",
    )

    class Meta:
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
            "description",
        ]
        widgets = {
            "image": forms.FileInput(attrs={"class": "form-control-file"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            # Новый пользователь
            self.initial["user_id"] = generate_id_with_random_number()

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password2 = cleaned_data.get("password2")

        if password or password2:
            if password != password2:
                self.add_error("password2", "Пароли не совпадают.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class StaffForms(forms.ModelForm):
    """Form for creating and updating staff users."""

    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(
            attrs={"class": "form-control pass-value", "maxlength": "255"}
        ),
        required=False,
    )
    password2 = forms.CharField(
        label="Повторить пароль",
        widget=forms.PasswordInput(
            attrs={"class": "form-control pass-value", "maxlength": "255"}
        ),
        required=False,
    )

    class Meta:
        """Meta configuration for StaffForms."""

        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "role",
            "status",
            "is_staff",
            "is_active",
        ]
        labels = {
            "first_name": "Имя",
            "last_name": "Фамилия",
            "email": "Email (логин)",
            "phone": "Телефон",
            "role": "Роль",
            "status": "Статус",
            "is_staff": "Admin Access",
            "is_active": "Active",
        }

    def __init__(self, *args, **kwargs):
        """Initialize form and make passwords optional for existing users."""
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["password"].required = False
            self.fields["password2"].required = False

    def clean(self):
        """Validate passwords if provided and ensure they match."""
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password2 = cleaned_data.get("password2")
        if password or password2:
            if password != password2:
                self.add_error("password2", "Пароли не совпадают")
        return cleaned_data

    def save(self, *, commit=True):
        """Save staff user and set password if provided."""
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        user.is_staff = True
        if commit:
            user.save()
        return user
