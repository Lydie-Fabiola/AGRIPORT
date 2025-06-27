"""
Serializers for buyer management.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.users.models import BuyerProfile
from .models import BuyerAddress, BuyerPreferences, FavoriteFarmer, Wishlist
from apps.products.models import Product, Category
from apps.farmers.serializers import ProductSerializer

User = get_user_model()


class BuyerProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for buyer profile.
    """
    buyer_email = serializers.EmailField(source='buyer.email', read_only=True)
    buyer_name = serializers.CharField(source='buyer.full_name', read_only=True)
    buyer_username = serializers.CharField(source='buyer.username', read_only=True)
    
    class Meta:
        model = BuyerProfile
        fields = [
            'buyer', 'buyer_email', 'buyer_name', 'buyer_username',
            'location', 'company_name', 'business_type', 'business_registration',
            'tax_id', 'preferred_products', 'bio', 'preferred_payment_method',
            'average_order_value', 'purchase_frequency', 'is_verified_buyer',
            'verification_documents', 'created_at', 'updated_at'
        ]
        read_only_fields = ['buyer', 'is_verified_buyer', 'created_at', 'updated_at']
    
    def validate_verification_documents(self, value):
        """Validate verification documents."""
        if value:
            # Check file size (max 10MB)
            if value.size > 10 * 1024 * 1024:
                raise serializers.ValidationError("File size cannot exceed 10MB.")
            
            # Check file extension
            allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx']
            if not any(value.name.lower().endswith(ext) for ext in allowed_extensions):
                raise serializers.ValidationError(
                    "Only PDF, JPG, JPEG, PNG, DOC, and DOCX files are allowed."
                )
        
        return value


