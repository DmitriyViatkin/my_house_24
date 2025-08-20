"""Database models for managing personal accounts, invoices, and cashbox records."""

from django.db import models

from src.building.models import Apartment
from src.services.models import Counter
from src.services.models import Service
from src.services.models import Tariff
from src.users.models import User


class PersonalAccount(models.Model):
    """Represents a personal account for a specific apartment and user.

    Attributes:
        apartment (OneToOneField): The apartment associated with this account.
        account_number (UUIDField): Unique account number.
        user (ForeignKey): The user who owns the account.
        status (BooleanField): Indicates if the account is active.

    """

    apartment = models.OneToOneField(Apartment, on_delete=models.CASCADE)
    account_number = models.UUIDField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.BooleanField(default=True)

    def __str__(self):
        """Return the account number as the string representation."""
        return self.account_number


STATUS_TYPE_CHOICES = [
    ("new", "Оплачено"),
    ("zero", "Неоплачено"),
    ("counted", "Частично оплачено"),
]


class Invoice(models.Model):
    """Represents an invoice issued for services or tariffs.

    Attributes:
        conducted (BooleanField): Whether the invoice is conducted.
        status (CharField): Payment status of the invoice.
        account_number (UUIDField): Related personal account number.
        mount (DateField): Month the invoice is issued for.
        service (ForeignKey): Related service.
        tariff (ForeignKey): Related tariff.
        date (DateField): Invoice creation date.

    """

    conducted = models.BooleanField()
    status = models.CharField(choices=STATUS_TYPE_CHOICES, max_length=20)
    account_number = models.UUIDField()
    mount = models.DateField()
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    tariff = models.ForeignKey(Tariff, on_delete=models.CASCADE)
    date = models.DateField()

    def __str__(self):
        """Return a string representation of the invoice item."""
        return f"{self.name} for Invoice #{self.invoice.id}"


class InvoiseItem(models.Model):
    """Represents a single item in an invoice.

    Attributes:
        invoice (ForeignKey): Related invoice.
        service (ForeignKey): Related service.
        counter (ForeignKey): Related counter for usage measurement.
        total (DecimalField): Total amount for the item.

    """

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    counter = models.ForeignKey(Counter, on_delete=models.CASCADE)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        """Return a string representation of the invoice item."""
        # Assuming you have a 'name' field and a 'invoice' ForeignKey
        return f"{self.name} for Invoice #{self.invoice.id}"


class Template(models.Model):
    """Represents a file template for generating documents.

    Attributes:
        name (CharField): Template name.
        file (FileField): The template file.

    """

    name = models.CharField(max_length=255)
    file = models.FileField(upload_to="templates/")

    def __str__(self):
        """Return the name of the template."""
        return self.name


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

    cash_box_number = models.UUIDField()
    date = models.DateField()
    is_conducted = models.BooleanField()
    payment_articles = models.ForeignKey(PaymentArticles, on_delete=models.CASCADE)
    personal_account = models.ForeignKey(PersonalAccount, on_delete=models.CASCADE)
    sum = models.DecimalField(max_digits=12, decimal_places=2)
    comment = models.TextField()
    manager = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="managed_cashboxes"
    )
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_cashboxes"
    )

    def __str__(self):
        """Return the date and amount of the cashbox transaction."""
        return f"CashBox transaction on {self.date} for {self.amount}"
