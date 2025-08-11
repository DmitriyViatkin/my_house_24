"""Application configuration for the user app."""

from django.apps import AppConfig


class CabinetConfig(AppConfig):
    """Configuration for the user application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "src.users"
