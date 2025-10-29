"""Provide user-related context data for templates."""


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
