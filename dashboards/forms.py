from django import forms
from .models import SellerVerification


class SellerVerificationForm(forms.ModelForm):
    class Meta:
        model = SellerVerification
        fields = (
            "full_name", "store_name", "phone", "address",
            "city", "country", "id_type", "id_number", "document",
        )
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "ff-input", "placeholder": "e.g. Adaeze Okafor"}),
            "store_name": forms.TextInput(attrs={"class": "ff-input", "placeholder": "e.g. TechVault Store"}),
            "phone": forms.TextInput(attrs={"class": "ff-input", "placeholder": "+234 800 000 0000"}),
            "address": forms.TextInput(attrs={"class": "ff-input", "placeholder": "Street address"}),
            "city": forms.TextInput(attrs={"class": "ff-input", "placeholder": "Lagos"}),
            "country": forms.TextInput(attrs={"class": "ff-input", "placeholder": "Nigeria"}),
            "id_type": forms.Select(attrs={"class": "ff-input"}),
            "id_number": forms.TextInput(attrs={"class": "ff-input", "placeholder": "ID number"}),
            "document": forms.ClearableFileInput(attrs={"class": "ff-input"}),
        }
        labels = {
            "id_type": "Government ID type",
            "id_number": "ID number",
            "document": "Upload ID document (photo / scan / PDF)",
        }
