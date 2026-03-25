# WebSocket routing disabled - using HTTP polling instead
# This file is kept for backwards compatibility but not used

from django.urls import re_path

# Legacy WebSocket consumer (no longer used)
# from .consumers import PollConsumer

# websocket_urlpatterns = [
#     re_path(r'^ws/polls/(?P<poll_id>[\w-]+)/$', PollConsumer.as_asgi()),
# ]

websocket_urlpatterns = []
