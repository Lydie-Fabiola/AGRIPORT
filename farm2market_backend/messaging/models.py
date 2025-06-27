"""
Real-time messaging models for Farm2Market.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.core.models import BaseModel
from datetime import timedelta
import os

User = get_user_model()


class Conversation(BaseModel):
    """
    Conversation model for messaging between users.
    """
    participants = models.ManyToManyField(
        User,
        through='ConversationParticipant',
        related_name='conversations',
        help_text=_('Users participating in this conversation.')
    )
    
    subject = models.CharField(
        _('subject'),
        max_length=200,
        blank=True,
        help_text=_('Subject or title of the conversation.')
    )
    
    related_product = models.ForeignKey(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations',
        help_text=_('Product related to this conversation.')
    )
    
    related_order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations',
        help_text=_('Order related to this conversation.')
    )
    
    is_active = models.BooleanField(
        _('is active'),
        default=True,
        help_text=_('Whether this conversation is active.')
    )
    
    last_message_at = models.DateTimeField(
        _('last message at'),
        null=True,
        blank=True,
        help_text=_('Timestamp of the last message.')
    )
    
    class Meta:
        verbose_name = _('Conversation')
        verbose_name_plural = _('Conversations')
        ordering = ['-last_message_at', '-created_at']
        indexes = [
            models.Index(fields=['related_product']),
            models.Index(fields=['related_order']),
            models.Index(fields=['is_active', 'last_message_at']),
        ]
        
    def __str__(self):
        if self.subject:
            return self.subject
        elif self.related_product:
            return f"Conversation about {self.related_product.product_name}"
        elif self.related_order:
            return f"Conversation about Order {self.related_order.order_number}"
        else:
            participant_names = [p.full_name for p in self.participants.all()[:2]]
            return f"Conversation: {', '.join(participant_names)}"
    
    @property
    def participant_count(self):
        """Get number of active participants."""
        return self.participants.filter(
            conversationparticipant__is_active=True
        ).count()
    
    def get_other_participant(self, user):
        """Get the other participant in a 2-person conversation."""
        return self.participants.exclude(id=user.id).first()
    
    def add_participant(self, user):
        """Add a participant to the conversation."""
        participant, created = ConversationParticipant.objects.get_or_create(
            conversation=self,
            user=user,
            defaults={'is_active': True}
        )
        if not created and not participant.is_active:
            participant.is_active = True
            participant.left_at = None
            participant.save()
        return participant
    
    def remove_participant(self, user):
        """Remove a participant from the conversation."""
        try:
            participant = ConversationParticipant.objects.get(
                conversation=self,
                user=user
            )
            participant.is_active = False
            participant.left_at = timezone.now()
            participant.save()
            return True
        except ConversationParticipant.DoesNotExist:
            return False
    
    def get_unread_count(self, user):
        """Get unread message count for a user."""
        # Get messages after user's last read
        last_read = MessageRead.objects.filter(
            message__conversation=self,
            user=user
        ).order_by('-read_at').first()
        
        if last_read:
            return self.messages.filter(
                created_at__gt=last_read.read_at
            ).exclude(sender=user).count()
        else:
            return self.messages.exclude(sender=user).count()


class ConversationParticipant(models.Model):
    """
    Through model for conversation participants.
    """
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    
    joined_at = models.DateTimeField(
        _('joined at'),
        auto_now_add=True
    )
    
    left_at = models.DateTimeField(
        _('left at'),
        null=True,
        blank=True
    )
    
    is_active = models.BooleanField(
        _('is active'),
        default=True
    )
    
    class Meta:
        verbose_name = _('Conversation Participant')
        verbose_name_plural = _('Conversation Participants')
        unique_together = ['conversation', 'user']
        
    def __str__(self):
        return f"{self.user.full_name} in {self.conversation}"


class Message(BaseModel):
    """
    Message model for individual messages in conversations.
    """
    MESSAGE_TYPE_CHOICES = [
        ('text', _('Text')),
        ('image', _('Image')),
        ('file', _('File')),
        ('system', _('System')),
    ]
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    
    content = models.TextField(
        _('content'),
        help_text=_('Message content.')
    )
    
    message_type = models.CharField(
        _('message type'),
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
        default='text'
    )
    
    attachment = models.FileField(
        _('attachment'),
        upload_to='messages/%Y/%m/',
        null=True,
        blank=True,
        help_text=_('File attachment.')
    )
    
    attachment_name = models.CharField(
        _('attachment name'),
        max_length=255,
        blank=True,
        help_text=_('Original filename of attachment.')
    )
    
    attachment_size = models.PositiveIntegerField(
        _('attachment size'),
        null=True,
        blank=True,
        help_text=_('Size of attachment in bytes.')
    )
    
    is_edited = models.BooleanField(
        _('is edited'),
        default=False
    )
    
    edited_at = models.DateTimeField(
        _('edited at'),
        null=True,
        blank=True
    )
    
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
        help_text=_('Message this is replying to.')
    )
    
    class Meta:
        verbose_name = _('Message')
        verbose_name_plural = _('Messages')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender']),
            models.Index(fields=['message_type']),
        ]
        
    def __str__(self):
        return f"Message from {self.sender.full_name} in {self.conversation}"
    
    def save(self, *args, **kwargs):
        # Store attachment info
        if self.attachment:
            self.attachment_name = self.attachment.name
            self.attachment_size = self.attachment.size
        
        super().save(*args, **kwargs)
        
        # Update conversation's last message timestamp
        self.conversation.last_message_at = self.created_at
        self.conversation.save(update_fields=['last_message_at'])
    
    @property
    def is_read_by_all(self):
        """Check if message is read by all participants except sender."""
        participants = self.conversation.participants.exclude(id=self.sender.id)
        read_count = MessageRead.objects.filter(
            message=self,
            user__in=participants
        ).count()
        return read_count == participants.count()
    
    def mark_as_read(self, user):
        """Mark message as read by user."""
        if user != self.sender:
            MessageRead.objects.get_or_create(
                message=self,
                user=user
            )
    
    def get_attachment_url(self):
        """Get attachment URL if exists."""
        if self.attachment:
            return self.attachment.url
        return None
    
    def get_attachment_extension(self):
        """Get file extension of attachment."""
        if self.attachment_name:
            return os.path.splitext(self.attachment_name)[1].lower()
        return None


class MessageRead(models.Model):
    """
    Track message read status by users.
    """
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='read_by'
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='message_reads'
    )
    
    read_at = models.DateTimeField(
        _('read at'),
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = _('Message Read')
        verbose_name_plural = _('Message Reads')
        unique_together = ['message', 'user']
        indexes = [
            models.Index(fields=['message']),
            models.Index(fields=['user', 'read_at']),
        ]
        
    def __str__(self):
        return f"{self.user.full_name} read message {self.message.id}"


class MessageTemplate(BaseModel):
    """
    Template for automated and quick messages.
    """
    TEMPLATE_TYPE_CHOICES = [
        ('order_confirmation', _('Order Confirmation')),
        ('delivery_update', _('Delivery Update')),
        ('price_inquiry', _('Price Inquiry')),
        ('negotiation', _('Negotiation')),
        ('general', _('General')),
    ]
    
    name = models.CharField(
        _('name'),
        max_length=100,
        help_text=_('Template name.')
    )
    
    template_type = models.CharField(
        _('template type'),
        max_length=30,
        choices=TEMPLATE_TYPE_CHOICES,
        default='general'
    )
    
    content = models.TextField(
        _('content'),
        help_text=_('Template content with variables like {{variable_name}}.')
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
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_templates'
    )
    
    class Meta:
        verbose_name = _('Message Template')
        verbose_name_plural = _('Message Templates')
        ordering = ['template_type', 'name']
        indexes = [
            models.Index(fields=['template_type', 'is_active']),
        ]
        
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"
    
    def render(self, **context):
        """Render template with provided context."""
        content = self.content
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            content = content.replace(placeholder, str(value))
        return content


class UserOnlineStatus(models.Model):
    """
    Track user online status for real-time features.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='online_status'
    )
    
    is_online = models.BooleanField(
        _('is online'),
        default=False
    )
    
    last_seen = models.DateTimeField(
        _('last seen'),
        auto_now=True
    )
    
    device_info = models.CharField(
        _('device info'),
        max_length=255,
        blank=True
    )
    
    ip_address = models.GenericIPAddressField(
        _('IP address'),
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('User Online Status')
        verbose_name_plural = _('User Online Statuses')
        
    def __str__(self):
        status = "Online" if self.is_online else f"Last seen {self.last_seen}"
        return f"{self.user.full_name} - {status}"
    
    @property
    def is_recently_active(self):
        """Check if user was active in the last 5 minutes."""
        return timezone.now() - self.last_seen < timedelta(minutes=5)


class TypingIndicator(models.Model):
    """
    Track typing indicators for real-time messaging.
    """
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='typing_indicators'
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='typing_indicators'
    )
    
    is_typing = models.BooleanField(
        _('is typing'),
        default=True
    )
    
    started_at = models.DateTimeField(
        _('started at'),
        auto_now_add=True
    )
    
    expires_at = models.DateTimeField(
        _('expires at'),
        help_text=_('When this typing indicator expires.')
    )
    
    class Meta:
        verbose_name = _('Typing Indicator')
        verbose_name_plural = _('Typing Indicators')
        unique_together = ['conversation', 'user']
        
    def __str__(self):
        return f"{self.user.full_name} typing in {self.conversation}"
    
    def save(self, *args, **kwargs):
        # Set expiration time (default 10 seconds)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(seconds=10)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if typing indicator has expired."""
        return timezone.now() > self.expires_at
