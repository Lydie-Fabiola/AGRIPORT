"""
Farmer-specific models for Farm2Market.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import BaseModel, StatusChoices
import os

User = get_user_model()


class FarmCertification(BaseModel):
    """
    Model for farm certifications.
    """
    CERTIFICATION_TYPES = [
        ('organic', _('Organic Certification')),
        ('fair_trade', _('Fair Trade Certification')),
        ('gmp', _('Good Manufacturing Practice')),
        ('haccp', _('HACCP Certification')),
        ('iso', _('ISO Certification')),
        ('gap', _('Good Agricultural Practice')),
        ('rainforest', _('Rainforest Alliance')),
        ('other', _('Other Certification')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending Verification')),
        ('verified', _('Verified')),
        ('rejected', _('Rejected')),
        ('expired', _('Expired')),
    ]
    
    farmer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='certifications',
        limit_choices_to={'user_type': 'Farmer'}
    )
    
    certification_type = models.CharField(
        _('certification type'),
        max_length=50,
        choices=CERTIFICATION_TYPES
    )
    
    certification_name = models.CharField(
        _('certification name'),
        max_length=200,
        help_text=_('Official name of the certification.')
    )
    
    issuing_authority = models.CharField(
        _('issuing authority'),
        max_length=200,
        help_text=_('Organization that issued the certification.')
    )
    
    certificate_number = models.CharField(
        _('certificate number'),
        max_length=100,
        unique=True,
        help_text=_('Unique certificate identification number.')
    )
    
    issue_date = models.DateField(
        _('issue date'),
        help_text=_('Date when the certificate was issued.')
    )
    
    expiry_date = models.DateField(
        _('expiry date'),
        help_text=_('Date when the certificate expires.')
    )
    
    certificate_file = models.FileField(
        _('certificate file'),
        upload_to='certifications/',
        help_text=_('Upload the certificate document (PDF, JPG, PNG).')
    )
    
    verification_status = models.CharField(
        _('verification status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_certifications',
        limit_choices_to={'user_type': 'Admin'}
    )
    
    verified_at = models.DateTimeField(
        _('verified at'),
        null=True,
        blank=True
    )
    
    rejection_reason = models.TextField(
        _('rejection reason'),
        blank=True,
        help_text=_('Reason for rejection if applicable.')
    )
    
    notes = models.TextField(
        _('notes'),
        blank=True,
        help_text=_('Additional notes about the certification.')
    )
    
    class Meta:
        verbose_name = _('Farm Certification')
        verbose_name_plural = _('Farm Certifications')
        unique_together = ['farmer', 'certificate_number']
        
    def __str__(self):
        return f"{self.farmer.full_name} - {self.get_certification_type_display()}"
    
    @property
    def is_expired(self):
        """Check if certification is expired."""
        from django.utils import timezone
        return timezone.now().date() > self.expiry_date
    
    @property
    def is_valid(self):
        """Check if certification is valid (verified and not expired)."""
        return self.verification_status == 'verified' and not self.is_expired
    
    @property
    def days_until_expiry(self):
        """Calculate days until expiry."""
        from django.utils import timezone
        delta = self.expiry_date - timezone.now().date()
        return delta.days


class FarmImage(BaseModel):
    """
    Model for farm images.
    """
    farmer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='farm_images',
        limit_choices_to={'user_type': 'Farmer'}
    )
    
    image = models.ImageField(
        _('farm image'),
        upload_to='farm_images/',
        help_text=_('Upload farm image.')
    )
    
    title = models.CharField(
        _('image title'),
        max_length=200,
        blank=True
    )
    
    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Description of the image.')
    )
    
    is_primary = models.BooleanField(
        _('is primary'),
        default=False,
        help_text=_('Set as primary farm image.')
    )
    
    display_order = models.PositiveIntegerField(
        _('display order'),
        default=0,
        help_text=_('Order in which images are displayed.')
    )
    
    class Meta:
        verbose_name = _('Farm Image')
        verbose_name_plural = _('Farm Images')
        ordering = ['display_order', '-created_at']
        
    def __str__(self):
        return f"{self.farmer.full_name} - {self.title or 'Farm Image'}"
    
    def save(self, *args, **kwargs):
        # Ensure only one primary image per farmer
        if self.is_primary:
            FarmImage.objects.filter(
                farmer=self.farmer,
                is_primary=True
            ).exclude(id=self.id).update(is_primary=False)
        super().save(*args, **kwargs)


class FarmLocation(BaseModel):
    """
    Model for farm locations (farmers can have multiple farm locations).
    """
    farmer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='farm_locations',
        limit_choices_to={'user_type': 'Farmer'}
    )
    
    name = models.CharField(
        _('location name'),
        max_length=200,
        help_text=_('Name or identifier for this farm location.')
    )
    
    address = models.TextField(
        _('address'),
        help_text=_('Full address of the farm location.')
    )
    
    city = models.CharField(
        _('city'),
        max_length=100
    )
    
    state = models.CharField(
        _('state/region'),
        max_length=100
    )
    
    country = models.CharField(
        _('country'),
        max_length=100,
        default='Cameroon'
    )
    
    postal_code = models.CharField(
        _('postal code'),
        max_length=20,
        blank=True
    )
    
    latitude = models.DecimalField(
        _('latitude'),
        max_digits=10,
        decimal_places=8,
        null=True,
        blank=True
    )
    
    longitude = models.DecimalField(
        _('longitude'),
        max_digits=11,
        decimal_places=8,
        null=True,
        blank=True
    )
    
    farm_size = models.DecimalField(
        _('farm size (hectares)'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    
    is_primary = models.BooleanField(
        _('is primary location'),
        default=False,
        help_text=_('Set as primary farm location.')
    )
    
    is_active = models.BooleanField(
        _('is active'),
        default=True,
        help_text=_('Whether this location is currently active.')
    )
    
    notes = models.TextField(
        _('notes'),
        blank=True,
        help_text=_('Additional notes about this location.')
    )
    
    class Meta:
        verbose_name = _('Farm Location')
        verbose_name_plural = _('Farm Locations')
        unique_together = ['farmer', 'name']
        
    def __str__(self):
        return f"{self.farmer.full_name} - {self.name}"
    
    def save(self, *args, **kwargs):
        # Ensure only one primary location per farmer
        if self.is_primary:
            FarmLocation.objects.filter(
                farmer=self.farmer,
                is_primary=True
            ).exclude(id=self.id).update(is_primary=False)
        super().save(*args, **kwargs)
