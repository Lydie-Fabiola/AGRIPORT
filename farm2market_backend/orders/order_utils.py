"""
Order processing utilities and business logic.
"""
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import Order, OrderItem, OrderStatusHistory, Cart, CartItem
from apps.products.models import Product, StockMovement


class OrderProcessor:
    """
    Handle order creation and processing logic.
    """
    
    def __init__(self, buyer):
        self.buyer = buyer
    
    @transaction.atomic
    def create_order_from_cart(self, delivery_address, delivery_method='delivery', 
                              payment_method='cash', preferred_delivery_date=None, notes=''):
        """
        Create order from user's cart.
        """
        # Get buyer's cart
        try:
            cart = Cart.objects.get(buyer=self.buyer)
        except Cart.DoesNotExist:
            raise ValidationError("Cart not found.")
        
        if cart.is_empty:
            raise ValidationError("Cart is empty.")
        
        # Validate cart items
        self._validate_cart_items(cart)
        
        # Group cart items by farmer
        farmer_orders = self._group_cart_by_farmer(cart)
        
        created_orders = []
        
        # Create separate orders for each farmer
        for farmer, items in farmer_orders.items():
            order = self._create_single_order(
                farmer=farmer,
                items=items,
                delivery_address=delivery_address,
                delivery_method=delivery_method,
                payment_method=payment_method,
                preferred_delivery_date=preferred_delivery_date,
                notes=notes
            )
            created_orders.append(order)
        
        # Clear cart after successful order creation
        cart.clear()
        
        return created_orders
    
    def _validate_cart_items(self, cart):
        """
        Validate all cart items for availability and stock.
        """
        for item in cart.items.all():
            if not item.is_available:
                raise ValidationError(
                    f"Product '{item.product.product_name}' is no longer available "
                    f"in the requested quantity ({item.quantity})."
                )
    
    def _group_cart_by_farmer(self, cart):
        """
        Group cart items by farmer.
        """
        farmer_groups = {}
        
        for item in cart.items.all():
            farmer = item.product.farmer
            if farmer not in farmer_groups:
                farmer_groups[farmer] = []
            farmer_groups[farmer].append(item)
        
        return farmer_groups
    
    def _create_single_order(self, farmer, items, delivery_address, delivery_method,
                           payment_method, preferred_delivery_date, notes):
        """
        Create a single order for one farmer.
        """
        # Calculate order totals
        subtotal = sum(item.total_price for item in items)
        delivery_fee = self._calculate_delivery_fee(farmer, delivery_address, delivery_method)
        tax_amount = self._calculate_tax(subtotal)
        
        # Create order
        order = Order.objects.create(
            buyer=self.buyer,
            farmer=farmer,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            tax_amount=tax_amount,
            delivery_address=delivery_address,
            delivery_method=delivery_method,
            payment_method=payment_method,
            preferred_delivery_date=preferred_delivery_date,
            notes=notes
        )
        
        # Create order items and reserve stock
        for cart_item in items:
            self._create_order_item(order, cart_item)
            self._reserve_stock(cart_item.product, cart_item.quantity, order)
        
        # Create initial status history
        OrderStatusHistory.objects.create(
            order=order,
            status='pending',
            notes='Order created from cart',
            changed_by=self.buyer
        )
        
        return order
    
    def _create_order_item(self, order, cart_item):
        """
        Create order item from cart item.
        """
        return OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            quantity=cart_item.quantity,
            unit_price=cart_item.product.price
        )
    
    def _reserve_stock(self, product, quantity, order):
        """
        Reserve stock for the order.
        """
        if product.available_quantity < quantity:
            raise ValidationError(
                f"Insufficient stock for {product.product_name}. "
                f"Available: {product.available_quantity}, Requested: {quantity}"
            )
        
        # Update product quantity
        product.quantity -= quantity
        product.save(update_fields=['quantity'])
        
        # Create stock movement record
        StockMovement.objects.create(
            product=product,
            movement_type='sale',
            quantity=quantity,
            reference_type='order',
            reference_id=order.id,
            notes=f'Stock reserved for order {order.order_number}'
        )
    
    def _calculate_delivery_fee(self, farmer, delivery_address, delivery_method):
        """
        Calculate delivery fee based on farmer's delivery zones.
        """
        if delivery_method == 'pickup':
            return Decimal('0.00')
        
        # Check if delivery address is in farmer's delivery zones
        delivery_zones = farmer.delivery_zones.filter(is_active=True)
        
        # For now, return a default delivery fee
        # In a real implementation, you would check if the address is within any delivery zone
        return Decimal('5.00')  # Default delivery fee
    
    def _calculate_tax(self, subtotal):
        """
        Calculate tax amount.
        """
        # For now, no tax calculation
        # In a real implementation, you might have different tax rates
        return Decimal('0.00')


