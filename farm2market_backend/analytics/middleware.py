"""
Middleware for automatic analytics tracking.
"""
import json
import time
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.urls import resolve
from .services import AnalyticsService

User = get_user_model()


class AnalyticsTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to automatically track user activities and page views.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.analytics_service = AnalyticsService()
        
        # Define which URLs to track
        self.tracked_patterns = [
            'products:product-detail',
            'farmers:farmer-detail',
            'orders:order-detail',
            'messaging:conversation-detail',
        ]
        
        # Define activity mappings
        self.activity_mappings = {
            'GET': {
                'products:product-detail': ('view_product', 'product'),
                'farmers:farmer-detail': ('view_farmer', 'user'),
                'orders:order-detail': ('view_order', 'order'),
            },
            'POST': {
                'orders:order-create': ('place_order', 'order'),
                'cart:add-item': ('add_to_cart', 'product'),
                'messaging:send-message': ('send_message', 'message'),
                'products:product-create': ('add_product', 'product'),
                'reservations:reservation-create': ('create_reservation', 'reservation'),
            },
            'PUT': {
                'users:profile-update': ('update_profile', 'user'),
                'products:product-update': ('update_product', 'product'),
            },
            'DELETE': {
                'cart:remove-item': ('remove_from_cart', 'product'),
                'orders:order-cancel': ('cancel_order', 'order'),
            }
        }
    
    def process_request(self, request):
        """Process incoming request."""
        # Store request start time for duration tracking
        request._analytics_start_time = time.time()
        
        # Store session ID if not exists
        if not request.session.session_key:
            request.session.create()
        
        return None
    
    def process_response(self, request, response):
        """Process response and track analytics."""
        try:
            # Skip tracking for certain conditions
            if self._should_skip_tracking(request, response):
                return response
            
            # Get URL pattern
            try:
                url_match = resolve(request.path_info)
                url_name = f"{url_match.namespace}:{url_match.url_name}" if url_match.namespace else url_match.url_name
            except:
                return response
            
            # Track activity if mapped
            self._track_activity(request, response, url_name)
            
            # Track product view if applicable
            self._track_product_view(request, response, url_name)
            
        except Exception as e:
            # Don't let analytics tracking break the response
            pass
        
        return response
    
    def _should_skip_tracking(self, request, response):
        """Determine if tracking should be skipped."""
        # Skip for non-successful responses
        if response.status_code >= 400:
            return True
        
        # Skip for static files and admin
        if request.path_info.startswith('/static/') or request.path_info.startswith('/admin/'):
            return True
        
        # Skip for API documentation
        if request.path_info.startswith('/api/docs/') or request.path_info.startswith('/api/schema/'):
            return True
        
        # Skip for health checks
        if request.path_info in ['/health/', '/ping/']:
            return True
        
        # Skip for bots (basic check)
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        bot_indicators = ['bot', 'crawler', 'spider', 'scraper']
        if any(indicator in user_agent for indicator in bot_indicators):
            return True
        
        return False
    
    def _track_activity(self, request, response, url_name):
        """Track user activity based on URL pattern."""
        method = request.method
        
        if method in self.activity_mappings and url_name in self.activity_mappings[method]:
            activity_type, resource_type = self.activity_mappings[method][url_name]
            
            # Get resource ID from URL kwargs or response
            resource_id = self._extract_resource_id(request, response, resource_type)
            
            if resource_id:
                # Prepare metadata
                metadata = {
                    'url': request.path_info,
                    'method': method,
                    'status_code': response.status_code,
                }
                
                # Add request duration if available
                if hasattr(request, '_analytics_start_time'):
                    duration = time.time() - request._analytics_start_time
                    metadata['duration_ms'] = round(duration * 1000, 2)
                
                # Add query parameters for search tracking
                if activity_type == 'search':
                    metadata['query_params'] = dict(request.GET)
                
                # Track the activity
                user = request.user if request.user.is_authenticated else None
                
                self.analytics_service.track_user_activity(
                    user=user,
                    activity_type=activity_type,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    metadata=metadata,
                    request=request
                )
    
    def _track_product_view(self, request, response, url_name):
        """Track product page views."""
        if url_name == 'products:product-detail' and request.method == 'GET':
            # Extract product ID
            product_id = self._extract_resource_id(request, response, 'product')
            
            if product_id:
                try:
                    from apps.products.models import Product
                    product = Product.objects.get(id=product_id)
                    
                    user = request.user if request.user.is_authenticated else None
                    
                    # Track product view
                    product_view = self.analytics_service.track_product_view(
                        product=product,
                        viewer=user,
                        request=request
                    )
                    
                    # Update view duration if available
                    if hasattr(request, '_analytics_start_time'):
                        duration = time.time() - request._analytics_start_time
                        product_view.view_duration = int(duration)
                        product_view.save(update_fields=['view_duration'])
                
                except Product.DoesNotExist:
                    pass
    
    def _extract_resource_id(self, request, response, resource_type):
        """Extract resource ID from request or response."""
        # Try to get from URL kwargs first
        if hasattr(request, 'resolver_match') and request.resolver_match:
            kwargs = request.resolver_match.kwargs
            
            # Common ID parameter names
            id_params = ['id', 'pk', f'{resource_type}_id']
            
            for param in id_params:
                if param in kwargs:
                    return kwargs[param]
        
        # Try to get from response data for POST requests
        if request.method == 'POST' and response.status_code in [200, 201]:
            try:
                if hasattr(response, 'data') and isinstance(response.data, dict):
                    if 'id' in response.data:
                        return response.data['id']
                    elif 'data' in response.data and isinstance(response.data['data'], dict):
                        if 'id' in response.data['data']:
                            return response.data['data']['id']
            except:
                pass
        
        # Try to get from request data for certain operations
        if request.method in ['POST', 'PUT', 'DELETE']:
            try:
                if request.content_type == 'application/json':
                    data = json.loads(request.body)
                    if isinstance(data, dict) and f'{resource_type}_id' in data:
                        return data[f'{resource_type}_id']
            except:
                pass
        
        return None


class SearchTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to track search queries and results.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.analytics_service = AnalyticsService()
    
    def process_response(self, request, response):
        """Track search queries."""
        try:
            # Check if this is a search request
            if self._is_search_request(request) and response.status_code == 200:
                self._track_search(request, response)
        except Exception as e:
            # Don't let search tracking break the response
            pass
        
        return response
    
    def _is_search_request(self, request):
        """Check if request is a search."""
        # Check URL patterns that indicate search
        search_patterns = [
            '/api/v1/products/',
            '/api/v1/search/',
            '/search/',
        ]
        
        # Check if URL matches search patterns and has query parameter
        if any(request.path_info.startswith(pattern) for pattern in search_patterns):
            return 'q' in request.GET or 'query' in request.GET or 'search' in request.GET
        
        return False
    
    def _track_search(self, request, response):
        """Track search query and results."""
        # Extract search query
        query = (
            request.GET.get('q') or 
            request.GET.get('query') or 
            request.GET.get('search') or 
            ''
        ).strip()
        
        if not query:
            return
        
        # Extract results count from response
        results_count = 0
        
        try:
            if hasattr(response, 'data'):
                data = response.data
                
                # Handle different response formats
                if isinstance(data, dict):
                    if 'count' in data:
                        results_count = data['count']
                    elif 'data' in data and isinstance(data['data'], dict):
                        if 'count' in data['data']:
                            results_count = data['data']['count']
                        elif 'pagination' in data['data'] and 'total_count' in data['data']['pagination']:
                            results_count = data['data']['pagination']['total_count']
                    elif 'results' in data and isinstance(data['results'], list):
                        results_count = len(data['results'])
                elif isinstance(data, list):
                    results_count = len(data)
        except:
            pass
        
        # Extract filters and sort order
        filters_used = {}
        sort_order = request.GET.get('ordering', request.GET.get('sort', ''))
        
        # Common filter parameters
        filter_params = [
            'category', 'price_min', 'price_max', 'location', 'farmer',
            'availability', 'organic', 'rating_min'
        ]
        
        for param in filter_params:
            if param in request.GET:
                filters_used[param] = request.GET[param]
        
        # Track the search
        user = request.user if request.user.is_authenticated else None
        
        self.analytics_service.track_search(
            query=query,
            user=user,
            results_count=results_count,
            filters_used=filters_used,
            sort_order=sort_order,
            request=request
        )


class CartAbandonmentTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to track cart abandonment.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.analytics_service = AnalyticsService()
    
    def process_response(self, request, response):
        """Track cart abandonment signals."""
        try:
            # Track cart abandonment at different stages
            if self._is_cart_abandonment_signal(request):
                self._track_cart_abandonment(request)
        except Exception as e:
            pass
        
        return response
    
    def _is_cart_abandonment_signal(self, request):
        """Check if request indicates potential cart abandonment."""
        # This would be triggered by frontend JavaScript
        # when user leaves cart/checkout pages
        
        abandonment_signals = [
            '/api/v1/analytics/cart-abandonment/',
            '/api/v1/cart/abandon/',
        ]
        
        return any(request.path_info.startswith(signal) for signal in abandonment_signals)
    
    def _track_cart_abandonment(self, request):
        """Track cart abandonment event."""
        try:
            # Extract cart data from request
            if request.method == 'POST':
                data = json.loads(request.body)
                
                cart_value = data.get('cart_value', 0)
                items_count = data.get('items_count', 0)
                stage = data.get('stage', 'cart')
                
                user = request.user if request.user.is_authenticated else None
                session_id = request.session.session_key
                
                self.analytics_service.track_cart_abandonment(
                    user=user,
                    session_id=session_id,
                    cart_value=cart_value,
                    items_count=items_count,
                    stage=stage
                )
        except:
            pass
