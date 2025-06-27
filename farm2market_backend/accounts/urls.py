"""
URL configuration for accounts app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.users import views

app_name = 'accounts'

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),

    # Authentication endpoints
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('refresh/', views.TokenRefreshView.as_view(), name='refresh'),

    # Password management
    path('password/reset/', views.PasswordResetRequestView.as_view(), name='password_reset'),
    path('password/reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password/change/', views.PasswordChangeView.as_view(), name='password_change'),

    # Email verification
    path('email/verify/', views.EmailVerificationView.as_view(), name='email_verify'),
    path('email/resend/', views.ResendEmailVerificationView.as_view(), name='email_resend'),

    # SMS verification
    path('sms/verify/', views.SMSVerificationView.as_view(), name='sms_verify'),
    path('sms/send/', views.SendSMSVerificationView.as_view(), name='sms_send'),

    # User profile
    path('profile/', views.UserProfileView.as_view(), name='profile'),
]
