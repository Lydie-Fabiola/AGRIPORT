"""
Security services for Farm2Market.
"""
import hashlib
import hmac
import secrets
import re
import magic
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import SecurityEvent, RateLimitViolation, FileUploadScan

User = get_user_model()


class SecurityService:
    """
    Main security service for logging and monitoring.
    """
    
    def log_security_event(self, event_type, severity, description, 
                          user=None, ip_address=None, user_agent=None, metadata=None):
        """
        Log a security event.
        """
        SecurityEvent.objects.create(
            user=user,
            event_type=event_type,
            severity=severity,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {}
        )
        
        # Send alerts for high/critical severity events
        if severity in ['high', 'critical']:
            self._send_security_alert(event_type, severity, description, user)
    
    def _send_security_alert(self, event_type, severity, description, user):
        """
        Send security alert to administrators.
        """
        # This would integrate with notification system
        from apps.notifications.services import send_system_notification
        
        # Get admin users
        admin_users = User.objects.filter(user_type='Admin', is_active=True)
        
        for admin in admin_users:
            send_system_notification(
                admin,
                'security_alert',
                {
                    'event_type': event_type,
                    'severity': severity,
                    'description': description,
                    'user_email': user.email if user else 'Unknown',
                    'timestamp': timezone.now().isoformat()
                }
            )


class InputValidationService:
    """
    Service for input validation and sanitization.
    """
    
    def __init__(self):
        # SQL injection patterns
        self.sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\b(OR|AND)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)",
            r"(--|#|/\*|\*/)",
            r"(\bxp_\w+)",
            r"(\bsp_\w+)",
        ]
        
        # XSS patterns
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>.*?</iframe>",
            r"<object[^>]*>.*?</object>",
            r"<embed[^>]*>.*?</embed>",
        ]
    
    def validate_input(self, data, field_name='input'):
        """
        Validate input for security threats.
        """
        if not isinstance(data, str):
            return {'is_valid': True, 'sanitized': data}
        
        issues = []
        
        # Check for SQL injection
        if self._contains_sql_injection(data):
            issues.append(f'{field_name} contains potential SQL injection')
        
        # Check for XSS
        if self._contains_xss(data):
            issues.append(f'{field_name} contains potential XSS')
        
        # Check for path traversal
        if self._contains_path_traversal(data):
            issues.append(f'{field_name} contains potential path traversal')
        
        # Sanitize the data
        sanitized = self._sanitize_input(data)
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'sanitized': sanitized
        }
    
    def _contains_sql_injection(self, data):
        """Check for SQL injection patterns."""
        data_lower = data.lower()
        
        for pattern in self.sql_patterns:
            if re.search(pattern, data_lower, re.IGNORECASE):
                return True
        
        return False
    
    def _contains_xss(self, data):
        """Check for XSS patterns."""
        data_lower = data.lower()
        
        for pattern in self.xss_patterns:
            if re.search(pattern, data_lower, re.IGNORECASE):
                return True
        
        return False
    
    def _contains_path_traversal(self, data):
        """Check for path traversal patterns."""
        patterns = [
            r"\.\./",
            r"\.\.\\",
            r"%2e%2e%2f",
            r"%2e%2e%5c",
        ]
        
        data_lower = data.lower()
        
        for pattern in patterns:
            if re.search(pattern, data_lower):
                return True
        
        return False
    
    def _sanitize_input(self, data):
        """Sanitize input data."""
        # Remove null bytes
        data = data.replace('\x00', '')
        
        # Remove control characters except newline and tab
        data = ''.join(char for char in data if ord(char) >= 32 or char in '\n\t')
        
        # Limit length
        max_length = getattr(settings, 'MAX_INPUT_LENGTH', 10000)
        if len(data) > max_length:
            data = data[:max_length]
        
        return data


