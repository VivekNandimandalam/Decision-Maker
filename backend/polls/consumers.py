import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Poll

logger = logging.getLogger(__name__)


class PollConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.poll_id = self.scope['url_route']['kwargs']['poll_id']
            self.group_name = f'poll_{self.poll_id}'
            logger.info(f"WebSocket connect attempt for poll_id: {self.poll_id}")
            logger.info(f"Scope path: {self.scope.get('path')}")
            logger.info(f"Channel name: {self.channel_name}")

            poll_exists = await self._poll_exists(self.poll_id)
            logger.info(f"Poll exists: {poll_exists}")
            
            if not poll_exists:
                logger.warning(f"Poll {self.poll_id} not found, closing connection")
                await self.close(code=4004)
                return

            logger.info(f"Adding to group: {self.group_name}")
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            
            logger.info(f"Accepting WebSocket connection")
            await self.accept()
            logger.info(f"WebSocket connected for poll_id: {self.poll_id}")
        except Exception as e:
            logger.exception(f"Error in WebSocket connect: {e}")
            try:
                await self.close(code=1001)
            except Exception as close_error:
                logger.exception(f"Error closing connection: {close_error}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # This consumer is broadcast-only; clients do not send events.
        return

    async def poll_event(self, event):
        await self.send(
            text_data=json.dumps(
                {"type": event["event_type"], "payload": event["payload"]},
                default=str,
            )
        )

    @staticmethod
    @database_sync_to_async
    def _poll_exists(poll_id: str) -> bool:
        return Poll.objects.filter(id=poll_id).exists()
