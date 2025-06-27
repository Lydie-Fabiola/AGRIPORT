"""
WebSocket consumers for real-time messaging.
"""
import json
import asyncio
from datetime import timedelta
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from .models import (
    Conversation, Message, MessageRead, TypingIndicator, UserOnlineStatus
)
from .serializers import MessageSerializer, TypingIndicatorSerializer

User = get_user_model()


class MessagingConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time messaging.
    """
    
    async def connect(self):
        """Handle WebSocket connection."""
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.conversation_group_name = f'conversation_{self.conversation_id}'
        self.user = self.scope['user']
        
        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Check if user is participant in conversation
        is_participant = await self.check_conversation_participant()
        if not is_participant:
            await self.close()
            return
        
        # Join conversation group
        await self.channel_layer.group_add(
            self.conversation_group_name,
            self.channel_name
        )
        
        # Update user online status
        await self.update_user_online_status(True)
        
        # Accept connection
        await self.accept()
        
        # Notify other participants that user is online
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'user_status_update',
                'user_id': self.user.id,
                'is_online': True,
                'timestamp': timezone.now().isoformat()
            }
        )
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'conversation_group_name'):
            # Leave conversation group
            await self.channel_layer.group_discard(
                self.conversation_group_name,
                self.channel_name
            )
            
            # Update user online status
            await self.update_user_online_status(False)
            
            # Clear typing indicator
            await self.clear_typing_indicator()
            
            # Notify other participants that user is offline
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'user_status_update',
                    'user_id': self.user.id,
                    'is_online': False,
                    'timestamp': timezone.now().isoformat()
                }
            )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'send_message':
                await self.handle_send_message(data)
            elif message_type == 'typing_start':
                await self.handle_typing_start(data)
            elif message_type == 'typing_stop':
                await self.handle_typing_stop(data)
            elif message_type == 'mark_read':
                await self.handle_mark_read(data)
            elif message_type == 'ping':
                await self.handle_ping(data)
            else:
                await self.send_error('Unknown message type')
                
        except json.JSONDecodeError:
            await self.send_error('Invalid JSON')
        except Exception as e:
            await self.send_error(f'Error processing message: {str(e)}')
    
    async def handle_send_message(self, data):
        """Handle sending a new message."""
        content = data.get('content', '').strip()
        message_type = data.get('message_type', 'text')
        reply_to_id = data.get('reply_to_id')
        
        if not content:
            await self.send_error('Message content cannot be empty')
            return
        
        # Create message
        message = await self.create_message(content, message_type, reply_to_id)
        if not message:
            await self.send_error('Failed to create message')
            return
        
        # Serialize message
        message_data = await self.serialize_message(message)
        
        # Broadcast message to conversation group
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'new_message',
                'message': message_data,
                'sender_id': self.user.id
            }
        )
    
    async def handle_typing_start(self, data):
        """Handle typing start indicator."""
        await self.set_typing_indicator(True)
        
        # Broadcast typing indicator to other participants
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'is_typing': True,
                'timestamp': timezone.now().isoformat()
            }
        )
    
    async def handle_typing_stop(self, data):
        """Handle typing stop indicator."""
        await self.set_typing_indicator(False)
        
        # Broadcast typing stop to other participants
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'is_typing': False,
                'timestamp': timezone.now().isoformat()
            }
        )
    
    async def handle_mark_read(self, data):
        """Handle marking messages as read."""
        message_ids = data.get('message_ids', [])
        
        if message_ids:
            await self.mark_messages_read(message_ids)
            
            # Broadcast read status update
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'messages_read',
                    'user_id': self.user.id,
                    'message_ids': message_ids,
                    'timestamp': timezone.now().isoformat()
                }
            )
    
    async def handle_ping(self, data):
        """Handle ping to keep connection alive."""
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'timestamp': timezone.now().isoformat()
        }))
    
    # Group message handlers
    
    async def new_message(self, event):
        """Send new message to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': event['message'],
            'sender_id': event['sender_id']
        }))
    
    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket."""
        # Don't send typing indicator to the sender
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing_indicator',
                'user_id': event['user_id'],
                'is_typing': event['is_typing'],
                'timestamp': event['timestamp']
            }))
    
    async def user_status_update(self, event):
        """Send user status update to WebSocket."""
        # Don't send status update to the user themselves
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_status_update',
                'user_id': event['user_id'],
                'is_online': event['is_online'],
                'timestamp': event['timestamp']
            }))
    
    async def messages_read(self, event):
        """Send message read status update to WebSocket."""
        # Don't send read status to the reader themselves
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'messages_read',
                'user_id': event['user_id'],
                'message_ids': event['message_ids'],
                'timestamp': event['timestamp']
            }))
    
    # Helper methods
    
    async def send_error(self, message):
        """Send error message to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
            'timestamp': timezone.now().isoformat()
        }))
    
    @database_sync_to_async
    def check_conversation_participant(self):
        """Check if user is participant in conversation."""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return conversation.participants.filter(
                id=self.user.id,
                conversationparticipant__is_active=True
            ).exists()
        except Conversation.DoesNotExist:
            return False
    
    @database_sync_to_async
    def create_message(self, content, message_type, reply_to_id):
        """Create a new message."""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            
            reply_to = None
            if reply_to_id:
                try:
                    reply_to = Message.objects.get(
                        id=reply_to_id,
                        conversation=conversation
                    )
                except Message.DoesNotExist:
                    pass
            
            message = Message.objects.create(
                conversation=conversation,
                sender=self.user,
                content=content,
                message_type=message_type,
                reply_to=reply_to
            )
            return message
        except Exception:
            return None
    
    @database_sync_to_async
    def serialize_message(self, message):
        """Serialize message for WebSocket transmission."""
        serializer = MessageSerializer(message)
        return serializer.data
    
    @database_sync_to_async
    def update_user_online_status(self, is_online):
        """Update user online status."""
        status, created = UserOnlineStatus.objects.get_or_create(
            user=self.user,
            defaults={'is_online': is_online}
        )
        if not created:
            status.is_online = is_online
            status.save()
    
    @database_sync_to_async
    def set_typing_indicator(self, is_typing):
        """Set typing indicator for user."""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            
            if is_typing:
                indicator, created = TypingIndicator.objects.get_or_create(
                    conversation=conversation,
                    user=self.user,
                    defaults={
                        'is_typing': True,
                        'expires_at': timezone.now() + timedelta(seconds=10)
                    }
                )
                if not created:
                    indicator.is_typing = True
                    indicator.expires_at = timezone.now() + timedelta(seconds=10)
                    indicator.save()
            else:
                TypingIndicator.objects.filter(
                    conversation=conversation,
                    user=self.user
                ).delete()
        except Exception:
            pass
    
    @database_sync_to_async
    def clear_typing_indicator(self):
        """Clear typing indicator for user."""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            TypingIndicator.objects.filter(
                conversation=conversation,
                user=self.user
            ).delete()
        except Exception:
            pass
    
    @database_sync_to_async
    def mark_messages_read(self, message_ids):
        """Mark messages as read by user."""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            messages = Message.objects.filter(
                id__in=message_ids,
                conversation=conversation
            ).exclude(sender=self.user)
            
            for message in messages:
                MessageRead.objects.get_or_create(
                    message=message,
                    user=self.user
                )
        except Exception:
            pass


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for general notifications.
    """
    
    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope['user']
        
        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.user_group_name = f'user_{self.user.id}'
        
        # Join user group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        # Accept connection
        await self.accept()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'user_group_name'):
            # Leave user group
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': timezone.now().isoformat()
                }))
        except json.JSONDecodeError:
            pass
    
    # Notification handlers
    
    async def new_message_notification(self, event):
        """Send new message notification."""
        await self.send(text_data=json.dumps({
            'type': 'new_message_notification',
            'conversation_id': event['conversation_id'],
            'sender_name': event['sender_name'],
            'message_preview': event['message_preview'],
            'timestamp': event['timestamp']
        }))
    
    async def order_update_notification(self, event):
        """Send order update notification."""
        await self.send(text_data=json.dumps({
            'type': 'order_update_notification',
            'order_id': event['order_id'],
            'order_number': event['order_number'],
            'status': event['status'],
            'message': event['message'],
            'timestamp': event['timestamp']
        }))
    
    async def general_notification(self, event):
        """Send general notification."""
        await self.send(text_data=json.dumps({
            'type': 'general_notification',
            'title': event['title'],
            'message': event['message'],
            'category': event.get('category', 'general'),
            'timestamp': event['timestamp']
        }))
