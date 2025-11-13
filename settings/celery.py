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
