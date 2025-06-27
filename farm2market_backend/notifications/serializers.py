"""
Serializers for notification system.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    NotificationChannel, NotificationTemplate, Notification,
    UserNotificationPreference, DeviceToken, NotificationDeliveryLog
)

User = get_user_model()


class NotificationChannelSerializer(serializers.ModelSerializer):
    """
    Serializer for notification channels.
    """
    class Meta:
        model = NotificationChannel
        fields = [
            'id', 'name', 'display_name', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for notification templates.
    """
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', 
        read_only=True
    )
    channels = NotificationChannelSerializer(many=True, read_only=True)
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'notification_type', 'notification_type_display',
            'subject_template', 'content_template', 'variables', 'channels',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for notifications.
    """
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', 
        read_only=True
    )
    priority_display = serializers.CharField(
        source='get_priority_display', 
        read_only=True
    )
    is_expired = serializers.ReadOnlyField()
    action_url = serializers.ReadOnlyField(source='get_action_url')
    related_object_id = serializers.ReadOnlyField(source='get_related_object_id')
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'notification_type_display', 'title',
            'message', 'data', 'channels_sent', 'is_read', 'read_at',
            'priority', 'priority_display', 'expires_at', 'is_expired',
            'action_url', 'related_object_id', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'notification_type', 'title', 'message', 'data', 'channels_sent',
            'priority', 'expires_at', 'created_at', 'updated_at'
        ]


class NotificationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating notifications.
    """
    class Meta:
        model = Notification
        fields = [
            'recipient', 'notification_type', 'title', 'message', 'data',
            'priority', 'expires_at'
        ]
    
    def validate_recipient(self, value):
        """Validate recipient exists and is active."""
        if not value.is_active:
            raise serializers.ValidationError("Recipient account is not active.")
        return value


class UserNotificationPreferenceSerializer(serializers.ModelSerializer):
    """
    Serializer for user notification preferences.
    """
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    channel_display_name = serializers.CharField(source='channel.display_name', read_only=True)
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', 
        read_only=True
    )
    
    class Meta:
        model = UserNotificationPreference
        fields = [
            'id', 'notification_type', 'notification_type_display', 'channel',
            'channel_name', 'channel_display_name', 'is_enabled',
            'quiet_hours_start', 'quiet_hours_end', 'timezone',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class UserNotificationPreferenceUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating notification preferences.
    """
    class Meta:
        model = UserNotificationPreference
        fields = [
            'is_enabled', 'quiet_hours_start', 'quiet_hours_end', 'timezone'
        ]
    
    def validate(self, attrs):
        """Validate quiet hours."""
        start = attrs.get('quiet_hours_start')
        end = attrs.get('quiet_hours_end')
        
        if (start and not end) or (end and not start):
            raise serializers.ValidationError(
                "Both quiet_hours_start and quiet_hours_end must be provided together."
            )
        
        return attrs


class DeviceTokenSerializer(serializers.ModelSerializer):
    """
    Serializer for device tokens.
    """
    device_type_display = serializers.CharField(
        source='get_device_type_display', 
        read_only=True
    )
    
    class Meta:
        model = DeviceToken
        fields = [
            'id', 'token', 'device_type', 'device_type_display', 'device_id',
            'app_version', 'is_active', 'last_used', 'created_at', 'updated_at'
        ]
        read_only_fields = ['last_used', 'created_at', 'updated_at']


class DeviceTokenCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating device tokens.
    """
    class Meta:
        model = DeviceToken
        fields = ['token', 'device_type', 'device_id', 'app_version']
    
    def create(self, validated_data):
        """Create or update device token."""
        user = self.context['request'].user
        token = validated_data['token']
        
        # Deactivate existing tokens for this user and device
        DeviceToken.objects.filter(
            user=user,
            device_type=validated_data['device_type'],
            device_id=validated_data.get('device_id')
        ).update(is_active=False)
        
        # Create new token
        device_token = DeviceToken.objects.create(
            user=user,
            **validated_data
        )
        
        return device_token


class NotificationDeliveryLogSerializer(serializers.ModelSerializer):
    """
    Serializer for notification delivery logs.
    """
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = NotificationDeliveryLog
        fields = [
            'id', 'channel', 'channel_name', 'status', 'status_display',
            'external_id', 'error_message', 'sent_at', 'delivered_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class NotificationStatsSerializer(serializers.Serializer):
    """
    Serializer for notification statistics.
    """
    total_notifications = serializers.IntegerField()
    unread_count = serializers.IntegerField()
    read_count = serializers.IntegerField()
    by_type = serializers.DictField()
    by_priority = serializers.DictField()
    recent_notifications = NotificationSerializer(many=True)


class BulkNotificationSerializer(serializers.Serializer):
    """
    Serializer for bulk notification operations.
    """
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        allow_empty=False
    )
    
    action = serializers.ChoiceField(
        choices=['mark_read', 'mark_unread', 'delete'],
        required=True
    )
    
    def validate_notification_ids(self, value):
        """Validate notification IDs belong to the user."""
        user = self.context['request'].user
        
        existing_count = Notification.objects.filter(
            id__in=value,
            recipient=user
        ).count()
        
        if existing_count != len(value):
            raise serializers.ValidationError(
                "Some notification IDs are invalid or don't belong to you."
            )
        
        return value


class TestNotificationSerializer(serializers.Serializer):
    """
    Serializer for sending test notifications.
    """
    notification_type = serializers.ChoiceField(
        choices=NotificationTemplate.NOTIFICATION_TYPE_CHOICES,
        required=True
    )
    
    channels = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=['IN_APP']
    )
    
    test_data = serializers.DictField(
        required=False,
        default=dict,
        help_text="Test data for template variables"
    )
    
    def validate_channels(self, value):
        """Validate channel names."""
        valid_channels = NotificationChannel.objects.filter(
            name__in=value,
            is_active=True
        ).values_list('name', flat=True)
        
        invalid_channels = set(value) - set(valid_channels)
        if invalid_channels:
            raise serializers.ValidationError(
                f"Invalid channels: {', '.join(invalid_channels)}"
            )
        
        return value


class NotificationPreferencesSerializer(serializers.Serializer):
    """
    Serializer for notification preferences overview.
    """
    email_enabled = serializers.BooleanField()
    sms_enabled = serializers.BooleanField()
    push_enabled = serializers.BooleanField()
    in_app_enabled = serializers.BooleanField()
    
    order_notifications = serializers.DictField()
    product_notifications = serializers.DictField()
    system_notifications = serializers.DictField()
    
    quiet_hours = serializers.DictField()
    timezone = serializers.CharField()


class NotificationSettingsUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating notification settings in bulk.
    """
    preferences = serializers.ListField(
        child=serializers.DictField(),
        required=True
    )
    
    def validate_preferences(self, value):
        """Validate preference updates."""
        user = self.context['request'].user
        
        for pref in value:
            if 'notification_type' not in pref or 'channel' not in pref:
                raise serializers.ValidationError(
                    "Each preference must have 'notification_type' and 'channel'."
                )
            
            # Validate notification type
            valid_types = [choice[0] for choice in NotificationTemplate.NOTIFICATION_TYPE_CHOICES]
            if pref['notification_type'] not in valid_types:
                raise serializers.ValidationError(
                    f"Invalid notification type: {pref['notification_type']}"
                )
            
            # Validate channel
            try:
                NotificationChannel.objects.get(
                    name=pref['channel'],
                    is_active=True
                )
            except NotificationChannel.DoesNotExist:
                raise serializers.ValidationError(
                    f"Invalid channel: {pref['channel']}"
                )
        
        return value
