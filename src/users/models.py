"""Database models for the user application."""

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Custom user model inheriting from AbstractUser.

    Uses email as the unique identifier for authentication.
    """

    image = models.ImageField(
        upload_to="users/images/", blank=True, null=True, verbose_name="Аватар"
    )
    user_id = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, verbose_name="ID"
    )
    description = models.TextField(blank=True, verbose_name="Описание")
    status = models.BooleanField(default=True, verbose_name="Активный пользователь")
    viber = models.CharField(max_length=255, blank=True, verbose_name="Viber")
    telegram = models.CharField(max_length=255, blank=True, verbose_name="Telegram")
    email = models.EmailField(_("email address"), unique=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []


class Role(models.Model):
    """The Role model represents the permissions .

    Each user is associated with a single role that defines what sections
     and functionalities
    they can access, such as statistics, cashbox, invoices, etc.
    This model is a core
    component for managing user permissions and access control.
    """

    name = models.CharField(max_length=100, unique=True, verbose_name="Роль")
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    has_statistic = models.BooleanField(default=False, verbose_name="Статистика")
    has_cashbox = models.BooleanField(default=False, verbose_name="Касса")
    has_invoice = models.BooleanField(default=False, verbose_name="Квитанции")
    has_personal_account = models.BooleanField(
        default=False, verbose_name="личный счёт"
    )
    has_user = models.BooleanField(default=False, verbose_name="Работники")
    has_owner = models.BooleanField(default=False, verbose_name="Владельци")
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
    ("new", "New"),
    ("work", "In Progress"),
    ("done", "Done"),
]


class Ticket(models.Model):
    """Represents a support ticket submitted by a user for a specific house.

    This model tracks the lifecycle of a ticket, from creation to completion,
    including details like the user who submitted it, the associated property,
    the current status, and relevant contact information and comments.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Владелец")
    house = models.ForeignKey(
        "building.House", on_delete=models.CASCADE, verbose_name="Дом"
    )
    status = models.CharField(
        max_length=4,
        choices=STATUS_TYPE_CHOICES,
        default="new",
        verbose_name="Статус заявки",
    )
    summary = models.CharField(max_length=255, verbose_name="Короткое описание")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    date = models.DateField(auto_now_add=True, verbose_name="Дата ")
    time = models.TimeField(auto_now_add=True, verbose_name="Время")
    comment = models.TextField(verbose_name="Комментарий", blank=True)

    def __str__(self):
        """Return the name of the role as its string representation."""
        return f"Ticket for {self.house} by {self.user}"


class Message(models.Model):
    """The Message model represents a communication sent by a user.

    It includes a title and the body of the message, and is linked to the
    user who created it. This model is used for internal messaging within
    the system.
    """

    title = models.CharField(max_length=255, verbose_name="Заголовок")
    text = models.TextField(verbose_name="Текст сообщения")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Владелец")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        """Return the name of the role as its string representation."""

        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        ordering = ["-created_at"]

    def __str__(self):
        """Return the name of the role as its string representation."""
        return self.title
