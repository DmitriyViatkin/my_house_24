"""Views for handling user-related functionality."""

from django.views.generic import TemplateView

from .models import AboutUs
from .models import Contact
from .models import Main
from .models import ServiceStr


class MainPageView(TemplateView):
    """View for the main page of the website."""

    template_name = "main_page.html"

    def get_context_data(self, **kwargs):
        """Add main page and contact data to the context."""
        context = super().get_context_data(**kwargs)
        # Получаем первый (или единственный) объект Main
        # используя select_related() для SEO и prefetch_related() для blocks
        main_page = (
            Main.objects.select_related("seo").prefetch_related("blocks").first()
        )
        contact = Contact.objects.first()
        context["main_page"] = main_page
        context["contact"] = contact
        return context


class AboutPageView(TemplateView):
    """View for the 'About Us' page."""

    template_name = "about_us.html"

    def get_context_data(self, **kwargs):
        """Add additional company data to the context."""
        context = super().get_context_data(**kwargs)

        about = (
            AboutUs.objects.select_related("seo")
            .prefetch_related("galleries__images", "documents")
            .first()
        )
        main_gallery = about.galleries.filter(name="main").first()
        additional_gallery = about.galleries.filter(name="additional").first()
        context["about"] = about
        context["main_gallery"] = main_gallery
        context["additional_gallery"] = additional_gallery
        return context


class ServicePageView(TemplateView):
    """View for the services page."""

    template_name = "service.html"

    def get_context_data(self, **kwargs):
        """Add all available services to the context."""
        context = super().get_context_data(**kwargs)

        services = (
            ServiceStr.objects.select_related("seo").filter(is_tariff=False).all()
        )

        context["services"] = services

        return context


class TariffsPageView(TemplateView):
    """View for the tariffs page."""

    template_name = "tariffs1.html"

    def get_context_data(self, **kwargs):
        """Add tariff data to the context."""
        context = super().get_context_data(**kwargs)

        tariffs = ServiceStr.objects.select_related("seo").filter(is_tariff=True).all()

        context["tariffs"] = tariffs

        return context


class ContactPageView(TemplateView):
    """View for the contact page."""

    template_name = "contact.html"

    def get_context_data(self, **kwargs):
        """Add contact information to the context."""
        context = super().get_context_data(**kwargs)

        contact = Contact.objects.select_related("seo").first()

        context["contact"] = contact

        return context
