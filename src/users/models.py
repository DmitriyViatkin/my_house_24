"""Database models for the user application."""

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Custom user model inheriting from AbstractUser.

    Uses email as the unique identifier for authentication.
    """

    image = models.ImageField(upload_to="users/images/", blank=True, null=True)
    user_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    description = models.TextField(blank=True, default="")
    status = models.BooleanField(default=True)  # аналог is_active
    viber = models.CharField(max_length=255, blank=True, default="")
    telegram = models.CharField(max_length=255, blank=True, default="")
    email = models.EmailField(_("email address"), unique=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
