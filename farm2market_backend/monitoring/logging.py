"""
Structured logging and monitoring for Farm2Market.
"""
import json
import logging
import traceback
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
import structlog

User = get_user_model()


class StructuredLogger:
    """
    Structured logging service with context management.
    """
    
    def __init__(self, name=None):
        self.logger = structlog.get_logger(name or __name__)
        self.context = {}
    
    def add_context(self, **kwargs):
        """Add context to all log messages."""
        self.context.update(kwargs)
        return self
    
    def clear_context(self):
        """Clear logging context."""
        self.context = {}
        return self
    
    def info(self, message, **kwargs):
        """Log info message with context."""
        self.logger.info(message, **{**self.context, **kwargs})
    
    def warning(self, message, **kwargs):
        """Log warning message with context."""
        self.logger.warning(message, **{**self.context, **kwargs})
    
    def error(self, message, **kwargs):
        """Log error message with context."""
        self.logger.error(message, **{**self.context, **kwargs})
    
    def critical(self, message, **kwargs):
        """Log critical message with context."""
        self.logger.critical(message, **{**self.context, **kwargs})
    
    def debug(self, message, **kwargs):
        """Log debug message with context."""
        self.logger.debug(message, **{**self.context, **kwargs})


class SecurityLogger:
    """
    Specialized logger for security events.
    """
    
    def __init__(self):
        self.logger = StructuredLogger('security')
    
    def log_authentication_event(self, event_type, user=None, ip_address=None, 
                                user_agent=None, success=True, **kwargs):
        """Log authentication events."""
        self.logger.add_context(
            event_category='authentication',
            event_type=event_type,
            user_id=user.id if user else None,
            user_email=user.email if user else None,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            timestamp=timezone.now().isoformat()
        ).info(f"Authentication event: {event_type}", **kwargs)
    
    def log_authorization_event(self, event_type, user=None, resource=None, 
                              action=None, success=True, **kwargs):
        """Log authorization events."""
        self.logger.add_context(
            event_category='authorization',
            event_type=event_type,
            user_id=user.id if user else None,
            resource=resource,
            action=action,
            success=success,
            timestamp=timezone.now().isoformat()
        ).info(f"Authorization event: {event_type}", **kwargs)
    
    def log_data_access_event(self, event_type, user=None, data_type=None, 
                            record_id=None, **kwargs):
        """Log data access events."""
        self.logger.add_context(
            event_category='data_access',
            event_type=event_type,
            user_id=user.id if user else None,
            data_type=data_type,
            record_id=record_id,
            timestamp=timezone.now().isoformat()
        ).info(f"Data access event: {event_type}", **kwargs)
    
    def log_security_violation(self, violation_type, severity='medium', 
                             user=None, ip_address=None, **kwargs):
        """Log security violations."""
        self.logger.add_context(
            event_category='security_violation',
            violation_type=violation_type,
            severity=severity,
            user_id=user.id if user else None,
            ip_address=ip_address,
            timestamp=timezone.now().isoformat()
        ).error(f"Security violation: {violation_type}", **kwargs)


class PerformanceLogger:
    """
    Logger for performance monitoring.
    """
    
    def __init__(self):
        self.logger = StructuredLogger('performance')
    
    def log_request_performance(self, request, response, duration, **kwargs):
        """Log request performance metrics."""
        self.logger.add_context(
            event_category='request_performance',
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
            user_id=request.user.id if request.user.is_authenticated else None,
            timestamp=timezone.now().isoformat()
        ).info(f"Request completed: {request.method} {request.path}", **kwargs)
    
    def log_database_performance(self, query_count, duration, operation=None, **kwargs):
        """Log database performance metrics."""
        self.logger.add_context(
            event_category='database_performance',
            query_count=query_count,
            duration_ms=round(duration * 1000, 2),
            operation=operation,
            timestamp=timezone.now().isoformat()
        ).info(f"Database operation completed: {operation}", **kwargs)
    
    def log_cache_performance(self, operation, hit=True, duration=None, **kwargs):
        """Log cache performance metrics."""
        self.logger.add_context(
            event_category='cache_performance',
            operation=operation,
            cache_hit=hit,
            duration_ms=round(duration * 1000, 2) if duration else None,
            timestamp=timezone.now().isoformat()
        ).info(f"Cache operation: {operation}", **kwargs)


