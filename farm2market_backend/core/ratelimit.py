"""
Rate limiting utilities for Farm2Market API.
"""
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
import hashlib


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    pass


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_rate_limit_key(request, key_func=None):
    """Generate rate limit key for caching."""
    if key_func:
        return key_func(request)
    
    # Default: use IP address
    ip = get_client_ip(request)
    return f"rate_limit_{ip}"


def rate_limit(rate='60/h', key_func=None, methods=['POST'], block=True):
    """
    Rate limiting decorator.
    
    Args:
        rate: Rate limit in format 'count/period' (e.g., '60/h', '10/m', '100/d')
        key_func: Function to generate cache key
        methods: HTTP methods to apply rate limiting
        block: Whether to block request or just log
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check if method should be rate limited
            if request.method not in methods:
                return view_func(request, *args, **kwargs)
            
            # Parse rate limit
            count, period = rate.split('/')
            count = int(count)
            
            # Convert period to seconds
            period_seconds = {
                's': 1,
                'm': 60,
                'h': 3600,
                'd': 86400
            }.get(period, 3600)
            
            # Generate cache key
            cache_key = get_rate_limit_key(request, key_func)
            
            # Get current count
            current_count = cache.get(cache_key, 0)
            
            if current_count >= count:
                if block:
                    return JsonResponse({
                        'success': False,
                        'error': {
                            'code': 'rate_limit_exceeded',
                            'message': f'Rate limit exceeded. Maximum {count} requests per {period}.',
                            'details': {
                                'limit': count,
                                'period': period,
                                'retry_after': period_seconds
                            }
                        },
                        'data': None
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)
                else:
                    # Just log the violation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Rate limit exceeded for {cache_key}")
            
            # Increment counter
            cache.set(cache_key, current_count + 1, timeout=period_seconds)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def auth_rate_limit(request):
    """Rate limit key for authentication endpoints."""
    ip = get_client_ip(request)
    return f"auth_rate_limit_{ip}"


def user_rate_limit(request):
    """Rate limit key per user."""
    if request.user.is_authenticated:
        return f"user_rate_limit_{request.user.id}"
    return get_rate_limit_key(request)


def email_rate_limit(request):
    """Rate limit key for email-based operations."""
    email = request.data.get('email', '')
    if email:
        email_hash = hashlib.md5(email.encode()).hexdigest()
        return f"email_rate_limit_{email_hash}"
    return get_rate_limit_key(request)


class RateLimitMiddleware:
    """
    Middleware for global rate limiting.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Apply global rate limiting
        ip = get_client_ip(request)
        cache_key = f"global_rate_limit_{ip}"
        
        # Global limit: 1000 requests per hour
        current_count = cache.get(cache_key, 0)
        if current_count >= 1000:
            return JsonResponse({
                'success': False,
                'error': {
                    'code': 'global_rate_limit_exceeded',
                    'message': 'Global rate limit exceeded. Please try again later.',
                    'details': {
                        'limit': 1000,
                        'period': 'hour',
                        'retry_after': 3600
                    }
                },
                'data': None
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Increment counter
        cache.set(cache_key, current_count + 1, timeout=3600)
        
        response = self.get_response(request)
        return response


# Predefined rate limit decorators
login_rate_limit = rate_limit(rate='5/m', key_func=auth_rate_limit, methods=['POST'])
register_rate_limit = rate_limit(rate='3/m', key_func=auth_rate_limit, methods=['POST'])
password_reset_rate_limit = rate_limit(rate='3/h', key_func=email_rate_limit, methods=['POST'])
email_verification_rate_limit = rate_limit(rate='5/h', key_func=user_rate_limit, methods=['POST'])
sms_rate_limit = rate_limit(rate='3/h', key_func=user_rate_limit, methods=['POST'])


def apply_rate_limits(view_class):
    """
    Class decorator to apply rate limits to view methods.
    """
    # Apply rate limits based on view name
    view_name = view_class.__name__.lower()
    
    if 'login' in view_name:
        view_class.post = login_rate_limit(view_class.post)
    elif 'register' in view_name:
        view_class.post = register_rate_limit(view_class.post)
    elif 'passwordreset' in view_name:
        view_class.post = password_reset_rate_limit(view_class.post)
    elif 'emailverification' in view_name or 'resendemail' in view_name:
        view_class.post = email_verification_rate_limit(view_class.post)
    elif 'sms' in view_name:
        view_class.post = sms_rate_limit(view_class.post)
    
    return view_class
