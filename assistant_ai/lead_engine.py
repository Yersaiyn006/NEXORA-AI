"""Простой детерминированный сбор заявок без платных AI API."""
import re
from datetime import datetime, timedelta, time
from django.utils import timezone
from .models import Lead

INTENT = re.compile(r"\b(записат(?:ься|ь|ся)?|запишите|запись|забронировать|бронь)\b", re.I)
PHONE = re.compile(r"(?:\+?7|8)[\s()\-]*\d(?:[\s()\-]*\d){9}\b")
DATE = re.compile(r"\b(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})\b")
TIME = re.compile(r"\b(?:в\s*)?([01]?\d|2[0-3]):([0-5]\d)\b")


def parse_datetime(message):
    today = timezone.localdate()
    text = message.lower()
    if "послезавтра" in text:
        day = today + timedelta(days=2)
    elif "завтра" in text:
        day = today + timedelta(days=1)
    elif "сегодня" in text:
        day = today
    else:
        match = DATE.search(message)
        if not match:
            return None
        value = match.group(1)
        try:
            day = datetime.strptime(value, "%d.%m.%Y" if "." in value else "%Y-%m-%d").date()
        except ValueError:
            return None
    match = TIME.search(message)
    if not match:
        return None
    hour, minute = map(int, match.groups())
    dt = timezone.make_aware(datetime.combine(day, time(hour, minute)), timezone.get_current_timezone())
    return dt if dt > timezone.now() else None


def respond_to_lead(conversation, message):
    """Возвращает ответ для заявки или None, если это обычный вопрос."""
    text = message.strip()
    lead = conversation.leads.filter(status="collecting").order_by("-id").first()
    if lead is None:
        if not INTENT.search(text):
            return None
        lead = Lead.objects.create(business=conversation.business, conversation=conversation)
        # Запрос вида «запишите на мужскую стрижку» сохраняет услугу.
        service = re.search(r"\bна\s+(.+?)(?:\s+(?:завтра|послезавтра|сегодня|\d{2}\.\d{2}\.\d{4})\b|$)", text, re.I)
        if service:
            lead.service = service.group(1).strip(" .,!?")[:200]
            lead.save(update_fields=["service", "updated_at"])
        if not lead.service:
            return "На какую услугу хотите записаться? Для отмены напишите «отмена заявки»."
        return "Как вас зовут?"

    if text.lower() in {"отмена заявки", "отменить заявку", "стоп заявка"}:
        lead.status = "cancelled"
        lead.save(update_fields=["status", "updated_at"])
        return "Сбор заявки отменён."

    if not lead.service:
        if len(text) < 2 or len(text) > 200:
            return "Напишите название услуги (до 200 символов)."
        lead.service = text
        lead.save(update_fields=["service", "updated_at"])
        return "Как вас зовут?"

    if not lead.customer_name:
        if not re.fullmatch(r"[\w\s\-]{2,150}", text, re.UNICODE) or any(ch.isdigit() for ch in text):
            return "Укажите имя буквами (от 2 до 150 символов)."
        lead.customer_name = text
        lead.save(update_fields=["customer_name", "updated_at"])
        return "Оставьте номер телефона в формате +7XXXXXXXXXX. Мы используем его для связи по заявке."

    if not lead.phone:
        match = PHONE.fullmatch(text)
        if not match:
            return "Введите номер телефона Казахстана в формате +7XXXXXXXXXX."
        digits = re.sub(r"\D", "", text)
        lead.phone = "+7" + digits[1:]
        lead.save(update_fields=["phone", "updated_at"])
        return "На какую дату и время хотите записаться? Например: завтра в 15:00 или 15.10.2026 15:00."

    dt = parse_datetime(text)
    if not dt:
        return "Не удалось определить будущую дату и время. Напишите, например: завтра в 15:00 или 15.10.2026 15:00."
    lead.requested_at = dt
    lead.status = "new"
    lead.save(update_fields=["requested_at", "status", "updated_at"])
    return (
        f"Заявка №{lead.pk} создана! Услуга: {lead.service}. "
        f"Клиент: {lead.customer_name}. Желаемое время: "
        f"{timezone.localtime(dt):%d.%m.%Y %H:%M}. "
        "Это запрос на запись, а не подтверждённое бронирование. "
        "Сотрудник должен проверить доступность времени и подтвердить заявку."
    )
