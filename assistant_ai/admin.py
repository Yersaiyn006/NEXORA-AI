from django.contrib import admin
from .models import KnowledgeItem, Conversation, Message


@admin.register(KnowledgeItem)
class KnowledgeItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "business",
        "category",
        "is_active",
        "updated_at",
    )

    list_filter = ("category", "is_active", "business")
    search_fields = ("title", "content")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "business",
        "customer_name",
        "channel",
        "status",
        "created_at",
    )

    list_filter = ("business", "channel", "status")
    search_fields = ("customer_name",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "conversation",
        "role",
        "ai_provider",
        "tokens_used",
        "created_at",
    )

    list_filter = ("role", "ai_provider")
    search_fields = ("content",)