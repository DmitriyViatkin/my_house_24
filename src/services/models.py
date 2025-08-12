"""Models for managing services, tariffs, and utility counters.

This module defines models to handle:
- Tariff: Defines pricing plans for services.
- Service: Represents a specific utility or service (e.g., water, electricity).
- Unit: The unit of measurement for a service (e.g., kWh, m³).
- TariffService: A junction model linking tariffs and services.
- Counter: Tracks utility usage for a specific apartment.
"""

from django.db import models


class Tariff(models.Model):
    """Represents a tariff with a title, description, date, and currency."""

    title = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    currency = models.CharField(max_length=10, verbose_name="Валюта")

    def __str__(self):
        """Return the title of the tariff."""
        return self.title


class Service(models.Model):
    """Represents a specific service (e.g., 'Electricity', 'Water')."""

    name = models.CharField(max_length=255, verbose_name="Название")

    def __str__(self):
        """Return the name of the service."""
        return self.name


class Unit(models.Model):
    """Represents a unit of measurement for a service (e.g., 'kWh', 'm³')."""

    name = models.CharField(max_length=100, verbose_name="Название")
    service = models.OneToOneField(
        Service, on_delete=models.CASCADE, verbose_name="Услуга"
    )

    def __str__(self):
        """Return the name of the unit."""
        return self.name


class TariffService(models.Model):
    """A junction model linking a Tariff to a Service."""

    tariff = models.ForeignKey(Tariff, on_delete=models.CASCADE, verbose_name="Тариф")
    service = models.OneToOneField(
        Service, on_delete=models.CASCADE, verbose_name="Услуга"
    )

    def __str__(self):
        """Return the representation of the tariff service."""
        return f"{self.service.name} ({self.tariff.title})"


STATUS_CHOICES = [
    ("new", "Новое"),
    ("zero", "Нулевое"),
    ("counted", "Учтено"),
    ("done", "Учтено и оплачено"),
]


class Counter(models.Model):
    """Represents a counter for an apartment, tracking service usage."""

    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, verbose_name="Услуга"
    )
    meter_reading = models.FloatField(verbose_name="Показания счетчика")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Дата")
    apartment = models.ForeignKey(
        "building.Apartment", on_delete=models.CASCADE, verbose_name="Квартира"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="new", verbose_name="Статус"
    )

    def __str__(self):
        """Return a string representation of the counter."""
        return f"{self.apartment} - {self.service.name} ({self.status})"
