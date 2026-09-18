from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("dashboards", "0006_boostplan_boostorder_cartitem")]

    operations = [
        migrations.AddField(
            model_name="order",
            name="delivery_note",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="order",
            name="dispute_reason",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="order",
            name="disputed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(choices=[("pending", "Pending"), ("in_transit", "In Transit"), ("delivered", "Delivered"), ("confirmed", "Confirmed"), ("refunded", "Refunded"), ("disputed", "Delivery disputed"), ("cancelled", "Cancelled")], default="pending", max_length=12),
        ),
        migrations.CreateModel(
            name="OrderTrackingEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(max_length=30)),
                ("message", models.CharField(max_length=280)),
                ("location", models.CharField(blank=True, default="", max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("order", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="tracking_events", to="dashboards.order")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
