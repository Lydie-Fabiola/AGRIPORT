from rest_framework import serializers
from .models import Transaction

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            'id', 'reservation', 'buyer', 'farmer', 'product', 'quantity', 'price', 'amount', 'currency', 'type', 'status',
            'reference_id', 'momo_reference', 'created_at', 'updated_at', 'message'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at', 'momo_reference', 'message']