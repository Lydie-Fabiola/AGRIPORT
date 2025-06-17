from rest_framework import serializers
from .models import Conversation, Message

class MessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.EmailField(source='sender.email', read_only=True)
    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'sender_email', 'content', 'sent_at', 'is_read']
        read_only_fields = ['id', 'sent_at', 'sender_email']

class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    reservation = serializers.PrimaryKeyRelatedField(read_only=True)
    product = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Conversation
        fields = ['id', 'farmer', 'buyer', 'reservation', 'product', 'created_at', 'updated_at', 'messages']
        read_only_fields = ['id', 'created_at', 'updated_at', 'messages', 'reservation', 'product'] 