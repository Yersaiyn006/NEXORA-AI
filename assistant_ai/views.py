from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.db import transaction

from core.models import Membership
from .models import Conversation, Message
from .services import find_answer


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


@login_required
@require_POST
def send_message(request):
    business_id = request.POST.get("business_id")
    question = request.POST.get("message", "").strip()
    conversation_id = request.POST.get("conversation_id")

    if not business_id or not business_id.isdigit():
        return JsonResponse(
            {"error": "Некорректная компания."},
            status=400,
        )

    membership = get_object_or_404(
        Membership.objects.select_related("business"),
        user=request.user,
        business_id=business_id,
    )

    if not question:
        return JsonResponse(
            {"error": "Введите сообщение."},
            status=400,
        )

    if len(question) > 2000:
        return JsonResponse(
            {"error": "Максимум 2000 символов."},
            status=400,
        )

    business = membership.business

    with transaction.atomic():
        if conversation_id:
            conversation = get_object_or_404(
                Conversation,
                id=conversation_id,
                business=business,
                channel="web",
                customer_name=f"Playground:{request.user.pk}",
            )

            if conversation.status != "active":
                return JsonResponse(
                    {"error": "Диалог закрыт."},
                    status=400,
                )

        else:
            conversation = Conversation.objects.create(
                business=business,
                channel="web",
                customer_name=f"Playground:{request.user.pk}",
            )

        Message.objects.create(
            conversation=conversation,
            role="customer",
            content=question,
        )

        answer = find_answer(business, question)

        if answer:
            provider = "knowledge_base"
        else:
            provider = "fallback"
            answer = (
                "Пока у меня недостаточно информации, "
                "чтобы точно ответить на этот вопрос. "
                "Пожалуйста, обратитесь к сотруднику."
            )

        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=answer,
            ai_provider=provider,
            tokens_used=0,
        )

    return JsonResponse({
        "answer": answer,
        "conversation_id": str(conversation.id),
        "source": provider,
    })