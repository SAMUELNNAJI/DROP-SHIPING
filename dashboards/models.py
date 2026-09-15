from django.db import models

# Create your models here.

class SellerVerification(models.Model):
    STATUS_CHOICES = [
        ("unverified", "Unverified"),
        ("pending", "Under review"),
        ("verified", "Verified"),
        ("rejected", "Needs attention"),
    ]
    ID_CHOICES = [
        ("national_id", "National ID (NIN slip / card)"),
        ("passport", "International Passport"),
        ("drivers_license", "Driver's License"),
        ("voters_card", "Voter's Card"),
    ]
    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="seller_verification")
    full_name = models.CharField(max_length=120, default="")
    store_name = models.CharField(max_length=120, default="")
    phone = models.CharField(max_length=20, default="")
    address = models.CharField(max_length=255, default="")
    city = models.CharField(max_length=80, default="")
    country = models.CharField(max_length=80, default="Nigeria")
    id_type = models.CharField(max_length=20, choices=ID_CHOICES, default="national_id")
    id_number = models.CharField(max_length=60, default="")
    document = models.FileField(upload_to="seller_docs/", blank=True, null=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="unverified")
    reviewer_note = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "%s — %s" % (self.store_name, self.get_status_display())

