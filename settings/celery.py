"""Celery configuration for the Django project.

This module:
- initializes Celery
- loads settings from Django
- discovers tasks in all installed apps
- provides a debug task for testing
"""

import logging
import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.settings")

app = Celery("settings")

# Load task modules from all registered Django apps.
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to log Celery request information.

    Useful for verifying that Celery is configured correctly.
    """
    logging.getLogger(__name__).info("Celery request: %s", self.request)


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