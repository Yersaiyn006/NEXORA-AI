from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from core.models import Business, Membership
from assistant_ai.models import KnowledgeItem, Conversation, Lead
from .views import booking_conflict

class StudioTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="ownerstudio", password="testpass123")
        self.other = get_user_model().objects.create_user(username="otherstudio", password="testpass123")
        self.business = Business.objects.create(name="Barbershop")
        self.foreign = Business.objects.create(name="Other shop")
        Membership.objects.create(user=self.owner, business=self.business, role="owner")
        Membership.objects.create(user=self.other, business=self.foreign, role="owner")
        self.client.force_login(self.owner)

    def test_studio_loads(self):
        self.assertEqual(self.client.get("/studio/").status_code, 200)

    def test_knowledge_create(self):
        response = self.client.post("/studio/knowledge/save/", {"business": self.business.pk, "title": "Стрижка", "content": "3500 тенге", "category": "service", "is_active": "on"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(KnowledgeItem.objects.filter(business=self.business, title="Стрижка").exists())

    def test_cannot_edit_foreign_business(self):
        response = self.client.post("/studio/knowledge/save/", {"business": self.foreign.pk, "title": "X", "content": "Y", "category": "service"})
        self.assertEqual(response.status_code, 404)

    def test_booking_conflict(self):
        c = Conversation.objects.create(business=self.business)
        when = timezone.now() + timedelta(days=2)
        Lead.objects.create(business=self.business, conversation=c, status="confirmed", requested_at=when)
        new = Lead.objects.create(business=self.business, conversation=c, status="new", requested_at=when + timedelta(minutes=30))
        self.assertTrue(booking_conflict(new))
        response = self.client.post(f"/studio/booking/{new.pk}/", {"business": self.business.pk, "action": "confirmed"})
        self.assertEqual(response.status_code, 302)
        new.refresh_from_db()
        self.assertEqual(new.status, "new")

    def test_booking_confirmation(self):
        c = Conversation.objects.create(business=self.business)
        lead = Lead.objects.create(business=self.business, conversation=c, status="new", requested_at=timezone.now() + timedelta(days=3))
        response = self.client.post(f"/studio/booking/{lead.pk}/", {"business": self.business.pk, "action": "confirmed"})
        self.assertEqual(response.status_code, 302)
        lead.refresh_from_db()
        self.assertEqual(lead.status, "confirmed")
