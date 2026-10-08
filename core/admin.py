from django.contrib import admin
from .models import Business, Membership


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "industry",
        "phone",
        "created_at"
    )

    search_fields = (
        "name",
        "industry"
    )

    readonly_fields = ("created_at",)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "business",
        "role"
    )

    list_filter = ("role",)