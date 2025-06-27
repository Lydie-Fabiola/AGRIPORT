"""
Standardized API response utilities for Farm2Market API.
"""
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.utils.translation import gettext_lazy as _


class StandardResponse:
    """
    Utility class for creating standardized API responses.
    """
    
    @staticmethod
    def success(data=None, message=None, status_code=status.HTTP_200_OK, meta=None):
        """
        Create a successful response.
        
        Args:
            data: Response data
            message: Success message
            status_code: HTTP status code
            meta: Additional metadata
        """
        response_data = {
            'success': True,
            'message': message or _('Operation successful.'),
            'data': data,
            'error': None
        }
        
        if meta:
            response_data['meta'] = meta
            
        return Response(response_data, status=status_code)
    
    @staticmethod
    def error(message, code='error', status_code=status.HTTP_400_BAD_REQUEST, details=None):
        """
        Create an error response.
        
        Args:
            message: Error message
            code: Error code
            status_code: HTTP status code
            details: Additional error details
        """
        response_data = {
            'success': False,
            'message': None,
            'data': None,
            'error': {
                'code': code,
                'message': str(message),
                'details': details or {}
            }
        }
        
        return Response(response_data, status=status_code)
    
    @staticmethod
    def created(data=None, message=None):
        """
        Create a 201 Created response.
        """
        return StandardResponse.success(
            data=data,
            message=message or _('Resource created successfully.'),
            status_code=status.HTTP_201_CREATED
        )
    
    @staticmethod
    def updated(data=None, message=None):
        """
        Create a 200 OK response for updates.
        """
        return StandardResponse.success(
            data=data,
            message=message or _('Resource updated successfully.'),
            status_code=status.HTTP_200_OK
        )
    
    @staticmethod
    def deleted(message=None):
        """
        Create a 204 No Content response for deletions.
        """
        return StandardResponse.success(
            data=None,
            message=message or _('Resource deleted successfully.'),
            status_code=status.HTTP_204_NO_CONTENT
        )
    
    @staticmethod
    def not_found(message=None):
        """
        Create a 404 Not Found response.
        """
        return StandardResponse.error(
            message=message or _('Resource not found.'),
            code='not_found',
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    @staticmethod
    def unauthorized(message=None):
        """
        Create a 401 Unauthorized response.
        """
        return StandardResponse.error(
            message=message or _('Authentication required.'),
            code='unauthorized',
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    @staticmethod
    def forbidden(message=None):
        """
        Create a 403 Forbidden response.
        """
        return StandardResponse.error(
            message=message or _('Permission denied.'),
            code='forbidden',
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    @staticmethod
    def validation_error(errors, message=None):
        """
        Create a 400 Bad Request response for validation errors.
        """
        return StandardResponse.error(
            message=message or _('Validation failed.'),
            code='validation_error',
            status_code=status.HTTP_400_BAD_REQUEST,
            details=errors
        )


class StandardPagination(PageNumberPagination):
    """
    Custom pagination class with standardized response format.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        """
        Return a paginated style Response object with standardized format.
        """
        return StandardResponse.success(
            data=data,
            meta={
                'pagination': {
                    'page': self.page.number,
                    'page_size': self.page.paginator.per_page,
                    'total_pages': self.page.paginator.num_pages,
                    'total_count': self.page.paginator.count,
                    'has_next': self.page.has_next(),
                    'has_previous': self.page.has_previous(),
                    'next_page': self.page.next_page_number() if self.page.has_next() else None,
                    'previous_page': self.page.previous_page_number() if self.page.has_previous() else None,
                }
            }
        )


class APIVersionMixin:
    """
    Mixin to handle API versioning.
    """
    
    def get_api_version(self):
        """
        Get the API version from the request.
        """
        return getattr(self.request, 'version', 'v1')
    
    def is_version(self, version):
        """
        Check if the current API version matches the given version.
        """
        return self.get_api_version() == version
