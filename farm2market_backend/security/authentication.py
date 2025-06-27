"""
Enhanced authentication security for Farm2Market.
"""
import hashlib
import secrets
import re
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from django.core.cache import cache
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from .models import LoginAttempt, AccountLockout, SecurityEvent
from .services import SecurityService


class SecureAuthenticationService:
    """
    Enhanced authentication service with security features.
    """
    
    def __init__(self):
        self.security_service = SecurityService()
        
        # Security settings
        self.max_failed_attempts = getattr(settings, 'MAX_FAILED_LOGIN_ATTEMPTS', 5)
        self.lockout_duration = getattr(settings, 'ACCOUNT_LOCKOUT_DURATION', 30)  # minutes
        self.password_min_length = getattr(settings, 'PASSWORD_MIN_LENGTH', 8)
        self.jwt_access_token_lifetime = getattr(settings, 'JWT_ACCESS_TOKEN_LIFETIME', 15)  # minutes
        self.jwt_refresh_token_lifetime = getattr(settings, 'JWT_REFRESH_TOKEN_LIFETIME', 7)  # days
    
    def authenticate_user(self, email, password, request=None):
        """
        Authenticate user with enhanced security checks.
        """
        ip_address = self._get_client_ip(request) if request else None
        user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
        
        # Check if account is locked
        if self._is_account_locked(email):
            self._log_login_attempt(
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                status='blocked',
                failure_reason='Account locked'
            )
            
            self.security_service.log_security_event(
                event_type='login_failed',
                severity='medium',
                description=f'Login attempt on locked account: {email}',
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return {
                'success': False,
                'error': 'Account is temporarily locked due to multiple failed login attempts.',
                'locked_until': self._get_lockout_expiry(email)
            }
        
        # Check rate limiting
        if self._is_rate_limited(ip_address, email):
            self._log_login_attempt(
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                status='blocked',
                failure_reason='Rate limited'
            )
            
            return {
                'success': False,
                'error': 'Too many login attempts. Please try again later.'
            }
        
        # Authenticate user
        user = authenticate(username=email, password=password)
        
        if user:
            if not user.is_active:
                self._log_login_attempt(
                    user=user,
                    email=email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status='failed',
                    failure_reason='Account inactive'
                )
                
                return {
                    'success': False,
                    'error': 'Account is inactive. Please contact support.'
                }
            
            # Successful login
            self._log_login_attempt(
                user=user,
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                status='success'
            )
            
            # Clear failed attempts
            self._clear_failed_attempts(email)
            
            # Generate secure tokens
            tokens = self._generate_tokens(user)
            
            # Log security event
            self.security_service.log_security_event(
                user=user,
                event_type='login_success',
                severity='low',
                description=f'Successful login from {ip_address}',
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return {
                'success': True,
                'user': user,
                'tokens': tokens
            }
        
        else:
            # Failed login
            self._log_login_attempt(
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                status='failed',
                failure_reason='Invalid credentials'
            )
            
            # Increment failed attempts
            failed_count = self._increment_failed_attempts(email, ip_address)
            
            # Check if account should be locked
            if failed_count >= self.max_failed_attempts:
                self._lock_account(email, ip_address, failed_count)
                
                self.security_service.log_security_event(
                    event_type='account_locked',
                    severity='high',
                    description=f'Account locked after {failed_count} failed attempts: {email}',
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                return {
                    'success': False,
                    'error': 'Account has been locked due to multiple failed login attempts.',
                    'locked_until': self._get_lockout_expiry(email)
                }
            
            return {
                'success': False,
                'error': 'Invalid email or password.',
                'attempts_remaining': self.max_failed_attempts - failed_count
            }
    
    def validate_password_strength(self, password):
        """
        Validate password strength according to security requirements.
        """
        errors = []
        
        # Minimum length
        if len(password) < self.password_min_length:
            errors.append(f'Password must be at least {self.password_min_length} characters long.')
        
        # Must contain uppercase letter
        if not re.search(r'[A-Z]', password):
            errors.append('Password must contain at least one uppercase letter.')
        
        # Must contain lowercase letter
        if not re.search(r'[a-z]', password):
            errors.append('Password must contain at least one lowercase letter.')
        
        # Must contain digit
        if not re.search(r'\d', password):
            errors.append('Password must contain at least one digit.')
        
        # Must contain special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append('Password must contain at least one special character.')
        
        # Check against common passwords
        if self._is_common_password(password):
            errors.append('Password is too common. Please choose a more unique password.')
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    def _generate_tokens(self, user):
        """
        Generate secure JWT tokens with short expiry.
        """
        refresh = RefreshToken.for_user(user)
        
        # Customize token claims
        refresh['user_id'] = user.id
        refresh['email'] = user.email
        refresh['user_type'] = user.user_type
        
        # Set custom expiry times
        refresh.set_exp(lifetime=timedelta(days=self.jwt_refresh_token_lifetime))
        
        access_token = refresh.access_token
        access_token.set_exp(lifetime=timedelta(minutes=self.jwt_access_token_lifetime))
        
        return {
            'access': str(access_token),
            'refresh': str(refresh),
            'access_expires_in': self.jwt_access_token_lifetime * 60,  # seconds
            'refresh_expires_in': self.jwt_refresh_token_lifetime * 24 * 60 * 60,  # seconds
        }
    
    def _is_account_locked(self, email):
        """
        Check if account is currently locked.
        """
        try:
            lockout = AccountLockout.objects.filter(
                user__email=email,
                is_active=True
            ).latest('locked_at')
            
            # Check if lockout has expired
            lockout_expiry = lockout.locked_at + timedelta(minutes=self.lockout_duration)
            
            if timezone.now() > lockout_expiry:
                lockout.unlock()
                return False
            
            return True
            
        except AccountLockout.DoesNotExist:
            return False
    
    def _get_lockout_expiry(self, email):
        """
        Get lockout expiry time.
        """
        try:
            lockout = AccountLockout.objects.filter(
                user__email=email,
                is_active=True
            ).latest('locked_at')
            
            return lockout.locked_at + timedelta(minutes=self.lockout_duration)
            
        except AccountLockout.DoesNotExist:
            return None
    
    def _is_rate_limited(self, ip_address, email):
        """
        Check if IP or email is rate limited.
        """
        if not ip_address:
            return False
        
        # Check IP-based rate limiting
        ip_key = f'login_attempts_ip:{ip_address}'
        ip_attempts = cache.get(ip_key, 0)
        
        if ip_attempts >= 10:  # 10 attempts per hour per IP
            return True
        
        # Check email-based rate limiting
        email_key = f'login_attempts_email:{email}'
        email_attempts = cache.get(email_key, 0)
        
        if email_attempts >= 5:  # 5 attempts per hour per email
            return True
        
        return False
    
    def _increment_failed_attempts(self, email, ip_address):
        """
        Increment failed login attempts counter.
        """
        # Database counter
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user = User.objects.get(email=email)
            failed_count = LoginAttempt.objects.filter(
                user=user,
                status='failed',
                timestamp__gte=timezone.now() - timedelta(minutes=self.lockout_duration)
            ).count() + 1
        except User.DoesNotExist:
            failed_count = LoginAttempt.objects.filter(
                email=email,
                status='failed',
                timestamp__gte=timezone.now() - timedelta(minutes=self.lockout_duration)
            ).count() + 1
        
        # Cache-based rate limiting
        if ip_address:
            ip_key = f'login_attempts_ip:{ip_address}'
            cache.set(ip_key, cache.get(ip_key, 0) + 1, 3600)  # 1 hour
        
        email_key = f'login_attempts_email:{email}'
        cache.set(email_key, cache.get(email_key, 0) + 1, 3600)  # 1 hour
        
        return failed_count
    
    def _clear_failed_attempts(self, email):
        """
        Clear failed login attempts after successful login.
        """
        # Clear cache
        email_key = f'login_attempts_email:{email}'
        cache.delete(email_key)
    
    def _lock_account(self, email, ip_address, failed_count):
        """
        Lock user account due to failed attempts.
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user = User.objects.get(email=email)
            
            AccountLockout.objects.create(
                user=user,
                ip_address=ip_address,
                failed_attempts=failed_count
            )
            
        except User.DoesNotExist:
            pass
    
    def _log_login_attempt(self, email, ip_address, user_agent, status, 
                          failure_reason='', user=None):
        """
        Log login attempt for security monitoring.
        """
        LoginAttempt.objects.create(
            user=user,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            failure_reason=failure_reason
        )
    
    def _is_common_password(self, password):
        """
        Check if password is in common passwords list.
        """
        # This would check against a list of common passwords
        # For now, we'll check against a few obvious ones
        common_passwords = [
            'password', '123456', '123456789', 'qwerty', 'abc123',
            'password123', 'admin', 'letmein', 'welcome', 'monkey'
        ]
        
        return password.lower() in common_passwords
    
    def _get_client_ip(self, request):
        """
        Get client IP address from request.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class APIKeyAuthentication:
    """
    API key authentication for external integrations.
    """
    
    def authenticate(self, request):
        """
        Authenticate using API key.
        """
        api_key = self._get_api_key_from_request(request)
        
        if not api_key:
            return None
        
        try:
            from .models import APIKey
            
            api_key_obj = APIKey.objects.get(
                key=api_key,
                is_active=True
            )
            
            # Check if expired
            if api_key_obj.is_expired:
                return None
            
            # Update last used
            api_key_obj.update_last_used()
            
            return (api_key_obj.user, api_key_obj)
            
        except APIKey.DoesNotExist:
            return None
    
    def _get_api_key_from_request(self, request):
        """
        Extract API key from request headers.
        """
        # Check Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('ApiKey '):
            return auth_header[7:]
        
        # Check X-API-Key header
        return request.META.get('HTTP_X_API_KEY')


def generate_api_key():
    """
    Generate a secure API key.
    """
    return secrets.token_urlsafe(32)
