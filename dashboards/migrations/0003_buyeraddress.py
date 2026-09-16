from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("dashboards", "0002_wishlistitem")]
    operations = [migrations.CreateModel(name="BuyerAddress", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("label", models.CharField(default="Home", max_length=40)), ("recipient_name", models.CharField(max_length=120)), ("phone", models.CharField(max_length=30)), ("line1", models.CharField(max_length=160)), ("line2", models.CharField(blank=True, max_length=160)), ("city", models.CharField(max_length=80)), ("state", models.CharField(blank=True, max_length=80)), ("postal_code", models.CharField(blank=True, max_length=20)), ("country", models.CharField(default="Nigeria", max_length=80)), ("is_default", models.BooleanField(default=False)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("user", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="addresses", to=settings.AUTH_USER_MODEL))], options={"ordering": ["-is_default", "-updated_at"]})]
