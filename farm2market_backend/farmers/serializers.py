"""
Serializers for farmer management.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.users.models import FarmerProfile
from .models import FarmCertification, FarmImage, FarmLocation
from apps.products.models import Product, Category, ProductImage, StockMovement, LowStockAlert, InventorySettings

User = get_user_model()


class FarmerBasicSerializer(serializers.ModelSerializer):
    """
    Basic serializer for farmer information (for use in other apps).
    """
    farmer_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'farmer_profile']
        read_only_fields = ['id', 'full_name', 'email', 'farmer_profile']

    def get_farmer_profile(self, obj):
        """Get basic farmer profile information."""
        try:
            profile = obj.farmer_profile
            return {
                'farm_name': profile.farm_name,
                'location': profile.location,
                'organic_certified': profile.organic_certified,
                'trust_badge': profile.trust_badge,
            }
        except:
            return None


class FarmerProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for farmer profile.
    """
    farmer_email = serializers.EmailField(source='farmer.email', read_only=True)
    farmer_name = serializers.CharField(source='farmer.full_name', read_only=True)
    farmer_username = serializers.CharField(source='farmer.username', read_only=True)
    
    class Meta:
        model = FarmerProfile
        fields = [
            'farmer', 'farmer_email', 'farmer_name', 'farmer_username',
            'location', 'trust_badge', 'farm_size', 'farming_experience',
            'specialization', 'bio', 'is_certified', 'certification_level',
            'farm_name', 'business_registration', 'tax_id', 'latitude',
            'longitude', 'created_at', 'updated_at'
        ]
        read_only_fields = ['farmer', 'trust_badge', 'created_at', 'updated_at']


class FarmCertificationSerializer(serializers.ModelSerializer):
    """
    Serializer for farm certifications.
    """
    farmer_name = serializers.CharField(source='farmer.full_name', read_only=True)
    is_expired = serializers.ReadOnlyField()
    is_valid = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()
    
    class Meta:
        model = FarmCertification
        fields = [
            'id', 'farmer', 'farmer_name', 'certification_type', 'certification_name',
            'issuing_authority', 'certificate_number', 'issue_date', 'expiry_date',
            'certificate_file', 'verification_status', 'verified_by', 'verified_at',
            'rejection_reason', 'notes', 'is_expired', 'is_valid', 'days_until_expiry',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'farmer', 'verification_status', 'verified_by', 'verified_at',
            'created_at', 'updated_at'
        ]
    
    def validate_certificate_file(self, value):
        """Validate certificate file."""
        if value:
            # Check file size (max 5MB)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("File size cannot exceed 5MB.")
            
            # Check file extension
            allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
            if not any(value.name.lower().endswith(ext) for ext in allowed_extensions):
                raise serializers.ValidationError(
                    "Only PDF, JPG, JPEG, and PNG files are allowed."
                )
        
        return value


class FarmImageSerializer(serializers.ModelSerializer):
    """
    Serializer for farm images.
    """
    farmer_name = serializers.CharField(source='farmer.full_name', read_only=True)
    
    class Meta:
        model = FarmImage
        fields = [
            'id', 'farmer', 'farmer_name', 'image', 'title', 'description',
            'is_primary', 'display_order', 'created_at', 'updated_at'
        ]
        read_only_fields = ['farmer', 'created_at', 'updated_at']
    
    def validate_image(self, value):
        """Validate image file."""
        if value:
            # Check file size (max 10MB)
            if value.size > 10 * 1024 * 1024:
                raise serializers.ValidationError("Image size cannot exceed 10MB.")
            
            # Check file extension
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
            if not any(value.name.lower().endswith(ext) for ext in allowed_extensions):
                raise serializers.ValidationError(
                    "Only JPG, JPEG, PNG, and WebP files are allowed."
                )
        
        return value


