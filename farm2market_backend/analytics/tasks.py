"""
Celery tasks for analytics processing.
"""
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Sum, Count, Avg, F
from datetime import datetime, timedelta, date
from decimal import Decimal
import csv
import os
from .models import (
    UserActivity, ProductView, SearchAnalytics, CartAbandonment,
    RevenueAnalytics, UserEngagementMetrics, ProductPopularityMetrics,
    Report, PriceHistory, GeographicAnalytics
)

User = get_user_model()


@shared_task
def process_daily_analytics():
    """
    Process daily analytics aggregations.
    """
    yesterday = timezone.now().date() - timedelta(days=1)
    
    # Process revenue analytics
    process_daily_revenue_analytics.delay(yesterday.isoformat())
    
    # Process user engagement metrics
    process_daily_user_engagement.delay(yesterday.isoformat())
    
    # Process product popularity metrics
    process_daily_product_popularity.delay(yesterday.isoformat())
    
    # Process geographic analytics
    process_daily_geographic_analytics.delay(yesterday.isoformat())
    
    return f"Started daily analytics processing for {yesterday}"


@shared_task
def process_daily_revenue_analytics(date_str):
    """
    Process daily revenue analytics.
    """
    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    from apps.orders.models import Order, OrderItem
    
    # Get orders for the target date
    orders = Order.objects.filter(
        created_at__date=target_date,
        status__in=['delivered', 'completed']
    )
    
    processed_count = 0
    
    # Aggregate by farmer
    farmer_data = orders.values('farmer').annotate(
        revenue=Sum('total_amount'),
        orders_count=Count('id'),
        avg_order_value=Avg('total_amount')
    )
    
    for data in farmer_data:
        farmer = User.objects.get(id=data['farmer'])
        
        # Get units sold for this farmer
        units_sold = OrderItem.objects.filter(
            order__farmer=farmer,
            order__created_at__date=target_date,
            order__status__in=['delivered', 'completed']
        ).aggregate(total_units=Sum('quantity'))['total_units'] or 0
        
        RevenueAnalytics.objects.update_or_create(
            date=target_date,
            farmer=farmer,
            product=None,
            category=None,
            defaults={
                'revenue': data['revenue'] or Decimal('0.00'),
                'orders_count': data['orders_count'],
                'units_sold': units_sold,
                'avg_order_value': data['avg_order_value'] or Decimal('0.00'),
            }
        )
        processed_count += 1
    
    # Aggregate by product
    order_items = OrderItem.objects.filter(
        order__created_at__date=target_date,
        order__status__in=['delivered', 'completed']
    )
    
    product_data = order_items.values('product').annotate(
        revenue=Sum('total_price'),
        orders_count=Count('order', distinct=True),
        units_sold=Sum('quantity')
    )
    
    for data in product_data:
        from apps.products.models import Product
        
        try:
            product = Product.objects.get(id=data['product'])
            
            avg_order_value = data['revenue'] / data['orders_count'] if data['orders_count'] > 0 else Decimal('0.00')
            
            RevenueAnalytics.objects.update_or_create(
                date=target_date,
                farmer=product.farmer,
                product=product,
                category=product.categories.first(),
                defaults={
                    'revenue': data['revenue'] or Decimal('0.00'),
                    'orders_count': data['orders_count'],
                    'units_sold': data['units_sold'],
                    'avg_order_value': avg_order_value,
                }
            )
            processed_count += 1
            
        except Product.DoesNotExist:
            continue
    
    return f"Processed {processed_count} revenue analytics records for {target_date}"


@shared_task
def process_daily_user_engagement(date_str):
    """
    Process daily user engagement metrics.
    """
    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    # Get all users who were active on the target date
    active_users = UserActivity.objects.filter(
        timestamp__date=target_date
    ).values('user').distinct()
    
    processed_count = 0
    
    for user_data in active_users:
        if not user_data['user']:
            continue
            
        user = User.objects.get(id=user_data['user'])
        
        # Calculate engagement metrics for this user
        user_activities = UserActivity.objects.filter(
            user=user,
            timestamp__date=target_date
        )
        
        # Count different types of activities
        sessions_count = user_activities.values('session_id').distinct().count()
        actions_count = user_activities.count()
        
        # Count specific activities
        orders_placed = user_activities.filter(activity_type='place_order').count()
        messages_sent = user_activities.filter(activity_type='send_message').count()
        products_viewed = user_activities.filter(activity_type='view_product').count()
        searches_performed = user_activities.filter(activity_type='search').count()
        
        # Get product views for page view count
        page_views = ProductView.objects.filter(
            viewer=user,
            timestamp__date=target_date
        ).count()
        
        # Calculate time spent (simplified - would need more sophisticated tracking)
        time_spent_minutes = sessions_count * 15  # Estimate 15 minutes per session
        
        UserEngagementMetrics.objects.update_or_create(
            user=user,
            date=target_date,
            defaults={
                'sessions_count': sessions_count,
                'page_views': page_views,
                'time_spent_minutes': time_spent_minutes,
                'actions_count': actions_count,
                'orders_placed': orders_placed,
                'messages_sent': messages_sent,
                'products_viewed': products_viewed,
                'searches_performed': searches_performed,
            }
        )
        processed_count += 1
    
    return f"Processed {processed_count} user engagement records for {target_date}"


