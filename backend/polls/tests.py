from datetime import timedelta

from channels.layers import get_channel_layer
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Poll


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }
)
class PollApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _create_poll(self, **overrides):
        payload = {
            "question": "Where should we have lunch?",
            "options": ["Cafe", "Food court"],
            "multi_select": False,
            "expires_at": (timezone.now() + timedelta(minutes=5)).isoformat(),
        }
        payload.update(overrides)
        return self.client.post("/api/polls/create/", payload, format="json")

    def test_create_poll_and_fetch_results(self):
        create_response = self._create_poll()
        self.assertEqual(create_response.status_code, 201)
        payload = create_response.json()

        detail_response = self.client.get(f"/api/polls/{payload['id']}/")
        self.assertEqual(detail_response.status_code, 200)

        results_response = self.client.get(f"/api/polls/{payload['id']}/results/")
        self.assertEqual(results_response.status_code, 200)
        self.assertEqual(results_response.json()["vote_record_count"], 0)

    def test_create_poll_rejects_invalid_expiration_and_duplicate_options(self):
        short_expiration = self._create_poll(
            expires_at=(timezone.now() + timedelta(seconds=30)).isoformat(),
        )
        self.assertEqual(short_expiration.status_code, 400)

        duplicate_options = self._create_poll(options=["A", "A"])
        self.assertEqual(duplicate_options.status_code, 400)

    def test_single_select_vote_requires_name_and_blocks_duplicate_device_vote(self):
        create_response = self._create_poll()
        payload = create_response.json()
        poll_id = payload["id"]
        option_id = payload["options"][0]["id"]

        missing_name = self.client.post(
            f"/api/polls/{poll_id}/vote/",
            {"option_ids": [option_id]},
            format="json",
        )
        self.assertEqual(missing_name.status_code, 400)

        first_vote = self.client.post(
            f"/api/polls/{poll_id}/vote/",
            {"voter_name": "Alice", "option_ids": [option_id]},
            format="json",
        )
        self.assertEqual(first_vote.status_code, 201)
        self.assertIn("voter_device_token", first_vote.cookies)

        second_vote = self.client.post(
            f"/api/polls/{poll_id}/vote/",
            {"voter_name": "Alice Again", "option_ids": [option_id]},
            format="json",
        )
        self.assertEqual(second_vote.status_code, 409)

    def test_multi_select_poll_accepts_multiple_options(self):
        create_response = self._create_poll(
            question="Choose your favorite fruits",
            options=["Apple", "Banana", "Mango"],
            multi_select=True,
        )
        payload = create_response.json()

        vote_response = self.client.post(
            f"/api/polls/{payload['id']}/vote/",
            {
                "voter_name": "Mina",
                "option_ids": [payload["options"][0]["id"], payload["options"][1]["id"]],
            },
            format="json",
        )
        self.assertEqual(vote_response.status_code, 201)
        self.assertEqual(vote_response.json()["total_votes"], 2)
        self.assertEqual(vote_response.json()["vote_record_count"], 1)

    def test_expired_poll_rejects_vote(self):
        create_response = self._create_poll(expires_at=(timezone.now() + timedelta(minutes=1, seconds=5)).isoformat())
        poll_id = create_response.json()["id"]
        poll = Poll.objects.get(id=poll_id)
        poll.expires_at = timezone.now() - timedelta(seconds=5)
        poll.save(update_fields=["expires_at", "updated_at"])

        vote_response = self.client.post(
            f"/api/polls/{poll_id}/vote/",
            {"voter_name": "Late voter", "option_ids": [str(poll.options.first().id)]},
            format="json",
        )
        self.assertEqual(vote_response.status_code, 400)

    def test_creator_can_edit_and_delete_with_valid_token(self):
        create_response = self._create_poll()
        payload = create_response.json()
        poll_id = payload["id"]
        creator_token = payload["creator_token"]

        forbidden_edit = self.client.patch(
            f"/api/polls/{poll_id}/",
            {
                "question": "Updated question",
                "options": ["One", "Two"],
                "multi_select": False,
                "expires_at": (timezone.now() + timedelta(minutes=10)).isoformat(),
                "creator_token": "x" * 24,
            },
            format="json",
        )
        self.assertEqual(forbidden_edit.status_code, 403)

        allowed_edit = self.client.patch(
            f"/api/polls/{poll_id}/",
            {
                "question": "Updated question",
                "options": ["One", "Two"],
                "multi_select": True,
                "expires_at": (timezone.now() + timedelta(minutes=10)).isoformat(),
                "creator_token": creator_token,
            },
            format="json",
        )
        self.assertEqual(allowed_edit.status_code, 200)
        self.assertEqual(allowed_edit.json()["question"], "Updated question")

        forbidden_delete = self.client.delete(f"/api/polls/{poll_id}/?token=bad-token")
        self.assertEqual(forbidden_delete.status_code, 403)

        allowed_delete = self.client.delete(f"/api/polls/{poll_id}/?token={creator_token}")
        self.assertEqual(allowed_delete.status_code, 204)

    def test_expired_poll_marks_notification_timestamp(self):
        create_response = self._create_poll(expires_at=(timezone.now() + timedelta(minutes=1, seconds=1)).isoformat())
        poll = Poll.objects.get(id=create_response.json()["id"])
        poll.expires_at = timezone.now() - timedelta(seconds=2)
        poll.save(update_fields=["expires_at", "updated_at"])

        response = self.client.get(f"/api/polls/{poll.id}/results/")
        self.assertEqual(response.status_code, 200)
        poll.refresh_from_db()
        self.assertIsNotNone(poll.expired_notified_at)

    def test_channel_layer_is_available_for_realtime_contract(self):
        self.assertIsNotNone(get_channel_layer())
