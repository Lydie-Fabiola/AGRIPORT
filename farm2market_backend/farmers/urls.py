"""
URL configuration for farmers app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'farmers'

router = DefaultRouter()
router.register(r'certifications', views.FarmCertificationViewSet, basename='certification')
router.register(r'farm-images', views.FarmImageViewSet, basename='farm-image')
router.register(r'locations', views.FarmLocationViewSet, basename='location')
router.register(r'products', views.FarmerProductViewSet, basename='product')
router.register(r'alerts', views.LowStockAlertViewSet, basename='alert')

urlpatterns = [
    path('', include(router.urls)),

    # Profile Management
    path('profile/', views.FarmerProfileView.as_view(), name='profile'),

    # Inventory Management
    path('inventory/', views.FarmerInventoryView.as_view(), name='inventory'),
    path('inventory/stock-adjustment/', views.StockAdjustmentView.as_view(), name='stock-adjustment'),
    path('inventory/movements/', views.StockMovementListView.as_view(), name='movements'),
    path('inventory/settings/', views.InventorySettingsView.as_view(), name='inventory-settings'),
]
