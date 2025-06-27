"""
Base test classes and utilities for Farm2Market testing.
"""
import json
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.farmers.models import FarmerProfile
from apps.buyers.models import BuyerPreferences
from apps.products.models import Product, ProductCategory
from apps.orders.models import Order, OrderItem
from decimal import Decimal

User = get_user_model()


class BaseTestCase(TestCase):
    """
    Base test case with common setup and utilities.
    """
    
    def setUp(self):
        """Set up test data."""
        self.create_test_users()
        self.create_test_categories()
        self.create_test_products()
    
    def create_test_users(self):
        """Create test users."""
        # Create farmer user
        self.farmer_user = User.objects.create_user(
            email='farmer@test.com',
            password='TestPass123!',
            full_name='Test Farmer',
            user_type='Farmer',
            email_verified=True
        )
        
        # Create farmer profile
        self.farmer_profile = FarmerProfile.objects.create(
            user=self.farmer_user,
            farm_name='Test Farm',
            location='Test Location',
            farm_size=10.5,
            farming_experience=5,
            organic_certified=True,
            description='Test farm description'
        )
        
        # Create buyer user
        self.buyer_user = User.objects.create_user(
            email='buyer@test.com',
            password='TestPass123!',
            full_name='Test Buyer',
            user_type='Buyer',
            email_verified=True
        )
        
        # Create buyer preferences
        self.buyer_preferences = BuyerPreferences.objects.create(
            user=self.buyer_user,
            preferred_location='Test City',
            max_delivery_distance=50,
            organic_preference=True,
            budget_range='medium'
        )
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='TestPass123!',
            full_name='Test Admin',
            user_type='Admin',
            email_verified=True,
            is_staff=True,
            is_superuser=True
        )
    
    def create_test_categories(self):
        """Create test product categories."""
        self.category_vegetables = ProductCategory.objects.create(
            name='Vegetables',
            description='Fresh vegetables'
        )
        
        self.category_fruits = ProductCategory.objects.create(
            name='Fruits',
            description='Fresh fruits'
        )
    
    def create_test_products(self):
        """Create test products."""
        self.product1 = Product.objects.create(
            farmer=self.farmer_user,
            product_name='Fresh Tomatoes',
            description='Organic red tomatoes',
            price=Decimal('5.99'),
            quantity=100,
            unit='kg',
            status='Available'
        )
        self.product1.categories.add(self.category_vegetables)
        
        self.product2 = Product.objects.create(
            farmer=self.farmer_user,
            product_name='Sweet Apples',
            description='Crispy red apples',
            price=Decimal('3.50'),
            quantity=50,
            unit='kg',
            status='Available'
        )
        self.product2.categories.add(self.category_fruits)
    
    def get_jwt_token(self, user):
        """Get JWT token for user."""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)


class BaseAPITestCase(APITestCase):
    """
    Base API test case with authentication utilities.
    """
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.create_test_users()
        self.create_test_categories()
        self.create_test_products()
    
    def create_test_users(self):
        """Create test users."""
        # Create farmer user
        self.farmer_user = User.objects.create_user(
            email='farmer@test.com',
            password='TestPass123!',
            full_name='Test Farmer',
            user_type='Farmer',
            email_verified=True
        )
        
        # Create farmer profile
        self.farmer_profile = FarmerProfile.objects.create(
            user=self.farmer_user,
            farm_name='Test Farm',
            location='Test Location',
            farm_size=10.5,
            farming_experience=5,
            organic_certified=True,
            description='Test farm description'
        )
        
        # Create buyer user
        self.buyer_user = User.objects.create_user(
            email='buyer@test.com',
            password='TestPass123!',
            full_name='Test Buyer',
            user_type='Buyer',
            email_verified=True
        )
        
        # Create buyer preferences
        self.buyer_preferences = BuyerPreferences.objects.create(
            user=self.buyer_user,
            preferred_location='Test City',
            max_delivery_distance=50,
            organic_preference=True,
            budget_range='medium'
        )
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='TestPass123!',
            full_name='Test Admin',
            user_type='Admin',
            email_verified=True,
            is_staff=True,
            is_superuser=True
        )
    
    def create_test_categories(self):
        """Create test product categories."""
        self.category_vegetables = ProductCategory.objects.create(
            name='Vegetables',
            description='Fresh vegetables'
        )
        
        self.category_fruits = ProductCategory.objects.create(
            name='Fruits',
            description='Fresh fruits'
        )
    
    def create_test_products(self):
        """Create test products."""
        self.product1 = Product.objects.create(
            farmer=self.farmer_user,
            product_name='Fresh Tomatoes',
            description='Organic red tomatoes',
            price=Decimal('5.99'),
            quantity=100,
            unit='kg',
            status='Available'
        )
        self.product1.categories.add(self.category_vegetables)
        
        self.product2 = Product.objects.create(
            farmer=self.farmer_user,
            product_name='Sweet Apples',
            description='Crispy red apples',
            price=Decimal('3.50'),
            quantity=50,
            unit='kg',
            status='Available'
        )
        self.product2.categories.add(self.category_fruits)
    
    def authenticate_user(self, user):
        """Authenticate user for API requests."""
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        return access_token
    
    def authenticate_farmer(self):
        """Authenticate farmer user."""
        return self.authenticate_user(self.farmer_user)
    
    def authenticate_buyer(self):
        """Authenticate buyer user."""
        return self.authenticate_user(self.buyer_user)
    
    def authenticate_admin(self):
        """Authenticate admin user."""
        return self.authenticate_user(self.admin_user)
    
    def clear_authentication(self):
        """Clear authentication credentials."""
        self.client.credentials()
    
    def assertResponseSuccess(self, response, status_code=200):
        """Assert response is successful."""
        self.assertEqual(response.status_code, status_code)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        return data
    
    def assertResponseError(self, response, status_code=400):
        """Assert response is an error."""
        self.assertEqual(response.status_code, status_code)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        return data
    
    def assertResponseValidationError(self, response):
        """Assert response is a validation error."""
        return self.assertResponseError(response, 400)
    
    def assertResponseNotFound(self, response):
        """Assert response is not found."""
        return self.assertResponseError(response, 404)
    
    def assertResponseUnauthorized(self, response):
        """Assert response is unauthorized."""
        return self.assertResponseError(response, 401)
    
    def assertResponseForbidden(self, response):
        """Assert response is forbidden."""
        return self.assertResponseError(response, 403)


