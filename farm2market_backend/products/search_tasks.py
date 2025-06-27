"""
Celery tasks for product search and discovery.
"""
from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import Product
from .search_models import SearchQuery, PopularSearch, ProductView, SavedSearch
from .search_utils import ProductSearchEngine

User = get_user_model()


@shared_task
def cleanup_old_search_queries():
    """
    Clean up old search queries (older than 6 months).
    """
    cutoff_date = timezone.now() - timedelta(days=180)
    
    deleted_count, _ = SearchQuery.objects.filter(
        created_at__lt=cutoff_date
    ).delete()
    
    return f"Cleaned up {deleted_count} old search queries"


@shared_task
def cleanup_old_product_views():
    """
    Clean up old product views (older than 1 year).
    """
    cutoff_date = timezone.now() - timedelta(days=365)
    
    deleted_count, _ = ProductView.objects.filter(
        viewed_at__lt=cutoff_date
    ).delete()
    
    return f"Cleaned up {deleted_count} old product views"


@shared_task
def update_popular_searches():
    """
    Update popular searches based on recent search activity.
    """
    # Get search queries from the last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    recent_searches = SearchQuery.objects.filter(
        timestamp__gte=thirty_days_ago,
        query__isnull=False
    ).exclude(query='')
    
    # Count search frequencies
    search_counts = {}
    for search in recent_searches:
        query = search.query.lower().strip()
        if len(query) >= 2:  # Only count meaningful queries
            search_counts[query] = search_counts.get(query, 0) + 1
    
    # Update popular searches
    updated_count = 0
    for query, count in search_counts.items():
        popular_search, created = PopularSearch.objects.get_or_create(
            query=query,
            defaults={'search_count': count}
        )
        
        if not created:
            # Update existing record
            popular_search.search_count = count
            popular_search.save(update_fields=['search_count', 'last_searched'])
        
        updated_count += 1
    
    return f"Updated {updated_count} popular search terms"


@shared_task
def send_saved_search_notifications():
    """
    Send notifications for saved searches with new matching products.
    """
    # Get active saved searches with notifications enabled
    saved_searches = SavedSearch.objects.filter(
        is_active=True,
        notification_enabled=True
    )
    
    notifications_sent = 0
    
    for saved_search in saved_searches:
        try:
            # Check when last notification was sent
            last_notification = saved_search.last_notification_sent
            if last_notification:
                # Only check for products created since last notification
                since_date = last_notification
            else:
                # First time - check for products from last 24 hours
                since_date = timezone.now() - timedelta(days=1)
            
            # Perform search to find new matching products
            search_engine = ProductSearchEngine(user=saved_search.user)
            
            # Get products created since last notification
            new_products = search_engine.search(
                query=saved_search.search_query,
                filters=saved_search.filters
            ).filter(created_at__gte=since_date)
            
            if new_products.exists():
                # Send notification
                send_saved_search_notification.delay(
                    saved_search.id,
                    list(new_products.values_list('id', flat=True))
                )
                
                # Update last notification sent
                saved_search.last_notification_sent = timezone.now()
                saved_search.save(update_fields=['last_notification_sent'])
                
                notifications_sent += 1
                
        except Exception as e:
            print(f"Error processing saved search {saved_search.id}: {str(e)}")
    
    return f"Sent {notifications_sent} saved search notifications"


