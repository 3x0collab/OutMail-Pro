from django import forms
from .models import SMTPConfig


class BulkEmailForm(forms.Form):
    recipients = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 6}),
        help_text="Paste emails comma/space/newline separated (up to 3000).",
    )
    subject = forms.CharField(max_length=255)
    body = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 12}),
        help_text="HTML allowed",
    )


class SMTPConfigForm(forms.ModelForm):
    """
    Form for users to enter or update their SMTP login info.
    """
    password = forms.CharField(
        widget=forms.PasswordInput(render_value=True),
        required=False,
        help_text="Leave blank to keep your current password.",
    )

    class Meta:
        model = SMTPConfig
        fields = [
            "host",
            "port",
            "username",
            "password",
            "use_ssl",
            "use_tls",
            "default_from",   # ✅ Correct field name
            "display_name",
        ]
        widgets = {
            "password": forms.PasswordInput(render_value=True),
        }