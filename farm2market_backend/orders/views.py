"""
Views for order management.
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.core.responses import StandardResponse
from apps.core.exceptions import ValidationError, NotFoundError, BusinessLogicError
from apps.users.permissions import IsBuyer, IsFarmer
from .models import Order, OrderItem, OrderStatusHistory, Reservation, Cart, CartItem
from .serializers import (
    OrderSerializer, OrderCreateSerializer, OrderStatusHistorySerializer,
    ReservationSerializer, ReservationCreateSerializer, ReservationResponseSerializer,
    CartSerializer, CartItemSerializer, AddToCartSerializer
)
from .order_utils import OrderProcessor, OrderStatusManager, CartManager
from apps.products.models import Product

User = get_user_model()


class CartView(APIView):
    """
    Shopping cart management.
    """
    permission_classes = [permissions.IsAuthenticated, IsBuyer]
    
    def get(self, request):
        """Get user's cart."""
        cart_manager = CartManager(request.user)
        serializer = CartSerializer(cart_manager.cart)
        
        return StandardResponse.success(
            data=serializer.data,
            message='Cart retrieved successfully.'
        )
    
    def post(self, request):
        """Add item to cart."""
        serializer = AddToCartSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                product = Product.objects.get(id=serializer.validated_data['product_id'])
                quantity = serializer.validated_data['quantity']
                
                cart_manager = CartManager(request.user)
                cart_item = cart_manager.add_item(product, quantity)
                
                cart_serializer = CartSerializer(cart_manager.cart)
                
                return StandardResponse.success(
                    data=cart_serializer.data,
                    message='Item added to cart successfully.'
                )
                
            except Product.DoesNotExist:
                return StandardResponse.not_found(
                    message='Product not found.'
                )
            except DjangoValidationError as e:
                return StandardResponse.validation_error(
                    errors={'detail': str(e)},
                    message='Failed to add item to cart.'
                )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Invalid cart item data.'
        )
    
    def delete(self, request):
        """Clear cart."""
        cart_manager = CartManager(request.user)
        cart_manager.clear_cart()
        
        return StandardResponse.success(
            message='Cart cleared successfully.'
        )


class CartItemView(APIView):
    """
    Individual cart item management.
    """
    permission_classes = [permissions.IsAuthenticated, IsBuyer]
    
    def put(self, request, product_id):
        """Update cart item quantity."""
        try:
            product = Product.objects.get(id=product_id)
            quantity = request.data.get('quantity', 0)
            
            if not isinstance(quantity, int) or quantity < 0:
                return StandardResponse.validation_error(
                    errors={'quantity': 'Quantity must be a non-negative integer.'},
                    message='Invalid quantity.'
                )
            
            cart_manager = CartManager(request.user)
            cart_item = cart_manager.update_item_quantity(product, quantity)
            
            cart_serializer = CartSerializer(cart_manager.cart)
            
            return StandardResponse.updated(
                data=cart_serializer.data,
                message='Cart item updated successfully.'
            )
            
        except Product.DoesNotExist:
            return StandardResponse.not_found(
                message='Product not found.'
            )
        except DjangoValidationError as e:
            return StandardResponse.validation_error(
                errors={'detail': str(e)},
                message='Failed to update cart item.'
            )
    
    def delete(self, request, product_id):
        """Remove item from cart."""
        try:
            product = Product.objects.get(id=product_id)
            
            cart_manager = CartManager(request.user)
            removed = cart_manager.remove_item(product)
            
            if removed:
                cart_serializer = CartSerializer(cart_manager.cart)
                return StandardResponse.success(
                    data=cart_serializer.data,
                    message='Item removed from cart successfully.'
                )
            else:
                return StandardResponse.not_found(
                    message='Item not found in cart.'
                )
                
        except Product.DoesNotExist:
            return StandardResponse.not_found(
                message='Product not found.'
            )


