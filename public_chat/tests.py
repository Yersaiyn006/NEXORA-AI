from django.test import TestCase
from django.urls import reverse
from core.models import Business
from assistant_ai.models import Conversation, Lead, KnowledgeItem
from business_brain.models import CatalogItem
from django.test import override_settings


class PublicChatTests(TestCase):
    def setUp(self):
        self.a = Business.objects.create(name="Salon A", slug="salon-a", public_chat_enabled=True)
        self.b = Business.objects.create(name="Salon B", slug="salon-b", public_chat_enabled=True)
        self.url = reverse("public_chat_page", args=[self.a.slug])
        self.send = reverse("public_chat_send", args=[self.a.slug])

    def test_disabled_business_is_hidden(self):
        self.a.public_chat_enabled = False
        self.a.save()
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.send, {"message": "test"}).status_code, 404)

    def test_public_chat_creates_real_conversation(self):
        self.client.get(self.url)
        response = self.client.post(self.send, {"message": "Здравствуйте"})
        self.assertEqual(response.status_code, 200)
        conv = Conversation.objects.get(business=self.a)
        self.assertTrue(conv.customer_name.startswith("Public:"))
        self.assertEqual(conv.messages.count(), 2)

    def test_sessions_are_isolated(self):
        self.client.get(self.url)
        self.client.post(self.send, {"message": "Первый"})
        from django.test import Client
        other = Client()
        other.get(self.url)
        self.assertNotContains(other.get(self.url), "Первый")

    def test_company_knowledge_is_isolated(self):
        KnowledgeItem.objects.create(business=self.b, title="Уникальная услуга", content="Секрет компании B")
        self.client.get(self.url)
        response = self.client.post(self.send, {"message": "Уникальная услуга"})
        self.assertNotIn("Секрет компании B", response.json()["answer"])

    def test_lead_created_for_public_customer(self):
        self.client.get(self.url)
        for text in ("Хочу записаться", "Стрижка", "Арман", "+77771112233", "31.12.2027 15:00"):
            response = self.client.post(self.send, {"message": text})
            self.assertEqual(response.status_code, 200)
        lead = Lead.objects.get(business=self.a)
        self.assertEqual(lead.status, "new")
        self.assertEqual(lead.phone, "+77771112233")

    def test_limit_and_input_validation(self):
        self.client.get(self.url)
        self.assertEqual(self.client.post(self.send, {"message": " "}).status_code, 400)
        for _ in range(15):
            self.assertEqual(self.client.post(self.send, {"message": "test"}).status_code, 200)
        self.assertEqual(self.client.post(self.send, {"message": "test"}).status_code, 429)


@override_settings(NEXORA_AI_ENABLED=False)
class PublicCatalogIntegrationTests(TestCase):
    def setUp(self):
        self.business = Business.objects.create(name="Tagam", slug="tagam-test", public_chat_enabled=True)
        CatalogItem.objects.create(business=self.business, kind="dish", name="Завтрак", price="2500.00", currency="KZT")
        self.send_url = reverse("public_chat_send", args=[self.business.slug])

    def test_public_chat_reads_own_catalog_without_gemini(self):
        response = self.client.post(self.send_url, {"message": "Какие блюда есть в вашем ресторане?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source"], "catalog_fallback")
        self.assertIn("Завтрак", response.json()["answer"])
        self.assertIn("2500", response.json()["answer"])

    def test_catalog_is_tenant_isolated(self):
        other = Business.objects.create(name="Other", slug="other-test", public_chat_enabled=True)
        CatalogItem.objects.create(business=other, kind="dish", name="Секретное блюдо", price="99999")
        response = self.client.post(self.send_url, {"message": "Покажите меню"})
        self.assertNotIn("Секретное блюдо", response.json()["answer"])
