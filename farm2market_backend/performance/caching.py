"""
Caching services for Farm2Market performance optimization.
"""
import json
import hashlib
from functools import wraps
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class CacheService:
    """
    Main caching service with intelligent cache management.
    """
    
    def __init__(self):
        self.default_timeout = getattr(settings, 'CACHE_DEFAULT_TIMEOUT', 300)  # 5 minutes
        self.cache_prefix = getattr(settings, 'CACHE_KEY_PREFIX', 'farm2market')
    
    def get_cache_key(self, key_parts, prefix=None):
        """
        Generate a consistent cache key.
        """
        if prefix is None:
            prefix = self.cache_prefix
        
        # Convert all parts to strings and join
        key_string = ':'.join(str(part) for part in key_parts)
        
        # Hash long keys to avoid Redis key length limits
        if len(key_string) > 200:
            key_string = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"{prefix}:{key_string}"
    
    def set_cache(self, key, value, timeout=None):
        """
        Set cache value with optional timeout.
        """
        if timeout is None:
            timeout = self.default_timeout
        
        cache.set(key, value, timeout)
    
    def get_cache(self, key, default=None):
        """
        Get cache value with default fallback.
        """
        return cache.get(key, default)
    
    def delete_cache(self, key):
        """
        Delete cache entry.
        """
        cache.delete(key)
    
    def delete_pattern(self, pattern):
        """
        Delete cache entries matching pattern.
        """
        # This requires Redis backend with delete_pattern support
        try:
            cache.delete_pattern(f"{self.cache_prefix}:{pattern}")
        except AttributeError:
            # Fallback for backends that don't support pattern deletion
            pass
    
    def invalidate_user_cache(self, user_id):
        """
        Invalidate all cache entries for a specific user.
        """
        patterns = [
            f"user:{user_id}:*",
            f"farmer:{user_id}:*",
            f"buyer:{user_id}:*",
        ]
        
        for pattern in patterns:
            self.delete_pattern(pattern)
    
    def invalidate_product_cache(self, product_id):
        """
        Invalidate cache entries related to a product.
        """
        patterns = [
            f"product:{product_id}:*",
            f"products:*",  # Invalidate product lists
            f"search:*",    # Invalidate search results
        ]
        
        for pattern in patterns:
            self.delete_pattern(pattern)


class QueryCacheService:
    """
    Service for caching database query results.
    """
    
    def __init__(self):
        self.cache_service = CacheService()
        self.query_timeout = 600  # 10 minutes
    
    def cache_queryset(self, queryset, cache_key_parts, timeout=None):
        """
        Cache queryset results.
        """
        if timeout is None:
            timeout = self.query_timeout
        
        cache_key = self.cache_service.get_cache_key(cache_key_parts, 'query')
        
        # Check if already cached
        cached_result = self.cache_service.get_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Execute query and cache result
        result = list(queryset.values())
        self.cache_service.set_cache(cache_key, result, timeout)
        
        return result
    
    def cache_model_instance(self, model_class, instance_id, timeout=None):
        """
        Cache model instance.
        """
        if timeout is None:
            timeout = self.query_timeout
        
        cache_key = self.cache_service.get_cache_key(
            ['model', model_class.__name__.lower(), instance_id],
            'instance'
        )
        
        # Check cache first
        cached_instance = self.cache_service.get_cache(cache_key)
        if cached_instance is not None:
            return cached_instance
        
        # Get from database and cache
        try:
            instance = model_class.objects.get(id=instance_id)
            self.cache_service.set_cache(cache_key, instance, timeout)
            return instance
        except model_class.DoesNotExist:
            return None
    
    def invalidate_model_cache(self, model_class, instance_id=None):
        """
        Invalidate cache for model instances.
        """
        if instance_id:
            # Invalidate specific instance
            cache_key = self.cache_service.get_cache_key(
                ['model', model_class.__name__.lower(), instance_id],
                'instance'
            )
            self.cache_service.delete_cache(cache_key)
        else:
            # Invalidate all instances of this model
            pattern = f"instance:{model_class.__name__.lower()}:*"
            self.cache_service.delete_pattern(pattern)


class APIResponseCacheService:
    """
    Service for caching API responses.
    """
    
    def __init__(self):
        self.cache_service = CacheService()
        self.api_timeout = 300  # 5 minutes
    
    def get_api_cache_key(self, request):
        """
        Generate cache key for API request.
        """
        # Include path, query parameters, and user info
        key_parts = [
            'api',
            request.path,
            request.method,
        ]
        
        # Add query parameters (sorted for consistency)
        if request.GET:
            query_params = sorted(request.GET.items())
            key_parts.append(json.dumps(query_params))
        
        # Add user ID for user-specific responses
        if request.user.is_authenticated:
            key_parts.append(f"user:{request.user.id}")
        else:
            key_parts.append("anonymous")
        
        return self.cache_service.get_cache_key(key_parts)
    
    def cache_api_response(self, request, response_data, timeout=None):
        """
        Cache API response.
        """
        if timeout is None:
            timeout = self.api_timeout
        
        cache_key = self.get_api_cache_key(request)
        
        # Add timestamp to cached data
        cached_data = {
            'data': response_data,
            'cached_at': timezone.now().isoformat(),
            'expires_at': (timezone.now() + timedelta(seconds=timeout)).isoformat()
        }
        
        self.cache_service.set_cache(cache_key, cached_data, timeout)
    
    def get_cached_api_response(self, request):
        """
        Get cached API response.
        """
        cache_key = self.get_api_cache_key(request)
        return self.cache_service.get_cache(cache_key)


