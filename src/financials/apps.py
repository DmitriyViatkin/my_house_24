"""Application configuration for the financials app."""

from django.apps import AppConfig


class FinancialsConfig(AppConfig):
    """Configuration class for the financials application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "financials"
