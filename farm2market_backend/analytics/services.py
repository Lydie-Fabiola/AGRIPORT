"""
Analytics services for data processing and calculations.
"""
from django.db.models import Sum, Count, Avg, Q, F
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from .models import (
    UserActivity, ProductView, SearchAnalytics, CartAbandonment,
    RevenueAnalytics, UserEngagementMetrics, ProductPopularityMetrics,
    PriceHistory, GeographicAnalytics
)

User = get_user_model()


class AnalyticsService:
    """
    Main analytics service for data processing and insights.
    """
    
    def __init__(self):
        pass
    
    def track_user_activity(self, user, activity_type, resource_type, resource_id, 
                          metadata=None, request=None):
        """
        Track user activity.
        """
        activity_data = {
            'user': user,
            'activity_type': activity_type,
            'resource_type': resource_type,
            'resource_id': str(resource_id),
            'metadata': metadata or {},
        }
        
        if request:
            activity_data.update({
                'ip_address': self._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'session_id': request.session.session_key,
            })
        
        return UserActivity.objects.create(**activity_data)
    
    def track_product_view(self, product, viewer=None, request=None):
        """
        Track product page view.
        """
        view_data = {
            'product': product,
            'viewer': viewer,
        }
        
        if request:
            view_data.update({
                'ip_address': self._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'referrer': request.META.get('HTTP_REFERER', ''),
                'session_id': request.session.session_key,
            })
        
        return ProductView.objects.create(**view_data)
    
    def track_search(self, query, user=None, results_count=0, filters_used=None, 
                    sort_order=None, request=None):
        """
        Track search query.
        """
        search_data = {
            'query': query,
            'user': user,
            'results_count': results_count,
            'filters_used': filters_used or {},
            'sort_order': sort_order or '',
        }
        
        if request:
            search_data.update({
                'ip_address': self._get_client_ip(request),
                'session_id': request.session.session_key,
            })
        
        return SearchAnalytics.objects.create(**search_data)
    
    def track_search_click(self, search_id, clicked_product, position):
        """
        Track search result click.
        """
        try:
            search = SearchAnalytics.objects.get(id=search_id)
            search.clicked_product = clicked_product
            search.clicked_result_position = position
            search.save()
            return search
        except SearchAnalytics.DoesNotExist:
            return None
    
    def track_cart_abandonment(self, user=None, session_id=None, cart_value=0, 
                              items_count=0, stage='cart'):
        """
        Track cart abandonment.
        """
        return CartAbandonment.objects.create(
            user=user,
            session_id=session_id,
            cart_value=cart_value,
            items_count=items_count,
            abandonment_stage=stage,
            last_activity=timezone.now()
        )
    
    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SalesAnalyticsService:
    """
    Sales and revenue analytics service.
    """
    
    def get_revenue_summary(self, farmer=None, start_date=None, end_date=None):
        """
        Get revenue summary for a period.
        """
        queryset = RevenueAnalytics.objects.all()
        
        if farmer:
            queryset = queryset.filter(farmer=farmer)
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        summary = queryset.aggregate(
            total_revenue=Sum('revenue'),
            total_orders=Sum('orders_count'),
            total_units=Sum('units_sold'),
            avg_order_value=Avg('avg_order_value')
        )
        
        return {
            'total_revenue': summary['total_revenue'] or Decimal('0.00'),
            'total_orders': summary['total_orders'] or 0,
            'total_units': summary['total_units'] or 0,
            'avg_order_value': summary['avg_order_value'] or Decimal('0.00'),
        }
    
    def get_revenue_trends(self, farmer=None, days=30):
        """
        Get revenue trends over time.
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        queryset = RevenueAnalytics.objects.filter(
            date__range=[start_date, end_date]
        )
        
        if farmer:
            queryset = queryset.filter(farmer=farmer)
        
        trends = queryset.values('date').annotate(
            daily_revenue=Sum('revenue'),
            daily_orders=Sum('orders_count'),
            daily_units=Sum('units_sold')
        ).order_by('date')
        
        return list(trends)
    
    def get_top_products(self, farmer=None, limit=10, start_date=None, end_date=None):
        """
        Get top-selling products.
        """
        queryset = RevenueAnalytics.objects.exclude(product__isnull=True)
        
        if farmer:
            queryset = queryset.filter(farmer=farmer)
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        top_products = queryset.values(
            'product__id',
            'product__product_name'
        ).annotate(
            total_revenue=Sum('revenue'),
            total_orders=Sum('orders_count'),
            total_units=Sum('units_sold')
        ).order_by('-total_revenue')[:limit]
        
        return list(top_products)
    
    def get_conversion_rates(self, farmer=None, start_date=None, end_date=None):
        """
        Calculate conversion rates.
        """
        # Get product views
        view_queryset = ProductView.objects.all()
        
        if farmer:
            view_queryset = view_queryset.filter(product__farmer=farmer)
        
        if start_date:
            view_queryset = view_queryset.filter(timestamp__date__gte=start_date)
        
        if end_date:
            view_queryset = view_queryset.filter(timestamp__date__lte=end_date)
        
        total_views = view_queryset.count()
        unique_viewers = view_queryset.values('viewer').distinct().count()
        
        # Get orders
        from apps.orders.models import Order
        order_queryset = Order.objects.all()
        
        if farmer:
            order_queryset = order_queryset.filter(farmer=farmer)
        
        if start_date:
            order_queryset = order_queryset.filter(created_at__date__gte=start_date)
        
        if end_date:
            order_queryset = order_queryset.filter(created_at__date__lte=end_date)
        
        total_orders = order_queryset.count()
        
        # Calculate conversion rates
        view_to_order_rate = (total_orders / total_views * 100) if total_views > 0 else 0
        visitor_to_buyer_rate = (total_orders / unique_viewers * 100) if unique_viewers > 0 else 0
        
        return {
            'total_views': total_views,
            'unique_viewers': unique_viewers,
            'total_orders': total_orders,
            'view_to_order_rate': round(view_to_order_rate, 2),
            'visitor_to_buyer_rate': round(visitor_to_buyer_rate, 2),
        }


class UserBehaviorAnalyticsService:
    """
    User behavior analytics service.
    """
    
    def get_user_engagement_summary(self, user=None, start_date=None, end_date=None):
        """
        Get user engagement summary.
        """
        queryset = UserEngagementMetrics.objects.all()
        
        if user:
            queryset = queryset.filter(user=user)
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        summary = queryset.aggregate(
            total_sessions=Sum('sessions_count'),
            total_page_views=Sum('page_views'),
            total_time_spent=Sum('time_spent_minutes'),
            total_actions=Sum('actions_count'),
            total_orders=Sum('orders_placed'),
            total_messages=Sum('messages_sent'),
            total_products_viewed=Sum('products_viewed'),
            total_searches=Sum('searches_performed')
        )
        
        # Calculate averages
        days_count = queryset.values('date').distinct().count()
        
        return {
            'total_sessions': summary['total_sessions'] or 0,
            'total_page_views': summary['total_page_views'] or 0,
            'total_time_spent': summary['total_time_spent'] or 0,
            'total_actions': summary['total_actions'] or 0,
            'total_orders': summary['total_orders'] or 0,
            'total_messages': summary['total_messages'] or 0,
            'total_products_viewed': summary['total_products_viewed'] or 0,
            'total_searches': summary['total_searches'] or 0,
            'avg_sessions_per_day': round((summary['total_sessions'] or 0) / max(days_count, 1), 2),
            'avg_time_per_session': round((summary['total_time_spent'] or 0) / max(summary['total_sessions'] or 1, 1), 2),
        }
    
    def get_popular_products(self, limit=10, start_date=None, end_date=None):
        """
        Get most popular products based on views and engagement.
        """
        queryset = ProductPopularityMetrics.objects.all()
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        popular_products = queryset.values(
            'product__id',
            'product__product_name',
            'product__farmer__full_name'
        ).annotate(
            total_views=Sum('views_count'),
            total_unique_viewers=Sum('unique_viewers'),
            total_cart_additions=Sum('cart_additions'),
            total_orders=Sum('orders_count'),
            total_revenue=Sum('revenue'),
            avg_popularity_score=Avg('popularity_score')
        ).order_by('-avg_popularity_score')[:limit]
        
        return list(popular_products)
    
    def get_search_insights(self, limit=20, start_date=None, end_date=None):
        """
        Get search insights and popular queries.
        """
        queryset = SearchAnalytics.objects.all()
        
        if start_date:
            queryset = queryset.filter(timestamp__date__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(timestamp__date__lte=end_date)
        
        # Popular search queries
        popular_queries = queryset.values('query').annotate(
            search_count=Count('id'),
            avg_results=Avg('results_count'),
            click_rate=Count('clicked_product') * 100.0 / Count('id')
        ).order_by('-search_count')[:limit]
        
        # Zero result searches
        zero_result_queries = queryset.filter(
            results_count=0
        ).values('query').annotate(
            search_count=Count('id')
        ).order_by('-search_count')[:10]
        
        return {
            'popular_queries': list(popular_queries),
            'zero_result_queries': list(zero_result_queries),
            'total_searches': queryset.count(),
            'avg_results_per_search': queryset.aggregate(avg=Avg('results_count'))['avg'] or 0,
        }
    
    def get_cart_abandonment_analysis(self, start_date=None, end_date=None):
        """
        Analyze cart abandonment patterns.
        """
        queryset = CartAbandonment.objects.all()
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # Abandonment by stage
        by_stage = queryset.values('abandonment_stage').annotate(
            count=Count('id'),
            avg_cart_value=Avg('cart_value'),
            avg_items_count=Avg('items_count')
        ).order_by('abandonment_stage')
        
        # Overall statistics
        total_abandonments = queryset.count()
        total_abandoned_value = queryset.aggregate(total=Sum('cart_value'))['total'] or Decimal('0.00')
        avg_abandoned_value = queryset.aggregate(avg=Avg('cart_value'))['avg'] or Decimal('0.00')
        
        return {
            'total_abandonments': total_abandonments,
            'total_abandoned_value': total_abandoned_value,
            'avg_abandoned_value': avg_abandoned_value,
            'by_stage': list(by_stage),
        }
