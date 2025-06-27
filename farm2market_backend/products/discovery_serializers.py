"""
Serializers for product discovery and search.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Product, Category, ProductImage, ProductReview
from .search_models import SearchQuery, PopularSearch, DeliveryZone, SavedSearch
from apps.farmers.serializers import FarmerBasicSerializer

User = get_user_model()


class ProductImageSerializer(serializers.ModelSerializer):
    """
    Serializer for product images.
    """
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary', 'display_order']


class CategoryTreeSerializer(serializers.ModelSerializer):
    """
    Serializer for category with subcategories.
    """
    subcategories = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'description', 'image', 'display_order',
            'subcategories', 'product_count'
        ]
    
    def get_subcategories(self, obj):
        """Get active subcategories."""
        subcategories = obj.subcategories.filter(is_active=True)
        return CategoryTreeSerializer(subcategories, many=True).data
    
    def get_product_count(self, obj):
        """Get count of available products in this category."""
        return obj.products.filter(status='Available').count()


class ProductSearchSerializer(serializers.ModelSerializer):
    """
    Serializer for product search results.
    """
    farmer_name = serializers.CharField(source='farmer.full_name', read_only=True)
    farmer_username = serializers.CharField(source='farmer.username', read_only=True)
    farmer_location = serializers.CharField(source='farmer.farmer_profile.location', read_only=True)
    farmer_trust_badge = serializers.CharField(source='farmer.farmer_profile.trust_badge', read_only=True)
    
    categories = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)
    
    # Calculated fields
    available_quantity = serializers.ReadOnlyField()
    is_in_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    
    # Annotated fields from search
    avg_rating = serializers.DecimalField(max_digits=3, decimal_places=2, read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    
    # Location information
    location_name = serializers.CharField(source='location.name', read_only=True)
    location_city = serializers.CharField(source='location.city', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'product_name', 'description', 'price', 'quantity', 'unit',
            'status', 'sku', 'minimum_order_quantity', 'harvest_date', 'expiry_date',
            'organic_certified', 'featured', 'views_count', 'available_quantity',
            'is_in_stock', 'is_low_stock', 'farmer_name', 'farmer_username',
            'farmer_location', 'farmer_trust_badge', 'categories', 'primary_image',
            'images', 'avg_rating', 'review_count', 'location_name', 'location_city',
            'created_at', 'updated_at'
        ]
    
    def get_categories(self, obj):
        """Get product categories."""
        return [{'id': cat.id, 'name': cat.name} for cat in obj.categories.all()]
    
    def get_primary_image(self, obj):
        """Get primary product image."""
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            return ProductImageSerializer(primary_image).data
        return None


class ProductDetailSerializer(ProductSearchSerializer):
    """
    Detailed product serializer with additional information.
    """
    farmer_details = serializers.SerializerMethodField()
    related_products = serializers.SerializerMethodField()
    recent_reviews = serializers.SerializerMethodField()
    delivery_zones = serializers.SerializerMethodField()
    
    class Meta(ProductSearchSerializer.Meta):
        fields = ProductSearchSerializer.Meta.fields + [
            'farmer_details', 'related_products', 'recent_reviews', 'delivery_zones'
        ]
    
    def get_farmer_details(self, obj):
        """Get detailed farmer information."""
        farmer = obj.farmer
        farmer_data = {
            'id': farmer.id,
            'username': farmer.username,
            'full_name': farmer.full_name,
            'email': farmer.email,
            'phone_number': farmer.phone_number,
            'is_approved': farmer.is_approved,
        }
        
        if hasattr(farmer, 'farmer_profile'):
            profile = farmer.farmer_profile
            farmer_data.update({
                'location': profile.location,
                'trust_badge': profile.trust_badge,
                'farm_name': profile.farm_name,
                'specialization': profile.specialization,
                'farming_experience': profile.farming_experience,
                'is_certified': profile.is_certified,
                'bio': profile.bio,
            })
        
        return farmer_data
    
    def get_related_products(self, obj):
        """Get related products from same farmer or category."""
        # Get products from same farmer (excluding current product)
        farmer_products = Product.objects.filter(
            farmer=obj.farmer,
            status='Available'
        ).exclude(id=obj.id)[:3]
        
        # Get products from same categories
        category_products = Product.objects.filter(
            categories__in=obj.categories.all(),
            status='Available'
        ).exclude(id=obj.id).exclude(
            id__in=farmer_products.values_list('id', flat=True)
        ).distinct()[:3]
        
        related = list(farmer_products) + list(category_products)
        return ProductSearchSerializer(related[:6], many=True).data
    
    def get_recent_reviews(self, obj):
        """Get recent approved reviews."""
        recent_reviews = obj.reviews.filter(is_approved=True).order_by('-created_at')[:5]
        return ProductReviewSerializer(recent_reviews, many=True).data
    
    def get_delivery_zones(self, obj):
        """Get farmer's delivery zones."""
        zones = obj.farmer.delivery_zones.filter(is_active=True)
        return DeliveryZoneSerializer(zones, many=True).data


