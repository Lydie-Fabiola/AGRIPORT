import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Notification

class NotificationsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope['user'].is_anonymous:
            await self.close()
        else:
            self.user = self.scope['user']
            self.group_name = f'notifications_{self.user.id}'
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # No-op: notifications are pushed from server
        pass

    async def notify(self, event):
        await self.send(text_data=json.dumps(event['notification']))

    @database_sync_to_async
    def get_latest_notifications(self):
        return list(Notification.objects.filter(user=self.user, is_read=False).values()) 