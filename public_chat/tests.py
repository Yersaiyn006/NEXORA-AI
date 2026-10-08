from django.test import TestCase
from django.urls import reverse
from core.models import Business
from assistant_ai.models import Conversation, Lead, Message, KnowledgeItem


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
