"""Management command to populate initial data in the database.

Creates roles, superuser, staff, owners, houses, sections, floors, apartments,
personal accounts, services, tariffs, tariff services, and website content.

Use this command to initialize the database with default records.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from src.financials.models import PaymentArticles
from src.services.models import PaymentDetail
from src.services.models import Service
from src.services.models import Tariff
from src.services.models import TariffService
from src.services.models import Unit
from src.users.models import Role

from .start_data import PAYMENT_ARTICLES
from .start_data import PAYMENT_DETAIL
from .start_data import ROLES
from .start_data import SERVICES
from .start_data import STAFF
from .start_data import SUPERUSER_EMAIL
from .start_data import SUPERUSER_PASSWORD
from .start_data import TARIFF_SERVICES
from .start_data import TARIFFS
from .start_data import UNITS


class Command(BaseCommand):
    """Initialize roles, superuser, staff,      and website content."""

    help = (
        "Create initial database records for roles, superuser, staff, and site content."
    )

    def handle(self, *args, **options):
        """Execute the command to populate initial data."""
        self.create_roles()
        self.create_superuser()
        self.create_staff_users()
        self.create_payment_articles()
        self.create_payment_details()
        self.create_units()
        self.create_services()
        self.create_tariffs_and_services()
        self.create_website_content()
        self.create_owners()
        self.create_houses()
        self.assign_staff_to_houses()
        self.create_sections_floors_apartments()
        self.create_personal_accounts()

    def create_roles(self):
        """Create or verify roles."""
        self.stdout.write(self.style.HTTP_INFO("--- Creating/Verifying Roles ---"))
        for role_data in ROLES:
            role, created = Role.objects.get_or_create(
                name=role_data["name"], defaults=role_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created role: {role.name}"))
            else:
                self.stdout.write(
                    self.style.WARNING(f"Role '{role.name}' already exists. Skipping.")
                )

    def create_superuser(self):
        """Create or verify superuser."""
        self.stdout.write(
            self.style.HTTP_INFO("\n--- Creating/Verifying Superuser ---")
        )
        user_model = get_user_model()
        if not user_model.objects.filter(email=SUPERUSER_EMAIL).exists():
            user_model.objects.create_superuser(
                email=SUPERUSER_EMAIL, password=SUPERUSER_PASSWORD, user_id=100
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully created superuser: {SUPERUSER_EMAIL}."
                )
            )
            self.stdout.write(
                self.style.NOTICE(
                    f"Email: {SUPERUSER_EMAIL}, Password: {SUPERUSER_PASSWORD}"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Superuser with email '{SUPERUSER_EMAIL}' already "
                    f"exists. Skipping."
                )
            )

    def create_staff_users(self):
        """Create or verify staff users and assign roles."""
        self.stdout.write(self.style.HTTP_INFO("\n--- Creating/Verifying Staff ---"))
        user_model = get_user_model()
        for staff_data in STAFF:
            email = staff_data.pop("email")
            password = staff_data.pop("password", None)
            role_name = staff_data.pop("role_id", None)

            role = Role.objects.get(name=role_name) if role_name else None
            user, created = user_model.objects.get_or_create(
                email=email, defaults=staff_data
            )

            if role:
                user.role = role
            if created and password:
                user.set_password(password)
            user.save()

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created user: {user.email} with role {role_name}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"User {user.email} already exists. Skipping.")
                )

    def create_payment_articles(self):
        """Create or verify payment articles."""
        self.stdout.write(self.style.HTTP_INFO("\n--- Creating Payment Articles ---"))
        for article_data in PAYMENT_ARTICLES:
            article, created = PaymentArticles.objects.get_or_create(
                name=article_data["name"], defaults=article_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created article: {article.name}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Payment article '{article.name}' already exists. Skipping."
                    )
                )

    def create_payment_details(self):
        """Create or verify payment details."""
        self.stdout.write(self.style.HTTP_INFO("\n--- Creating Payment Details ---"))
        for payment_data in PAYMENT_DETAIL:
            detail, created = PaymentDetail.objects.get_or_create(
                name=payment_data["name"], defaults=payment_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created payment detail: {detail.name}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Payment detail '{detail.name}' already exists. Skipping."
                    )
                )

    def create_units(self):
        """Create or verify units."""
        self.stdout.write(self.style.HTTP_INFO("\n--- Creating Units ---"))
        for unit in UNITS:
            unit_obj, created = Unit.objects.get_or_create(
                name=unit["name"], defaults=unit
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created unit: {unit_obj.name}"))
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Unit '{unit_obj.name}' already exists. Skipping."
                    )
                )

    def create_services(self):
        """Create or verify services."""
        self.stdout.write(self.style.HTTP_INFO("\n--- Creating Services ---"))
        for service_data in SERVICES:
            unit_name = service_data.pop("unit_name", None)
            if not unit_name:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping service '{service_data['name']}' — missing unit_name"
                    )
                )
                continue
            try:
                unit = Unit.objects.get(name=unit_name)
            except Unit.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping service '{service_data['name']}' — unit '"
                        f"{unit_name}' not found"
                    )
                )
                continue

            service, created = Service.objects.get_or_create(
                name=service_data["name"],
                defaults={"unit": unit, "is_show": service_data.get("is_show", False)},
            )
            if not created and service.unit != unit:
                service.unit = unit
                service.save()
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created service: {service.name}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Service '{service.name}' already exists. Skipping."
                    )
                )

    def create_tariffs_and_services(self):
        """Create tariffs and link TariffService."""
        self.stdout.write(
            self.style.HTTP_INFO("\n--- Creating Tariffs and TariffServices ---")
        )
        for tariff_data in TARIFFS:
            tariff, created = Tariff.objects.get_or_create(
                title=tariff_data["title"],
                defaults={"description": tariff_data.get("description", "")},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created tariff: {tariff.title}"))
            else:
                self.stdout.write(
                    self.style.WARNING(f"Tariff '{tariff.title}' already exists")
                )

        for ts_data in TARIFF_SERVICES:
            try:
                tariff = Tariff.objects.get(title=ts_data["tariff_title"])
                service = Service.objects.get(name=ts_data["service_name"])
                tariff_service, created = TariffService.objects.get_or_create(
                    tariff=tariff,
                    service=service,
                    defaults={
                        "unit": service.unit,
                        "price": ts_data["price"],
                        "currency": ts_data.get("currency", "грн"),
                    },
                )
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f"Created TariffService: {tariff_service}")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"TariffService '{tariff_service}' already exists"
                        )
                    )
            except Service.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f"Service '{ts_data['service_name']}' not found. "
                        f"Create it first."
                    )
                )
            except Tariff.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Tariff '{ts_data['tariff_title']}' not found.")
                )
