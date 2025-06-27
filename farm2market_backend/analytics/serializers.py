"""
Serializers for analytics system.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    UserActivity, ProductView, SearchAnalytics, CartAbandonment,
    RevenueAnalytics, UserEngagementMetrics, ProductPopularityMetrics,
    Report, DashboardWidget, PriceHistory, GeographicAnalytics
)

User = get_user_model()


class UserActivitySerializer(serializers.ModelSerializer):
    """
    Serializer for user activities.
    """
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)
    resource_type_display = serializers.CharField(source='get_resource_type_display', read_only=True)
    
    class Meta:
        model = UserActivity
        fields = [
            'id', 'user', 'user_name', 'activity_type', 'activity_type_display',
            'resource_type', 'resource_type_display', 'resource_id', 'metadata',
            'ip_address', 'session_id', 'timestamp'
        ]
        read_only_fields = ['timestamp']


class ProductViewSerializer(serializers.ModelSerializer):
    """
    Serializer for product views.
    """
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    viewer_name = serializers.CharField(source='viewer.full_name', read_only=True)
    
    class Meta:
        model = ProductView
        fields = [
            'id', 'product', 'product_name', 'viewer', 'viewer_name',
            'ip_address', 'referrer', 'session_id', 'view_duration', 'timestamp'
        ]
        read_only_fields = ['timestamp']


class SearchAnalyticsSerializer(serializers.ModelSerializer):
    """
    Serializer for search analytics.
    """
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    clicked_product_name = serializers.CharField(source='clicked_product.product_name', read_only=True)
    
    class Meta:
        model = SearchAnalytics
        fields = [
            'id', 'query', 'user', 'user_name', 'results_count',
            'clicked_result_position', 'clicked_product', 'clicked_product_name',
            'filters_used', 'sort_order', 'ip_address', 'session_id', 'timestamp'
        ]
        read_only_fields = ['timestamp']


class CartAbandonmentSerializer(serializers.ModelSerializer):
    """
    Serializer for cart abandonment.
    """
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    abandonment_stage_display = serializers.CharField(source='get_abandonment_stage_display', read_only=True)
    
    class Meta:
        model = CartAbandonment
        fields = [
            'id', 'user', 'user_name', 'session_id', 'cart_value',
            'items_count', 'abandonment_stage', 'abandonment_stage_display',
            'last_activity', 'created_at'
        ]
        read_only_fields = ['created_at']


class RevenueAnalyticsSerializer(serializers.ModelSerializer):
    """
    Serializer for revenue analytics.
    """
    farmer_name = serializers.CharField(source='farmer.full_name', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = RevenueAnalytics
        fields = [
            'id', 'date', 'farmer', 'farmer_name', 'product', 'product_name',
            'category', 'category_name', 'revenue', 'orders_count',
            'units_sold', 'avg_order_value', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class UserEngagementMetricsSerializer(serializers.ModelSerializer):
    """
    Serializer for user engagement metrics.
    """
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    engagement_score = serializers.ReadOnlyField()
    
    class Meta:
        model = UserEngagementMetrics
        fields = [
            'id', 'user', 'user_name', 'date', 'sessions_count',
            'page_views', 'time_spent_minutes', 'actions_count',
            'orders_placed', 'messages_sent', 'products_viewed',
            'searches_performed', 'engagement_score', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ProductPopularityMetricsSerializer(serializers.ModelSerializer):
    """
    Serializer for product popularity metrics.
    """
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    farmer_name = serializers.CharField(source='product.farmer.full_name', read_only=True)
    
    class Meta:
        model = ProductPopularityMetrics
        fields = [
            'id', 'product', 'product_name', 'farmer_name', 'date',
            'views_count', 'unique_viewers', 'cart_additions', 'orders_count',
            'revenue', 'rating_average', 'reviews_count', 'popularity_score',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ReportSerializer(serializers.ModelSerializer):
    """
    Serializer for reports.
    """
    generated_by_name = serializers.CharField(source='generated_by.full_name', read_only=True)
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_completed = serializers.ReadOnlyField()
    is_failed = serializers.ReadOnlyField()
    
    class Meta:
        model = Report
        fields = [
            'id', 'name', 'report_type', 'report_type_display', 'parameters',
            'generated_by', 'generated_by_name', 'file_path', 'status',
            'status_display', 'start_date', 'end_date', 'total_records',
            'file_size', 'error_message', 'is_completed', 'is_failed',
            'created_at', 'completed_at'
        ]
        read_only_fields = [
            'generated_by', 'file_path', 'status', 'total_records',
            'file_size', 'error_message', 'created_at', 'completed_at'
        ]


class ReportCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating reports.
    """
    class Meta:
        model = Report
        fields = [
            'name', 'report_type', 'parameters', 'start_date', 'end_date'
        ]
    
    def create(self, validated_data):
        """Create report with current user as generator."""
        validated_data['generated_by'] = self.context['request'].user
        return super().create(validated_data)