def cache_result(timeout=300, key_prefix='result'):
    """
    Decorator for caching function results.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_service = CacheService()
            
            # Generate cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            
            # Add args to key
            for arg in args:
                if hasattr(arg, 'id'):
                    key_parts.append(f"{arg.__class__.__name__}:{arg.id}")
                else:
                    key_parts.append(str(arg))
            
            # Add kwargs to key (sorted for consistency)
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}:{v}")
            
            cache_key = cache_service.get_cache_key(key_parts)
            
            # Check cache
            cached_result = cache_service.get_cache(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_service.set_cache(cache_key, result, timeout)
            
            return result
        
        return wrapper
    return decorator


def cache_queryset(timeout=600, key_prefix='queryset'):
    """
    Decorator for caching queryset results.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_service = CacheService()
            
            # Generate cache key
            key_parts = [key_prefix, func.__name__]
            
            # Add args and kwargs to key
            for arg in args:
                if hasattr(arg, 'id'):
                    key_parts.append(f"{arg.__class__.__name__}:{arg.id}")
                else:
                    key_parts.append(str(arg))
            
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}:{v}")
            
            cache_key = cache_service.get_cache_key(key_parts)
            
            # Check cache
            cached_result = cache_service.get_cache(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            queryset = func(*args, **kwargs)
            
            # Convert queryset to list for caching
            if hasattr(queryset, 'values'):
                result = list(queryset.values())
            else:
                result = list(queryset)
            
            cache_service.set_cache(cache_key, result, timeout)
            
            return result
        
        return wrapper
    return decorator


class SessionCacheService:
    """
    Service for caching session data.
    """
    
    def __init__(self):
        self.cache_service = CacheService()
        self.session_timeout = 3600  # 1 hour
    
    def cache_user_session_data(self, user_id, data, timeout=None):
        """
        Cache user session data.
        """
        if timeout is None:
            timeout = self.session_timeout
        
        cache_key = self.cache_service.get_cache_key(['session', 'user', user_id])
        self.cache_service.set_cache(cache_key, data, timeout)
    
    def get_user_session_data(self, user_id):
        """
        Get cached user session data.
        """
        cache_key = self.cache_service.get_cache_key(['session', 'user', user_id])
        return self.cache_service.get_cache(cache_key)
    
    def invalidate_user_session(self, user_id):
        """
        Invalidate user session cache.
        """
        cache_key = self.cache_service.get_cache_key(['session', 'user', user_id])
        self.cache_service.delete_cache(cache_key)


class CacheInvalidationService:
    """
    Service for intelligent cache invalidation.
    """
    
    def __init__(self):
        self.cache_service = CacheService()
    
    def invalidate_on_model_change(self, model_instance, action='update'):
        """
        Invalidate relevant caches when model changes.
        """
        model_name = model_instance.__class__.__name__.lower()
        
        # Invalidate model instance cache
        cache_key = self.cache_service.get_cache_key(
            ['model', model_name, model_instance.id],
            'instance'
        )
        self.cache_service.delete_cache(cache_key)
        
        # Model-specific invalidation
        if model_name == 'product':
            self._invalidate_product_caches(model_instance)
        elif model_name == 'order':
            self._invalidate_order_caches(model_instance)
        elif model_name == 'user':
            self._invalidate_user_caches(model_instance)
    
    def _invalidate_product_caches(self, product):
        """Invalidate product-related caches."""
        patterns = [
            f"product:{product.id}:*",
            "products:*",
            "search:*",
            f"farmer:{product.farmer.id}:products:*",
            f"category:{product.categories.first().id if product.categories.exists() else 'none'}:*",
        ]
        
        for pattern in patterns:
            self.cache_service.delete_pattern(pattern)
    
    def _invalidate_order_caches(self, order):
        """Invalidate order-related caches."""
        patterns = [
            f"order:{order.id}:*",
            f"user:{order.buyer.id}:orders:*",
            f"farmer:{order.farmer.id}:orders:*",
            "orders:*",
        ]
        
        for pattern in patterns:
            self.cache_service.delete_pattern(pattern)
    
    def _invalidate_user_caches(self, user):
        """Invalidate user-related caches."""
        patterns = [
            f"user:{user.id}:*",
            f"farmer:{user.id}:*" if user.user_type == 'Farmer' else f"buyer:{user.id}:*",
        ]
        
        for pattern in patterns:
            self.cache_service.delete_pattern(pattern)
