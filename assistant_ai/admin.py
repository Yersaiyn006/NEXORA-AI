from django.contrib import admin
from .models import KnowledgeItem, Conversation, Message, Lead


@admin.register(KnowledgeItem)
class KnowledgeItemAdmin(admin.ModelAdmin):
    list_display = ("title", "business", "category", "is_active")
    list_filter = ("business", "category", "is_active")
    search_fields = ("title", "content")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "business", "channel", "status", "created_at")
    list_filter = ("business", "channel", "status")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "role", "ai_provider", "created_at")
    list_filter = ("role", "ai_provider")


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("id", "business", "customer_name", "service", "requested_at", "status")
    list_filter = ("business", "status")
    search_fields = ("customer_name", "phone", "service")
