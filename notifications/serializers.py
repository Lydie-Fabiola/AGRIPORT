from rest_framework import serializers
from .models import Notification, Alert

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'title', 'message', 'is_read', 'created_at',
            'notification_type', 'related_entity_type', 'related_entity_id'
        ]
        read_only_fields = ['id', 'created_at']

class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = [
            'id', 'farmer', 'alert_type', 'title', 'message', 'severity',
            'is_read', 'created_at', 'valid_until'
        ]
        read_only_fields = ['id', 'created_at']
