from django.test import TestCase
from django.contrib.auth import get_user_model
from core.models import Business, Membership
from assistant_ai.models import Conversation, Message, Lead
from .sales_radar import sales_radar

class SalesRadarTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="radar_owner", password="testpass123!")
        self.other = get_user_model().objects.create_user(username="outsider", password="testpass123!")
        self.business = Business.objects.create(name="Radar Test Salon")
        self.other_business = Business.objects.create(name="Other Radar Salon")
        Membership.objects.create(user=self.user, business=self.business, role="owner")

    def test_interest_without_lead(self):
        c = Conversation.objects.create(business=self.business, customer_name="Customer")
        Message.objects.create(conversation=c, role="customer", content="Сколько стоит стрижка?")
        data = sales_radar(self.business)
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["opportunity_count"], 1)

    def test_existing_lead_is_not_opportunity(self):
        c = Conversation.objects.create(business=self.business)
        Message.objects.create(conversation=c, role="customer", content="Хочу записаться")
        Lead.objects.create(business=self.business, conversation=c, status="new")
        data = sales_radar(self.business)
        self.assertEqual(data["opportunity_count"], 0)
        self.assertEqual(data["with_lead"], 1)

    def test_playground_excluded_by_default(self):
        c = Conversation.objects.create(business=self.business, customer_name=f"Playground:{self.user.pk}")
        Message.objects.create(conversation=c, role="customer", content="Сколько стоит?")
        self.assertEqual(sales_radar(self.business)["total"], 0)
        self.assertEqual(sales_radar(self.business, True)["total"], 1)

    def test_no_cross_business_data(self):
        c = Conversation.objects.create(business=self.other_business)
        Message.objects.create(conversation=c, role="customer", content="Сколько стоит?")
        self.assertEqual(sales_radar(self.business)["total"], 0)

    def test_access_requires_membership(self):
        self.client.force_login(self.other)
        response = self.client.get("/radar/?business=" + str(self.business.pk))
        self.assertEqual(response.status_code, 404)
