"""
Performance tests for Farm2Market platform.
"""
import time
from django.test import TestCase, override_settings
from django.db import connection
from django.core.cache import cache
from django.urls import reverse
from .test_base import BaseAPITestCase, PerformanceTestMixin, MockDataMixin


class DatabasePerformanceTestCase(BaseAPITestCase, PerformanceTestMixin, MockDataMixin):
    """
    Test cases for database performance optimization.
    """
    
    def setUp(self):
        super().setUp()
        # Create more test data for performance testing
        self.mock_users = self.create_mock_users(count=20)
        self.mock_products = self.create_mock_products(count=100)
    
    @override_settings(DEBUG=True)
    def test_product_list_query_optimization(self):
        """Test that product list uses optimized queries."""
        url = reverse('products:product-list')
        
        # Clear query log
        connection.queries_log.clear()
        
        response = self.client.get(url)
        self.assertResponseSuccess(response)
        
        # Check query count is reasonable
        query_count = len(connection.queries)
        self.assertLess(query_count, 10, f"Too many queries: {query_count}")
        
        # Check for N+1 query problems
        select_queries = [q for q in connection.queries if q['sql'].strip().upper().startswith('SELECT')]
        self.assertLess(len(select_queries), 8, "Possible N+1 query problem")
    
    @override_settings(DEBUG=True)
    def test_order_list_query_optimization(self):
        """Test that order list uses optimized queries."""
        # Create test orders
        for i in range(10):
            self.create_test_order()
        
        self.authenticate_buyer()
        url = reverse('orders:order-list')
        
        # Clear query log
        connection.queries_log.clear()
        
        response = self.client.get(url)
        self.assertResponseSuccess(response)
        
        # Check query count
        query_count = len(connection.queries)
        self.assertLess(query_count, 15, f"Too many queries: {query_count}")
    
    def test_product_search_performance(self):
        """Test product search performance with large dataset."""
        def search_products():
            url = reverse('products:product-list')
            response = self.client.get(url, {'search': 'test'})
            return response
        
        # Measure response time
        response, response_time = self.measure_response_time(search_products, max_time=2.0)
        self.assertResponseSuccess(response)
        
        print(f"Search response time: {response_time:.3f}s")
    
    def test_product_filtering_performance(self):
        """Test product filtering performance."""
        def filter_products():
            url = reverse('products:product-list')
            response = self.client.get(url, {
                'category': self.category_vegetables.id,
                'price_min': '3.00',
                'price_max': '10.00'
            })
            return response
        
        response, response_time = self.measure_response_time(filter_products, max_time=1.5)
        self.assertResponseSuccess(response)
        
        print(f"Filter response time: {response_time:.3f}s")
    
    def test_pagination_performance(self):
        """Test pagination performance with large datasets."""
        def get_paginated_products():
            url = reverse('products:product-list')
            response = self.client.get(url, {'page': 2, 'page_size': 20})
            return response
        
        response, response_time = self.measure_response_time(get_paginated_products, max_time=1.0)
        self.assertResponseSuccess(response)
        
        print(f"Pagination response time: {response_time:.3f}s")


