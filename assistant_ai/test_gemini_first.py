from unittest.mock import patch
from django.test import TestCase, override_settings
from core.models import Business
from business_brain.models import CatalogItem
from .models import Conversation
from .universal_engine import respond


@override_settings(NEXORA_AI_ENABLED=True)
class GeminiFirstTests(TestCase):
    def setUp(self):
        self.business = Business.objects.create(name="Demo Business", slug="gemini-demo")
        self.chat = Conversation.objects.create(business=self.business)

    def test_gemini_used_even_for_catalog_questions(self):
        CatalogItem.objects.create(business=self.business, name="Завтрак", kind="food", price=2500)
        with patch("assistant_ai.universal_engine._safe_llm_answer", return_value="Живой ответ AI") as ai:
            result = respond(self.chat, "Какие товары и услуги есть?")
        self.assertEqual(result.source, "gemini")
        self.assertEqual(result.answer, "Живой ответ AI")
        self.assertTrue(ai.called)

    def test_general_question_uses_gemini(self):
        with patch("assistant_ai.universal_engine._safe_llm_answer", return_value="О компании"):
            result = respond(self.chat, "Расскажи о вашей компании")
        self.assertEqual(result.source, "gemini")

    def test_other_business_data_not_in_context(self):
        other = Business.objects.create(name="Other", slug="gemini-other")
        CatalogItem.objects.create(business=other, name="Чужой секрет", kind="food", price=999)
        with patch("assistant_ai.universal_engine._safe_llm_answer", return_value="Ответ") as ai:
            respond(self.chat, "Расскажи о товарах")
        self.assertNotIn("Чужой секрет", str(ai.call_args))
