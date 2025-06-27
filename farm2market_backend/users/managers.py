from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """
    Custom user manager for the User model
    """
    
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and return a regular user with an email and password.
        """
        if not email:
            raise ValueError(_('The Email field must be set'))
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and return a superuser with an email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_approved', True)
        extra_fields.setdefault('user_type', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(email, password, **extra_fields)
    
    def create_farmer(self, email, password=None, **extra_fields):
        """
        Create and return a farmer user.
        """
        extra_fields.setdefault('user_type', 'farmer')
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)
    
    def create_buyer(self, email, password=None, **extra_fields):
        """
        Create and return a buyer user.
        """
        extra_fields.setdefault('user_type', 'buyer')
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)
    
    def get_farmers(self):
        """
        Return all farmer users.
        """
        return self.filter(user_type='farmer')
    
    def get_buyers(self):
        """
        Return all buyer users.
        """
        return self.filter(user_type='buyer')
    
    def get_admins(self):
        """
        Return all admin users.
        """
        return self.filter(user_type='admin')
    
    def get_approved_users(self):
        """
        Return all approved users.
        """
        return self.filter(is_approved=True)
    
    def get_pending_approval(self):
        """
        Return all users pending approval.
        """
        return self.filter(is_approved=False, is_active=True)
