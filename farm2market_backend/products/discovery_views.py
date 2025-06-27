"""
Views for product discovery and search.
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Avg
from django.utils import timezone
from apps.core.responses import StandardResponse
from apps.core.exceptions import ValidationError, NotFoundError
from .models import Product, Category, ProductReview
from .search_models import SearchQuery, PopularSearch, DeliveryZone, SavedSearch
from .search_utils import ProductSearchEngine, ProductRecommendationEngine, track_product_view
from .discovery_serializers import (
    ProductSearchSerializer, ProductDetailSerializer, CategoryTreeSerializer,
    ProductReviewSerializer, SearchQuerySerializer, PopularSearchSerializer,
    DeliveryZoneSerializer, SavedSearchSerializer, SearchFiltersSerializer,
    SortOptionsSerializer
)

User = get_user_model()


class ProductSearchView(APIView):
    """
    Advanced product search with filtering and sorting.
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """
        Search products with advanced filtering and sorting.
        
        Query Parameters:
        - q: Search query
        - categories: Comma-separated category IDs
        - min_price, max_price: Price range
        - latitude, longitude, radius: Location filtering
        - in_stock_only: Boolean
        - organic_only: Boolean
        - verified_farmers_only: Boolean
        - featured_only: Boolean
        - sort_by: Sorting option
        - page: Page number
        - page_size: Results per page
        """
        # Validate filters
        filter_serializer = SearchFiltersSerializer(data=request.query_params)
        if not filter_serializer.is_valid():
            return StandardResponse.validation_error(
                errors=filter_serializer.errors,
                message='Invalid search filters.'
            )
        
        # Validate sorting
        sort_serializer = SortOptionsSerializer(data=request.query_params)
        if not sort_serializer.is_valid():
            return StandardResponse.validation_error(
                errors=sort_serializer.errors,
                message='Invalid sort option.'
            )
        
        # Extract parameters
        query = filter_serializer.validated_data.get('query', '')
        filters = {k: v for k, v in filter_serializer.validated_data.items() if k != 'query' and v is not None}
        sort_by = sort_serializer.validated_data.get('sort_by', 'relevance')
        
        # Perform search
        search_engine = ProductSearchEngine(
            user=request.user if request.user.is_authenticated else None,
            request=request
        )
        
        queryset = search_engine.search(
            query=query,
            filters=filters,
            sort_by=sort_by
        )
        
        # Pagination
        page_size = min(int(request.query_params.get('page_size', 20)), 100)
        page = int(request.query_params.get('page', 1))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        total_count = queryset.count()
        products = queryset[start:end]
        
        # Serialize results
        serializer = ProductSearchSerializer(products, many=True)
        
        # Prepare response data
        data = {
            'products': serializer.data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': (total_count + page_size - 1) // page_size,
                'has_next': end < total_count,
                'has_previous': page > 1,
            },
            'search_info': {
                'query': query,
                'filters_applied': len([v for v in filters.values() if v]),
                'sort_by': sort_by,
            }
        }
        
        return StandardResponse.success(
            data=data,
            message=f'Found {total_count} products.'
        )


class ProductBrowseView(APIView):
    """
    Browse products by category with filtering.
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """Browse products with optional category filtering."""
        category_id = request.query_params.get('category')
        featured_only = request.query_params.get('featured_only', '').lower() == 'true'
        
        queryset = Product.objects.filter(status='Available').select_related(
            'farmer', 'farmer__farmer_profile'
        ).prefetch_related('categories', 'images')
        
        # Filter by category
        if category_id:
            try:
                category = Category.objects.get(id=category_id, is_active=True)
                queryset = queryset.filter(categories=category)
            except Category.DoesNotExist:
                return StandardResponse.not_found(
                    message='Category not found.'
                )
        
        # Filter featured products
        if featured_only:
            queryset = queryset.filter(featured=True)
        
        # Add annotations
        queryset = queryset.annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews', filter=Q(reviews__is_approved=True))
        )
        
        # Sorting
        sort_by = request.query_params.get('sort_by', 'featured')
        if sort_by == 'featured':
            queryset = queryset.order_by('-featured', '-created_at')
        elif sort_by == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort_by == 'price_low_high':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_high_low':
            queryset = queryset.order_by('-price')
        elif sort_by == 'popularity':
            queryset = queryset.order_by('-views_count')
        
        # Pagination
        page_size = min(int(request.query_params.get('page_size', 20)), 100)
        page = int(request.query_params.get('page', 1))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        total_count = queryset.count()
        products = queryset[start:end]
        
        serializer = ProductSearchSerializer(products, many=True)
        
        data = {
            'products': serializer.data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': (total_count + page_size - 1) // page_size,
                'has_next': end < total_count,
                'has_previous': page > 1,
            }
        }
        
        return StandardResponse.success(
            data=data,
            message=f'Found {total_count} products.'
        )


class CategoryListView(generics.ListAPIView):
    """
    List all product categories with hierarchy.
    """
    serializer_class = CategoryTreeSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        return Category.objects.filter(is_active=True, parent=None).order_by('display_order', 'name')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return StandardResponse.success(
            data=serializer.data,
            message='Categories retrieved successfully.'
        )


class FeaturedProductsView(APIView):
    """
    Get featured products.
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """Get featured products."""
        limit = min(int(request.query_params.get('limit', 10)), 50)
        
        products = Product.objects.filter(
            status='Available',
            featured=True
        ).select_related(
            'farmer', 'farmer__farmer_profile'
        ).prefetch_related(
            'categories', 'images'
        ).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews', filter=Q(reviews__is_approved=True))
        ).order_by('-created_at')[:limit]
        
        serializer = ProductSearchSerializer(products, many=True)
        
        return StandardResponse.success(
            data=serializer.data,
            message=f'Retrieved {len(products)} featured products.'
        )


