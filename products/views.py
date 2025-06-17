from django.shortcuts import render
from rest_framework import viewsets, permissions, filters
from .models import Product, Category
from .serializers import ProductSerializer, CategorySerializer
from users.permissions import IsFarmer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from notifications.models import Notification
from notifications.utils import send_notification_ws

# Create your views here.

class ProductPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().select_related('category', 'farmer')
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'status', 'is_organic', 'is_fresh_today', 'unit']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at']
    pagination_class = ProductPagination
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Product.objects.filter(status='available')
        # Only products from active farmers
        queryset = queryset.filter(farmer__user__is_active=True)
        # Filter by farmer if ?farmer=<id>
        farmer_id = self.request.query_params.get('farmer')
        if farmer_id:
            queryset = queryset.filter(farmer_id=farmer_id)
        # Price range filtering
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        # Location filtering (by farmer location)
        location = self.request.query_params.get('location')
        if location:
            queryset = queryset.filter(farmer__location__icontains=location)
        # Featured products logic (e.g., ?featured=true)
        featured = self.request.query_params.get('featured')
        if featured == 'true':
            queryset = queryset.order_by('-is_fresh_today', '-created_at')[:10]
        return queryset

    def perform_create(self, serializer):
        serializer.save(farmer=self.request.user.farmer_profile)

    def perform_update(self, serializer):
        instance = serializer.save(farmer=self.request.user.farmer_profile)
        # Notify buyers if product is restocked (quantity increased from 0)
        if 'quantity' in serializer.validated_data:
            old_quantity = self.get_object().quantity
            new_quantity = serializer.validated_data['quantity']
            if old_quantity == 0 and new_quantity > 0:
                # Notify all buyers with a reservation for this product
                from reservations.models import Reservation
                buyers = Reservation.objects.filter(product=instance, status__in=['pending', 'approved']).values_list('buyer', flat=True).distinct()
                for buyer_id in buyers:
                    Notification.objects.create(
                        user_id=buyer_id,
                        title='Product Available',
                        message=f'{instance.name} is now available.',
                        notification_type='product',
                        related_entity_type='product',
                        related_entity_id=instance.id
                    )
                    send_notification_ws(buyer_id, {
                        'title': 'Product Available',
                        'message': f'{instance.name} is now available.',
                        'notification_type': 'product',
                        'related_entity_type': 'product',
                        'related_entity_id': instance.id,
                    })

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsFarmer()]
        return [permissions.AllowAny()]
