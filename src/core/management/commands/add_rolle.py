"""Add initial roles, users, and related data to the database."""

import uuid

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from src.building.models import Apartment
from src.building.models import Floor
from src.building.models import House
from src.building.models import Section
from src.building.models import Staff
from src.financials.models import PaymentArticles
from src.financials.models import PersonalAccount
from src.services.models import PaymentDetail
from src.services.models import Service
from src.services.models import Tariff
from src.services.models import TariffService
from src.services.models import Unit
from src.users.models import Role
from src.web_site.models import SEO
from src.web_site.models import AboutUs
from src.web_site.models import Block
from src.web_site.models import Contact
from src.web_site.models import Gallery
from src.web_site.models import Image
from src.web_site.models import Main
from src.web_site.models import ServiceStr

from .start_data import HOUSES
from .start_data import OWNERS
from .start_data import PAYMENT_ARTICLES
from .start_data import PAYMENT_DETAIL
from .start_data import ROLES
from .start_data import SERVICES
from .start_data import STAFF as STAFF_DATA
from .start_data import SUPERUSER_EMAIL
from .start_data import SUPERUSER_PASSWORD
from .start_data import TARIFF_SERVICES
from .start_data import TARIFFS
from .start_data import UNITS


class Command(BaseCommand):
    """Create initial roles, users, and related entities in the database."""

    help = "Create initial roles, users, and related entities in the database."

    def handle(self, *args, **options):
        """Execute the management command to initialize default data."""
        self._create_roles()
        self._create_superuser()
        self._create_staff()
        self._create_payment_articles()
        self._create_payment_details()
        self._create_units()
        self._create_services()
        self._create_tariffs()
        self._create_tariff_services()
        self._create_site_content()
        self._create_owners()
        self._create_houses()
        self._assign_staff_to_houses()
        self._create_apartments()
        self._create_accounts()

        self.stdout.write(
            self.style.SUCCESS("✅ All initial data successfully created.")
        )

    # --- SECTIONS ---

    def _create_roles(self):
        """Create or verify default roles."""
        self.stdout.write(self.style.HTTP_INFO("--- Creating/Checking Roles ---"))
        for role_data in ROLES:
            role, created = Role.objects.get_or_create(
                name=role_data["name"], defaults=role_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Role created: {role.name}"))
            else:
                self.stdout.write(
                    self.style.WARNING(f"Role '{role.name}' already exists. Skipped.")
                )

    def _create_superuser(self):
        """Create or verify the superuser."""
        self.stdout.write(self.style.HTTP_INFO("\n--- Creating/Checking Superuser ---"))
        user_model = get_user_model()
        if not user_model.objects.filter(email=SUPERUSER_EMAIL).exists():
            user_model.objects.create_superuser(
                email=SUPERUSER_EMAIL,
                password=SUPERUSER_PASSWORD,
                user_id=100,
            )
            self.stdout.write(
                self.style.SUCCESS(f"Superuser created: {SUPERUSER_EMAIL}")
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Superuser with email '{SUPERUSER_EMAIL}' already exists. Skipped."
                )
            )

    def _create_staff(self):
        """Create or verify staff users."""
        self.stdout.write(self.style.HTTP_INFO("\n--- Creating/Checking Staff ---"))
        user_model = get_user_model()
        for staff_data in STAFF_DATA:
            email = staff_data.pop("email")
            password = staff_data.pop("password", None)
            role_name = staff_data.pop("role_id", None)
            role = Role.objects.filter(name=role_name).first() if role_name else None

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
                    self.style.SUCCESS(f"Staff created: {user.email} ({role_name})")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"Staff {user.email} already exists. Skipped.")
                )

    def _create_payment_articles(self):
        """Create or verify payment articles."""
        self.stdout.write(
            self.style.HTTP_INFO("\n--- Creating/Checking Payment Articles ---")
        )
        for article_data in PAYMENT_ARTICLES:
            article, created = PaymentArticles.objects.get_or_create(
                name=article_data["name"], defaults=article_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Payment article created: {article.name}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Payment article '{article.name}' already exists. Skipped."
                    )
                )

    def _create_payment_details(self):
        """Create or verify payment details."""
        self.stdout.write(
            self.style.HTTP_INFO("\n--- Creating/Checking Payment Details ---")
        )
        for payment_data in PAYMENT_DETAIL:
            payment_detail, created = PaymentDetail.objects.get_or_create(
                name=payment_data["name"], defaults=payment_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Payment detail created: {payment_detail.name}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Payment detail '{payment_detail.name}' already exists. Skipped."
                    )
                )

    def _create_units(self):
        """Create or verify measurement units."""
        self.stdout.write(self.style.HTTP_INFO("\n--- Creating/Checking Units ---"))
        for unit_info in UNITS:
            unit, created = Unit.objects.get_or_create(
                name=unit_info["name"], defaults=unit_info
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Unit created: {unit.name}"))
            else:
                self.stdout.write(
                    self.style.WARNING(f"Unit '{unit.name}' already exists. Skipped.")
                )

    def _create_services(self):
        """Create or verify services."""
        self.stdout.write(self.style.HTTP_INFO("\n--- Creating/Checking Services ---"))
        for service_data in SERVICES:
            unit_name = service_data.pop("unit_name", None)
            if not unit_name:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipped service '{service_data['name']}' — missing unit_name."
                    )
                )
                continue

            try:
                unit = Unit.objects.get(name=unit_name)
            except Unit.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipped service '{service_data['name']}' — unit '{unit_name}' not found."
                    )
                )
                continue

            service, created = Service.objects.get_or_create(
                name=service_data["name"],
                defaults={
                    "unit": unit,
                    "is_show": service_data.get("is_show", False),
                },
            )
            if not created and service.unit != unit:
                service.unit = unit
                service.save()

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Service created: {service.name}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Service '{service.name}' already exists. Skipped."
                    )
                )

    def _create_tariffs(self):
        """Create or verify tariffs."""
        self.stdout.write(self.style.HTTP_INFO("\n--- Creating/Checking Tariffs ---"))
        for tariff_data in TARIFFS:
            tariff, created = Tariff.objects.get_or_create(
                title=tariff_data["title"],
                defaults={"description": tariff_data.get("description", "")},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Tariff created: {tariff.title}"))
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Tariff '{tariff.title}' already exists. Skipped."
                    )
                )

    def _create_tariff_services(self):
        """Create or verify tariff-service bindings."""
        self.stdout.write(
            self.style.HTTP_INFO("\n--- Creating/Checking Tariff Services ---")
        )
        for ts_data in TARIFF_SERVICES:
            try:
                tariff = Tariff.objects.get(title=ts_data["tariff_title"])
                service = Service.objects.get(name=ts_data["service_name"])
            except (Service.DoesNotExist, Tariff.DoesNotExist) as e:
                self.stdout.write(self.style.ERROR(f"Error: {e}"))
                continue

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
                    self.style.SUCCESS(f"TariffService created: {tariff_service}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"TariffService '{tariff_service}' already exists."
                    )
                )

    def _create_site_content(self):
        """Create or verify website content (SEO, main, about, contact, etc.)."""
        self.stdout.write(self.style.HTTP_INFO("\n--- Creating Site Content ---"))

        seo_main, _ = SEO.objects.get_or_create(
            title="Main Page",
            defaults={"description": "Main page description", "keyword": "main, site"},
        )
        seo_about, _ = SEO.objects.get_or_create(
            title="About Us",
            defaults={"description": "About us page", "keyword": "about, company"},
        )
        seo_service, _ = SEO.objects.get_or_create(
            title="Services",
            defaults={"description": "Services page", "keyword": "services, tariffs"},
        )
        seo_contact, _ = SEO.objects.get_or_create(
            title="Contacts",
            defaults={"description": "Contact page", "keyword": "contact, address"},
        )

        main_page, _ = Main.objects.get_or_create(
            title="Welcome to our site",
            defaults={
                "description": "<p>Main page description</p>",
                "slide": "slides/slide1.jpg",
                "slide2": "slides/slide2.jpg",
                "slide3": "slides/slide3.jpg",
                "seo": seo_main,
            },
        )

        for block_data in [
            {
                "title": "Block 1",
                "description": "Description 1",
                "image": "blocks/block1.jpg",
            },
            {
                "title": "Block 2",
                "description": "Description 2",
                "image": "blocks/block2.jpg",
            },
        ]:
            Block.objects.get_or_create(
                title=block_data["title"],
                main=main_page,
                defaults={
                    "description": block_data["description"],
                    "image": block_data["image"],
                },
            )

        about_us_page, _ = AboutUs.objects.get_or_create(
            title="About Our Company",
            defaults={
                "image": "about_us/about.jpg",
                "description": "Company description",
                "title2": "More",
                "description2": "Additional info",
                "seo": seo_about,
            },
        )

        gallery, _ = Gallery.objects.get_or_create(about_us=about_us_page, name="main")
        Image.objects.get_or_create(gallery=gallery, image="gallery/image1.jpg")

        ServiceStr.objects.get_or_create(
            title="Service 1",
            defaults={
                "description": "Service description",
                "image": "services/service1.jpg",
                "is_tariff": False,
                "seo": seo_service,
            },
        )

        Contact.objects.get_or_create(
            full_name="Example LLC",
            defaults={
                "title": "Our Office",
                "description": "Contact info",
                "location": "Kyiv",
                "phone": "+380123456789",
                "url": "https://example.com",
                "address": "1 Example St",
                "map": "<iframe>map</iframe>",
                "email": "info@example.com",
                "seo": seo_contact,
            },
        )

    def _create_owners(self):
        """Create or verify apartment owners."""
        self.stdout.write(self.style.HTTP_INFO("\n--- Creating/Checking Owners ---"))
        user_model = get_user_model()
        for owner_data in OWNERS:
            email = owner_data.pop("email")
            password = owner_data.pop("password", None)
            user, created = user_model.objects.get_or_create(
                email=email, defaults=owner_data
            )
            if created and password:
                user.set_password(password)
                user.save()
            msg = (
                f"Owner created: {user.email}"
                if created
                else f"Owner {user.email} exists. Skipped."
            )
            self.stdout.write(
                self.style.SUCCESS(msg) if created else self.style.WARNING(msg)
            )

    def _create_houses(self):
        """Create or verify houses."""
        self.stdout.write(self.style.HTTP_INFO("\n--- Creating/Checking Houses ---"))
        for house_data in HOUSES:
            house, created = House.objects.get_or_create(
                title=house_data["title"], defaults={"address": house_data["address"]}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"House created: {house.title}"))
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"House '{house.title}' already exists. Skipped."
                    )
                )

    def _assign_staff_to_houses(self):
        """Assign staff users to houses."""
        self.stdout.write(self.style.HTTP_INFO("\n--- Assigning Staff to Houses ---"))
        user_model = get_user_model()
        houses = list(House.objects.all()[:2])
        if len(houses) < 2:
            self.stdout.write(
                self.style.ERROR("Not enough houses for staff assignment.")
            )
            return

        for idx, user_id in enumerate(range(1, 11)):
            try:
                user = user_model.objects.get(id=user_id)
                house = houses[0] if user_id <= 5 else houses[1]
                _, created = Staff.objects.get_or_create(house=house, user=user)
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f"{user.email} assigned to {house.title}")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"{user.email} already linked to {house.title}"
                        )
                    )
            except user_model.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"User with id={user_id} not found.")
                )

    def _create_apartments(self):
        """Create sections, floors, and apartments."""
        self.stdout.write(self.style.HTTP_INFO("\n--- Creating Apartments ---"))
        user_model = get_user_model()
        houses = list(House.objects.all()[:2])
        sections = ["A", "B"]
        tariff = Tariff.objects.first()
        if not tariff:
            self.stdout.write(self.style.ERROR("No available tariffs."))
            return

        apartment_counter = 1
        for i, owner_data in enumerate(OWNERS):
            try:
                user = user_model.objects.get(user_id=owner_data["user_id"])
            except user_model.DoesNotExist:
                continue

            house = houses[i % len(houses)]
            section, _ = Section.objects.get_or_create(
                name=sections[i % len(sections)], house=house
            )
            floor, _ = Floor.objects.get_or_create(name=str((i % 5) + 1), house=house)

            apartment, created = Apartment.objects.get_or_create(
                apartment_number=apartment_counter,
                house=house,
                section=section,
                floor=floor,
                defaults={"area": 45 + (i % 4) * 10, "tariff": tariff, "user": user},
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Apt #{apartment.apartment_number} "
                        f"created in {house.title} → {user.email}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Apt #{apartment.apartment_number} already exists."
                    )
                )
            apartment_counter += 1

    def _create_accounts(self):
        """Create personal accounts for apartments."""
        self.stdout.write(self.style.HTTP_INFO("\n--- Creating Personal Accounts ---"))
        apartments = Apartment.objects.select_related("user", "account").all()

        for apartment in apartments:
            if not apartment.user:
                self.stdout.write(
                    self.style.WARNING(
                        f"Apt #{apartment.apartment_number} has no owner. Skipped."
                    )
                )
                continue
            if apartment.account:
                self.stdout.write(
                    self.style.WARNING(
                        f"Apt #{apartment.apartment_number} already has account "
                        f"{apartment.account.account_number}."
                    )
                )
                continue

            account = PersonalAccount.objects.create(
                user=apartment.user,
                account_number=uuid.uuid4().hex[:10].upper(),
                status="active",
            )
            apartment.account = account
            apartment.save(update_fields=["account"])
            self.stdout.write(
                self.style.SUCCESS(
                    f"Account {account.account_number} "
                    f"created for Apt #{apartment.apartment_number}"
                )
            )
