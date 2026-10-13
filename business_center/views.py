from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from assistant_ai.models import KnowledgeItem, Lead, Conversation
from business_brain.models import CatalogItem


from core.access import selected_membership as context_for


def go(business):
    return redirect(f"/studio/?business={business.pk}")


@login_required
def studio(request):
    memberships, membership = context_for(request)
    business = membership.business if membership else None
    knowledge = KnowledgeItem.objects.filter(business=business).order_by("category", "title") if business else KnowledgeItem.objects.none()
    leads = Lead.objects.filter(business=business).exclude(status="collecting").order_by("-created_at") if business else Lead.objects.none()
    query = request.GET.get("q", "").strip()[:100]
    if query:
        leads = leads.filter(Q(customer_name__icontains=query) | Q(phone__icontains=query) | Q(service__icontains=query))
    leads = leads[:100]
    confirmed = Lead.objects.filter(business=business, status="confirmed", requested_at__gte=timezone.now()).order_by("requested_at")[:30] if business else Lead.objects.none()
    return render(request, "business_center/studio.html", {
        "memberships": memberships, "membership": membership, "business": business,
        "knowledge": knowledge, "leads": leads, "confirmed": confirmed, "q": query,
        "categories": KnowledgeItem.CATEGORY_CHOICES,
        "metrics": {"facts": KnowledgeItem.objects.filter(business=business, is_active=True).count() + CatalogItem.objects.filter(business=business).count() if business else 0, "knowledge": knowledge.count(), "leads": Lead.objects.filter(business=business).exclude(status="collecting").count() if business else 0,
                    "confirmed": Lead.objects.filter(business=business, status="confirmed").count() if business else 0,
                    "conversations": Conversation.objects.filter(business=business).exclude(customer_name__startswith="Playground:").count() if business else 0},
    })


@login_required
@require_POST
def knowledge_save(request):
    _, member = context_for(request)
    if not member or member.role not in ("owner", "admin"):
        raise PermissionDenied
    business = member.business
    raw_id = request.POST.get("item_id", "").strip()
    if raw_id and (not raw_id.isascii() or not raw_id.isdigit() or len(raw_id) > 18):
        from django.http import Http404
        raise Http404
    item = get_object_or_404(KnowledgeItem, pk=raw_id, business=business) if raw_id else KnowledgeItem(business=business)
    title = request.POST.get("title", "").strip()
    content = request.POST.get("content", "").strip()
    category = request.POST.get("category", "general")
    if not (1 <= len(title) <= 200 and 1 <= len(content) <= 5000) or category not in dict(KnowledgeItem.CATEGORY_CHOICES):
        messages.error(request, "Проверьте название, содержание и категорию.")
        return go(business)
    item.title, item.content, item.category = title, content, category
    item.is_active = request.POST.get("is_active") == "on"
    item.save()
    messages.success(request, "База знаний обновлена.")
    return go(business)


@login_required
@require_POST
def knowledge_delete(request, item_id):
    _, member = context_for(request)
    if not member or member.role not in ("owner", "admin"):
        raise PermissionDenied
    get_object_or_404(KnowledgeItem, pk=item_id, business=member.business).delete()
    messages.success(request, "Запись удалена.")
    return go(member.business)


def booking_conflict(lead):
    if not lead.requested_at:
        return False
    start = lead.requested_at
    # Default 60-minute reservation window; configurable durations are a later milestone.
    return Lead.objects.filter(business=lead.business, status="confirmed", requested_at__gt=start - timedelta(minutes=60), requested_at__lt=start + timedelta(minutes=60)).exclude(pk=lead.pk).exists()


@login_required
@require_POST
def booking_action(request, lead_id):
    _, member = context_for(request)
    if not member or member.role not in ("owner", "admin"):
        raise PermissionDenied
    from assistant_ai.booking import change_status
    ok, text = change_status(member.business, lead_id, request.POST.get("action"))
    (messages.success if ok else messages.error)(request, text)
    return go(member.business)
