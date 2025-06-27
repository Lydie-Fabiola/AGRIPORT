"""
URL configuration for users app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

app_name = 'users'

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    # User management endpoints will be added here
    # path('profile/', views.UserProfileView.as_view(), name='profile'),
    # path('profile/update/', views.UpdateProfileView.as_view(), name='update_profile'),
]
