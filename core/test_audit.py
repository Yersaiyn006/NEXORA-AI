from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from assistant_ai.models import Conversation, Lead, Message
from business_brain.models import CatalogItem
from .models import Business, Membership


@override_settings(NEXORA_AI_ENABLED=False)
class AccessAuditTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username="audit_owner", password="StrongPass432!")
        self.staff = User.objects.create_user(username="audit_staff", password="StrongPass432!")
        self.foreign_user = User.objects.create_user(username="foreign_owner", password="StrongPass432!")
        self.business = Business.objects.create(name="Tagam", public_chat_enabled=True)
        self.foreign = Business.objects.create(name="Foreign", public_chat_enabled=True)
        Membership.objects.create(user=self.owner, business=self.business, role="owner")
        Membership.objects.create(user=self.staff, business=self.business, role="staff")
        Membership.objects.create(user=self.foreign_user, business=self.foreign, role="owner")
        self.chat = Conversation.objects.create(business=self.business, customer_name="Public:test")
        self.lead = Lead.objects.create(business=self.business, conversation=self.chat, customer_name="Арман", phone="+77771112233", status="new")

    def test_nonstaff_business_owner_can_sign_back_in(self):
        self.assertFalse(self.owner.is_staff)
        response = self.client.post(reverse("login"), {"username": "audit_owner", "password": "StrongPass432!"})
        self.assertRedirects(response, "/")
        self.assertEqual(self.client.get(reverse("business_studio")).status_code, 200)

    def test_logout_requires_post_and_owner_can_return(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 302)

    def test_login_does_not_accept_external_next_redirect(self):
        response = self.client.post(reverse("login"), {"username": "audit_owner", "password": "StrongPass432!", "next": "https://evil.example/"})
        self.assertEqual(response.url, "/")

    def test_auth_pages_have_private_cache_headers(self):
        self.client.force_login(self.owner)
        for url in ("/", "/leads/", "/studio/", "/brain/", "/connect/", "/ai/"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertIn("no-store", response["Cache-Control"])

    def test_invalid_tenant_selectors_are_404_not_500(self):
        self.client.force_login(self.owner)
        for url in ("/", "/leads/", "/studio/", "/brain/", "/connect/", "/ai/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, {"business": "broken"}).status_code, 404)

    def test_foreign_tenant_selectors_are_rejected_in_all_workspaces(self):
        self.client.force_login(self.owner)
        for url in ("/", "/leads/", "/studio/", "/brain/", "/connect/", "/ai/", "/radar/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, {"business": self.foreign.pk}).status_code, 404)

    def test_crm_search_works_and_remains_tenant_scoped(self):
        foreign_chat = Conversation.objects.create(business=self.foreign)
        Lead.objects.create(business=self.foreign, conversation=foreign_chat, customer_name="Арман SECRET_FOREIGN", status="new")
        self.client.force_login(self.owner)
        response = self.client.get("/studio/", {"business": self.business.pk, "q": "Арман"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Арман")
        self.assertNotContains(response, "SECRET_FOREIGN")

    def test_untimed_request_can_be_confirmed_from_both_crm_views(self):
        self.client.force_login(self.owner)
        for name, data in (("lead_status", {"status": "confirmed"}), ("studio_booking_action", {"action": "confirmed"})):
            with self.subTest(name=name):
                self.lead.status = "new"
                self.lead.save()
                data["business"] = self.business.pk
                self.assertEqual(self.client.post(reverse(name, args=[self.lead.pk]), data).status_code, 302)
                self.lead.refresh_from_db()
                self.assertEqual(self.lead.status, "confirmed")

    def test_staff_cannot_confirm_or_cancel_leads(self):
        self.client.force_login(self.staff)
        for name, data in (("lead_status", {"status": "confirmed"}), ("studio_booking_action", {"action": "cancelled"})):
            data["business"] = self.business.pk
            self.assertEqual(self.client.post(reverse(name, args=[self.lead.pk]), data).status_code, 403)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, "new")

    def test_cannot_change_foreign_lead_even_with_own_business_selector(self):
        self.client.force_login(self.foreign_user)
        self.assertEqual(self.client.post(reverse("lead_status", args=[self.lead.pk]), {"business": self.foreign.pk, "status": "confirmed"}).status_code, 404)

    def test_past_booking_cannot_be_confirmed(self):
        self.lead.requested_at = timezone.now() - timedelta(days=1)
        self.lead.save()
        self.client.force_login(self.owner)
        self.client.post(reverse("lead_status", args=[self.lead.pk]), {"business": self.business.pk, "status": "confirmed"})
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, "new")

    def test_negative_price_and_zero_duration_are_rejected(self):
        self.client.force_login(self.owner)
        for price, duration in (("-1", "30"), ("10", "0")):
            response = self.client.post(reverse("brain_item_save"), {"business": self.business.pk, "kind": "product", "name": "Invalid", "price": price, "duration_minutes": duration, "currency": "KZT"})
            self.assertEqual(response.status_code, 400)
        self.assertFalse(CatalogItem.objects.exists())

    def test_malformed_edit_item_ids_do_not_crash(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(reverse("brain_item_save"), {"business": self.business.pk, "item_id": "not-an-id"}).status_code, 404)
        self.assertEqual(self.client.post(reverse("studio_knowledge_save"), {"business": self.business.pk, "item_id": "not-an-id"}).status_code, 404)

    def test_dashboard_conversion_is_bounded_and_excludes_playground(self):
        Lead.objects.create(business=self.business, conversation=self.chat, status="new")
        demo = Conversation.objects.create(business=self.business, customer_name=f"Playground:{self.owner.pk}")
        Lead.objects.create(business=self.business, conversation=demo, status="confirmed")
        self.client.force_login(self.owner)
        response = self.client.get("/")
        self.assertEqual(response.context["conversion_rate"], 100)
        self.assertEqual(response.context["total_conversations"], 1)

    def test_owner_cannot_read_another_staff_playground(self):
        demo = Conversation.objects.create(business=self.business, customer_name=f"Playground:{self.staff.pk}")
        Message.objects.create(conversation=demo, role="customer", content="PRIVATE_STAFF")
        self.client.force_login(self.owner)
        response = self.client.get(reverse("ai_conversation_detail", args=[demo.pk]), {"business_id": self.business.pk})
        self.assertEqual(response.status_code, 404)

    def test_csrf_required_on_staff_mutation(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(reverse("lead_status", args=[self.lead.pk]), {"business": self.business.pk, "status": "confirmed"}).status_code, 403)

    def test_csrf_required_for_public_chat(self):
        client = Client(enforce_csrf_checks=True)
        url = reverse("public_chat_send", args=[self.business.slug])
        self.assertEqual(client.post(url, {"message": "Привет"}).status_code, 403)
        client.get(reverse("public_chat_page", args=[self.business.slug]))
        token = client.cookies["csrftoken"].value
        self.assertEqual(client.post(url, {"message": "Привет", "csrfmiddlewaretoken": token}).status_code, 200)

    def test_xss_payload_is_escaped_in_public_history(self):
        self.client.get(reverse("public_chat_page", args=[self.business.slug]))
        self.client.post(reverse("public_chat_send", args=[self.business.slug]), {"message": "<script>alert('xss')</script>"})
        response = self.client.get(reverse("public_chat_page", args=[self.business.slug]))
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>alert('xss')</script>")

    def test_playground_invalid_turn_id_returns_400(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("ai_send_message"), {"business_id": self.business.pk, "message": "Привет", "turn_id": "broken"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["conversation_id"], None)

    def test_playground_first_turn_retry_keeps_one_dialogue_and_one_provider_call(self):
        import uuid
        from unittest.mock import patch
        from assistant_ai.universal_engine import Result
        self.client.force_login(self.owner)
        data = {"business_id": self.business.pk, "message": "Что продаёте?", "turn_id": str(uuid.uuid4())}
        with patch("assistant_ai.views.respond", return_value=Result("Ответ", "gemini", 10)) as provider:
            first = self.client.post(reverse("ai_send_message"), data)
            # Simulates a lost first HTTP response: client still has no conversation_id.
            second = self.client.post(reverse("ai_send_message"), data)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.json()["conversation_id"], first.json()["conversation_id"])
        chat = Conversation.objects.get(pk=first.json()["conversation_id"])
        self.assertEqual(chat.messages.count(), 2)
        provider.assert_called_once()

    def test_playground_message_list_query_count_does_not_grow_per_dialogue(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        self.client.force_login(self.owner)
        url = reverse("ai_conversations")
        def add_dialogue(i):
            chat = Conversation.objects.create(business=self.business, customer_name=f"Playground:{self.owner.pk}")
            Message.objects.create(conversation=chat, role="customer", content=f"Вопрос {i}")
        add_dialogue(0)
        with CaptureQueriesContext(connection) as small:
            self.client.get(url, {"business_id": self.business.pk})
        for i in range(1, 15):
            add_dialogue(i)
        with CaptureQueriesContext(connection) as large:
            response = self.client.get(url, {"business_id": self.business.pk})
        self.assertEqual(len(response.json()["conversations"]), 15)
        self.assertEqual(len(small), len(large))
