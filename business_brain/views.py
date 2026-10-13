from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import CatalogForm, ProfileForm
from .models import BusinessProfile, CatalogItem


from core.access import selected_membership as membership_for


def editor(member):
    if not member or member.role not in ("owner", "admin"):
        raise PermissionDenied


def home_url(business):
    return f"/brain/?business={business.pk}"


@login_required
def home(request):
    memberships, member = membership_for(request)
    business = member.business if member else None
    profile = BusinessProfile.objects.filter(business=business).first() if business else None
    return render(request, "business_brain/home.html", {
        "memberships": memberships, "member": member, "business": business,
        "profile": profile, "profile_form": ProfileForm(instance=profile),
        "catalog_form": CatalogForm(),
        "items": CatalogItem.objects.filter(business=business) if business else [],
    })


@login_required
@require_POST
def save_profile(request):
    _, member = membership_for(request)
    editor(member)
    profile, _ = BusinessProfile.objects.get_or_create(business=member.business)
    form = ProfileForm(request.POST, instance=profile)
    if form.is_valid():
        form.save()
        return redirect(home_url(member.business))
    return render(request, "business_brain/error.html", {"form": form, "business": member.business}, status=400)


@login_required
@require_POST
def save_item(request):
    _, member = membership_for(request)
    editor(member)
    item_id = request.POST.get("item_id", "").strip()
    if item_id and (not item_id.isascii() or not item_id.isdigit() or len(item_id) > 18):
        from django.http import Http404
        raise Http404
    item = get_object_or_404(CatalogItem, business=member.business, pk=item_id) if item_id else CatalogItem(business=member.business)
    form = CatalogForm(request.POST, instance=item)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.business = member.business
        obj.save()
        return redirect(home_url(member.business))
    return render(request, "business_brain/error.html", {"form": form, "business": member.business}, status=400)


@login_required
@require_POST
def delete_item(request, item_id):
    _, member = membership_for(request)
    editor(member)
    get_object_or_404(CatalogItem, business=member.business, pk=item_id).delete()
    return redirect(home_url(member.business))
