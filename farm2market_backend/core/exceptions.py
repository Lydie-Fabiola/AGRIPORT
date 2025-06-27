"""
Custom exception classes for the Farm2Market API.
"""
from rest_framework import status
from rest_framework.views import exception_handler
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)


class Farm2MarketException(Exception):
    """
    Base exception class for Farm2Market API.
    """
    default_message = _('An error occurred.')
    default_code = 'error'
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, message=None, code=None, status_code=None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        if status_code:
            self.status_code = status_code
        super().__init__(self.message)


class ValidationError(Farm2MarketException):
    """
    Exception for validation errors.
    """
    default_message = _('Validation failed.')
    default_code = 'validation_error'
    status_code = status.HTTP_400_BAD_REQUEST


class AuthenticationError(Farm2MarketException):
    """
    Exception for authentication errors.
    """
    default_message = _('Authentication failed.')
    default_code = 'authentication_error'
    status_code = status.HTTP_401_UNAUTHORIZED


class PermissionError(Farm2MarketException):
    """
    Exception for permission errors.
    """
    default_message = _('Permission denied.')
    default_code = 'permission_error'
    status_code = status.HTTP_403_FORBIDDEN


class NotFoundError(Farm2MarketException):
    """
    Exception for resource not found errors.
    """
    default_message = _('Resource not found.')
    default_code = 'not_found'
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(Farm2MarketException):
    """
    Exception for conflict errors.
    """
    default_message = _('Resource conflict.')
    default_code = 'conflict_error'
    status_code = status.HTTP_409_CONFLICT


class BusinessLogicError(Farm2MarketException):
    """
    Exception for business logic errors.
    """
    default_message = _('Business logic error.')
    default_code = 'business_logic_error'
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class ExternalServiceError(Farm2MarketException):
    """
    Exception for external service errors.
    """
    default_message = _('External service error.')
    default_code = 'external_service_error'
    status_code = status.HTTP_502_BAD_GATEWAY


class RateLimitError(Farm2MarketException):
    """
    Exception for rate limit errors.
    """
    default_message = _('Rate limit exceeded.')
    default_code = 'rate_limit_error'
    status_code = status.HTTP_429_TOO_MANY_REQUESTS


def custom_exception_handler(exc, context):
    """
    Custom exception handler for the API.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Handle DRF exceptions
        custom_response_data = {
            'success': False,
            'error': {
                'code': getattr(exc, 'default_code', 'error'),
                'message': str(exc),
                'details': response.data if isinstance(response.data, dict) else {'detail': response.data}
            },
            'data': None
        }
        response.data = custom_response_data

    elif isinstance(exc, Farm2MarketException):
        # Handle custom exceptions
        custom_response_data = {
            'success': False,
            'error': {
                'code': exc.code,
                'message': str(exc.message),
                'details': {}
            },
            'data': None
        }
        response = Response(custom_response_data, status=exc.status_code)

    else:
        # Handle unexpected exceptions
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        custom_response_data = {
            'success': False,
            'error': {
                'code': 'internal_server_error',
                'message': _('An unexpected error occurred.'),
                'details': {}
            },
            'data': None
        }
        response = Response(custom_response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response