class BuyerAddressSerializer(serializers.ModelSerializer):
    """
    Serializer for buyer addresses.
    """
    buyer_name = serializers.CharField(source='buyer.full_name', read_only=True)
    
    class Meta:
        model = BuyerAddress
        fields = [
            'id', 'buyer', 'buyer_name', 'address_type', 'title', 'full_name',
            'phone_number', 'address_line_1', 'address_line_2', 'city', 'state',
            'postal_code', 'country', 'latitude', 'longitude', 'is_default',
            'delivery_instructions', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['buyer', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        """Validate address data."""
        # Ensure required fields are provided
        required_fields = ['title', 'full_name', 'phone_number', 'address_line_1', 'city', 'state']
        for field in required_fields:
            if not attrs.get(field):
                raise serializers.ValidationError({field: "This field is required."})
        
        return attrs


class CategorySerializer(serializers.ModelSerializer):
    """
    Simple category serializer for preferences.
    """
    class Meta:
        model = Category
        fields = ['id', 'name', 'description']


class BuyerPreferencesSerializer(serializers.ModelSerializer):
    """
    Serializer for buyer preferences.
    """
    buyer_name = serializers.CharField(source='buyer.full_name', read_only=True)
    preferred_categories = CategorySerializer(many=True, read_only=True)
    preferred_category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = BuyerPreferences
        fields = [
            'buyer', 'buyer_name', 'preferred_categories', 'preferred_category_ids',
            'organic_only', 'local_farmers_only', 'max_delivery_distance',
            'budget_range_min', 'budget_range_max', 'email_notifications',
            'sms_notifications', 'push_notifications', 'new_products_alerts',
            'price_drop_alerts', 'order_updates', 'farmer_updates',
            'auto_reorder', 'save_payment_methods', 'created_at', 'updated_at'
        ]
        read_only_fields = ['buyer', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        """Validate preferences data."""
        budget_min = attrs.get('budget_range_min')
        budget_max = attrs.get('budget_range_max')
        
        if budget_min and budget_max and budget_min > budget_max:
            raise serializers.ValidationError({
                'budget_range_max': 'Maximum budget must be greater than minimum budget.'
            })
        
        return attrs
    
    def update(self, instance, validated_data):
        """Update preferences with categories."""
        category_ids = validated_data.pop('preferred_category_ids', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if category_ids is not None:
            categories = Category.objects.filter(id__in=category_ids)
            instance.preferred_categories.set(categories)
        
        return instance


class FarmerBasicSerializer(serializers.ModelSerializer):
    """
    Basic farmer serializer for favorite farmers.
    """
    full_name = serializers.ReadOnlyField()
    farmer_profile = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'full_name', 'phone_number',
            'is_approved', 'farmer_profile'
        ]
    
    def get_farmer_profile(self, obj):
        """Get farmer profile information."""
        if hasattr(obj, 'farmer_profile'):
            return {
                'location': obj.farmer_profile.location,
                'trust_badge': obj.farmer_profile.trust_badge,
                'farm_name': obj.farmer_profile.farm_name,
                'specialization': obj.farmer_profile.specialization,
                'is_certified': obj.farmer_profile.is_certified,
            }
        return None


class FavoriteFarmerSerializer(serializers.ModelSerializer):
    """
    Serializer for favorite farmers.
    """
    buyer_name = serializers.CharField(source='buyer.full_name', read_only=True)
    farmer_details = FarmerBasicSerializer(source='farmer', read_only=True)
    farmer_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = FavoriteFarmer
        fields = [
            'id', 'buyer', 'buyer_name', 'farmer', 'farmer_id', 'farmer_details',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['buyer', 'created_at', 'updated_at']
    
    def validate_farmer_id(self, value):
        """Validate farmer exists and is approved."""
        try:
            farmer = User.objects.get(id=value, user_type='Farmer')
            if not farmer.is_approved:
                raise serializers.ValidationError("Farmer is not approved yet.")
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("Farmer not found.")
    
    def create(self, validated_data):
        """Create favorite farmer."""
        farmer_id = validated_data.pop('farmer_id')
        farmer = User.objects.get(id=farmer_id)
        validated_data['farmer'] = farmer
        return super().create(validated_data)


class ProductBasicSerializer(serializers.ModelSerializer):
    """
    Basic product serializer for wishlist.
    """
    farmer_name = serializers.CharField(source='farmer.full_name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    is_in_stock = serializers.ReadOnlyField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'product_name', 'price', 'unit', 'status', 'farmer_name',
            'primary_image', 'is_in_stock', 'quantity'
        ]
    
    def get_primary_image(self, obj):
        """Get primary image."""
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            return {
                'id': primary_image.id,
                'image': primary_image.image.url if primary_image.image else None,
                'alt_text': primary_image.alt_text
            }
        return None


class WishlistSerializer(serializers.ModelSerializer):
    """
    Serializer for wishlist items.
    """
    buyer_name = serializers.CharField(source='buyer.full_name', read_only=True)
    product_details = ProductBasicSerializer(source='product', read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    is_price_target_met = serializers.ReadOnlyField()
    is_available = serializers.ReadOnlyField()
    
    class Meta:
        model = Wishlist
        fields = [
            'id', 'buyer', 'buyer_name', 'product', 'product_id', 'product_details',
            'desired_quantity', 'target_price', 'notes', 'notify_when_available',
            'notify_on_price_drop', 'is_price_target_met', 'is_available',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['buyer', 'created_at', 'updated_at']
    
    def validate_product_id(self, value):
        """Validate product exists."""
        try:
            Product.objects.get(id=value)
            return value
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found.")
    
    def validate_desired_quantity(self, value):
        """Validate desired quantity."""
        if value <= 0:
            raise serializers.ValidationError("Desired quantity must be greater than 0.")
        return value
    
    def validate_target_price(self, value):
        """Validate target price."""
        if value is not None and value <= 0:
            raise serializers.ValidationError("Target price must be greater than 0.")
        return value
    
    def create(self, validated_data):
        """Create wishlist item."""
        product_id = validated_data.pop('product_id')
        product = Product.objects.get(id=product_id)
        validated_data['product'] = product
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Update wishlist item."""
        product_id = validated_data.pop('product_id', None)
        
        if product_id:
            product = Product.objects.get(id=product_id)
            instance.product = product
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance
