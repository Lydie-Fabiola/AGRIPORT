"""
Notification system models for Farm2Market.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.core.models import BaseModel
import json

User = get_user_model()


class NotificationChannel(models.Model):
    """
    Notification delivery channels (Email, SMS, Push, In-App).
    """
    name = models.CharField(
        _('name'),
        max_length=50,
        unique=True,
        help_text=_('Channel identifier (EMAIL, SMS, PUSH, IN_APP).')
    )
    
    display_name = models.CharField(
        _('display name'),
        max_length=100,
        help_text=_('Human-readable channel name.')
    )
    
    is_active = models.BooleanField(
        _('is active'),
        default=True,
        help_text=_('Whether this channel is active.')
    )
    
    configuration = models.JSONField(
        _('configuration'),
        default=dict,
        blank=True,
        help_text=_('Channel-specific configuration.')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Notification Channel')
        verbose_name_plural = _('Notification Channels')
        ordering = ['name']
        
    def __str__(self):
        return self.display_name


class NotificationTemplate(BaseModel):
    """
    Templates for different types of notifications.
    """
    NOTIFICATION_TYPE_CHOICES = [
        # Order notifications
        ('order_received', _('New Order Received')),
        ('order_confirmed', _('Order Confirmed')),
        ('order_preparing', _('Order Being Prepared')),
        ('order_ready', _('Order Ready')),
        ('order_in_transit', _('Order In Transit')),
        ('order_delivered', _('Order Delivered')),
        ('order_cancelled', _('Order Cancelled')),
        ('payment_received', _('Payment Received')),
        ('payment_failed', _('Payment Failed')),
        
        # Product notifications
        ('new_product_favorite_farmer', _('New Product from Favorite Farmer')),
        ('price_drop_wishlist', _('Price Drop on Wishlist Item')),
        ('stock_available_wishlist', _('Stock Available for Wishlist Item')),
        ('seasonal_products', _('Seasonal Products Available')),
        ('product_expiring_soon', _('Product Expiring Soon')),
        
        # Reservation notifications
        ('reservation_received', _('Reservation Request Received')),
        ('reservation_accepted', _('Reservation Accepted')),
        ('reservation_rejected', _('Reservation Rejected')),
        ('reservation_counter_offer', _('Reservation Counter Offer')),
        ('reservation_expired', _('Reservation Expired')),
        
        # System notifications
        ('account_verification', _('Account Verification')),
        ('password_reset', _('Password Reset')),
        ('security_alert', _('Security Alert')),
        ('maintenance_announcement', _('Maintenance Announcement')),
        ('welcome_message', _('Welcome Message')),
        ('profile_incomplete', _('Profile Incomplete')),
        
        # Marketing notifications
        ('promotional_offer', _('Promotional Offer')),
        ('newsletter', _('Newsletter')),
        ('survey_request', _('Survey Request')),
        
        # General notifications
        ('general_announcement', _('General Announcement')),
        ('system_update', _('System Update')),
    ]
    
    name = models.CharField(
        _('name'),
        max_length=100,
        help_text=_('Template name.')
    )
    
    notification_type = models.CharField(
        _('notification type'),
        max_length=50,
        choices=NOTIFICATION_TYPE_CHOICES,
        help_text=_('Type of notification.')
    )
    
    channels = models.ManyToManyField(
        NotificationChannel,
        through='NotificationTemplateChannel',
        related_name='templates',
        help_text=_('Channels this template can be sent through.')
    )
    
    subject_template = models.CharField(
        _('subject template'),
        max_length=200,
        help_text=_('Subject line template with variables.')
    )
    
    content_template = models.TextField(
        _('content template'),
        help_text=_('Message content template with variables.')
    )
    
    variables = models.JSONField(
        _('variables'),
        default=dict,
        blank=True,
        help_text=_('Available variables for this template.')
    )
    
    is_active = models.BooleanField(
        _('is active'),
        default=True
    )
    
    class Meta:
        verbose_name = _('Notification Template')
        verbose_name_plural = _('Notification Templates')
        ordering = ['notification_type', 'name']
        indexes = [
            models.Index(fields=['notification_type', 'is_active']),
        ]
        
    def __str__(self):
        return f"{self.name} ({self.get_notification_type_display()})"
    
    def render(self, **context):
        """Render template with provided context."""
        subject = self.subject_template
        content = self.content_template
        
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            subject = subject.replace(placeholder, str(value))
            content = content.replace(placeholder, str(value))
        
        return subject, content


class NotificationTemplateChannel(models.Model):
    """
    Through model for template-channel relationships.
    """
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.CASCADE
    )
    
    channel = models.ForeignKey(
        NotificationChannel,
        on_delete=models.CASCADE
    )
    
    is_active = models.BooleanField(
        _('is active'),
        default=True
    )
    
    class Meta:
        verbose_name = _('Template Channel')
        verbose_name_plural = _('Template Channels')
        unique_together = ['template', 'channel']


class Notification(BaseModel):
    """
    Individual notifications sent to users.
    """
    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('normal', _('Normal')),
        ('high', _('High')),
        ('urgent', _('Urgent')),
    ]
    
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text=_('User receiving the notification.')
    )
    
    notification_type = models.CharField(
        _('notification type'),
        max_length=50,
        choices=NotificationTemplate.NOTIFICATION_TYPE_CHOICES,
        help_text=_('Type of notification.')
    )
    
    title = models.CharField(
        _('title'),
        max_length=200,
        help_text=_('Notification title/subject.')
    )
    
    message = models.TextField(
        _('message'),
        help_text=_('Notification message content.')
    )
    
    data = models.JSONField(
        _('data'),
        default=dict,
        blank=True,
        help_text=_('Additional context data.')
    )
    
    channels_sent = models.JSONField(
        _('channels sent'),
        default=list,
        blank=True,
        help_text=_('List of channels this notification was sent through.')
    )
    
    is_read = models.BooleanField(
        _('is read'),
        default=False
    )
    
    read_at = models.DateTimeField(
        _('read at'),
        null=True,
        blank=True
    )
    
    priority = models.CharField(
        _('priority'),
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal'
    )
    
    expires_at = models.DateTimeField(
        _('expires at'),
        null=True,
        blank=True,
        help_text=_('When this notification expires.')
    )
    
    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['priority', 'created_at']),
            models.Index(fields=['expires_at']),
        ]
        
    def __str__(self):
        return f"{self.title} - {self.recipient.full_name}"
    
    def mark_as_read(self):
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    @property
    def is_expired(self):
        """Check if notification is expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def get_action_url(self):
        """Get action URL from data if available."""
        return self.data.get('action_url')
    
    def get_related_object_id(self):
        """Get related object ID from data."""
        return self.data.get('object_id')