class TransactionTestMixin:
    """
    Mixin for tests that require database transactions.
    """
    
    def create_test_order(self, buyer=None, farmer=None, products=None):
        """Create a test order."""
        if buyer is None:
            buyer = self.buyer_user
        if farmer is None:
            farmer = self.farmer_user
        if products is None:
            products = [self.product1]
        
        order = Order.objects.create(
            buyer=buyer,
            farmer=farmer,
            order_number=f'ORD-{Order.objects.count() + 1:06d}',
            status='pending',
            total_amount=Decimal('0.00')
        )
        
        total_amount = Decimal('0.00')
        for product in products:
            quantity = 2
            unit_price = product.price
            total_price = unit_price * quantity
            
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price
            )
            
            total_amount += total_price
        
        order.total_amount = total_amount
        order.save()
        
        return order


class MockDataMixin:
    """
    Mixin for creating mock data for testing.
    """
    
    def create_mock_users(self, count=5):
        """Create multiple mock users."""
        users = []
        
        for i in range(count):
            user = User.objects.create_user(
                email=f'user{i}@test.com',
                password='TestPass123!',
                full_name=f'Test User {i}',
                user_type='Buyer' if i % 2 == 0 else 'Farmer',
                email_verified=True
            )
            users.append(user)
        
        return users
    
    def create_mock_products(self, farmer=None, count=10):
        """Create multiple mock products."""
        if farmer is None:
            farmer = self.farmer_user
        
        products = []
        
        for i in range(count):
            product = Product.objects.create(
                farmer=farmer,
                product_name=f'Test Product {i}',
                description=f'Description for product {i}',
                price=Decimal(f'{5 + i}.99'),
                quantity=100 - i * 5,
                unit='kg',
                status='Available'
            )
            
            # Add random category
            category = self.category_vegetables if i % 2 == 0 else self.category_fruits
            product.categories.add(category)
            
            products.append(product)
        
        return products


class PerformanceTestMixin:
    """
    Mixin for performance testing utilities.
    """
    
    def assertQueryCountLessThan(self, max_queries):
        """Assert that query count is less than specified maximum."""
        from django.test.utils import override_settings
        from django.db import connection
        
        def decorator(func):
            def wrapper(*args, **kwargs):
                with override_settings(DEBUG=True):
                    initial_queries = len(connection.queries)
                    result = func(*args, **kwargs)
                    final_queries = len(connection.queries)
                    query_count = final_queries - initial_queries
                    
                    self.assertLess(
                        query_count, 
                        max_queries,
                        f'Query count {query_count} exceeds maximum {max_queries}'
                    )
                    
                    return result
            return wrapper
        return decorator
    
    def measure_response_time(self, func, max_time=1.0):
        """Measure response time and assert it's under maximum."""
        import time
        
        start_time = time.time()
        result = func()
        end_time = time.time()
        
        response_time = end_time - start_time
        self.assertLess(
            response_time,
            max_time,
            f'Response time {response_time:.3f}s exceeds maximum {max_time}s'
        )
        
        return result, response_time