class CartCheckoutView(APIView):
    """
    Cart checkout to create orders.
    """
    permission_classes = [permissions.IsAuthenticated, IsBuyer]
    
    def post(self, request):
        """Checkout cart and create orders."""
        serializer = OrderCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            try:
                # Validate cart
                cart_manager = CartManager(request.user)
                invalid_items = cart_manager.validate_cart()
                
                if invalid_items:
                    return StandardResponse.validation_error(
                        errors={'cart': 'Some items in your cart are no longer available.'},
                        data={'invalid_items': invalid_items},
                        message='Cart validation failed.'
                    )
                
                # Create orders
                order_processor = OrderProcessor(request.user)
                orders = order_processor.create_order_from_cart(
                    delivery_address_id=serializer.validated_data['delivery_address_id'],
                    delivery_method=serializer.validated_data['delivery_method'],
                    payment_method=serializer.validated_data['payment_method'],
                    preferred_delivery_date=serializer.validated_data.get('preferred_delivery_date'),
                    notes=serializer.validated_data.get('notes', '')
                )
                
                # Serialize created orders
                order_serializer = OrderSerializer(orders, many=True)
                
                return StandardResponse.created(
                    data=order_serializer.data,
                    message=f'Successfully created {len(orders)} order(s).'
                )
                
            except DjangoValidationError as e:
                return StandardResponse.validation_error(
                    errors={'detail': str(e)},
                    message='Checkout failed.'
                )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Invalid checkout data.'
        )