class ProductReviewSerializer(serializers.ModelSerializer):
    """
    Serializer for product reviews.
    """
    buyer_name = serializers.CharField(source='buyer.full_name', read_only=True)
    buyer_username = serializers.CharField(source='buyer.username', read_only=True)
    
    class Meta:
        model = ProductReview
        fields = [
            'id', 'buyer', 'buyer_name', 'buyer_username', 'rating',
            'review_text', 'is_verified_purchase', 'helpful_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['buyer', 'is_verified_purchase', 'helpful_count']


class SearchQuerySerializer(serializers.ModelSerializer):
    """
    Serializer for search queries.
    """
    user_email = serializers.CharField(source='user.email', read_only=True)
    filters_display = serializers.ReadOnlyField(source='get_filters_display')
    
    class Meta:
        model = SearchQuery
        fields = [
            'id', 'user', 'user_email', 'query', 'filters', 'filters_display',
            'results_count', 'timestamp', 'has_results'
        ]


class PopularSearchSerializer(serializers.ModelSerializer):
    """
    Serializer for popular searches.
    """
    class Meta:
        model = PopularSearch
        fields = ['id', 'query', 'search_count', 'last_searched']


class DeliveryZoneSerializer(serializers.ModelSerializer):
    """
    Serializer for delivery zones.
    """
    farmer_name = serializers.CharField(source='farmer.full_name', read_only=True)
    
    class Meta:
        model = DeliveryZone
        fields = [
            'id', 'farmer', 'farmer_name', 'zone_name', 'coordinates',
            'delivery_fee', 'minimum_order', 'estimated_delivery_time',
            'delivery_days', 'notes', 'is_active'
        ]
        read_only_fields = ['farmer']


class SavedSearchSerializer(serializers.ModelSerializer):
    """
    Serializer for saved searches.
    """
    user_email = serializers.CharField(source='user.email', read_only=True)
    filters_display = serializers.ReadOnlyField(source='get_filters_display')
    
    class Meta:
        model = SavedSearch
        fields = [
            'id', 'user', 'user_email', 'name', 'search_query', 'filters',
            'filters_display', 'is_active', 'notification_enabled',
            'last_notification_sent', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'last_notification_sent']


class SearchFiltersSerializer(serializers.Serializer):
    """
    Serializer for search filters validation.
    """
    query = serializers.CharField(required=False, allow_blank=True, max_length=500)
    categories = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    min_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        min_value=0
    )
    max_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        min_value=0
    )
    latitude = serializers.FloatField(required=False, min_value=-90, max_value=90)
    longitude = serializers.FloatField(required=False, min_value=-180, max_value=180)
    radius = serializers.FloatField(required=False, min_value=1, max_value=500)
    in_stock_only = serializers.BooleanField(required=False, default=False)
    organic_only = serializers.BooleanField(required=False, default=False)
    verified_farmers_only = serializers.BooleanField(required=False, default=False)
    featured_only = serializers.BooleanField(required=False, default=False)
    min_quantity = serializers.IntegerField(required=False, min_value=1)
    harvest_date_from = serializers.DateField(required=False)
    harvest_date_to = serializers.DateField(required=False)
    
    def validate(self, attrs):
        """Validate filter combinations."""
        min_price = attrs.get('min_price')
        max_price = attrs.get('max_price')
        
        if min_price and max_price and min_price > max_price:
            raise serializers.ValidationError({
                'max_price': 'Maximum price must be greater than minimum price.'
            })
        
        harvest_from = attrs.get('harvest_date_from')
        harvest_to = attrs.get('harvest_date_to')
        
        if harvest_from and harvest_to and harvest_from > harvest_to:
            raise serializers.ValidationError({
                'harvest_date_to': 'End date must be after start date.'
            })
        
        # Location validation
        lat = attrs.get('latitude')
        lng = attrs.get('longitude')
        radius = attrs.get('radius')
        
        if any([lat, lng, radius]) and not all([lat, lng, radius]):
            raise serializers.ValidationError(
                'Latitude, longitude, and radius must all be provided for location filtering.'
            )
        
        return attrs


class SortOptionsSerializer(serializers.Serializer):
    """
    Serializer for sort options validation.
    """
    SORT_CHOICES = [
        ('relevance', 'Relevance'),
        ('price_low_high', 'Price: Low to High'),
        ('price_high_low', 'Price: High to Low'),
        ('newest', 'Newest First'),
        ('oldest', 'Oldest First'),
        ('harvest_date_newest', 'Freshest First'),
        ('harvest_date_oldest', 'Oldest Harvest'),
        ('quantity_high_low', 'Stock: High to Low'),
        ('quantity_low_high', 'Stock: Low to High'),
        ('farmer_rating', 'Farmer Rating'),
        ('popularity', 'Most Popular'),
        ('distance', 'Distance'),
    ]
    
    sort_by = serializers.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        default='relevance'
    )
