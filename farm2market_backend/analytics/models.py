"""
Analytics and reporting models for Farm2Market.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.core.models import BaseModel
from decimal import Decimal
import json

User = get_user_model()


class UserActivity(models.Model):
    """
    Track user activities across the platform.
    """
    ACTIVITY_TYPE_CHOICES = [
        ('login', _('Login')),
        ('logout', _('Logout')),
        ('view_product', _('View Product')),
        ('add_to_cart', _('Add to Cart')),
        ('remove_from_cart', _('Remove from Cart')),
        ('place_order', _('Place Order')),
        ('cancel_order', _('Cancel Order')),
        ('send_message', _('Send Message')),
        ('search', _('Search')),
        ('create_reservation', _('Create Reservation')),
        ('update_profile', _('Update Profile')),
        ('add_product', _('Add Product')),
        ('update_product', _('Update Product')),
        ('view_farmer', _('View Farmer Profile')),
        ('follow_farmer', _('Follow Farmer')),
        ('unfollow_farmer', _('Unfollow Farmer')),
        ('rate_product', _('Rate Product')),
        ('write_review', _('Write Review')),
    ]
    
    RESOURCE_TYPE_CHOICES = [
        ('product', _('Product')),
        ('order', _('Order')),
        ('message', _('Message')),
        ('user', _('User')),
        ('reservation', _('Reservation')),
        ('cart', _('Cart')),
        ('search', _('Search')),
        ('review', _('Review')),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
        help_text=_('User who performed the activity (null for anonymous).')
    )
    
    activity_type = models.CharField(
        _('activity type'),
        max_length=50,
        choices=ACTIVITY_TYPE_CHOICES
    )
    
    resource_type = models.CharField(
        _('resource type'),
        max_length=50,
        choices=RESOURCE_TYPE_CHOICES
    )
    
    resource_id = models.CharField(
        _('resource ID'),
        max_length=50,
        help_text=_('ID of the resource being acted upon.')
    )
    
    metadata = models.JSONField(
        _('metadata'),
        default=dict,
        blank=True,
        help_text=_('Additional context data.')
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
    
    session_id = models.CharField(
        _('session ID'),
        max_length=100,
        blank=True,
        help_text=_('Session identifier for anonymous tracking.')
    )
    
    timestamp = models.DateTimeField(
        _('timestamp'),
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = _('User Activity')
        verbose_name_plural = _('User Activities')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'activity_type']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['session_id']),
        ]
        
    def __str__(self):
        user_name = self.user.full_name if self.user else 'Anonymous'
        return f"{user_name} - {self.get_activity_type_display()}"


class ProductView(models.Model):
    """
    Track product page views for analytics.
    """
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='views'
    )
    
    viewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='product_views',
        help_text=_('User who viewed the product (null for anonymous).')
    )
    
    ip_address = models.GenericIPAddressField(
        _('IP address'),
        null=True,
        blank=True
    )
    
    referrer = models.URLField(
        _('referrer'),
        blank=True,
        help_text=_('URL that referred to this product page.')
    )
    
    user_agent = models.CharField(
        _('user agent'),
        max_length=500,
        blank=True
    )
    
    session_id = models.CharField(
        _('session ID'),
        max_length=100,
        blank=True
    )
    
    view_duration = models.PositiveIntegerField(
        _('view duration'),
        default=0,
        help_text=_('Time spent viewing the product in seconds.')
    )
    
    timestamp = models.DateTimeField(
        _('timestamp'),
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = _('Product View')
        verbose_name_plural = _('Product Views')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['product', 'timestamp']),
            models.Index(fields=['viewer']),
            models.Index(fields=['session_id']),
        ]
        
    def __str__(self):
        viewer_name = self.viewer.full_name if self.viewer else 'Anonymous'
        return f"{viewer_name} viewed {self.product.product_name}"


class SearchAnalytics(models.Model):
    """
    Track search queries and results for analytics.
    """
    query = models.CharField(
        _('search query'),
        max_length=500
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='searches',
        help_text=_('User who performed the search (null for anonymous).')
    )
    
    results_count = models.PositiveIntegerField(
        _('results count'),
        default=0,
        help_text=_('Number of results returned.')
    )
    
    clicked_result_position = models.PositiveIntegerField(
        _('clicked result position'),
        null=True,
        blank=True,
        help_text=_('Position of the clicked result (1-based).')
    )
    
    clicked_product = models.ForeignKey(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='search_clicks',
        help_text=_('Product that was clicked from search results.')
    )
    
    filters_used = models.JSONField(
        _('filters used'),
        default=dict,
        blank=True,
        help_text=_('Search filters applied.')
    )
    
    sort_order = models.CharField(
        _('sort order'),
        max_length=50,
        blank=True,
        help_text=_('Sort order used for results.')
    )
    
    ip_address = models.GenericIPAddressField(
        _('IP address'),
        null=True,
        blank=True
    )
    
    session_id = models.CharField(
        _('session ID'),
        max_length=100,
        blank=True
    )
    
    timestamp = models.DateTimeField(
        _('timestamp'),
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = _('Search Analytics')
        verbose_name_plural = _('Search Analytics')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['query']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['results_count']),
        ]
        
    def __str__(self):
        user_name = self.user.full_name if self.user else 'Anonymous'
        return f"{user_name} searched for '{self.query}'"


class CartAbandonment(models.Model):
    """
    Track cart abandonment for conversion analysis.
    """
    ABANDONMENT_STAGE_CHOICES = [
        ('cart', _('Cart')),
        ('checkout', _('Checkout')),
        ('payment', _('Payment')),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cart_abandonments'
    )
    
    session_id = models.CharField(
        _('session ID'),
        max_length=100,
        blank=True
    )
    
    cart_value = models.DecimalField(
        _('cart value'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    items_count = models.PositiveIntegerField(
        _('items count'),
        default=0
    )
    
    abandonment_stage = models.CharField(
        _('abandonment stage'),
        max_length=20,
        choices=ABANDONMENT_STAGE_CHOICES,
        default='cart'
    )
    
    last_activity = models.DateTimeField(
        _('last activity'),
        help_text=_('Last activity timestamp before abandonment.')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Cart Abandonment')
        verbose_name_plural = _('Cart Abandonments')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'abandonment_stage']),
            models.Index(fields=['session_id']),
            models.Index(fields=['created_at']),
        ]
        
    def __str__(self):
        user_name = self.user.full_name if self.user else f'Session {self.session_id}'
        return f"{user_name} abandoned cart at {self.get_abandonment_stage_display()}"


class RevenueAnalytics(models.Model):
    """
    Daily revenue analytics aggregated by various dimensions.
    """
    date = models.DateField(_('date'))
    
    farmer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='revenue_analytics',
        limit_choices_to={'user_type': 'Farmer'}
    )
    
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='revenue_analytics'
    )
    
    category = models.ForeignKey(
        'products.ProductCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='revenue_analytics'
    )
    
    revenue = models.DecimalField(
        _('revenue'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    orders_count = models.PositiveIntegerField(
        _('orders count'),
        default=0
    )
    
    units_sold = models.PositiveIntegerField(
        _('units sold'),
        default=0
    )
    
    avg_order_value = models.DecimalField(
        _('average order value'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Revenue Analytics')
        verbose_name_plural = _('Revenue Analytics')
        unique_together = ['date', 'farmer', 'product']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date', 'farmer']),
            models.Index(fields=['date', 'product']),
            models.Index(fields=['date', 'category']),
        ]
        
    def __str__(self):
        if self.product:
            return f"{self.date} - {self.product.product_name}: ${self.revenue}"
        elif self.farmer:
            return f"{self.date} - {self.farmer.full_name}: ${self.revenue}"
        else:
            return f"{self.date} - Platform: ${self.revenue}"


class UserEngagementMetrics(models.Model):
    """
    Daily user engagement metrics.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='engagement_metrics'
    )
    
    date = models.DateField(_('date'))
    
    sessions_count = models.PositiveIntegerField(
        _('sessions count'),
        default=0
    )
    
    page_views = models.PositiveIntegerField(
        _('page views'),
        default=0
    )
    
    time_spent_minutes = models.PositiveIntegerField(
        _('time spent (minutes)'),
        default=0
    )
    
    actions_count = models.PositiveIntegerField(
        _('actions count'),
        default=0
    )
    
    orders_placed = models.PositiveIntegerField(
        _('orders placed'),
        default=0
    )
    
    messages_sent = models.PositiveIntegerField(
        _('messages sent'),
        default=0
    )
    
    products_viewed = models.PositiveIntegerField(
        _('products viewed'),
        default=0
    )
    
    searches_performed = models.PositiveIntegerField(
        _('searches performed'),
        default=0
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('User Engagement Metrics')
        verbose_name_plural = _('User Engagement Metrics')
        unique_together = ['user', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['date']),
        ]
        
    def __str__(self):
        return f"{self.user.full_name} - {self.date}"
    
    @property
    def engagement_score(self):
        """Calculate engagement score based on activities."""
        score = (
            self.page_views * 1 +
            self.time_spent_minutes * 2 +
            self.actions_count * 3 +
            self.orders_placed * 10 +
            self.messages_sent * 5 +
            self.searches_performed * 2
        )
        return min(score, 1000)  # Cap at 1000


