"""
Serializers for user authentication and management.
"""
from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, FarmerProfile, BuyerProfile, AdminProfile
from .authentication import validate_password_strength

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text="Password must be at least 8 characters with uppercase, lowercase, digit, and special character."
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text="Confirm your password."
    )
    
    class Meta:
        model = User
        fields = [
            'email', 'username', 'first_name', 'last_name', 
            'phone_number', 'user_type', 'password', 'password_confirm'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'phone_number': {'required': True},
            'user_type': {'required': True},
        }
    
    def validate_email(self, value):
        """Validate email uniqueness."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def validate_username(self, value):
        """Validate username uniqueness."""
        if value and User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value
    
    def validate_password(self, value):
        """Validate password strength."""
        errors = validate_password_strength(value)
        if errors:
            raise serializers.ValidationError(errors)
        return value
    
    def validate(self, attrs):
        """Validate password confirmation."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': "Password confirmation doesn't match."
            })
        return attrs
    
    def create(self, validated_data):
        """Create user with validated data."""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        required=True
    )
    
    def validate(self, attrs):
        """Validate user credentials."""
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            # Check if user exists
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise serializers.ValidationError("Invalid email or password.")
            
            # Check if account is locked
            if user.is_account_locked:
                raise serializers.ValidationError(
                    "Account is temporarily locked due to multiple failed login attempts. "
                    "Please try again later."
                )
            
            # Authenticate user
            user = authenticate(request=self.context.get('request'), email=email, password=password)
            
            if not user:
                # Increment failed login attempts
                try:
                    user_obj = User.objects.get(email=email)
                    user_obj.increment_failed_login()
                except User.DoesNotExist:
                    pass
                raise serializers.ValidationError("Invalid email or password.")
            
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled.")
            
            # Reset failed login attempts on successful authentication
            user.reset_failed_login()
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError("Must include email and password.")


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile information.
    """
    full_name = serializers.ReadOnlyField()
    is_farmer = serializers.ReadOnlyField()
    is_buyer = serializers.ReadOnlyField()
    is_admin_user = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'phone_number', 'user_type', 'is_approved', 'email_verified',
            'phone_verified', 'is_active', 'date_joined', 'last_login',
            'full_name', 'is_farmer', 'is_buyer', 'is_admin_user'
        ]
        read_only_fields = [
            'id', 'email', 'user_type', 'is_approved', 'email_verified',
            'phone_verified', 'is_active', 'date_joined', 'last_login'
        ]


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change.
    """
    old_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        required=True
    )
    new_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        required=True
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        required=True
    )
    
    def validate_old_password(self, value):
        """Validate old password."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value
    
    def validate_new_password(self, value):
        """Validate new password strength."""
        errors = validate_password_strength(value)
        if errors:
            raise serializers.ValidationError(errors)
        return value
    
    def validate(self, attrs):
        """Validate password confirmation."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "Password confirmation doesn't match."
            })
        return attrs
    
    def save(self):
        """Change user password."""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for password reset request.
    """
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        """Validate that user with this email exists."""
        try:
            User.objects.get(email=value)
        except User.DoesNotExist:
            # Don't reveal that user doesn't exist for security
            pass
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for password reset confirmation.
    """
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        required=True
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        required=True
    )
    
    def validate_new_password(self, value):
        """Validate new password strength."""
        errors = validate_password_strength(value)
        if errors:
            raise serializers.ValidationError(errors)
        return value
    
    def validate(self, attrs):
        """Validate password confirmation and token."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "Password confirmation doesn't match."
            })
        
        # Validate token
        from .models import PasswordResetToken
        try:
            token = PasswordResetToken.objects.get(
                token=attrs['token'],
                is_used=False
            )
            if not token.is_valid:
                raise serializers.ValidationError({
                    'token': "Token is invalid or expired."
                })
            attrs['reset_token'] = token
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError({
                'token': "Invalid token."
            })
        
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    """
    Serializer for email verification.
    """
    token = serializers.CharField(required=True)
    
    def validate_token(self, value):
        """Validate email verification token."""
        from .models import EmailVerificationToken
        try:
            token = EmailVerificationToken.objects.get(
                token=value,
                is_used=False
            )
            if not token.is_valid:
                raise serializers.ValidationError("Token is invalid or expired.")
            return token
        except EmailVerificationToken.DoesNotExist:
            raise serializers.ValidationError("Invalid token.")


class SMSVerificationSerializer(serializers.Serializer):
    """
    Serializer for SMS verification.
    """
    phone_number = serializers.CharField(required=True)
    code = serializers.CharField(required=True, max_length=6, min_length=6)
    
    def validate(self, attrs):
        """Validate SMS verification code."""
        from .models import SMSVerificationToken
        try:
            token = SMSVerificationToken.objects.get(
                phone_number=attrs['phone_number'],
                token=attrs['code'],
                is_used=False
            )
            if not token.is_valid:
                raise serializers.ValidationError("Code is invalid or expired.")
            attrs['sms_token'] = token
        except SMSVerificationToken.DoesNotExist:
            raise serializers.ValidationError("Invalid verification code.")
        
        return attrs