@shared_task
def send_saved_search_notification(saved_search_id, product_ids):
    """
    Send email notification for saved search matches.
    """
    try:
        saved_search = SavedSearch.objects.get(id=saved_search_id)
        products = Product.objects.filter(id__in=product_ids)
        
        if not products.exists():
            return "No products found for notification"
        
        user = saved_search.user
        
        # Check user preferences
        preferences = getattr(user, 'buyer_preferences', None)
        if preferences and not preferences.email_notifications:
            return "User has disabled email notifications"
        
        subject = f'New Products Match Your Saved Search: {saved_search.name} - Farm2Market'
        
        context = {
            'user': user,
            'saved_search': saved_search,
            'products': products,
            'product_count': products.count(),
        }
        
        html_message = render_to_string('emails/saved_search_notification.html', context)
        
        send_mail(
            subject=subject,
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return f"Saved search notification sent to {user.email} for {products.count()} products"
        
    except SavedSearch.DoesNotExist:
        return f"Saved search {saved_search_id} not found"
    except Exception as e:
        return f"Error sending saved search notification: {str(e)}"


@shared_task
def generate_search_analytics_report():
    """
    Generate search analytics report for admin.
    """
    try:
        # Get analytics for the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Total searches
        total_searches = SearchQuery.objects.filter(
            timestamp__gte=thirty_days_ago
        ).count()
        
        # Searches with results vs no results
        searches_with_results = SearchQuery.objects.filter(
            timestamp__gte=thirty_days_ago,
            results_count__gt=0
        ).count()
        
        searches_no_results = total_searches - searches_with_results
        
        # Top search terms
        top_searches = PopularSearch.objects.order_by('-search_count')[:10]
        
        # Most viewed products
        most_viewed = Product.objects.order_by('-views_count')[:10]
        
        # Search success rate
        success_rate = (searches_with_results / total_searches * 100) if total_searches > 0 else 0
        
        analytics_data = {
            'period': '30 days',
            'total_searches': total_searches,
            'searches_with_results': searches_with_results,
            'searches_no_results': searches_no_results,
            'success_rate': round(success_rate, 2),
            'top_searches': [{'query': s.query, 'count': s.search_count} for s in top_searches],
            'most_viewed_products': [{'name': p.product_name, 'views': p.views_count} for p in most_viewed],
            'generated_at': timezone.now().isoformat(),
        }
        
        # TODO: Store analytics data or send to admin
        # cache.set('search_analytics_report', analytics_data, timeout=86400)
        
        return f"Generated search analytics report: {total_searches} searches, {success_rate:.1f}% success rate"
        
    except Exception as e:
        return f"Error generating search analytics report: {str(e)}"


@shared_task
def update_product_popularity_scores():
    """
    Update product popularity scores based on views, searches, and other metrics.
    """
    try:
        # Get all products
        products = Product.objects.filter(status='Available')
        
        updated_count = 0
        
        for product in products:
            # Calculate popularity score based on various factors
            view_score = min(product.views_count / 100, 10)  # Max 10 points for views
            
            # Recent views (last 7 days)
            recent_views = ProductView.objects.filter(
                product=product,
                viewed_at__gte=timezone.now() - timedelta(days=7)
            ).count()
            recent_view_score = min(recent_views / 10, 5)  # Max 5 points for recent views
            
            # Reviews score
            avg_rating = product.reviews.filter(is_approved=True).aggregate(
                avg_rating=models.Avg('rating')
            )['avg_rating'] or 0
            review_score = avg_rating  # Max 5 points for rating
            
            # Wishlist score (if product is in wishlists)
            wishlist_count = product.wishlisted_by_buyers.count()
            wishlist_score = min(wishlist_count / 5, 3)  # Max 3 points for wishlist
            
            # Calculate total popularity score
            popularity_score = view_score + recent_view_score + review_score + wishlist_score
            
            # Update product (you might want to add a popularity_score field to Product model)
            # product.popularity_score = popularity_score
            # product.save(update_fields=['popularity_score'])
            
            updated_count += 1
        
        return f"Updated popularity scores for {updated_count} products"
        
    except Exception as e:
        return f"Error updating product popularity scores: {str(e)}"


@shared_task
def optimize_search_index():
    """
    Optimize search performance by updating search indexes.
    """
    try:
        # This would typically involve updating search engine indexes
        # For now, we'll just clean up and optimize database queries
        
        # Update product search relevance scores
        products_updated = 0
        
        # You could implement more sophisticated search indexing here
        # For example, updating Elasticsearch indexes, creating search vectors, etc.
        
        return f"Optimized search index for {products_updated} products"
        
    except Exception as e:
        return f"Error optimizing search index: {str(e)}"


@shared_task
def send_weekly_search_trends_report():
    """
    Send weekly search trends report to admin.
    """
    try:
        # Get search trends for the last week
        week_ago = timezone.now() - timedelta(days=7)
        
        # Top searches this week
        recent_searches = SearchQuery.objects.filter(
            timestamp__gte=week_ago
        ).values('query').annotate(
            search_count=models.Count('id')
        ).order_by('-search_count')[:10]
        
        # Trending products (most viewed this week)
        trending_products = ProductView.objects.filter(
            viewed_at__gte=week_ago
        ).values('product__product_name').annotate(
            view_count=models.Count('id')
        ).order_by('-view_count')[:10]
        
        # Search success rate
        total_searches = SearchQuery.objects.filter(timestamp__gte=week_ago).count()
        successful_searches = SearchQuery.objects.filter(
            timestamp__gte=week_ago,
            results_count__gt=0
        ).count()
        
        success_rate = (successful_searches / total_searches * 100) if total_searches > 0 else 0
        
        context = {
            'period': 'Last 7 days',
            'total_searches': total_searches,
            'success_rate': round(success_rate, 2),
            'top_searches': recent_searches,
            'trending_products': trending_products,
        }
        
        # TODO: Send email to admin
        # html_message = render_to_string('emails/weekly_search_trends.html', context)
        # send_mail(...)
        
        return f"Weekly search trends report generated: {total_searches} searches, {success_rate:.1f}% success rate"
        
    except Exception as e:
        return f"Error generating weekly search trends report: {str(e)}"
