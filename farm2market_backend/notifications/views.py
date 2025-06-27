"""
Views for notification system.
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django.utils import timezone
from apps.core.responses import StandardResponse
from apps.core.exceptions import ValidationError, NotFoundError
from .models import (
    NotificationChannel, NotificationTemplate, Notification,
    UserNotificationPreference, DeviceToken, NotificationDeliveryLog
)
from .serializers import (
    NotificationChannelSerializer, NotificationTemplateSerializer,
    NotificationSerializer, UserNotificationPreferenceSerializer,
    UserNotificationPreferenceUpdateSerializer, DeviceTokenSerializer,
    DeviceTokenCreateSerializer, NotificationStatsSerializer,
    BulkNotificationSerializer, TestNotificationSerializer,
    NotificationPreferencesSerializer, NotificationSettingsUpdateSerializer
)
from .services import NotificationService, send_system_notification

User = get_user_model()


class NotificationViewSet(ReadOnlyModelViewSet):
    """
    User notifications viewset.
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get notifications for authenticated user."""
        return Notification.objects.filter(
            recipient=self.request.user,
            is_deleted=False
        ).select_related('recipient').order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        """List user notifications with filtering."""
        queryset = self.get_queryset()
        
        # Filter by read status
        is_read = request.query_params.get('is_read')
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')
        
        # Filter by notification type
        notification_type = request.query_params.get('type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        # Filter by priority
        priority = request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # Exclude expired notifications
        exclude_expired = request.query_params.get('exclude_expired', 'true')
        if exclude_expired.lower() == 'true':
            queryset = queryset.filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
            )
        
        # Pagination
        page_size = min(int(request.query_params.get('page_size', 20)), 100)
        page = int(request.query_params.get('page', 1))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        total_count = queryset.count()
        notifications = queryset[start:end]
        
        serializer = self.get_serializer(notifications, many=True)
        
        data = {
            'notifications': serializer.data,
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
            message='Notifications retrieved successfully.'
        )
    
    @action(detail=True, methods=['put'])
    def mark_read(self, request, pk=None):
        """Mark notification as read."""
        notification = self.get_object()
        notification.mark_as_read()
        
        serializer = self.get_serializer(notification)
        
        return StandardResponse.updated(
            data=serializer.data,
            message='Notification marked as read.'
        )
    
    @action(detail=True, methods=['put'])
    def mark_unread(self, request, pk=None):
        """Mark notification as unread."""
        notification = self.get_object()
        
        notification.is_read = False
        notification.read_at = None
        notification.save(update_fields=['is_read', 'read_at'])
        
        serializer = self.get_serializer(notification)
        
        return StandardResponse.updated(
            data=serializer.data,
            message='Notification marked as unread.'
        )
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read."""
        updated_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
            is_deleted=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        return StandardResponse.success(
            data={'updated_count': updated_count},
            message=f'Marked {updated_count} notifications as read.'
        )
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get unread notification count."""
        unread_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
            is_deleted=False
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        ).count()
        
        return StandardResponse.success(
            data={'unread_count': unread_count},
            message='Unread count retrieved successfully.'
        )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get notification statistics."""
        queryset = self.get_queryset()
        
        total_notifications = queryset.count()
        unread_count = queryset.filter(is_read=False).count()
        read_count = total_notifications - unread_count
        
        # Group by type
        by_type = dict(queryset.values('notification_type').annotate(
            count=Count('id')
        ).values_list('notification_type', 'count'))
        
        # Group by priority
        by_priority = dict(queryset.values('priority').annotate(
            count=Count('id')
        ).values_list('priority', 'count'))
        
        # Recent notifications
        recent_notifications = queryset[:5]
        recent_serializer = NotificationSerializer(recent_notifications, many=True)
        
        stats_data = {
            'total_notifications': total_notifications,
            'unread_count': unread_count,
            'read_count': read_count,
            'by_type': by_type,
            'by_priority': by_priority,
            'recent_notifications': recent_serializer.data
        }
        
        return StandardResponse.success(
            data=stats_data,
            message='Notification statistics retrieved successfully.'
        )
    
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """Perform bulk actions on notifications."""
        serializer = BulkNotificationSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            notification_ids = serializer.validated_data['notification_ids']
            action = serializer.validated_data['action']
            
            notifications = Notification.objects.filter(
                id__in=notification_ids,
                recipient=request.user
            )
            
            if action == 'mark_read':
                updated_count = notifications.update(
                    is_read=True,
                    read_at=timezone.now()
                )
                message = f'Marked {updated_count} notifications as read.'
                
            elif action == 'mark_unread':
                updated_count = notifications.update(
                    is_read=False,
                    read_at=None
                )
                message = f'Marked {updated_count} notifications as unread.'
                
            elif action == 'delete':
                updated_count = notifications.update(
                    is_deleted=True,
                    deleted_at=timezone.now()
                )
                message = f'Deleted {updated_count} notifications.'
            
            return StandardResponse.success(
                data={'updated_count': updated_count},
                message=message
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Invalid bulk action data.'
        )


