"""Server-authorized, short-transaction lead transitions shared by both CRM views."""
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from core.models import Business
from .models import Lead


def change_status(business, lead_id, status):
    from business_center.views import booking_conflict
    with transaction.atomic():
        # Serialize competing confirmations for this business (including on SQLite).
        Business.objects.filter(pk=business.pk).update(name=F("name"))
        lead = get_object_or_404(Lead.objects.select_for_update(), pk=lead_id, business=business)
        if status not in ("confirmed", "cancelled") or lead.status != "new":
            return False, "Нельзя выполнить это изменение статуса."
        if status == "confirmed" and lead.requested_at:
            if lead.requested_at <= timezone.now() or booking_conflict(lead):
                return False, "Время прошло или занято другой подтверждённой записью (окно 60 минут)."
        lead.status = status
        lead.save(update_fields=["status", "updated_at"])
        return True, "Статус заявки обновлён."