class FarmLocationSerializer(serializers.ModelSerializer):
    """
    Serializer for farm locations.
    """
    farmer_name = serializers.CharField(source='farmer.full_name', read_only=True)
    
    class Meta:
        model = FarmLocation
        fields = [
            'id', 'farmer', 'farmer_name', 'name', 'address', 'city', 'state',
            'country', 'postal_code', 'latitude', 'longitude', 'farm_size',
            'is_primary', 'is_active', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['farmer', 'created_at', 'updated_at']


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for product categories.
    """
    subcategories = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'description', 'parent', 'parent_name', 'full_name',
            'image', 'is_active', 'display_order', 'subcategories',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_subcategories(self, obj):
        """Get subcategories."""
        if obj.subcategories.exists():
            return CategorySerializer(obj.subcategories.filter(is_active=True), many=True).data
        return []


class ProductImageSerializer(serializers.ModelSerializer):
    """
    Serializer for product images.
    """
    class Meta:
        model = ProductImage
        fields = [
            'id', 'product', 'image', 'alt_text', 'is_primary',
            'display_order', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer for products.
    """
    farmer_name = serializers.CharField(source='farmer.full_name', read_only=True)
    farmer_username = serializers.CharField(source='farmer.username', read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    images = ProductImageSerializer(many=True, read_only=True)
    primary_image = serializers.SerializerMethodField()
    available_quantity = serializers.ReadOnlyField()
    is_in_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    location_name = serializers.CharField(source='location.name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'farmer', 'farmer_name', 'farmer_username', 'product_name',
            'description', 'price', 'quantity', 'unit', 'status', 'categories',
            'category_ids', 'sku', 'minimum_order_quantity', 'harvest_date',
            'expiry_date', 'organic_certified', 'location', 'location_name',
            'slug', 'featured', 'views_count', 'reserved_quantity', 'sold_quantity',
            'available_quantity', 'is_in_stock', 'is_low_stock', 'images',
            'primary_image', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'farmer', 'sku', 'slug', 'views_count', 'reserved_quantity',
            'sold_quantity', 'created_at', 'updated_at'
        ]
    
    def get_primary_image(self, obj):
        """Get primary image."""
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            return ProductImageSerializer(primary_image).data
        return None
    
    def create(self, validated_data):
        """Create product with categories."""
        category_ids = validated_data.pop('category_ids', [])
        product = Product.objects.create(**validated_data)
        
        if category_ids:
            categories = Category.objects.filter(id__in=category_ids)
            product.categories.set(categories)
        
        return product
    
    def update(self, instance, validated_data):
        """Update product with categories."""
        category_ids = validated_data.pop('category_ids', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if category_ids is not None:
            categories = Category.objects.filter(id__in=category_ids)
            instance.categories.set(categories)
        
        return instance


class StockMovementSerializer(serializers.ModelSerializer):
    """
    Serializer for stock movements.
    """
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    
    class Meta:
        model = StockMovement
        fields = [
            'id', 'product', 'product_name', 'movement_type', 'quantity',
            'reference_order', 'notes', 'created_by', 'created_by_name',
            'stock_after', 'created_at'
        ]
        read_only_fields = ['created_by', 'stock_after', 'created_at']


class StockAdjustmentSerializer(serializers.Serializer):
    """
    Serializer for stock adjustments.
    """
    product_id = serializers.IntegerField()
    adjustment_type = serializers.ChoiceField(choices=[
        ('set', 'Set to specific quantity'),
        ('add', 'Add quantity'),
        ('subtract', 'Subtract quantity')
    ])
    quantity = serializers.IntegerField(min_value=0)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    def validate_product_id(self, value):
        """Validate product exists and belongs to farmer."""
        try:
            product = Product.objects.get(id=value)
            request = self.context.get('request')
            if request and product.farmer != request.user:
                raise serializers.ValidationError("Product does not belong to you.")
            return value
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found.")


class LowStockAlertSerializer(serializers.ModelSerializer):
    """
    Serializer for low stock alerts.
    """
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    farmer_name = serializers.CharField(source='product.farmer.full_name', read_only=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.full_name', read_only=True)
    
    class Meta:
        model = LowStockAlert
        fields = [
            'id', 'product', 'product_name', 'farmer_name', 'threshold_quantity',
            'current_quantity', 'status', 'acknowledged_by', 'acknowledged_by_name',
            'acknowledged_at', 'resolved_at', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'acknowledged_by', 'acknowledged_at', 'resolved_at', 'created_at', 'updated_at'
        ]


class InventorySettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for inventory settings.
    """
    farmer_name = serializers.CharField(source='farmer.full_name', read_only=True)
    
    class Meta:
        model = InventorySettings
        fields = [
            'farmer', 'farmer_name', 'low_stock_threshold_percentage',
            'auto_low_stock_alerts', 'email_notifications', 'sms_notifications',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['farmer', 'created_at', 'updated_at']