class ProductPopularityMetrics(models.Model):
    """
    Daily product popularity metrics.
    """
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='popularity_metrics'
    )

    date = models.DateField(_('date'))

    views_count = models.PositiveIntegerField(
        _('views count'),
        default=0
    )

    unique_viewers = models.PositiveIntegerField(
        _('unique viewers'),
        default=0
    )

    cart_additions = models.PositiveIntegerField(
        _('cart additions'),
        default=0
    )

    orders_count = models.PositiveIntegerField(
        _('orders count'),
        default=0
    )

    revenue = models.DecimalField(
        _('revenue'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    rating_average = models.DecimalField(
        _('average rating'),
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.00')
    )

    reviews_count = models.PositiveIntegerField(
        _('reviews count'),
        default=0
    )

    popularity_score = models.DecimalField(
        _('popularity score'),
        max_digits=8,
        decimal_places=4,
        default=Decimal('0.0000')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Product Popularity Metrics')
        verbose_name_plural = _('Product Popularity Metrics')
        unique_together = ['product', 'date']
        ordering = ['-popularity_score', '-date']
        indexes = [
            models.Index(fields=['product', 'date']),
            models.Index(fields=['date', 'popularity_score']),
        ]

    def __str__(self):
        return f"{self.product.product_name} - {self.date} (Score: {self.popularity_score})"

    def calculate_popularity_score(self):
        """Calculate popularity score based on various metrics."""
        # Weighted scoring algorithm
        view_score = self.views_count * 1
        cart_score = self.cart_additions * 5
        order_score = self.orders_count * 10
        rating_score = float(self.rating_average) * self.reviews_count * 2

        total_score = view_score + cart_score + order_score + rating_score

        # Normalize by unique viewers to account for product reach
        if self.unique_viewers > 0:
            normalized_score = total_score / self.unique_viewers
        else:
            normalized_score = 0

        self.popularity_score = Decimal(str(round(normalized_score, 4)))
        return self.popularity_score


class Report(BaseModel):
    """
    Generated reports for analytics.
    """
    REPORT_TYPE_CHOICES = [
        ('sales', _('Sales Report')),
        ('users', _('Users Report')),
        ('products', _('Products Report')),
        ('orders', _('Orders Report')),
        ('revenue', _('Revenue Report')),
        ('engagement', _('Engagement Report')),
        ('custom', _('Custom Report')),
    ]

    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('generating', _('Generating')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
    ]

    name = models.CharField(
        _('name'),
        max_length=200
    )

    report_type = models.CharField(
        _('report type'),
        max_length=20,
        choices=REPORT_TYPE_CHOICES
    )

    parameters = models.JSONField(
        _('parameters'),
        default=dict,
        blank=True,
        help_text=_('Report generation parameters.')
    )

    generated_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='generated_reports'
    )

    file_path = models.FileField(
        _('file path'),
        upload_to='reports/%Y/%m/',
        blank=True,
        help_text=_('Path to generated report file.')
    )

    status = models.CharField(
        _('status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    start_date = models.DateField(
        _('start date'),
        null=True,
        blank=True
    )

    end_date = models.DateField(
        _('end date'),
        null=True,
        blank=True
    )

    total_records = models.PositiveIntegerField(
        _('total records'),
        default=0
    )

    file_size = models.PositiveBigIntegerField(
        _('file size'),
        default=0,
        help_text=_('File size in bytes.')
    )

    error_message = models.TextField(
        _('error message'),
        blank=True
    )

    completed_at = models.DateTimeField(
        _('completed at'),
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = _('Report')
        verbose_name_plural = _('Reports')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['report_type', 'status']),
            models.Index(fields=['generated_by']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"

    @property
    def is_completed(self):
        return self.status == 'completed'

    @property
    def is_failed(self):
        return self.status == 'failed'

    def mark_completed(self, file_path=None, total_records=0, file_size=0):
        """Mark report as completed."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if file_path:
            self.file_path = file_path
        self.total_records = total_records
        self.file_size = file_size
        self.save()

    def mark_failed(self, error_message):
        """Mark report as failed."""
        self.status = 'failed'
        self.error_message = error_message
        self.save()


class DashboardWidget(models.Model):
    """
    Customizable dashboard widgets for users.
    """
    WIDGET_TYPE_CHOICES = [
        ('chart', _('Chart')),
        ('metric', _('Metric')),
        ('table', _('Table')),
        ('map', _('Map')),
        ('calendar', _('Calendar')),
        ('list', _('List')),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='dashboard_widgets'
    )

    widget_type = models.CharField(
        _('widget type'),
        max_length=20,
        choices=WIDGET_TYPE_CHOICES
    )

    title = models.CharField(
        _('title'),
        max_length=100
    )

    config = models.JSONField(
        _('configuration'),
        default=dict,
        blank=True,
        help_text=_('Widget configuration and data source.')
    )

    position = models.PositiveIntegerField(
        _('position'),
        default=0,
        help_text=_('Widget position in dashboard.')
    )

    width = models.PositiveIntegerField(
        _('width'),
        default=6,
        help_text=_('Widget width (1-12 grid system).')
    )

    height = models.PositiveIntegerField(
        _('height'),
        default=4,
        help_text=_('Widget height in grid units.')
    )

    is_active = models.BooleanField(
        _('is active'),
        default=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Dashboard Widget')
        verbose_name_plural = _('Dashboard Widgets')
        ordering = ['position']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['widget_type']),
        ]

    def __str__(self):
        return f"{self.user.full_name} - {self.title}"


class PriceHistory(models.Model):
    """
    Track product price changes over time.
    """
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='price_history'
    )

    price = models.DecimalField(
        _('price'),
        max_digits=10,
        decimal_places=2
    )

    date = models.DateField(_('date'))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Price History')
        verbose_name_plural = _('Price Histories')
        unique_together = ['product', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['product', 'date']),
        ]

    def __str__(self):
        return f"{self.product.product_name} - {self.date}: ${self.price}"


class GeographicAnalytics(models.Model):
    """
    Geographic distribution analytics.
    """
    region = models.CharField(
        _('region'),
        max_length=100
    )

    city = models.CharField(
        _('city'),
        max_length=100,
        blank=True
    )

    state = models.CharField(
        _('state'),
        max_length=100,
        blank=True
    )

    country = models.CharField(
        _('country'),
        max_length=100,
        default='Cameroon'
    )

    date = models.DateField(_('date'))

    users_count = models.PositiveIntegerField(
        _('users count'),
        default=0
    )

    farmers_count = models.PositiveIntegerField(
        _('farmers count'),
        default=0
    )

    buyers_count = models.PositiveIntegerField(
        _('buyers count'),
        default=0
    )

    orders_count = models.PositiveIntegerField(
        _('orders count'),
        default=0
    )

    revenue = models.DecimalField(
        _('revenue'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Geographic Analytics')
        verbose_name_plural = _('Geographic Analytics')
        unique_together = ['region', 'date']
        ordering = ['-date', 'region']
        indexes = [
            models.Index(fields=['region', 'date']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.region} - {self.date}"