class NearbyProductsView(APIView):
    """
    Get products near a specific location.
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """Get products near specified coordinates."""
        latitude = request.query_params.get('latitude')
        longitude = request.query_params.get('longitude')
        radius = request.query_params.get('radius', '50')  # Default 50km
        
        if not latitude or not longitude:
            return StandardResponse.validation_error(
                errors={'location': 'Latitude and longitude are required.'},
                message='Location parameters missing.'
            )
        
        try:
            lat = float(latitude)
            lng = float(longitude)
            radius_km = float(radius)
        except ValueError:
            return StandardResponse.validation_error(
                errors={'location': 'Invalid coordinate values.'},
                message='Invalid location parameters.'
            )
        
        # Use search engine for location filtering
        search_engine = ProductSearchEngine(
            user=request.user if request.user.is_authenticated else None,
            request=request
        )
        
        filters = {
            'latitude': lat,
            'longitude': lng,
            'radius': radius_km
        }
        
        queryset = search_engine.search(filters=filters, sort_by='distance')
        
        limit = min(int(request.query_params.get('limit', 20)), 100)
        products = queryset[:limit]
        
        serializer = ProductSearchSerializer(products, many=True)
        
        return StandardResponse.success(
            data=serializer.data,
            message=f'Found {len(products)} products within {radius_km}km.'
        )


class ProductDetailView(generics.RetrieveAPIView):
    """
    Get detailed product information.
    """
    serializer_class = ProductDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Product.objects.select_related(
            'farmer', 'farmer__farmer_profile', 'location'
        ).prefetch_related(
            'categories', 'images', 'reviews'
        ).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews', filter=Q(reviews__is_approved=True))
        )
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Track product view
        track_product_view(
            product=instance,
            user=request.user if request.user.is_authenticated else None,
            request=request
        )
        
        serializer = self.get_serializer(instance)
        
        return StandardResponse.success(
            data=serializer.data,
            message='Product details retrieved successfully.'
        )


class ProductRecommendationsView(APIView):
    """
    Get product recommendations for user.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get personalized product recommendations."""
        limit = min(int(request.query_params.get('limit', 10)), 50)
        
        recommendation_engine = ProductRecommendationEngine(user=request.user)
        recommendations = recommendation_engine.get_recommendations(limit=limit)
        
        serializer = ProductSearchSerializer(recommendations, many=True)
        
        return StandardResponse.success(
            data=serializer.data,
            message=f'Retrieved {len(recommendations)} recommendations.'
        )


class PopularSearchesView(APIView):
    """
    Get popular search terms.
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """Get popular search terms."""
        limit = min(int(request.query_params.get('limit', 10)), 50)
        
        popular_searches = PopularSearch.objects.all()[:limit]
        serializer = PopularSearchSerializer(popular_searches, many=True)
        
        return StandardResponse.success(
            data=serializer.data,
            message='Popular searches retrieved successfully.'
        )


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def search_suggestions(request):
    """
    Get search suggestions based on query.
    """
    query = request.query_params.get('q', '').strip()
    
    if len(query) < 2:
        return StandardResponse.success(
            data=[],
            message='Query too short for suggestions.'
        )
    
    # Get product name suggestions
    product_suggestions = Product.objects.filter(
        product_name__icontains=query,
        status='Available'
    ).values_list('product_name', flat=True).distinct()[:5]
    
    # Get category suggestions
    category_suggestions = Category.objects.filter(
        name__icontains=query,
        is_active=True
    ).values_list('name', flat=True)[:3]
    
    # Get popular search suggestions
    popular_suggestions = PopularSearch.objects.filter(
        query__icontains=query
    ).values_list('query', flat=True)[:3]
    
    suggestions = {
        'products': list(product_suggestions),
        'categories': list(category_suggestions),
        'popular': list(popular_suggestions),
    }
    
    return StandardResponse.success(
        data=suggestions,
        message='Search suggestions retrieved successfully.'
    )