class OrderStatusManager:
    """
    Manage order status transitions and validations.
    """
    
    # Define valid status transitions
    STATUS_TRANSITIONS = {
        'pending': ['confirmed', 'cancelled'],
        'confirmed': ['preparing', 'cancelled'],
        'preparing': ['ready', 'cancelled'],
        'ready': ['in_transit', 'delivered', 'cancelled'],
        'in_transit': ['delivered', 'cancelled'],
        'delivered': ['refunded'],
        'cancelled': [],
        'refunded': [],
    }
    
    @classmethod
    def can_transition_to(cls, current_status, new_status):
        """
        Check if status transition is valid.
        """
        return new_status in cls.STATUS_TRANSITIONS.get(current_status, [])
    
    @classmethod
    @transaction.atomic
    def update_order_status(cls, order, new_status, changed_by, notes=''):
        """
        Update order status with validation and history tracking.
        """
        if not cls.can_transition_to(order.status, new_status):
            raise ValidationError(
                f"Cannot transition from {order.status} to {new_status}"
            )
        
        old_status = order.status
        order.status = new_status
        order.save(update_fields=['status', 'updated_at'])
        
        # Create status history record
        OrderStatusHistory.objects.create(
            order=order,
            status=new_status,
            notes=notes,
            changed_by=changed_by
        )
        
        # Handle status-specific logic
        cls._handle_status_change(order, old_status, new_status)
        
        return order
    
    @classmethod
    def _handle_status_change(cls, order, old_status, new_status):
        """
        Handle side effects of status changes.
        """
        if new_status == 'cancelled':
            cls._handle_order_cancellation(order)
        elif new_status == 'delivered':
            cls._handle_order_delivery(order)
        elif new_status == 'refunded':
            cls._handle_order_refund(order)
    
    @classmethod
    def _handle_order_cancellation(cls, order):
        """
        Handle order cancellation - restore stock.
        """
        for item in order.items.all():
            # Restore stock
            item.product.quantity += item.quantity
            item.product.save(update_fields=['quantity'])
            
            # Create stock movement record
            StockMovement.objects.create(
                product=item.product,
                movement_type='return',
                quantity=item.quantity,
                reference_type='order',
                reference_id=order.id,
                notes=f'Stock restored from cancelled order {order.order_number}'
            )
    
    @classmethod
    def _handle_order_delivery(cls, order):
        """
        Handle order delivery - mark as completed.
        """
        order.actual_delivery_date = timezone.now()
        order.save(update_fields=['actual_delivery_date'])
    
    @classmethod
    def _handle_order_refund(cls, order):
        """
        Handle order refund - restore stock and update payment status.
        """
        # Restore stock (similar to cancellation)
        cls._handle_order_cancellation(order)
        
        # Update payment status
        order.payment_status = 'refunded'
        order.save(update_fields=['payment_status'])


class CartManager:
    """
    Manage shopping cart operations.
    """
    
    def __init__(self, buyer):
        self.buyer = buyer
        self.cart = self._get_or_create_cart()
    
    def _get_or_create_cart(self):
        """
        Get or create cart for buyer.
        """
        cart, created = Cart.objects.get_or_create(buyer=self.buyer)
        return cart
    
    def add_item(self, product, quantity):
        """
        Add item to cart or update quantity if exists.
        """
        if product.status != 'Available':
            raise ValidationError("Product is not available.")
        
        if quantity > product.available_quantity:
            raise ValidationError(
                f"Only {product.available_quantity} units available."
            )
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=self.cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            # Update existing item
            new_quantity = cart_item.quantity + quantity
            if new_quantity > product.available_quantity:
                raise ValidationError(
                    f"Cannot add {quantity} more units. "
                    f"Only {product.available_quantity - cart_item.quantity} more units available."
                )
            cart_item.quantity = new_quantity
            cart_item.save(update_fields=['quantity', 'updated_at'])
        
        return cart_item
    
    def update_item_quantity(self, product, quantity):
        """
        Update cart item quantity.
        """
        try:
            cart_item = CartItem.objects.get(cart=self.cart, product=product)
        except CartItem.DoesNotExist:
            raise ValidationError("Item not found in cart.")
        
        if quantity <= 0:
            cart_item.delete()
            return None
        
        if quantity > product.available_quantity:
            raise ValidationError(
                f"Only {product.available_quantity} units available."
            )
        
        cart_item.quantity = quantity
        cart_item.save(update_fields=['quantity', 'updated_at'])
        
        return cart_item
    
    def remove_item(self, product):
        """
        Remove item from cart.
        """
        try:
            cart_item = CartItem.objects.get(cart=self.cart, product=product)
            cart_item.delete()
            return True
        except CartItem.DoesNotExist:
            return False
    
    def clear_cart(self):
        """
        Clear all items from cart.
        """
        self.cart.clear()
    
    def validate_cart(self):
        """
        Validate all cart items for availability and stock.
        """
        invalid_items = []
        
        for item in self.cart.items.all():
            if not item.is_available:
                invalid_items.append({
                    'product': item.product.product_name,
                    'requested': item.quantity,
                    'available': item.product.available_quantity,
                    'status': item.product.status
                })
        
        return invalid_items
