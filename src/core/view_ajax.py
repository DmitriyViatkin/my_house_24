"""AJAX views for datatables in the core application."""

from ajax_datatable.views import AjaxDatatableView
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.html import format_html

User = get_user_model()


class UserAjaxDatatableView(AjaxDatatableView):
    """AJAX datatable view for listing system users with staff filter."""

    model = User
    title = "Список пользователей"
    initial_order = [["email", "asc"]]
    length_menu = [[50], [50]]

    column_defs = [
        {"name": "id", "visible": False, "searchable": False},
        {
            "name": "full_name",
            "title": "Пользователь",
            "searchable": True,
            "orderable": True,
        },
        {
            "name": "role",
            "title": "Роль",
            "foreign_field": "role__name",
            "searchable": True,
        },
        {"name": "phone", "title": "Телефон", "searchable": True},
        {"name": "email", "title": "Email (логин)", "searchable": True},
        {
            "name": "status",
            "title": "Статус",
            "searchable": True,
            "choices": ((True, "Активный"), (False, "Заблокирован")),
        },
        {
            "name": "actions",
            "title": "Действия",
            "searchable": False,
            "orderable": False,
        },
    ]

    def get_initial_queryset(self, request=None):
        """Return the initial queryset filtered by staff users only."""
        return User.objects.filter(is_staff=True)

    def render_column(self, row, column):
        """Render a specific column for the datatable.

        Args:
            row (User): The User instance for the current row.
            column (str): The name of the column being rendered.

        Returns:
            str: The value to display in the column.

        """
        if column == "full_name":
            return f"{row.first_name} {row.last_name}".strip() or row.email
        if column == "status":
            return "Активный" if row.status else "Заблокирован"
        if column == "actions":
            edit_url = reverse("admin:user_update", args=[row.pk])
            delete_url = reverse("admin:user_delete", args=[row.pk])
            return format_html(
                '<a href="{}" class="btn btn-sm btn-primary">✏️</a> '
                '<a href="{}" class="btn btn-sm btn-danger">🗑️</a>',
                edit_url,
                delete_url,
            )
        return super().render_column(row, column)
