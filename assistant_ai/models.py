from django.db import models
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

    initial_turn_id = models.UUIDField(null=True, blank=True)
    public_session_key = models.CharField(max_length=64, null=True, blank=True)
    processing_token = models.UUIDField(null=True, blank=True)
    processing_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["business", "public_session_key"], name="unique_public_business_session"),
                       models.UniqueConstraint(fields=["business", "customer_name", "initial_turn_id"], name="unique_playground_initial_turn")]

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
    turn_id = models.UUIDField(null=True, blank=True)
    # Server action receipt: survives an interrupted assistant-message write.
    request_response = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["conversation", "role", "turn_id"], name="unique_conversation_role_turn")]

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

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.conversation_id and self.business_id and self.conversation.business_id != self.business_id:
            raise ValidationError("Заявка и диалог должны принадлежать одной компании.")

    def __str__(self):
        return f"{self.business.name}: {self.customer_name or 'Новая заявка'} ({self.status})"


class RateLimitBucket(models.Model):
    """Shared fixed-window counters. Keys contain HMAC digests, not client IPs."""
    key = models.CharField(max_length=120, unique=True)
    count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)
