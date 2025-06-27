"""
Search and discovery models for Farm2Market.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import BaseModel
import json

User = get_user_model()


class SearchQuery(BaseModel):
    """
    Model for tracking search queries and analytics.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='search_queries',
        help_text=_('User who performed the search (null for anonymous users).')
    )
    
    query = models.CharField(
        _('search query'),
        max_length=500,
        help_text=_('The search query string.')
    )
    
    filters = models.JSONField(
        _('search filters'),
        default=dict,
        blank=True,
        help_text=_('Applied filters in JSON format.')
    )
    
    results_count = models.PositiveIntegerField(
        _('results count'),
        default=0,
        help_text=_('Number of results returned.')
    )
    
    timestamp = models.DateTimeField(
        _('search timestamp'),
        auto_now_add=True,
        help_text=_('When the search was performed.')
    )
    
    # Additional tracking fields
    ip_address = models.GenericIPAddressField(
        _('IP address'),
        null=True,
        blank=True,
        help_text=_('IP address of the searcher.')
    )
    
    user_agent = models.TextField(
        _('user agent'),
        blank=True,
        help_text=_('Browser user agent string.')
    )
    
    session_id = models.CharField(
        _('session ID'),
        max_length=100,
        blank=True,
        help_text=_('Session identifier for anonymous users.')
    )
    
    class Meta:
        verbose_name = _('Search Query')
        verbose_name_plural = _('Search Queries')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['query']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['results_count']),
        ]
        
    def __str__(self):
        user_info = self.user.email if self.user else 'Anonymous'
        return f"{user_info}: '{self.query}' ({self.results_count} results)"
    
    @property
    def has_results(self):
        """Check if search returned any results."""
        return self.results_count > 0
    
    def get_filters_display(self):
        """Get human-readable filters."""
        if not self.filters:
            return "No filters"
        
        filter_parts = []
        for key, value in self.filters.items():
            if value:
                filter_parts.append(f"{key}: {value}")
        
        return ", ".join(filter_parts) if filter_parts else "No filters"


class PopularSearch(models.Model):
    """
    Model for tracking popular search terms.
    """
    query = models.CharField(
        _('search query'),
        max_length=200,
        unique=True,
        help_text=_('Popular search term.')
    )
    
    search_count = models.PositiveIntegerField(
        _('search count'),
        default=0,
        help_text=_('Number of times this term has been searched.')
    )
    
    last_searched = models.DateTimeField(
        _('last searched'),
        auto_now=True,
        help_text=_('When this term was last searched.')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Popular Search')
        verbose_name_plural = _('Popular Searches')
        ordering = ['-search_count', '-last_searched']
        indexes = [
            models.Index(fields=['-search_count']),
            models.Index(fields=['-last_searched']),
        ]
        
    def __str__(self):
        return f"'{self.query}' ({self.search_count} searches)"
    
    @classmethod
    def increment_search_count(cls, query):
        """Increment search count for a query."""
        popular_search, created = cls.objects.get_or_create(
            query=query.lower().strip(),
            defaults={'search_count': 1}
        )
        
        if not created:
            popular_search.search_count += 1
            popular_search.save(update_fields=['search_count', 'last_searched'])
        
        return popular_search


class DeliveryZone(BaseModel):
    """
    Model for farmer delivery zones with geospatial data.
    """
    farmer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='delivery_zones',
        limit_choices_to={'user_type': 'Farmer'},
        help_text=_('Farmer who owns this delivery zone.')
    )
    
    zone_name = models.CharField(
        _('zone name'),
        max_length=100,
        help_text=_('Name of the delivery zone.')
    )
    
    coordinates = models.JSONField(
        _('coordinates'),
        help_text=_('GeoJSON polygon coordinates for the delivery zone.')
    )
    
    delivery_fee = models.DecimalField(
        _('delivery fee'),
        max_digits=8,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        help_text=_('Delivery fee for this zone.')
    )
    
    minimum_order = models.DecimalField(
        _('minimum order'),
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        help_text=_('Minimum order amount for delivery to this zone.')
    )
    
    is_active = models.BooleanField(
        _('is active'),
        default=True,
        help_text=_('Whether delivery is available to this zone.')
    )
    
    # Additional zone information
    estimated_delivery_time = models.CharField(
        _('estimated delivery time'),
        max_length=50,
        blank=True,
        help_text=_('Estimated delivery time (e.g., "2-4 hours", "Next day").')
    )
    
    delivery_days = models.JSONField(
        _('delivery days'),
        default=list,
        blank=True,
        help_text=_('Days of the week when delivery is available.')
    )
    
    notes = models.TextField(
        _('notes'),
        blank=True,
        help_text=_('Additional notes about delivery to this zone.')
    )
    
    class Meta:
        verbose_name = _('Delivery Zone')
        verbose_name_plural = _('Delivery Zones')
        unique_together = ['farmer', 'zone_name']
        indexes = [
            models.Index(fields=['farmer', 'is_active']),
            models.Index(fields=['delivery_fee']),
        ]
        
    def __str__(self):
        return f"{self.farmer.full_name} - {self.zone_name}"
    
    def get_coordinates_as_geojson(self):
        """Get coordinates in GeoJSON format."""
        return {
            "type": "Polygon",
            "coordinates": self.coordinates
        }
    
    @property
    def has_delivery_fee(self):
        """Check if zone has delivery fee."""
        return self.delivery_fee > 0


