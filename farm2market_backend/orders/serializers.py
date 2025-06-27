"""
Serializers for order management.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from .models import Order, OrderItem, OrderStatusHistory, Reservation, Cart, CartItem
from apps.products.models import Product
from apps.buyers.models import BuyerAddress

User = get_user_model()


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for order items.
    """
    product_name = serializers.ReadOnlyField()
    product_unit = serializers.ReadOnlyField()
    unit_price = serializers.ReadOnlyField()
    total_price = serializers.ReadOnlyField()
    
    # Product details for display
    product_details = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_name', 'product_unit', 'quantity',
            'unit_price', 'total_price', 'product_details', 'created_at'
        ]
        read_only_fields = ['product_name', 'product_unit', 'unit_price', 'total_price']
    
    def get_product_details(self, obj):
        """Get basic product details."""
        if obj.product:
            return {
                'id': obj.product.id,
                'name': obj.product.product_name,
                'farmer_name': obj.product.farmer.full_name,
                'current_price': obj.product.price,
                'available_quantity': obj.product.available_quantity,
            }
        return None


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for order status history.
    """
    changed_by_name = serializers.CharField(source='changed_by.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = OrderStatusHistory
        fields = [
            'id', 'status', 'status_display', 'notes', 'changed_by',
            'changed_by_name', 'timestamp'
        ]
        read_only_fields = ['changed_by', 'timestamp']


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer for orders.
    """
    buyer_name = serializers.CharField(source='buyer.full_name', read_only=True)
    farmer_name = serializers.CharField(source='farmer.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    
    # Calculated fields
    can_be_cancelled = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    
    # Delivery address details
    delivery_address_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'buyer', 'buyer_name', 'farmer', 'farmer_name',
            'status', 'status_display', 'order_type', 'order_type_display',
            'subtotal', 'delivery_fee', 'tax_amount', 'total_amount',
            'delivery_address', 'delivery_address_details', 'delivery_method',
            'preferred_delivery_date', 'actual_delivery_date', 'payment_method',
            'payment_method_display', 'payment_status', 'payment_status_display',
            'notes', 'estimated_preparation_time', 'tracking_number',
            'can_be_cancelled', 'is_completed', 'is_active', 'items',
            'status_history', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'order_number', 'buyer', 'farmer', 'subtotal', 'total_amount',
            'created_at', 'updated_at'
        ]
    
    def get_delivery_address_details(self, obj):
        """Get delivery address details."""
        if obj.delivery_address:
            return {
                'id': obj.delivery_address.id,
                'title': obj.delivery_address.title,
                'full_name': obj.delivery_address.full_name,
                'phone_number': obj.delivery_address.phone_number,
                'address_line_1': obj.delivery_address.address_line_1,
                'address_line_2': obj.delivery_address.address_line_2,
                'city': obj.delivery_address.city,
                'state': obj.delivery_address.state,
            }
        return None


class OrderCreateSerializer(serializers.Serializer):
    """
    Serializer for creating orders from cart.
    """
    delivery_address_id = serializers.IntegerField(required=True)
    delivery_method = serializers.ChoiceField(
        choices=Order.DELIVERY_METHOD_CHOICES,
        default='delivery'
    )
    payment_method = serializers.ChoiceField(
        choices=Order.PAYMENT_METHOD_CHOICES,
        default='cash'
    )
    preferred_delivery_date = serializers.DateTimeField(required=False)
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    
    def validate_delivery_address_id(self, value):
        """Validate delivery address belongs to user."""
        request = self.context.get('request')
        if request and request.user:
            try:
                address = BuyerAddress.objects.get(
                    id=value,
                    buyer=request.user,
                    is_active=True
                )
                return value
            except BuyerAddress.DoesNotExist:
                raise serializers.ValidationError("Invalid delivery address.")
        raise serializers.ValidationError("Authentication required.")


