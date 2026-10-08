from django.db import models
from django.conf import settings
from django.utils.text import slugify
import uuid


class Business(models.Model):
    name = models.CharField(max_length=150)

    slug = models.SlugField(
        max_length=180,
        unique=True,
        blank=True
    )

    description = models.TextField(blank=True)

    industry = models.CharField(
        max_length=100,
        blank=True
    )

    phone = models.CharField(
        max_length=30,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = (
                slugify(self.name, allow_unicode=True)[:120]
                + "-"
                + uuid.uuid4().hex[:8]
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Membership(models.Model):

    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("admin", "Admin"),
        ("staff", "Staff"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships"
    )

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="memberships"
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="staff"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "business"],
                name="unique_business_member"
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.business}"