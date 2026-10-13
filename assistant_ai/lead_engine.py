"""Простой детерминированный сбор заявок без платных AI API."""
import re
from datetime import datetime, timedelta, time
from django.utils import timezone
from .models import Lead
from .intent_engine import is_booking, is_cancel
from .universal_requests import wants_request, extract_subject

INTENT = re.compile(r"\b(записат(?:ься|ь|ся)?|запишите|запись|забронировать|бронь)\b", re.I)
PHONE = re.compile(r"(?:\+?7|8)[\s()\-]*\d(?:[\s()\-]*\d){9}\b")
DATE = re.compile(r"\b(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})\b")
TIME = re.compile(r"\b(?:в\s*)?([01]?\d|2[0-3]):([0-5]\d)\b")
WEEKDAYS = {"понедельник": 0, "вторник": 1, "среду": 2, "среда": 2, "четверг": 3, "пятницу": 4, "пятница": 4, "субботу": 5, "суббота": 5, "воскресенье": 6, "дүйсенбі": 0, "сейсенбі": 1, "сәрсенбі": 2, "бейсенбі": 3, "жұма": 4, "сенбі": 5, "жексенбі": 6}


def parse_datetime(message):
    today = timezone.localdate()
    text = message.lower()
    if "послезавтра" in text or "бүрсігүні" in text:
        day = today + timedelta(days=2)
    elif "завтра" in text or "ертең" in text:
        day = today + timedelta(days=1)
    elif "сегодня" in text or "бүгін" in text:
        day = today
    elif any(word in text for word in WEEKDAYS):
        weekday = next(value for word, value in WEEKDAYS.items() if word in text)
        delta = (weekday - today.weekday()) % 7
        day = today + timedelta(days=delta or 7)
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
        if not (is_booking(text) or wants_request(text)):
            return None
        lead = Lead.objects.create(business=conversation.business, conversation=conversation)
        # Извлекаем услугу только из явной конструкции «на ...».
        service = extract_subject(text)
        if service:
            lead.service = service[:200]
            lead.save(update_fields=["service", "updated_at"])
        if not lead.service:
            return "Что именно вас интересует? Укажите товар, услугу или детали запроса. Для отмены напишите «отмена заявки»."
        return "Как вас зовут?"

    if is_cancel(text):
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
        return "Когда вам удобно или когда нужен заказ? Укажите дату и время, например: завтра в 15:00. Если точное время не важно, напишите «без времени»."

    no_time = text.casefold() in ("без времени", "не важно", "неважно", "когда угодно", "уақыт маңызды емес")
    dt = None if no_time else parse_datetime(text)
    if not dt and not no_time:
        return "Не удалось определить будущую дату и время. Напишите, например: завтра в 15:00 или 15.10.2026 15:00."
    lead.requested_at = dt
    lead.status = "new"
    lead.save(update_fields=["requested_at", "status", "updated_at"])
    return (
        f"Заявка №{lead.pk} создана! Запрос: {lead.service}. "
        f"Клиент: {lead.customer_name}. Желаемое время: "
        f"{timezone.localtime(dt).strftime('%d.%m.%Y %H:%M') if dt else 'не указано'}. "
        "Это запрос клиента, а не подтверждённый заказ или бронирование. "
        "Сотрудник должен проверить доступность времени и подтвердить заявку."
    )
