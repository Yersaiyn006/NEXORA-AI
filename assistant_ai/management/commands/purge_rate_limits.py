from django.core.management.base import BaseCommand
from django.utils import timezone
from assistant_ai.models import RateLimitBucket


class Command(BaseCommand):
    help = "Remove expired abuse-control counters (run daily). Does not delete conversations."

    def handle(self, *args, **options):
        count, _ = RateLimitBucket.objects.filter(expires_at__lt=timezone.now()).delete()
        self.stdout.write(f"Removed {count} expired counters")
