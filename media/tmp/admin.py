from django.contrib import admin
from .models import EmailLog

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("recipient", "subject", "status", "retries", "sent_at")
    list_filter = ("status",)
    search_fields = ("recipient", "subject")
