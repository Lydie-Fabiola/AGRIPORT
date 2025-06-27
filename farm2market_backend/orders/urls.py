"""
URL configuration for orders app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'orders'

router = DefaultRouter()
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'reservations', views.ReservationViewSet, basename='reservation')

urlpatterns = [
    path('', include(router.urls)),

    # Cart Management
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/items/<int:product_id>/', views.CartItemView.as_view(), name='cart-item'),
    path('cart/checkout/', views.CartCheckoutView.as_view(), name='cart-checkout'),
]
