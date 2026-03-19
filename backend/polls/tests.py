from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient


class PollApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()

	def test_create_get_and_vote_flow(self):
		expires_at = (timezone.now() + timedelta(hours=1)).isoformat()
		create_response = self.client.post(
			'/api/polls/create/',
			{
				'question': 'Where should we have lunch?',
				'options': ['Cafe', 'Food court'],
				'multi_select': False,
				'expires_at': expires_at,
			},
			format='json',
		)
		self.assertEqual(create_response.status_code, 201)
		payload = create_response.json()

		poll_id = payload['id']
		option_id = payload['options'][0]['id']

		get_response = self.client.get(f'/api/polls/{poll_id}/')
		self.assertEqual(get_response.status_code, 200)

		vote_response = self.client.post(
			f'/api/polls/{poll_id}/vote/',
			{'option_ids': [option_id]},
			format='json',
		)
		self.assertEqual(vote_response.status_code, 201)

	def test_duplicate_vote_is_blocked(self):
		expires_at = (timezone.now() + timedelta(hours=1)).isoformat()
		create_response = self.client.post(
			'/api/polls/create/',
			{
				'question': 'What movie should we watch?',
				'options': ['Action', 'Comedy'],
				'multi_select': False,
				'expires_at': expires_at,
			},
			format='json',
		)
		self.assertEqual(create_response.status_code, 201)
		payload = create_response.json()

		poll_id = payload['id']
		option_id = payload['options'][0]['id']

		first_vote = self.client.post(
			f'/api/polls/{poll_id}/vote/',
			{'option_ids': [option_id]},
			format='json',
		)
		self.assertEqual(first_vote.status_code, 201)

		second_vote = self.client.post(
			f'/api/polls/{poll_id}/vote/',
			{'option_ids': [option_id]},
			format='json',
		)
		self.assertEqual(second_vote.status_code, 409)

	def test_create_poll_rejects_empty_question(self):
		expires_at = (timezone.now() + timedelta(hours=1)).isoformat()
		response = self.client.post(
			'/api/polls/create/',
			{
				'question': '   ',
				'options': ['Option A', 'Option B'],
				'multi_select': False,
				'expires_at': expires_at,
			},
			format='json',
		)
		self.assertEqual(response.status_code, 400)

	def test_create_poll_rejects_option_count_outside_range(self):
		expires_at = (timezone.now() + timedelta(hours=1)).isoformat()
		too_few = self.client.post(
			'/api/polls/create/',
			{
				'question': 'Question',
				'options': ['Only one'],
				'multi_select': False,
				'expires_at': expires_at,
			},
			format='json',
		)
		self.assertEqual(too_few.status_code, 400)

		too_many_options = [f'Option {index}' for index in range(1, 22)]
		too_many = self.client.post(
			'/api/polls/create/',
			{
				'question': 'Question',
				'options': too_many_options,
				'multi_select': False,
				'expires_at': expires_at,
			},
			format='json',
		)
		self.assertEqual(too_many.status_code, 400)

	def test_vote_rejected_for_expired_poll(self):
		expires_at = (timezone.now() - timedelta(minutes=1)).isoformat()
		create_response = self.client.post(
			'/api/polls/create/',
			{
				'question': 'Expired poll',
				'options': ['A', 'B'],
				'multi_select': False,
				'expires_at': expires_at,
			},
			format='json',
		)
		self.assertEqual(create_response.status_code, 400)

	def test_multi_select_poll_accepts_multiple_options(self):
		expires_at = (timezone.now() + timedelta(hours=1)).isoformat()
		create_response = self.client.post(
			'/api/polls/create/',
			{
				'question': 'Choose your favorite fruits',
				'options': ['Apple', 'Banana', 'Mango'],
				'multi_select': True,
				'expires_at': expires_at,
			},
			format='json',
		)
		self.assertEqual(create_response.status_code, 201)
		payload = create_response.json()
		poll_id = payload['id']
		option_ids = [payload['options'][0]['id'], payload['options'][1]['id']]

		vote_response = self.client.post(
			f'/api/polls/{poll_id}/vote/',
			{'option_ids': option_ids},
			format='json',
		)
		self.assertEqual(vote_response.status_code, 201)
