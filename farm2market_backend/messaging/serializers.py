"""
Serializers for messaging system.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import (
    Conversation, ConversationParticipant, Message, MessageRead,
    MessageTemplate, UserOnlineStatus, TypingIndicator
)

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """
    Basic user serializer for messaging.
    """
    full_name = serializers.ReadOnlyField()
    is_online = serializers.SerializerMethodField()
    last_seen = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'full_name', 'user_type',
            'is_online', 'last_seen'
        ]
    
    def get_is_online(self, obj):
        """Get user online status."""
        if hasattr(obj, 'online_status'):
            return obj.online_status.is_online
        return False
    
    def get_last_seen(self, obj):
        """Get user last seen timestamp."""
        if hasattr(obj, 'online_status'):
            return obj.online_status.last_seen
        return None


class ConversationParticipantSerializer(serializers.ModelSerializer):
    """
    Serializer for conversation participants.
    """
    user = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = ConversationParticipant
        fields = [
            'user', 'joined_at', 'left_at', 'is_active'
        ]


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for messages.
    """
    sender = UserBasicSerializer(read_only=True)
    message_type_display = serializers.CharField(source='get_message_type_display', read_only=True)
    is_read_by_all = serializers.ReadOnlyField()
    attachment_url = serializers.ReadOnlyField(source='get_attachment_url')
    attachment_extension = serializers.ReadOnlyField(source='get_attachment_extension')
    
    # Reply information
    reply_to_message = serializers.SerializerMethodField()
    
    # Read status for current user
    is_read_by_me = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'content', 'message_type',
            'message_type_display', 'attachment', 'attachment_url',
            'attachment_name', 'attachment_size', 'attachment_extension',
            'is_edited', 'edited_at', 'reply_to', 'reply_to_message',
            'is_read_by_all', 'is_read_by_me', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'sender', 'is_edited', 'edited_at', 'attachment_name',
            'attachment_size', 'created_at', 'updated_at'
        ]
    
    def get_reply_to_message(self, obj):
        """Get basic info about the message being replied to."""
        if obj.reply_to:
            return {
                'id': obj.reply_to.id,
                'sender_name': obj.reply_to.sender.full_name,
                'content': obj.reply_to.content[:100] + '...' if len(obj.reply_to.content) > 100 else obj.reply_to.content,
                'message_type': obj.reply_to.message_type,
                'created_at': obj.reply_to.created_at
            }
        return None
    
    def get_is_read_by_me(self, obj):
        """Check if current user has read this message."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return MessageRead.objects.filter(
                message=obj,
                user=request.user
            ).exists()
        return False


class MessageCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating messages.
    """
    class Meta:
        model = Message
        fields = [
            'content', 'message_type', 'attachment', 'reply_to'
        ]
    
    def validate_content(self, value):
        """Validate message content."""
        if not value.strip() and not self.initial_data.get('attachment'):
            raise serializers.ValidationError("Message content cannot be empty without an attachment.")
        return value.strip()
    
    def validate_attachment(self, value):
        """Validate attachment."""
        if value:
            # Check file size (max 10MB)
            if value.size > 10 * 1024 * 1024:
                raise serializers.ValidationError("File size cannot exceed 10MB.")
            
            # Check file type based on message_type
            message_type = self.initial_data.get('message_type', 'text')
            if message_type == 'image':
                allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
                if not any(value.name.lower().endswith(ext) for ext in allowed_extensions):
                    raise serializers.ValidationError("Only image files are allowed for image messages.")
            
        return value


