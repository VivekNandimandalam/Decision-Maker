import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone


def default_poll_expiration():
	return timezone.now() + timedelta(hours=1)


class Poll(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	question = models.CharField(max_length=255)
	multi_select = models.BooleanField(default=False)
	expires_at = models.DateTimeField(default=default_poll_expiration)
	creator_token_hash = models.CharField(max_length=64)
	expired_notified_at = models.DateTimeField(blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']


class PollOption(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='options')
	text = models.CharField(max_length=255)
	votes = models.IntegerField(default=0)


class VoteRecord(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='vote_records')
	option = models.ForeignKey(PollOption, on_delete=models.CASCADE, related_name='vote_records')
	voter_name = models.CharField(max_length=120)
	device_token_hash = models.CharField(max_length=64)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['poll', 'device_token_hash', 'option'], name='unique_option_vote_per_device'),
		]
