"""
Views for user authentication and management.
"""
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.core.responses import StandardResponse
from apps.core.exceptions import ValidationError, NotFoundError, BusinessLogicError
from apps.core.ratelimit import apply_rate_limits
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    PasswordChangeSerializer, PasswordResetRequestSerializer, 
    PasswordResetConfirmSerializer, EmailVerificationSerializer,
    SMSVerificationSerializer
)
from .authentication import (
    CustomRefreshToken, TokenBlacklist, create_email_verification_token,
    create_sms_verification_token, create_password_reset_token
)
from .permissions import IsProfileOwner
from .models import User, EmailVerificationToken, SMSVerificationToken, PasswordResetToken

User = get_user_model()


@apply_rate_limits
class UserRegistrationView(APIView):
    """
    User registration endpoint.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Create email verification token
            email_token = create_email_verification_token(user)
            
            # TODO: Send verification email
            # send_verification_email.delay(user.id, email_token.token)
            
            # Create response data
            response_data = {
                'user': UserProfileSerializer(user).data,
                'message': 'Registration successful. Please check your email for verification instructions.'
            }
            
            return StandardResponse.created(
                data=response_data,
                message='User registered successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Registration failed.'
        )


@apply_rate_limits
class UserLoginView(APIView):
    """
    User login endpoint with JWT token generation.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Generate JWT tokens
            refresh = CustomRefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            response_data = {
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'access': str(access_token),
                    'refresh': str(refresh),
                },
                'message': 'Login successful.'
            }
            
            return StandardResponse.success(
                data=response_data,
                message='Login successful.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Login failed.'
        )


class UserLogoutView(APIView):
    """
    User logout endpoint with token blacklisting.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                # Blacklist the token
                TokenBlacklist.blacklist_token(token)
                
            return StandardResponse.success(
                message='Logout successful.'
            )
        except Exception as e:
            return StandardResponse.error(
                message='Logout failed.',
                details={'error': str(e)}
            )


class TokenRefreshView(TokenRefreshView):
    """
    Custom token refresh view.
    """
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            return StandardResponse.success(
                data=response.data,
                message='Token refreshed successfully.'
            )
        return response


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    User profile view for retrieving and updating profile.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsProfileOwner]
    
    def get_object(self):
        return self.request.user
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return StandardResponse.success(
            data=serializer.data,
            message='Profile retrieved successfully.'
        )
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            self.perform_update(serializer)
            return StandardResponse.updated(
                data=serializer.data,
                message='Profile updated successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Profile update failed.'
        )


class PasswordChangeView(APIView):
    """
    Password change endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def put(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return StandardResponse.success(
                message='Password changed successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Password change failed.'
        )


@apply_rate_limits
class PasswordResetRequestView(APIView):
    """
    Password reset request endpoint.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            
            try:
                user = User.objects.get(email=email)
                reset_token = create_password_reset_token(user)
                
                # TODO: Send password reset email
                # send_password_reset_email.delay(user.id, reset_token.token)
                
            except User.DoesNotExist:
                # Don't reveal that user doesn't exist
                pass
            
            return StandardResponse.success(
                message='If an account with this email exists, you will receive password reset instructions.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Password reset request failed.'
        )


class PasswordResetConfirmView(APIView):
    """
    Password reset confirmation endpoint.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            reset_token = serializer.validated_data['reset_token']
            new_password = serializer.validated_data['new_password']
            
            # Reset password
            user = reset_token.user
            user.set_password(new_password)
            user.save()
            
            # Mark token as used
            reset_token.mark_as_used()
            
            return StandardResponse.success(
                message='Password reset successful. You can now login with your new password.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Password reset failed.'
        )


class EmailVerificationView(APIView):
    """
    Email verification endpoint.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data['token']
            
            # Mark email as verified
            user = token.user
            user.email_verified = True
            user.save(update_fields=['email_verified'])
            
            # Mark token as used
            token.mark_as_used()
            
            return StandardResponse.success(
                message='Email verified successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='Email verification failed.'
        )


@apply_rate_limits
class ResendEmailVerificationView(APIView):
    """
    Resend email verification endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if user.email_verified:
            return StandardResponse.error(
                message='Email is already verified.',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Create new verification token
        email_token = create_email_verification_token(user)
        
        # TODO: Send verification email
        # send_verification_email.delay(user.id, email_token.token)
        
        return StandardResponse.success(
            message='Verification email sent successfully.'
        )


class SMSVerificationView(APIView):
    """
    SMS verification endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = SMSVerificationSerializer(data=request.data)
        if serializer.is_valid():
            sms_token = serializer.validated_data['sms_token']
            
            # Mark phone as verified
            user = request.user
            user.phone_verified = True
            user.phone_number = sms_token.phone_number
            user.save(update_fields=['phone_verified', 'phone_number'])
            
            # Mark token as used
            sms_token.mark_as_used()
            
            return StandardResponse.success(
                message='Phone number verified successfully.'
            )
        
        return StandardResponse.validation_error(
            errors=serializer.errors,
            message='SMS verification failed.'
        )


@apply_rate_limits
class SendSMSVerificationView(APIView):
    """
    Send SMS verification code endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        phone_number = request.data.get('phone_number')
        if not phone_number:
            return StandardResponse.validation_error(
                errors={'phone_number': ['This field is required.']},
                message='Phone number is required.'
            )
        
        user = request.user
        sms_token = create_sms_verification_token(user, phone_number)
        
        # TODO: Send SMS
        # send_sms_verification.delay(phone_number, sms_token.token)
        
        return StandardResponse.success(
            message='SMS verification code sent successfully.'
        )