class ReservationSerializer(serializers.ModelSerializer):
    """
    Serializer for reservations.
    """
    buyer_name = serializers.CharField(source='buyer.full_name', read_only=True)
    farmer_name = serializers.CharField(source='farmer.full_name', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # Calculated fields
    is_expired = serializers.ReadOnlyField()
    can_be_accepted = serializers.ReadOnlyField()
    can_be_rejected = serializers.ReadOnlyField()
    final_price = serializers.ReadOnlyField()
    total_amount = serializers.ReadOnlyField()
    
    # Product details
    product_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Reservation
        fields = [
            'id', 'buyer', 'buyer_name', 'farmer', 'farmer_name', 'product',
            'product_name', 'product_details', 'quantity_requested', 'price_offered',
            'harvest_date_requested', 'pickup_delivery_date', 'status', 'status_display',
            'farmer_response', 'counter_offer_price', 'expires_at', 'buyer_notes',
            'total_amount', 'is_expired', 'can_be_accepted', 'can_be_rejected',
            'final_price', 'created_at', 'updated_at'
        ]
        read_only_fields = ['buyer', 'farmer', 'total_amount', 'created_at', 'updated_at']
    
    def get_product_details(self, obj):
        """Get product details."""
        if obj.product:
            return {
                'id': obj.product.id,
                'name': obj.product.product_name,
                'current_price': obj.product.price,
                'unit': obj.product.unit,
                'available_quantity': obj.product.available_quantity,
                'farmer_name': obj.product.farmer.full_name,
            }
        return None


class ReservationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating reservations.
    """
    class Meta:
        model = Reservation
        fields = [
            'product', 'quantity_requested', 'price_offered',
            'harvest_date_requested', 'pickup_delivery_date', 'buyer_notes'
        ]
    
    def validate_product(self, value):
        """Validate product exists and is available."""
        if value.status != 'Available':
            raise serializers.ValidationError("Product is not available for reservation.")
        return value
    
    def validate_quantity_requested(self, value):
        """Validate requested quantity."""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0.")
        return value
    
    def validate_price_offered(self, value):
        """Validate offered price."""
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0.")
        return value


class ReservationResponseSerializer(serializers.Serializer):
    """
    Serializer for farmer's response to reservation.
    """
    action = serializers.ChoiceField(choices=['accept', 'reject', 'counter_offer'])
    farmer_response = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    counter_offer_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        min_value=Decimal('0.01')
    )
    
    def validate(self, attrs):
        """Validate response data."""
        action = attrs.get('action')
        
        if action == 'counter_offer' and not attrs.get('counter_offer_price'):
            raise serializers.ValidationError({
                'counter_offer_price': 'Counter offer price is required when making a counter offer.'
            })
        
        return attrs


class CartItemSerializer(serializers.ModelSerializer):
    """
    Serializer for cart items.
    """
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    farmer_name = serializers.CharField(source='product.farmer.full_name', read_only=True)
    unit_price = serializers.ReadOnlyField()
    total_price = serializers.ReadOnlyField()
    is_available = serializers.ReadOnlyField()
    
    # Product details
    product_details = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'product', 'product_name', 'farmer_name', 'quantity',
            'unit_price', 'total_price', 'is_available', 'product_details',
            'added_at', 'updated_at'
        ]
        read_only_fields = ['added_at', 'updated_at']
    
    def get_product_details(self, obj):
        """Get product details."""
        if obj.product:
            return {
                'id': obj.product.id,
                'name': obj.product.product_name,
                'price': obj.product.price,
                'unit': obj.product.unit,
                'available_quantity': obj.product.available_quantity,
                'status': obj.product.status,
                'farmer_id': obj.product.farmer.id,
                'farmer_name': obj.product.farmer.full_name,
            }
        return None
    
    def validate_quantity(self, value):
        """Validate quantity against available stock."""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0.")
        
        # Check if we have the product in context for validation
        if hasattr(self, 'instance') and self.instance and self.instance.product:
            if value > self.instance.product.available_quantity:
                raise serializers.ValidationError(
                    f"Only {self.instance.product.available_quantity} units available."
                )
        
        return value


class CartSerializer(serializers.ModelSerializer):
    """
    Serializer for shopping cart.
    """
    buyer_name = serializers.CharField(source='buyer.full_name', read_only=True)
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.ReadOnlyField()
    total_amount = serializers.ReadOnlyField()
    is_empty = serializers.ReadOnlyField()
    
    class Meta:
        model = Cart
        fields = [
            'id', 'buyer', 'buyer_name', 'items', 'total_items',
            'total_amount', 'is_empty', 'created_at', 'updated_at'
        ]
        read_only_fields = ['buyer', 'created_at', 'updated_at']


class AddToCartSerializer(serializers.Serializer):
    """
    Serializer for adding items to cart.
    """
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    
    def validate_product_id(self, value):
        """Validate product exists and is available."""
        try:
            product = Product.objects.get(id=value)
            if product.status != 'Available':
                raise serializers.ValidationError("Product is not available.")
            return value
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found.")
    
    def validate(self, attrs):
        """Validate quantity against available stock."""
        try:
            product = Product.objects.get(id=attrs['product_id'])
            if attrs['quantity'] > product.available_quantity:
                raise serializers.ValidationError({
                    'quantity': f"Only {product.available_quantity} units available."
                })
        except Product.DoesNotExist:
            pass  # Will be caught by product_id validation
        
        return attrs
