"""Database-backed bounded public usage; independent of cookies and worker caches."""
import hashlib
import hmac
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from .models import RateLimitBucket


def private_key(value):
    return hmac.new(settings.SECRET_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()


def consume(scopes, now=None):
    """All counters advance atomically, or none do. Fixed windows don't slide."""
    now = now or timezone.now()
    with transaction.atomic():
        for scope, identity, window, limit in scopes:
            slot = int(now.timestamp()) // window
            key = f"{scope}:{private_key(str(identity))}:{slot}"
            bucket, _ = RateLimitBucket.objects.get_or_create(
                key=key, defaults={"expires_at": now + timedelta(seconds=window)},
            )
            if not RateLimitBucket.objects.filter(pk=bucket.pk, count__lt=limit).update(count=F("count") + 1):
                transaction.set_rollback(True)
                return False
    return True


def public_allow(request, business):
    # REMOTE_ADDR is intentionally used: untrusted X-Forwarded-For is never accepted.
    return consume([
        ("public-session", request.session.session_key, 60, settings.NEXORA_PUBLIC_SESSION_PER_MINUTE),
        ("public-ip", request.META.get("REMOTE_ADDR", "unknown"), 60, settings.NEXORA_PUBLIC_IP_PER_MINUTE),
        ("public-business", business.pk, 86400, settings.NEXORA_PUBLIC_BUSINESS_PER_DAY),
        ("public-global", "platform", 86400, settings.NEXORA_PUBLIC_GLOBAL_PER_DAY),
    ])
