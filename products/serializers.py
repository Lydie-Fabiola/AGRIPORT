from rest_framework import serializers
from .models import Product, Category

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'icon_url']

class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True, required=False
    )
    image = serializers.ImageField(required=False, allow_null=True)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)

    class Meta:
        model = Product
        fields = [
            'id', 'farmer', 'category', 'category_id', 'name', 'description', 'price', 'quantity', 'unit',
            'status', 'is_organic', 'is_fresh_today', 'harvest_date', 'image', 'created_at', 'updated_at',
            'latitude', 'longitude', 'featured', 'popularity_score'
        ]
        read_only_fields = ['id', 'farmer', 'created_at', 'updated_at', 'status', 'popularity_score'] 