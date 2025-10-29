"""Database models for managing personal accounts, invoices, and cashbox records."""

from decimal import Decimal

from django.db import models
from django.db.models import Sum
from django.utils.timezone import now

from src.services.models import Tariff
from src.services.models import TariffService
from src.users.models import User

STATUS_CHOICES = [
    ("activ", "Активный"),
    ("desactiv", "Неактивный"),
]


class PersonalAccount(models.Model):
    """Represents a personal account for a specific apartment and user.

    Attributes:
        apartment (OneToOneField): The apartment associated with this account.
        account_number (UUIDField): Unique account number.
        user (ForeignKey): The user who owns the account.
        status (BooleanField): Indicates if the account is active.

    """

    account_number = models.CharField(
        max_length=50,
        unique=True,
        editable=True,
        verbose_name="Лицевой счет",
    )
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    status = models.CharField(choices=STATUS_CHOICES, max_length=20)

    def __str__(self):
        """Return the account number as the string representation."""
        return self.account_number


STATUS_TYPE_CHOICES = [
    ("new", "Оплачено"),
    ("zero", "Не оплачено"),
    ("counted", "Частично оплачено"),
]


class Invoice(models.Model):
    """Model representing a single item in an invoice."""

    conducted = models.BooleanField()
    status = models.CharField(choices=STATUS_TYPE_CHOICES, max_length=20)
    invoice_number = models.CharField(
        max_length=50, unique=True, editable=True, verbose_name="ID"
    )
    mount = models.DateField(default=now)
    start_date = models.DateField(null=True, blank=True)  # временно разрешаем null
    end_date = models.DateField(null=True, blank=True)
    personal_account = models.ForeignKey(
        PersonalAccount, on_delete=models.CASCADE, blank=True, null=True
    )

    tariff = models.ForeignKey(Tariff, on_delete=models.CASCADE)
    date = models.DateField()

    def __str__(self):
        """Return a human-readable representation of the invoice item."""
        return f"Счёт #{self.id} - {self.status}"

    @property
    def total_amount(self):
        """Return the total amount of all items in this invoice."""
        return self.items.aggregate(total=models.Sum("total"))["total"] or 0

    @property
    def balance(self):
        """Возвращает текущий баланс квартиры."""
        # ✅ 1. Сумма всех оплат (проведённых приходов)
        incoming = CashBox.objects.filter(
            personal_account=self, is_conducted=True, payment_articles__record_type="in"
        ).aggregate(total=Sum("suma"))["total"] or Decimal("0.00")

        # ✅ 2. Сумма всех начислений (проведённых квитанций)
        invoices = Invoice.objects.filter(
            personal_account=self,
            conducted=True,
        ).aggregate(total=Sum("items__total"))["total"] or Decimal("0.00")

        # ✅ 3. Разница: оплат - начислений
        return incoming - invoices


class InvoiceItem(models.Model):
    """Invoice item, links a service and its amount to a specific Invoice."""

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    tariff_service = models.ForeignKey(
        TariffService,
        on_delete=models.SET_NULL,
        null=True,
        related_name="tariff_service",
    )
    count = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        """Возвращает строковое представление элемента счёта."""
        return f"{self.tariff_service.name} ({self.total}) для счёта #{self.invoice.id}"


class Template(models.Model):
    """Represents a file template for generating documents."""

    name = models.CharField(max_length=255)
    file = models.FileField(upload_to="templates/")
    is_default = models.BooleanField(default=False)

    def __str__(self):
        """Return the name of the financial object."""
        return self.name

    def save(self, *args, **kwargs):
        """Save the financial object, ensuring default flag consistency."""
        if self.is_default:
            # Скидаємо прапор у всіх інших шаблонів
            Template.objects.exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


RECORD_TYPE_CHOICES = [
    ("out", "Расход"),
    ("in", "Приход"),
]


class PaymentArticles(models.Model):
    """Represent a type of payment transaction.

    Attributes:
        name (CharField): Name of the payment item.
        record_type (CharField): Type of the record (income/expense).

    """

    name = models.CharField(max_length=255)
    record_type = models.CharField(choices=RECORD_TYPE_CHOICES, max_length=20)

    def __str__(self):
        """Return the name of the payment item."""
        return self.name


class CashBox(models.Model):
    """Represents a cashbox transaction.

    Attributes:
        cash_box_number (UUIDField): Unique identifier for the transaction.
        date (DateField): Date of the transaction.
        is_conducted (BooleanField): Whether the transaction is conducted.
        payment_item (ForeignKey): Related payment item.
        personal_account (ForeignKey): Related personal account.
        sum (DecimalField): Transaction amount.
        comment (TextField): Additional notes.
        manager (ForeignKey): Manager responsible for the transaction.
        owner (ForeignKey): Owner of the transaction.

    """

    cash_box_number = models.CharField(
        max_length=50,
        unique=True,
        editable=True,
        verbose_name="ID",
    )
    date = models.DateField()
    is_conducted = models.BooleanField()
    payment_articles = models.ForeignKey(PaymentArticles, on_delete=models.CASCADE)
    personal_account = models.ForeignKey(
        PersonalAccount, on_delete=models.CASCADE, blank=True, null=True
    )
    suma = models.DecimalField(max_digits=12, decimal_places=2)
    comment = models.TextField()
    manager = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="managed_cashboxes"
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="owned_cashboxes",
        blank=True,
        null=True,
    )

    def __str__(self):
        """Return the date and amount of the cashbox transaction."""
        return f"CashBox transaction on {self.date} for {self.suma}"
