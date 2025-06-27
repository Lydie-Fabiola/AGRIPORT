"""
Product models for Farm2Market.
Based on the farm2market.sql schema.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import BaseModel, StatusChoices
from decimal import Decimal

User = get_user_model()


class Category(models.Model):
    """
    Product categories based on categories table from SQL schema.
    """
    name = models.CharField(
        _('category name'),
        max_length=100,
        unique=True,
        help_text=_('Name of the product category.')
    )
    
    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Description of the category.')
    )
    
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories',
        help_text=_('Parent category for hierarchical structure.')
    )
    
    image = models.ImageField(
        _('category image'),
        upload_to='categories/',
        blank=True,
        null=True
    )
    
    is_active = models.BooleanField(
        _('is active'),
        default=True
    )
    
    display_order = models.PositiveIntegerField(
        _('display order'),
        default=0
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
        ordering = ['display_order', 'name']
        
    def __str__(self):
        return self.name
    
    @property
    def full_name(self):
        """Get full category name including parent."""
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class Product(BaseModel):
    """
    Product model based on farmer_listings table from SQL schema.
    """
    PRODUCT_STATUS_CHOICES = [
        ('Available', _('Available')),
        ('Sold', _('Sold')),
        ('Reserved', _('Reserved')),
        ('Draft', _('Draft')),
        ('Inactive', _('Inactive')),
    ]
    
    UNIT_CHOICES = [
        ('kg', _('Kilogram')),
        ('g', _('Gram')),
        ('lb', _('Pound')),
        ('piece', _('Piece')),
        ('dozen', _('Dozen')),
        ('bag', _('Bag')),
        ('box', _('Box')),
        ('crate', _('Crate')),
        ('liter', _('Liter')),
        ('ml', _('Milliliter')),
    ]
    
    # Based on farmer_listings table
    farmer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='products',
        limit_choices_to={'user_type': 'Farmer'},
        help_text=_('Farmer who owns this product.')
    )
    
    product_name = models.CharField(
        _('product name'),
        max_length=100,
        help_text=_('Name of the product.')
    )
    
    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Detailed description of the product.')
    )
    
    price = models.DecimalField(
        _('price'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text=_('Price per unit in local currency.')
    )
    
    quantity = models.PositiveIntegerField(
        _('quantity available'),
        validators=[MinValueValidator(0)],
        help_text=_('Available quantity in stock.')
    )
    
    unit = models.CharField(
        _('unit of measurement'),
        max_length=20,
        choices=UNIT_CHOICES,
        default='kg',
        help_text=_('Unit of measurement for the product.')
    )
    
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=PRODUCT_STATUS_CHOICES,
        default='Available'
    )
    
    # Additional fields for enhanced product management
    categories = models.ManyToManyField(
        Category,
        through='ProductCategory',
        related_name='products',
        blank=True,
        help_text=_('Categories this product belongs to.')
    )
    
    sku = models.CharField(
        _('SKU'),
        max_length=50,
        unique=True,
        blank=True,
        help_text=_('Stock Keeping Unit - unique product identifier.')
    )
    
    minimum_order_quantity = models.PositiveIntegerField(
        _('minimum order quantity'),
        default=1,
        validators=[MinValueValidator(1)],
        help_text=_('Minimum quantity that can be ordered.')
    )
    
    harvest_date = models.DateField(
        _('harvest date'),
        null=True,
        blank=True,
        help_text=_('Date when the product was harvested.')
    )
    
    expiry_date = models.DateField(
        _('expiry date'),
        null=True,
        blank=True,
        help_text=_('Date when the product expires.')
    )
    
    organic_certified = models.BooleanField(
        _('organic certified'),
        default=False,
        help_text=_('Whether the product is organic certified.')
    )
    
    location = models.ForeignKey(
        'farmers.FarmLocation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        help_text=_('Farm location where this product is grown.')
    )
    
    # SEO and marketing fields
    slug = models.SlugField(
        _('slug'),
        max_length=100,
        unique=True,
        blank=True,
        help_text=_('URL-friendly version of the product name.')
    )
    
    featured = models.BooleanField(
        _('featured'),
        default=False,
        help_text=_('Whether this product is featured.')
    )
    
    views_count = models.PositiveIntegerField(
        _('views count'),
        default=0,
        help_text=_('Number of times this product has been viewed.')
    )
    
    # Inventory tracking
    reserved_quantity = models.PositiveIntegerField(
        _('reserved quantity'),
        default=0,
        help_text=_('Quantity currently reserved in pending orders.')
    )
    
    sold_quantity = models.PositiveIntegerField(
        _('sold quantity'),
        default=0,
        help_text=_('Total quantity sold.')
    )
    
    class Meta:
        verbose_name = _('Product')
        verbose_name_plural = _('Products')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['farmer', 'status']),
            models.Index(fields=['status', 'featured']),
            models.Index(fields=['created_at']),
        ]
        
    def __str__(self):
        return f"{self.product_name} - {self.farmer.full_name}"
    
    @property
    def available_quantity(self):
        """Calculate available quantity (total - reserved)."""
        return max(0, self.quantity - self.reserved_quantity)
    
    @property
    def is_in_stock(self):
        """Check if product is in stock."""
        return self.available_quantity > 0
    
    @property
    def is_low_stock(self):
        """Check if product is low in stock (less than 10% of original quantity)."""
        if self.quantity + self.sold_quantity == 0:
            return False
        original_quantity = self.quantity + self.sold_quantity
        return self.available_quantity < (original_quantity * 0.1)
    
    def save(self, *args, **kwargs):
        # Auto-generate SKU if not provided
        if not self.sku:
            import uuid
            self.sku = f"PRD-{uuid.uuid4().hex[:8].upper()}"
        
        # Auto-generate slug if not provided
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(f"{self.product_name}-{self.farmer.username}")
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(id=self.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        super().save(*args, **kwargs)


class ProductCategory(models.Model):
    """
    Through model for Product-Category relationship.
    Based on product_categories table from SQL schema.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='product_categories'
    )
    
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='product_categories'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Product Category')
        verbose_name_plural = _('Product Categories')
        unique_together = ['product', 'category']
        
    def __str__(self):
        return f"{self.product.product_name} - {self.category.name}"


