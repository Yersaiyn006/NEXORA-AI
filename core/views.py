from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from assistant_ai.models import Conversation, Message, Lead


from core.access import selected_membership as selected_membership


@login_required
def dashboard(request):
    memberships, membership = selected_membership(request)
    business = membership.business if membership else None
    context = {"memberships": memberships, "business": business,
               "total_conversations": 0, "total_leads": 0, "ai_responses": 0, "conversion_rate": 0,
               "recent_leads": []}
    if business:
        conversations = Conversation.objects.filter(business=business).exclude(customer_name__startswith="Playground:")
        total = conversations.count()
        leads = Lead.objects.filter(business=business).exclude(status="collecting").exclude(conversation__customer_name__startswith="Playground:")
        context.update(total_conversations=total, total_leads=leads.count(),
                       ai_responses=Message.objects.filter(conversation__in=conversations, role="assistant", ai_provider="gemini").count(),
                       conversion_rate=round(leads.filter(status__in=("new", "confirmed")).values("conversation_id").distinct().count() * 100 / total, 1) if total else 0,
                       recent_leads=leads.order_by("-created_at")[:5])
    return render(request, "core/dashboard.html", context)


@login_required
def leads(request):
    memberships, membership = selected_membership(request)
    business = membership.business if membership else None
    items = Lead.objects.filter(business=business).exclude(status="collecting").order_by("-created_at") if business else Lead.objects.none()
    return render(request, "core/leads.html", {"memberships": memberships, "business": business, "leads": items, "selected_member": membership})


@login_required
@require_POST
def lead_status(request, lead_id):
    memberships, membership = selected_membership(request)
    if membership is None or membership.role not in ("owner", "admin"):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    from assistant_ai.booking import change_status
    ok, text = change_status(membership.business, lead_id, request.POST.get("status"))
    (messages.success if ok else messages.error)(request, text)
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
