"""Small-scale lexical retrieval; no vector service needed for this data volume."""
import json
import re
from .models import KnowledgeItem
from django.db.models import Q
from business_brain.models import CatalogItem, BusinessProfile

PHONE = re.compile(r"(?<!\d)(?:\+?7|8)[\s()\-]*\d(?:[\s()\-]*\d){9}(?!\d)")
EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")


def redact(value):
    return EMAIL.sub("[email скрыт]", PHONE.sub("[телефон скрыт]", value))


def words(text):
    return {w for w in re.findall(r"[^\W_]+", text.casefold()) if len(w) >= 3}


def ranked(rows, query):
    tokens = words(query)
    def score(row):
        title = words(row["title"])
        body = words(row["content"])
        return 4 * len(tokens & title) + len(tokens & body)
    return sorted(rows, key=lambda row: (-score(row), row["id"]))


def build_context(conversation, question, max_chars=24000):
    """Company facts have priority over bounded recent history; all queries are scoped."""
    business = conversation.business
    history = list(conversation.messages.exclude(role="system").order_by("-created_at", "-pk").values("role", "content")[:24])
    history.reverse()
    # send_message persists the customer question first; don't send it twice.
    if history and history[-1]["role"] == "customer" and history[-1]["content"] == question:
        history.pop()
    recent = " ".join(m["content"] for m in history[-4:])
    query = question + " " + recent
    profile = BusinessProfile.objects.filter(business=business).first()
    facts = {"business": {"name": business.name[:150], "industry": business.industry[:100], "description": business.description[:1500]},
             "profile": {field: getattr(profile, field)[:1200] for field in ("address", "working_hours", "delivery_info", "payment_info", "rules")} if profile else {},
             "catalog": [], "knowledge": [], "context_truncated": False}
    catalog_qs = CatalogItem.objects.filter(business=business).order_by("pk")
    knowledge_qs = KnowledgeItem.objects.filter(business=business, is_active=True).order_by("pk")
    def candidates(qs, fields):
        condition = Q()
        for token in sorted(words(query), key=lambda w: (-len(w), w))[:12]:
            for field in fields:
                condition |= Q(**{field + "__iregex": re.escape(token)})
        matched = list(qs.filter(condition)[:250]) if condition else []
        baseline = list(qs[:40])
        return list({row.pk: row for row in matched + baseline}.values())
    catalog = [{"id": item.pk, "title": item.name, "content": item.description[:900], "kind": item.kind,
                "price": str(item.price) if item.price is not None else None, "currency": item.currency,
                "available": item.is_available, "duration_minutes": item.duration_minutes}
               for item in candidates(catalog_qs, ("name", "description"))]
    knowledge = [{"id": row.pk, "title": row.title, "content": row.content[:1800], "category": row.category}
                 for row in candidates(knowledge_qs, ("title", "content"))]
    # Reserve space for recent turns and the latest question. Character budget is not a token count.
    facts_budget = max(4000, max_chars - 7000)
    catalog_limit = len(json.dumps(facts, ensure_ascii=False)) + int((facts_budget - len(json.dumps(facts, ensure_ascii=False))) * (0.6 if knowledge else 1.0))
    for target, rows in (("catalog", ranked(catalog, query)), ("knowledge", ranked(knowledge, query))):
        for row in rows[:40]:
            facts[target].append(row)
            if len(json.dumps(facts, ensure_ascii=False)) > (catalog_limit if target == "catalog" else facts_budget):
                facts[target].pop()
                facts["context_truncated"] = True
                break
        if len(rows) > len(facts[target]):
            facts["context_truncated"] = True
    if catalog_qs.count() > len(facts["catalog"]) or knowledge_qs.count() > len(facts["knowledge"]):
        facts["context_truncated"] = True
    # Business phone is a deliberately published company contact, not a customer's phone.
    facts["business"]["phone"] = business.phone[:30]
    names = list(conversation.leads.exclude(customer_name="").values_list("customer_name", flat=True))
    def clean_customer(text):
        text = redact(text)
        for name in names:
            text = re.sub(r"(?<!\w)" + re.escape(name) + r"(?!\w)", "[имя скрыто]", text, flags=re.I)
        return text
    dialogue = [{"role": "model" if m["role"] == "assistant" else "user", "text": clean_customer(m["content"][:1200])} for m in history if m["role"] in ("customer", "assistant")]
    latest = clean_customer(question[:2000])
    while dialogue and len(json.dumps(facts, ensure_ascii=False)) + sum(len(m["text"]) for m in dialogue) + len(latest) > max_chars:
        dialogue.pop(0)
    return facts, dialogue, latest
