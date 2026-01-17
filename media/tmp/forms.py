from django import forms

class BulkEmailForm(forms.Form):
    recipients = forms.CharField(widget=forms.Textarea(attrs={"rows":6}), help_text="Paste emails comma/space/newline separated (up to 3000).")
    subject = forms.CharField(max_length=255)
    body = forms.CharField(widget=forms.Textarea(attrs={"rows":12}), help_text="HTML allowed")
