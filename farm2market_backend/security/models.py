"""
Security models for Farm2Market.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.core.models import BaseModel
import json

User = get_user_model()


class LoginAttempt(models.Model):
    """
    Track login attempts for security monitoring.
    """
    STATUS_CHOICES = [
        ('success', _('Success')),
        ('failed', _('Failed')),
        ('blocked', _('Blocked')),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='login_attempts'
    )
    
    email = models.EmailField(
        _('email'),
        help_text=_('Email used in login attempt.')
    )
    
    ip_address = models.GenericIPAddressField(
        _('IP address')
    )
    
    user_agent = models.CharField(
        _('user agent'),
        max_length=500,
        blank=True
    )
    
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=STATUS_CHOICES
    )
    
    failure_reason = models.CharField(
        _('failure reason'),
        max_length=100,
        blank=True,
        help_text=_('Reason for failed login.')
    )
    
    timestamp = models.DateTimeField(
        _('timestamp'),
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = _('Login Attempt')
        verbose_name_plural = _('Login Attempts')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['email', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
            models.Index(fields=['status']),
        ]
        
    def __str__(self):
        return f"{self.email} - {self.status} at {self.timestamp}"


class AccountLockout(models.Model):
    """
    Track account lockouts due to failed login attempts.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='lockouts'
    )
    
    ip_address = models.GenericIPAddressField(
        _('IP address'),
        null=True,
        blank=True
    )
    
    failed_attempts = models.PositiveIntegerField(
        _('failed attempts'),
        default=0
    )
    
    locked_at = models.DateTimeField(
        _('locked at'),
        auto_now_add=True
    )
    
    unlocked_at = models.DateTimeField(
        _('unlocked at'),
        null=True,
        blank=True
    )
    
    is_active = models.BooleanField(
        _('is active'),
        default=True,
        help_text=_('Whether this lockout is currently active.')
    )
    
    class Meta:
        verbose_name = _('Account Lockout')
        verbose_name_plural = _('Account Lockouts')
        ordering = ['-locked_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['ip_address']),
        ]
        
    def __str__(self):
        return f"{self.user.email} locked at {self.locked_at}"
    
    def unlock(self):
        """Unlock the account."""
        self.is_active = False
        self.unlocked_at = timezone.now()
        self.save()


class SecurityEvent(models.Model):
    """
    Track security events for monitoring and alerting.
    """
    EVENT_TYPE_CHOICES = [
        ('login_success', _('Login Success')),
        ('login_failed', _('Login Failed')),
        ('account_locked', _('Account Locked')),
        ('password_changed', _('Password Changed')),
        ('email_changed', _('Email Changed')),
        ('profile_updated', _('Profile Updated')),
        ('suspicious_activity', _('Suspicious Activity')),
        ('rate_limit_exceeded', _('Rate Limit Exceeded')),
        ('invalid_token', _('Invalid Token')),
        ('permission_denied', _('Permission Denied')),
        ('data_breach_attempt', _('Data Breach Attempt')),
        ('file_upload_blocked', _('File Upload Blocked')),
    ]
    
    SEVERITY_CHOICES = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('critical', _('Critical')),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_events'
    )
    
    event_type = models.CharField(
        _('event type'),
        max_length=50,
        choices=EVENT_TYPE_CHOICES
    )
    
    severity = models.CharField(
        _('severity'),
        max_length=20,
        choices=SEVERITY_CHOICES,
        default='low'
    )
    
    description = models.TextField(
        _('description'),
        help_text=_('Detailed description of the security event.')
    )
    
    ip_address = models.GenericIPAddressField(
        _('IP address'),
        null=True,
        blank=True
    )
    
    user_agent = models.CharField(
        _('user agent'),
        max_length=500,
        blank=True
    )
    
    metadata = models.JSONField(
        _('metadata'),
        default=dict,
        blank=True,
        help_text=_('Additional event data.')
    )
    
    timestamp = models.DateTimeField(
        _('timestamp'),
        auto_now_add=True
    )
    
    is_resolved = models.BooleanField(
        _('is resolved'),
        default=False
    )
    
    resolved_at = models.DateTimeField(
        _('resolved at'),
        null=True,
        blank=True
    )
    
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_security_events'
    )
    
    class Meta:
        verbose_name = _('Security Event')
        verbose_name_plural = _('Security Events')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['event_type', 'severity']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['is_resolved']),
        ]
        
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.get_severity_display()}"
    
    def resolve(self, resolved_by=None):
        """Mark security event as resolved."""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.resolved_by = resolved_by
        self.save()


