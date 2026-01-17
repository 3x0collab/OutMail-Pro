import re
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.mail import EmailMessage, get_connection
from django.core.cache import cache
from django.conf import settings
from .models import EmailLog, SMTPConfig  # ✅ Added SMTPConfig import


# ==========================================================
# Helper: clean + extract emails
# ==========================================================
def extract_and_clean_emails(raw_text):
    """Extract and normalize valid emails."""
    if not raw_text:
        return []
    emails = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", raw_text)
    return list(dict.fromkeys(e.strip().lower() for e in emails))


# ==========================================================
# Progress tracking with cache
# ==========================================================
def init_progress(job_id, total):
    cache.set(
        f"progress:{job_id}",
        {"sent": 0, "failed": 0, "total": total, "state": "PROGRESS"},
        3600,
    )


def get_progress(job_id):
    return cache.get(
        f"progress:{job_id}",
        {"sent": 0, "failed": 0, "total": 0, "state": "NOT_FOUND"},
    )


def update_progress(job_id, sent_inc=0, failed_inc=0):
    data = get_progress(job_id)
    data["sent"] += sent_inc
    data["failed"] += failed_inc
    cache.set(f"progress:{job_id}", data, 3600)


# ==========================================================
# Format text to HTML automatically
# ==========================================================
def format_body_as_html(text):
    """Convert plain text with URLs to safe HTML format."""
    if not text:
        return ""
    if "<html" in text.lower():
        return text
    text = re.sub(r"(https?://[^\s<]+)", r'<a href="\1">\1</a>', text)
    return f"<html><body>{text.replace(chr(10), '<br>')}</body></html>"


# ==========================================================
# Connection pooling for SMTP (supports per-user config)
# ==========================================================
def get_connection_pool(size=5, user=None):
    pool = []

    smtp = None
    if user:
        try:
            smtp = user.smtp_config
        except SMTPConfig.DoesNotExist:
            smtp = None

    for _ in range(size):
        try:
            if smtp:
                conn = get_connection(
                    host=smtp.host,
                    port=smtp.port,
                    username=smtp.username,
                    password=smtp.password,
                    use_tls=smtp.use_tls,
                    use_ssl=smtp.use_ssl,
                    fail_silently=False,
                )
            else:
                conn = get_connection(
                    host=settings.EMAIL_HOST,
                    port=settings.EMAIL_PORT,
                    username=settings.EMAIL_HOST_USER,
                    password=settings.EMAIL_HOST_PASSWORD,
                    use_tls=settings.EMAIL_USE_TLS,
                    use_ssl=settings.EMAIL_USE_SSL,
                    fail_silently=False,
                )

            conn.open()
            pool.append(conn)

        except Exception as e:
            print(f"[Pool] Failed to open connection: {e}")

    return pool



# ==========================================================
# Helpers
# ==========================================================
def batch_emails(emails, batch_size):
    """Split emails into smaller batches."""
    for i in range(0, len(emails), batch_size):
        yield emails[i : i + batch_size]


def is_valid_recipient(recipient):
    """Reject temporary or invalid domains."""
    if not recipient or "@" not in recipient:
        return False
    domain = recipient.split("@")[-1].lower()
    bad_domains = [
        "spam",
        "blocklist",
        "blacklist",
        "invalid",
        "example.com",
        "test.com",
        "temp",
    ]
    return not any(b in domain for b in bad_domains)


# ==========================================================
# Send one email (no retry if failed)
# ==========================================================
# ==========================================================
# Send one email (no retry if failed) — UPDATED
# ==========================================================
def send_email_single(user, recipient, subject, body_html, attachments, job_id, connection, from_email):
    """Send one email using pre-opened SMTP connection."""
    if not is_valid_recipient(recipient):
        EmailLog.objects.create(
            user=user,
            recipient=recipient,
            subject=subject,
            status="failed",
            error_message="Invalid domain",
            retries=1,
        )
        update_progress(job_id, failed_inc=1)
        return False

    try:
        email = EmailMessage(
            subject=subject,
            body=body_html,
            from_email=from_email,
            to=[recipient],
            connection=connection,
        )
        email.content_subtype = "html"
        email.extra_headers = {
            "Reply-To": from_email,
            "X-Mailer": "Python/Django Mailer",
        }

        for att in attachments:
            email.attach(att["name"], att["content"], att["content_type"])

        email.send(fail_silently=False)

        # ✅ Log success
        EmailLog.objects.create(
            user=user,
            recipient=recipient,
            subject=subject,
            body=body_html[:1000],  # save snippet
            status="sent",
            retries=1,
        )

        update_progress(job_id, sent_inc=1)
        return True

    except Exception as e:
        # ✅ Log failure
        EmailLog.objects.create(
            user=user,
            recipient=recipient,
            subject=subject,
            body=body_html[:1000],
            status="failed",
            error_message=str(e),
            retries=1,
        )
        update_progress(job_id, failed_inc=1)
        return False


# ==========================================================
# Bulk sender — updated to include user in thread calls
# ==========================================================
def send_bulk_emails_sync(user, emails, subject, body, job_id=None, attachments=None):
    if not emails:
        return {"sent": 0, "failed": 0}

    body_html = format_body_as_html(body)
    total = len(emails)
    if job_id:
        init_progress(job_id, total)

    # ✅ Determine "from" email (user’s config or global)
    try:
        smtp = user.smtp_config
        from_email = f"{smtp.display_name or smtp.username} <{smtp.default_from or smtp.username}>"
    except SMTPConfig.DoesNotExist:
        from_email = settings.DEFAULT_FROM_EMAIL

    # Load attachments once
    attachment_data = []
    if attachments:
        for f in attachments:
            try:
                attachment_data.append(
                    {"name": f.name, "content": f.read(), "content_type": f.content_type}
                )
                f.seek(0)
            except Exception as e:
                print(f"[Attachment error] {e}")

    connection_pool = get_connection_pool(5, user=user)
    sent = failed = 0

    try:
        for chunk in batch_emails(emails, 50):
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = [
                    executor.submit(
                        send_email_single,
                        user,  # ✅ pass user
                        r,
                        subject,
                        body_html,
                        attachment_data,
                        job_id,
                        random.choice(connection_pool),
                        from_email,
                    )
                    for r in chunk
                ]

                for future in as_completed(futures):
                    try:
                        if future.result():
                            sent += 1
                        else:
                            failed += 1
                    except Exception as e:
                        failed += 1
                        print(f"[Thread error] {e}")

            # Sleep to avoid throttling
            time.sleep(5)

    finally:
        for conn in connection_pool:
            try:
                conn.close()
            except Exception:
                pass

    if job_id:
        data = get_progress(job_id)
        data["state"] = "SUCCESS"
        cache.set(f"progress:{job_id}", data, 3600)

    return {"sent": sent, "failed": failed}