class CachePerformanceTestCase(BaseAPITestCase, PerformanceTestMixin):
    """
    Test cases for caching performance.
    """
    
    def setUp(self):
        super().setUp()
        # Clear cache before each test
        cache.clear()
    
    def test_cache_hit_performance(self):
        """Test cache hit performance."""
        # First request (cache miss)
        url = reverse('products:product-list')
        
        start_time = time.time()
        response1 = self.client.get(url)
        miss_time = time.time() - start_time
        
        self.assertResponseSuccess(response1)
        
        # Second request (should be cached)
        start_time = time.time()
        response2 = self.client.get(url)
        hit_time = time.time() - start_time
        
        self.assertResponseSuccess(response2)
        
        # Cache hit should be significantly faster
        print(f"Cache miss time: {miss_time:.3f}s, Cache hit time: {hit_time:.3f}s")
        self.assertLess(hit_time, miss_time * 0.5, "Cache hit not significantly faster")
    
    def test_cache_invalidation(self):
        """Test cache invalidation on data changes."""
        self.authenticate_farmer()
        
        # Get product list (populate cache)
        list_url = reverse('products:product-list')
        response1 = self.client.get(list_url)
        self.assertResponseSuccess(response1)
        
        # Update a product (should invalidate cache)
        update_url = reverse('products:product-detail', kwargs={'pk': self.product1.id})
        update_data = {'product_name': 'Updated Product Name'}
        
        response2 = self.client.patch(update_url, update_data, format='json')
        self.assertResponseSuccess(response2)
        
        # Get product list again (should reflect changes)
        response3 = self.client.get(list_url)
        self.assertResponseSuccess(response3)
        
        # Check that the change is reflected
        products = response3.json()['data']['results']
        updated_product = next((p for p in products if p['id'] == self.product1.id), None)
        
        if updated_product:
            self.assertEqual(updated_product['product_name'], 'Updated Product Name')
    
    def test_user_session_caching(self):
        """Test user session data caching."""
        self.authenticate_farmer()
        
        # First profile request
        url = reverse('users:profile')
        
        start_time = time.time()
        response1 = self.client.get(url)
        first_time = time.time() - start_time
        
        self.assertResponseSuccess(response1)
        
        # Second profile request (should use cached session data)
        start_time = time.time()
        response2 = self.client.get(url)
        second_time = time.time() - start_time
        
        self.assertResponseSuccess(response2)
        
        print(f"First request: {first_time:.3f}s, Second request: {second_time:.3f}s")


class APIPerformanceTestCase(BaseAPITestCase, PerformanceTestMixin):
    """
    Test cases for API endpoint performance.
    """
    
    def test_authentication_performance(self):
        """Test authentication endpoint performance."""
        def login_user():
            url = reverse('users:login')
            data = {
                'email': 'farmer@test.com',
                'password': 'TestPass123!'
            }
            response = self.client.post(url, data, format='json')
            return response
        
        response, response_time = self.measure_response_time(login_user, max_time=1.0)
        self.assertResponseSuccess(response)
        
        print(f"Login response time: {response_time:.3f}s")
    
    def test_token_refresh_performance(self):
        """Test token refresh performance."""
        # First login to get refresh token
        login_url = reverse('users:login')
        login_data = {
            'email': 'farmer@test.com',
            'password': 'TestPass123!'
        }
        
        login_response = self.client.post(login_url, login_data, format='json')
        login_data = self.assertResponseSuccess(login_response)
        
        refresh_token = login_data['data']['tokens']['refresh']
        
        def refresh_token_request():
            url = reverse('users:token-refresh')
            data = {'refresh': refresh_token}
            response = self.client.post(url, data, format='json')
            return response
        
        response, response_time = self.measure_response_time(refresh_token_request, max_time=0.5)
        self.assertResponseSuccess(response)
        
        print(f"Token refresh response time: {response_time:.3f}s")
    
    def test_concurrent_requests_performance(self):
        """Test performance under concurrent requests."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            try:
                url = reverse('products:product-list')
                start_time = time.time()
                response = self.client.get(url)
                end_time = time.time()
                
                results.put({
                    'status_code': response.status_code,
                    'response_time': end_time - start_time
                })
            except Exception as e:
                results.put({'error': str(e)})
        
        # Create 10 concurrent threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Collect results
        response_times = []
        errors = 0
        
        while not results.empty():
            result = results.get()
            if 'error' in result:
                errors += 1
            else:
                response_times.append(result['response_time'])
        
        # Analyze results
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            
            print(f"Concurrent requests - Total time: {total_time:.3f}s")
            print(f"Average response time: {avg_response_time:.3f}s")
            print(f"Max response time: {max_response_time:.3f}s")
            print(f"Errors: {errors}")
            
            # Assert reasonable performance
            self.assertLess(avg_response_time, 2.0, "Average response time too high")
            self.assertLess(max_response_time, 5.0, "Max response time too high")
            self.assertEqual(errors, 0, "Errors occurred during concurrent requests")


class SecurityPerformanceTestCase(BaseAPITestCase):
    """
    Test cases for security feature performance impact.
    """
    
    def test_rate_limiting_performance(self):
        """Test that rate limiting doesn't significantly impact performance."""
        url = reverse('products:product-list')
        
        # Make multiple requests within rate limit
        response_times = []
        
        for i in range(5):
            start_time = time.time()
            response = self.client.get(url)
            end_time = time.time()
            
            self.assertResponseSuccess(response)
            response_times.append(end_time - start_time)
        
        # Check that response times are consistent
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        
        print(f"Rate limiting - Average time: {avg_time:.3f}s, Max time: {max_time:.3f}s")
        
        # Rate limiting shouldn't add significant overhead
        self.assertLess(max_time - avg_time, 0.5, "Rate limiting adds too much overhead")
    
    def test_input_validation_performance(self):
        """Test input validation performance impact."""
        self.authenticate_farmer()
        
        url = reverse('products:product-list')
        
        # Test with normal input
        start_time = time.time()
        response1 = self.client.post(url, {
            'product_name': 'Normal Product',
            'description': 'Normal description',
            'price': '10.00',
            'quantity': 50,
            'unit': 'kg'
        }, format='json')
        normal_time = time.time() - start_time
        
        # Test with input that requires validation
        start_time = time.time()
        response2 = self.client.post(url, {
            'product_name': 'Product with special chars !@#$%',
            'description': 'Description with <script>alert("test")</script>',
            'price': '10.00',
            'quantity': 50,
            'unit': 'kg'
        }, format='json')
        validation_time = time.time() - start_time
        
        print(f"Normal input: {normal_time:.3f}s, Validation input: {validation_time:.3f}s")
        
        # Validation shouldn't add significant overhead
        self.assertLess(validation_time - normal_time, 0.2, "Input validation adds too much overhead")


