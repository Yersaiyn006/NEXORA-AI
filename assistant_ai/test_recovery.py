"""Recovery tests for business actions and budgets across both chat channels."""
import os
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from django.test import TransactionTestCase, TestCase, override_settings
from core.models import Business
from .models import Conversation, Lead, Message
from .turns import process_turn
from .universal_engine import respond


@override_settings(NEXORA_AI_ENABLED=False)
class RequestRecoveryTests(TransactionTestCase):
    def setUp(self):
        self.business = Business.objects.create(name="Recovery shop")
        self.chat = Conversation.objects.create(business=self.business)

    def failed_answer_then_retry(self, text):
        turn = uuid.uuid4()
        original = Message.objects.create
        def save(**kwargs):
            if kwargs.get("role") == "assistant":
                raise RuntimeError("synthetic answer storage failure")
            return original(**kwargs)
        with patch("assistant_ai.turns.Message.objects.create", side_effect=save):
            with self.assertRaises(RuntimeError):
                process_turn(self.chat, text, turn, respond)
        return process_turn(self.chat, text, turn, respond)

    def test_creation_retry_does_not_consume_initial_request_as_customer_name(self):
        answer = self.failed_answer_then_retry("Хочу заказать пиццу")
        self.assertEqual(self.chat.leads.count(), 1)
        self.assertEqual(self.chat.leads.get().customer_name, "")
        self.assertEqual(answer.content, "Как вас зовут?")
        self.assertEqual(self.chat.messages.count(), 2)

    def test_name_retry_replays_the_same_next_question(self):
        Lead.objects.create(business=self.business, conversation=self.chat, service="пицца")
        answer = self.failed_answer_then_retry("Арман")
        self.assertIn("Оставьте номер телефона", answer.content)
        self.assertEqual(self.chat.leads.get().customer_name, "Арман")

    def test_finalization_retry_does_not_create_another_lead(self):
        Lead.objects.create(business=self.business, conversation=self.chat, service="пицца", customer_name="Арман", phone="+77771112233")
        answer = self.failed_answer_then_retry("без времени")
        self.assertEqual(self.chat.leads.count(), 1)
        self.assertEqual(self.chat.leads.get().status, "new")
        self.assertIn("создана", answer.content)
        self.assertEqual(answer.ai_provider, "request_engine")

    def test_action_rolls_back_if_receipt_cannot_be_saved(self):
        original = Message.save
        def save(message, *args, **kwargs):
            if kwargs.get("update_fields") == ['request_response']:
                raise RuntimeError("synthetic receipt failure")
            return original(message, *args, **kwargs)
        turn = uuid.uuid4()
        with patch.object(Message, "save", save):
            with self.assertRaises(RuntimeError):
                process_turn(self.chat, "Хочу заказать пиццу", turn, respond)
        self.assertFalse(self.chat.leads.exists())
        answer = process_turn(self.chat, "Хочу заказать пиццу", turn, respond)
        self.assertEqual(answer.content, "Как вас зовут?")

    def test_stale_worker_cannot_apply_a_request_action(self):
        from .turns import TurnError
        def stale(chat, text):
            Conversation.objects.filter(pk=chat.pk).update(processing_token=uuid.uuid4())
            return respond(chat, text)
        with self.assertRaises(TurnError):
            process_turn(self.chat, "Хочу заказать пиццу", uuid.uuid4(), stale)
        self.assertFalse(self.chat.leads.exists())


@override_settings(NEXORA_AI_ENABLED=True, NEXORA_AI_BUSINESS_PER_DAY=1, NEXORA_AI_GLOBAL_PER_DAY=2)
class ProviderBudgetTests(TestCase):
    @patch.dict(os.environ, {"GEMINI_API_KEY": "synthetic-only"})
    def test_provider_budget_covers_different_conversations_and_businesses(self):
        businesses = [Business.objects.create(name=f"Budget {i}") for i in range(3)]
        chats = [Conversation.objects.create(business=b) for b in businesses]
        client = MagicMock()
        client.__enter__.return_value = client
        client.models.generate_content.return_value = SimpleNamespace(text="Answer", usage_metadata=None)
        with patch("google.genai.Client", return_value=client) as factory:
            self.assertEqual(respond(chats[0], "Здравствуйте").source, "gemini")
            # Another conversation for the same company cannot evade its budget.
            extra = Conversation.objects.create(business=businesses[0])
            self.assertNotEqual(respond(extra, "Здравствуйте").source, "gemini")
            self.assertEqual(respond(chats[1], "Здравствуйте").source, "gemini")
            self.assertNotEqual(respond(chats[2], "Здравствуйте").source, "gemini")
        self.assertEqual(factory.call_count, 2)
