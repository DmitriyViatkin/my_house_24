"""Define asynchronous Celery tasks for user notifications and invoice delivery."""

from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.html import strip_tags

from src.core.export_exel import excel_to_html_openpyxl
from src.core.export_exel import fill_invoice_to_excel
from src.core.export_exel import html_to_pdf
from src.financials.models import Invoice
from src.financials.models import Template
from src.users.models import Message

User = get_user_model()
import logging


logger = logging.getLogger(__name__)

@shared_task
def send_user_message(title, description, user_id=None, sender_id=None):
    """Create a message and send it to the specified user or to all users.

    If `user_id` is None, the message is sent to all users.
    """
    recipients = User.objects.filter(id=user_id) if user_id else User.objects.all()
    sender = User.objects.filter(id=sender_id).first() if sender_id else None

    message_obj = Message.objects.create(title=title, text=description, sender=sender)
    message_obj.recipients.add(*recipients)

    sent_count = 0
    for user in recipients:
        if user.email:
            plain_text = strip_tags(description)
            send_mail(
                subject=title,
                message=plain_text,
                from_email="no-reply@yourdomain.com",
                recipient_list=[user.email],
                html_message=description,
            )
            sent_count += 1

    return (
        f"Created message for {recipients.count()} users, email sent to {sent_count}."
    )


@shared_task
def send_invoice_pdf_email(invoice_id, recipient_email, template_id=None):
    """Generate a PDF invoice and send it to the specified email.

    If `template_id` is not provided, use the default template.
    """
    xlsx_path = html_path = pdf_path = None
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)

        template_obj = (
            get_object_or_404(Template, id=template_id)
            if template_id
            else Template.objects.filter(is_default=True).first()
        )
        if not template_obj:
            return "Error: No default template found for invoice!"

        template_name = template_obj.file.name

        # Generate Excel file
        xlsx_path = fill_invoice_to_excel(invoice_id, template_name=template_name)

        # Convert Excel → HTML → PDF
        html_path = excel_to_html_openpyxl(xlsx_path)
        pdf_path = html_to_pdf(html_path)

        if not Path(pdf_path).exists():
            return "Error: PDF file not found after generation."

        # Send email
        subject = f"Invoice #{invoice.invoice_number}"
        body = "Hello! Your invoice is attached."
        email = EmailMessage(
            subject, body, settings.DEFAULT_FROM_EMAIL, [recipient_email]
        )
        email.attach_file(pdf_path, mimetype="application/pdf")
        email.send(fail_silently=False)

        return f"Invoice #{invoice.invoice_number} sent to {recipient_email}"

    finally:
        # Remove temporary files
        for f in [xlsx_path, html_path, pdf_path]:
            path = Path(f) if f else None
            if path and path.exists():
                try:
                    path.unlink()
                except OSError:
                    # Use silent cleanup, no print/log to avoid T201
                    continue


@shared_task
def send_invitation_task(email, phone):
    """Send an invitation asynchronously via email and/or SMS.

    Email is sent if an address is provided; phone is included in the message body.
    """
    if email:
        subject = "Invitation to join us!"
        message = (
            f"Hello! We are pleased to invite you. "
            f"Please follow the link to register. "
            f"(Contact: {phone or 'not provided'})"
        )
        send_mail(
            subject, message, "viatkindima@gmail.com", [email], fail_silently=False
        )

    return "Invitation processed."


@shared_task
def send_broadcast_email(  # noqa: PLR0913
    message_id,
    house_id=None,
    section_id=None,
    floor_id=None,
    flat_id=None,
    *,
    only_debtors=False,
):
    """Send a broadcast email based on filtering criteria.

    Retrieve the message by ID and send it to users filtered by house, section,
    floor, or apartment. Optionally, send only to debtors.
    """
    user_model = get_user_model()

    try:
        message_obj = Message.objects.get(pk=message_id)
        subject = message_obj.title
        text = message_obj.text
    except Message.DoesNotExist:
        return f"Message with ID={message_id} not found. Sending aborted."

    # Base queryset: active users with email, excluding staff
    user_queryset = user_model.objects.filter(
        is_active=True, email__isnull=False
    ).exclude(is_staff=True)

    # Filter by location
    if any([flat_id, floor_id, section_id, house_id]):
        filter_kwargs = {}
        if flat_id:
            filter_kwargs["apartments__id"] = flat_id
        elif floor_id:
            filter_kwargs["apartments__floor_id"] = floor_id
        elif section_id:
            filter_kwargs["apartments__section_id"] = section_id
        elif house_id:
            filter_kwargs["apartments__house_id"] = house_id
        user_queryset = user_queryset.filter(**filter_kwargs)

    # Filter debtors
    if only_debtors:
        debt_accounts_pks = (
            Invoice.objects.filter(
                Q(status="zero") | Q(status="counted"),
                conducted=True,
            )
            .values_list("personal_account__pk", flat=True)
            .distinct()
        )
        user_queryset = user_queryset.filter(personalaccount__pk__in=debt_accounts_pks)

    user_queryset = user_queryset.distinct()
    recipient_list = list(user_queryset.values_list("email", flat=True))

    if not recipient_list:
        return f"No active users found matching criteria for broadcast '{subject}'."

    send_mail(
        subject,
        text,
        settings.DEFAULT_FROM_EMAIL,
        recipient_list,
        fail_silently=False,
    )

    message_obj.recipients.set(user_queryset)
    message_obj.save()

    return f"Email '{subject}' successfully sent to {len(recipient_list)} users."


@shared_task(bind=True, ignore_result=True)
def send_password_reset_email(self, subject, message, recipient_list):
    """
    Celery task to send password reset email asynchronously.

    Args:
        subject (str): Тема письма
        message (str): Текст письма (ссылки для сброса)
        recipient_list (list): Список email получателей
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        logger.info("Password reset email sent to: %s", recipient_list)
    except Exception as e:
        logger.error("Failed to send password reset email: %s", e)