@shared_task
def process_daily_product_popularity(date_str):
    """
    Process daily product popularity metrics.
    """
    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    # Get all products that had activity on the target date
    active_products = ProductView.objects.filter(
        timestamp__date=target_date
    ).values('product').distinct()
    
    processed_count = 0
    
    for product_data in active_products:
        from apps.products.models import Product
        
        try:
            product = Product.objects.get(id=product_data['product'])
        except Product.DoesNotExist:
            continue
        
        # Calculate popularity metrics
        views = ProductView.objects.filter(
            product=product,
            timestamp__date=target_date
        )
        
        views_count = views.count()
        unique_viewers = views.values('viewer').distinct().count()
        
        # Cart additions (from user activities)
        cart_additions = UserActivity.objects.filter(
            activity_type='add_to_cart',
            resource_type='product',
            resource_id=str(product.id),
            timestamp__date=target_date
        ).count()
        
        # Orders count
        from apps.orders.models import OrderItem
        
        orders_data = OrderItem.objects.filter(
            product=product,
            order__created_at__date=target_date
        ).aggregate(
            orders_count=Count('order', distinct=True),
            revenue=Sum('total_price')
        )
        
        orders_count = orders_data['orders_count'] or 0
        revenue = orders_data['revenue'] or Decimal('0.00')
        
        # Get rating data (if reviews exist)
        rating_average = Decimal('0.00')
        reviews_count = 0
        
        # Calculate popularity score
        popularity_metrics = ProductPopularityMetrics(
            product=product,
            date=target_date,
            views_count=views_count,
            unique_viewers=unique_viewers,
            cart_additions=cart_additions,
            orders_count=orders_count,
            revenue=revenue,
            rating_average=rating_average,
            reviews_count=reviews_count
        )
        
        popularity_score = popularity_metrics.calculate_popularity_score()
        
        ProductPopularityMetrics.objects.update_or_create(
            product=product,
            date=target_date,
            defaults={
                'views_count': views_count,
                'unique_viewers': unique_viewers,
                'cart_additions': cart_additions,
                'orders_count': orders_count,
                'revenue': revenue,
                'rating_average': rating_average,
                'reviews_count': reviews_count,
                'popularity_score': popularity_score,
            }
        )
        processed_count += 1
    
    return f"Processed {processed_count} product popularity records for {target_date}"


@shared_task
def process_daily_geographic_analytics(date_str):
    """
    Process daily geographic analytics.
    """
    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    # This would require IP geolocation data
    # For now, we'll use user profile location data
    
    from apps.farmers.models import FarmerProfile
    from apps.buyers.models import BuyerPreferences
    from apps.orders.models import Order
    
    # Get regions from farmer profiles
    farmer_regions = FarmerProfile.objects.filter(
        user__date_joined__date=target_date
    ).values('location').annotate(
        farmers_count=Count('id')
    )
    
    # Get regions from buyer preferences
    buyer_regions = BuyerPreferences.objects.filter(
        user__date_joined__date=target_date
    ).values('preferred_location').annotate(
        buyers_count=Count('id')
    )
    
    # Get order data by region
    order_regions = Order.objects.filter(
        created_at__date=target_date
    ).values('delivery_address__region').annotate(
        orders_count=Count('id'),
        revenue=Sum('total_amount')
    )
    
    processed_count = 0
    
    # Process farmer regions
    for region_data in farmer_regions:
        if region_data['location']:
            GeographicAnalytics.objects.update_or_create(
                region=region_data['location'],
                date=target_date,
                defaults={
                    'farmers_count': region_data['farmers_count'],
                }
            )
            processed_count += 1
    
    # Process buyer regions
    for region_data in buyer_regions:
        if region_data['preferred_location']:
            analytics, created = GeographicAnalytics.objects.get_or_create(
                region=region_data['preferred_location'],
                date=target_date,
                defaults={'buyers_count': region_data['buyers_count']}
            )
            if not created:
                analytics.buyers_count += region_data['buyers_count']
                analytics.save()
            processed_count += 1
    
    # Process order regions
    for region_data in order_regions:
        if region_data['delivery_address__region']:
            analytics, created = GeographicAnalytics.objects.get_or_create(
                region=region_data['delivery_address__region'],
                date=target_date,
                defaults={
                    'orders_count': region_data['orders_count'],
                    'revenue': region_data['revenue'] or Decimal('0.00')
                }
            )
            if not created:
                analytics.orders_count += region_data['orders_count']
                analytics.revenue += region_data['revenue'] or Decimal('0.00')
                analytics.save()
            processed_count += 1
    
    return f"Processed {processed_count} geographic analytics records for {target_date}"


@shared_task
def update_price_history():
    """
    Update daily price history for all products.
    """
    from apps.products.models import Product
    
    today = timezone.now().date()
    products = Product.objects.filter(status='Available')
    
    updated_count = 0
    
    for product in products:
        PriceHistory.objects.update_or_create(
            product=product,
            date=today,
            defaults={'price': product.price}
        )
        updated_count += 1
    
    return f"Updated price history for {updated_count} products"


@shared_task
def generate_report(report_id):
    """
    Generate analytics report.
    """
    try:
        report = Report.objects.get(id=report_id)
        report.status = 'generating'
        report.save()
        
        # Generate report based on type
        if report.report_type == 'sales':
            file_path = generate_sales_report(report)
        elif report.report_type == 'users':
            file_path = generate_users_report(report)
        elif report.report_type == 'products':
            file_path = generate_products_report(report)
        elif report.report_type == 'orders':
            file_path = generate_orders_report(report)
        elif report.report_type == 'revenue':
            file_path = generate_revenue_report(report)
        elif report.report_type == 'engagement':
            file_path = generate_engagement_report(report)
        else:
            raise ValueError(f"Unknown report type: {report.report_type}")
        
        # Get file size
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        
        # Mark report as completed
        report.mark_completed(file_path, 0, file_size)
        
        return f"Generated report {report.name} successfully"
        
    except Report.DoesNotExist:
        return f"Report {report_id} not found"
    except Exception as e:
        report.mark_failed(str(e))
        return f"Failed to generate report {report_id}: {str(e)}"


def generate_sales_report(report):
    """Generate sales report CSV."""
    from django.conf import settings
    import os
    
    # Create reports directory if it doesn't exist
    reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports', str(timezone.now().year), str(timezone.now().month))
    os.makedirs(reports_dir, exist_ok=True)
    
    filename = f"sales_report_{report.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
    file_path = os.path.join(reports_dir, filename)
    
    # Get sales data
    queryset = RevenueAnalytics.objects.all()
    
    if report.start_date:
        queryset = queryset.filter(date__gte=report.start_date)
    
    if report.end_date:
        queryset = queryset.filter(date__lte=report.end_date)
    
    # Generate CSV
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow([
            'Date', 'Farmer', 'Product', 'Category', 'Revenue',
            'Orders Count', 'Units Sold', 'Avg Order Value'
        ])
        
        # Write data
        for record in queryset.select_related('farmer', 'product', 'category'):
            writer.writerow([
                record.date,
                record.farmer.full_name if record.farmer else 'All Farmers',
                record.product.product_name if record.product else 'All Products',
                record.category.name if record.category else 'All Categories',
                record.revenue,
                record.orders_count,
                record.units_sold,
                record.avg_order_value,
            ])
    
    return file_path


def generate_users_report(report):
    """Generate users report CSV."""
    # Similar implementation for users report
    pass


def generate_products_report(report):
    """Generate products report CSV."""
    # Similar implementation for products report
    pass


def generate_orders_report(report):
    """Generate orders report CSV."""
    # Similar implementation for orders report
    pass


def generate_revenue_report(report):
    """Generate revenue report CSV."""
    # Similar implementation for revenue report
    pass


def generate_engagement_report(report):
    """Generate engagement report CSV."""
    # Similar implementation for engagement report
    pass


@shared_task
def cleanup_old_analytics_data():
    """
    Clean up old analytics data to manage database size.
    """
    # Keep data for 2 years
    cutoff_date = timezone.now().date() - timedelta(days=730)
    
    # Clean up user activities older than 1 year
    activity_cutoff = timezone.now().date() - timedelta(days=365)
    deleted_activities = UserActivity.objects.filter(
        timestamp__date__lt=activity_cutoff
    ).delete()[0]
    
    # Clean up product views older than 1 year
    deleted_views = ProductView.objects.filter(
        timestamp__date__lt=activity_cutoff
    ).delete()[0]
    
    # Clean up search analytics older than 1 year
    deleted_searches = SearchAnalytics.objects.filter(
        timestamp__date__lt=activity_cutoff
    ).delete()[0]
    
    # Clean up aggregated analytics older than 2 years
    deleted_revenue = RevenueAnalytics.objects.filter(
        date__lt=cutoff_date
    ).delete()[0]
    
    deleted_engagement = UserEngagementMetrics.objects.filter(
        date__lt=cutoff_date
    ).delete()[0]
    
    deleted_popularity = ProductPopularityMetrics.objects.filter(
        date__lt=cutoff_date
    ).delete()[0]
    
    return f"Cleaned up analytics data: {deleted_activities} activities, {deleted_views} views, {deleted_searches} searches, {deleted_revenue} revenue records, {deleted_engagement} engagement records, {deleted_popularity} popularity records"