class NotificationPreferencesView(APIView):
    """
    User notification preferences management.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get user notification preferences."""
        user = request.user
        
        # Get all preferences
        preferences = UserNotificationPreference.objects.filter(
            user=user
        ).select_related('channel')
        
        # Organize preferences by channel and type
        email_prefs = preferences.filter(channel__name='EMAIL')
        sms_prefs = preferences.filter(channel__name='SMS')
        push_prefs = preferences.filter(channel__name='PUSH')
        in_app_prefs = preferences.filter(channel__name='IN_APP')
        
        # Get general settings
        general_pref = preferences.first()
        
        data = {
            'email_enabled': email_prefs.filter(is_enabled=True).exists(),
            'sms_enabled': sms_prefs.filter(is_enabled=True).exists(),
            'push_enabled': push_prefs.filter(is_enabled=True).exists(),
            'in_app_enabled': in_app_prefs.filter(is_enabled=True).exists(),
            
            'order_notifications': self._get_type_preferences(preferences, 'order_'),
            'product_notifications': self._get_type_preferences(preferences, 'product_'),
            'system_notifications': self._get_type_preferences(preferences, 'system_'),
            
            'quiet_hours': {
                'start': general_pref.quiet_hours_start if general_pref else None,
                'end': general_pref.quiet_hours_end if general_pref else None,
            },
            'timezone': general_pref.timezone if general_pref else 'UTC',
        }
        
        return StandardResponse.success(
            data=data,
            message='Notification preferences retrieved successfully.'
        )
    
    def put(self, request):
        """Update notification preferences."""
        serializer = NotificationSettingsUpdateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            preferences_data = serializer.validated_data['preferences']
            
            updated_count = 0
            
            for pref_data in preferences_data:
                channel = NotificationChannel.objects.get(name=pref_data['channel'])
                
                preference, created = UserNotificationPreference.objects.get_or_create(
                    user=request.user,
                    notification_type=pref_data['notification_type'],
                    channel=channel,
                    defaults=pref_data
                )
                
                if not created:
                    for key, value in pref_data.items():
                        if key not in ['notification_type', 'channel']:
                            setattr(preference, key, value)
                    preference.save()
                
                updated_count += 1
            
            return StandardResponse.success(
                data={'updated_count': updated_count},
                message='Notification preferences updated successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Invalid preference data.'
        )
    
    def _get_type_preferences(self, preferences, type_prefix):
        """Get preferences for a specific notification type prefix."""
        type_prefs = preferences.filter(
            notification_type__startswith=type_prefix
        )
        
        result = {}
        for pref in type_prefs:
            if pref.notification_type not in result:
                result[pref.notification_type] = {}
            result[pref.notification_type][pref.channel.name.lower()] = pref.is_enabled
        
        return result


class DeviceTokenViewSet(ModelViewSet):
    """
    Device token management for push notifications.
    """
    serializer_class = DeviceTokenSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return DeviceToken.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return DeviceTokenCreateSerializer
        return DeviceTokenSerializer
    
    def create(self, request, *args, **kwargs):
        """Register device token."""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            device_token = serializer.save()
            response_serializer = DeviceTokenSerializer(device_token)
            
            return StandardResponse.created(
                data=response_serializer.data,
                message='Device token registered successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Device token registration failed.'
        )


class TestNotificationView(APIView):
    """
    Send test notifications for testing purposes.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Send test notification."""
        serializer = TestNotificationSerializer(data=request.data)
        
        if serializer.is_valid():
            notification_type = serializer.validated_data['notification_type']
            channels = serializer.validated_data['channels']
            test_data = serializer.validated_data['test_data']
            
            # Add default test data
            context = {
                'user_name': request.user.full_name,
                'platform_name': 'Farm2Market',
                'test_mode': True,
                **test_data
            }
            
            # Send test notification
            service = NotificationService()
            notification = service.send_notification(
                request.user,
                notification_type,
                context,
                channels
            )
            
            if notification:
                serializer = NotificationSerializer(notification)
                return StandardResponse.success(
                    data=serializer.data,
                    message='Test notification sent successfully.'
                )
            else:
                return StandardResponse.error(
                    message='Failed to send test notification.',
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Invalid test notification data.'
        )
