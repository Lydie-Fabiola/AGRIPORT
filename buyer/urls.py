from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import BuyerRegisterView, BuyerProfileMeView, WishlistItemViewSet

router = DefaultRouter()
router.register(r'wishlist', WishlistItemViewSet, basename='wishlist')

urlpatterns = [
    path('register/', BuyerRegisterView.as_view(), name='buyer-register'),
    path('me/', BuyerProfileMeView.as_view(), name='buyer-profile-me'),
] + router.urls
