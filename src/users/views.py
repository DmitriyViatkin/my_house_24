"""Views for the user-facing cabinet application."""

from django.views.generic import TemplateView


class CabinetView(TemplateView):
    """View for displaying the user's personal cabinet page."""

    template_name = "main.html"

    def get_context_data(self, **kwargs):
        """Add the page title to the template context."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Cabinet"
        return context
