from rest_framework import serializers
from django.utils import timezone

from datetime import timedelta


MIN_EXPIRATION_DELTA = timedelta(minutes=1)


class PollCreateSerializer(serializers.Serializer):
    question = serializers.CharField(min_length=1, max_length=255)
    options = serializers.ListField(
        child=serializers.CharField(min_length=1, max_length=255),
        min_length=2,
        max_length=20,
    )
    multi_select = serializers.BooleanField(default=False)
    expires_at = serializers.DateTimeField()

    def validate_question(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError('Question cannot be empty.')
        return value

    def validate_options(self, values):
        cleaned = []
        for item in values:
            text = item.strip()
            if not text:
                raise serializers.ValidationError('Each option must be a non-empty string.')
            cleaned.append(text)
        return cleaned

    def validate_expires_at(self, value):
        if value < timezone.now() + MIN_EXPIRATION_DELTA:
            raise serializers.ValidationError('Expiration time must be at least 1 minute in the future.')
        return value


class PollUpdateSerializer(serializers.Serializer):
    question = serializers.CharField(min_length=1, max_length=255)
    options = serializers.ListField(
        child=serializers.CharField(min_length=1, max_length=255),
        min_length=2,
        max_length=20,
    )
    multi_select = serializers.BooleanField(default=False)
    expires_at = serializers.DateTimeField()
    creator_token = serializers.CharField(min_length=20, max_length=200)

    def validate_question(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError('Question cannot be empty.')
        return value

    def validate_options(self, values):
        cleaned = []
        for item in values:
            text = item.strip()
            if not text:
                raise serializers.ValidationError('Each option must be a non-empty string.')
            cleaned.append(text)
        return cleaned

    def validate_expires_at(self, value):
        if value < timezone.now() + MIN_EXPIRATION_DELTA:
            raise serializers.ValidationError('Expiration time must be at least 1 minute in the future.')
        return value


class VoteSerializer(serializers.Serializer):
    voter_name = serializers.CharField(min_length=1, max_length=120)
    option_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=20,
    )

    def validate_voter_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError('Voter name is required.')
        return cleaned

    def validate_option_ids(self, values):
        unique_values = list(dict.fromkeys(values))
        return unique_values
