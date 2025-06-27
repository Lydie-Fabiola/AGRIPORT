"""
Signals for order management.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Order, OrderStatusHistory, Reservation
from .tasks import (
    send_order_confirmation_email, send_order_status_update_email,
    send_reservation_notification_email
)

User = get_user_model()


@receiver(post_save, sender=Order)
def handle_order_creation(sender, instance, created, **kwargs):
    """
    Handle order creation - send confirmation emails.
    """
    if created:
        # Send order confirmation emails
        send_order_confirmation_email.delay(instance.id)


@receiver(post_save, sender=OrderStatusHistory)
def handle_order_status_change(sender, instance, created, **kwargs):
    """
    Handle order status changes - send notifications.
    """
    if created:
        # Get the previous status from the order
        order = instance.order
        
        # Get the previous status history entry
        previous_history = OrderStatusHistory.objects.filter(
            order=order
        ).exclude(id=instance.id).order_by('-timestamp').first()
        
        old_status = previous_history.status if previous_history else 'pending'
        
        # Send status update email
        send_order_status_update_email.delay(
            order.id, old_status, instance.status
        )


@receiver(post_save, sender=Reservation)
def handle_reservation_creation(sender, instance, created, **kwargs):
    """
    Handle reservation creation - send notification to farmer.
    """
    if created:
        # Send notification to farmer about new reservation
        send_reservation_notification_email.delay(instance.id, 'created')


@receiver(pre_save, sender=Reservation)
def handle_reservation_status_change(sender, instance, **kwargs):
    """
    Handle reservation status changes - send notifications.
    """
    if instance.pk:  # Only for existing reservations
        try:
            old_instance = Reservation.objects.get(pk=instance.pk)
            old_status = old_instance.status
            new_status = instance.status
            
            if old_status != new_status:
                # Store the change for post_save signal
                instance._status_changed = True
                instance._old_status = old_status
                instance._new_status = new_status
        except Reservation.DoesNotExist:
            pass


@receiver(post_save, sender=Reservation)
def handle_reservation_status_notification(sender, instance, created, **kwargs):
    """
    Send notifications for reservation status changes.
    """
    if not created and hasattr(instance, '_status_changed') and instance._status_changed:
        old_status = instance._old_status
        new_status = instance._new_status
        
        # Send appropriate notification based on status change
        if new_status == 'accepted':
            send_reservation_notification_email.delay(instance.id, 'accepted')
        elif new_status == 'rejected':
            send_reservation_notification_email.delay(instance.id, 'rejected')
        elif new_status == 'counter_offered':
            send_reservation_notification_email.delay(instance.id, 'counter_offered')
        
        # Clean up temporary attributes
        delattr(instance, '_status_changed')
        delattr(instance, '_old_status')
        delattr(instance, '_new_status')


@receiver(post_save, sender=User)
def create_user_cart(sender, instance, created, **kwargs):
    """
    Create shopping cart when a buyer user is created.
    """
    if created and instance.user_type == 'Buyer':
        from .models import Cart
        Cart.objects.get_or_create(buyer=instance)
