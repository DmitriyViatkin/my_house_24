"""Application configuration for the building app."""

from django.apps import AppConfig


class BuildingConfig(AppConfig):
    """Configuration class for the building application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "building"
