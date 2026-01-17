import re
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.cache import cache
from django.core.mail import EmailMessage, get_connection
from django.conf import settings
from .models import EmailLog, SMTPConfig  # ✅ import your model for per-user SMTP


# -----------------------------
# Cache helpers
# -----------------------------
def _make_progress_key(job_id):
    return f"mailer_progress:{job_id}"

def init_progress(job_id, total):
    cache.set(_make_progress_key(job_id), {
        "sent": 0,
        "failed": 0,
        "total": total,
        "errors": [],
        "completed": False,
    }, timeout=60 * 60)

def get_progress(job_id):
    return cache.get(_make_progress_key(job_id)) or {
        "sent": 0,
        "failed": 0,
        "total": 0,
        "errors": [],
        "completed": False,
    }

def update_progress(job_id, sent_inc=0, failed_inc=0, error=None):
    state = get_progress(job_id)
    state["sent"] += sent_inc
    state["failed"] += failed_inc
    if error and len(state["errors"]) < 50:
        state["errors"].append(error)
    cache.set(_make_progress_key(job_id), state, timeout=60 * 60)


# -----------------------------
# HTML formatter
# -----------------------------
def format_body_as_html(text):
    if not text:
        return ""
    if "<html" in text.lower() or "<body" in text.lower():
        return text
    text = re.sub(r'(https?://[^\s<]+)', r'<a href="\1">\1</a>', text)
    text = text.replace("\n", "<br>")
    return f"<html><body>{text}</body></html>"


# -----------------------------
# Validate recipient
# -----------------------------
def is_valid_recipient(recipient):
    if not recipient or "@" not in recipient:
        return False
    domain = recipient.split("@")[-1].lower()
    bad_domains = ["spam", "blacklist", "blocklist", "invalid",
                   "example.com", "test.com", "noemail", "temp"]
    return not any(b in domain for b in bad_domains)


# -----------------------------
# SMTP Connection (Per User)
# -----------------------------
def get_user_smtp_connection(user):
    """
    Creates an SMTP connection using the logged-in user's saved SMTPConfig.
    """
    try:
        smtp = SMTPConfig.objects.get(user=user)
    except SMTPConfig.DoesNotExist:
        raise Exception("SMTP configuration not found for this user")

    conn = get_connection(
        backend="django.core.mail.backends.smtp.EmailBackend",
        host=smtp.host,
        port=smtp.port,
        username=smtp.username,
        password=smtp.password,
        use_tls=smtp.use_tls,
        use_ssl=smtp.use_ssl,
        fail_silently=False
    )
    conn.open()
    return conn, smtp


# -----------------------------
# Send single email
# -----------------------------
def send_email_single(user, recipient, subject, body_html, attachments, job_id=None, connection=None, from_email=None):
    try:
        if not is_valid_recipient(recipient):
            EmailLog.objects.create(user=user, recipient=recipient, subject=subject,
                                    status="skipped", error_message="Invalid domain")
            if job_id:
                update_progress(job_id, failed_inc=1)
            return False

        email = EmailMessage(
            subject=subject,
            body=body_html,
            from_email=from_email,
            to=[recipient],
            connection=connection
        )
        email.content_subtype = "html"
        email.extra_headers = {
            "Reply-To": from_email,
            "X-Mailer": "Python/Django Mailer",
        }

        for att in attachments:
            email.attach(att["name"], att["content"], att["content_type"])

        email.send(fail_silently=False)
        EmailLog.objects.create(user=user, recipient=recipient, subject=subject, status="sent")
        if job_id:
            update_progress(job_id, sent_inc=1)
        return True

    except Exception as e:
        EmailLog.objects.create(user=user, recipient=recipient, subject=subject,
                                status="failed", error_message=str(e))
        if job_id:
            update_progress(job_id, failed_inc=1, error={"recipient": recipient, "error": str(e)})
        return False


# -----------------------------
# Bulk email sender
# -----------------------------
def send_bulk_emails_sync(user, emails, subject, body, job_id=None, batch_size=50, workers=10, attachments=None):
    """
    Sends emails in parallel using the user's SMTP credentials.
    """
    if not emails:
        return {"sent": 0, "failed": 0}

    total = len(emails)
    body_html = format_body_as_html(body)
    attachments = attachments or []

    if job_id:
        init_progress(job_id, total)

    # Preload attachments once
    attachment_data = []
    for f in attachments:
        try:
            data = f.read() if hasattr(f, 'read') else open(f, "rb").read()
            attachment_data.append({
                "name": f.name if hasattr(f, 'name') else f.split("/")[-1],
                "content": data,
                "content_type": getattr(f, "content_type", "application/octet-stream")
            })
            if hasattr(f, 'seek'):
                f.seek(0)
        except Exception as e:
            print(f"Attachment load error: {e}")

    sent = failed = 0
    conn, smtp = get_user_smtp_connection(user)

    try:
        for i in range(0, total, batch_size):
            batch = emails[i:i + batch_size]

            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(
                        send_email_single,
                        user, r, subject, body_html, attachment_data,
                        job_id, conn, smtp.default_from_email
                    ): r for r in batch
                }

                for future in as_completed(futures):
                    try:
                        if future.result():
                            sent += 1
                        else:
                            failed += 1
                    except Exception as e:
                        failed += 1
                        print(f"Thread error: {e}")

            # avoid throttling
            if i + batch_size < total:
                time.sleep(3)

    finally:
        try:
            conn.close()
        except Exception:
            pass

    if job_id:
        state = get_progress(job_id)
        state["completed"] = True
        cache.set(_make_progress_key(job_id), state, timeout=60 * 60)

    print(f"✅ Done. Sent: {sent}, Failed: {failed}")
    return {"sent": sent, "failed": failed}
