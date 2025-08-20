"""Filters for the core application models."""

import django_filters

from src.building.models import House
from src.users.models import User


class UserFilter(django_filters.FilterSet):
    """FilterSet for the User model, allowing filtering by various fields."""

    fio = django_filters.CharFilter(
        field_name="full_name", lookup_expr="icontains", label="ФИО"
    )
    phone = django_filters.CharFilter(lookup_expr="icontains")
    email = django_filters.CharFilter(lookup_expr="icontains")
    house = django_filters.NumberFilter()
    apartment = django_filters.NumberFilter()
    created = django_filters.DateFilter(
        field_name="created",
        lookup_expr="date",  # точное совпадение даты (игнорируя время)
        label="Дата создания",
    )
    is_active = django_filters.BooleanFilter()
    debt = django_filters.RangeFilter()

    class Meta:
        """Meta options for the UserFilter."""

        model = User
        fields = [
            "id",
            "fio",
            "phone",
            "email",
            "house",
            "apartment",
            "created",
            "is_active",
            "debt",
        ]


class HouseFilter(django_filters.FilterSet):
    """FilterSet for the House model, allowing filtering by title and address."""

    title = django_filters.CharFilter(
        field_name="title", lookup_expr="icontains", label=" Название"
    )
    address = django_filters.CharFilter(
        field_name="address", lookup_expr="icontains", label="Адрес"
    )

    class Meta:
        """Meta options for the HouseFilter."""

        model = House
        fields = ["title", "address"]
