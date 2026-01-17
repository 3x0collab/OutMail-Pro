import os
from celery import Celery

# Set default Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "outmail_pro.settings")

app = Celery("outmail_pro")

# Load settings with CELERY_ prefix
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks.py in apps
app.autodiscover_tasks()
