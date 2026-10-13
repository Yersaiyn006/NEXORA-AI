from django.db import models
from core.models import Business


class BusinessProfile(models.Model):
    business = models.OneToOneField(Business, on_delete=models.CASCADE, related_name="brain_profile")
    address = models.CharField(max_length=250, blank=True)
    working_hours = models.CharField(max_length=300, blank=True)
    delivery_info = models.TextField(blank=True)
    payment_info = models.TextField(blank=True)
    rules = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class CatalogItem(models.Model):
    KINDS = [("service", "Услуга"), ("product", "Товар"), ("dish", "Блюдо"), ("other", "Другое")]
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="catalog_items")
    kind = models.CharField(max_length=20, choices=KINDS, default="service")
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="KZT")
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "pk"]
        indexes = [models.Index(fields=["business", "is_available"], name="brain_catalog_avail_idx")]

    def __str__(self):
        return f"{self.business.name}: {self.name}"
