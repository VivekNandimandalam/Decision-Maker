import json

from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.exceptions import ObjectDoesNotExist

from .models import Poll


class PollConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.poll_id = self.scope['url_route']['kwargs']['poll_id']
        self.group_name = f'poll_{self.poll_id}'

        poll_exists = await self._poll_exists(self.poll_id)
        if not poll_exists:
            await self.close(code=4004)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # This consumer is broadcast-only; clients do not send events.
        return

    async def poll_updated(self, event):
        await self.send(text_data=json.dumps({'type': 'poll.updated', 'payload': event['payload']}, default=str))

    @staticmethod
    async def _poll_exists(poll_id: str) -> bool:
        try:
            return await Poll.objects.filter(id=poll_id).aexists()
        except ObjectDoesNotExist:
            return False
