"""
Views for farmer management.
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
from apps.users.permissions import IsFarmer, IsOwnerOrReadOnly, IsProfileOwner
from apps.users.models import FarmerProfile
from .models import FarmCertification, FarmImage, FarmLocation
from .serializers import (
    FarmerProfileSerializer, FarmCertificationSerializer, FarmImageSerializer,
    FarmLocationSerializer, ProductSerializer, CategorySerializer,
    ProductImageSerializer, StockMovementSerializer, StockAdjustmentSerializer,
    LowStockAlertSerializer, InventorySettingsSerializer
)
from apps.products.models import Product, Category, ProductImage, StockMovement, LowStockAlert, InventorySettings

User = get_user_model()


class FarmerProfileView(generics.RetrieveUpdateAPIView):
    """
    Farmer profile management.
    """
    serializer_class = FarmerProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsFarmer, IsProfileOwner]
    
    def get_object(self):
        farmer_profile, created = FarmerProfile.objects.get_or_create(
            farmer=self.request.user
        )
        return farmer_profile
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return StandardResponse.success(
            data=serializer.data,
            message='Farmer profile retrieved successfully.'
        )
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            self.perform_update(serializer)
            return StandardResponse.updated(
                data=serializer.data,
                message='Farmer profile updated successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Profile update failed.'
        )


class FarmCertificationViewSet(ModelViewSet):
    """
    Farm certification management.
    """
    serializer_class = FarmCertificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsFarmer]
    
    def get_queryset(self):
        return FarmCertification.objects.filter(farmer=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(farmer=self.request.user)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return StandardResponse.created(
                data=serializer.data,
                message='Certification uploaded successfully. Pending verification.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Certification upload failed.'
        )
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Don't allow updates to verified certifications
        if instance.verification_status == 'verified':
            return StandardResponse.error(
                message='Cannot modify verified certifications.',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            self.perform_update(serializer)
            return StandardResponse.updated(
                data=serializer.data,
                message='Certification updated successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Certification update failed.'
        )


class FarmImageViewSet(ModelViewSet):
    """
    Farm image management.
    """
    serializer_class = FarmImageSerializer
    permission_classes = [permissions.IsAuthenticated, IsFarmer]
    
    def get_queryset(self):
        return FarmImage.objects.filter(farmer=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(farmer=self.request.user)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return StandardResponse.created(
                data=serializer.data,
                message='Farm image uploaded successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Image upload failed.'
        )


class FarmLocationViewSet(ModelViewSet):
    """
    Farm location management.
    """
    serializer_class = FarmLocationSerializer
    permission_classes = [permissions.IsAuthenticated, IsFarmer]
    
    def get_queryset(self):
        return FarmLocation.objects.filter(farmer=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(farmer=self.request.user)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return StandardResponse.created(
                data=serializer.data,
                message='Farm location added successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Location creation failed.'
        )


class FarmerProductViewSet(ModelViewSet):
    """
    Farmer product management.
    """
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated, IsFarmer]
    
    def get_queryset(self):
        return Product.objects.filter(farmer=self.request.user).select_related(
            'farmer', 'location'
        ).prefetch_related('categories', 'images')
    
    def perform_create(self, serializer):
        serializer.save(farmer=self.request.user)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            with transaction.atomic():
                self.perform_create(serializer)
                
                # Create initial stock movement
                StockMovement.objects.create(
                    product=serializer.instance,
                    movement_type='IN',
                    quantity=serializer.instance.quantity,
                    notes='Initial stock',
                    created_by=request.user,
                    stock_after=serializer.instance.quantity
                )
            
            return StandardResponse.created(
                data=serializer.data,
                message='Product created successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Product creation failed.'
        )
    
    @action(detail=True, methods=['post'])
    def upload_image(self, request, pk=None):
        """Upload product image."""
        product = self.get_object()
        
        serializer = ProductImageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(product=product)
            return StandardResponse.created(
                data=serializer.data,
                message='Product image uploaded successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Image upload failed.'
        )
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get all product categories."""
        categories = Category.objects.filter(is_active=True, parent=None)
        serializer = CategorySerializer(categories, many=True)
        return StandardResponse.success(
            data=serializer.data,
            message='Categories retrieved successfully.'
        )


class FarmerInventoryView(APIView):
    """
    Farmer inventory overview.
    """
    permission_classes = [permissions.IsAuthenticated, IsFarmer]
    
    def get(self, request):
        """Get inventory overview."""
        products = Product.objects.filter(farmer=request.user)
        
        # Calculate inventory statistics
        total_products = products.count()
        in_stock_products = products.filter(quantity__gt=0).count()
        low_stock_products = sum(1 for p in products if p.is_low_stock)
        out_of_stock_products = products.filter(quantity=0).count()
        
        # Get recent stock movements
        recent_movements = StockMovement.objects.filter(
            product__farmer=request.user
        ).select_related('product').order_by('-created_at')[:10]
        
        # Get active low stock alerts
        active_alerts = LowStockAlert.objects.filter(
            product__farmer=request.user,
            status='active'
        ).select_related('product')
        
        data = {
            'statistics': {
                'total_products': total_products,
                'in_stock_products': in_stock_products,
                'low_stock_products': low_stock_products,
                'out_of_stock_products': out_of_stock_products,
            },
            'recent_movements': StockMovementSerializer(recent_movements, many=True).data,
            'active_alerts': LowStockAlertSerializer(active_alerts, many=True).data,
        }
        
        return StandardResponse.success(
            data=data,
            message='Inventory overview retrieved successfully.'
        )


