
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import Business, Membership


User = get_user_model()


class BusinessRegistrationTests(TestCase):

    def registration_data(self, **overrides):
        data = {
            "username": "testowner",
            "email": "owner@example.com",
            "company_name": "Test Business",
            "industry": "Services",
            "password1": "StrongTestPassword123!",
            "password2": "StrongTestPassword123!",
        }
        data.update(overrides)
        return data

    def test_registration_page_opens(self):
        response = self.client.get(reverse("register"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "core/register.html",
        )

    @patch(
        "core.registration.consume",
        return_value=True,
    )
    def test_creates_owner_and_business(self, mocked_consume):
        response = self.client.post(
            reverse("register"),
            self.registration_data(),
        )

        user = User.objects.get(username="testowner")
        business = Business.objects.get(name="Test Business")

        self.assertTrue(
            Membership.objects.filter(
                user=user,
                business=business,
                role="owner",
            ).exists()
        )

        self.assertFalse(business.public_chat_enabled)

        self.assertRedirects(
            response,
            reverse(
                "launch_setup",
                args=[business.pk],
            ),
            fetch_redirect_response=False,
        )

    @patch(
        "core.registration.consume",
        return_value=True,
    )
    def test_duplicate_email_is_rejected(self, mocked_consume):
        User.objects.create_user(
            username="existing",
            email="owner@example.com",
            password="ExistingPassword123!",
        )

        response = self.client.post(
            reverse("register"),
            self.registration_data(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Business.objects.filter(
                name="Test Business"
            ).count(),
            0,
        )

    @patch(
        "core.registration.consume",
        return_value=True,
    )
    def test_password_mismatch_is_rejected(self, mocked_consume):
        response = self.client.post(
            reverse("register"),
            self.registration_data(
                password2="DifferentPassword123!",
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            User.objects.filter(
                username="testowner"
            ).exists()
        )

    @patch(
        "core.registration.consume",
        return_value=False,
    )
    def test_registration_rate_limit(self, mocked_consume):
        response = self.client.post(
            reverse("register"),
            self.registration_data(),
        )

        self.assertEqual(response.status_code, 429)
        self.assertEqual(
            User.objects.filter(
                username="testowner"
            ).count(),
            0,
        )
