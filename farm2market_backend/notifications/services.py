"""
Notification delivery services for different channels.
"""
import logging
import requests
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from .models import (
    NotificationChannel, NotificationTemplate, Notification,
    NotificationDeliveryLog, UserNotificationPreference, DeviceToken
)

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Main notification service for sending notifications through various channels.
    """
    
    def __init__(self):
        self.channels = {
            'EMAIL': EmailNotificationService(),
            'SMS': SMSNotificationService(),
            'PUSH': PushNotificationService(),
            'IN_APP': InAppNotificationService(),
        }
    
    def send_notification(self, user, notification_type, context=None, channels=None):
        """
        Send notification to user through specified channels.
        
        Args:
            user: User to send notification to
            notification_type: Type of notification
            context: Context data for template rendering
            channels: List of channel names (if None, use template defaults)
        """
        try:
            # Get notification template
            template = NotificationTemplate.objects.get(
                notification_type=notification_type,
                is_active=True
            )
        except NotificationTemplate.DoesNotExist:
            logger.error(f"No template found for notification type: {notification_type}")
            return False
        
        # Render template content
        context = context or {}
        subject, content = template.render(**context)
        
        # Create notification record
        notification = Notification.objects.create(
            recipient=user,
            notification_type=notification_type,
            title=subject,
            message=content,
            data=context,
            priority=context.get('priority', 'normal')
        )
        
        # Determine channels to send through
        if channels is None:
            channels = template.channels.filter(is_active=True).values_list('name', flat=True)
        
        # Send through each channel
        sent_channels = []
        for channel_name in channels:
            if self._should_send_to_channel(user, notification_type, channel_name):
                success = self._send_to_channel(notification, channel_name)
                if success:
                    sent_channels.append(channel_name)
        
        # Update notification with sent channels
        notification.channels_sent = sent_channels
        notification.save(update_fields=['channels_sent'])
        
        return notification
    
    def _should_send_to_channel(self, user, notification_type, channel_name):
        """Check if notification should be sent to specific channel."""
        try:
            preference = UserNotificationPreference.objects.get(
                user=user,
                notification_type=notification_type,
                channel__name=channel_name
            )
            
            if not preference.is_enabled:
                return False
            
            # Check quiet hours
            if preference.is_in_quiet_hours():
                return False
            
            return True
            
        except UserNotificationPreference.DoesNotExist:
            # Default to enabled if no preference set
            return True
    
    def _send_to_channel(self, notification, channel_name):
        """Send notification through specific channel."""
        if channel_name not in self.channels:
            logger.error(f"Unknown channel: {channel_name}")
            return False
        
        try:
            channel = NotificationChannel.objects.get(name=channel_name, is_active=True)
            service = self.channels[channel_name]
            
            # Create delivery log
            delivery_log = NotificationDeliveryLog.objects.create(
                notification=notification,
                channel=channel,
                status='pending'
            )
            
            # Send notification
            success = service.send(notification, delivery_log)
            
            return success
            
        except NotificationChannel.DoesNotExist:
            logger.error(f"Channel not found or inactive: {channel_name}")
            return False
        except Exception as e:
            logger.error(f"Error sending notification via {channel_name}: {str(e)}")
            return False


class EmailNotificationService:
    """
    Email notification delivery service.
    """
    
    def send(self, notification, delivery_log):
        """Send email notification."""
        try:
            user = notification.recipient
            
            # Render HTML email template
            html_content = render_to_string('emails/notification.html', {
                'notification': notification,
                'user': user,
                'action_url': notification.get_action_url()
            })
            
            # Send email
            send_mail(
                subject=notification.title,
                message=notification.message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_content,
                fail_silently=False,
            )
            
            # Update delivery log
            delivery_log.status = 'sent'
            delivery_log.sent_at = timezone.now()
            delivery_log.save()
            
            logger.info(f"Email sent to {user.email} for notification {notification.id}")
            return True
            
        except Exception as e:
            delivery_log.status = 'failed'
            delivery_log.error_message = str(e)
            delivery_log.save()
            
            logger.error(f"Failed to send email to {user.email}: {str(e)}")
            return False


class SMSNotificationService:
    """
    SMS notification delivery service.
    """
    
    def send(self, notification, delivery_log):
        """Send SMS notification."""
        try:
            user = notification.recipient
            
            if not user.phone_number:
                delivery_log.status = 'failed'
                delivery_log.error_message = 'User has no phone number'
                delivery_log.save()
                return False
            
            # Get SMS configuration
            channel = NotificationChannel.objects.get(name='SMS')
            config = channel.configuration
            
            if not config.get('account_sid') or not config.get('auth_token'):
                delivery_log.status = 'failed'
                delivery_log.error_message = 'SMS service not configured'
                delivery_log.save()
                return False
            
            # Send SMS using Twilio (example)
            success = self._send_twilio_sms(
                user.phone_number,
                notification.message,
                config,
                delivery_log
            )
            
            if success:
                logger.info(f"SMS sent to {user.phone_number} for notification {notification.id}")
            
            return success
            
        except Exception as e:
            delivery_log.status = 'failed'
            delivery_log.error_message = str(e)
            delivery_log.save()
            
            logger.error(f"Failed to send SMS to {user.phone_number}: {str(e)}")
            return False
    
    def _send_twilio_sms(self, phone_number, message, config, delivery_log):
        """Send SMS using Twilio API."""
        try:
            from twilio.rest import Client
            
            client = Client(config['account_sid'], config['auth_token'])
            
            message = client.messages.create(
                body=message,
                from_=config.get('from_number', '+1234567890'),
                to=phone_number
            )
            
            delivery_log.status = 'sent'
            delivery_log.external_id = message.sid
            delivery_log.sent_at = timezone.now()
            delivery_log.save()
            
            return True
            
        except Exception as e:
            delivery_log.status = 'failed'
            delivery_log.error_message = str(e)
            delivery_log.save()
            return False


class PushNotificationService:
    """
    Push notification delivery service using Firebase Cloud Messaging.
    """
    
    def send(self, notification, delivery_log):
        """Send push notification."""
        try:
            user = notification.recipient
            
            # Get active device tokens for user
            device_tokens = DeviceToken.objects.filter(
                user=user,
                is_active=True
            ).values_list('token', flat=True)
            
            if not device_tokens:
                delivery_log.status = 'failed'
                delivery_log.error_message = 'No active device tokens'
                delivery_log.save()
                return False
            
            # Get FCM configuration
            channel = NotificationChannel.objects.get(name='PUSH')
            config = channel.configuration
            
            server_key = config.get('firebase_server_key')
            if not server_key:
                delivery_log.status = 'failed'
                delivery_log.error_message = 'Firebase server key not configured'
                delivery_log.save()
                return False
            
            # Send push notification
            success = self._send_fcm_notification(
                list(device_tokens),
                notification,
                server_key,
                delivery_log
            )
            
            if success:
                logger.info(f"Push notification sent to {len(device_tokens)} devices for user {user.id}")
            
            return success
            
        except Exception as e:
            delivery_log.status = 'failed'
            delivery_log.error_message = str(e)
            delivery_log.save()
            
            logger.error(f"Failed to send push notification: {str(e)}")
            return False
    
    def _send_fcm_notification(self, tokens, notification, server_key, delivery_log):
        """Send notification using Firebase Cloud Messaging."""
        try:
            url = 'https://fcm.googleapis.com/fcm/send'
            
            headers = {
                'Authorization': f'key={server_key}',
                'Content-Type': 'application/json',
            }
            
            payload = {
                'registration_ids': tokens,
                'notification': {
                    'title': notification.title,
                    'body': notification.message,
                    'click_action': notification.get_action_url(),
                },
                'data': {
                    'notification_id': str(notification.id),
                    'notification_type': notification.notification_type,
                    **notification.data
                }
            }
            
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            
            delivery_log.status = 'sent'
            delivery_log.external_id = result.get('multicast_id')
            delivery_log.sent_at = timezone.now()
            delivery_log.save()
            
            return True
            
        except Exception as e:
            delivery_log.status = 'failed'
            delivery_log.error_message = str(e)
            delivery_log.save()
            return False


class InAppNotificationService:
    """
    In-app notification service (just creates the notification record).
    """
    
    def send(self, notification, delivery_log):
        """Mark in-app notification as sent."""
        try:
            # For in-app notifications, just mark as sent
            # The notification record already exists and will be shown in the UI
            
            delivery_log.status = 'sent'
            delivery_log.sent_at = timezone.now()
            delivery_log.save()
            
            # Send real-time notification via WebSocket if available
            self._send_realtime_notification(notification)
            
            logger.info(f"In-app notification created for user {notification.recipient.id}")
            return True
            
        except Exception as e:
            delivery_log.status = 'failed'
            delivery_log.error_message = str(e)
            delivery_log.save()
            
            logger.error(f"Failed to create in-app notification: {str(e)}")
            return False
    
    def _send_realtime_notification(self, notification):
        """Send real-time notification via WebSocket."""
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f'user_{notification.recipient.id}',
                    {
                        'type': 'general_notification',
                        'title': notification.title,
                        'message': notification.message,
                        'category': notification.notification_type,
                        'timestamp': timezone.now().isoformat()
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to send real-time notification: {str(e)}")


# Convenience functions for common notification types

def send_order_notification(order, notification_type, additional_context=None):
    """Send order-related notification."""
    service = NotificationService()
    
    context = {
        'order_number': order.order_number,
        'buyer_name': order.buyer.full_name,
        'farmer_name': order.farmer.full_name,
        'total_amount': order.total_amount,
        'order_status': order.get_status_display(),
        'action_url': f'/orders/{order.id}/',
        'object_id': order.id,
    }
    
    if additional_context:
        context.update(additional_context)
    
    # Send to buyer
    service.send_notification(order.buyer, notification_type, context)
    
    # Send to farmer for certain types
    farmer_types = ['order_received', 'payment_received']
    if notification_type in farmer_types:
        service.send_notification(order.farmer, notification_type, context)


def send_product_notification(product, notification_type, users, additional_context=None):
    """Send product-related notification to multiple users."""
    service = NotificationService()
    
    context = {
        'product_name': product.product_name,
        'farmer_name': product.farmer.full_name,
        'price': product.price,
        'action_url': f'/products/{product.id}/',
        'object_id': product.id,
    }
    
    if additional_context:
        context.update(additional_context)
    
    for user in users:
        service.send_notification(user, notification_type, context)


def send_system_notification(user, notification_type, additional_context=None):
    """Send system notification to user."""
    service = NotificationService()
    
    context = {
        'user_name': user.full_name,
        'platform_name': 'Farm2Market',
    }
    
    if additional_context:
        context.update(additional_context)
    
    service.send_notification(user, notification_type, context)
