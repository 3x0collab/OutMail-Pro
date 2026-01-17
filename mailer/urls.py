from django.urls import path
from . import views

app_name = "mailer"  # ✅ important for namespace

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("start-send/", views.start_send, name="start_send"),
    path("progress/<str:job_id>/", views.progress, name="progress"),
    path("logs/", views.sent_logs, name="sent_logs"),

    # ✅ New route: SMTP Configuration page
    path("smtp-config/", views.smtp_config_view, name="smtp_config"),
]
