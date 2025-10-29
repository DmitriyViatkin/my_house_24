"""Django settings for the project.

Includes configuration for:
- installed apps
- middleware
- templates
- database
- authentication
- static and media files
- logging
- Celery
- email
- CKEditor
- reCAPTCHA
"""

import os
from pathlib import Path

from django.urls import reverse_lazy
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = True

# S104: Убираем "0.0.0.0" из ALLOWED_HOSTS в dev, оставляем только безопасные
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

AUTH_USER_MODEL = "users.User"
INTERNAL_IPS = ["127.0.0.1"]

LOGOUT_REDIRECT_URL = reverse_lazy("login")

INSTALLED_APPS = [
    "debug_toolbar",
    "ckeditor",
    "ckeditor_uploader",
    "src.core",
    "dal",
    "dal_select2",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "src.users",
    "src.building",
    "src.web_site",
    "src.services",
    "src.financials",
    "ajax_datatable",
    "src.authentication",
    "snowpenguin.django.recaptcha3",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

ROOT_URLCONF = "settings.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.static",
                "src.core.context_processors.user_houses",
            ],
        },
    },
]

WSGI_APPLICATION = "settings.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "djangфвмвo.contrib.auth.password_validation"
            ".UserAttributeSimilarityValidator"
        )
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = (
    "src.authentication.authentication.EmailAuthBackend",
    "django.contrib.auth.backends.ModelBackend",
)

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/admin/dashboard"

LANGUAGE_CODE = "ru"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles_collected"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"  # PTH118: заменяем os.path.join на Path

CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_CONFIGS = {
    "default": {"toolbar": "full"},
    "short_text": {
        "toolbar": "Custom",
        "toolbar_Custom": [
            [
                "Bold",
                "Italic",
                "Underline",
                "-",
                "NumberedList",
                "BulletedList",
                "-",
                "Link",
                "Unlink",
            ],
            ["TextColor", "BGColor", "-", "Font", "FontSize"],
            ["Source"],
        ],
        "extraPlugins": "autolink,codesnippet",
        "width": "100%",
        "height": "auto",
        "resize_enabled": True,
        "resize_minHeight": 800,
        "resize_maxHeight": 1500,
    },
}
CKEDITOR_BASEPATH = "/static/ckeditor/ckeditor/"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(levelname)s %(asctime)s %(name)s %(message)s"}
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
        "file": {
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs/site_debug.log",  # S108: безопасный путь
            "formatter": "verbose",
        },
    },
    "loggers": {
        "": {"handlers": ["console", "file"], "level": "DEBUG"},
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

RECAPTCHA_PRIVATE_KEY = os.getenv("RECAPTCHA_PRIVATE_KEY")
RECAPTCHA_PUBLIC_KEY = os.getenv("RECAPTCHA_PUBLIC_KEY")
RECAPTCHA_DEFAULT_ACTION = "generic"
RECAPTCHA_SCORE_THRESHOLD = 0.5

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))  # PLW1508: default как строка
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False").lower() == "true"
SERVER_EMAIL = os.getenv("SERVER_EMAIL", EMAIL_HOST_USER)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)

# Celery
CELERY_BROKER_URL = "redis://127.0.0.1:6379/0"
CELERY_RESULT_BACKEND = "redis://127.0.0.1:6379/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