class RateLimitViolation(models.Model):
    """
    Track rate limit violations.
    """
    identifier = models.CharField(
        _('identifier'),
        max_length=255,
        help_text=_('IP address, user ID, or other identifier.')
    )
    
    endpoint = models.CharField(
        _('endpoint'),
        max_length=255,
        help_text=_('API endpoint that was rate limited.')
    )
    
    limit_type = models.CharField(
        _('limit type'),
        max_length=50,
        help_text=_('Type of rate limit (per_minute, per_hour, etc.).')
    )
    
    violation_count = models.PositiveIntegerField(
        _('violation count'),
        default=1
    )
    
    timestamp = models.DateTimeField(
        _('timestamp'),
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = _('Rate Limit Violation')
        verbose_name_plural = _('Rate Limit Violations')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['identifier', 'endpoint']),
            models.Index(fields=['timestamp']),
        ]
        
    def __str__(self):
        return f"{self.identifier} - {self.endpoint} at {self.timestamp}"


class FileUploadScan(models.Model):
    """
    Track file upload security scans.
    """
    SCAN_STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('scanning', _('Scanning')),
        ('clean', _('Clean')),
        ('infected', _('Infected')),
        ('suspicious', _('Suspicious')),
        ('error', _('Error')),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='file_scans'
    )
    
    file_name = models.CharField(
        _('file name'),
        max_length=255
    )
    
    file_path = models.CharField(
        _('file path'),
        max_length=500
    )
    
    file_size = models.PositiveBigIntegerField(
        _('file size'),
        help_text=_('File size in bytes.')
    )
    
    file_hash = models.CharField(
        _('file hash'),
        max_length=64,
        help_text=_('SHA-256 hash of the file.')
    )
    
    mime_type = models.CharField(
        _('MIME type'),
        max_length=100
    )
    
    scan_status = models.CharField(
        _('scan status'),
        max_length=20,
        choices=SCAN_STATUS_CHOICES,
        default='pending'
    )
    
    scan_result = models.JSONField(
        _('scan result'),
        default=dict,
        blank=True,
        help_text=_('Detailed scan results.')
    )
    
    uploaded_at = models.DateTimeField(
        _('uploaded at'),
        auto_now_add=True
    )
    
    scanned_at = models.DateTimeField(
        _('scanned at'),
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = _('File Upload Scan')
        verbose_name_plural = _('File Upload Scans')
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['user', 'scan_status']),
            models.Index(fields=['file_hash']),
            models.Index(fields=['scan_status']),
        ]
        
    def __str__(self):
        return f"{self.file_name} - {self.get_scan_status_display()}"


class APIKey(BaseModel):
    """
    API keys for external integrations.
    """
    name = models.CharField(
        _('name'),
        max_length=100,
        help_text=_('Descriptive name for the API key.')
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='api_keys'
    )
    
    key = models.CharField(
        _('key'),
        max_length=64,
        unique=True,
        help_text=_('The API key value.')
    )
    
    permissions = models.JSONField(
        _('permissions'),
        default=list,
        blank=True,
        help_text=_('List of permissions for this API key.')
    )
    
    is_active = models.BooleanField(
        _('is active'),
        default=True
    )
    
    last_used = models.DateTimeField(
        _('last used'),
        null=True,
        blank=True
    )
    
    expires_at = models.DateTimeField(
        _('expires at'),
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = _('API Key')
        verbose_name_plural = _('API Keys')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['key']),
        ]
        
    def __str__(self):
        return f"{self.name} - {self.user.email}"
    
    @property
    def is_expired(self):
        """Check if API key is expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def update_last_used(self):
        """Update last used timestamp."""
        self.last_used = timezone.now()
        self.save(update_fields=['last_used'])
