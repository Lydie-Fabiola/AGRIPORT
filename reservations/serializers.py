from rest_framework import serializers
from .models import Reservation, Review
from products.models import Product

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'reservation', 'reviewer', 'farmer', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'reviewer', 'farmer', 'created_at', 'reservation']

class ReservationSerializer(serializers.ModelSerializer):
    review = ReviewSerializer(read_only=True)
    class Meta:
        model = Reservation
        fields = [
            'id', 'product', 'buyer', 'quantity', 'status', 'requested_at',
            'resolved_at', 'pickup_time', 'delivery_option', 'notes', 'note_to_farmer', 'review'
        ]
        read_only_fields = ['id', 'status', 'requested_at', 'resolved_at', 'buyer', 'review']

    def validate(self, data):
        product = data.get('product')
        quantity = data.get('quantity')
        buyer = self.context['request'].user
        # Check product availability
        if product and quantity:
            if quantity > product.quantity:
                raise serializers.ValidationError('Requested quantity exceeds available stock.')
        # Prevent duplicate unresolved reservations
        if product and buyer:
            exists = Reservation.objects.filter(
                product=product, buyer=buyer, status__in=['pending', 'approved']
            ).exists()
            if exists and self.instance is None:
                raise serializers.ValidationError('You already have an unresolved reservation for this product.')
        return data
