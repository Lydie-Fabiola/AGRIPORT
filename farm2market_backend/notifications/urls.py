"""
URL configuration for notifications app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'notifications'

router = DefaultRouter()
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'device-tokens', views.DeviceTokenViewSet, basename='device-token')

urlpatterns = [
    path('', include(router.urls)),

    # Notification Management
    path('preferences/', views.NotificationPreferencesView.as_view(), name='preferences'),
    path('test/', views.TestNotificationView.as_view(), name='test'),
]
