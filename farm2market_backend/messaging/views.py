"""
Views for messaging system.
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Max
from django.utils import timezone
from apps.core.responses import StandardResponse
from apps.core.exceptions import ValidationError, NotFoundError
from .models import (
    Conversation, ConversationParticipant, Message, MessageRead,
    MessageTemplate, UserOnlineStatus, TypingIndicator
)
from .serializers import (
    ConversationSerializer, ConversationCreateSerializer, MessageSerializer,
    MessageCreateSerializer, MessageTemplateSerializer, MarkAsReadSerializer,
    UnreadCountSerializer, OnlineStatusSerializer
)

User = get_user_model()


class ConversationViewSet(ModelViewSet):
    """
    Conversation management viewset.
    """
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get conversations for authenticated user."""
        return Conversation.objects.filter(
            participants=self.request.user,
            conversationparticipant__is_active=True,
            is_active=True
        ).select_related(
            'related_product', 'related_order'
        ).prefetch_related(
            'participants', 'conversationparticipant_set'
        ).annotate(
            last_message_time=Max('messages__created_at')
        ).order_by('-last_message_time', '-created_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ConversationCreateSerializer
        return ConversationSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new conversation."""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            conversation = serializer.save()
            response_serializer = ConversationSerializer(
                conversation, 
                context={'request': request}
            )
            
            return StandardResponse.created(
                data=response_serializer.data,
                message='Conversation created successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Conversation creation failed.'
        )
    
    def update(self, request, *args, **kwargs):
        """Update conversation (limited fields)."""
        instance = self.get_object()
        
        # Only allow updating subject and is_active
        allowed_fields = ['subject', 'is_active']
        filtered_data = {k: v for k, v in request.data.items() if k in allowed_fields}
        
        serializer = self.get_serializer(instance, data=filtered_data, partial=True)
        if serializer.is_valid():
            self.perform_update(serializer)
            return StandardResponse.updated(
                data=serializer.data,
                message='Conversation updated successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Conversation update failed.'
        )
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get messages in a conversation."""
        conversation = self.get_object()
        
        # Check if user is participant
        if not conversation.participants.filter(
            id=request.user.id,
            conversationparticipant__is_active=True
        ).exists():
            return StandardResponse.error(
                message='You are not a participant in this conversation.',
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Get messages with pagination
        page_size = min(int(request.query_params.get('page_size', 50)), 100)
        page = int(request.query_params.get('page', 1))
        
        messages = conversation.messages.select_related(
            'sender', 'reply_to'
        ).prefetch_related('read_by').order_by('-created_at')
        
        start = (page - 1) * page_size
        end = start + page_size
        
        total_count = messages.count()
        message_list = list(messages[start:end])
        message_list.reverse()  # Show oldest first
        
        serializer = MessageSerializer(
            message_list, 
            many=True, 
            context={'request': request}
        )
        
        data = {
            'messages': serializer.data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': (total_count + page_size - 1) // page_size,
                'has_next': end < total_count,
                'has_previous': page > 1,
            }
        }
        
        return StandardResponse.success(
            data=data,
            message='Messages retrieved successfully.'
        )
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a message in a conversation."""
        conversation = self.get_object()
        
        # Check if user is participant
        if not conversation.participants.filter(
            id=request.user.id,
            conversationparticipant__is_active=True
        ).exists():
            return StandardResponse.error(
                message='You are not a participant in this conversation.',
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        serializer = MessageCreateSerializer(data=request.data)
        if serializer.is_valid():
            message = serializer.save(
                conversation=conversation,
                sender=request.user
            )
            
            response_serializer = MessageSerializer(
                message, 
                context={'request': request}
            )
            
            return StandardResponse.created(
                data=response_serializer.data,
                message='Message sent successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Message sending failed.'
        )
    
    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """Add a participant to the conversation."""
        conversation = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return StandardResponse.validation_error(
                errors={'user_id': 'User ID is required.'},
                message='Invalid request data.'
            )
        
        try:
            user = User.objects.get(id=user_id)
            participant = conversation.add_participant(user)
            
            return StandardResponse.success(
                message=f'{user.full_name} added to conversation successfully.'
            )
        except User.DoesNotExist:
            return StandardResponse.not_found(
                message='User not found.'
            )
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Leave a conversation."""
        conversation = self.get_object()
        
        if conversation.remove_participant(request.user):
            return StandardResponse.success(
                message='Left conversation successfully.'
            )
        else:
            return StandardResponse.error(
                message='You are not a participant in this conversation.',
                status_code=status.HTTP_400_BAD_REQUEST
            )


class MessageViewSet(ModelViewSet):
    """
    Message management viewset.
    """
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'put', 'delete']
    
    def get_queryset(self):
        """Get messages for authenticated user's conversations."""
        return Message.objects.filter(
            conversation__participants=self.request.user,
            conversation__conversationparticipant__is_active=True
        ).select_related('sender', 'conversation', 'reply_to')
    
    def update(self, request, *args, **kwargs):
        """Update message (edit content)."""
        instance = self.get_object()
        
        # Only sender can edit their own messages
        if instance.sender != request.user:
            return StandardResponse.error(
                message='You can only edit your own messages.',
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Only allow editing content
        content = request.data.get('content', '').strip()
        if not content:
            return StandardResponse.validation_error(
                errors={'content': 'Content cannot be empty.'},
                message='Invalid message content.'
            )
        
        instance.content = content
        instance.is_edited = True
        instance.edited_at = timezone.now()
        instance.save()
        
        serializer = self.get_serializer(instance)
        
        return StandardResponse.updated(
            data=serializer.data,
            message='Message updated successfully.'
        )
    
    def destroy(self, request, *args, **kwargs):
        """Delete message (soft delete)."""
        instance = self.get_object()
        
        # Only sender can delete their own messages
        if instance.sender != request.user:
            return StandardResponse.error(
                message='You can only delete your own messages.',
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Soft delete
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.content = '[Message deleted]'
        instance.save()
        
        return StandardResponse.success(
            message='Message deleted successfully.'
        )


class MarkAsReadView(APIView):
    """
    Mark messages as read.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Mark messages as read."""
        serializer = MarkAsReadSerializer(data=request.data)
        
        if serializer.is_valid():
            message_ids = serializer.validated_data.get('message_ids')
            conversation_id = serializer.validated_data.get('conversation_id')
            
            marked_count = 0
            
            if message_ids:
                # Mark specific messages as read
                messages = Message.objects.filter(
                    id__in=message_ids,
                    conversation__participants=request.user
                ).exclude(sender=request.user)
                
                for message in messages:
                    MessageRead.objects.get_or_create(
                        message=message,
                        user=request.user
                    )
                    marked_count += 1
            
            elif conversation_id:
                # Mark all unread messages in conversation as read
                try:
                    conversation = Conversation.objects.get(
                        id=conversation_id,
                        participants=request.user
                    )
                    
                    unread_messages = conversation.messages.exclude(
                        sender=request.user
                    ).exclude(
                        read_by__user=request.user
                    )
                    
                    for message in unread_messages:
                        MessageRead.objects.get_or_create(
                            message=message,
                            user=request.user
                        )
                        marked_count += 1
                        
                except Conversation.DoesNotExist:
                    return StandardResponse.not_found(
                        message='Conversation not found.'
                    )
            
            return StandardResponse.success(
                data={'marked_count': marked_count},
                message=f'Marked {marked_count} messages as read.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Invalid request data.'
        )


class UnreadCountView(APIView):
    """
    Get unread message count.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get unread message count for user."""
        # Get all conversations for user
        conversations = Conversation.objects.filter(
            participants=request.user,
            conversationparticipant__is_active=True,
            is_active=True
        )
        
        total_unread = 0
        conversation_data = []
        
        for conversation in conversations:
            unread_count = conversation.get_unread_count(request.user)
            total_unread += unread_count
            
            if unread_count > 0:
                conversation_data.append({
                    'conversation_id': conversation.id,
                    'unread_count': unread_count,
                    'last_message_at': conversation.last_message_at
                })
        
        data = {
            'total_unread': total_unread,
            'conversations': conversation_data
        }
        
        return StandardResponse.success(
            data=data,
            message='Unread count retrieved successfully.'
        )


class MessageTemplateViewSet(ModelViewSet):
    """
    Message template management.
    """
    serializer_class = MessageTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return MessageTemplate.objects.filter(
            is_active=True
        ).order_by('template_type', 'name')
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def render(self, request, pk=None):
        """Render template with provided variables."""
        template = self.get_object()
        variables = request.data.get('variables', {})
        
        try:
            rendered_content = template.render(**variables)
            
            return StandardResponse.success(
                data={'rendered_content': rendered_content},
                message='Template rendered successfully.'
            )
        except Exception as e:
            return StandardResponse.error(
                message=f'Template rendering failed: {str(e)}',
                status_code=status.HTTP_400_BAD_REQUEST
            )


class OnlineStatusView(APIView):
    """
    Get online status of users.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get online status of conversation participants."""
        conversation_id = request.query_params.get('conversation_id')
        
        if conversation_id:
            try:
                conversation = Conversation.objects.get(
                    id=conversation_id,
                    participants=request.user
                )
                
                participants = conversation.participants.all()
                status_data = []
                
                for participant in participants:
                    online_status = getattr(participant, 'online_status', None)
                    if online_status:
                        status_data.append({
                            'user_id': participant.id,
                            'user_name': participant.full_name,
                            'is_online': online_status.is_online,
                            'last_seen': online_status.last_seen,
                            'is_recently_active': online_status.is_recently_active
                        })
                
                return StandardResponse.success(
                    data=status_data,
                    message='Online status retrieved successfully.'
                )
                
            except Conversation.DoesNotExist:
                return StandardResponse.not_found(
                    message='Conversation not found.'
                )
        
        return StandardResponse.validation_error(
            errors={'conversation_id': 'Conversation ID is required.'},
            message='Invalid request parameters.'
        )
