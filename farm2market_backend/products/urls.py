"""
URL configuration for products app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .discovery_views import (
    ProductSearchView, ProductBrowseView, CategoryListView,
    FeaturedProductsView, NearbyProductsView, ProductDetailView,
    ProductRecommendationsView, PopularSearchesView, search_suggestions
)

app_name = 'products'

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),

    # Product Discovery & Search
    path('search/', ProductSearchView.as_view(), name='search'),
    path('browse/', ProductBrowseView.as_view(), name='browse'),
    path('categories/', CategoryListView.as_view(), name='categories'),
    path('featured/', FeaturedProductsView.as_view(), name='featured'),
    path('nearby/', NearbyProductsView.as_view(), name='nearby'),
    path('recommendations/', ProductRecommendationsView.as_view(), name='recommendations'),
    path('popular-searches/', PopularSearchesView.as_view(), name='popular-searches'),
    path('search-suggestions/', search_suggestions, name='search-suggestions'),

    # Product Details
    path('<int:id>/', ProductDetailView.as_view(), name='detail'),
]
