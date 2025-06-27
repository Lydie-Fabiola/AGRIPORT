"""
Simple tests to verify the testing framework works.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class SimpleTestCase(TestCase):
    """
    Simple test cases to verify basic functionality.
    """
    
    def test_django_setup(self):
        """Test that Django is properly set up."""
        self.assertTrue(True)
    
    def test_user_model_exists(self):
        """Test that the User model exists."""
        self.assertIsNotNone(User)
    
    def test_create_user(self):
        """Test creating a user."""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )
        
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.full_name, 'Test User')
        self.assertTrue(user.check_password('testpass123'))
    
    def test_database_connection(self):
        """Test database connection."""
        # This will fail if database connection is not working
        count = User.objects.count()
        self.assertGreaterEqual(count, 0)
    
    def test_basic_math(self):
        """Test basic functionality."""
        self.assertEqual(2 + 2, 4)
        self.assertNotEqual(2 + 2, 5)
    
    def test_string_operations(self):
        """Test string operations."""
        test_string = "Farm2Market"
        self.assertIn("Farm", test_string)
        self.assertEqual(len(test_string), 11)
    
    def test_list_operations(self):
        """Test list operations."""
        test_list = [1, 2, 3, 4, 5]
        self.assertEqual(len(test_list), 5)
        self.assertIn(3, test_list)
        self.assertEqual(test_list[0], 1)
    
    def test_dict_operations(self):
        """Test dictionary operations."""
        test_dict = {'name': 'Farm2Market', 'type': 'platform'}
        self.assertEqual(test_dict['name'], 'Farm2Market')
        self.assertIn('type', test_dict)
        self.assertEqual(len(test_dict), 2)
