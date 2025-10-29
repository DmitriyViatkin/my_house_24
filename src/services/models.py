"""Models for managing services, tariffs, and utility counters.

This module defines models to handle:
- Tariff: Defines pricing plans for services.
- Service: Represents a specific utility or service (e.g., water, electricity).
- Unit: The unit of measurement for a service (e.g., kWh, m³).
- TariffService: A junction model linking tariffs and services.
- Counter: Tracks utility usage for a specific apartment.
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.timezone import localtime


class PaymentDetail(models.Model):
    """Represents a detailed payment entry or transaction type.

    Attributes:
        name (CharField): The name of the payment detail.
        description (TextField): Additional description or notes.

    """

    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        """Return the name of the PaymentDetail."""
        return self.name


class Unit(models.Model):
    """Represents a unit of measurement for a service (e.g., 'kWh', 'm³')."""

    name = models.CharField(max_length=100, verbose_name="Ед. изм.")

    def __str__(self):
        """Return the name of the unit."""
        return self.name

    def delete(self, *args, **kwargs):
        """Prevent deletion if this unit is used by any service."""
        if self.service_set.exists():
            message = (
                "Эта единица измерения используется в услуге и не может быть удалена."
            )
            raise ValidationError(message)
        super().delete(*args, **kwargs)


class Service(models.Model):
    """Represents a specific service (e.g., 'Electricity', 'Water')."""

    name = models.CharField(max_length=255, verbose_name="Услуга")
    unit = models.ForeignKey(
        Unit, on_delete=models.CASCADE, verbose_name="Единица измерения"
    )
    is_show = models.BooleanField(default=False, verbose_name="Показывать в счетчиках")

    def __str__(self):
        """Return the name of the service."""
        return self.name


class Tariff(models.Model):
    """Represents a tariff with a title, description, date, and currency."""

    title = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        """Return the title of the tariff."""
        return self.title


class TariffService(models.Model):
    """A service included in a specific tariff plan.

    This class links a service to a tariff.
    """

    tariff = models.ForeignKey(
        "Tariff", on_delete=models.CASCADE, related_name="services"
    )
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, verbose_name="Услуга"
    )
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, verbose_name="Единица")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    currency = models.CharField(max_length=10, default="грн", verbose_name="Валюта")

    def __str__(self):
        """Return a readable representation of the tariff service."""
        return f"{self.service.name} ({self.price} {self.currency})"


STATUS_CHOICES = [
    ("new", "Новое"),
    ("zero", "Нулевое"),
    ("counted", "Учтено"),
    ("done", "Учтено и оплачено"),
]


class Counter(models.Model):
    """Represents a counter for an apartment, tracking service usage."""

    counter_number = models.CharField(
        max_length=50,
        unique=True,
        editable=True,
        verbose_name="number",
    )
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, verbose_name="Услуга"
    )
    meter_reading = models.FloatField(verbose_name="Показания счетчика")
    date = models.DateTimeField(verbose_name="Дата", default=timezone.now)
    apartment = models.ForeignKey(
        "building.Apartment", on_delete=models.CASCADE, verbose_name="Квартира"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="new", verbose_name="Статус"
    )

    def __str__(self):
        """Return a string representation of the counter."""
        return f"{self.apartment} - {self.service.name} ({self.status})"

    @property
    def service_unit(self):
        """Return the unit name of the related service."""
        return self.service.unit.name

    @property
    def month_year(self):
        """Возвращает месяц и год из даты, например 'Март 2025'."""
        months = [
            "Январь",
            "Февраль",
            "Март",
            "Апрель",
            "Май",
            "Июнь",
            "Июль",
            "Август",
            "Сентябрь",
            "Октябрь",
            "Ноябрь",
            "Декабрь",
        ]
        if self.date:
            local_date = localtime(self.date)
            return f"{months[local_date.month - 1]} {local_date.year}"
        return ""
