"""App configuration for the authentication app."""

from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    """Configuration class for the authentication application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "src.authentication"
