from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [("core", "0002_business_public_chat_enabled")]
    operations = [
        migrations.CreateModel(name="BusinessProfile", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("address", models.CharField(blank=True, max_length=250)),
            ("working_hours", models.CharField(blank=True, max_length=300)),
            ("delivery_info", models.TextField(blank=True)),
            ("payment_info", models.TextField(blank=True)),
            ("rules", models.TextField(blank=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("business", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="brain_profile", to="core.business")),
        ]),
        migrations.CreateModel(name="CatalogItem", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("kind", models.CharField(choices=[("service", "Услуга"), ("product", "Товар"), ("dish", "Блюдо"), ("other", "Другое")], default="service", max_length=20)),
            ("name", models.CharField(max_length=180)),
            ("description", models.TextField(blank=True)),
            ("price", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
            ("currency", models.CharField(default="KZT", max_length=3)),
            ("duration_minutes", models.PositiveIntegerField(blank=True, null=True)),
            ("is_available", models.BooleanField(default=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("business", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="catalog_items", to="core.business")),
        ], options={"ordering": ["name", "pk"]}),
        migrations.AddIndex(model_name="catalogitem", index=models.Index(fields=["business", "is_available"], name="brain_catalog_avail_idx")),
    ]
