from django.shortcuts import render
from rest_framework import generics, permissions
from .models import FarmerProfile
from .serializers import FarmerProfileSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from reservations.serializers import ReviewSerializer

# Create your views here.

class FarmerProfileMeView(generics.RetrieveUpdateAPIView):
    serializer_class = FarmerProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsFarmer]

    def get_object(self):
        return self.request.user.farmer_profile

class FarmerProfileDetailView(generics.RetrieveAPIView):
    queryset = FarmerProfile.objects.all()
    serializer_class = FarmerProfileSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=True, methods=['get'], url_path='ratings')
    def ratings(self, request, pk=None):
        farmer = self.get_object()
        reviews = farmer.reviews.all()
        avg_rating = farmer.average_rating()
        data = {
            'average_rating': avg_rating,
            'reviews': ReviewSerializer(reviews, many=True).data
        }
        return Response(data)
