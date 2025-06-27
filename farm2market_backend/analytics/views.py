"""
Views for analytics system.
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from apps.core.responses import StandardResponse
from apps.core.exceptions import ValidationError, NotFoundError
from apps.users.permissions import IsFarmer, IsBuyer, IsAdmin
from .models import (
    UserActivity, ProductView, SearchAnalytics, Report, DashboardWidget
)
from .serializers import (
    UserActivitySerializer, ProductViewSerializer, SearchAnalyticsSerializer,
    ReportSerializer, ReportCreateSerializer, DashboardWidgetSerializer,
    DashboardWidgetCreateSerializer, SalesSummarySerializer,
    RevenueTrendSerializer, TopProductSerializer, ConversionRatesSerializer,
    EngagementSummarySerializer, PopularProductSerializer,
    SearchInsightsSerializer, CartAbandonmentAnalysisSerializer,
    AnalyticsOverviewSerializer
)
from .services import (
    AnalyticsService, SalesAnalyticsService, UserBehaviorAnalyticsService
)

User = get_user_model()


class FarmerAnalyticsView(APIView):
    """
    Analytics endpoints for farmers.
    """
    permission_classes = [permissions.IsAuthenticated, IsFarmer]
    
    def __init__(self):
        super().__init__()
        self.sales_service = SalesAnalyticsService()
        self.behavior_service = UserBehaviorAnalyticsService()
    
    @action(detail=False, methods=['get'])
    def sales(self, request):
        """Get farmer sales analytics."""
        farmer = request.user
        
        # Get date range from query params
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Get sales summary
        sales_summary = self.sales_service.get_revenue_summary(
            farmer=farmer,
            start_date=start_date,
            end_date=end_date
        )
        
        # Get revenue trends
        revenue_trends = self.sales_service.get_revenue_trends(
            farmer=farmer,
            days=30
        )
        
        # Get top products
        top_products = self.sales_service.get_top_products(
            farmer=farmer,
            limit=10,
            start_date=start_date,
            end_date=end_date
        )
        
        # Get conversion rates
        conversion_rates = self.sales_service.get_conversion_rates(
            farmer=farmer,
            start_date=start_date,
            end_date=end_date
        )
        
        data = {
            'sales_summary': sales_summary,
            'revenue_trends': revenue_trends,
            'top_products': top_products,
            'conversion_rates': conversion_rates,
        }
        
        return StandardResponse.success(
            data=data,
            message='Farmer sales analytics retrieved successfully.'
        )
    
    @action(detail=False, methods=['get'])
    def products(self, request):
        """Get farmer product analytics."""
        farmer = request.user
        
        # Get product performance metrics
        from .models import ProductPopularityMetrics
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        queryset = ProductPopularityMetrics.objects.filter(
            product__farmer=farmer
        )
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            queryset = queryset.filter(date__gte=start_date)
        
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            queryset = queryset.filter(date__lte=end_date)
        
        # Aggregate product metrics
        product_metrics = queryset.values(
            'product__id',
            'product__product_name'
        ).annotate(
            total_views=Sum('views_count'),
            total_unique_viewers=Sum('unique_viewers'),
            total_cart_additions=Sum('cart_additions'),
            total_orders=Sum('orders_count'),
            total_revenue=Sum('revenue'),
            avg_popularity_score=Avg('popularity_score')
        ).order_by('-avg_popularity_score')
        
        return StandardResponse.success(
            data=list(product_metrics),
            message='Farmer product analytics retrieved successfully.'
        )
    
    @action(detail=False, methods=['get'])
    def customers(self, request):
        """Get farmer customer analytics."""
        farmer = request.user
        
        # Get customer insights from orders
        from apps.orders.models import Order
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        orders_queryset = Order.objects.filter(farmer=farmer)
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            orders_queryset = orders_queryset.filter(created_at__date__gte=start_date)
        
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            orders_queryset = orders_queryset.filter(created_at__date__lte=end_date)
        
        # Customer metrics
        total_customers = orders_queryset.values('buyer').distinct().count()
        repeat_customers = orders_queryset.values('buyer').annotate(
            order_count=Count('id')
        ).filter(order_count__gt=1).count()
        
        # Top customers by revenue
        top_customers = orders_queryset.values(
            'buyer__id',
            'buyer__full_name'
        ).annotate(
            total_orders=Count('id'),
            total_spent=Sum('total_amount')
        ).order_by('-total_spent')[:10]
        
        # Customer acquisition over time
        customer_acquisition = orders_queryset.extra(
            select={'month': "DATE_FORMAT(created_at, '%%Y-%%m')"}
        ).values('month').annotate(
            new_customers=Count('buyer', distinct=True)
        ).order_by('month')
        
        data = {
            'total_customers': total_customers,
            'repeat_customers': repeat_customers,
            'repeat_customer_rate': round((repeat_customers / max(total_customers, 1)) * 100, 2),
            'top_customers': list(top_customers),
            'customer_acquisition': list(customer_acquisition),
        }
        
        return StandardResponse.success(
            data=data,
            message='Farmer customer analytics retrieved successfully.'
        )
    
    @action(detail=False, methods=['get'])
    def performance(self, request):
        """Get farmer performance analytics."""
        farmer = request.user
        
        # Get overall performance metrics
        from .models import RevenueAnalytics
        
        # Last 30 days performance
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        current_period = RevenueAnalytics.objects.filter(
            farmer=farmer,
            date__range=[start_date, end_date]
        ).aggregate(
            revenue=Sum('revenue'),
            orders=Sum('orders_count'),
            units=Sum('units_sold')
        )
        
        # Previous 30 days for comparison
        prev_end_date = start_date - timedelta(days=1)
        prev_start_date = prev_end_date - timedelta(days=30)
        
        previous_period = RevenueAnalytics.objects.filter(
            farmer=farmer,
            date__range=[prev_start_date, prev_end_date]
        ).aggregate(
            revenue=Sum('revenue'),
            orders=Sum('orders_count'),
            units=Sum('units_sold')
        )
        
        # Calculate growth rates
        def calculate_growth(current, previous):
            if previous and previous > 0:
                return round(((current or 0) - previous) / previous * 100, 2)
            return 0
        
        revenue_growth = calculate_growth(
            current_period['revenue'], previous_period['revenue']
        )
        orders_growth = calculate_growth(
            current_period['orders'], previous_period['orders']
        )
        units_growth = calculate_growth(
            current_period['units'], previous_period['units']
        )
        
        # Product performance
        product_performance = ProductView.objects.filter(
            product__farmer=farmer,
            timestamp__date__range=[start_date, end_date]
        ).values(
            'product__id',
            'product__product_name'
        ).annotate(
            views=Count('id'),
            unique_viewers=Count('viewer', distinct=True)
        ).order_by('-views')[:5]
        
        data = {
            'current_period': {
                'revenue': current_period['revenue'] or 0,
                'orders': current_period['orders'] or 0,
                'units': current_period['units'] or 0,
            },
            'growth_rates': {
                'revenue_growth': revenue_growth,
                'orders_growth': orders_growth,
                'units_growth': units_growth,
            },
            'top_viewed_products': list(product_performance),
        }
        
        return StandardResponse.success(
            data=data,
            message='Farmer performance analytics retrieved successfully.'
        )


class BuyerAnalyticsView(APIView):
    """
    Analytics endpoints for buyers.
    """
    permission_classes = [permissions.IsAuthenticated, IsBuyer]
    
    def __init__(self):
        super().__init__()
        self.behavior_service = UserBehaviorAnalyticsService()
    
    @action(detail=False, methods=['get'])
    def purchases(self, request):
        """Get buyer purchase analytics."""
        buyer = request.user
        
        # Get purchase history
        from apps.orders.models import Order
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        orders_queryset = Order.objects.filter(buyer=buyer)
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            orders_queryset = orders_queryset.filter(created_at__date__gte=start_date)
        
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            orders_queryset = orders_queryset.filter(created_at__date__lte=end_date)
        
        # Purchase summary
        purchase_summary = orders_queryset.aggregate(
            total_orders=Count('id'),
            total_spent=Sum('total_amount'),
            avg_order_value=Avg('total_amount')
        )
        
        # Purchase trends
        purchase_trends = orders_queryset.extra(
            select={'month': "DATE_FORMAT(created_at, '%%Y-%%m')"}
        ).values('month').annotate(
            orders_count=Count('id'),
            total_spent=Sum('total_amount')
        ).order_by('month')
        
        # Favorite farmers
        favorite_farmers = orders_queryset.values(
            'farmer__id',
            'farmer__full_name'
        ).annotate(
            orders_count=Count('id'),
            total_spent=Sum('total_amount')
        ).order_by('-orders_count')[:5]
        
        # Product categories
        from apps.orders.models import OrderItem
        
        category_spending = OrderItem.objects.filter(
            order__buyer=buyer
        ).values(
            'product__categories__name'
        ).annotate(
            total_spent=Sum('total_price'),
            items_count=Count('id')
        ).order_by('-total_spent')[:10]
        
        data = {
            'purchase_summary': purchase_summary,
            'purchase_trends': list(purchase_trends),
            'favorite_farmers': list(favorite_farmers),
            'category_spending': list(category_spending),
        }
        
        return StandardResponse.success(
            data=data,
            message='Buyer purchase analytics retrieved successfully.'
        )
    
    @action(detail=False, methods=['get'])
    def savings(self, request):
        """Get buyer savings analytics."""
        buyer = request.user
        
        # Calculate potential savings from price drops
        from apps.buyers.models import WishlistItem
        
        wishlist_items = WishlistItem.objects.filter(buyer=buyer)
        
        total_potential_savings = 0
        savings_opportunities = []
        
        for item in wishlist_items:
            if item.target_price and item.product.price < item.target_price:
                savings = item.target_price - item.product.price
                total_potential_savings += savings
                
                savings_opportunities.append({
                    'product_id': item.product.id,
                    'product_name': item.product.product_name,
                    'target_price': item.target_price,
                    'current_price': item.product.price,
                    'savings': savings,
                })
        
        # Compare with market average prices
        # This would require market price data
        
        data = {
            'total_potential_savings': total_potential_savings,
            'savings_opportunities': savings_opportunities,
            'wishlist_items_count': wishlist_items.count(),
        }
        
        return StandardResponse.success(
            data=data,
            message='Buyer savings analytics retrieved successfully.'
        )
    
    @action(detail=False, methods=['get'])
    def preferences(self, request):
        """Get buyer preference analytics."""
        buyer = request.user
        
        # Analyze browsing and purchase patterns
        product_views = ProductView.objects.filter(viewer=buyer)
        
        # Most viewed categories
        viewed_categories = product_views.values(
            'product__categories__name'
        ).annotate(
            views_count=Count('id')
        ).order_by('-views_count')[:10]
        
        # Search patterns
        search_patterns = SearchAnalytics.objects.filter(user=buyer).values(
            'query'
        ).annotate(
            search_count=Count('id')
        ).order_by('-search_count')[:10]
        
        # Engagement metrics
        engagement = self.behavior_service.get_user_engagement_summary(
            user=buyer,
            start_date=timezone.now().date() - timedelta(days=30)
        )
        
        data = {
            'viewed_categories': list(viewed_categories),
            'search_patterns': list(search_patterns),
            'engagement_metrics': engagement,
        }
        
        return StandardResponse.success(
            data=data,
            message='Buyer preference analytics retrieved successfully.'
        )


class AdminAnalyticsView(APIView):
    """
    Analytics endpoints for administrators.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def __init__(self):
        super().__init__()
        self.sales_service = SalesAnalyticsService()
        self.behavior_service = UserBehaviorAnalyticsService()

    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Get platform overview analytics."""
        # Get date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        else:
            start_date = timezone.now().date() - timedelta(days=30)

        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = timezone.now().date()

        # Platform metrics
        total_users = User.objects.filter(is_active=True).count()
        total_farmers = User.objects.filter(user_type='Farmer', is_active=True).count()
        total_buyers = User.objects.filter(user_type='Buyer', is_active=True).count()

        # Revenue metrics
        revenue_summary = self.sales_service.get_revenue_summary(
            start_date=start_date,
            end_date=end_date
        )

        # Product metrics
        from apps.products.models import Product
        total_products = Product.objects.filter(status='Available').count()

        # Order metrics
        from apps.orders.models import Order
        total_orders = Order.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).count()

        # Engagement metrics
        engagement_summary = self.behavior_service.get_user_engagement_summary(
            start_date=start_date,
            end_date=end_date
        )

        # Popular products
        popular_products = self.behavior_service.get_popular_products(
            limit=10,
            start_date=start_date,
            end_date=end_date
        )

        data = {
            'platform_metrics': {
                'total_users': total_users,
                'total_farmers': total_farmers,
                'total_buyers': total_buyers,
                'total_products': total_products,
                'total_orders': total_orders,
            },
            'revenue_summary': revenue_summary,
            'engagement_summary': engagement_summary,
            'popular_products': popular_products,
        }

        return StandardResponse.success(
            data=data,
            message='Platform overview analytics retrieved successfully.'
        )

    @action(detail=False, methods=['get'])
    def users(self, request):
        """Get user analytics."""
        # User registration trends
        user_registration = User.objects.extra(
            select={'month': "DATE_FORMAT(date_joined, '%%Y-%%m')"}
        ).values('month', 'user_type').annotate(
            count=Count('id')
        ).order_by('month')

        # User activity metrics
        from .models import UserEngagementMetrics

        active_users_30d = UserEngagementMetrics.objects.filter(
            date__gte=timezone.now().date() - timedelta(days=30)
        ).values('user').distinct().count()

        # Geographic distribution
        from .models import GeographicAnalytics

        geographic_data = GeographicAnalytics.objects.filter(
            date__gte=timezone.now().date() - timedelta(days=30)
        ).values('region').annotate(
            total_users=Sum('users_count'),
            total_farmers=Sum('farmers_count'),
            total_buyers=Sum('buyers_count')
        ).order_by('-total_users')[:10]

        data = {
            'registration_trends': list(user_registration),
            'active_users_30d': active_users_30d,
            'geographic_distribution': list(geographic_data),
        }

        return StandardResponse.success(
            data=data,
            message='User analytics retrieved successfully.'
        )

    @action(detail=False, methods=['get'])
    def transactions(self, request):
        """Get transaction analytics."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        else:
            start_date = timezone.now().date() - timedelta(days=30)

        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = timezone.now().date()

        # Transaction volume and value
        from apps.orders.models import Order

        transactions = Order.objects.filter(
            created_at__date__range=[start_date, end_date]
        )

        transaction_summary = transactions.aggregate(
            total_transactions=Count('id'),
            total_value=Sum('total_amount'),
            avg_transaction_value=Avg('total_amount')
        )

        # Transaction trends
        transaction_trends = transactions.extra(
            select={'date': "DATE(created_at)"}
        ).values('date').annotate(
            transactions_count=Count('id'),
            total_value=Sum('total_amount')
        ).order_by('date')

        # Payment method distribution
        payment_methods = transactions.values('payment_method').annotate(
            count=Count('id'),
            total_value=Sum('total_amount')
        ).order_by('-count')

        # Order status distribution
        order_statuses = transactions.values('status').annotate(
            count=Count('id')
        ).order_by('-count')

        data = {
            'transaction_summary': transaction_summary,
            'transaction_trends': list(transaction_trends),
            'payment_methods': list(payment_methods),
            'order_statuses': list(order_statuses),
        }

        return StandardResponse.success(
            data=data,
            message='Transaction analytics retrieved successfully.'
        )