class ProductView(models.Model):
    """
    Model for tracking product views and analytics.
    """
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='product_views'
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='product_views'
    )
    
    ip_address = models.GenericIPAddressField(
        _('IP address'),
        null=True,
        blank=True
    )
    
    user_agent = models.TextField(
        _('user agent'),
        blank=True
    )
    
    viewed_at = models.DateTimeField(
        _('viewed at'),
        auto_now_add=True
    )
    
    # Additional tracking
    referrer = models.URLField(
        _('referrer'),
        blank=True,
        help_text=_('Page that referred to this product.')
    )
    
    session_id = models.CharField(
        _('session ID'),
        max_length=100,
        blank=True
    )
    
    class Meta:
        verbose_name = _('Product View')
        verbose_name_plural = _('Product Views')
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['product', 'viewed_at']),
            models.Index(fields=['user', 'viewed_at']),
            models.Index(fields=['viewed_at']),
        ]
        
    def __str__(self):
        user_info = self.user.email if self.user else f"Anonymous ({self.ip_address})"
        return f"{user_info} viewed {self.product.product_name}"


class SavedSearch(BaseModel):
    """
    Model for user's saved searches with notifications.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='saved_searches'
    )
    
    name = models.CharField(
        _('search name'),
        max_length=100,
        help_text=_('User-defined name for this saved search.')
    )
    
    search_query = models.CharField(
        _('search query'),
        max_length=500,
        blank=True,
        help_text=_('The search query string.')
    )
    
    filters = models.JSONField(
        _('search filters'),
        default=dict,
        blank=True,
        help_text=_('Search filters in JSON format.')
    )
    
    is_active = models.BooleanField(
        _('is active'),
        default=True,
        help_text=_('Whether this saved search is active.')
    )
    
    notification_enabled = models.BooleanField(
        _('notification enabled'),
        default=False,
        help_text=_('Send notifications when new products match this search.')
    )
    
    last_notification_sent = models.DateTimeField(
        _('last notification sent'),
        null=True,
        blank=True,
        help_text=_('When the last notification was sent for this search.')
    )
    
    class Meta:
        verbose_name = _('Saved Search')
        verbose_name_plural = _('Saved Searches')
        unique_together = ['user', 'name']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['notification_enabled']),
        ]
        
    def __str__(self):
        return f"{self.user.email} - {self.name}"
    
    def get_filters_display(self):
        """Get human-readable filters."""
        if not self.filters:
            return "No filters"
        
        filter_parts = []
        for key, value in self.filters.items():
            if value:
                filter_parts.append(f"{key}: {value}")
        
        return ", ".join(filter_parts) if filter_parts else "No filters"
