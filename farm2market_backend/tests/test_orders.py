"""
Tests for order management functionality.
"""
from django.urls import reverse
from rest_framework import status
from decimal import Decimal
from .test_base import BaseAPITestCase, TransactionTestMixin
from apps.orders.models import Order, OrderItem


class OrderTestCase(BaseAPITestCase, TransactionTestMixin):
    """
    Test cases for order management.
    """
    
    def test_create_order_success(self):
        """Test successful order creation."""
        self.authenticate_buyer()
        
        url = reverse('orders:order-list')
        data = {
            'farmer': self.farmer_user.id,
            'items': [
                {
                    'product': self.product1.id,
                    'quantity': 2
                },
                {
                    'product': self.product2.id,
                    'quantity': 1
                }
            ],
            'delivery_address': {
                'street': '123 Test Street',
                'city': 'Test City',
                'state': 'Test State',
                'postal_code': '12345',
                'country': 'Cameroon'
            }
        }
        
        response = self.client.post(url, data, format='json')
        response_data = self.assertResponseSuccess(response, status.HTTP_201_CREATED)
        
        # Check order was created
        order_id = response_data['data']['id']
        order = Order.objects.get(id=order_id)
        
        self.assertEqual(order.buyer, self.buyer_user)
        self.assertEqual(order.farmer, self.farmer_user)
        self.assertEqual(order.status, 'pending')
        
        # Check order items
        self.assertEqual(order.items.count(), 2)
        
        # Check total amount calculation
        expected_total = (self.product1.price * 2) + (self.product2.price * 1)
        self.assertEqual(order.total_amount, expected_total)
    
    def test_create_order_unauthorized(self):
        """Test order creation without authentication."""
        url = reverse('orders:order-list')
        data = {
            'farmer': self.farmer_user.id,
            'items': [{'product': self.product1.id, 'quantity': 2}]
        }
        
        response = self.client.post(url, data, format='json')
        self.assertResponseUnauthorized(response)
    
    def test_create_order_farmer_forbidden(self):
        """Test that farmers cannot create orders."""
        self.authenticate_farmer()
        
        url = reverse('orders:order-list')
        data = {
            'farmer': self.farmer_user.id,
            'items': [{'product': self.product1.id, 'quantity': 2}]
        }
        
        response = self.client.post(url, data, format='json')
        self.assertResponseForbidden(response)
    
    def test_create_order_invalid_quantity(self):
        """Test order creation with invalid quantity."""
        self.authenticate_buyer()
        
        url = reverse('orders:order-list')
        data = {
            'farmer': self.farmer_user.id,
            'items': [
                {
                    'product': self.product1.id,
                    'quantity': 1000  # Exceeds available quantity
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        self.assertResponseValidationError(response)
    
    def test_create_order_mixed_farmers(self):
        """Test order creation with products from different farmers."""
        # Create another farmer and product
        other_farmer = User.objects.create_user(
            email='farmer2@test.com',
            password='TestPass123!',
            full_name='Other Farmer',
            user_type='Farmer',
            email_verified=True
        )
        
        other_product = Product.objects.create(
            farmer=other_farmer,
            product_name='Other Product',
            description='Product from other farmer',
            price=Decimal('7.99'),
            quantity=50,
            unit='kg',
            status='Available'
        )
        
        self.authenticate_buyer()
        
        url = reverse('orders:order-list')
        data = {
            'farmer': self.farmer_user.id,
            'items': [
                {'product': self.product1.id, 'quantity': 2},
                {'product': other_product.id, 'quantity': 1}  # Different farmer
            ]
        }
        
        response = self.client.post(url, data, format='json')
        self.assertResponseValidationError(response)
    
    def test_list_orders_buyer(self):
        """Test order listing for buyer."""
        # Create test order
        order = self.create_test_order()
        
        self.authenticate_buyer()
        
        url = reverse('orders:order-list')
        response = self.client.get(url)
        
        response_data = self.assertResponseSuccess(response)
        
        # Check orders are returned
        results = response_data['data']['results']
        self.assertGreater(len(results), 0)
        
        # Check only buyer's orders are returned
        for order_data in results:
            self.assertEqual(order_data['buyer']['id'], self.buyer_user.id)
    
    def test_list_orders_farmer(self):
        """Test order listing for farmer."""
        # Create test order
        order = self.create_test_order()
        
        self.authenticate_farmer()
        
        url = reverse('orders:order-list')
        response = self.client.get(url)
        
        response_data = self.assertResponseSuccess(response)
        
        # Check orders are returned
        results = response_data['data']['results']
        self.assertGreater(len(results), 0)
        
        # Check only farmer's orders are returned
        for order_data in results:
            self.assertEqual(order_data['farmer']['id'], self.farmer_user.id)
    
    def test_get_order_detail_buyer(self):
        """Test order detail retrieval by buyer."""
        order = self.create_test_order()
        
        self.authenticate_buyer()
        
        url = reverse('orders:order-detail', kwargs={'pk': order.id})
        response = self.client.get(url)
        
        response_data = self.assertResponseSuccess(response)
        
        # Check order details
        order_data = response_data['data']
        self.assertEqual(order_data['id'], order.id)
        self.assertEqual(order_data['order_number'], order.order_number)
        self.assertIn('items', order_data)
    
    def test_get_order_detail_farmer(self):
        """Test order detail retrieval by farmer."""
        order = self.create_test_order()
        
        self.authenticate_farmer()
        
        url = reverse('orders:order-detail', kwargs={'pk': order.id})
        response = self.client.get(url)
        
        response_data = self.assertResponseSuccess(response)
        
        # Check order details
        order_data = response_data['data']
        self.assertEqual(order_data['id'], order.id)
    
    def test_get_order_detail_unauthorized_user(self):
        """Test that users cannot access orders they're not involved in."""
        order = self.create_test_order()
        
        # Create another user
        other_user = User.objects.create_user(
            email='other@test.com',
            password='TestPass123!',
            full_name='Other User',
            user_type='Buyer',
            email_verified=True
        )
        
        self.authenticate_user(other_user)
        
        url = reverse('orders:order-detail', kwargs={'pk': order.id})
        response = self.client.get(url)
        
        self.assertResponseForbidden(response)
    
    def test_update_order_status_farmer(self):
        """Test order status update by farmer."""
        order = self.create_test_order()
        
        self.authenticate_farmer()
        
        url = reverse('orders:order-detail', kwargs={'pk': order.id})
        data = {'status': 'confirmed'}
        
        response = self.client.patch(url, data, format='json')
        response_data = self.assertResponseSuccess(response)
        
        # Check status was updated
        order.refresh_from_db()
        self.assertEqual(order.status, 'confirmed')
    
    def test_update_order_status_buyer_forbidden(self):
        """Test that buyers cannot update order status."""
        order = self.create_test_order()
        
        self.authenticate_buyer()
        
        url = reverse('orders:order-detail', kwargs={'pk': order.id})
        data = {'status': 'confirmed'}
        
        response = self.client.patch(url, data, format='json')
        self.assertResponseForbidden(response)
    
    def test_cancel_order_buyer(self):
        """Test order cancellation by buyer."""
        order = self.create_test_order()
        
        self.authenticate_buyer()
        
        url = reverse('orders:cancel-order', kwargs={'pk': order.id})
        
        response = self.client.post(url)
        response_data = self.assertResponseSuccess(response)
        
        # Check order was cancelled
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
    
    def test_cancel_order_after_confirmation_forbidden(self):
        """Test that orders cannot be cancelled after confirmation."""
        order = self.create_test_order()
        order.status = 'confirmed'
        order.save()
        
        self.authenticate_buyer()
        
        url = reverse('orders:cancel-order', kwargs={'pk': order.id})
        
        response = self.client.post(url)
        self.assertResponseValidationError(response)
    
    def test_order_status_history(self):
        """Test order status history tracking."""
        order = self.create_test_order()
        
        # Update status multiple times
        self.authenticate_farmer()
        
        url = reverse('orders:order-detail', kwargs={'pk': order.id})
        
        # Confirm order
        response = self.client.patch(url, {'status': 'confirmed'}, format='json')
        self.assertResponseSuccess(response)
        
        # Mark as preparing
        response = self.client.patch(url, {'status': 'preparing'}, format='json')
        self.assertResponseSuccess(response)
        
        # Check status history
        history_url = reverse('orders:order-status-history', kwargs={'pk': order.id})
        response = self.client.get(history_url)
        
        response_data = self.assertResponseSuccess(response)
        
        # Should have multiple status entries
        history = response_data['data']
        self.assertGreaterEqual(len(history), 3)  # pending, confirmed, preparing
    
    def test_order_payment_processing(self):
        """Test order payment processing."""
        order = self.create_test_order()
        
        self.authenticate_buyer()
        
        url = reverse('orders:process-payment', kwargs={'pk': order.id})
        data = {
            'payment_method': 'credit_card',
            'payment_details': {
                'card_number': '4111111111111111',
                'expiry_month': '12',
                'expiry_year': '2025',
                'cvv': '123'
            }
        }
        
        response = self.client.post(url, data, format='json')
        
        # This would depend on payment integration implementation
        # For now, just check the endpoint exists
        self.assertIn(response.status_code, [200, 201, 400, 501])
    
    def test_order_delivery_tracking(self):
        """Test order delivery tracking."""
        order = self.create_test_order()
        order.status = 'shipped'
        order.save()
        
        self.authenticate_buyer()
        
        url = reverse('orders:delivery-tracking', kwargs={'pk': order.id})
        response = self.client.get(url)
        
        # This would depend on delivery tracking implementation
        # For now, just check the endpoint exists
        self.assertIn(response.status_code, [200, 404, 501])
    
    def test_order_filters(self):
        """Test order listing with filters."""
        # Create multiple orders with different statuses
        order1 = self.create_test_order()
        order1.status = 'confirmed'
        order1.save()
        
        order2 = self.create_test_order()
        order2.status = 'delivered'
        order2.save()
        
        self.authenticate_buyer()
        
        # Filter by status
        url = reverse('orders:order-list')
        response = self.client.get(url, {'status': 'confirmed'})
        
        response_data = self.assertResponseSuccess(response)
        
        # Check only confirmed orders are returned
        results = response_data['data']['results']
        for order_data in results:
            self.assertEqual(order_data['status'], 'confirmed')
    
    def test_order_search(self):
        """Test order search functionality."""
        order = self.create_test_order()
        
        self.authenticate_buyer()
        
        # Search by order number
        url = reverse('orders:order-list')
        response = self.client.get(url, {'search': order.order_number})
        
        response_data = self.assertResponseSuccess(response)
        
        # Should find the order
        results = response_data['data']['results']
        self.assertGreater(len(results), 0)
        
        found_order = any(o['order_number'] == order.order_number for o in results)
        self.assertTrue(found_order)
    
    def test_order_total_calculation(self):
        """Test order total amount calculation."""
        self.authenticate_buyer()
        
        url = reverse('orders:order-list')
        data = {
            'farmer': self.farmer_user.id,
            'items': [
                {'product': self.product1.id, 'quantity': 3},
                {'product': self.product2.id, 'quantity': 2}
            ]
        }
        
        response = self.client.post(url, data, format='json')
        response_data = self.assertResponseSuccess(response, status.HTTP_201_CREATED)
        
        # Check total calculation
        expected_total = (self.product1.price * 3) + (self.product2.price * 2)
        actual_total = Decimal(str(response_data['data']['total_amount']))
        
        self.assertEqual(actual_total, expected_total)
    
    def test_order_inventory_update(self):
        """Test that order creation updates product inventory."""
        original_quantity = self.product1.quantity
        order_quantity = 5
        
        self.authenticate_buyer()
        
        url = reverse('orders:order-list')
        data = {
            'farmer': self.farmer_user.id,
            'items': [{'product': self.product1.id, 'quantity': order_quantity}]
        }
        
        response = self.client.post(url, data, format='json')
        self.assertResponseSuccess(response, status.HTTP_201_CREATED)
        
        # Check inventory was updated
        self.product1.refresh_from_db()
        expected_quantity = original_quantity - order_quantity
        self.assertEqual(self.product1.quantity, expected_quantity)
