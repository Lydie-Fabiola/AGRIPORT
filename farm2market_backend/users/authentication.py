"""
Custom JWT authentication utilities for Farm2Market.
"""
import uuid
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework import exceptions
from .models import User

User = get_user_model()


class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that checks for account locks and verification.
    """
    
    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
        
        # Check if account is locked
        if user.is_account_locked:
            raise exceptions.AuthenticationFailed(
                'Account is temporarily locked due to multiple failed login attempts.'
            )
        
        # Check if account is approved (for farmers and buyers)
        if user.user_type in ['Farmer', 'Buyer'] and not user.is_approved:
            raise exceptions.AuthenticationFailed(
                'Account is pending approval. Please wait for admin approval.'
            )
        
        return (user, validated_token)


class CustomRefreshToken(RefreshToken):
    """
    Custom refresh token with additional user information in payload.
    """
    
    @classmethod
    def for_user(cls, user):
        """
        Create a refresh token for the given user with custom payload.
        """
        token = super().for_user(user)
        
        # Add custom claims
        token['user_type'] = user.user_type
        token['is_approved'] = user.is_approved
        token['email_verified'] = user.email_verified
        token['phone_verified'] = user.phone_verified
        token['full_name'] = user.full_name
        token['username'] = user.username
        
        # Add profile information if available
        if hasattr(user, 'farmer_profile'):
            token['profile_type'] = 'farmer'
            token['trust_badge'] = user.farmer_profile.trust_badge
        elif hasattr(user, 'buyer_profile'):
            token['profile_type'] = 'buyer'
            token['company_name'] = getattr(user.buyer_profile, 'company_name', '')
        elif hasattr(user, 'admin_profile'):
            token['profile_type'] = 'admin'
            token['department'] = getattr(user.admin_profile, 'department', '')
        
        return token


class TokenBlacklist:
    """
    Simple token blacklist implementation using cache.
    """
    
    @staticmethod
    def blacklist_token(token):
        """
        Add token to blacklist.
        """
        from django.core.cache import cache
        
        # Extract token ID and expiration
        try:
            token_id = str(token['jti'])
            exp = token['exp']
            
            # Calculate TTL (time to live) for cache
            now = timezone.now().timestamp()
            ttl = max(0, int(exp - now))
            
            # Store in cache with TTL
            cache.set(f"blacklisted_token_{token_id}", True, timeout=ttl)
            return True
        except (KeyError, TypeError):
            return False
    
    @staticmethod
    def is_blacklisted(token):
        """
        Check if token is blacklisted.
        """
        from django.core.cache import cache
        
        try:
            token_id = str(token['jti'])
            return cache.get(f"blacklisted_token_{token_id}", False)
        except (KeyError, TypeError):
            return False


def generate_verification_token():
    """
    Generate a secure verification token.
    """
    return uuid.uuid4().hex


def generate_sms_code():
    """
    Generate a 6-digit SMS verification code.
    """
    import random
    return f"{random.randint(100000, 999999)}"


def create_email_verification_token(user):
    """
    Create an email verification token for the user.
    """
    from .models import EmailVerificationToken
    
    # Invalidate existing tokens
    EmailVerificationToken.objects.filter(
        user=user, 
        is_used=False
    ).update(is_used=True)
    
    # Create new token
    token = EmailVerificationToken.objects.create(
        user=user,
        token=generate_verification_token(),
        expires_at=timezone.now() + timedelta(hours=24)
    )
    
    return token


def create_sms_verification_token(user, phone_number):
    """
    Create an SMS verification token for the user.
    """
    from .models import SMSVerificationToken
    
    # Invalidate existing tokens for this phone number
    SMSVerificationToken.objects.filter(
        user=user,
        phone_number=phone_number,
        is_used=False
    ).update(is_used=True)
    
    # Create new token
    token = SMSVerificationToken.objects.create(
        user=user,
        token=generate_sms_code(),
        phone_number=phone_number,
        expires_at=timezone.now() + timedelta(minutes=10)
    )
    
    return token


def create_password_reset_token(user):
    """
    Create a password reset token for the user.
    """
    from .models import PasswordResetToken
    
    # Invalidate existing tokens
    PasswordResetToken.objects.filter(
        user=user,
        is_used=False
    ).update(is_used=True)
    
    # Create new token
    token = PasswordResetToken.objects.create(
        user=user,
        token=generate_verification_token(),
        expires_at=timezone.now() + timedelta(hours=1)
    )
    
    return token


def validate_password_strength(password):
    """
    Validate password strength according to security requirements.
    """
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter.")
    
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter.")
    
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit.")
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain at least one special character.")
    
    # Check for common passwords
    common_passwords = [
        'password', '123456', '123456789', 'qwerty', 'abc123',
        'password123', 'admin', 'letmein', 'welcome', 'monkey'
    ]
    
    if password.lower() in common_passwords:
        errors.append("Password is too common. Please choose a more secure password.")
    
    return errors
