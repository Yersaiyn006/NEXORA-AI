from urllib.parse import urlsplit
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from business_brain.models import CatalogItem
from core.models import Business, Membership


class LaunchFlowTests(TestCase):
    def setUp(self):
        self.operator = get_user_model().objects.create_user(username="operator_launch", password="Testpass991!", is_staff=True)

    def make_invite(self):
        self.client.force_login(self.operator)
        response = self.client.post(reverse("launch_create"), {"name": "Кафе Мечта", "industry": "Ресторан", "email": "owner@example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Business.objects.count(), 1)
        self.assertFalse(Business.objects.first().public_chat_enabled)
        return urlsplit(response.context["invite_link"]).path

    def test_full_business_to_customer_flow(self):
        invite_path = self.make_invite()
        self.client.logout()
        response = self.client.post(invite_path, {"username": "cafe_owner", "password": "Validpass991!", "password_repeat": "Validpass991!"})
        business = Business.objects.get()
        self.assertRedirects(response, reverse("launch_setup", args=[business.pk]))
        self.assertTrue(Membership.objects.filter(business=business, role="owner", user__username="cafe_owner").exists())
        self.assertEqual(self.client.get(invite_path).status_code, 410)
        response = self.client.post(reverse("launch_setup", args=[business.pk]), {"name": "Кафе Мечта", "industry": "Ресторан", "description": "Кафе с домашней кухней", "working_hours": "10:00–22:00"})
        self.assertRedirects(response, reverse("launch_catalog", args=[business.pk]))
        self.client.post(reverse("launch_catalog", args=[business.pk]), {"kind": "dish", "name": "Бургер", "price": "2500", "description": "Говядина"})
        self.assertTrue(CatalogItem.objects.filter(business=business, name="Бургер").exists())
        self.assertRedirects(self.client.post(reverse("launch_publish", args=[business.pk])), reverse("launch_ready", args=[business.pk]))
        business.refresh_from_db()
        self.assertTrue(business.public_chat_enabled)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("public_chat_page", args=[business.slug])).status_code, 200)

    def test_non_operator_cannot_invite(self):
        user = get_user_model().objects.create_user(username="regular_launch", password="Validpass991!")
        self.client.force_login(user)
        self.assertEqual(self.client.post(reverse("launch_create"), {"name": "X", "industry": "Y", "email": "x@example.com"}).status_code, 403)

    def test_cannot_publish_without_catalog(self):
        self.make_invite()
        business = Business.objects.get()
        Membership.objects.create(user=self.operator, business=business, role="owner")
        self.assertRedirects(self.client.post(reverse("launch_publish", args=[business.pk])), reverse("launch_catalog", args=[business.pk]))
        business.refresh_from_db()
        self.assertFalse(business.public_chat_enabled)

    def test_cross_business_isolation(self):
        self.make_invite()
        outsider = get_user_model().objects.create_user(username="outsider_launch", password="Validpass991!")
        self.client.force_login(outsider)
        self.assertEqual(self.client.get(reverse("launch_setup", args=[Business.objects.first().pk])).status_code, 404)
