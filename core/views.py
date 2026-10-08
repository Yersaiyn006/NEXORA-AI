from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from .models import Business, Membership


@login_required
def dashboard(request):
    memberships = (
        Membership.objects
        .filter(user=request.user)
        .select_related("business")
        .order_by("business__name")
    )

    selected_business = None

    business_id = request.GET.get("business")

    if business_id:
        membership = get_object_or_404(
            memberships,
            business_id=business_id
        )
        selected_business = membership.business

    elif memberships.exists():
        selected_business = memberships.first().business

    context = {
        "memberships": memberships,
        "business": selected_business,
        "total_conversations": 0,
        "total_leads": 0,
        "ai_responses": 0,
        "conversion_rate": 0,
    }

    return render(request, "core/dashboard.html", context)