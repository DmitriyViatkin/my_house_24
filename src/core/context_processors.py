"""Provide user-related context data for templates."""
import logging
from src.users.models import User
from django.db.models import Q
logger = logging.getLogger(__name__)



def user_apartments(request):
    """Add the user's apartments to the context of all templates."""
    if request.user.is_authenticated:
        apartments = request.user.apartments.select_related(
            "house", "section", "floor", "account"
        )
        return {
            "user": request.user,
            "apartments": apartments,
            "houses": {apt.house for apt in apartments},
            "sections": {apt.section for apt in apartments},
        }
    return {}


def user_houses(request):
    """Add the user's houses and related apartments to the context of all templates."""
    if request.user.is_authenticated:
        apartments = request.user.apartments.select_related(
            "house", "section", "floor", "account"
        )
        return {
            "user": request.user,
            "apartments": apartments,
            "houses": {apt.house for apt in apartments},
        }
    return {}


def new_users_count(request):
    """
    Повертає кількість користувачів зі статусом 'new'.
    """
    count = 0
    try:
        count = User.objects.filter(status='new').count()

        # --- Правильне логування ---
        # Використовуйте logger.info() замість print()
        logger.info(f"Кількість нових користувачів (Context Processor): {count}")
        # ---------------------------

    except Exception as e:
        # Для помилок використовуйте logger.error()
        logger.error(f"Помилка при отриманні кількості нових користувачів: {e}",
                     exc_info=True)
        count = 0

    return {
        'NEW_USERS_COUNT': count
    }