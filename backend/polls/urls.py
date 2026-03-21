from django.urls import path

from .views import (
    HealthCheckView,
    PollCreateView,
    PollDetailView,
    PollListView,
    PollResultsView,
    PollVoteView,
)

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health'),
    path('polls/', PollListView.as_view(), name='polls'),
    path('polls/create/', PollCreateView.as_view(), name='poll-create'),
    path('polls/<uuid:poll_id>/', PollDetailView.as_view(), name='poll-detail'),
    path('polls/<uuid:poll_id>/results/', PollResultsView.as_view(), name='poll-results'),
    path('polls/<uuid:poll_id>/vote/', PollVoteView.as_view(), name='poll-vote'),
]
