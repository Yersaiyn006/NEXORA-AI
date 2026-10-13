"""Conservative rule-based signals. No AI calls, no speculative revenue."""
import re
from collections import Counter
from django.db.models import Count
from assistant_ai.models import Conversation, Lead

INTEREST = re.compile(r"(?:\b(?:цена|цену|стоимость|стоит|сколько|прайс|записаться|запишите|запись|бронь|забронировать|услуг[аиу]|свободн(?:ое|ые)\s+время)\b|қанша|бағасы|жазыл)", re.I)
PRICE = re.compile(r"(?:\b(?:цена|цену|стоимость|стоит|сколько|прайс)\b|қанша|бағасы)", re.I)
BOOKING = re.compile(r"(?:\b(?:записаться|запишите|запись|бронь|забронировать)\b|жазыл)", re.I)


def sales_radar(business, include_playground=False):
    conversations = Conversation.objects.filter(business=business)
    if not include_playground:
        conversations = conversations.exclude(customer_name__startswith="Playground:")
    conversations = conversations.prefetch_related("messages", "leads").order_by("-updated_at")
    total = 0
    opportunities = []
    signals = Counter()
    with_lead = 0
    for conversation in conversations:
        total += 1
        leads = list(conversation.leads.all())
        if any(lead.status in ("new", "confirmed") for lead in leads):
            with_lead += 1
        customer_messages = [m.content for m in conversation.messages.all() if m.role == "customer"]
        matched = [m for m in customer_messages if INTEREST.search(m)]
        if not matched or leads:
            continue  # Existing or incomplete lead is not labelled as lost
        combined = " ".join(matched)
        reason = "Интерес к записи" if BOOKING.search(combined) else "Вопрос о цене" if PRICE.search(combined) else "Интерес к услуге"
        signals[reason] += 1
        opportunities.append({
            "id": conversation.id,
            "channel": conversation.get_channel_display(),
            "reason": reason,
            "excerpt": matched[-1][:180],
            "updated_at": conversation.updated_at,
            "is_playground": conversation.customer_name.startswith("Playground:"),
        })
    lead_qs = Lead.objects.filter(business=business)
    if not include_playground:
        lead_qs = lead_qs.exclude(conversation__customer_name__startswith="Playground:")
    statuses = dict(lead_qs.values_list("status").annotate(n=Count("id")))
    return {
        "total": total,
        "with_lead": with_lead,
        "conversion": round(with_lead * 100 / total, 1) if total else 0,
        "opportunities": opportunities[:100],
        "opportunity_count": len(opportunities),
        "new_leads": statuses.get("new", 0),
        "confirmed_leads": statuses.get("confirmed", 0),
        "cancelled_leads": statuses.get("cancelled", 0),
        "collecting_leads": statuses.get("collecting", 0),
        "top_signals": signals.most_common(3),
        "include_playground": include_playground,
    }
