from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from users.permissions import IsFarmer, IsBuyer
from django.db import models
from reservations.models import Reservation
from products.models import Product
from notifications.models import Notification
from notifications.utils import send_notification_ws

# Create your views here.

class ConversationViewSet(viewsets.ModelViewSet):
    queryset = Conversation.objects.all().prefetch_related('messages')
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(
            models.Q(farmer__user=user) | models.Q(buyer=user)
        ).distinct()

    def perform_create(self, serializer):
        buyer = self.request.user
        farmer_id = self.request.data.get('farmer')
        reservation_id = self.request.data.get('reservation')
        product_id = self.request.data.get('product')
        farmer = None
        reservation = None
        product = None
        if farmer_id:
            from farmer.models import FarmerProfile
            farmer = FarmerProfile.objects.get(id=farmer_id)
        if reservation_id:
            reservation = Reservation.objects.get(id=reservation_id)
        if product_id:
            product = Product.objects.get(id=product_id)
        serializer.save(buyer=buyer, farmer=farmer, reservation=reservation, product=product)

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'create']:
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all().select_related('conversation', 'sender')
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        message = serializer.save(sender=self.request.user)
        # Determine recipient
        conversation = message.conversation
        if message.sender == conversation.buyer:
            recipient = conversation.farmer.user
        else:
            recipient = conversation.buyer
        notification = Notification.objects.create(
            user=recipient,
            title='New Message',
            message=f'You have a new message from {message.sender.email}',
            notification_type='message',
            related_entity_type='conversation',
            related_entity_id=conversation.id
        )
        # Send WebSocket push
        send_notification_ws(recipient.id, {
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'notification_type': notification.notification_type,
            'created_at': str(notification.created_at),
            'related_entity_type': notification.related_entity_type,
            'related_entity_id': notification.related_entity_id,
        })

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        message = self.get_object()
        message.is_read = True
        message.save()
        return Response({'status': 'marked as read'})