class UserNotificationPreference(models.Model):
    """
    User preferences for notification types and channels.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    notification_type = models.CharField(
        _('notification type'),
        max_length=50,
        choices=NotificationTemplate.NOTIFICATION_TYPE_CHOICES
    )
    
    channel = models.ForeignKey(
        NotificationChannel,
        on_delete=models.CASCADE
    )
    
    is_enabled = models.BooleanField(
        _('is enabled'),
        default=True
    )
    
    quiet_hours_start = models.TimeField(
        _('quiet hours start'),
        null=True,
        blank=True,
        help_text=_('Start of quiet hours (no notifications).')
    )
    
    quiet_hours_end = models.TimeField(
        _('quiet hours end'),
        null=True,
        blank=True,
        help_text=_('End of quiet hours.')
    )
    
    timezone = models.CharField(
        _('timezone'),
        max_length=50,
        default='UTC',
        help_text=_('User timezone for quiet hours.')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('User Notification Preference')
        verbose_name_plural = _('User Notification Preferences')
        unique_together = ['user', 'notification_type', 'channel']
        indexes = [
            models.Index(fields=['user', 'notification_type']),
        ]
        
    def __str__(self):
        return f"{self.user.full_name} - {self.notification_type} via {self.channel.name}"
    
    def is_in_quiet_hours(self):
        """Check if current time is in user's quiet hours."""
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        # TODO: Implement timezone-aware quiet hours checking
        from datetime import datetime
        now = datetime.now().time()
        
        if self.quiet_hours_start <= self.quiet_hours_end:
            return self.quiet_hours_start <= now <= self.quiet_hours_end
        else:
            # Quiet hours span midnight
            return now >= self.quiet_hours_start or now <= self.quiet_hours_end


