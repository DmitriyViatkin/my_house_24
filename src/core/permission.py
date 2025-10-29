"""Implement a custom permission mixin for role-based access control in Django views."""

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponseForbidden


class RolePermissionRequiredMixin(PermissionRequiredMixin):
    """Check user access rights using a role-based permission flag.

    Inherits from Django's standard PermissionRequiredMixin.

    Example:
        class CashboxView(RolePermissionRequiredMixin, View):
            role_permission = "has_cashbox"

    """

    role_permission: str = None
    permission_denied_message = "Insufficient permissions"
    raise_exception = True

    def has_permission(self):
        """Override the default PermissionRequiredMixin method.

        Check permissions not through Django's built-in permission system,
        but via a flag inside the user's role object.
        """
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True

        if not self.role_permission:
            return True

        role = getattr(user, "role", None)
        return getattr(role, self.role_permission, False)

    def handle_no_permission(self):
        """Return HTTP 403 Forbidden when the user lacks permissions."""
        return HttpResponseForbidden(self.permission_denied_message)
