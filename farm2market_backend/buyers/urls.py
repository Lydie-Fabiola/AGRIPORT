"""
URL configuration for buyers app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'buyers'

router = DefaultRouter()
router.register(r'addresses', views.BuyerAddressViewSet, basename='address')
router.register(r'favorite-farmers', views.FavoriteFarmerViewSet, basename='favorite-farmer')
router.register(r'wishlist', views.WishlistViewSet, basename='wishlist')

urlpatterns = [
    path('', include(router.urls)),

    # Profile Management
    path('profile/', views.BuyerProfileView.as_view(), name='profile'),
    path('preferences/', views.BuyerPreferencesView.as_view(), name='preferences'),
]
