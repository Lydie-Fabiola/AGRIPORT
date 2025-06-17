from django.urls import path
from .views import FarmerProfileMeView, FarmerProfileDetailView

urlpatterns = [
    path('me/', FarmerProfileMeView.as_view(), name='farmer-profile-me'),
    path('<int:pk>/', FarmerProfileDetailView.as_view(), name='farmer-profile-detail'),
    path('<int:pk>/ratings/', FarmerProfileDetailView.as_view({'get': 'ratings'}), name='farmer-profile-ratings'),
] 