class RateLimitingService:
    """
    Service for API rate limiting.
    """
    
    def __init__(self):
        self.default_limits = {
            'per_minute': 60,
            'per_hour': 1000,
            'per_day': 10000,
        }
        
        # Endpoint-specific limits
        self.endpoint_limits = {
            '/api/v1/auth/login/': {
                'per_minute': 5,
                'per_hour': 20,
            },
            '/api/v1/auth/register/': {
                'per_minute': 3,
                'per_hour': 10,
            },
            '/api/v1/auth/password-reset/': {
                'per_minute': 2,
                'per_hour': 5,
            },
            '/api/v1/messaging/': {
                'per_minute': 30,
                'per_hour': 500,
            },
        }
    
    def is_rate_limited(self, identifier, endpoint, request=None):
        """
        Check if request should be rate limited.
        """
        # Get limits for this endpoint
        limits = self.endpoint_limits.get(endpoint, self.default_limits)
        
        for period, limit in limits.items():
            if self._check_rate_limit(identifier, endpoint, period, limit):
                # Log violation
                self._log_rate_limit_violation(identifier, endpoint, period)
                
                # Log security event
                SecurityService().log_security_event(
                    event_type='rate_limit_exceeded',
                    severity='medium',
                    description=f'Rate limit exceeded for {endpoint}',
                    ip_address=self._get_client_ip(request) if request else None,
                    metadata={
                        'identifier': identifier,
                        'endpoint': endpoint,
                        'period': period,
                        'limit': limit
                    }
                )
                
                return True
        
        # Increment counters
        self._increment_counters(identifier, endpoint)
        
        return False
    
    def _check_rate_limit(self, identifier, endpoint, period, limit):
        """Check if rate limit is exceeded for a specific period."""
        key = f'rate_limit:{identifier}:{endpoint}:{period}'
        current_count = cache.get(key, 0)
        
        return current_count >= limit
    
    def _increment_counters(self, identifier, endpoint):
        """Increment rate limit counters."""
        periods = {
            'per_minute': 60,
            'per_hour': 3600,
            'per_day': 86400,
        }
        
        for period, timeout in periods.items():
            key = f'rate_limit:{identifier}:{endpoint}:{period}'
            
            try:
                cache.add(key, 0, timeout)
                cache.incr(key)
            except ValueError:
                # Key doesn't exist, set it
                cache.set(key, 1, timeout)
    
    def _log_rate_limit_violation(self, identifier, endpoint, period):
        """Log rate limit violation."""
        violation, created = RateLimitViolation.objects.get_or_create(
            identifier=identifier,
            endpoint=endpoint,
            limit_type=period,
            defaults={'violation_count': 1}
        )
        
        if not created:
            violation.violation_count += 1
            violation.save()
    
    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class FileSecurityService:
    """
    Service for secure file upload validation.
    """
    
    def __init__(self):
        # Allowed file types
        self.allowed_mime_types = {
            'images': [
                'image/jpeg', 'image/png', 'image/gif', 'image/webp'
            ],
            'documents': [
                'application/pdf', 'text/plain', 'text/csv',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            ],
            'archives': [
                'application/zip', 'application/x-rar-compressed'
            ]
        }
        
        # File size limits (in bytes)
        self.size_limits = {
            'images': 5 * 1024 * 1024,  # 5MB
            'documents': 10 * 1024 * 1024,  # 10MB
            'archives': 50 * 1024 * 1024,  # 50MB
        }
        
        # Dangerous file extensions
        self.dangerous_extensions = [
            '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
            '.jar', '.php', '.asp', '.aspx', '.jsp', '.py', '.rb', '.pl'
        ]
    
    def validate_file(self, file, file_type='images', user=None):
        """
        Validate uploaded file for security.
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'file_info': {}
        }
        
        # Check file size
        if file.size > self.size_limits.get(file_type, 5 * 1024 * 1024):
            validation_result['is_valid'] = False
            validation_result['errors'].append(
                f'File size exceeds limit of {self.size_limits[file_type] / (1024*1024):.1f}MB'
            )
        
        # Check file extension
        file_name = file.name.lower()
        if any(file_name.endswith(ext) for ext in self.dangerous_extensions):
            validation_result['is_valid'] = False
            validation_result['errors'].append('File type not allowed')
        
        # Check MIME type
        try:
            # Read first chunk to determine MIME type
            file.seek(0)
            file_content = file.read(1024)
            file.seek(0)
            
            mime_type = magic.from_buffer(file_content, mime=True)
            
            allowed_types = self.allowed_mime_types.get(file_type, [])
            if mime_type not in allowed_types:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f'File type {mime_type} not allowed')
            
            validation_result['file_info']['mime_type'] = mime_type
            
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append('Could not determine file type')
        
        # Calculate file hash
        try:
            file.seek(0)
            file_hash = hashlib.sha256()
            for chunk in iter(lambda: file.read(4096), b""):
                file_hash.update(chunk)
            file.seek(0)
            
            validation_result['file_info']['hash'] = file_hash.hexdigest()
            
        except Exception as e:
            validation_result['errors'].append('Could not calculate file hash')
        
        # Check for malicious content (basic)
        if self._scan_file_content(file):
            validation_result['is_valid'] = False
            validation_result['errors'].append('File contains suspicious content')
        
        # Log file upload scan
        if user:
            self._log_file_scan(
                user=user,
                file_name=file.name,
                file_size=file.size,
                file_hash=validation_result['file_info'].get('hash', ''),
                mime_type=validation_result['file_info'].get('mime_type', ''),
                scan_status='clean' if validation_result['is_valid'] else 'suspicious'
            )
        
        return validation_result
    
    def _scan_file_content(self, file):
        """
        Basic file content scanning for malicious patterns.
        """
        try:
            file.seek(0)
            content = file.read(8192).decode('utf-8', errors='ignore')
            file.seek(0)
            
            # Check for script tags and other suspicious content
            suspicious_patterns = [
                r'<script[^>]*>',
                r'javascript:',
                r'eval\s*\(',
                r'document\.write',
                r'window\.location',
                r'<?php',
                r'<%.*%>',
            ]
            
            for pattern in suspicious_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return True
            
            return False
            
        except Exception:
            # If we can't read the file, consider it suspicious
            return True
    
    def _log_file_scan(self, user, file_name, file_size, file_hash, 
                      mime_type, scan_status):
        """Log file upload scan."""
        FileUploadScan.objects.create(
            user=user,
            file_name=file_name,
            file_path='',  # Will be set after successful upload
            file_size=file_size,
            file_hash=file_hash,
            mime_type=mime_type,
            scan_status=scan_status,
            scanned_at=timezone.now()
        )


class EncryptionService:
    """
    Service for data encryption and decryption.
    """
    
    def __init__(self):
        self.secret_key = getattr(settings, 'ENCRYPTION_KEY', settings.SECRET_KEY)
    
    def encrypt_sensitive_data(self, data):
        """
        Encrypt sensitive data using HMAC.
        """
        if not isinstance(data, str):
            data = str(data)
        
        # Create HMAC signature
        signature = hmac.new(
            self.secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"{data}:{signature}"
    
    def decrypt_sensitive_data(self, encrypted_data):
        """
        Decrypt and verify sensitive data.
        """
        try:
            data, signature = encrypted_data.rsplit(':', 1)
            
            # Verify signature
            expected_signature = hmac.new(
                self.secret_key.encode(),
                data.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if hmac.compare_digest(signature, expected_signature):
                return data
            else:
                raise ValueError("Invalid signature")
                
        except ValueError:
            raise ValueError("Invalid encrypted data format")
    
    def hash_pii_data(self, data):
        """
        Hash PII data for logging (irreversible).
        """
        if not data:
            return None
        
        # Add salt to prevent rainbow table attacks
        salt = getattr(settings, 'PII_HASH_SALT', 'farm2market_salt')
        
        return hashlib.sha256(f"{salt}{data}".encode()).hexdigest()[:16]