class StockAdjustmentView(APIView):
    """
    Stock adjustment endpoint.
    """
    permission_classes = [permissions.IsAuthenticated, IsFarmer]
    
    def post(self, request):
        """Perform stock adjustment."""
        serializer = StockAdjustmentSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            with transaction.atomic():
                product_id = serializer.validated_data['product_id']
                adjustment_type = serializer.validated_data['adjustment_type']
                quantity = serializer.validated_data['quantity']
                notes = serializer.validated_data.get('notes', '')
                
                product = Product.objects.select_for_update().get(id=product_id)
                old_quantity = product.quantity
                
                # Calculate new quantity
                if adjustment_type == 'set':
                    new_quantity = quantity
                    movement_quantity = quantity - old_quantity
                elif adjustment_type == 'add':
                    new_quantity = old_quantity + quantity
                    movement_quantity = quantity
                else:  # subtract
                    new_quantity = max(0, old_quantity - quantity)
                    movement_quantity = -(old_quantity - new_quantity)
                
                # Update product quantity
                product.quantity = new_quantity
                product.save(update_fields=['quantity'])
                
                # Create stock movement record
                movement = StockMovement.objects.create(
                    product=product,
                    movement_type='ADJUSTMENT',
                    quantity=movement_quantity,
                    notes=notes or f'Stock {adjustment_type}',
                    created_by=request.user,
                    stock_after=new_quantity
                )
                
                # Check for low stock and create alert if needed
                if product.is_low_stock:
                    settings, _ = InventorySettings.objects.get_or_create(
                        farmer=request.user
                    )
                    if settings.auto_low_stock_alerts:
                        LowStockAlert.objects.get_or_create(
                            product=product,
                            status='active',
                            defaults={
                                'threshold_quantity': int(product.quantity * 0.1),
                                'current_quantity': product.quantity
                            }
                        )
                
                return StandardResponse.success(
                    data=StockMovementSerializer(movement).data,
                    message='Stock adjustment completed successfully.'
                )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Stock adjustment failed.'
        )


class StockMovementListView(generics.ListAPIView):
    """
    List stock movements for farmer's products.
    """
    serializer_class = StockMovementSerializer
    permission_classes = [permissions.IsAuthenticated, IsFarmer]

    def get_queryset(self):
        return StockMovement.objects.filter(
            product__farmer=self.request.user
        ).select_related('product', 'created_by').order_by('-created_at')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Add filtering by product
        product_id = request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)

        # Add filtering by movement type
        movement_type = request.query_params.get('movement_type')
        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return StandardResponse.success(
            data=serializer.data,
            message='Stock movements retrieved successfully.'
        )


class LowStockAlertViewSet(ModelViewSet):
    """
    Low stock alert management.
    """
    serializer_class = LowStockAlertSerializer
    permission_classes = [permissions.IsAuthenticated, IsFarmer]
    http_method_names = ['get', 'patch', 'delete']

    def get_queryset(self):
        return LowStockAlert.objects.filter(
            product__farmer=self.request.user
        ).select_related('product', 'acknowledged_by')

    @action(detail=True, methods=['patch'])
    def acknowledge(self, request, pk=None):
        """Acknowledge a low stock alert."""
        alert = self.get_object()
        alert.acknowledge(request.user)

        serializer = self.get_serializer(alert)
        return StandardResponse.updated(
            data=serializer.data,
            message='Alert acknowledged successfully.'
        )

    @action(detail=True, methods=['patch'])
    def resolve(self, request, pk=None):
        """Resolve a low stock alert."""
        alert = self.get_object()
        alert.resolve()

        serializer = self.get_serializer(alert)
        return StandardResponse.updated(
            data=serializer.data,
            message='Alert resolved successfully.'
        )


class InventorySettingsView(generics.RetrieveUpdateAPIView):
    """
    Inventory settings management.
    """
    serializer_class = InventorySettingsSerializer
    permission_classes = [permissions.IsAuthenticated, IsFarmer]

    def get_object(self):
        settings, created = InventorySettings.objects.get_or_create(
            farmer=self.request.user
        )
        return settings

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return StandardResponse.success(
            data=serializer.data,
            message='Inventory settings retrieved successfully.'
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if serializer.is_valid():
            self.perform_update(serializer)
            return StandardResponse.updated(
                data=serializer.data,
                message='Inventory settings updated successfully.'
            )

        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Settings update failed.'
        )
