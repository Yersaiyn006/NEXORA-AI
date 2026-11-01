from django.core.exceptions import ValidationError
"""Public customer chat. Business and conversation identity are server-authorized."""
from django.db import OperationalError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.cache import never_cache
from core.models import Business
from assistant_ai.models import Conversation
from assistant_ai.universal_engine import respond
from assistant_ai.rate_limits import public_allow, private_key
from assistant_ai.turns import TurnError, parse_turn_id, process_turn, completed_turn


def enabled_business(slug):
    return get_object_or_404(Business, slug=slug, public_chat_enabled=True)


def session_conversation(request, business):
    if not request.session.session_key:
        request.session.create()
    field = f"public_chat_{business.pk}"
    conversation_id = request.session.get(field)
    # Never persist the raw Django session identifier in customer-facing data.
    safe_customer = f"Public:{private_key(request.session.session_key)}"
    conversation = None
    if conversation_id:
        try:
            conversation = Conversation.objects.filter(
                pk=conversation_id, business=business, channel="web",
                customer_name__in=[safe_customer, f"Public:{request.session.session_key}"],
            ).first()
        except (ValueError, TypeError, ValidationError):
            pass
    if conversation is None:
        conversation = Conversation.objects.filter(business=business, public_session_key=private_key(request.session.session_key)).first()
    return conversation, field


@never_cache
@xframe_options_exempt
@require_GET
def chat_page(request, slug):
    business = enabled_business(slug)
    conversation, _ = session_conversation(request, business)
    history = []
    if conversation:
        history = list(conversation.messages.order_by("-created_at", "-pk").values("role", "content")[:150])
        history.reverse()
    return render(request, "public_chat/chat.html", {"business": business, "history": history})


@never_cache
@require_POST
def chat_send(request, slug):
    business = enabled_business(slug)
    question = request.POST.get("message", "").strip()
    if not question or len(question) > 1000:
        return JsonResponse({"error": "Введите сообщение до 1000 символов."}, status=400)
    try:
        turn_id = parse_turn_id(request.POST.get("turn_id"))
        conversation, field = session_conversation(request, business)
        if conversation:
            answer = completed_turn(conversation, question, turn_id)
            if answer:
                return JsonResponse({"answer": answer.content, "source": answer.ai_provider, "turn_id": str(turn_id)})
        if not public_allow(request, business):
            response = JsonResponse({"error": "Лимит сообщений исчерпан. Попробуйте позже."}, status=429)
            response["Retry-After"] = "60"
            return response
        if conversation is None:
            conversation, _ = Conversation.objects.get_or_create(
                business=business, public_session_key=private_key(request.session.session_key),
                defaults={"channel": "web", "customer_name": f"Public:{private_key(request.session.session_key)}"},
            )
            request.session[field] = str(conversation.pk)
        answer = process_turn(conversation, question, turn_id, respond)
        return JsonResponse({"answer": answer.content, "source": answer.ai_provider, "turn_id": str(turn_id)})
    except TurnError as exc:
        return JsonResponse({"error": exc.message}, status=exc.status)
    except OperationalError:
        return JsonResponse({"error": "Сервис занят. Повторите отправку через несколько секунд."}, status=503)
