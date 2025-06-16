from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Reservation
from .serializers import ReservationSerializer
from products.models import Product
from notifications.models import Notification
from django.utils import timezone
from notifications.utils import send_notification_ws

class ReservationViewSet(viewsets.ModelViewSet):
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Buyers see only their reservations
        return Reservation.objects.filter(buyer=self.request.user).select_related('product', 'buyer')

    def perform_create(self, serializer):
        reservation = serializer.save(buyer=self.request.user)
        # Notify the farmer
        farmer_user = reservation.product.farmer.user
        Notification.objects.create(
            user=farmer_user,
            title='New Reservation',
            message=f'{self.request.user.email} reserved {reservation.quantity} of {reservation.product.name}.',
            notification_type='reservation',
            related_entity_type='reservation',
            related_entity_id=reservation.id
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        prev_status = instance.status
        response = super().update(request, *args, **kwargs)
        instance.refresh_from_db()
        # If status changed, notify buyer
        if prev_status != instance.status:
            Notification.objects.create(
                user=instance.buyer,
                title='Reservation Status Update',
                message=f'Your reservation for {instance.product.name} is now {instance.status}.',
                notification_type='reservation',
                related_entity_type='reservation',
                related_entity_id=instance.id
            )
            send_notification_ws(instance.buyer.id, {
                'title': 'Reservation Status Update',
                'message': f'Your reservation for {instance.product.name} is now {instance.status}.',
                'notification_type': 'reservation',
                'related_entity_type': 'reservation',
                'related_entity_id': instance.id,
            })
        # If status changed to approved, update product quantity
        if prev_status != instance.status and instance.status == 'approved':
            product = instance.product
            product.quantity -= instance.quantity
            product.save()
            instance.resolved_at = timezone.now()
            instance.save()
        elif prev_status != instance.status and instance.status in ['rejected', 'completed']:
            instance.resolved_at = timezone.now()
            instance.save()
        return response

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        reservation = self.get_object()
        if reservation.status != 'pending':
            return Response({'detail': 'Only pending reservations can be cancelled.'}, status=status.HTTP_400_BAD_REQUEST)
        reservation.status = 'cancelled'
        reservation.resolved_at = timezone.now()
        reservation.save()
        return Response({'status': 'cancelled'})

    @action(detail=False, methods=['get'], url_path='order-history')
    def order_history(self, request):
        completed = Reservation.objects.filter(buyer=request.user, status='completed').select_related('product', 'buyer')
        page = self.paginate_queryset(completed)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(completed, many=True)
        return Response(serializer.data)
