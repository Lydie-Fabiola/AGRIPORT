import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Conversation, Message
from users.models import User

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message')
        sender_id = data.get('sender_id')
        mark_read = data.get('mark_read', False)

        if message and sender_id:
            msg = await self.create_message(sender_id, message)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': msg.content,
                    'sender_id': msg.sender.id,
                    'sender_email': msg.sender.email,
                    'sent_at': str(msg.sent_at),
                    'is_read': msg.is_read,
                }
            )
        elif mark_read:
            await self.mark_messages_read(sender_id)

    # Receive message from room group
    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def create_message(self, sender_id, message):
        sender = User.objects.get(id=sender_id)
        conversation = Conversation.objects.get(id=self.conversation_id)
        return Message.objects.create(conversation=conversation, sender=sender, content=message)

    @database_sync_to_async
    def mark_messages_read(self, user_id):
        conversation = Conversation.objects.get(id=self.conversation_id)
        Message.objects.filter(conversation=conversation).exclude(sender_id=user_id).update(is_read=True) 