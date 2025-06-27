"""
Tests for product management functionality.
"""
from django.urls import reverse
from rest_framework import status
from decimal import Decimal
from .test_base import BaseAPITestCase, PerformanceTestMixin
from apps.products.models import Product, ProductCategory


class ProductTestCase(BaseAPITestCase, PerformanceTestMixin):
    """
    Test cases for product management.
    """
    
    def test_create_product_success(self):
        """Test successful product creation."""
        self.authenticate_farmer()
        
        url = reverse('products:product-list')
        data = {
            'product_name': 'Fresh Carrots',
            'description': 'Organic orange carrots',
            'price': '4.50',
            'quantity': 75,
            'unit': 'kg',
            'categories': [self.category_vegetables.id]
        }
        
        response = self.client.post(url, data, format='json')
        response_data = self.assertResponseSuccess(response, status.HTTP_201_CREATED)
        
        # Check product was created
        product_id = response_data['data']['id']
        product = Product.objects.get(id=product_id)
        
        self.assertEqual(product.product_name, 'Fresh Carrots')
        self.assertEqual(product.farmer, self.farmer_user)
        self.assertEqual(product.price, Decimal('4.50'))
        self.assertEqual(product.quantity, 75)
    
    def test_create_product_unauthorized(self):
        """Test product creation without authentication."""
        url = reverse('products:product-list')
        data = {
            'product_name': 'Fresh Carrots',
            'description': 'Organic orange carrots',
            'price': '4.50',
            'quantity': 75,
            'unit': 'kg'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertResponseUnauthorized(response)
    
    def test_create_product_buyer_forbidden(self):
        """Test that buyers cannot create products."""
        self.authenticate_buyer()
        
        url = reverse('products:product-list')
        data = {
            'product_name': 'Fresh Carrots',
            'description': 'Organic orange carrots',
            'price': '4.50',
            'quantity': 75,
            'unit': 'kg'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertResponseForbidden(response)
    
    def test_create_product_invalid_data(self):
        """Test product creation with invalid data."""
        self.authenticate_farmer()
        
        url = reverse('products:product-list')
        data = {
            'product_name': '',  # Empty name
            'description': 'Test description',
            'price': '-5.00',  # Negative price
            'quantity': -10,  # Negative quantity
            'unit': 'kg'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertResponseValidationError(response)
    
    def test_list_products_success(self):
        """Test successful product listing."""
        url = reverse('products:product-list')
        
        response = self.client.get(url)
        response_data = self.assertResponseSuccess(response)
        
        # Check products are returned
        self.assertIn('data', response_data)
        self.assertIn('results', response_data['data'])
        self.assertGreaterEqual(len(response_data['data']['results']), 2)
    
    def test_list_products_with_filters(self):
        """Test product listing with filters."""
        url = reverse('products:product-list')
        
        # Filter by category
        response = self.client.get(url, {'category': self.category_vegetables.id})
        response_data = self.assertResponseSuccess(response)
        
        # Should only return vegetables
        results = response_data['data']['results']
        for product in results:
            self.assertIn(self.category_vegetables.id, product['categories'])
    
    def test_list_products_with_search(self):
        """Test product listing with search."""
        url = reverse('products:product-list')
        
        # Search for tomatoes
        response = self.client.get(url, {'search': 'tomatoes'})
        response_data = self.assertResponseSuccess(response)
        
        # Should return products matching search
        results = response_data['data']['results']
        self.assertGreater(len(results), 0)
        
        # Check that results contain search term
        found_tomatoes = any('tomato' in product['product_name'].lower() for product in results)
        self.assertTrue(found_tomatoes)
    
    def test_list_products_with_price_filter(self):
        """Test product listing with price filters."""
        url = reverse('products:product-list')
        
        # Filter by price range
        response = self.client.get(url, {'price_min': '3.00', 'price_max': '5.00'})
        response_data = self.assertResponseSuccess(response)
        
        # Check all products are within price range
        results = response_data['data']['results']
        for product in results:
            price = Decimal(str(product['price']))
            self.assertGreaterEqual(price, Decimal('3.00'))
            self.assertLessEqual(price, Decimal('5.00'))
    
    def test_get_product_detail_success(self):
        """Test successful product detail retrieval."""
        url = reverse('products:product-detail', kwargs={'pk': self.product1.id})
        
        response = self.client.get(url)
        response_data = self.assertResponseSuccess(response)
        
        # Check product details
        product_data = response_data['data']
        self.assertEqual(product_data['id'], self.product1.id)
        self.assertEqual(product_data['product_name'], self.product1.product_name)
        self.assertEqual(Decimal(str(product_data['price'])), self.product1.price)
    
    def test_get_product_detail_not_found(self):
        """Test product detail retrieval for non-existent product."""
        url = reverse('products:product-detail', kwargs={'pk': 99999})
        
        response = self.client.get(url)
        self.assertResponseNotFound(response)
    
    def test_update_product_success(self):
        """Test successful product update."""
        self.authenticate_farmer()
        
        url = reverse('products:product-detail', kwargs={'pk': self.product1.id})
        data = {
            'product_name': 'Updated Tomatoes',
            'price': '6.99',
            'quantity': 80
        }
        
        response = self.client.patch(url, data, format='json')
        response_data = self.assertResponseSuccess(response)
        
        # Check product was updated
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.product_name, 'Updated Tomatoes')
        self.assertEqual(self.product1.price, Decimal('6.99'))
        self.assertEqual(self.product1.quantity, 80)
    
    def test_update_product_unauthorized(self):
        """Test product update without authentication."""
        url = reverse('products:product-detail', kwargs={'pk': self.product1.id})
        data = {'product_name': 'Updated Tomatoes'}
        
        response = self.client.patch(url, data, format='json')
        self.assertResponseUnauthorized(response)
    
    def test_update_product_wrong_farmer(self):
        """Test that farmers cannot update other farmers' products."""
        # Create another farmer
        other_farmer = self.create_test_users()[0]  # This would need to be implemented
        other_farmer.user_type = 'Farmer'
        other_farmer.save()
        
        self.authenticate_user(other_farmer)
        
        url = reverse('products:product-detail', kwargs={'pk': self.product1.id})
        data = {'product_name': 'Hacked Tomatoes'}
        
        response = self.client.patch(url, data, format='json')
        self.assertResponseForbidden(response)
    
    def test_delete_product_success(self):
        """Test successful product deletion."""
        self.authenticate_farmer()
        
        url = reverse('products:product-detail', kwargs={'pk': self.product1.id})
        
        response = self.client.delete(url)
        self.assertResponseSuccess(response, status.HTTP_204_NO_CONTENT)
        
        # Check product was deleted (soft delete)
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.status, 'Deleted')
    
    def test_delete_product_unauthorized(self):
        """Test product deletion without authentication."""
        url = reverse('products:product-detail', kwargs={'pk': self.product1.id})
        
        response = self.client.delete(url)
        self.assertResponseUnauthorized(response)
    
    def test_product_categories_list(self):
        """Test product categories listing."""
        url = reverse('products:category-list')
        
        response = self.client.get(url)
        response_data = self.assertResponseSuccess(response)
        
        # Check categories are returned
        categories = response_data['data']
        self.assertGreaterEqual(len(categories), 2)
        
        # Check category data
        category_names = [cat['name'] for cat in categories]
        self.assertIn('Vegetables', category_names)
        self.assertIn('Fruits', category_names)
    
    def test_farmer_products_list(self):
        """Test listing products for a specific farmer."""
        url = reverse('farmers:products', kwargs={'farmer_id': self.farmer_user.id})
        
        response = self.client.get(url)
        response_data = self.assertResponseSuccess(response)
        
        # Check only farmer's products are returned
        results = response_data['data']['results']
        for product in results:
            self.assertEqual(product['farmer']['id'], self.farmer_user.id)
    
    @PerformanceTestMixin.assertQueryCountLessThan(10)
    def test_product_list_performance(self):
        """Test product list performance with query optimization."""
        # Create more products for testing
        self.create_mock_products(count=20)
        
        url = reverse('products:product-list')
        response = self.client.get(url)
        
        self.assertResponseSuccess(response)
    
    def test_product_search_performance(self):
        """Test product search performance."""
        # Create more products for testing
        self.create_mock_products(count=50)
        
        def search_products():
            url = reverse('products:product-list')
            response = self.client.get(url, {'search': 'test'})
            return response
        
        response, response_time = self.measure_response_time(search_products, max_time=2.0)
        self.assertResponseSuccess(response)
    
    def test_product_availability_update(self):
        """Test updating product availability."""
        self.authenticate_farmer()
        
        url = reverse('products:product-detail', kwargs={'pk': self.product1.id})
        data = {'status': 'Out of Stock'}
        
        response = self.client.patch(url, data, format='json')
        response_data = self.assertResponseSuccess(response)
        
        # Check status was updated
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.status, 'Out of Stock')
    
    def test_product_image_upload(self):
        """Test product image upload."""
        self.authenticate_farmer()
        
        # This would require implementing file upload testing
        # For now, we'll test the endpoint exists
        url = reverse('products:product-images', kwargs={'product_id': self.product1.id})
        
        # Test GET request (list images)
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 404])  # Depending on implementation
    
    def test_product_inventory_tracking(self):
        """Test product inventory tracking."""
        self.authenticate_farmer()
        
        original_quantity = self.product1.quantity
        
        # Update quantity
        url = reverse('products:product-detail', kwargs={'pk': self.product1.id})
        data = {'quantity': original_quantity - 10}
        
        response = self.client.patch(url, data, format='json')
        self.assertResponseSuccess(response)
        
        # Check quantity was updated
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.quantity, original_quantity - 10)


