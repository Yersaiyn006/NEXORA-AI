from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Membership
from assistant_ai.models import Conversation, Message, Lead


def selected_membership(request):
    memberships = Membership.objects.filter(user=request.user).select_related("business").order_by("business__name")
    business_id = request.GET.get("business") or request.POST.get("business")
    membership = get_object_or_404(memberships, business_id=business_id) if business_id else memberships.first()
    return memberships, membership


@login_required
def dashboard(request):
    memberships, membership = selected_membership(request)
    business = membership.business if membership else None
    context = {"memberships": memberships, "business": business,
               "total_conversations": 0, "total_leads": 0, "ai_responses": 0, "conversion_rate": 0,
               "recent_leads": []}
    if business:
        conversations = Conversation.objects.filter(business=business)
        total = conversations.count()
        leads = Lead.objects.filter(business=business).exclude(status="collecting")
        context.update(total_conversations=total, total_leads=leads.count(),
                       ai_responses=Message.objects.filter(conversation__business=business, role="assistant").count(),
                       conversion_rate=round(leads.count() * 100 / total, 1) if total else 0,
                       recent_leads=leads.order_by("-created_at")[:5])
    return render(request, "core/dashboard.html", context)


@login_required
def leads(request):
    memberships, membership = selected_membership(request)
    business = membership.business if membership else None
    items = Lead.objects.filter(business=business).exclude(status="collecting").order_by("-created_at") if business else Lead.objects.none()
    return render(request, "core/leads.html", {"memberships": memberships, "business": business, "leads": items})


@login_required
@require_POST
def lead_status(request, lead_id):
    memberships, membership = selected_membership(request)
    if membership is None or membership.role not in ("owner", "admin"):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    lead = get_object_or_404(Lead, id=lead_id, business=membership.business)
    status = request.POST.get("status")
    if status not in ("confirmed", "cancelled") or lead.status != "new":
        messages.error(request, "Нельзя выполнить это изменение статуса.")
    else:
        lead.status = status
        lead.save(update_fields=["status", "updated_at"])
        messages.success(request, "Статус заявки обновлён.")
    return redirect(f"/leads/?business={membership.business_id}")


@login_required
def radar(request):
    from .sales_radar import sales_radar
    memberships, membership = selected_membership(request)
    business = membership.business if membership else None
    include_playground = request.GET.get("demo") == "1"
    data = sales_radar(business, include_playground) if business else None
    return render(request, "core/radar.html", {
        "memberships": memberships,
        "business": business,
        "radar": data,
    })
