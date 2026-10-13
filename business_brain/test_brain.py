from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from core.models import Business, Membership
from assistant_ai.models import Conversation
from assistant_ai.universal_engine import respond
from .models import CatalogItem, BusinessProfile

@override_settings(NEXORA_AI_ENABLED=False)
class BrainTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.owner = U.objects.create_user(username="brain_owner", password="testpass")
        self.staff = U.objects.create_user(username="brain_staff", password="testpass")
        self.business = Business.objects.create(name="Кафе Альфа", industry="ресторан")
        self.other = Business.objects.create(name="Магазин Бета", industry="магазин")
        Membership.objects.create(user=self.owner, business=self.business, role="owner")
        Membership.objects.create(user=self.staff, business=self.business, role="staff")
        self.item = CatalogItem.objects.create(business=self.business, kind="dish", name="Бургер", price="2500", description="С говядиной")
        self.conversation = Conversation.objects.create(business=self.business)

    def test_owner_can_edit_catalog(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("brain_item_save"), {"business": self.business.pk, "kind": "dish", "name": "Пицца", "price": "3800", "currency": "KZT", "is_available": "on"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CatalogItem.objects.filter(business=self.business, name="Пицца").exists())

    def test_staff_cannot_edit(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.post(reverse("brain_item_save"), {"business": self.business.pk, "name": "Суп"}).status_code, 403)

    def test_cross_tenant_rejected(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(reverse("brain_item_save"), {"business": self.other.pk, "name": "Чужое"}).status_code, 404)
        self.assertEqual(self.client.post(reverse("brain_item_delete", args=[self.item.pk]), {"business": self.other.pk}).status_code, 404)

    def test_catalog_answer_without_ai(self):
        answer = respond(self.conversation, "Сколько стоит Бургер?")
        self.assertEqual(answer.source, "catalog_fallback")
        self.assertIn("2500", answer.answer)

    def test_different_business_isolation(self):
        second = Conversation.objects.create(business=self.other)
        answer = respond(second, "Сколько стоит Бургер?")
        self.assertNotIn("2500", answer.answer)

    def test_profile_persists(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("brain_profile"), {"business": self.business.pk, "address": "Центр", "working_hours": "10:00–22:00"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(BusinessProfile.objects.get(business=self.business).address, "Центр")

    def test_unavailable_item_not_sold_as_available(self):
        self.item.is_available = False
        self.item.save()
        self.assertIn("недоступно", respond(self.conversation, "Какие блюда есть?").answer)
