"""
Signals for messaging system.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Message, UserOnlineStatus
from .tasks import send_message_notification, send_order_confirmation_message

User = get_user_model()


@receiver(post_save, sender=Message)
def handle_new_message(sender, instance, created, **kwargs):
    """
    Handle new message creation - send notifications.
    """
    if created and instance.message_type != 'system':
        # Send notification to offline participants
        send_message_notification.delay(instance.id)


@receiver(post_save, sender=User)
def create_user_online_status(sender, instance, created, **kwargs):
    """
    Create online status when user is created.
    """
    if created:
        UserOnlineStatus.objects.get_or_create(user=instance)


# Order-related signals
try:
    from apps.orders.models import Order, OrderStatusHistory
    
    @receiver(post_save, sender=Order)
    def handle_order_creation_message(sender, instance, created, **kwargs):
        """
        Send order confirmation message when order is created.
        """
        if created:
            send_order_confirmation_message.delay(instance.id)
    
    @receiver(post_save, sender=OrderStatusHistory)
    def handle_order_status_message(sender, instance, created, **kwargs):
        """
        Send delivery update message when order status changes.
        """
        if created and instance.status in ['confirmed', 'preparing', 'ready', 'in_transit', 'delivered']:
            from .tasks import send_delivery_update_message
            
            status_messages = {
                'confirmed': 'Your order has been confirmed and is being prepared.',
                'preparing': 'Your order is currently being prepared.',
                'ready': 'Your order is ready for pickup/delivery.',
                'in_transit': 'Your order is on its way to you.',
                'delivered': 'Your order has been delivered. Thank you for your business!'
            }
            
            status_update = status_messages.get(instance.status, f'Order status updated to {instance.get_status_display()}')
            send_delivery_update_message.delay(instance.order.id, status_update)

except ImportError:
    # Orders app not available yet
    pass


# Reservation-related signals
try:
    from apps.orders.models import Reservation
    
    @receiver(post_save, sender=Reservation)
    def handle_reservation_message(sender, instance, created, **kwargs):
        """
        Send message when reservation status changes.
        """
        if not created and hasattr(instance, '_status_changed'):
            from .tasks import send_automated_message
            from .models import Conversation
            
            # Find or create conversation between buyer and farmer
            conversation = Conversation.objects.filter(
                participants__in=[instance.buyer, instance.farmer]
            ).first()
            
            if not conversation:
                conversation = Conversation.objects.create(
                    subject=f"Reservation for {instance.product.product_name}"
                )
                conversation.add_participant(instance.buyer)
                conversation.add_participant(instance.farmer)
            
            # Send appropriate message based on status
            if instance.status == 'accepted':
                variables = {
                    'buyer_name': instance.buyer.full_name,
                    'product_name': instance.product.product_name,
                    'quantity': instance.quantity_requested,
                    'price': instance.final_price,
                    'farmer_name': instance.farmer.full_name
                }
                
                content = "Great news {{buyer_name}}! Your reservation for {{quantity}} units of {{product_name}} at ${{price}} per unit has been accepted. - {{farmer_name}}"
                
                send_automated_message.delay(
                    conversation.id,
                    'Reservation Accepted',
                    variables,
                    instance.farmer.id
                )
            
            elif instance.status == 'rejected':
                variables = {
                    'buyer_name': instance.buyer.full_name,
                    'product_name': instance.product.product_name,
                    'farmer_response': instance.farmer_response or 'No specific reason provided.',
                    'farmer_name': instance.farmer.full_name
                }
                
                content = "Hi {{buyer_name}}, unfortunately I cannot fulfill your reservation for {{product_name}}. {{farmer_response}} - {{farmer_name}}"
                
                send_automated_message.delay(
                    conversation.id,
                    'Reservation Rejected',
                    variables,
                    instance.farmer.id
                )
            
            elif instance.status == 'counter_offered':
                variables = {
                    'buyer_name': instance.buyer.full_name,
                    'product_name': instance.product.product_name,
                    'original_price': instance.price_offered,
                    'counter_price': instance.counter_offer_price,
                    'farmer_response': instance.farmer_response or 'Please consider my counter offer.',
                    'farmer_name': instance.farmer.full_name
                }
                
                content = "Hi {{buyer_name}}, regarding your reservation for {{product_name}} at ${{original_price}}, I can offer ${{counter_price}} per unit instead. {{farmer_response}} - {{farmer_name}}"
                
                send_automated_message.delay(
                    conversation.id,
                    'Counter Offer',
                    variables,
                    instance.farmer.id
                )

except ImportError:
    # Orders app not available yet
    pass
