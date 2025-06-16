from django.shortcuts import render
from rest_framework import generics, permissions, viewsets
from users.models import User
from .models import BuyerProfile, WishlistItem
from .serializers import BuyerProfileSerializer, WishlistItemSerializer
from users.serializers import RegisterSerializer
from rest_framework.response import Response
from rest_framework import status

# Create your views here.

class BuyerRegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['role'] = 'buyer'
        data['is_buyer'] = True
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(RegisterSerializer(user).data, status=status.HTTP_201_CREATED, headers=headers)

class BuyerProfileMeView(generics.RetrieveUpdateAPIView):
    serializer_class = BuyerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.buyer_profile

class WishlistItemViewSet(viewsets.ModelViewSet):
    serializer_class = WishlistItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WishlistItem.objects.filter(buyer=self.request.user.buyer_profile)

    def perform_create(self, serializer):
        serializer.save(buyer=self.request.user.buyer_profile)
