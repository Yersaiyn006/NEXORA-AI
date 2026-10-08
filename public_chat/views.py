"""Public customer chat. Never accepts business_id or conversation_id from clients."""
from django.core.cache import cache
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from core.models import Business
from assistant_ai.models import Conversation, Message
from assistant_ai.services import find_answer
from assistant_ai.lead_engine import respond_to_lead


def enabled_business(slug):
    return get_object_or_404(Business, slug=slug, public_chat_enabled=True)


def session_conversation(request, business):
    """Only the server-side session chooses a conversation."""
    if not request.session.session_key:
        request.session.create()
    key = f"public_chat_{business.pk}"
    conversation_id = request.session.get(key)
    conversation = None
    if conversation_id:
        conversation = Conversation.objects.filter(
            pk=conversation_id, business=business, channel="web",
            customer_name=f"Public:{request.session.session_key}",
        ).first()
    return conversation, key


@require_GET
def chat_page(request, slug):
    business = enabled_business(slug)
    conversation, _ = session_conversation(request, business)
    messages = []
    if conversation:
        messages = list(conversation.messages.order_by("created_at", "pk").values("role", "content")[:150])
    return render(request, "public_chat/chat.html", {"business": business, "history": messages})


@require_POST
def chat_send(request, slug):
    business = enabled_business(slug)
    question = request.POST.get("message", "").strip()
    if not question or len(question) > 1000:
        return JsonResponse({"error": "Введите сообщение до 1000 символов."}, status=400)

    # Development throttling: cache is per-process; production requires shared Redis + edge protection.
    if not request.session.session_key:
        request.session.create()
    key = f"public_limit:{request.session.session_key}"
    count = cache.get(key, 0)
    if count >= 15:
        return JsonResponse({"error": "Слишком много сообщений. Попробуйте через минуту."}, status=429)
    cache.set(key, count + 1, 60)

    with transaction.atomic():
        conversation, session_field = session_conversation(request, business)
        if conversation is None:
            conversation = Conversation.objects.create(
                business=business, channel="web",
                customer_name=f"Public:{request.session.session_key}",
            )
            request.session[session_field] = str(conversation.pk)
        if conversation.status != "active":
            return JsonResponse({"error": "Этот диалог завершён."}, status=400)
        if conversation.messages.filter(role="customer").count() >= 100:
            return JsonResponse({"error": "Лимит сообщений в этом диалоге исчерпан."}, status=429)
        Message.objects.create(conversation=conversation, role="customer", content=question)
        answer = respond_to_lead(conversation, question)
        source = "lead_engine" if answer is not None else "knowledge_base"
        if answer is None:
            answer = find_answer(business, question)
        if not answer:
            source = "fallback"
            answer = "Пока не могу точно ответить. Пожалуйста, свяжитесь с сотрудником компании."
        Message.objects.create(conversation=conversation, role="assistant", content=answer, ai_provider=source)
        Conversation.objects.filter(pk=conversation.pk).update(updated_at=timezone.now())
    return JsonResponse({"answer": answer, "source": source})
