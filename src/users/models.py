"""Database models for the user application."""

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class Role(models.Model):
    """The Role model represents the permissions .

    Each user is associated with a single role that defines what sections
     and functionalities
    they can access, such as statistics, cashbox, invoices, etc.
    This model is a core
    component for managing user permissions and access control.
    """

    name = models.CharField(max_length=100, unique=True, verbose_name="Роль")
    is_worker_role = models.BooleanField(
        default=False, verbose_name="Административный персонал"
    )
    has_statistic = models.BooleanField(default=False, verbose_name="Статистика")
    has_cashbox = models.BooleanField(default=False, verbose_name="Касса")
    has_house = models.BooleanField(default=False, verbose_name="Дома")
    has_invoice = models.BooleanField(default=False, verbose_name="Квитанции")
    has_personal_account = models.BooleanField(
        default=False, verbose_name="личный счёт"
    )
    has_apartment = models.BooleanField(default=False, verbose_name="Квартиры")
    has_user = models.BooleanField(default=False, verbose_name="Пользователи")
    has_owner = models.BooleanField(default=False, verbose_name="Владельцы")
    has_message = models.BooleanField(default=False, verbose_name="Сообщения")
    has_applications = models.BooleanField(default=False, verbose_name="")
    has_managment = models.BooleanField(default=False, verbose_name="Управление")
    has_service = models.BooleanField(default=False, verbose_name="Услуги")
    has_role = models.BooleanField(default=False, verbose_name="Роли")
    has_tariff = models.BooleanField(default=False, verbose_name="Тарифы")
    has_payment_details = models.BooleanField(
        default=False, verbose_name="Платежные даные"
    )
    has_counter = models.BooleanField(default=False, verbose_name="Счётчики")

    def __str__(self):
        """Return the name of the role as its string representation."""
        return self.name


STATUS_TYPE_CHOICES = [
    ("new", "Новый"),
    ("work", "Активный"),
    ("done", "Отключен"),
]


class CustomUserManager(BaseUserManager):
    """User manager using email as login instead of username."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with the given email and password."""
        if not email:
            error_msg = "User must have an email address"
            raise ValueError(error_msg)
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with administrative privileges."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if not extra_fields.get("is_staff"):
            error_msg = "Superuser must have is_staff=True."
            raise ValueError(error_msg)
        if not extra_fields.get("is_superuser"):
            error_msg = "Superuser must have is_superuser=True."
            raise ValueError(error_msg)

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model with email as login."""

    second_name = models.CharField(
        max_length=150, blank=True, verbose_name="Middle name"
    )
    username = None
    email = models.EmailField(_("email address"), unique=True)
    date_birthday = models.DateField(blank=True, null=True, verbose_name="Birth date")
    image = models.ImageField(
        upload_to="users/images/", blank=True, null=True, verbose_name="Avatar"
    )
    user_id = models.CharField(
        max_length=50, unique=True, editable=True, verbose_name="ID"
    )
    description = models.TextField(blank=True, verbose_name="Description")
    status = models.CharField(
        max_length=20,
        choices=STATUS_TYPE_CHOICES,
        default="new",
        verbose_name="User status",
    )
    phone = models.CharField(max_length=255, blank=True, verbose_name="Viber")
    viber = models.CharField(max_length=255, blank=True, verbose_name="Viber")
    telegram = models.CharField(max_length=255, blank=True, verbose_name="Telegram")
    role = models.ForeignKey(
        "Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="User role",
    )

    objects = CustomUserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        """Return the full name or email of the user."""
        return self.full_name or self.email

    @property
    def full_name(self):
        """Return the full name of the user (Last, First, Middle)."""
        return f"{self.last_name} {self.first_name} {self.second_name}".strip()


STATUS_TYPE_CHOICES_TICKET = [
    ("new", "Новый"),
    ("work", "В работе"),
    ("done", "Выполнено"),
]


class Ticket(models.Model):
    """Заявка на обслуживание."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Владелец")

    apartment = models.ForeignKey(
        "building.Apartment",
        on_delete=models.CASCADE,
        verbose_name="Квартира",
        null=True,
        blank=True,
    )

    role = models.ForeignKey(
        "Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
        verbose_name="Роль исполнителя",
    )
    worker = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets_as_worker",
        verbose_name="Назначенный мастер",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_TYPE_CHOICES_TICKET,
        default="new",
        verbose_name="Статус заявки",
    )
    summary = models.CharField(max_length=255, verbose_name="Короткое описание")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    date = models.DateField(blank=True, null=True, verbose_name="Дата заявки")
    time = models.TimeField(blank=True, null=True, verbose_name="Время заявки")
    comment = models.TextField(verbose_name="Комментарий")

    def __str__(self):
        """Return the full name or email of the user."""
        if self.apartment and self.apartment.house:
            house_title = self.apartment.house.title
        else:
            house_title = "Без дома"
        return f"Заявка {self.summary} ({house_title})"

    @property
    def user_full_name(self):
        """Return the full name of the user associated with the ticket."""
        return self.user.full_name if self.user else ""

    def user_apartments(self):
        """Return a comma-separated list of user's apartments."""
        if self.user:
            return ", ".join(
                str(a.apartment_number) for a in self.user.apartments.all()
            )
        return ""


class Message(models.Model):
    """Model representing messages sent between users."""

    title = models.CharField(max_length=255, verbose_name="Заголовок")
    text = models.TextField(verbose_name="Текст сообщения")
    recipients = models.ManyToManyField(User, verbose_name="Получатели")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        # Что делать при удалении отправителя (установить NULL)
        null=True,  # Разрешить значение NULL в базе данных
        related_name="sent_messages",
        # Имя для обратной связи (user.sent_messages.all())
        verbose_name="Отправитель",
    )

    class Meta:
        """Metadata for Message model."""

        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        ordering = ["-created_at"]

    def __str__(self):
        """Return message title and sender name."""
        # Также можно изменить __str__ для отображения отправителя
        sender_name = self.sender.get_full_name() if self.sender else "Неизвестный"
        return f"{self.title} (От: {sender_name})"
