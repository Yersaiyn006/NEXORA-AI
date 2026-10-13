from django.core.exceptions import ValidationError

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max, OuterRef, Subquery
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from core.models import Membership
from .models import Conversation, Message
from .universal_engine import respond


# Проверяем доступ пользователя к диалогам компании
def user_conversations(request, business_id):
    allowed_businesses = Membership.objects.filter(
        user=request.user
    ).values("business_id")

    return Conversation.objects.filter(
        business_id__in=allowed_businesses,
        business_id=business_id,
        channel="web",
        customer_name=f"Playground:{request.user.pk}",
    )


# Главная страница AI Playground
@login_required
def playground(request):
    memberships = (
        Membership.objects
        .filter(user=request.user)
        .select_related("business")
        .order_by("business__name")
    )

    business_id = request.GET.get("business")

    if business_id and (not business_id.isascii() or not business_id.isdigit() or len(business_id) > 18):
        from django.http import Http404
        raise Http404
    if business_id:
        membership = get_object_or_404(
            memberships,
            business_id=business_id
        )
    else:
        membership = memberships.first()

    business = membership.business if membership else None

    return render(
        request,
        "assistant_ai/playground.html",
        {
            "business": business,
            "memberships": memberships,
        },
    )


# Получение списка прошлых диалогов
@login_required
@require_GET
def conversation_list(request):
    business_id = request.GET.get("business_id", "")

    if not business_id.isascii() or not business_id.isdigit() or len(business_id) > 18:
        return JsonResponse(
            {"error": "Некорректная компания."},
            status=400
        )

    get_object_or_404(
        Membership,
        user=request.user,
        business_id=business_id,
    )

    search = request.GET.get("q", "").strip()[:100]

    conversations = user_conversations(
        request,
        business_id
    ).annotate(
        last_message_at=Max("messages__created_at"),
        first_customer=Subquery(Message.objects.filter(conversation_id=OuterRef("pk"), role="customer").order_by("created_at", "pk").values("content")[:1]),
    )

    if search:
        conversations = conversations.filter(
            messages__content__icontains=search
        ).distinct()

    conversations = conversations.order_by(
        "-last_message_at",
        "-created_at"
    )[:100]

    results = []

    for conversation in conversations:
        title = (conversation.first_customer or "Новый диалог")[:65]

        results.append({
            "id": str(conversation.id),
            "title": title,
            "created_at": conversation.created_at.isoformat(),
            "status": conversation.status,
        })

    return JsonResponse({
        "conversations": results
    })


# Загрузка сообщений выбранного диалога
@login_required
@require_GET
def conversation_detail(request, conversation_id):
    business_id = request.GET.get("business_id", "")

    if not business_id.isascii() or not business_id.isdigit() or len(business_id) > 18:
        return JsonResponse(
            {"error": "Некорректная компания."},
            status=400
        )

    conversation = get_object_or_404(
        user_conversations(request, business_id),
        id=conversation_id,
    )

    messages = conversation.messages.order_by(
        "created_at",
        "id"
    )

    results = []

    for message in messages:
        results.append({
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
        })

    return JsonResponse({
        "id": str(conversation.id),
        "status": conversation.status,
        "messages": results,
    })


# Удаление диалога и его сообщений
@login_required
@require_POST
def conversation_delete(request, conversation_id):
    business_id = request.POST.get("business_id", "")

    if not business_id.isascii() or not business_id.isdigit() or len(business_id) > 18:
        return JsonResponse(
            {"error": "Некорректная компания."},
            status=400
        )

    conversation = get_object_or_404(
        user_conversations(request, business_id),
        id=conversation_id,
    )

    from django.db.models import F
    with transaction.atomic():
        Conversation.objects.filter(pk=conversation.pk).update(status=F("status"))
        conversation.refresh_from_db()
        if conversation.processing_until and conversation.processing_until > timezone.now():
            return JsonResponse({"error": "Дождитесь завершения ответа перед удалением диалога."}, status=409)
        conversation.delete()

    return JsonResponse({
        "success": True
    })


# Отправка сообщения AI-сотруднику
@login_required
@require_POST
def send_message(request):
    business_id = request.POST.get("business_id", "")
    question = request.POST.get("message", "").strip()
    conversation_id = request.POST.get("conversation_id")

    if not business_id.isascii() or not business_id.isdigit() or len(business_id) > 18:
        return JsonResponse(
            {"error": "Некорректная компания."},
            status=400
        )

    membership = get_object_or_404(
        Membership.objects.select_related("business"),
        user=request.user,
        business_id=business_id,
    )

    if not question:
        return JsonResponse(
            {"error": "Введите сообщение."},
            status=400
        )

    if len(question) > 2000:
        return JsonResponse(
            {"error": "Максимум 2000 символов."},
            status=400
        )

    business = membership.business

    from .turns import TurnError, parse_turn_id, process_turn, completed_turn
    from .rate_limits import consume
    from django.db import OperationalError
    conversation = None
    try:
        turn_id = parse_turn_id(request.POST.get("turn_id"))
        if conversation_id:
            try:
                conversation = get_object_or_404(user_conversations(request, business_id), id=conversation_id)
            except (ValueError, TypeError, ValidationError):
                return JsonResponse({"error": "Некорректный диалог."}, status=400)
        else:
            conversation, _ = Conversation.objects.get_or_create(
                business=business, channel="web", customer_name=f"Playground:{request.user.pk}", initial_turn_id=turn_id,
            )
        replay = completed_turn(conversation, question, turn_id)
        if not replay and not consume([("playground", request.user.pk, 60, 30)]):
            return JsonResponse({"error": "Слишком много сообщений. Попробуйте позже."}, status=429)
        answer = replay or process_turn(conversation, question, turn_id, respond)
        return JsonResponse({"answer": answer.content, "conversation_id": str(conversation.pk), "source": answer.ai_provider, "turn_id": str(turn_id)})
    except TurnError as exc:
        return JsonResponse({"error": exc.message, "conversation_id": str(conversation.pk) if conversation else None}, status=exc.status)
    except OperationalError:
        return JsonResponse({"error": "Сервис занят. Повторите отправку."}, status=503)
