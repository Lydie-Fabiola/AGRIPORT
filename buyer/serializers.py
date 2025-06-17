from rest_framework import serializers
from .models import BuyerProfile
from users.models import User

class BuyerProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    class Meta:
        model = BuyerProfile
        fields = ['id', 'user', 'email', 'full_name', 'phone_number', 'location', 'profile_image', 'bio']
        read_only_fields = ['id', 'user', 'email']

class BuyerRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    full_name = serializers.CharField(write_only=True)
    phone_number = serializers.CharField(write_only=True, required=False)
    location = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'full_name', 'phone_number', 'location']

    def create(self, validated_data):
        full_name = validated_data.pop('full_name', '')
        phone_number = validated_data.pop('phone_number', '')
        location = validated_data.pop('location', '')
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
            role='buyer',
            is_buyer=True
        )
        BuyerProfile.objects.filter(user=user).update(
            full_name=full_name,
            phone_number=phone_number,
            location=location
        )
        return user 