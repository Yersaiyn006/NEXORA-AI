
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from core.models import Membership
from .models import Conversation, Message
from .services import find_answer
from .lead_engine import respond_to_lead


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

    if not business_id.isdigit():
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
        last_message_at=Max("messages__created_at")
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
        first_message = conversation.messages.filter(
            role="customer"
        ).order_by(
            "created_at",
            "id"
        ).first()

        title = (
            first_message.content[:65]
            if first_message
            else "Новый диалог"
        )

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

    if not business_id.isdigit():
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

    if not business_id.isdigit():
        return JsonResponse(
            {"error": "Некорректная компания."},
            status=400
        )

    conversation = get_object_or_404(
        user_conversations(request, business_id),
        id=conversation_id,
    )

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

    if not business_id.isdigit():
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

    with transaction.atomic():

        # Продолжаем старый диалог или создаём новый
        if conversation_id:
            conversation = get_object_or_404(
                user_conversations(request, business_id),
                id=conversation_id,
            )

            if conversation.status != "active":
                return JsonResponse(
                    {"error": "Диалог закрыт."},
                    status=400
                )

        else:
            conversation = Conversation.objects.create(
                business=business,
                channel="web",
                customer_name=f"Playground:{request.user.pk}",
            )

        # Сохраняем вопрос пользователя
        Message.objects.create(
            conversation=conversation,
            role="customer",
            content=question,
        )

        # Ищем ответ в базе знаний
        answer = respond_to_lead(conversation, question)
        if answer is not None:
            provider = "lead_engine"
        else:
            answer = find_answer(business, question)
            provider = "knowledge_base" if answer else "fallback"

        if not answer:
            provider = "fallback"
            answer = (
                "Пока у меня недостаточно информации, "
                "чтобы точно ответить на этот вопрос. "
                "Пожалуйста, обратитесь к сотруднику."
            )

        # Сохраняем ответ
        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=answer,
            ai_provider=provider,
            tokens_used=0,
        )

        # Обновляем время последней активности
        Conversation.objects.filter(
            pk=conversation.pk
        ).update(
            updated_at=timezone.now()
        )

    return JsonResponse({
        "answer": answer,
        "conversation_id": str(conversation.id),
        "source": provider,
    })
