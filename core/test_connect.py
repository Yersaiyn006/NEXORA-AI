
from urllib.parse import quote

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from core.models import Business, Membership


class ConnectTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.owner = User.objects.create_user(
            username="owner_connect",
            password="secret"
        )

        self.other = User.objects.create_user(
            username="other_connect",
            password="secret"
        )

        self.business = Business.objects.create(
            name="Ресторан",
            public_chat_enabled=True
        )

        Membership.objects.create(
            user=self.owner,
            business=self.business,
            role="owner"
        )

        Membership.objects.create(
            user=self.other,
            business=self.business,
            role="staff"
        )

    def test_requires_login(self):
        response = self.client.get(
            reverse("connect_home")
        )

        self.assertEqual(response.status_code, 302)

    def test_owner_can_view_and_get_qr(self):
        self.client.force_login(self.owner)

        response = self.client.get(
            reverse("connect_home")
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            quote(self.business.slug)
        )

        qr_response = self.client.get(
            reverse("connect_qr")
        )

        self.assertEqual(qr_response.status_code, 200)

        self.assertTrue(
            qr_response.content.startswith(b"\x89PNG")
        )

    def test_staff_cannot_toggle(self):
        self.client.force_login(self.other)

        response = self.client.post(
            reverse("connect_toggle"),
            {"enabled": "0"}
        )

        self.assertEqual(response.status_code, 403)

    def test_owner_can_toggle(self):
        self.client.force_login(self.owner)

        self.client.post(
            reverse("connect_toggle"),
            {"enabled": "0"}
        )

        self.business.refresh_from_db()

        self.assertFalse(
            self.business.public_chat_enabled
        )

    def test_cross_business_isolation(self):
        other_business = Business.objects.create(
            name="Другой"
        )

        self.client.force_login(self.owner)

        response = self.client.get(
            reverse("connect_home"),
            {"business": other_business.pk}
        )

        self.assertEqual(response.status_code, 404)
