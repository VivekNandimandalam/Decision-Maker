import hashlib
import secrets
from html import escape

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Poll, PollOption, Vote
from .serializers import PollCreateSerializer, PollUpdateSerializer, VoteSerializer


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()


def _safe_text(value: str) -> str:
    return escape(value.strip())


def _is_expired(poll: Poll) -> bool:
    return poll.expires_at <= timezone.now()


def _poll_to_payload(poll: Poll) -> dict:
    options = poll.options.values('id', 'text', 'votes').order_by('id')
    options_payload = [
        {
            'id': str(option['id']),
            'text': option['text'],
            'votes': option['votes'],
        }
        for option in options
    ]
    total_votes = sum(option['votes'] for option in options_payload)
    winner = None
    if options_payload:
        winner = max(options_payload, key=lambda item: item['votes'])

    return {
        'id': str(poll.id),
        'question': poll.question,
        'multi_select': poll.multi_select,
        'expires_at': poll.expires_at,
        'is_expired': _is_expired(poll),
        'options': options_payload,
        'total_votes': total_votes,
        'winner': winner,
        'created_at': poll.created_at,
        'updated_at': poll.updated_at,
        'share_url': f'/poll/{poll.id}/',
    }


def _broadcast_poll_update(poll: Poll) -> None:
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    payload = _poll_to_payload(poll)
    async_to_sync(channel_layer.group_send)(
        f'poll_{poll.id}',
        {
            'type': 'poll.updated',
            'payload': payload,
        },
    )


def _create_poll_response(validated_data: dict) -> tuple[dict, int]:
    question = _safe_text(validated_data['question'])
    options = [_safe_text(option) for option in validated_data['options']]

    if len(set(options)) < 2:
        return {'detail': 'Options must be unique.'}, status.HTTP_400_BAD_REQUEST

    creator_token = secrets.token_urlsafe(32)
    creator_token_hash = _hash_token(creator_token)

    with transaction.atomic():
        poll = Poll.objects.create(
            question=question,
            multi_select=validated_data['multi_select'],
            expires_at=validated_data['expires_at'],
            creator_token_hash=creator_token_hash,
        )
        PollOption.objects.bulk_create([PollOption(poll=poll, text=text) for text in options])

    payload = _poll_to_payload(poll)
    payload['manage_url'] = f'/manage/{poll.id}?token={creator_token}'
    payload['creator_token'] = creator_token
    return payload, status.HTTP_201_CREATED


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({'status': 'ok'})


class PollListView(APIView):
    authentication_classes = []
    permission_classes = []

    @method_decorator(ratelimit(key='ip', rate='20/m', method='POST', block=True))
    def post(self, request):
        serializer = PollCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload, status_code = _create_poll_response(serializer.validated_data)
        return Response(payload, status=status_code)


class PollCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    @method_decorator(ratelimit(key='ip', rate='20/m', method='POST', block=True))
    def post(self, request):
        serializer = PollCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload, status_code = _create_poll_response(serializer.validated_data)
        return Response(payload, status=status_code)


class PollDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, poll_id):
        try:
            poll = Poll.objects.get(id=poll_id)
        except Poll.DoesNotExist:
            return Response({'detail': 'Poll not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(_poll_to_payload(poll))

    @method_decorator(ratelimit(key='ip', rate='10/m', method='PATCH', block=True))
    def patch(self, request, poll_id):
        serializer = PollUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            poll = Poll.objects.get(id=poll_id)
        except Poll.DoesNotExist:
            return Response({'detail': 'Poll not found.'}, status=status.HTTP_404_NOT_FOUND)

        incoming_hash = _hash_token(serializer.validated_data['creator_token'])
        if poll.creator_token_hash != incoming_hash:
            return Response({'detail': 'Invalid creator token.'}, status=status.HTTP_403_FORBIDDEN)

        options = [_safe_text(option) for option in serializer.validated_data['options']]
        if len(set(options)) < 2:
            return Response({'detail': 'Options must be unique.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            poll.question = _safe_text(serializer.validated_data['question'])
            poll.multi_select = serializer.validated_data['multi_select']
            poll.expires_at = serializer.validated_data['expires_at']
            poll.save(update_fields=['question', 'multi_select', 'expires_at', 'updated_at'])
            poll.options.all().delete()
            PollOption.objects.bulk_create([PollOption(poll=poll, text=text) for text in options])

        _broadcast_poll_update(poll)
        return Response(_poll_to_payload(poll))

    @method_decorator(ratelimit(key='ip', rate='10/m', method='DELETE', block=True))
    def delete(self, request, poll_id):
        creator_token = request.query_params.get('token', '')
        if not creator_token:
            return Response({'detail': 'Creator token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            poll = Poll.objects.get(id=poll_id)
        except Poll.DoesNotExist:
            return Response({'detail': 'Poll not found.'}, status=status.HTTP_404_NOT_FOUND)

        if poll.creator_token_hash != _hash_token(creator_token):
            return Response({'detail': 'Invalid creator token.'}, status=status.HTTP_403_FORBIDDEN)

        poll.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PollVoteView(APIView):
    authentication_classes = []
    permission_classes = []

    @method_decorator(ratelimit(key='ip', rate='30/m', method='POST', block=True))
    def post(self, request, poll_id):
        serializer = VoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            poll = Poll.objects.get(id=poll_id)
        except Poll.DoesNotExist:
            return Response({'detail': 'Poll not found.'}, status=status.HTTP_404_NOT_FOUND)

        if _is_expired(poll):
            return Response({'detail': 'This poll has expired.'}, status=status.HTTP_400_BAD_REQUEST)

        option_ids = serializer.validated_data['option_ids']
        if not poll.multi_select and len(option_ids) != 1:
            return Response(
                {'detail': 'This poll only allows one selected option.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        options = list(poll.options.filter(id__in=option_ids))
        if len(options) != len(option_ids):
            return Response({'detail': 'One or more options are invalid for this poll.'}, status=status.HTTP_400_BAD_REQUEST)

        voter_token = request.COOKIES.get('voter_token') or secrets.token_urlsafe(24)

        with transaction.atomic():
            if Vote.objects.filter(poll=poll, voter_token=voter_token).exists():
                return Response({'detail': 'You have already voted on this poll.'}, status=status.HTTP_409_CONFLICT)

            Vote.objects.bulk_create([
                Vote(poll=poll, option=option, voter_token=voter_token) for option in options
            ])

            for option in options:
                PollOption.objects.filter(id=option.id).update(votes=F('votes') + 1)

        poll.refresh_from_db()
        _broadcast_poll_update(poll)

        response = Response(_poll_to_payload(poll), status=status.HTTP_201_CREATED)
        if 'voter_token' not in request.COOKIES:
            response.set_cookie(
                'voter_token',
                voter_token,
                max_age=60 * 60 * 24 * 365,
                httponly=True,
                samesite='Lax',
            )
        return response