class OrderViewSet(ModelViewSet):
    """
    Order management viewset.
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'Buyer':
            return Order.objects.filter(buyer=user).select_related(
                'buyer', 'farmer', 'delivery_address'
            ).prefetch_related('items', 'status_history')
        elif user.user_type == 'Farmer':
            return Order.objects.filter(farmer=user).select_related(
                'buyer', 'farmer', 'delivery_address'
            ).prefetch_related('items', 'status_history')
        else:
            return Order.objects.none()
    
    def create(self, request, *args, **kwargs):
        """Orders are created through cart checkout."""
        return StandardResponse.error(
            message='Orders must be created through cart checkout.',
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def update(self, request, *args, **kwargs):
        """Update order (limited fields)."""
        instance = self.get_object()
        
        # Only allow certain fields to be updated
        allowed_fields = ['notes', 'preferred_delivery_date']
        
        # Farmers can update additional fields
        if request.user.user_type == 'Farmer' and request.user == instance.farmer:
            allowed_fields.extend(['estimated_preparation_time', 'tracking_number'])
        
        # Filter request data to only allowed fields
        filtered_data = {k: v for k, v in request.data.items() if k in allowed_fields}
        
        serializer = self.get_serializer(instance, data=filtered_data, partial=True)
        if serializer.is_valid():
            self.perform_update(serializer)
            return StandardResponse.updated(
                data=serializer.data,
                message='Order updated successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Order update failed.'
        )
    
    def destroy(self, request, *args, **kwargs):
        """Orders cannot be deleted, only cancelled."""
        return StandardResponse.error(
            message='Orders cannot be deleted. Use cancel action instead.',
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an order."""
        order = self.get_object()
        
        # Check if user can cancel this order
        if request.user != order.buyer and request.user != order.farmer:
            return StandardResponse.error(
                message='You do not have permission to cancel this order.',
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        if not order.can_be_cancelled:
            return StandardResponse.error(
                message=f'Order cannot be cancelled. Current status: {order.get_status_display()}',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            notes = request.data.get('notes', f'Cancelled by {request.user.full_name}')
            
            OrderStatusManager.update_order_status(
                order=order,
                new_status='cancelled',
                changed_by=request.user,
                notes=notes
            )
            
            serializer = self.get_serializer(order)
            
            return StandardResponse.updated(
                data=serializer.data,
                message='Order cancelled successfully.'
            )
            
        except DjangoValidationError as e:
            return StandardResponse.validation_error(
                errors={'detail': str(e)},
                message='Failed to cancel order.'
            )
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update order status (farmers only)."""
        order = self.get_object()
        
        # Only farmers can update order status
        if request.user.user_type != 'Farmer' or request.user != order.farmer:
            return StandardResponse.error(
                message='Only the assigned farmer can update order status.',
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')
        
        if not new_status:
            return StandardResponse.validation_error(
                errors={'status': 'Status is required.'},
                message='Invalid status update data.'
            )
        
        try:
            OrderStatusManager.update_order_status(
                order=order,
                new_status=new_status,
                changed_by=request.user,
                notes=notes
            )
            
            serializer = self.get_serializer(order)
            
            return StandardResponse.updated(
                data=serializer.data,
                message='Order status updated successfully.'
            )
            
        except DjangoValidationError as e:
            return StandardResponse.validation_error(
                errors={'detail': str(e)},
                message='Failed to update order status.'
            )
    
    @action(detail=True, methods=['get'])
    def status_history(self, request, pk=None):
        """Get order status history."""
        order = self.get_object()
        history = order.status_history.all()
        serializer = OrderStatusHistorySerializer(history, many=True)
        
        return StandardResponse.success(
            data=serializer.data,
            message='Order status history retrieved successfully.'
        )


class ReservationViewSet(ModelViewSet):
    """
    Reservation management viewset.
    """
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'Buyer':
            return Reservation.objects.filter(buyer=user).select_related(
                'buyer', 'farmer', 'product'
            )
        elif user.user_type == 'Farmer':
            return Reservation.objects.filter(farmer=user).select_related(
                'buyer', 'farmer', 'product'
            )
        else:
            return Reservation.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return ReservationCreateSerializer
        return ReservationSerializer

    def perform_create(self, serializer):
        """Create reservation with buyer and farmer."""
        product = serializer.validated_data['product']
        serializer.save(
            buyer=self.request.user,
            farmer=product.farmer
        )

    def create(self, request, *args, **kwargs):
        """Create a new reservation."""
        if request.user.user_type != 'Buyer':
            return StandardResponse.error(
                message='Only buyers can create reservations.',
                status_code=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)

            # Get the created reservation with full details
            reservation = Reservation.objects.get(id=serializer.instance.id)
            response_serializer = ReservationSerializer(reservation)

            return StandardResponse.created(
                data=response_serializer.data,
                message='Reservation created successfully.'
            )

        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Reservation creation failed.'
        )

    def update(self, request, *args, **kwargs):
        """Update reservation (limited fields)."""
        instance = self.get_object()

        # Only buyer can update their own reservations and only if pending
        if (request.user != instance.buyer or
            instance.status not in ['pending', 'counter_offered']):
            return StandardResponse.error(
                message='You cannot update this reservation.',
                status_code=status.HTTP_403_FORBIDDEN
            )

        # Only allow certain fields to be updated
        allowed_fields = ['quantity_requested', 'price_offered', 'buyer_notes']
        filtered_data = {k: v for k, v in request.data.items() if k in allowed_fields}

        serializer = self.get_serializer(instance, data=filtered_data, partial=True)
        if serializer.is_valid():
            self.perform_update(serializer)
            return StandardResponse.updated(
                data=serializer.data,
                message='Reservation updated successfully.'
            )

        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Reservation update failed.'
        )

    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        """Farmer response to reservation."""
        reservation = self.get_object()

        # Only farmer can respond to their reservations
        if request.user.user_type != 'Farmer' or request.user != reservation.farmer:
            return StandardResponse.error(
                message='Only the assigned farmer can respond to this reservation.',
                status_code=status.HTTP_403_FORBIDDEN
            )

        if not reservation.can_be_accepted and not reservation.can_be_rejected:
            return StandardResponse.error(
                message='This reservation cannot be modified.',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        serializer = ReservationResponseSerializer(data=request.data)
        if serializer.is_valid():
            action = serializer.validated_data['action']
            farmer_response = serializer.validated_data.get('farmer_response', '')
            counter_offer_price = serializer.validated_data.get('counter_offer_price')

            # Update reservation based on action
            if action == 'accept':
                reservation.status = 'accepted'
            elif action == 'reject':
                reservation.status = 'rejected'
            elif action == 'counter_offer':
                reservation.status = 'counter_offered'
                reservation.counter_offer_price = counter_offer_price

            reservation.farmer_response = farmer_response
            reservation.save()

            response_serializer = ReservationSerializer(reservation)

            return StandardResponse.updated(
                data=response_serializer.data,
                message=f'Reservation {action.replace("_", " ")} successfully.'
            )

        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Invalid response data.'
        )

    @action(detail=False, methods=['get'])
    def incoming(self, request):
        """Get incoming reservations for farmer."""
        if request.user.user_type != 'Farmer':
            return StandardResponse.error(
                message='Only farmers can view incoming reservations.',
                status_code=status.HTTP_403_FORBIDDEN
            )

        reservations = Reservation.objects.filter(
            farmer=request.user
        ).select_related('buyer', 'product').order_by('-created_at')

        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            reservations = reservations.filter(status=status_filter)

        serializer = ReservationSerializer(reservations, many=True)

        return StandardResponse.success(
            data=serializer.data,
            message='Incoming reservations retrieved successfully.'
        )

    @action(detail=False, methods=['get'])
    def outgoing(self, request):
        """Get outgoing reservations for buyer."""
        if request.user.user_type != 'Buyer':
            return StandardResponse.error(
                message='Only buyers can view outgoing reservations.',
                status_code=status.HTTP_403_FORBIDDEN
            )

        reservations = Reservation.objects.filter(
            buyer=request.user
        ).select_related('farmer', 'product').order_by('-created_at')

        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            reservations = reservations.filter(status=status_filter)

        serializer = ReservationSerializer(reservations, many=True)

        return StandardResponse.success(
            data=serializer.data,
            message='Outgoing reservations retrieved successfully.'
        )