class ReportViewSet(ModelViewSet):
    """
    Report management viewset.
    """
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Get reports for authenticated user."""
        user = self.request.user

        if user.user_type == 'Admin':
            return Report.objects.all()
        else:
            return Report.objects.filter(generated_by=user)

    def get_serializer_class(self):
        if self.action == 'create':
            return ReportCreateSerializer
        return ReportSerializer

    def create(self, request, *args, **kwargs):
        """Create a new report."""
        serializer = self.get_serializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            report = serializer.save()

            # Queue report generation
            from .tasks import generate_report
            generate_report.delay(report.id)

            response_serializer = ReportSerializer(report)

            return StandardResponse.created(
                data=response_serializer.data,
                message='Report generation started.'
            )

        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Report creation failed.'
        )


class DashboardWidgetViewSet(ModelViewSet):
    """
    Dashboard widget management viewset.
    """
    serializer_class = DashboardWidgetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DashboardWidget.objects.filter(
            user=self.request.user,
            is_active=True
        ).order_by('position')

    def get_serializer_class(self):
        if self.action == 'create':
            return DashboardWidgetCreateSerializer
        return DashboardWidgetSerializer

    def create(self, request, *args, **kwargs):
        """Create a new dashboard widget."""
        serializer = self.get_serializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            widget = serializer.save()
            response_serializer = DashboardWidgetSerializer(widget)

            return StandardResponse.created(
                data=response_serializer.data,
                message='Dashboard widget created successfully.'
            )

        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Widget creation failed.'
        )

    @action(detail=False, methods=['post'])
    def reorder(self, request):
        """Reorder dashboard widgets."""
        widget_orders = request.data.get('widget_orders', [])

        if not isinstance(widget_orders, list):
            return StandardResponse.validation_error(
                errors={'widget_orders': 'Must be a list of widget IDs in order.'},
                message='Invalid widget order data.'
            )

        updated_count = 0

        for position, widget_id in enumerate(widget_orders):
            try:
                widget = DashboardWidget.objects.get(
                    id=widget_id,
                    user=request.user
                )
                widget.position = position
                widget.save(update_fields=['position'])
                updated_count += 1
            except DashboardWidget.DoesNotExist:
                continue

        return StandardResponse.success(
            data={'updated_count': updated_count},
            message='Dashboard widgets reordered successfully.'
        )
