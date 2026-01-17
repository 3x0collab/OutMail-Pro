"""
Django settings for OutMail Pro project
User-based SMTP edition
"""

import os
from pathlib import Path

# ───────────────────────────────
# Base Directory
# ───────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent


# ───────────────────────────────
# Basic Configuration
# ───────────────────────────────
SECRET_KEY = "django-insecure-7@e=pso6kb=-2i)t44_tznv#me7+$0^j(r#kxund)2vl^am&6u"
DEBUG = True
ALLOWED_HOSTS = ["*"]


# ───────────────────────────────
# Installed Apps
# ───────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "mailer",  # OutMail Pro app
    "django_celery_results",
    "django_celery_beat",
]


# ───────────────────────────────
# Middleware
# ───────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ───────────────────────────────
# URLs / WSGI / ASGI
# ───────────────────────────────
ROOT_URLCONF = "outmail_pro.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "outmail_pro.wsgi.application"
ASGI_APPLICATION = "outmail_pro.asgi.application"


# ───────────────────────────────
# Database (SQLite)
# ───────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# ───────────────────────────────
# Authentication
# ───────────────────────────────
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"


# ───────────────────────────────
# Static & Media Files
# ───────────────────────────────
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# ───────────────────────────────
# Email Configuration (User-Based)
# ───────────────────────────────
# Each user provides their SMTP credentials in SMTPConfig.
# Global settings only serve as fallback or test mode.

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# Optional fallback (safe defaults)
EMAIL_HOST = "localhost"
EMAIL_PORT = 25
EMAIL_USE_TLS = False
EMAIL_USE_SSL = False
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
DEFAULT_FROM_EMAIL = "OutMail Pro <no-reply@outmailpro.local>"

MAILER_BATCH_SIZE = 50
MAILER_BATCH_DELAY_SECONDS = 10.0


# ───────────────────────────────
# Celery Configuration
# ───────────────────────────────
CELERY_BROKER_URL = "sqla+sqlite:///celerybroker/celerydb.sqlite3"
CELERY_RESULT_BACKEND = "django-db"

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Africa/Lagos"


# ───────────────────────────────
# Caching (for progress tracking)
# ───────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "outmail_pro-cache",
    }
}


# ───────────────────────────────
# Internationalization
# ───────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True


# ───────────────────────────────
# Default Auto Field
# ───────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ───────────────────────────────
# Security (Production Tips)
# ───────────────────────────────
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_SSL_REDIRECT = True
