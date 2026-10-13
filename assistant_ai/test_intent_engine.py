from datetime import timedelta
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from core.models import Business
from .models import Conversation, KnowledgeItem, Lead
from .intent_engine import is_booking, asks_services
from .lead_engine import parse_datetime, respond_to_lead
from .services import find_answer


class IntentTests(SimpleTestCase):
    def test_booking_phrases(self):
        for phrase in ("Хочу оставить заявку", "Надо записаться", "Можно к вам завтра?", "Жазылғым келеді"):
            with self.subTest(phrase=phrase):
                self.assertTrue(is_booking(phrase))

    def test_information_is_not_booking(self):
        for phrase in ("Сколько стоит стрижка?", "Когда вы работаете?", "Какие услуги есть?"):
            self.assertFalse(is_booking(phrase))

    def test_service_intent(self):
        self.assertTrue(asks_services("Какие услуги есть?"))
        self.assertTrue(asks_services("Қандай қызметтер бар?"))

    @override_settings(TIME_ZONE="Asia/Qyzylorda")
    def test_today_future_time(self):
        now = timezone.localtime()
        candidate = now + timedelta(hours=2)
        if candidate.date() == now.date():
            self.assertIsNotNone(parse_datetime(f"Сегодня {candidate:%H:%M}"))

    def test_tomorrow(self):
        self.assertIsNotNone(parse_datetime("завтра в 15:00"))
        self.assertIsNotNone(parse_datetime("ертең 15:00"))


class SmartFlowTests(TestCase):
    def setUp(self):
        self.business = Business.objects.create(name="Test Salon", slug="smart-test")
        self.conversation = Conversation.objects.create(business=self.business)

    def test_service_catalog(self):
        KnowledgeItem.objects.create(business=self.business, category="service", title="Стрижка", content="Мужская стрижка 3500 тенге")
        answer = find_answer(self.business, "Какие услуги есть?")
        self.assertIn("Стрижка", answer)

    def test_no_cross_business_leak(self):
        other = Business.objects.create(name="Other", slug="other-smart")
        KnowledgeItem.objects.create(business=other, category="service", title="Секрет", content="Только для другого бизнеса")
        self.assertIsNone(find_answer(self.business, "Какие услуги есть?"))

    def test_booking_request_creates_collecting_lead(self):
        answer = respond_to_lead(self.conversation, "Хочу оставить заявку")
        self.assertIn("услугу", answer)
        self.assertEqual(Lead.objects.get(conversation=self.conversation).status, "collecting")
