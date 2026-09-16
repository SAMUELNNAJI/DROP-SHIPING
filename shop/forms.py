from django import forms

from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            "name", "store_name", "category", "price", "old_price",
            "stock", "status", "badge", "description", "image", "image_url",
        )
        widgets = {
            "name": forms.TextInput(attrs={"class": "ff-input", "placeholder": "e.g. Wireless Headphones Pro", "required": True}),
            "store_name": forms.TextInput(attrs={"class": "ff-input", "placeholder": "e.g. TechVault Store"}),
            "category": forms.Select(attrs={"class": "ff-input"}),
            "price": forms.NumberInput(attrs={"class": "ff-input", "placeholder": "69.99", "step": "0.01", "min": "0", "required": True}),
            "old_price": forms.NumberInput(attrs={"class": "ff-input", "placeholder": "89.99 (optional)", "step": "0.01", "min": "0"}),
            "stock": forms.NumberInput(attrs={"class": "ff-input", "placeholder": "100", "min": "0", "required": True}),
            "status": forms.Select(attrs={"class": "ff-input"}),
            "badge": forms.Select(attrs={"class": "ff-input"}),
            "description": forms.Textarea(attrs={"class": "ff-input", "rows": 3, "placeholder": "Key features, materials, delivery notes..."}),
            "image": forms.ClearableFileInput(attrs={"class": "ff-input", "accept": "image/*"}),
            "image_url": forms.URLInput(attrs={"class": "ff-input", "placeholder": "https://... (optional image link)"}),
        }
        labels = {
            "name": "Product name",
            "store_name": "Store / brand name",
            "old_price": "Old price (USD) — for SALE badge",
            "image": "Product photo (upload)",
            "image_url": "…or paste an image URL",
        }

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price is not None and price <= 0:
            raise forms.ValidationError("Price must be greater than zero.")
        return price

    def clean(self):
        cleaned = super().clean()
        price = cleaned.get("price")
        old = cleaned.get("old_price")
        image = cleaned.get("image")
        image_url = (cleaned.get("image_url") or "").strip()
        if old is not None and price is not None and old <= price:
            self.add_error("old_price", "Old price must be higher than the selling price (or leave it empty).")
        if not image and not image_url and not (self.instance and self.instance.pk and (self.instance.image or self.instance.image_url)):
            raise forms.ValidationError("Add a product photo or paste an image URL so it fits the shop card.")
        return cleaned