class LoadTestCase(BaseAPITestCase, MockDataMixin):
    """
    Load testing for the platform.
    """
    
    def setUp(self):
        super().setUp()
        # Create large dataset for load testing
        self.mock_users = self.create_mock_users(count=100)
        self.mock_products = self.create_mock_products(count=500)
    
    def test_large_dataset_performance(self):
        """Test performance with large datasets."""
        # Test product listing with large dataset
        url = reverse('products:product-list')
        
        start_time = time.time()
        response = self.client.get(url)
        end_time = time.time()
        
        self.assertResponseSuccess(response)
        
        response_time = end_time - start_time
        print(f"Large dataset response time: {response_time:.3f}s")
        
        # Should handle large datasets efficiently
        self.assertLess(response_time, 3.0, "Large dataset response time too high")
    
    def test_search_with_large_dataset(self):
        """Test search performance with large dataset."""
        url = reverse('products:product-list')
        
        start_time = time.time()
        response = self.client.get(url, {'search': 'test'})
        end_time = time.time()
        
        self.assertResponseSuccess(response)
        
        response_time = end_time - start_time
        print(f"Large dataset search time: {response_time:.3f}s")
        
        # Search should be efficient even with large datasets
        self.assertLess(response_time, 2.0, "Large dataset search time too high")
    
    def test_memory_usage(self):
        """Test memory usage during operations."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Get initial memory usage
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform memory-intensive operations
        url = reverse('products:product-list')
        
        for i in range(10):
            response = self.client.get(url)
            self.assertResponseSuccess(response)
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        memory_increase = final_memory - initial_memory
        
        print(f"Memory usage - Initial: {initial_memory:.1f}MB, Final: {final_memory:.1f}MB")
        print(f"Memory increase: {memory_increase:.1f}MB")
        
        # Memory increase should be reasonable
        self.assertLess(memory_increase, 100, "Memory usage increased too much")
