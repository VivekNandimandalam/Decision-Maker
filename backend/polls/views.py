import hashlib
import logging
import secrets
from html import escape

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Poll, PollOption, VoteRecord
from .serializers import PollCreateSerializer, PollUpdateSerializer, VoteSerializer

logger = logging.getLogger(__name__)


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _safe_text(value: str) -> str:
    return escape(value.strip())


def _is_expired(poll: Poll) -> bool:
    return poll.expires_at <= timezone.now()


def _poll_to_payload(poll: Poll, device_token_hash: str = None) -> dict:
    options = poll.options.values("id", "text", "votes").order_by("id")
    options_payload = [
        {
            "id": str(option["id"]),
            "text": option["text"],
            "votes": option["votes"],
        }
        for option in options
    ]

    vote_records = poll.vote_records.order_by("created_at").values(
        "voter_name",
        "option_id",
        "created_at",
        "device_token_hash",
    )
    selections_by_voter: dict[str, dict] = {}
    latest_vote_at = None
    for record in vote_records:
        created_at = record["created_at"]
        latest_vote_at = created_at if latest_vote_at is None or created_at > latest_vote_at else latest_vote_at
        key = record["device_token_hash"]
        if key not in selections_by_voter:
            selections_by_voter[key] = {
                "voter_name": record["voter_name"],
                "option_ids": [],
                "created_at": created_at,
            }

        selections_by_voter[key]["option_ids"].append(str(record["option_id"]))
        if created_at > selections_by_voter[key]["created_at"]:
            selections_by_voter[key]["created_at"] = created_at

    voter_activity = list(selections_by_voter.values())

    total_votes = sum(option["votes"] for option in options_payload)
    
    payload = {
        "id": str(poll.id),
        "question": poll.question,
        "multi_select": poll.multi_select,
        "expires_at": poll.expires_at,
        "is_expired": _is_expired(poll),
        "options": options_payload,
        "total_votes": total_votes,
        "vote_record_count": len(voter_activity),
        "recent_voters": voter_activity[-10:],
        "share_url": f"/poll/{poll.id}/",
        "created_at": poll.created_at,
        "updated_at": poll.updated_at,
        "expired_notified_at": poll.expired_notified_at,
        "latest_vote_at": latest_vote_at,
        "has_user_voted": bool(device_token_hash and device_token_hash in selections_by_voter),
    }
    return payload

def _mark_expired_if_needed(poll: Poll) -> bool:
    if not _is_expired(poll) or poll.expired_notified_at is not None:
        return False

    poll.expired_notified_at = timezone.now()
    poll.save(update_fields=["expired_notified_at", "updated_at"])
    poll.refresh_from_db()
    # WebSocket broadcast removed - using HTTP polling instead
    return True


def _get_poll_or_404(poll_id):
    try:
        return Poll.objects.get(id=poll_id)
    except Poll.DoesNotExist:
        return None


def _ensure_creator_access(poll: Poll, creator_token: str) -> bool:
    return bool(creator_token) and poll.creator_token_hash == _hash_token(creator_token)


def _create_poll_response(validated_data: dict) -> tuple[dict, int]:
    question = _safe_text(validated_data["question"])
    options = [_safe_text(option) for option in validated_data["options"]]

    if len(set(options)) < 2:
        return {"detail": "Options must be unique."}, status.HTTP_400_BAD_REQUEST

    creator_token = secrets.token_urlsafe(32)
    creator_token_hash = _hash_token(creator_token)

    with transaction.atomic():
        poll = Poll.objects.create(
            question=question,
            multi_select=validated_data["multi_select"],
            expires_at=validated_data["expires_at"],
            creator_token_hash=creator_token_hash,
        )
        PollOption.objects.bulk_create([PollOption(poll=poll, text=text) for text in options])

    payload = _poll_to_payload(poll)
    payload["manage_url"] = f"/manage/{poll.id}/"
    payload["creator_token"] = creator_token
    return payload, status.HTTP_201_CREATED


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "ok"})


class PollListView(APIView):
    authentication_classes = []
    permission_classes = []

    @method_decorator(ratelimit(key="ip", rate="20/m", method="POST", block=True))
    def post(self, request):
        serializer = PollCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload, status_code = _create_poll_response(serializer.validated_data)
        return Response(payload, status=status_code)


class PollCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    @method_decorator(ratelimit(key="ip", rate="20/m", method="POST", block=True))
    def post(self, request):
        serializer = PollCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload, status_code = _create_poll_response(serializer.validated_data)
        return Response(payload, status=status_code)


class PollDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, poll_id):
        poll = _get_poll_or_404(poll_id)
        if poll is None:
            return Response({"detail": "Poll not found."}, status=status.HTTP_404_NOT_FOUND)

        _mark_expired_if_needed(poll)
        poll.refresh_from_db()
        
        # Include voting status for the current device
        device_token = request.COOKIES.get("voter_device_token")
        device_token_hash = _hash_token(device_token) if device_token else None
        
        return Response(_poll_to_payload(poll, device_token_hash))

    @method_decorator(ratelimit(key="ip", rate="10/m", method="PATCH", block=True))
    def patch(self, request, poll_id):
        serializer = PollUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        poll = _get_poll_or_404(poll_id)
        if poll is None:
            return Response({"detail": "Poll not found."}, status=status.HTTP_404_NOT_FOUND)

        if not _ensure_creator_access(poll, serializer.validated_data["creator_token"]):
            return Response({"detail": "Invalid creator token."}, status=status.HTTP_403_FORBIDDEN)

        options = [_safe_text(option) for option in serializer.validated_data["options"]]
        if len(set(options)) < 2:
            return Response({"detail": "Options must be unique."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            poll.question = _safe_text(serializer.validated_data["question"])
            poll.multi_select = serializer.validated_data["multi_select"]
            poll.expires_at = serializer.validated_data["expires_at"]
            poll.expired_notified_at = None
            poll.save(update_fields=["question", "multi_select", "expires_at", "expired_notified_at", "updated_at"])
            poll.options.all().delete()
            PollOption.objects.bulk_create([PollOption(poll=poll, text=text) for text in options])
            poll.vote_records.all().delete()

        poll.refresh_from_db()
        # WebSocket broadcast removed - using HTTP polling instead
        return Response(_poll_to_payload(poll))

    @method_decorator(ratelimit(key="ip", rate="10/m", method="DELETE", block=True))
    def delete(self, request, poll_id):
        creator_token = request.query_params.get("token", "")
        poll = _get_poll_or_404(poll_id)
        if poll is None:
            return Response({"detail": "Poll not found."}, status=status.HTTP_404_NOT_FOUND)

        if not _ensure_creator_access(poll, creator_token):
            return Response({"detail": "Invalid creator token."}, status=status.HTTP_403_FORBIDDEN)

        poll_identifier = str(poll.id)
        poll.delete()
        # WebSocket broadcast removed - using HTTP polling instead
        return Response(status=status.HTTP_204_NO_CONTENT)


class PollResultsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, poll_id):
        poll = _get_poll_or_404(poll_id)
        if poll is None:
            return Response({"detail": "Poll not found."}, status=status.HTTP_404_NOT_FOUND)

        _mark_expired_if_needed(poll)
        poll.refresh_from_db()
        return Response(_poll_to_payload(poll))


class PollVoteView(APIView):
    authentication_classes = []
    permission_classes = []

    @method_decorator(ratelimit(key="ip", rate="30/m", method="POST", block=True))
    def post(self, request, poll_id):
        serializer = VoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        poll = _get_poll_or_404(poll_id)
        if poll is None:
            return Response({"detail": "Poll not found."}, status=status.HTTP_404_NOT_FOUND)

        _mark_expired_if_needed(poll)
        poll.refresh_from_db()
        if _is_expired(poll):
            return Response({"detail": "This poll has expired."}, status=status.HTTP_400_BAD_REQUEST)

        option_ids = serializer.validated_data["option_ids"]
        if not poll.multi_select and len(option_ids) != 1:
            return Response(
                {"detail": "This poll only allows one selected option."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        options = list(poll.options.filter(id__in=option_ids))
        if len(options) != len(option_ids):
            return Response({"detail": "One or more options are invalid for this poll."}, status=status.HTTP_400_BAD_REQUEST)

        device_token = request.COOKIES.get("voter_device_token") or secrets.token_urlsafe(24)
        device_token_hash = _hash_token(device_token)

        logger.info(f"Vote attempt - Poll: {poll.id}")
        logger.info(f"Device token from cookie: {request.COOKIES.get('voter_device_token') is not None}")
        logger.info(f"Device token hash: {device_token_hash[:10]}...")
        logger.info(f"All cookies: {list(request.COOKIES.keys())}")

        with transaction.atomic():
            existing_vote = VoteRecord.objects.filter(poll=poll, device_token_hash=device_token_hash).exists()
            logger.info(f"Existing vote found: {existing_vote}")
            
            if existing_vote:
                logger.warning(f"Duplicate vote attempt for poll {poll.id} from device {device_token_hash[:10]}...")
                return Response(
                    {"detail": "You have already submitted your vote."},
                    status=status.HTTP_409_CONFLICT,
                )

            VoteRecord.objects.bulk_create(
                [
                    VoteRecord(
                        poll=poll,
                        option=option,
                        voter_name=_safe_text(serializer.validated_data["voter_name"]),
                        device_token_hash=device_token_hash,
                    )
                    for option in options
                ]
            )

            for option in options:
                PollOption.objects.filter(id=option.id).update(votes=F("votes") + 1)

        poll.refresh_from_db()
        # WebSocket broadcast removed - using HTTP polling instead

        response = Response(_poll_to_payload(poll, device_token_hash), status=status.HTTP_201_CREATED)
        if "voter_device_token" not in request.COOKIES:
            response.set_cookie(
                "voter_device_token",
                device_token,
                max_age=60 * 60 * 24 * 365,
                httponly=True,
                samesite="Lax",
                secure=False,  # Development: localhost without HTTPS
            )
        return response
