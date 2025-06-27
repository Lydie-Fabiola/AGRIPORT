"""
Buyer-specific models for Farm2Market.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import BaseModel, StatusChoices

User = get_user_model()


class BuyerAddress(BaseModel):
    """
    Model for buyer delivery addresses.
    """
    ADDRESS_TYPES = [
        ('home', _('Home')),
        ('office', _('Office')),
        ('warehouse', _('Warehouse')),
        ('store', _('Store')),
        ('other', _('Other')),
    ]
    
    buyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='addresses',
        limit_choices_to={'user_type': 'Buyer'}
    )
    
    address_type = models.CharField(
        _('address type'),
        max_length=20,
        choices=ADDRESS_TYPES,
        default='home'
    )
    
    title = models.CharField(
        _('address title'),
        max_length=100,
        help_text=_('e.g., "Home", "Office", "Main Store"')
    )
    
    full_name = models.CharField(
        _('full name'),
        max_length=200,
        help_text=_('Full name for delivery.')
    )
    
    phone_number = models.CharField(
        _('phone number'),
        max_length=20,
        help_text=_('Contact phone number for delivery.')
    )
    
    address_line_1 = models.CharField(
        _('address line 1'),
        max_length=200,
        help_text=_('Street address, building name, etc.')
    )
    
    address_line_2 = models.CharField(
        _('address line 2'),
        max_length=200,
        blank=True,
        help_text=_('Apartment, suite, unit, etc.')
    )
    
    city = models.CharField(
        _('city'),
        max_length=100
    )
    
    state = models.CharField(
        _('state/region'),
        max_length=100
    )
    
    postal_code = models.CharField(
        _('postal code'),
        max_length=20,
        blank=True
    )
    
    country = models.CharField(
        _('country'),
        max_length=100,
        default='Cameroon'
    )
    
    latitude = models.DecimalField(
        _('latitude'),
        max_digits=10,
        decimal_places=8,
        null=True,
        blank=True,
        help_text=_('GPS latitude for precise delivery.')
    )
    
    longitude = models.DecimalField(
        _('longitude'),
        max_digits=11,
        decimal_places=8,
        null=True,
        blank=True,
        help_text=_('GPS longitude for precise delivery.')
    )
    
    is_default = models.BooleanField(
        _('is default address'),
        default=False,
        help_text=_('Set as default delivery address.')
    )
    
    delivery_instructions = models.TextField(
        _('delivery instructions'),
        blank=True,
        help_text=_('Special instructions for delivery.')
    )
    
    is_active = models.BooleanField(
        _('is active'),
        default=True
    )
    
    class Meta:
        verbose_name = _('Buyer Address')
        verbose_name_plural = _('Buyer Addresses')
        unique_together = ['buyer', 'title']
        
    def __str__(self):
        return f"{self.buyer.full_name} - {self.title}"
    
    def save(self, *args, **kwargs):
        # Ensure only one default address per buyer
        if self.is_default:
            BuyerAddress.objects.filter(
                buyer=self.buyer,
                is_default=True
            ).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)


class BuyerPreferences(models.Model):
    """
    Model for buyer preferences and settings.
    """
    buyer = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='buyer_preferences',
        limit_choices_to={'user_type': 'Buyer'}
    )
    
    # Product preferences
    preferred_categories = models.ManyToManyField(
        'products.Category',
        blank=True,
        related_name='preferred_by_buyers',
        help_text=_('Preferred product categories.')
    )
    
    organic_only = models.BooleanField(
        _('organic products only'),
        default=False,
        help_text=_('Only show organic certified products.')
    )
    
    local_farmers_only = models.BooleanField(
        _('local farmers only'),
        default=False,
        help_text=_('Prefer products from local farmers.')
    )
    
    max_delivery_distance = models.PositiveIntegerField(
        _('max delivery distance (km)'),
        default=50,
        validators=[MinValueValidator(1), MaxValueValidator(500)],
        help_text=_('Maximum delivery distance in kilometers.')
    )
    
    # Price preferences
    budget_range_min = models.DecimalField(
        _('minimum budget'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Minimum budget per order.')
    )
    
    budget_range_max = models.DecimalField(
        _('maximum budget'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Maximum budget per order.')
    )
    
    # Notification preferences
    email_notifications = models.BooleanField(
        _('email notifications'),
        default=True,
        help_text=_('Receive email notifications.')
    )
    
    sms_notifications = models.BooleanField(
        _('SMS notifications'),
        default=False,
        help_text=_('Receive SMS notifications.')
    )
    
    push_notifications = models.BooleanField(
        _('push notifications'),
        default=True,
        help_text=_('Receive push notifications.')
    )
    
    # Notification types
    new_products_alerts = models.BooleanField(
        _('new products alerts'),
        default=True,
        help_text=_('Get notified about new products from favorite farmers.')
    )
    
    price_drop_alerts = models.BooleanField(
        _('price drop alerts'),
        default=True,
        help_text=_('Get notified about price drops on wishlist items.')
    )
    
    order_updates = models.BooleanField(
        _('order updates'),
        default=True,
        help_text=_('Get notified about order status updates.')
    )
    
    farmer_updates = models.BooleanField(
        _('farmer updates'),
        default=False,
        help_text=_('Get notified about updates from favorite farmers.')
    )
    
    # Shopping preferences
    auto_reorder = models.BooleanField(
        _('auto reorder'),
        default=False,
        help_text=_('Automatically reorder frequently bought items.')
    )
    
    save_payment_methods = models.BooleanField(
        _('save payment methods'),
        default=False,
        help_text=_('Save payment methods for faster checkout.')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Buyer Preferences')
        verbose_name_plural = _('Buyer Preferences')
        
    def __str__(self):
        return f"Preferences - {self.buyer.full_name}"


class FavoriteFarmer(BaseModel):
    """
    Model for buyer's favorite farmers.
    """
    buyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorite_farmers',
        limit_choices_to={'user_type': 'Buyer'}
    )
    
    farmer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorited_by_buyers',
        limit_choices_to={'user_type': 'Farmer'}
    )
    
    notes = models.TextField(
        _('notes'),
        blank=True,
        help_text=_('Personal notes about this farmer.')
    )
    
    class Meta:
        verbose_name = _('Favorite Farmer')
        verbose_name_plural = _('Favorite Farmers')
        unique_together = ['buyer', 'farmer']
        
    def __str__(self):
        return f"{self.buyer.full_name} -> {self.farmer.full_name}"


class Wishlist(BaseModel):
    """
    Model for buyer's wishlist items.
    """
    buyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='wishlist_items',
        limit_choices_to={'user_type': 'Buyer'}
    )
    
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='wishlisted_by_buyers'
    )
    
    desired_quantity = models.PositiveIntegerField(
        _('desired quantity'),
        default=1,
        help_text=_('Desired quantity to purchase.')
    )
    
    target_price = models.DecimalField(
        _('target price'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Target price per unit.')
    )
    
    notes = models.TextField(
        _('notes'),
        blank=True,
        help_text=_('Personal notes about this wishlist item.')
    )
    
    notify_when_available = models.BooleanField(
        _('notify when available'),
        default=True,
        help_text=_('Get notified when product becomes available.')
    )
    
    notify_on_price_drop = models.BooleanField(
        _('notify on price drop'),
        default=True,
        help_text=_('Get notified when price drops below target price.')
    )
    
    class Meta:
        verbose_name = _('Wishlist Item')
        verbose_name_plural = _('Wishlist Items')
        unique_together = ['buyer', 'product']
        
    def __str__(self):
        return f"{self.buyer.full_name} - {self.product.product_name}"
    
    @property
    def is_price_target_met(self):
        """Check if current price meets target price."""
        if self.target_price:
            return self.product.price <= self.target_price
        return False
    
    @property
    def is_available(self):
        """Check if product is available."""
        return self.product.is_in_stock and self.product.status == 'Available'
