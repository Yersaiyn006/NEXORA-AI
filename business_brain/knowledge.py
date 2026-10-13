"""Tenant-scoped structured facts. Never treat client-provided text as system instructions."""
import re
from .models import CatalogItem, BusinessProfile


def catalog_facts(business, limit=30):
    items = CatalogItem.objects.filter(business=business).order_by("name")[:limit]
    result = []
    for item in items:
        parts = [item.get_kind_display(), item.name, "доступно" if item.is_available else "недоступно"]
        if item.price is not None:
            parts.append(f"цена {item.price} {item.currency}")
        if item.duration_minutes:
            parts.append(f"длительность {item.duration_minutes} минут")
        if item.description:
            parts.append(item.description[:450])
        result.append("; ".join(parts))
    return result


def profile_facts(business):
    profile = BusinessProfile.objects.filter(business=business).first()
    if not profile:
        return []
    return [f"{label}: {getattr(profile, field)[:500]}" for label, field in [
        ("Адрес", "address"), ("График работы", "working_hours"),
        ("Доставка", "delivery_info"), ("Оплата", "payment_info"), ("Правила", "rules")
    ] if getattr(profile, field)]


def catalog_answer(business, question):
    q = question.casefold().strip()
    items = list(CatalogItem.objects.filter(business=business).order_by("name")[:80])
    if not items:
        return None
    if re.search(r"(?:какие|какой|что у вас|покажи|список|каталог|меню|прайс|ассортимент|услуги|товары|блюда|не бар|қандай|мәзір)", q):
        return "Каталог компании:\n" + "\n".join(
            f"• {i.name} — {i.price} {i.currency}" if i.price is not None and i.is_available else
            f"• {i.name} — {'цена уточняется' if i.is_available else 'сейчас недоступно'}"
            for i in items[:25]
        )
    matches = [i for i in items if i.name.casefold() in q or (len(q) >= 4 and q in i.name.casefold())]
    if len(matches) == 1:
        i = matches[0]
        price = f"{i.price} {i.currency}" if i.price is not None else "цена уточняется"
        return f"{i.name}: {price}. {'Доступно' if i.is_available else 'Сейчас недоступно'}. {i.description[:400]}".strip()
    return None