class DeviceToken(models.Model):
    """
    Device tokens for push notifications.
    """
    DEVICE_TYPE_CHOICES = [
        ('ios', _('iOS')),
        ('android', _('Android')),
        ('web', _('Web')),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='device_tokens'
    )
    
    token = models.CharField(
        _('token'),
        max_length=500,
        help_text=_('FCM device token.')
    )
    
    device_type = models.CharField(
        _('device type'),
        max_length=10,
        choices=DEVICE_TYPE_CHOICES
    )
    
    device_id = models.CharField(
        _('device ID'),
        max_length=255,
        blank=True,
        help_text=_('Unique device identifier.')
    )
    
    app_version = models.CharField(
        _('app version'),
        max_length=50,
        blank=True
    )
    
    is_active = models.BooleanField(
        _('is active'),
        default=True
    )
    
    last_used = models.DateTimeField(
        _('last used'),
        auto_now=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Device Token')
        verbose_name_plural = _('Device Tokens')
        unique_together = ['user', 'token']
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]
        
    def __str__(self):
        return f"{self.user.full_name} - {self.device_type} ({self.token[:20]}...)"


class NotificationDeliveryLog(models.Model):
    """
    Log of notification delivery attempts and status.
    """
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('sent', _('Sent')),
        ('delivered', _('Delivered')),
        ('failed', _('Failed')),
        ('bounced', _('Bounced')),
    ]

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='delivery_logs'
    )

    channel = models.ForeignKey(
        NotificationChannel,
        on_delete=models.CASCADE
    )

    status = models.CharField(
        _('status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    external_id = models.CharField(
        _('external ID'),
        max_length=255,
        blank=True,
        help_text=_('External service message ID.')
    )

    error_message = models.TextField(
        _('error message'),
        blank=True
    )

    sent_at = models.DateTimeField(
        _('sent at'),
        null=True,
        blank=True
    )

    delivered_at = models.DateTimeField(
        _('delivered at'),
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Notification Delivery Log')
        verbose_name_plural = _('Notification Delivery Logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['notification', 'channel']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.notification.title} via {self.channel.name} - {self.status}"


class NotificationQueue(models.Model):
    """
    Queue for batch processing of notifications.
    """
    PRIORITY_CHOICES = Notification.PRIORITY_CHOICES

    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('processing', _('Processing')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
    ]

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='queue_items'
    )

    channel = models.ForeignKey(
        NotificationChannel,
        on_delete=models.CASCADE
    )

    priority = models.CharField(
        _('priority'),
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal'
    )

    scheduled_at = models.DateTimeField(
        _('scheduled at'),
        default=timezone.now,
        help_text=_('When to send this notification.')
    )

    attempts = models.PositiveIntegerField(
        _('attempts'),
        default=0
    )

    max_attempts = models.PositiveIntegerField(
        _('max attempts'),
        default=3
    )

    status = models.CharField(
        _('status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    error_message = models.TextField(
        _('error message'),
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Notification Queue Item')
        verbose_name_plural = _('Notification Queue Items')
        ordering = ['priority', 'scheduled_at']
        indexes = [
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['priority', 'scheduled_at']),
        ]

    def __str__(self):
        return f"{self.notification.title} via {self.channel.name} - {self.status}"

    @property
    def can_retry(self):
        """Check if notification can be retried."""
        return self.attempts < self.max_attempts and self.status == 'failed'
