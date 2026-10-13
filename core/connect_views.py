"""Business-owned distribution channels for public chat."""
from io import BytesIO
import qrcode
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST


from core.access import selected_membership as member_for


def public_url(request, business):
    return request.build_absolute_uri(reverse("public_chat_page", args=[business.slug]))


@login_required
def connect_home(request):
    memberships, member = member_for(request)
    business = member.business if member else None
    url = public_url(request, business) if business else ""
    embed = (f'<script src="{request.build_absolute_uri("/static/core/nexora-widget.js")}" '
             f'data-nexora-chat="{url}" defer></script>') if business else ""
    return render(request, "core/connect.html", {
        "memberships": memberships, "member": member, "business": business,
        "public_url": url, "embed_code": embed,
    })


@login_required
@require_POST
def connect_toggle(request):
    _, member = member_for(request)
    if not member or member.role not in ("owner", "admin"):
        raise PermissionDenied
    member.business.public_chat_enabled = request.POST.get("enabled") == "1"
    member.business.save(update_fields=["public_chat_enabled"])
    return redirect(f'{reverse("connect_home")}?business={member.business.pk}')


@login_required
def connect_qr(request):
    _, member = member_for(request)
    if not member:
        raise PermissionDenied
    url = public_url(request, member.business)
    img = qrcode.make(url, box_size=10, border=3)
    stream = BytesIO()
    img.save(stream, format="PNG")
    response = HttpResponse(stream.getvalue(), content_type="image/png")
    response["Content-Disposition"] = f'attachment; filename="nexora-{member.business.pk}-qr.png"'
    response["Cache-Control"] = "private, no-store"
    return response
