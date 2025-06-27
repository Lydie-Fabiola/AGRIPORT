"""
URL configuration for analytics app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'analytics'

router = DefaultRouter()
router.register(r'reports', views.ReportViewSet, basename='report')
router.register(r'dashboard-widgets', views.DashboardWidgetViewSet, basename='dashboard-widget')

urlpatterns = [
    path('', include(router.urls)),

    # Farmer Analytics
    path('farmer/sales/', views.FarmerAnalyticsView.as_view(), {'action': 'sales'}, name='farmer-sales'),
    path('farmer/products/', views.FarmerAnalyticsView.as_view(), {'action': 'products'}, name='farmer-products'),
    path('farmer/customers/', views.FarmerAnalyticsView.as_view(), {'action': 'customers'}, name='farmer-customers'),
    path('farmer/performance/', views.FarmerAnalyticsView.as_view(), {'action': 'performance'}, name='farmer-performance'),

    # Buyer Analytics
    path('buyer/purchases/', views.BuyerAnalyticsView.as_view(), {'action': 'purchases'}, name='buyer-purchases'),
    path('buyer/savings/', views.BuyerAnalyticsView.as_view(), {'action': 'savings'}, name='buyer-savings'),
    path('buyer/preferences/', views.BuyerAnalyticsView.as_view(), {'action': 'preferences'}, name='buyer-preferences'),

    # Admin Analytics
    path('platform/overview/', views.AdminAnalyticsView.as_view(), {'action': 'overview'}, name='platform-overview'),
    path('platform/users/', views.AdminAnalyticsView.as_view(), {'action': 'users'}, name='platform-users'),
    path('platform/transactions/', views.AdminAnalyticsView.as_view(), {'action': 'transactions'}, name='platform-transactions'),
]
