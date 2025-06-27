"""
Security middleware for Farm2Market.
"""
import json
import time
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.core.cache import cache
from .services import SecurityService, InputValidationService, RateLimitingService


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Add security headers to all responses.
    """
    
    def process_response(self, request, response):
        """Add security headers."""
        # Content Security Policy
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        
        # X-Frame-Options
        response['X-Frame-Options'] = 'DENY'
        
        # X-Content-Type-Options
        response['X-Content-Type-Options'] = 'nosniff'
        
        # X-XSS-Protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Strict Transport Security (HTTPS only)
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Permissions Policy
        response['Permissions-Policy'] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "speaker=()"
        )
        
        return response


class RateLimitMiddleware(MiddlewareMixin):
    """
    Rate limiting middleware.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limiting_service = RateLimitingService()
        self.security_service = SecurityService()
    
    def process_request(self, request):
        """Check rate limits before processing request."""
        # Skip rate limiting for certain paths
        if self._should_skip_rate_limiting(request):
            return None
        
        # Get identifier (IP address or user ID)
        identifier = self._get_identifier(request)
        endpoint = request.path
        
        # Check rate limit
        if self.rate_limiting_service.is_rate_limited(identifier, endpoint, request):
            return JsonResponse({
                'error': 'Rate limit exceeded. Please try again later.',
                'status': 'error'
            }, status=429)
        
        return None
    
    def _should_skip_rate_limiting(self, request):
        """Determine if rate limiting should be skipped."""
        # Skip for static files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return True
        
        # Skip for health checks
        if request.path in ['/health/', '/ping/']:
            return True
        
        return False
    
    def _get_identifier(self, request):
        """Get identifier for rate limiting."""
        if request.user.is_authenticated:
            return f"user:{request.user.id}"
        else:
            return f"ip:{self._get_client_ip(request)}"
    
    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class InputValidationMiddleware(MiddlewareMixin):
    """
    Validate and sanitize input data.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.validation_service = InputValidationService()
        self.security_service = SecurityService()
    
    def process_request(self, request):
        """Validate input data."""
        # Skip validation for certain content types
        if self._should_skip_validation(request):
            return None
        
        # Validate query parameters
        if request.GET:
            validation_result = self._validate_query_params(request)
            if not validation_result['is_valid']:
                self._log_security_violation(request, 'query_params', validation_result['issues'])
                return JsonResponse({
                    'error': 'Invalid input detected.',
                    'status': 'error'
                }, status=400)
        
        # Validate POST/PUT data
        if request.method in ['POST', 'PUT', 'PATCH'] and request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                validation_result = self._validate_json_data(data)
                if not validation_result['is_valid']:
                    self._log_security_violation(request, 'json_data', validation_result['issues'])
                    return JsonResponse({
                        'error': 'Invalid input detected.',
                        'status': 'error'
                    }, status=400)
            except json.JSONDecodeError:
                pass  # Let Django handle invalid JSON
        
        return None
    
    def _should_skip_validation(self, request):
        """Determine if validation should be skipped."""
        # Skip for file uploads
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            return True
        
        # Skip for static files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return True
        
        return False
    
    def _validate_query_params(self, request):
        """Validate query parameters."""
        issues = []
        
        for key, value in request.GET.items():
            validation = self.validation_service.validate_input(value, f'query_param_{key}')
            if not validation['is_valid']:
                issues.extend(validation['issues'])
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues
        }
    
    def _validate_json_data(self, data, prefix=''):
        """Validate JSON data recursively."""
        issues = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                field_name = f"{prefix}.{key}" if prefix else key
                
                if isinstance(value, str):
                    validation = self.validation_service.validate_input(value, field_name)
                    if not validation['is_valid']:
                        issues.extend(validation['issues'])
                elif isinstance(value, (dict, list)):
                    nested_validation = self._validate_json_data(value, field_name)
                    if not nested_validation['is_valid']:
                        issues.extend(nested_validation['issues'])
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                field_name = f"{prefix}[{i}]" if prefix else f"item_{i}"
                
                if isinstance(item, str):
                    validation = self.validation_service.validate_input(item, field_name)
                    if not validation['is_valid']:
                        issues.extend(validation['issues'])
                elif isinstance(item, (dict, list)):
                    nested_validation = self._validate_json_data(item, field_name)
                    if not nested_validation['is_valid']:
                        issues.extend(nested_validation['issues'])
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues
        }
    
    def _log_security_violation(self, request, data_type, issues):
        """Log security violation."""
        self.security_service.log_security_event(
            event_type='data_breach_attempt',
            severity='high',
            description=f'Malicious input detected in {data_type}: {", ".join(issues)}',
            user=request.user if request.user.is_authenticated else None,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            metadata={
                'data_type': data_type,
                'issues': issues,
                'path': request.path,
                'method': request.method
            }
        )
    
    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CSRFProtectionMiddleware(MiddlewareMixin):
    """
    Enhanced CSRF protection middleware.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.security_service = SecurityService()
    
    def process_request(self, request):
        """Check CSRF token for state-changing requests."""
        # Skip for API endpoints using token authentication
        if request.path.startswith('/api/') and self._has_valid_auth_token(request):
            return None
        
        # Check CSRF for state-changing requests
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            if not self._verify_csrf_token(request):
                self._log_csrf_violation(request)
                return JsonResponse({
                    'error': 'CSRF token missing or invalid.',
                    'status': 'error'
                }, status=403)
        
        return None
    
    def _has_valid_auth_token(self, request):
        """Check if request has valid authentication token."""
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        return auth_header.startswith('Bearer ') or auth_header.startswith('Token ')
    
    def _verify_csrf_token(self, request):
        """Verify CSRF token."""
        # Get CSRF token from header or form data
        csrf_token = (
            request.META.get('HTTP_X_CSRFTOKEN') or
            request.POST.get('csrfmiddlewaretoken') or
            request.META.get('HTTP_X_CSRF_TOKEN')
        )
        
        if not csrf_token:
            return False
        
        # Get expected token from session/cookie
        expected_token = request.META.get('CSRF_COOKIE')
        
        return csrf_token == expected_token
    
    def _log_csrf_violation(self, request):
        """Log CSRF violation."""
        self.security_service.log_security_event(
            event_type='permission_denied',
            severity='medium',
            description='CSRF token missing or invalid',
            user=request.user if request.user.is_authenticated else None,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            metadata={
                'path': request.path,
                'method': request.method,
                'referer': request.META.get('HTTP_REFERER', '')
            }
        )
    
    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityMonitoringMiddleware(MiddlewareMixin):
    """
    Monitor requests for suspicious activity.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.security_service = SecurityService()
    
    def process_request(self, request):
        """Monitor request for suspicious patterns."""
        # Store request start time
        request._security_start_time = time.time()
        
        # Check for suspicious patterns
        if self._is_suspicious_request(request):
            self._log_suspicious_activity(request)
        
        return None
    
    def process_response(self, request, response):
        """Monitor response for security issues."""
        # Calculate request duration
        if hasattr(request, '_security_start_time'):
            duration = time.time() - request._security_start_time
            
            # Log slow requests (potential DoS)
            if duration > 10:  # 10 seconds
                self.security_service.log_security_event(
                    event_type='suspicious_activity',
                    severity='medium',
                    description=f'Slow request detected: {duration:.2f}s',
                    user=request.user if request.user.is_authenticated else None,
                    ip_address=self._get_client_ip(request),
                    metadata={
                        'path': request.path,
                        'method': request.method,
                        'duration': duration
                    }
                )
        
        return response
    
    def _is_suspicious_request(self, request):
        """Check if request shows suspicious patterns."""
        # Check for suspicious user agents
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        suspicious_agents = [
            'sqlmap', 'nikto', 'nmap', 'masscan', 'nessus',
            'burp', 'zap', 'w3af', 'havij', 'pangolin'
        ]
        
        if any(agent in user_agent for agent in suspicious_agents):
            return True
        
        # Check for suspicious paths
        suspicious_paths = [
            '/admin/', '/wp-admin/', '/phpmyadmin/', '/.env',
            '/config/', '/backup/', '/test/', '/debug/'
        ]
        
        if any(path in request.path.lower() for path in suspicious_paths):
            return True
        
        # Check for suspicious parameters
        query_string = request.META.get('QUERY_STRING', '').lower()
        suspicious_params = [
            'union', 'select', 'drop', 'insert', 'update',
            'script', 'alert', 'eval', 'exec'
        ]
        
        if any(param in query_string for param in suspicious_params):
            return True
        
        return False
    
    def _log_suspicious_activity(self, request):
        """Log suspicious activity."""
        self.security_service.log_security_event(
            event_type='suspicious_activity',
            severity='medium',
            description='Suspicious request pattern detected',
            user=request.user if request.user.is_authenticated else None,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            metadata={
                'path': request.path,
                'method': request.method,
                'query_string': request.META.get('QUERY_STRING', ''),
                'referer': request.META.get('HTTP_REFERER', '')
            }
        )
    
    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
