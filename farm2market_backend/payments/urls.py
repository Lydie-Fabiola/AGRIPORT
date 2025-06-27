"""
URL configuration for payments app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

app_name = 'payments'

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    # Payment endpoints will be added here
]