class ConversationSerializer(serializers.ModelSerializer):
    """
    Serializer for conversations.
    """
    participants = ConversationParticipantSerializer(
        source='conversationparticipant_set',
        many=True,
        read_only=True
    )
    
    participant_count = serializers.ReadOnlyField()
    
    # Related object details
    related_product_details = serializers.SerializerMethodField()
    related_order_details = serializers.SerializerMethodField()
    
    # Last message info
    last_message = serializers.SerializerMethodField()
    
    # Unread count for current user
    unread_count = serializers.SerializerMethodField()
    
    # Other participant (for 2-person conversations)
    other_participant = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'subject', 'related_product', 'related_product_details',
            'related_order', 'related_order_details', 'is_active',
            'participants', 'participant_count', 'other_participant',
            'last_message', 'last_message_at', 'unread_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'last_message_at']
    
    def get_related_product_details(self, obj):
        """Get related product details."""
        if obj.related_product:
            return {
                'id': obj.related_product.id,
                'name': obj.related_product.product_name,
                'price': obj.related_product.price,
                'farmer_name': obj.related_product.farmer.full_name,
            }
        return None
    
    def get_related_order_details(self, obj):
        """Get related order details."""
        if obj.related_order:
            return {
                'id': obj.related_order.id,
                'order_number': obj.related_order.order_number,
                'status': obj.related_order.status,
                'total_amount': obj.related_order.total_amount,
            }
        return None
    
    def get_last_message(self, obj):
        """Get last message in conversation."""
        last_message = obj.messages.order_by('-created_at').first()
        if last_message:
            return {
                'id': last_message.id,
                'sender_name': last_message.sender.full_name,
                'content': last_message.content[:100] + '...' if len(last_message.content) > 100 else last_message.content,
                'message_type': last_message.message_type,
                'created_at': last_message.created_at,
            }
        return None
    
    def get_unread_count(self, obj):
        """Get unread message count for current user."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_unread_count(request.user)
        return 0
    
    def get_other_participant(self, obj):
        """Get other participant in 2-person conversation."""
        request = self.context.get('request')
        if request and request.user.is_authenticated and obj.participant_count == 2:
            other_user = obj.get_other_participant(request.user)
            if other_user:
                return UserBasicSerializer(other_user).data
        return None


class ConversationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating conversations.
    """
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=True
    )
    
    initial_message = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True
    )
    
    class Meta:
        model = Conversation
        fields = [
            'subject', 'related_product', 'related_order',
            'participant_ids', 'initial_message'
        ]
    
    def validate_participant_ids(self, value):
        """Validate participant IDs."""
        if len(value) < 1:
            raise serializers.ValidationError("At least one participant is required.")
        
        # Check if all users exist
        existing_users = User.objects.filter(id__in=value).count()
        if existing_users != len(value):
            raise serializers.ValidationError("Some participant IDs are invalid.")
        
        return value
    
    def create(self, validated_data):
        """Create conversation with participants."""
        participant_ids = validated_data.pop('participant_ids')
        initial_message = validated_data.pop('initial_message', '')
        
        # Create conversation
        conversation = Conversation.objects.create(**validated_data)
        
        # Add participants
        for user_id in participant_ids:
            user = User.objects.get(id=user_id)
            conversation.add_participant(user)
        
        # Add creator as participant if not already included
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            conversation.add_participant(request.user)
            
            # Create initial message if provided
            if initial_message:
                Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    content=initial_message,
                    message_type='text'
                )
        
        return conversation


class MessageTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for message templates.
    """
    template_type_display = serializers.CharField(source='get_template_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    
    class Meta:
        model = MessageTemplate
        fields = [
            'id', 'name', 'template_type', 'template_type_display',
            'content', 'variables', 'is_active', 'created_by',
            'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class TypingIndicatorSerializer(serializers.ModelSerializer):
    """
    Serializer for typing indicators.
    """
    user = UserBasicSerializer(read_only=True)
    is_expired = serializers.ReadOnlyField()
    
    class Meta:
        model = TypingIndicator
        fields = [
            'conversation', 'user', 'is_typing', 'started_at',
            'expires_at', 'is_expired'
        ]
        read_only_fields = ['user', 'started_at', 'expires_at']


class MarkAsReadSerializer(serializers.Serializer):
    """
    Serializer for marking messages as read.
    """
    message_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False
    )
    
    conversation_id = serializers.IntegerField(required=False)
    
    def validate(self, attrs):
        """Validate that either message_ids or conversation_id is provided."""
        if not attrs.get('message_ids') and not attrs.get('conversation_id'):
            raise serializers.ValidationError(
                "Either message_ids or conversation_id must be provided."
            )
        return attrs


class UnreadCountSerializer(serializers.Serializer):
    """
    Serializer for unread message counts.
    """
    total_unread = serializers.IntegerField()
    conversations = serializers.ListField(
        child=serializers.DictField()
    )


class OnlineStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for user online status.
    """
    user = UserBasicSerializer(read_only=True)
    is_recently_active = serializers.ReadOnlyField()
    
    class Meta:
        model = UserOnlineStatus
        fields = [
            'user', 'is_online', 'last_seen', 'is_recently_active',
            'device_info', 'updated_at'
        ]
        read_only_fields = ['user', 'last_seen', 'updated_at']
