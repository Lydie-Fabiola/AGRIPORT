"""
Views for buyer management.
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from apps.core.responses import StandardResponse
from apps.core.exceptions import ValidationError, NotFoundError, BusinessLogicError
from apps.users.permissions import IsBuyer, IsOwnerOrReadOnly, IsProfileOwner
from apps.users.models import BuyerProfile
from .models import BuyerAddress, BuyerPreferences, FavoriteFarmer, Wishlist
from .serializers import (
    BuyerProfileSerializer, BuyerAddressSerializer, BuyerPreferencesSerializer,
    FavoriteFarmerSerializer, WishlistSerializer
)

User = get_user_model()


class BuyerProfileView(generics.RetrieveUpdateAPIView):
    """
    Buyer profile management.
    """
    serializer_class = BuyerProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsBuyer, IsProfileOwner]
    
    def get_object(self):
        buyer_profile, created = BuyerProfile.objects.get_or_create(
            buyer=self.request.user
        )
        return buyer_profile
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return StandardResponse.success(
            data=serializer.data,
            message='Buyer profile retrieved successfully.'
        )
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            self.perform_update(serializer)
            return StandardResponse.updated(
                data=serializer.data,
                message='Buyer profile updated successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Profile update failed.'
        )


class BuyerPreferencesView(generics.RetrieveUpdateAPIView):
    """
    Buyer preferences management.
    """
    serializer_class = BuyerPreferencesSerializer
    permission_classes = [permissions.IsAuthenticated, IsBuyer]
    
    def get_object(self):
        preferences, created = BuyerPreferences.objects.get_or_create(
            buyer=self.request.user
        )
        return preferences
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return StandardResponse.success(
            data=serializer.data,
            message='Buyer preferences retrieved successfully.'
        )
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            self.perform_update(serializer)
            return StandardResponse.updated(
                data=serializer.data,
                message='Buyer preferences updated successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Preferences update failed.'
        )


class BuyerAddressViewSet(ModelViewSet):
    """
    Buyer address management.
    """
    serializer_class = BuyerAddressSerializer
    permission_classes = [permissions.IsAuthenticated, IsBuyer]
    
    def get_queryset(self):
        return BuyerAddress.objects.filter(buyer=self.request.user, is_active=True)
    
    def perform_create(self, serializer):
        serializer.save(buyer=self.request.user)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return StandardResponse.created(
                data=serializer.data,
                message='Address added successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Address creation failed.'
        )
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            self.perform_update(serializer)
            return StandardResponse.updated(
                data=serializer.data,
                message='Address updated successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Address update failed.'
        )
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Soft delete by setting is_active to False
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        
        return StandardResponse.success(
            message='Address deleted successfully.'
        )
    
    @action(detail=True, methods=['patch'])
    def set_default(self, request, pk=None):
        """Set address as default."""
        address = self.get_object()
        
        # Remove default from other addresses
        BuyerAddress.objects.filter(
            buyer=request.user,
            is_default=True
        ).exclude(id=address.id).update(is_default=False)
        
        # Set this address as default
        address.is_default = True
        address.save(update_fields=['is_default'])
        
        serializer = self.get_serializer(address)
        return StandardResponse.updated(
            data=serializer.data,
            message='Default address updated successfully.'
        )


class FavoriteFarmerViewSet(ModelViewSet):
    """
    Favorite farmer management.
    """
    serializer_class = FavoriteFarmerSerializer
    permission_classes = [permissions.IsAuthenticated, IsBuyer]
    http_method_names = ['get', 'post', 'delete']
    
    def get_queryset(self):
        return FavoriteFarmer.objects.filter(buyer=self.request.user).select_related(
            'farmer', 'farmer__farmer_profile'
        )
    
    def perform_create(self, serializer):
        serializer.save(buyer=self.request.user)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Check if farmer is already in favorites
            farmer_id = serializer.validated_data['farmer_id']
            if FavoriteFarmer.objects.filter(
                buyer=request.user,
                farmer_id=farmer_id
            ).exists():
                return StandardResponse.error(
                    message='Farmer is already in your favorites.',
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            self.perform_create(serializer)
            return StandardResponse.created(
                data=serializer.data,
                message='Farmer added to favorites successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Failed to add farmer to favorites.'
        )
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        farmer_name = instance.farmer.full_name
        self.perform_destroy(instance)
        
        return StandardResponse.success(
            message=f'{farmer_name} removed from favorites successfully.'
        )
    
    @action(detail=False, methods=['get'])
    def farmers_with_new_products(self, request):
        """Get favorite farmers with new products."""
        # Get favorite farmers
        favorite_farmers = self.get_queryset()
        
        # Get farmers with products added in the last 7 days
        from datetime import timedelta
        from django.utils import timezone
        from apps.products.models import Product
        
        week_ago = timezone.now() - timedelta(days=7)
        farmers_with_new_products = []
        
        for favorite in favorite_farmers:
            new_products_count = Product.objects.filter(
                farmer=favorite.farmer,
                created_at__gte=week_ago,
                status='Available'
            ).count()
            
            if new_products_count > 0:
                farmer_data = self.get_serializer(favorite).data
                farmer_data['new_products_count'] = new_products_count
                farmers_with_new_products.append(farmer_data)
        
        return StandardResponse.success(
            data=farmers_with_new_products,
            message='Favorite farmers with new products retrieved successfully.'
        )


class WishlistViewSet(ModelViewSet):
    """
    Wishlist management.
    """
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated, IsBuyer]
    
    def get_queryset(self):
        return Wishlist.objects.filter(buyer=self.request.user).select_related(
            'product', 'product__farmer'
        ).prefetch_related('product__images')
    
    def perform_create(self, serializer):
        serializer.save(buyer=self.request.user)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Check if product is already in wishlist
            product_id = serializer.validated_data['product_id']
            if Wishlist.objects.filter(
                buyer=request.user,
                product_id=product_id
            ).exists():
                return StandardResponse.error(
                    message='Product is already in your wishlist.',
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            self.perform_create(serializer)
            return StandardResponse.created(
                data=serializer.data,
                message='Product added to wishlist successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Failed to add product to wishlist.'
        )
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            self.perform_update(serializer)
            return StandardResponse.updated(
                data=serializer.data,
                message='Wishlist item updated successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Wishlist update failed.'
        )
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        product_name = instance.product.product_name
        self.perform_destroy(instance)
        
        return StandardResponse.success(
            message=f'{product_name} removed from wishlist successfully.'
        )
    
    @action(detail=False, methods=['get'])
    def available_items(self, request):
        """Get wishlist items that are currently available."""
        available_items = self.get_queryset().filter(
            product__status='Available',
            product__quantity__gt=0
        )
        
        serializer = self.get_serializer(available_items, many=True)
        return StandardResponse.success(
            data=serializer.data,
            message='Available wishlist items retrieved successfully.'
        )
    
    @action(detail=False, methods=['get'])
    def price_targets_met(self, request):
        """Get wishlist items where price targets are met."""
        items_with_targets = self.get_queryset().exclude(target_price__isnull=True)
        price_targets_met = []
        
        for item in items_with_targets:
            if item.is_price_target_met:
                price_targets_met.append(item)
        
        serializer = self.get_serializer(price_targets_met, many=True)
        return StandardResponse.success(
            data=serializer.data,
            message='Wishlist items with met price targets retrieved successfully.'
        )
