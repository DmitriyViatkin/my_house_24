"""App configuration for the core app."""

from django.apps import AppConfig


class AdminConfig(AppConfig):
    """Configuration for the core app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "src.core"
