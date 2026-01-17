import uuid
import threading
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.cache import cache
from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver

from .forms import BulkEmailForm, SMTPConfigForm
from .utils import extract_and_clean_emails, send_bulk_emails_sync, init_progress, get_progress
from .models import EmailLog, SMTPConfig

# Optional Celery support
try:
    from .tasks import send_bulk_emails_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False


# ────────────────────────────────────────────────
# DASHBOARD
# ────────────────────────────────────────────────
@login_required
def dashboard(request):
    """
    Main dashboard showing the bulk email form.
    Redirects users to SMTP setup if not configured yet.
    """
    # ✅ Redirect if user has no SMTP setup
    if not SMTPConfig.objects.filter(user=request.user).exists():
        return redirect("mailer:smtp_config")

    form = BulkEmailForm()
    return render(request, "mailer/dashboard.html", {"form": form})


# ────────────────────────────────────────────────
# START BULK SEND
# ────────────────────────────────────────────────
@login_required
@require_POST
def start_send(request):
    form = BulkEmailForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)

    raw = form.cleaned_data.get("recipients", "")
    subject = form.cleaned_data.get("subject", "")
    body = form.cleaned_data.get("body", "")

    # ✅ Get attachments (if any)
    attachments = request.FILES.getlist("attachments")

    emails = extract_and_clean_emails(raw)
    if not emails:
        return JsonResponse({"ok": False, "error": "No valid recipient emails found"}, status=400)

    if len(emails) > 3000:
        emails = emails[:3000]

    job_id = str(uuid.uuid4())
    init_progress(job_id, len(emails))

    try:
        if CELERY_AVAILABLE:
            send_bulk_emails_task.delay(emails, subject, body, job_id, attachments)
        else:
            def thread_wrapper():
                try:
                    print(f"Sending job {job_id} for {len(emails)} recipients...")
                    send_bulk_emails_sync(
                        request.user, emails, subject, body, job_id, attachments=attachments
                    )
                except Exception as e:
                    import traceback
                    print(f"Exception inside email thread for job {job_id}: {e}")
                    traceback.print_exc()
                    data = get_progress(job_id)
                    data["state"] = "FAILED"
                    cache.set(f"progress:{job_id}", data, 3600)

            threading.Thread(target=thread_wrapper, daemon=True).start()

    except Exception as e:
        import traceback
        print(f"Exception starting send task for job {job_id}: {e}")
        traceback.print_exc()
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

    return JsonResponse({"ok": True, "job_id": job_id, "total": len(emails)})


# ────────────────────────────────────────────────
# PROGRESS VIEW
# ────────────────────────────────────────────────
@login_required
def progress(request, job_id):
    """
    Return JSON progress for a given job_id.
    """
    data = get_progress(job_id)
    return JsonResponse(data)


# ────────────────────────────────────────────────
# SENT LOGS
# ────────────────────────────────────────────────
@login_required
def sent_logs(request):
    """
    View paginated email logs with optional filtering by recipient or status.
    """
    qs = EmailLog.objects.filter(user=request.user).order_by("-sent_at")

    # Filter by recipient search
    q = request.GET.get("q")
    if q:
        qs = qs.filter(recipient__icontains=q)

    # Filter by status
    status = request.GET.get("status")
    if status in ("sent", "failed"):
        qs = qs.filter(status=status)

    paginator = Paginator(qs, 50)  # 50 logs per page
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    return render(request, "mailer/logs.html", {"page_obj": page_obj})


# ────────────────────────────────────────────────
# SMTP CONFIGURATION VIEW
# ────────────────────────────────────────────────
@login_required
def smtp_config_view(request):
    """
    Allow users to create or update their own SMTP settings.
    """
    try:
        instance = request.user.smtp_config
    except SMTPConfig.DoesNotExist:
        instance = None

    if request.method == "POST":
        form = SMTPConfigForm(request.POST, instance=instance)
        if form.is_valid():
            smtp_obj = form.save(commit=False)
            smtp_obj.user = request.user

            # keep existing password if left blank
            if instance and not form.cleaned_data.get("password"):
                smtp_obj.password = instance.password

            smtp_obj.save()
            messages.success(request, "✅ SMTP settings saved successfully.")
            return redirect("mailer:dashboard")  # ✅ Redirect back to dashboard after saving
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SMTPConfigForm(instance=instance)

    return render(request, "mailer/smtp_config.html", {"form": form})


# ────────────────────────────────────────────────
# CLEAR SMTP INFO ON LOGOUT
# ────────────────────────────────────────────────
@receiver(user_logged_out)
def clear_smtp_on_logout(sender, request, user, **kwargs):
    """
    Automatically delete user's SMTP settings when they log out.
    So next login requires fresh SMTP setup.
    """
    try:
        SMTPConfig.objects.filter(user=user).delete()
        print(f"🧹 Cleared SMTP config for {user.username} on logout.")
    except Exception as e:
        print(f"Failed to clear SMTP for {user}: {e}")