class BusinessLogger:
    """
    Logger for business events and metrics.
    """
    
    def __init__(self):
        self.logger = StructuredLogger('business')
    
    def log_order_event(self, event_type, order, user=None, **kwargs):
        """Log order-related events."""
        self.logger.add_context(
            event_category='order',
            event_type=event_type,
            order_id=order.id,
            order_number=order.order_number,
            buyer_id=order.buyer.id,
            farmer_id=order.farmer.id,
            total_amount=float(order.total_amount),
            status=order.status,
            user_id=user.id if user else None,
            timestamp=timezone.now().isoformat()
        ).info(f"Order event: {event_type}", **kwargs)
    
    def log_product_event(self, event_type, product, user=None, **kwargs):
        """Log product-related events."""
        self.logger.add_context(
            event_category='product',
            event_type=event_type,
            product_id=product.id,
            product_name=product.product_name,
            farmer_id=product.farmer.id,
            price=float(product.price),
            status=product.status,
            user_id=user.id if user else None,
            timestamp=timezone.now().isoformat()
        ).info(f"Product event: {event_type}", **kwargs)
    
    def log_user_event(self, event_type, user, **kwargs):
        """Log user-related events."""
        self.logger.add_context(
            event_category='user',
            event_type=event_type,
            user_id=user.id,
            user_type=user.user_type,
            user_email=user.email,
            timestamp=timezone.now().isoformat()
        ).info(f"User event: {event_type}", **kwargs)
    
    def log_payment_event(self, event_type, order, amount, payment_method=None, **kwargs):
        """Log payment-related events."""
        self.logger.add_context(
            event_category='payment',
            event_type=event_type,
            order_id=order.id,
            order_number=order.order_number,
            amount=float(amount),
            payment_method=payment_method,
            buyer_id=order.buyer.id,
            farmer_id=order.farmer.id,
            timestamp=timezone.now().isoformat()
        ).info(f"Payment event: {event_type}", **kwargs)


class ErrorLogger:
    """
    Logger for error tracking and monitoring.
    """
    
    def __init__(self):
        self.logger = StructuredLogger('error')
    
    def log_exception(self, exception, request=None, user=None, **kwargs):
        """Log exceptions with full context."""
        error_context = {
            'event_category': 'exception',
            'exception_type': exception.__class__.__name__,
            'exception_message': str(exception),
            'traceback': traceback.format_exc(),
            'timestamp': timezone.now().isoformat()
        }
        
        if request:
            error_context.update({
                'request_method': request.method,
                'request_path': request.path,
                'request_query': dict(request.GET),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'ip_address': self._get_client_ip(request)
            })
        
        if user:
            error_context.update({
                'user_id': user.id,
                'user_email': user.email,
                'user_type': user.user_type
            })
        
        self.logger.add_context(**error_context).error(
            f"Exception occurred: {exception.__class__.__name__}", **kwargs
        )
    
    def log_validation_error(self, errors, request=None, user=None, **kwargs):
        """Log validation errors."""
        self.logger.add_context(
            event_category='validation_error',
            validation_errors=errors,
            request_path=request.path if request else None,
            user_id=user.id if user else None,
            timestamp=timezone.now().isoformat()
        ).warning("Validation error occurred", **kwargs)
    
    def log_api_error(self, error_code, message, request=None, **kwargs):
        """Log API errors."""
        self.logger.add_context(
            event_category='api_error',
            error_code=error_code,
            error_message=message,
            request_method=request.method if request else None,
            request_path=request.path if request else None,
            timestamp=timezone.now().isoformat()
        ).error(f"API error: {error_code}", **kwargs)
    
    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PIIFilter:
    """
    Filter to remove PII from log messages.
    """
    
    def __init__(self):
        self.pii_fields = [
            'password', 'email', 'phone', 'address', 'ssn', 'credit_card',
            'bank_account', 'passport', 'license', 'personal_id'
        ]
    
    def filter_pii(self, data):
        """Remove or mask PII from data."""
        if isinstance(data, dict):
            filtered_data = {}
            for key, value in data.items():
                if any(pii_field in key.lower() for pii_field in self.pii_fields):
                    filtered_data[key] = self._mask_value(value)
                elif isinstance(value, (dict, list)):
                    filtered_data[key] = self.filter_pii(value)
                else:
                    filtered_data[key] = value
            return filtered_data
        
        elif isinstance(data, list):
            return [self.filter_pii(item) for item in data]
        
        return data
    
    def _mask_value(self, value):
        """Mask sensitive values."""
        if isinstance(value, str):
            if len(value) <= 4:
                return '*' * len(value)
            else:
                return value[:2] + '*' * (len(value) - 4) + value[-2:]
        return '***'


class LoggingMiddleware:
    """
    Middleware for automatic request/response logging.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.performance_logger = PerformanceLogger()
        self.error_logger = ErrorLogger()
    
    def __call__(self, request):
        start_time = timezone.now()
        
        try:
            response = self.get_response(request)
            
            # Log successful requests
            duration = (timezone.now() - start_time).total_seconds()
            
            if duration > 1.0:  # Log slow requests
                self.performance_logger.log_request_performance(
                    request, response, duration,
                    slow_request=True
                )
            
            return response
            
        except Exception as e:
            # Log exceptions
            self.error_logger.log_exception(e, request=request, user=request.user if hasattr(request, 'user') else None)
            raise


# Configure structlog
def configure_structlog():
    """Configure structlog for structured logging."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


# Initialize structured logging
configure_structlog()

# Create logger instances
security_logger = SecurityLogger()
performance_logger = PerformanceLogger()
business_logger = BusinessLogger()
error_logger = ErrorLogger()
