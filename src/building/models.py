"""Models for the 'building' application.

This module defines the House model, which represents a building or property
in the system, along with its associated details.
"""

from django.db import models

from src.users.models import User


class House(models.Model):
    """Model representing a single house or property in the system.

    This model stores details about a house, including its title, address,
    creation date, and allows for multiple users to be associated with it.
    It also includes multiple image fields for showcasing the property.
    """

    title = models.CharField(max_length=255, verbose_name="Title")
    user = models.ManyToManyField(User, verbose_name="Users")
    address = models.TextField(verbose_name="Address")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Date Added")

    # Image fields for the house
    image1 = models.ImageField(
        upload_to="houses/", blank=True, null=True, verbose_name="Image 1"
    )
    image2 = models.ImageField(
        upload_to="houses/", blank=True, null=True, verbose_name="Image 2"
    )
    image3 = models.ImageField(
        upload_to="houses/", blank=True, null=True, verbose_name="Image 3"
    )
    image4 = models.ImageField(
        upload_to="houses/", blank=True, null=True, verbose_name="Image 4"
    )
    image5 = models.ImageField(
        upload_to="houses/", blank=True, null=True, verbose_name="Image 5"
    )

    class Meta:
        """Meta options for the House model."""

        verbose_name = "House"
        verbose_name_plural = "Houses"

    def __str__(self):
        """Return the title of the house."""
        return self.title


class Section(models.Model):
    """Секция (подъезд) в доме.

    Атрибуты:
        name (str): Название секции.
        house (House): Дом, к которому относится секция.
    """

    name = models.CharField(max_length=255, verbose_name="Название секции")
    house = models.ForeignKey(House, on_delete=models.CASCADE, related_name="sections")

    class Meta:
        """Meta options for the Section model."""

        verbose_name = "Секция"
        verbose_name_plural = "Секции"

    def __str__(self):
        """Return the string representation of the section."""
        # Assuming you have a 'name' field, like 'Section A', 'Section B'
        return f"Section {self.name}"


class Floor(models.Model):
    """Этаж в секции.

    Атрибуты:
        name (str): Номер или название этажа.
        section (Section): Секция, к которой относится этаж.
    """

    name = models.CharField(max_length=50, verbose_name="Этаж")
    section = models.ForeignKey(
        Section, on_delete=models.CASCADE, related_name="floors"
    )

    class Meta:
        """Meta options for the Floor model."""

        verbose_name = "Этаж"
        verbose_name_plural = "Этажи"

    def __str__(self):
        """Return the floor number."""
        return f"Floor {self.number}"


class Apartment(models.Model):
    """Квартира в доме.

    Атрибуты:
        apartment_number (int): Номер квартиры.
        area (float): Площадь квартиры (в м²).
        floor (Floor): Этаж, на котором находится квартира.
        tariff (Tariff): Применяемый тариф.
        user (User): Владелец квартиры.
    """

    apartment_number = models.PositiveIntegerField(verbose_name="Номер квартиры")
    area = models.FloatField(verbose_name="Площадь, м²")
    floor = models.ForeignKey(
        Floor, on_delete=models.CASCADE, related_name="apartments"
    )
    tariff = models.ForeignKey(
        "services.Tariff", on_delete=models.SET_NULL, null=True, blank=True
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        """Meta options for the Floor model."""

        verbose_name = "Квартира"
        verbose_name_plural = "Квартиры"

    def __str__(self):
        """Return the apartment number."""
        return f"Apartment {self.number}"
