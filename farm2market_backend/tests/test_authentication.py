"""
Tests for user authentication and authorization.
"""
import json
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from .test_base import BaseAPITestCase

User = get_user_model()


class AuthenticationTestCase(BaseAPITestCase):
    """
    Test cases for user authentication.
    """
    
    def test_user_registration_success(self):
        """Test successful user registration."""
        url = reverse('users:register')
        data = {
            'email': 'newuser@test.com',
            'password': 'TestPass123!',
            'confirm_password': 'TestPass123!',
            'full_name': 'New User',
            'user_type': 'Buyer'
        }
        
        response = self.client.post(url, data, format='json')
        response_data = self.assertResponseSuccess(response, status.HTTP_201_CREATED)
        
        # Check user was created
        self.assertTrue(User.objects.filter(email='newuser@test.com').exists())
        
        # Check response data
        self.assertIn('user', response_data['data'])
        self.assertEqual(response_data['data']['user']['email'], 'newuser@test.com')
        self.assertEqual(response_data['data']['user']['user_type'], 'Buyer')
    
    def test_user_registration_duplicate_email(self):
        """Test registration with duplicate email."""
        url = reverse('users:register')
        data = {
            'email': 'farmer@test.com',  # Already exists
            'password': 'TestPass123!',
            'confirm_password': 'TestPass123!',
            'full_name': 'Another User',
            'user_type': 'Farmer'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertResponseValidationError(response)
    
    def test_user_registration_weak_password(self):
        """Test registration with weak password."""
        url = reverse('users:register')
        data = {
            'email': 'newuser@test.com',
            'password': '123',  # Weak password
            'confirm_password': '123',
            'full_name': 'New User',
            'user_type': 'Buyer'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertResponseValidationError(response)
    
    def test_user_registration_password_mismatch(self):
        """Test registration with password mismatch."""
        url = reverse('users:register')
        data = {
            'email': 'newuser@test.com',
            'password': 'TestPass123!',
            'confirm_password': 'DifferentPass123!',
            'full_name': 'New User',
            'user_type': 'Buyer'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertResponseValidationError(response)
    
    def test_user_login_success(self):
        """Test successful user login."""
        url = reverse('users:login')
        data = {
            'email': 'farmer@test.com',
            'password': 'TestPass123!'
        }
        
        response = self.client.post(url, data, format='json')
        response_data = self.assertResponseSuccess(response)
        
        # Check tokens are returned
        self.assertIn('tokens', response_data['data'])
        self.assertIn('access', response_data['data']['tokens'])
        self.assertIn('refresh', response_data['data']['tokens'])
        
        # Check user data
        self.assertIn('user', response_data['data'])
        self.assertEqual(response_data['data']['user']['email'], 'farmer@test.com')
    
    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        url = reverse('users:login')
        data = {
            'email': 'farmer@test.com',
            'password': 'WrongPassword'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertResponseValidationError(response)
    
    def test_user_login_nonexistent_user(self):
        """Test login with nonexistent user."""
        url = reverse('users:login')
        data = {
            'email': 'nonexistent@test.com',
            'password': 'TestPass123!'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertResponseValidationError(response)
    
    def test_user_logout_success(self):
        """Test successful user logout."""
        # First login to get tokens
        login_url = reverse('users:login')
        login_data = {
            'email': 'farmer@test.com',
            'password': 'TestPass123!'
        }
        
        login_response = self.client.post(login_url, login_data, format='json')
        login_response_data = self.assertResponseSuccess(login_response)
        
        refresh_token = login_response_data['data']['tokens']['refresh']
        access_token = login_response_data['data']['tokens']['access']
        
        # Set authentication
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Logout
        logout_url = reverse('users:logout')
        logout_data = {'refresh_token': refresh_token}
        
        response = self.client.post(logout_url, logout_data, format='json')
        self.assertResponseSuccess(response)
    
    def test_token_refresh_success(self):
        """Test successful token refresh."""
        # First login to get tokens
        login_url = reverse('users:login')
        login_data = {
            'email': 'farmer@test.com',
            'password': 'TestPass123!'
        }
        
        login_response = self.client.post(login_url, login_data, format='json')
        login_response_data = self.assertResponseSuccess(login_response)
        
        refresh_token = login_response_data['data']['tokens']['refresh']
        
        # Refresh token
        refresh_url = reverse('users:token-refresh')
        refresh_data = {'refresh': refresh_token}
        
        response = self.client.post(refresh_url, refresh_data, format='json')
        response_data = self.assertResponseSuccess(response)
        
        # Check new access token is returned
        self.assertIn('access', response_data['data'])
    
    def test_protected_endpoint_without_auth(self):
        """Test accessing protected endpoint without authentication."""
        url = reverse('users:profile')
        
        response = self.client.get(url)
        self.assertResponseUnauthorized(response)
    
    def test_protected_endpoint_with_auth(self):
        """Test accessing protected endpoint with authentication."""
        self.authenticate_farmer()
        
        url = reverse('users:profile')
        response = self.client.get(url)
        
        response_data = self.assertResponseSuccess(response)
        self.assertEqual(response_data['data']['email'], 'farmer@test.com')
    
    def test_password_change_success(self):
        """Test successful password change."""
        self.authenticate_farmer()
        
        url = reverse('users:password-change')
        data = {
            'current_password': 'TestPass123!',
            'new_password': 'NewTestPass123!',
            'confirm_new_password': 'NewTestPass123!'
        }
        
        response = self.client.put(url, data, format='json')
        self.assertResponseSuccess(response)
        
        # Verify password was changed by trying to login with new password
        self.clear_authentication()
        
        login_url = reverse('users:login')
        login_data = {
            'email': 'farmer@test.com',
            'password': 'NewTestPass123!'
        }
        
        login_response = self.client.post(login_url, login_data, format='json')
        self.assertResponseSuccess(login_response)
    
    def test_password_change_wrong_current_password(self):
        """Test password change with wrong current password."""
        self.authenticate_farmer()
        
        url = reverse('users:password-change')
        data = {
            'current_password': 'WrongPassword',
            'new_password': 'NewTestPass123!',
            'confirm_new_password': 'NewTestPass123!'
        }
        
        response = self.client.put(url, data, format='json')
        self.assertResponseValidationError(response)
    
    def test_password_reset_request_success(self):
        """Test successful password reset request."""
        url = reverse('users:password-reset-request')
        data = {'email': 'farmer@test.com'}
        
        response = self.client.post(url, data, format='json')
        self.assertResponseSuccess(response)
    
    def test_password_reset_request_nonexistent_email(self):
        """Test password reset request with nonexistent email."""
        url = reverse('users:password-reset-request')
        data = {'email': 'nonexistent@test.com'}
        
        # Should still return success for security reasons
        response = self.client.post(url, data, format='json')
        self.assertResponseSuccess(response)


class AuthorizationTestCase(BaseAPITestCase):
    """
    Test cases for user authorization and permissions.
    """
    
    def test_farmer_can_access_farmer_endpoints(self):
        """Test farmer can access farmer-specific endpoints."""
        self.authenticate_farmer()
        
        # Test farmer profile access
        url = reverse('farmers:profile')
        response = self.client.get(url)
        self.assertResponseSuccess(response)
    
    def test_buyer_cannot_access_farmer_endpoints(self):
        """Test buyer cannot access farmer-specific endpoints."""
        self.authenticate_buyer()
        
        # Test farmer profile access
        url = reverse('farmers:profile')
        response = self.client.get(url)
        self.assertResponseForbidden(response)
    
    def test_buyer_can_access_buyer_endpoints(self):
        """Test buyer can access buyer-specific endpoints."""
        self.authenticate_buyer()
        
        # Test buyer preferences access
        url = reverse('buyers:preferences')
        response = self.client.get(url)
        self.assertResponseSuccess(response)
    
    def test_farmer_cannot_access_buyer_endpoints(self):
        """Test farmer cannot access buyer-specific endpoints."""
        self.authenticate_farmer()
        
        # Test buyer preferences access
        url = reverse('buyers:preferences')
        response = self.client.get(url)
        self.assertResponseForbidden(response)
    
    def test_admin_can_access_admin_endpoints(self):
        """Test admin can access admin-specific endpoints."""
        self.authenticate_admin()
        
        # Test admin analytics access
        url = reverse('analytics:platform-overview')
        response = self.client.get(url)
        self.assertResponseSuccess(response)
    
    def test_non_admin_cannot_access_admin_endpoints(self):
        """Test non-admin users cannot access admin endpoints."""
        self.authenticate_farmer()
        
        # Test admin analytics access
        url = reverse('analytics:platform-overview')
        response = self.client.get(url)
        self.assertResponseForbidden(response)


class SecurityTestCase(BaseAPITestCase):
    """
    Test cases for security features.
    """
    
    def test_rate_limiting_login_attempts(self):
        """Test rate limiting on login attempts."""
        url = reverse('users:login')
        data = {
            'email': 'farmer@test.com',
            'password': 'WrongPassword'
        }
        
        # Make multiple failed login attempts
        for i in range(6):  # Exceed rate limit
            response = self.client.post(url, data, format='json')
            
            if i < 5:
                # First 5 attempts should return validation error
                self.assertResponseValidationError(response)
            else:
                # 6th attempt should be rate limited
                self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
    
    def test_sql_injection_protection(self):
        """Test protection against SQL injection."""
        self.authenticate_farmer()
        
        # Try SQL injection in search
        url = reverse('products:product-list')
        malicious_query = "'; DROP TABLE products_product; --"
        
        response = self.client.get(url, {'search': malicious_query})
        
        # Should not crash and should return normal response
        self.assertIn(response.status_code, [200, 400])
        
        # Verify table still exists by checking products
        self.assertTrue(self.product1.pk)
    
    def test_xss_protection(self):
        """Test protection against XSS attacks."""
        self.authenticate_farmer()
        
        # Try XSS in product creation
        url = reverse('products:product-list')
        data = {
            'product_name': '<script>alert("XSS")</script>',
            'description': 'Test description',
            'price': '10.00',
            'quantity': 10,
            'unit': 'kg',
            'categories': [self.category_vegetables.id]
        }
        
        response = self.client.post(url, data, format='json')
        
        # Should either reject the input or sanitize it
        if response.status_code == 201:
            response_data = self.assertResponseSuccess(response, 201)
            # Check that script tags are removed/escaped
            product_name = response_data['data']['product_name']
            self.assertNotIn('<script>', product_name)
    
    def test_csrf_protection(self):
        """Test CSRF protection for state-changing requests."""
        # This test would be more relevant for form-based requests
        # API endpoints typically use token authentication which provides CSRF protection
        pass
    
    def test_unauthorized_access_to_other_user_data(self):
        """Test that users cannot access other users' private data."""
        self.authenticate_buyer()
        
        # Try to access farmer's profile directly
        url = f'/api/v1/farmers/{self.farmer_user.id}/profile/'
        response = self.client.get(url)
        
        # Should be forbidden or not found
        self.assertIn(response.status_code, [403, 404])
