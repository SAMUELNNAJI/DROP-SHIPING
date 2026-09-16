from django import forms
from .models import BuyerAddress, BoostPlan, SellerPayoutMethod, SellerVerification


class BoostPlanForm(forms.ModelForm):
    class Meta:
        model  = BoostPlan
        fields = ("name", "price", "duration_days", "description", "is_active")
        widgets = {
            "name":          forms.TextInput(attrs={"class": "ff-input", "placeholder": "e.g. Pro Feature"}),
            "price":         forms.NumberInput(attrs={"class": "ff-input", "placeholder": "29.99", "step": "0.01", "min": "0"}),
            "duration_days": forms.NumberInput(attrs={"class": "ff-input", "placeholder": "7", "min": "1"}),
            "description":   forms.TextInput(attrs={"class": "ff-input", "placeholder": "Short benefit line (~8,000 extra views)"}),
            "is_active":     forms.CheckboxInput(attrs={"class": "ff-check"}),
        }
        labels = {
            "name":          "Plan name",
            "price":         "Price (USD)",
            "duration_days": "Duration (days)",
            "description":   "Short description",
            "is_active":     "Active (visible to sellers)",
        }


class SellerPayoutMethodForm(forms.ModelForm):
    class Meta:
        model = SellerPayoutMethod
        fields = ("method", "bank_name", "account_number", "account_name", "currency", "wallet_address", "is_default")
        widgets = {
            "method":          forms.Select(attrs={"class": "ff-input", "id": "pmMethod"}),
            "bank_name":       forms.TextInput(attrs={"class": "ff-input", "placeholder": "e.g. Guaranty Trust Bank"}),
            "account_number":  forms.TextInput(attrs={"class": "ff-input", "placeholder": "0123456789"}),
            "account_name":    forms.TextInput(attrs={"class": "ff-input", "placeholder": "Account holder name"}),
            "currency":        forms.Select(attrs={"class": "ff-input"}),
            "wallet_address":  forms.TextInput(attrs={"class": "ff-input", "placeholder": "Pi username or PayPal email"}),
            "is_default":      forms.CheckboxInput(attrs={"class": "ff-check"}),
        }
        labels = {
            "method":         "Payment method",
            "bank_name":      "Bank name",
            "account_number": "Account number",
            "account_name":   "Account name",
            "currency":       "Currency",
            "wallet_address": "Pi username / PayPal email",
            "is_default":     "Set as default payout method",
        }


class BuyerAddressForm(forms.ModelForm):
    class Meta:
        model = BuyerAddress
        fields = ("label", "recipient_name", "phone", "line1", "line2", "city", "state", "postal_code", "country", "is_default")
        widgets = {
            "label":          forms.TextInput(attrs={"class": "ff-input", "placeholder": "e.g. Home, Office"}),
            "recipient_name": forms.TextInput(attrs={"class": "ff-input", "placeholder": "Full name of recipient"}),
            "phone":          forms.TextInput(attrs={"class": "ff-input", "placeholder": "+234 800 000 0000"}),
            "line1":          forms.TextInput(attrs={"class": "ff-input", "placeholder": "Street address"}),
            "line2":          forms.TextInput(attrs={"class": "ff-input", "placeholder": "Apt, suite, unit (optional)"}),
            "city":           forms.TextInput(attrs={"class": "ff-input", "placeholder": "City"}),
            "state":          forms.TextInput(attrs={"class": "ff-input", "placeholder": "State / Province"}),
            "postal_code":    forms.TextInput(attrs={"class": "ff-input", "placeholder": "Postal code"}),
            "country":        forms.TextInput(attrs={"class": "ff-input", "placeholder": "Country"}),
            "is_default":     forms.CheckboxInput(attrs={"class": "ff-check"}),
        }


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