class ProductImage(BaseModel):
    """
    Model for product images.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    
    image = models.ImageField(
        _('product image'),
        upload_to='products/',
        help_text=_('Product image file.')
    )
    
    alt_text = models.CharField(
        _('alt text'),
        max_length=200,
        blank=True,
        help_text=_('Alternative text for the image.')
    )
    
    is_primary = models.BooleanField(
        _('is primary'),
        default=False,
        help_text=_('Set as primary product image.')
    )
    
    display_order = models.PositiveIntegerField(
        _('display order'),
        default=0
    )
    
    class Meta:
        verbose_name = _('Product Image')
        verbose_name_plural = _('Product Images')
        ordering = ['display_order', '-created_at']
        
    def __str__(self):
        return f"{self.product.product_name} - Image {self.id}"
    
    def save(self, *args, **kwargs):
        # Ensure only one primary image per product
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product,
                is_primary=True
            ).exclude(id=self.id).update(is_primary=False)
        super().save(*args, **kwargs)


class StockMovement(BaseModel):
    """
    Model for tracking stock movements and inventory changes.
    """
    MOVEMENT_TYPES = [
        ('IN', _('Stock In')),
        ('OUT', _('Stock Out')),
        ('ADJUSTMENT', _('Stock Adjustment')),
        ('RESERVED', _('Reserved')),
        ('UNRESERVED', _('Unreserved')),
        ('SOLD', _('Sold')),
        ('EXPIRED', _('Expired')),
        ('DAMAGED', _('Damaged')),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='stock_movements'
    )

    movement_type = models.CharField(
        _('movement type'),
        max_length=20,
        choices=MOVEMENT_TYPES
    )

    quantity = models.IntegerField(
        _('quantity'),
        help_text=_('Quantity moved (positive for IN, negative for OUT).')
    )

    reference_order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements',
        help_text=_('Related order if applicable.')
    )

    notes = models.TextField(
        _('notes'),
        blank=True,
        help_text=_('Additional notes about the stock movement.')
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='stock_movements_created'
    )

    # Stock levels after this movement
    stock_after = models.PositiveIntegerField(
        _('stock after movement'),
        help_text=_('Stock level after this movement.')
    )

    class Meta:
        verbose_name = _('Stock Movement')
        verbose_name_plural = _('Stock Movements')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'movement_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.product.product_name} - {self.get_movement_type_display()} ({self.quantity})"


class LowStockAlert(BaseModel):
    """
    Model for low stock alerts.
    """
    ALERT_STATUS_CHOICES = [
        ('active', _('Active')),
        ('acknowledged', _('Acknowledged')),
        ('resolved', _('Resolved')),
        ('dismissed', _('Dismissed')),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='low_stock_alerts'
    )

    threshold_quantity = models.PositiveIntegerField(
        _('threshold quantity'),
        help_text=_('Quantity threshold that triggered this alert.')
    )

    current_quantity = models.PositiveIntegerField(
        _('current quantity'),
        help_text=_('Current stock quantity when alert was created.')
    )

    status = models.CharField(
        _('alert status'),
        max_length=20,
        choices=ALERT_STATUS_CHOICES,
        default='active'
    )

    acknowledged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts'
    )

    acknowledged_at = models.DateTimeField(
        _('acknowledged at'),
        null=True,
        blank=True
    )

    resolved_at = models.DateTimeField(
        _('resolved at'),
        null=True,
        blank=True
    )

    notes = models.TextField(
        _('notes'),
        blank=True
    )

    class Meta:
        verbose_name = _('Low Stock Alert')
        verbose_name_plural = _('Low Stock Alerts')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"Low Stock Alert: {self.product.product_name} ({self.current_quantity} remaining)"

    def acknowledge(self, user):
        """Acknowledge the alert."""
        from django.utils import timezone
        self.status = 'acknowledged'
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save(update_fields=['status', 'acknowledged_by', 'acknowledged_at'])

    def resolve(self):
        """Mark alert as resolved."""
        from django.utils import timezone
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        self.save(update_fields=['status', 'resolved_at'])


class InventorySettings(models.Model):
    """
    Model for inventory management settings per farmer.
    """
    farmer = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='inventory_settings',
        limit_choices_to={'user_type': 'Farmer'}
    )

    low_stock_threshold_percentage = models.PositiveIntegerField(
        _('low stock threshold percentage'),
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text=_('Percentage of original stock to trigger low stock alert.')
    )

    auto_low_stock_alerts = models.BooleanField(
        _('auto low stock alerts'),
        default=True,
        help_text=_('Automatically create low stock alerts.')
    )

    email_notifications = models.BooleanField(
        _('email notifications'),
        default=True,
        help_text=_('Send email notifications for inventory alerts.')
    )

    sms_notifications = models.BooleanField(
        _('SMS notifications'),
        default=False,
        help_text=_('Send SMS notifications for inventory alerts.')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Inventory Settings')
        verbose_name_plural = _('Inventory Settings')

    def __str__(self):
        return f"Inventory Settings - {self.farmer.full_name}"


class ProductReview(BaseModel):
    """
    Model for product reviews and ratings.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews'
    )

    buyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='product_reviews',
        limit_choices_to={'user_type': 'Buyer'}
    )

    rating = models.PositiveIntegerField(
        _('rating'),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_('Rating from 1 to 5 stars.')
    )

    review_text = models.TextField(
        _('review text'),
        blank=True,
        help_text=_('Written review of the product.')
    )

    is_verified_purchase = models.BooleanField(
        _('is verified purchase'),
        default=False,
        help_text=_('Whether this review is from a verified purchase.')
    )

    is_approved = models.BooleanField(
        _('is approved'),
        default=True,
        help_text=_('Whether this review is approved for display.')
    )

    helpful_count = models.PositiveIntegerField(
        _('helpful count'),
        default=0,
        help_text=_('Number of users who found this review helpful.')
    )

    class Meta:
        verbose_name = _('Product Review')
        verbose_name_plural = _('Product Reviews')
        unique_together = ['buyer', 'product']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'is_approved']),
            models.Index(fields=['buyer']),
            models.Index(fields=['rating']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.buyer.full_name} - {self.product.product_name} ({self.rating}★)"
