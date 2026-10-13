"""Serialize one conversation without holding a DB transaction during network IO."""
import uuid
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .models import Conversation, Message


class TurnError(Exception):
    def __init__(self, message, status=409):
        self.message, self.status = message, status
        super().__init__(message)


def parse_turn_id(raw):
    try:
        return uuid.UUID(raw) if raw else uuid.uuid4()
    except (ValueError, TypeError, AttributeError):
        raise TurnError("Некорректный идентификатор сообщения.", 400)


def completed_turn(conversation, question, turn_id):
    customer = conversation.messages.filter(role="customer", turn_id=turn_id).first()
    if customer and customer.content != question:
        raise TurnError("Этот идентификатор уже использован для другого сообщения.")
    return conversation.messages.filter(role="assistant", turn_id=turn_id).first()


def process_turn(conversation, question, turn_id, responder):
    answer = completed_turn(conversation, question, turn_id)
    if answer:
        return answer
    now = timezone.now()
    token = uuid.uuid4()
    # Longer than the bounded Gemini timeout; late workers cannot commit an answer.
    ttl = max(90, settings.NEXORA_AI_TIMEOUT_MS // 1000 + 60)
    acquired = Conversation.objects.filter(pk=conversation.pk, status="active").filter(
        Q(processing_until__isnull=True) | Q(processing_until__lte=now)
    ).update(processing_token=token, processing_until=now + timedelta(seconds=ttl))
    if not acquired:
        raise TurnError("Диалог занят или завершён. Дождитесь ответа и попробуйте снова.")
    conversation._turn_token = token
    conversation._turn_id = turn_id
    try:
        # Recheck after obtaining the lease: a previous worker may have just completed.
        answer = completed_turn(conversation, question, turn_id)
        if answer:
            return answer
        if not conversation.messages.filter(role="customer", turn_id=turn_id).exists():
            if conversation.messages.filter(role="customer").count() >= settings.NEXORA_CONVERSATION_MAX_TURNS:
                raise TurnError("Лимит сообщений в этом диалоге исчерпан.", 429)
            Message.objects.create(conversation=conversation, role="customer", content=question, turn_id=turn_id)
        result = responder(conversation, question)
        if not result or not result.answer:
            raise TurnError("Не удалось сформировать ответ. Повторите отправку.", 503)
        with transaction.atomic():
            owned = Conversation.objects.filter(pk=conversation.pk, processing_token=token).update(updated_at=timezone.now())
            if not owned:
                raise TurnError("Запрос завершился слишком поздно. Повторите отправку.", 503)
            answer = Message.objects.create(
                conversation=conversation, role="assistant", content=result.answer,
                ai_provider=result.source, tokens_used=getattr(result, "tokens_used", 0), turn_id=turn_id,
            )
        return answer
    finally:
        Conversation.objects.filter(pk=conversation.pk, processing_token=token).update(processing_token=None, processing_until=None)
        conversation._turn_token = None
        conversation._turn_id = None
