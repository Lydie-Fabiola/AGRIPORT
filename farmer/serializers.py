from rest_framework import serializers
from .models import FarmerProfile

class FarmerProfileSerializer(serializers.ModelSerializer):
    profile_image = serializers.ImageField(required=False, allow_null=True)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)

    class Meta:
        model = FarmerProfile
        fields = [
            'id', 'user', 'name', 'bio', 'location', 'contact',
            'profile_image', 'slug', 'latitude', 'longitude'
        ]
        read_only_fields = ['id', 'user', 'slug']

    def update(self, instance, validated_data):
        # Handle image replacement
        image = validated_data.get('profile_image', None)
        if image and instance.profile_image:
            instance.profile_image.delete(save=False)
        return super().update(instance, validated_data) 