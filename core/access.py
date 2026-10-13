"""One selector for tenant membership; invalid IDs are a 404, never a server error."""
from django.http import Http404
from django.shortcuts import get_object_or_404
from .models import Membership


def selected_membership(request):
    memberships = Membership.objects.filter(user=request.user).select_related("business").order_by("business__name", "pk")
    raw = request.GET.get("business") or request.POST.get("business")
    if raw:
        if not raw.isascii() or not raw.isdigit() or len(raw) > 18:
            raise Http404
        return memberships, get_object_or_404(memberships, business_id=raw)
    return memberships, memberships.first()
