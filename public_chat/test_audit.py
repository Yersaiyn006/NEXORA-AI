import uuid
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from core.models import Business
from assistant_ai.models import Conversation, Message
from assistant_ai.universal_engine import Result


@override_settings(NEXORA_AI_ENABLED=False)
class PublicAuditTests(TestCase):
    def setUp(self):
        self.business = Business.objects.create(name="Tagam", public_chat_enabled=True)
        self.foreign = Business.objects.create(name="Other", public_chat_enabled=True)
        self.send = reverse("public_chat_send", args=[self.business.slug])
        self.page = reverse("public_chat_page", args=[self.business.slug])

    def test_public_history_never_cached(self):
        self.assertIn("no-store", self.client.get(self.page)["Cache-Control"])

    def test_repeat_turn_does_not_duplicate_question_answer_or_call(self):
        turn_id = str(uuid.uuid4())
        with patch("public_chat.views.respond", return_value=Result("Answer", "gemini", 777)) as ai:
            first = self.client.post(self.send, {"message": "Hello", "turn_id": turn_id})
            second = self.client.post(self.send, {"message": "Hello", "turn_id": turn_id})
        self.assertEqual(first.json(), second.json())
        self.assertEqual(Message.objects.count(), 2)
        self.assertEqual(Message.objects.get(role="assistant").tokens_used, 777)
        ai.assert_called_once()

    def test_malformed_turn_id_is_400(self):
        self.assertEqual(self.client.post(self.send, {"message": "Hi", "turn_id": "invalid"}).status_code, 400)
        self.assertFalse(Conversation.objects.exists())

    def test_client_cannot_choose_foreign_conversation(self):
        foreign = Conversation.objects.create(business=self.foreign)
        Message.objects.create(conversation=foreign, role="customer", content="FOREIGN_SECRET")
        response = self.client.post(self.send, {"message": "Hi", "conversation_id": str(foreign.pk), "business_id": self.foreign.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Conversation.objects.filter(business=self.business).count(), 1)
        self.assertNotContains(self.client.get(self.page), "FOREIGN_SECRET")

    def test_tampered_session_foreign_uuid_is_rejected(self):
        self.client.get(self.page)
        foreign = Conversation.objects.create(business=self.foreign, customer_name=f"Public:{self.client.session.session_key}")
        Message.objects.create(conversation=foreign, role="customer", content="FOREIGN_SECRET")
        session = self.client.session
        session[f"public_chat_{self.business.pk}"] = str(foreign.pk)
        session.save()
        self.assertNotContains(self.client.get(self.page), "FOREIGN_SECRET")

    def test_new_public_conversation_does_not_store_raw_session_key(self):
        self.client.get(self.page)
        session_key = self.client.session.session_key
        response = self.client.post(self.send, {"message": "Hello"})
        self.assertEqual(response.status_code, 200)
        conversation = Conversation.objects.get(business=self.business)
        self.assertTrue(conversation.customer_name.startswith("Public:"))
        self.assertNotIn(session_key, conversation.customer_name)

    def test_legacy_public_conversation_still_loads(self):
        self.client.get(self.page)
        session_key = self.client.session.session_key
        conversation = Conversation.objects.create(
            business=self.business, channel="web",
            customer_name=f"Public:{session_key}",
        )
        Message.objects.create(conversation=conversation, role="customer", content="Legacy history")
        session = self.client.session
        session[f"public_chat_{self.business.pk}"] = str(conversation.pk)
        session.save()
        self.assertContains(self.client.get(self.page), "Legacy history")

    def test_malformed_session_uuid_does_not_crash(self):
        self.client.get(self.page)
        session = self.client.session
        session[f"public_chat_{self.business.pk}"] = "invalid-uuid"
        session.save()
        self.assertEqual(self.client.get(self.page).status_code, 200)

    @override_settings(NEXORA_PUBLIC_IP_PER_MINUTE=2)
    def test_new_sessions_do_not_bypass_ip_quota(self):
        for _ in range(2):
            self.assertEqual(Client().post(self.send, {"message": "Hi"}).status_code, 200)
        self.assertEqual(Client().post(self.send, {"message": "Hi"}).status_code, 429)

    @override_settings(NEXORA_PUBLIC_BUSINESS_PER_DAY=2)
    def test_new_ips_do_not_bypass_business_daily_quota(self):
        for address in ("198.51.100.1", "198.51.100.2"):
            self.assertEqual(Client().post(self.send, {"message": "Hi"}, REMOTE_ADDR=address).status_code, 200)
        self.assertEqual(Client().post(self.send, {"message": "Hi"}, REMOTE_ADDR="198.51.100.3").status_code, 429)
        other_send = reverse("public_chat_send", args=[self.foreign.slug])
        self.assertEqual(Client().post(other_send, {"message": "Hi"}, REMOTE_ADDR="198.51.100.4").status_code, 200)

    @override_settings(NEXORA_PUBLIC_IP_PER_MINUTE=1)
    def test_untrusted_forwarded_for_cannot_bypass_ip_limit(self):
        self.assertEqual(Client().post(self.send, {"message": "Hi"}, HTTP_X_FORWARDED_FOR="198.51.100.1").status_code, 200)
        self.assertEqual(Client().post(self.send, {"message": "Hi"}, HTTP_X_FORWARDED_FOR="198.51.100.2").status_code, 429)

    def test_reload_contains_latest_messages_not_oldest_only(self):
        self.client.post(self.send, {"message": "first"})
        chat = Conversation.objects.get(business=self.business)
        Message.objects.bulk_create([Message(conversation=chat, role="customer", content=f"m-{i}") for i in range(160)])
        response = self.client.get(self.page)
        self.assertContains(response, "m-159")
        self.assertNotContains(response, "m-0")
