"""
Custom permissions for Farm2Market API.
"""
from rest_framework import permissions
from django.contrib.auth import get_user_model

User = get_user_model()


class IsFarmer(permissions.BasePermission):
    """
    Permission to only allow farmers to access the view.
    """
    message = "You must be a farmer to access this resource."
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.user_type == 'Farmer' and
            request.user.is_approved
        )


class IsBuyer(permissions.BasePermission):
    """
    Permission to only allow buyers to access the view.
    """
    message = "You must be a buyer to access this resource."
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.user_type == 'Buyer' and
            request.user.is_approved
        )


class IsAdmin(permissions.BasePermission):
    """
    Permission to only allow admin users to access the view.
    """
    message = "You must be an admin to access this resource."
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.user_type == 'Admin' and
            (request.user.is_staff or request.user.is_superuser)
        )


class IsFarmerOrBuyer(permissions.BasePermission):
    """
    Permission to allow both farmers and buyers to access the view.
    """
    message = "You must be a farmer or buyer to access this resource."
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.user_type in ['Farmer', 'Buyer'] and
            request.user.is_approved
        )


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    Assumes the model instance has an `owner` attribute.
    """
    message = "You can only modify your own resources."
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner of the object.
        return obj.owner == request.user


class IsOwnerOrAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow owners and admins to edit objects.
    """
    message = "You can only modify your own resources or you must be an admin."
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are allowed to the owner or admin
        return (
            obj.owner == request.user or
            (request.user.user_type == 'Admin' and request.user.is_staff)
        )


class IsProfileOwner(permissions.BasePermission):
    """
    Permission to only allow users to access their own profile.
    """
    message = "You can only access your own profile."
    
    def has_object_permission(self, request, view, obj):
        # Check if the object has a user attribute (for profiles)
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # Check if the object has a farmer/buyer/admin attribute (for profiles)
        if hasattr(obj, 'farmer'):
            return obj.farmer == request.user
        if hasattr(obj, 'buyer'):
            return obj.buyer == request.user
        if hasattr(obj, 'admin'):
            return obj.admin == request.user
        
        # Default to checking if the object itself is the user
        return obj == request.user


class IsApprovedUser(permissions.BasePermission):
    """
    Permission to only allow approved users to access the view.
    """
    message = "Your account must be approved to access this resource."
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (request.user.is_approved or request.user.user_type == 'Admin')
        )


class IsEmailVerified(permissions.BasePermission):
    """
    Permission to only allow users with verified email to access the view.
    """
    message = "You must verify your email address to access this resource."
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (request.user.email_verified or request.user.user_type == 'Admin')
        )


class IsActiveUser(permissions.BasePermission):
    """
    Permission to only allow active users to access the view.
    """
    message = "Your account is inactive."
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_active and
            not request.user.is_account_locked
        )


class CanCreateProduct(permissions.BasePermission):
    """
    Permission to allow only farmers to create products.
    """
    message = "Only farmers can create products."
    
    def has_permission(self, request, view):
        if request.method == 'POST':
            return (
                request.user and
                request.user.is_authenticated and
                request.user.user_type == 'Farmer' and
                request.user.is_approved and
                request.user.email_verified
            )
        return True


class CanPlaceOrder(permissions.BasePermission):
    """
    Permission to allow only buyers to place orders.
    """
    message = "Only buyers can place orders."
    
    def has_permission(self, request, view):
        if request.method == 'POST':
            return (
                request.user and
                request.user.is_authenticated and
                request.user.user_type == 'Buyer' and
                request.user.is_approved and
                request.user.email_verified
            )
        return True


class CanModerateContent(permissions.BasePermission):
    """
    Permission to allow only admins to moderate content.
    """
    message = "Only admins can moderate content."
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.user_type == 'Admin' and
            request.user.is_staff
        )