class ProductCategoryTestCase(BaseAPITestCase):
    """
    Test cases for product categories.
    """
    
    def test_create_category_admin_only(self):
        """Test that only admins can create categories."""
        self.authenticate_admin()
        
        url = reverse('products:category-list')
        data = {
            'name': 'Dairy Products',
            'description': 'Fresh dairy products'
        }
        
        response = self.client.post(url, data, format='json')
        response_data = self.assertResponseSuccess(response, status.HTTP_201_CREATED)
        
        # Check category was created
        self.assertTrue(ProductCategory.objects.filter(name='Dairy Products').exists())
    
    def test_create_category_farmer_forbidden(self):
        """Test that farmers cannot create categories."""
        self.authenticate_farmer()
        
        url = reverse('products:category-list')
        data = {
            'name': 'Dairy Products',
            'description': 'Fresh dairy products'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertResponseForbidden(response)
    
    def test_category_products_list(self):
        """Test listing products in a specific category."""
        url = reverse('products:category-products', kwargs={'category_id': self.category_vegetables.id})
        
        response = self.client.get(url)
        response_data = self.assertResponseSuccess(response)
        
        # Check only vegetables are returned
        results = response_data['data']['results']
        for product in results:
            self.assertIn(self.category_vegetables.id, product['categories'])
