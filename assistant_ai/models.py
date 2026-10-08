from django.db import models
from django.conf import settings
from core.models import Business
import uuid


class KnowledgeItem(models.Model):
    CATEGORY_CHOICES = [
        ("general", "Общая информация"),
        ("service", "Услуги"),
        ("price", "Цены"),
        ("schedule", "Расписание"),
        ("faq", "Частые вопросы"),
        ("policy", "Правила"),
    ]

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="knowledge_items"
    )

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default="general"
    )

    title = models.CharField(max_length=200)
    content = models.TextField()

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.business.name}: {self.title}"


class Conversation(models.Model):
    STATUS_CHOICES = [
        ("active", "Активный"),
        ("closed", "Закрытый"),
        ("human", "Передан сотруднику"),
    ]

    CHANNEL_CHOICES = [
        ("web", "Веб-сайт"),
        ("telegram", "Telegram"),
        ("whatsapp", "WhatsApp"),
        ("instagram", "Instagram"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="conversations"
    )

    customer_name = models.CharField(
        max_length=150,
        blank=True
    )

    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        default="web"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.business.name} | {self.customer_name or self.id}"


class Message(models.Model):
    ROLE_CHOICES = [
        ("customer", "Клиент"),
        ("assistant", "AI"),
        ("human", "Сотрудник"),
        ("system", "Система"),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )

    content = models.TextField()

    ai_provider = models.CharField(
        max_length=50,
        blank=True
    )

    tokens_used = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"

class Lead(models.Model):
    STATUS_CHOICES = [
        ("collecting", "Сбор данных"),
        ("new", "Новая"),
        ("confirmed", "Подтверждена"),
        ("cancelled", "Отменена"),
    ]

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="leads")
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="leads")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="collecting")
    service = models.CharField(max_length=200, blank=True)
    customer_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    requested_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.business.name}: {self.customer_name or 'Новая заявка'} ({self.status})"