class DashboardWidgetSerializer(serializers.ModelSerializer):
    """
    Serializer for dashboard widgets.
    """
    widget_type_display = serializers.CharField(source='get_widget_type_display', read_only=True)
    
    class Meta:
        model = DashboardWidget
        fields = [
            'id', 'widget_type', 'widget_type_display', 'title', 'config',
            'position', 'width', 'height', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class DashboardWidgetCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating dashboard widgets.
    """
    class Meta:
        model = DashboardWidget
        fields = [
            'widget_type', 'title', 'config', 'position', 'width', 'height'
        ]
    
    def create(self, validated_data):
        """Create widget for current user."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class PriceHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for price history.
    """
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    
    class Meta:
        model = PriceHistory
        fields = [
            'id', 'product', 'product_name', 'price', 'date', 'created_at'
        ]
        read_only_fields = ['created_at']


class GeographicAnalyticsSerializer(serializers.ModelSerializer):
    """
    Serializer for geographic analytics.
    """
    class Meta:
        model = GeographicAnalytics
        fields = [
            'id', 'region', 'city', 'state', 'country', 'date',
            'users_count', 'farmers_count', 'buyers_count', 'orders_count',
            'revenue', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


# Analytics summary serializers

class SalesSummarySerializer(serializers.Serializer):
    """
    Serializer for sales summary data.
    """
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_orders = serializers.IntegerField()
    total_units = serializers.IntegerField()
    avg_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    growth_rate = serializers.FloatField(required=False)
    period_comparison = serializers.DictField(required=False)


class RevenueTrendSerializer(serializers.Serializer):
    """
    Serializer for revenue trend data.
    """
    date = serializers.DateField()
    daily_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    daily_orders = serializers.IntegerField()
    daily_units = serializers.IntegerField()


class TopProductSerializer(serializers.Serializer):
    """
    Serializer for top product data.
    """
    product_id = serializers.IntegerField(source='product__id')
    product_name = serializers.CharField(source='product__product_name')
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_orders = serializers.IntegerField()
    total_units = serializers.IntegerField()


class ConversionRatesSerializer(serializers.Serializer):
    """
    Serializer for conversion rate data.
    """
    total_views = serializers.IntegerField()
    unique_viewers = serializers.IntegerField()
    total_orders = serializers.IntegerField()
    view_to_order_rate = serializers.FloatField()
    visitor_to_buyer_rate = serializers.FloatField()


class EngagementSummarySerializer(serializers.Serializer):
    """
    Serializer for engagement summary data.
    """
    total_sessions = serializers.IntegerField()
    total_page_views = serializers.IntegerField()
    total_time_spent = serializers.IntegerField()
    total_actions = serializers.IntegerField()
    total_orders = serializers.IntegerField()
    total_messages = serializers.IntegerField()
    total_products_viewed = serializers.IntegerField()
    total_searches = serializers.IntegerField()
    avg_sessions_per_day = serializers.FloatField()
    avg_time_per_session = serializers.FloatField()


class PopularProductSerializer(serializers.Serializer):
    """
    Serializer for popular product data.
    """
    product_id = serializers.IntegerField(source='product__id')
    product_name = serializers.CharField(source='product__product_name')
    farmer_name = serializers.CharField(source='product__farmer__full_name')
    total_views = serializers.IntegerField()
    total_unique_viewers = serializers.IntegerField()
    total_cart_additions = serializers.IntegerField()
    total_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    avg_popularity_score = serializers.FloatField()


class SearchInsightsSerializer(serializers.Serializer):
    """
    Serializer for search insights data.
    """
    popular_queries = serializers.ListField()
    zero_result_queries = serializers.ListField()
    total_searches = serializers.IntegerField()
    avg_results_per_search = serializers.FloatField()


class CartAbandonmentAnalysisSerializer(serializers.Serializer):
    """
    Serializer for cart abandonment analysis.
    """
    total_abandonments = serializers.IntegerField()
    total_abandoned_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    avg_abandoned_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    by_stage = serializers.ListField()


class AnalyticsOverviewSerializer(serializers.Serializer):
    """
    Serializer for analytics overview data.
    """
    sales_summary = SalesSummarySerializer()
    engagement_summary = EngagementSummarySerializer()
    conversion_rates = ConversionRatesSerializer()
    top_products = TopProductSerializer(many=True)
    popular_searches = serializers.ListField()
    recent_activities = UserActivitySerializer(many=True)
