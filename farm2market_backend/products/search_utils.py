"""
Search and filtering utilities for Farm2Market products.
"""
from django.db.models import Q, F, Count, Avg, Case, When, Value, FloatField, BooleanField
from django.utils import timezone
from datetime import timedelta
import math
from .models import Product, Category
from .search_models import SearchQuery, PopularSearch, ProductView

# Simple coordinate class to replace GIS Point
class SimplePoint:
    """Simple point class for basic coordinate operations."""
    def __init__(self, longitude, latitude):
        self.longitude = longitude
        self.latitude = latitude
        self.x = longitude
        self.y = latitude

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees).
    Returns distance in kilometers.
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))

    # Radius of earth in kilometers
    r = 6371

    return c * r


class ProductSearchEngine:
    """
    Advanced product search engine with filtering and sorting.
    """
    
    def __init__(self, user=None, request=None):
        self.user = user
        self.request = request
        self.base_queryset = Product.objects.select_related(
            'farmer', 'farmer__farmer_profile', 'location'
        ).prefetch_related(
            'categories', 'images', 'reviews'
        ).filter(status='Available')
    
    def search(self, query=None, filters=None, sort_by=None, page_size=20):
        """
        Perform comprehensive product search.
        
        Args:
            query: Search query string
            filters: Dictionary of filters
            sort_by: Sorting option
            page_size: Number of results per page
        """
        queryset = self.base_queryset
        
        # Apply text search
        if query:
            queryset = self._apply_text_search(queryset, query)
        
        # Apply filters
        if filters:
            queryset = self._apply_filters(queryset, filters)
        
        # Apply sorting
        if sort_by:
            queryset = self._apply_sorting(queryset, sort_by, filters)
        
        # Add annotations for additional data
        queryset = self._add_annotations(queryset)
        
        # Track search query
        if query or filters:
            self._track_search_query(query, filters, queryset.count())
        
        return queryset
    
    def _apply_text_search(self, queryset, query):
        """Apply text search across multiple fields."""
        search_query = Q()
        
        # Split query into terms
        terms = query.strip().split()
        
        for term in terms:
            term_query = (
                Q(product_name__icontains=term) |
                Q(description__icontains=term) |
                Q(farmer__first_name__icontains=term) |
                Q(farmer__last_name__icontains=term) |
                Q(farmer__farmer_profile__farm_name__icontains=term) |
                Q(categories__name__icontains=term)
            )
            search_query &= term_query
        
        return queryset.filter(search_query).distinct()
    
    def _apply_filters(self, queryset, filters):
        """Apply various filters to the queryset."""
        
        # Price range filter
        if filters.get('min_price'):
            queryset = queryset.filter(price__gte=filters['min_price'])
        if filters.get('max_price'):
            queryset = queryset.filter(price__lte=filters['max_price'])
        
        # Category filter
        if filters.get('categories'):
            category_ids = filters['categories']
            if isinstance(category_ids, str):
                category_ids = [int(id) for id in category_ids.split(',')]
            queryset = queryset.filter(categories__id__in=category_ids)
        
        # Location-based filter (radius)
        if filters.get('latitude') and filters.get('longitude') and filters.get('radius'):
            queryset = self._apply_location_filter(
                queryset, 
                float(filters['latitude']), 
                float(filters['longitude']), 
                float(filters['radius'])
            )
        
        # Availability filter
        if filters.get('in_stock_only'):
            queryset = queryset.filter(quantity__gt=0)
        
        # Organic filter
        if filters.get('organic_only'):
            queryset = queryset.filter(organic_certified=True)
        
        # Harvest date filter
        if filters.get('harvest_date_from'):
            queryset = queryset.filter(harvest_date__gte=filters['harvest_date_from'])
        if filters.get('harvest_date_to'):
            queryset = queryset.filter(harvest_date__lte=filters['harvest_date_to'])
        
        # Farmer verification filter
        if filters.get('verified_farmers_only'):
            queryset = queryset.filter(farmer__is_approved=True)
        
        # Minimum quantity filter
        if filters.get('min_quantity'):
            queryset = queryset.filter(quantity__gte=filters['min_quantity'])
        
        # Featured products filter
        if filters.get('featured_only'):
            queryset = queryset.filter(featured=True)
        
        return queryset
    
    def _apply_location_filter(self, queryset, lat, lng, radius_km):
        """Apply location-based filtering using distance calculation."""
        # Filter products within radius using our global distance function
        filtered_products = []

        for product in queryset:
            # Check if product has location data
            if hasattr(product, 'farmer') and hasattr(product.farmer, 'farmer_profile'):
                farmer_profile = product.farmer.farmer_profile
                if (hasattr(farmer_profile, 'latitude') and hasattr(farmer_profile, 'longitude') and
                    farmer_profile.latitude and farmer_profile.longitude):

                    distance = calculate_distance(
                        lat, lng,
                        float(farmer_profile.latitude),
                        float(farmer_profile.longitude)
                    )

                    if distance <= radius_km:
                        filtered_products.append(product.id)

        return queryset.filter(id__in=filtered_products)
    
    def _apply_sorting(self, queryset, sort_by, filters=None):
        """Apply sorting to the queryset."""
        
        if sort_by == 'price_low_high':
            return queryset.order_by('price')
        
        elif sort_by == 'price_high_low':
            return queryset.order_by('-price')
        
        elif sort_by == 'newest':
            return queryset.order_by('-created_at')
        
        elif sort_by == 'oldest':
            return queryset.order_by('created_at')
        
        elif sort_by == 'harvest_date_newest':
            return queryset.filter(harvest_date__isnull=False).order_by('-harvest_date')
        
        elif sort_by == 'harvest_date_oldest':
            return queryset.filter(harvest_date__isnull=False).order_by('harvest_date')
        
        elif sort_by == 'quantity_high_low':
            return queryset.order_by('-quantity')
        
        elif sort_by == 'quantity_low_high':
            return queryset.order_by('quantity')
        
        elif sort_by == 'farmer_rating':
            # Sort by farmer's average rating (would need farmer rating system)
            return queryset.order_by('-farmer__farmer_profile__trust_badge', '-created_at')
        
        elif sort_by == 'popularity':
            # Sort by view count
            return queryset.order_by('-views_count')
        
        elif sort_by == 'distance' and filters:
            # Distance sorting (simplified - would need proper geospatial sorting)
            if (filters.get('latitude') and filters.get('longitude')):
                return queryset.order_by('created_at')  # Placeholder
        
        # Default sorting
        return queryset.order_by('-featured', '-created_at')
    
    def _add_annotations(self, queryset):
        """Add useful annotations to the queryset."""
        return queryset.annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews', filter=Q(reviews__is_approved=True)),
            is_low_stock=Case(
                When(quantity__lte=F('sold_quantity') * 0.1, then=Value(True)),
                default=Value(False),
                output_field=BooleanField()
            )
        )
    
    def _track_search_query(self, query, filters, results_count):
        """Track search query for analytics."""
        if not query and not filters:
            return
        
        # Get client info
        ip_address = None
        user_agent = ''
        session_id = ''
        
        if self.request:
            ip_address = self._get_client_ip(self.request)
            user_agent = self.request.META.get('HTTP_USER_AGENT', '')
            session_id = self.request.session.session_key or ''
        
        # Create search query record
        SearchQuery.objects.create(
            user=self.user,
            query=query or '',
            filters=filters or {},
            results_count=results_count,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )
        
        # Update popular searches
        if query:
            PopularSearch.increment_search_count(query)
    
    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class ProductRecommendationEngine:
    """
    Product recommendation engine based on user behavior and preferences.
    """
    
    def __init__(self, user=None):
        self.user = user
    
    def get_recommendations(self, limit=10):
        """Get product recommendations for user."""
        if not self.user:
            return self._get_popular_products(limit)
        
        recommendations = []
        
        # Get recommendations based on user type
        if self.user.user_type == 'Buyer':
            recommendations.extend(self._get_preference_based_recommendations())
            recommendations.extend(self._get_wishlist_based_recommendations())
            recommendations.extend(self._get_view_history_recommendations())
        
        # Remove duplicates and limit
        seen_ids = set()
        unique_recommendations = []
        
        for product in recommendations:
            if product.id not in seen_ids:
                unique_recommendations.append(product)
                seen_ids.add(product.id)
                
                if len(unique_recommendations) >= limit:
                    break
        
        # Fill remaining slots with popular products
        if len(unique_recommendations) < limit:
            popular_products = self._get_popular_products(
                limit - len(unique_recommendations),
                exclude_ids=seen_ids
            )
            unique_recommendations.extend(popular_products)
        
        return unique_recommendations[:limit]
    
    def _get_preference_based_recommendations(self):
        """Get recommendations based on buyer preferences."""
        try:
            preferences = self.user.buyer_preferences
            queryset = Product.objects.filter(status='Available')
            
            # Filter by preferred categories
            if preferences.preferred_categories.exists():
                queryset = queryset.filter(
                    categories__in=preferences.preferred_categories.all()
                )
            
            # Filter by organic preference
            if preferences.organic_only:
                queryset = queryset.filter(organic_certified=True)
            
            # Filter by budget range
            if preferences.budget_range_min:
                queryset = queryset.filter(price__gte=preferences.budget_range_min)
            if preferences.budget_range_max:
                queryset = queryset.filter(price__lte=preferences.budget_range_max)
            
            return list(queryset.order_by('-featured', '-created_at')[:5])
            
        except:
            return []
    
    def _get_wishlist_based_recommendations(self):
        """Get recommendations based on wishlist items."""
        try:
            wishlist_items = self.user.wishlist_items.all()
            if not wishlist_items.exists():
                return []
            
            # Get categories from wishlist items
            wishlist_categories = set()
            for item in wishlist_items:
                wishlist_categories.update(item.product.categories.all())
            
            # Find similar products
            similar_products = Product.objects.filter(
                categories__in=wishlist_categories,
                status='Available'
            ).exclude(
                id__in=wishlist_items.values_list('product_id', flat=True)
            ).distinct()
            
            return list(similar_products.order_by('-featured', '-created_at')[:5])
            
        except:
            return []
    
    def _get_view_history_recommendations(self):
        """Get recommendations based on view history."""
        try:
            # Get recently viewed products
            recent_views = ProductView.objects.filter(
                user=self.user
            ).order_by('-viewed_at')[:10]
            
            if not recent_views:
                return []
            
            # Get categories from viewed products
            viewed_categories = set()
            for view in recent_views:
                viewed_categories.update(view.product.categories.all())
            
            # Find similar products
            similar_products = Product.objects.filter(
                categories__in=viewed_categories,
                status='Available'
            ).exclude(
                id__in=recent_views.values_list('product_id', flat=True)
            ).distinct()
            
            return list(similar_products.order_by('-featured', '-created_at')[:5])
            
        except:
            return []
    
    def _get_popular_products(self, limit=10, exclude_ids=None):
        """Get popular products based on views and ratings."""
        queryset = Product.objects.filter(status='Available')
        
        if exclude_ids:
            queryset = queryset.exclude(id__in=exclude_ids)
        
        # Order by popularity metrics
        queryset = queryset.annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        ).order_by('-featured', '-views_count', '-avg_rating', '-created_at')
        
        return list(queryset[:limit])


def track_product_view(product, user=None, request=None):
    """Track product view for analytics."""
    ip_address = None
    user_agent = ''
    referrer = ''
    session_id = ''
    
    if request:
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        referrer = request.META.get('HTTP_REFERER', '')
        session_id = request.session.session_key or ''
    
    # Create product view record
    ProductView.objects.create(
        product=product,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        referrer=referrer,
        session_id=session_id
    )
    
    # Increment product view count
    Product.objects.filter(id=product.id).update(
        views_count=F('views_count') + 1
    )
