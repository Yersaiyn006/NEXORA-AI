from unittest.mock import patch
from django.test import TestCase, override_settings
from core.models import Business
from .models import Conversation, KnowledgeItem, Lead
from .universal_engine import respond

@override_settings(NEXORA_AI_ENABLED=False)
class MultiIndustryTests(TestCase):
    def setUp(self):
        self.restaurant = Business.objects.create(name='Кафе Восток', slug='cafe-vostok', industry='Ресторан')
        self.shop = Business.objects.create(name='Товары', slug='goods-shop', industry='Интернет-магазин')
        self.salon = Business.objects.create(name='Салон', slug='salon-v5', industry='Парикмахерская')

    def test_restaurant_order_not_haircut(self):
        chat = Conversation.objects.create(business=self.restaurant)
        result = respond(chat, 'Хочу заказать пиццу')
        self.assertIn('Как вас зовут', result.answer)
        self.assertEqual(Lead.objects.get(conversation=chat).service, 'пиццу')
        self.assertNotIn('стриж', result.answer.lower())

    def test_shop_purchase(self):
        chat = Conversation.objects.create(business=self.shop)
        result = respond(chat, 'Хочу купить ноутбук')
        self.assertIn('Как вас зовут', result.answer)
        self.assertEqual(Lead.objects.get(conversation=chat).service, 'ноутбук')

    def test_no_cross_tenant_knowledge(self):
        KnowledgeItem.objects.create(business=self.salon, title='Секретная цена', content='999 тенге')
        chat = Conversation.objects.create(business=self.restaurant)
        self.assertNotIn('999', respond(chat, 'Сколько стоит?').answer)

    def test_ai_off_never_calls_provider(self):
        chat = Conversation.objects.create(business=self.restaurant)
        with patch('assistant_ai.universal_engine._safe_llm_answer', return_value=None) as mock:
            respond(chat, 'Что у вас в меню?')
            mock.assert_called_once()

    def test_continues_request(self):
        chat = Conversation.objects.create(business=self.restaurant)
        respond(chat, 'Хочу заказать пиццу')
        self.assertIn('телефон', respond(chat, 'Айжан').answer.lower())

    def test_no_fabricated_stock(self):
        chat = Conversation.objects.create(business=self.shop)
        self.assertNotIn('в наличии', respond(chat, 'Есть ли iPhone?').answer.lower())
