"""Custom authentication backend using email instead of username."""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend


class EmailAuthBackend(BaseBackend):
    """Authentication backend that allows login via email and password."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        """Authenticate user by email and password.

        Args:
            request: HttpRequest object (can be None).
            username (str): Provided username (treated as email).
            password (str): Provided password.
            **kwargs: Additional arguments (e.g., email).

        Returns:
            User instance if authentication succeeds, otherwise None.

        """
        user_model = get_user_model()

        if username is None:
            username = kwargs.get("email")

        try:
            user = user_model.objects.get(email__iexact=username.strip())
        except user_model.DoesNotExist:
            return None

        if user.check_password(password):
            return user
        return None

    def get_user(self, user_id):
        """Retrieve user instance by ID.

        Args:
            user_id (int): Primary key of the user.

        Returns:
            User instance if found, otherwise None.

        """
        user_model = get_user_model()
        try:
            return user_model.objects.get(pk=user_id)
        except user_model.DoesNotExist:
            return None
