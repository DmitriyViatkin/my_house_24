import logging

from django.contrib.auth.backends import BaseBackend
from django.db.models import Q

from src.users.models import User

logger = logging.getLogger(__name__)


class EmailAuthBackend(BaseBackend):
    """Authentication backend that allows login via email or user_id."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        logger.info(f"AUTH backend START, username={username}")

        if not username:
            return None

        username = username.strip()

        try:
            user = User.objects.get(
                Q(email__iexact=username) | Q(user_id__iexact=username)
            )
        except User.DoesNotExist:
            logger.info(f"AUTH backend: user not found for {username}")
            return None

        if user.check_password(password):
            logger.info(f"AUTH backend: SUCCESS login for {user.email}")
            return user

        logger.info(f"AUTH backend: wrong password for {username}")
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
