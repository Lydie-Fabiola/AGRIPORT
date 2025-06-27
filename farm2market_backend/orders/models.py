"""
Order management models for Farm2Market.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from apps.core.models import BaseModel
from decimal import Decimal
import uuid
from datetime import datetime, timedelta
from django.utils import timezone

User = get_user_model()


class Order(BaseModel):
    """
    Main order model for Farm2Market.
    """
    ORDER_STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('confirmed', _('Confirmed')),
        ('preparing', _('Preparing')),
        ('ready', _('Ready for Pickup/Delivery')),
        ('in_transit', _('In Transit')),
        ('delivered', _('Delivered')),
        ('cancelled', _('Cancelled')),
        ('refunded', _('Refunded')),
    ]
    
    ORDER_TYPE_CHOICES = [
        ('immediate', _('Immediate Order')),
        ('reservation', _('Reservation Order')),
    ]
    
    DELIVERY_METHOD_CHOICES = [
        ('pickup', _('Pickup')),
        ('delivery', _('Delivery')),
        ('shipping', _('Shipping')),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', _('Cash')),
        ('mobile_money', _('Mobile Money')),
        ('bank_transfer', _('Bank Transfer')),
        ('credit_card', _('Credit Card')),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('paid', _('Paid')),
        ('failed', _('Failed')),
        ('refunded', _('Refunded')),
    ]
    
    order_number = models.CharField(
        _('order number'),
        max_length=20,
        unique=True,
        help_text=_('Unique order identifier.')
    )
    
    buyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders_as_buyer',
        limit_choices_to={'user_type': 'Buyer'},
        help_text=_('Buyer who placed the order.')
    )
    
    farmer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders_as_farmer',
        limit_choices_to={'user_type': 'Farmer'},
        help_text=_('Farmer fulfilling the order.')
    )
    
    status = models.CharField(
        _('order status'),
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default='pending'
    )
    
    order_type = models.CharField(
        _('order type'),
        max_length=20,
        choices=ORDER_TYPE_CHOICES,
        default='immediate'
    )
    
    subtotal = models.DecimalField(
        _('subtotal'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    delivery_fee = models.DecimalField(
        _('delivery fee'),
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    tax_amount = models.DecimalField(
        _('tax amount'),
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    total_amount = models.DecimalField(
        _('total amount'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    delivery_address = models.ForeignKey(
        'buyers.BuyerAddress',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        help_text=_('Delivery address for the order.')
    )
    
    delivery_method = models.CharField(
        _('delivery method'),
        max_length=20,
        choices=DELIVERY_METHOD_CHOICES,
        default='delivery'
    )
    
    preferred_delivery_date = models.DateTimeField(
        _('preferred delivery date'),
        null=True,
        blank=True,
        help_text=_('Buyer\'s preferred delivery date and time.')
    )
    
    actual_delivery_date = models.DateTimeField(
        _('actual delivery date'),
        null=True,
        blank=True,
        help_text=_('Actual delivery date and time.')
    )
    
    payment_method = models.CharField(
        _('payment method'),
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash'
    )
    
    payment_status = models.CharField(
        _('payment status'),
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    
    notes = models.TextField(
        _('notes'),
        blank=True,
        help_text=_('Additional notes for the order.')
    )
    
    # Additional tracking fields
    estimated_preparation_time = models.DurationField(
        _('estimated preparation time'),
        null=True,
        blank=True,
        help_text=_('Estimated time to prepare the order.')
    )
    
    tracking_number = models.CharField(
        _('tracking number'),
        max_length=100,
        blank=True,
        help_text=_('Tracking number for delivery.')
    )
    
    class Meta:
        verbose_name = _('Order')
        verbose_name_plural = _('Orders')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['buyer', 'status']),
            models.Index(fields=['farmer', 'status']),
            models.Index(fields=['order_number']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['payment_status']),
        ]
        
    def __str__(self):
        return f"Order {self.order_number} - {self.buyer.full_name}"
    
    def save(self, *args, **kwargs):
        # Auto-generate order number if not provided
        if not self.order_number:
            self.order_number = self.generate_order_number()
        
        # Calculate total amount
        self.total_amount = self.subtotal + self.delivery_fee + self.tax_amount
        
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_order_number():
        """Generate unique order number."""
        import random
        import string
        
        # Format: ORD-YYYYMMDD-XXXX (e.g., ORD-20241225-A1B2)
        date_str = datetime.now().strftime('%Y%m%d')
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        order_number = f"ORD-{date_str}-{random_str}"
        
        # Ensure uniqueness
        while Order.objects.filter(order_number=order_number).exists():
            random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            order_number = f"ORD-{date_str}-{random_str}"
        
        return order_number
    
    @property
    def can_be_cancelled(self):
        """Check if order can be cancelled."""
        return self.status in ['pending', 'confirmed']
    
    @property
    def is_completed(self):
        """Check if order is completed."""
        return self.status == 'delivered'
    
    @property
    def is_active(self):
        """Check if order is active (not cancelled or refunded)."""
        return self.status not in ['cancelled', 'refunded']
    
    def calculate_subtotal(self):
        """Calculate subtotal from order items."""
        return sum(item.total_price for item in self.items.all())
    
    def update_totals(self):
        """Update order totals based on items."""
        self.subtotal = self.calculate_subtotal()
        self.total_amount = self.subtotal + self.delivery_fee + self.tax_amount
        self.save(update_fields=['subtotal', 'total_amount'])


class OrderItem(models.Model):
    """
    Individual items within an order.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='order_items'
    )
    
    quantity = models.PositiveIntegerField(
        _('quantity'),
        validators=[MinValueValidator(1)]
    )
    
    unit_price = models.DecimalField(
        _('unit price'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    total_price = models.DecimalField(
        _('total price'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Snapshot of product details at time of order
    product_name = models.CharField(
        _('product name'),
        max_length=200,
        help_text=_('Product name at time of order.')
    )
    
    product_unit = models.CharField(
        _('product unit'),
        max_length=20,
        help_text=_('Product unit at time of order.')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Order Item')
        verbose_name_plural = _('Order Items')
        unique_together = ['order', 'product']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['product']),
        ]
        
    def __str__(self):
        return f"{self.product_name} x{self.quantity} - {self.order.order_number}"
    
    def save(self, *args, **kwargs):
        # Calculate total price
        self.total_price = self.unit_price * self.quantity
        
        # Store product snapshot
        if self.product:
            self.product_name = self.product.product_name
            self.product_unit = self.product.unit
        
        super().save(*args, **kwargs)


class OrderStatusHistory(models.Model):
    """
    Track order status changes.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=Order.ORDER_STATUS_CHOICES
    )
    
    notes = models.TextField(
        _('notes'),
        blank=True,
        help_text=_('Additional notes about the status change.')
    )
    
    changed_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='order_status_changes'
    )
    
    timestamp = models.DateTimeField(
        _('timestamp'),
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = _('Order Status History')
        verbose_name_plural = _('Order Status Histories')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['order', 'timestamp']),
            models.Index(fields=['status']),
        ]
        
    def __str__(self):
        return f"{self.order.order_number} - {self.get_status_display()} by {self.changed_by.full_name}"


class Reservation(BaseModel):
    """
    Product reservation model for advance orders.
    """
    RESERVATION_STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('accepted', _('Accepted')),
        ('rejected', _('Rejected')),
        ('counter_offered', _('Counter Offered')),
        ('expired', _('Expired')),
        ('completed', _('Completed')),
    ]

    buyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reservations_as_buyer',
        limit_choices_to={'user_type': 'Buyer'},
        help_text=_('Buyer making the reservation.')
    )

    farmer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reservations_as_farmer',
        limit_choices_to={'user_type': 'Farmer'},
        help_text=_('Farmer receiving the reservation request.')
    )

    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='reservations',
        help_text=_('Product being reserved.')
    )

    quantity_requested = models.PositiveIntegerField(
        _('quantity requested'),
        validators=[MinValueValidator(1)],
        help_text=_('Quantity requested by buyer.')
    )

    price_offered = models.DecimalField(
        _('price offered'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text=_('Price offered by buyer per unit.')
    )

    harvest_date_requested = models.DateField(
        _('harvest date requested'),
        null=True,
        blank=True,
        help_text=_('Requested harvest date.')
    )

    pickup_delivery_date = models.DateField(
        _('pickup/delivery date'),
        null=True,
        blank=True,
        help_text=_('Requested pickup or delivery date.')
    )

    status = models.CharField(
        _('status'),
        max_length=20,
        choices=RESERVATION_STATUS_CHOICES,
        default='pending'
    )

    farmer_response = models.TextField(
        _('farmer response'),
        blank=True,
        help_text=_('Farmer\'s response to the reservation request.')
    )

    counter_offer_price = models.DecimalField(
        _('counter offer price'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text=_('Counter offer price from farmer.')
    )

    expires_at = models.DateTimeField(
        _('expires at'),
        help_text=_('When this reservation expires.')
    )

    # Additional fields
    buyer_notes = models.TextField(
        _('buyer notes'),
        blank=True,
        help_text=_('Additional notes from buyer.')
    )

    total_amount = models.DecimalField(
        _('total amount'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Total amount for the reservation.')
    )

    class Meta:
        verbose_name = _('Reservation')
        verbose_name_plural = _('Reservations')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['buyer', 'status']),
            models.Index(fields=['farmer', 'status']),
            models.Index(fields=['product']),
            models.Index(fields=['status', 'expires_at']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"Reservation {self.id} - {self.buyer.full_name} -> {self.farmer.full_name}"

    def save(self, *args, **kwargs):
        # Calculate total amount
        if self.counter_offer_price:
            self.total_amount = self.counter_offer_price * self.quantity_requested
        else:
            self.total_amount = self.price_offered * self.quantity_requested

        # Set expiration if not provided
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)  # Default 7 days

        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Check if reservation is expired."""
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @property
    def can_be_accepted(self):
        """Check if reservation can be accepted."""
        return self.status == 'pending' and not self.is_expired

    @property
    def can_be_rejected(self):
        """Check if reservation can be rejected."""
        return self.status in ['pending', 'counter_offered'] and not self.is_expired

    @property
    def final_price(self):
        """Get the final agreed price."""
        return self.counter_offer_price or self.price_offered


class Cart(models.Model):
    """
    Shopping cart for buyers.
    """
    buyer = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart',
        limit_choices_to={'user_type': 'Buyer'},
        help_text=_('Buyer who owns this cart.')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Shopping Cart')
        verbose_name_plural = _('Shopping Carts')

    def __str__(self):
        return f"Cart - {self.buyer.full_name}"

    @property
    def total_items(self):
        """Get total number of items in cart."""
        return sum(item.quantity for item in self.items.all())

    @property
    def total_amount(self):
        """Calculate total amount of cart."""
        return sum(item.total_price for item in self.items.all())

    @property
    def is_empty(self):
        """Check if cart is empty."""
        return not self.items.exists()

    def clear(self):
        """Clear all items from cart."""
        self.items.all().delete()


class CartItem(models.Model):
    """
    Individual items in shopping cart.
    """
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )

    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='cart_items'
    )

    quantity = models.PositiveIntegerField(
        _('quantity'),
        validators=[MinValueValidator(1)]
    )

    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Cart Item')
        verbose_name_plural = _('Cart Items')
        unique_together = ['cart', 'product']
        indexes = [
            models.Index(fields=['cart']),
            models.Index(fields=['product']),
        ]

    def __str__(self):
        return f"{self.product.product_name} x{self.quantity} - {self.cart.buyer.full_name}"

    @property
    def unit_price(self):
        """Get current unit price of product."""
        return self.product.price

    @property
    def total_price(self):
        """Calculate total price for this cart item."""
        return self.unit_price * self.quantity

    @property
    def is_available(self):
        """Check if product is still available."""
        return (self.product.status == 'Available' and
                self.product.available_quantity >= self.quantity)
