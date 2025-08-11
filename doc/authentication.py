"""Custom authentication backend.

That allows a user to log in
using their email address or user ID.
This module provides a class
`EmailAuthBackend` for authenticating users.
"""

from django.contrib.auth import get_user_model
from django.db.models import Q


class EmailAuthBackend:
    """Authenticate using e-mail account or user ID."""

    def authenticate(self, request, username=None, password=None):
        """Authenticate a user by their email or user ID and password."""
        user_model = get_user_model()
        try:
            user = user_model.objects.get(Q(email=username) | Q(user_id=username))
            if user.check_password(password):
                return user
        except user_model.DoesNotExist:
            return None

    def get_user(self, user_id):
        """Retrieve a user object by their primary key."""
        user_model = get_user_model()
        try:
            return user_model.objects.get(pk=user_id)
        except user_model.DoesNotExist:
            return None
