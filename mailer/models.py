from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User

User = get_user_model()


class EmailLog(models.Model):
    STATUS_CHOICES = [
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="email_logs")
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField(blank=True)  # store a copy or snippet
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    error_message = models.TextField(blank=True, null=True)
    retries = models.IntegerField(default=0)
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.recipient} - {self.status} - {self.sent_at.isoformat()}"




class SMTPConfig(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="smtp_config")
    host = models.CharField(max_length=255)
    port = models.IntegerField(default=587)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255, blank=True, null=True)
    use_ssl = models.BooleanField(default=False)
    use_tls = models.BooleanField(default=True)
    default_from = models.EmailField(blank=True, null=True)  # ✅ Add this
    display_name = models.CharField(max_length=255, blank=True, null=True)  # ✅ Already used

    def __str__(self):
        return f"{self.user.username} SMTP ({self.host})"

