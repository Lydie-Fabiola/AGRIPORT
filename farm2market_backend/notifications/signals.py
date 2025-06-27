"""
Signals for automatic notification triggers.
"""
from celery import shared_task
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserNotificationPreference, NotificationChannel
from .tasks import (
    send_order_status_notification, send_payment_notification,
    send_welcome_notification, send_profile_incomplete_reminder
)

User = get_user_model()


@receiver(post_save, sender=User)
def handle_user_creation(sender, instance, created, **kwargs):
    """
    Handle new user creation - create default preferences and send welcome.
    """
    if created:
        # Create default notification preferences
        create_default_notification_preferences.delay(instance.id)
        
        # Send welcome notification
        send_welcome_notification.delay(instance.id)
        
        # Schedule profile completion reminder
        send_profile_incomplete_reminder.apply_async(
            args=[instance.id],
            countdown=86400  # 24 hours later
        )


@shared_task
def create_default_notification_preferences(user_id):
    """
    Create default notification preferences for new user.
    """
    try:
        user = User.objects.get(id=user_id)
        channels = NotificationChannel.objects.filter(is_active=True)
        
        # Default notification types based on user type
        if user.user_type == 'Buyer':
            default_types = [
                'order_confirmed', 'order_preparing', 'order_ready',
                'order_in_transit', 'order_delivered', 'payment_received',
                'new_product_favorite_farmer', 'price_drop_wishlist',
                'stock_available_wishlist', 'account_verification',
                'password_reset', 'security_alert'
            ]
        elif user.user_type == 'Farmer':
            default_types = [
                'order_received', 'payment_received', 'reservation_received',
                'account_verification', 'password_reset', 'security_alert'
            ]
        else:
            default_types = [
                'account_verification', 'password_reset', 'security_alert'
            ]
        
        created_count = 0
        
        for notification_type in default_types:
            for channel in channels:
                # Default settings based on channel
                is_enabled = True
                if channel.name == 'SMS':
                    # SMS disabled by default except for urgent notifications
                    is_enabled = notification_type in [
                        'security_alert', 'password_reset', 'order_delivered'
                    ]
                
                UserNotificationPreference.objects.get_or_create(
                    user=user,
                    notification_type=notification_type,
                    channel=channel,
                    defaults={'is_enabled': is_enabled}
                )
                created_count += 1
        
        return f"Created {created_count} default preferences for {user.full_name}"
        
    except User.DoesNotExist:
        return f"User {user_id} not found"
    except Exception as e:
        return f"Error creating default preferences: {str(e)}"


# Order-related signals
try:
    from apps.orders.models import Order, OrderStatusHistory
    
    @receiver(post_save, sender=Order)
    def handle_new_order(sender, instance, created, **kwargs):
        """
        Handle new order creation - notify farmer.
        """
        if created:
            from .services import send_order_notification
            send_order_notification(instance, 'order_received')
    
    @receiver(post_save, sender=OrderStatusHistory)
    def handle_order_status_change(sender, instance, created, **kwargs):
        """
        Handle order status changes - notify buyer.
        """
        if created:
            # Get previous status
            previous_history = OrderStatusHistory.objects.filter(
                order=instance.order
            ).exclude(id=instance.id).order_by('-timestamp').first()
            
            old_status = previous_history.status if previous_history else 'pending'
            
            send_order_status_notification.delay(
                instance.order.id,
                old_status,
                instance.status
            )
    
    @receiver(pre_save, sender=Order)
    def handle_payment_status_change(sender, instance, **kwargs):
        """
        Handle payment status changes.
        """
        if instance.pk:
            try:
                old_instance = Order.objects.get(pk=instance.pk)
                if old_instance.payment_status != instance.payment_status:
                    # Store change for post_save signal
                    instance._payment_status_changed = True
                    instance._old_payment_status = old_instance.payment_status
            except Order.DoesNotExist:
                pass
    
    @receiver(post_save, sender=Order)
    def handle_payment_status_notification(sender, instance, created, **kwargs):
        """
        Send payment status notifications.
        """
        if not created and hasattr(instance, '_payment_status_changed'):
            send_payment_notification.delay(instance.id, instance.payment_status)
            
            # Clean up temporary attributes
            delattr(instance, '_payment_status_changed')
            delattr(instance, '_old_payment_status')

except ImportError:
    # Orders app not available yet
    pass


# Reservation-related signals
try:
    from apps.orders.models import Reservation
    
    @receiver(post_save, sender=Reservation)
    def handle_reservation_creation(sender, instance, created, **kwargs):
        """
        Handle new reservation - notify farmer.
        """
        if created:
            from .services import NotificationService
            
            context = {
                'buyer_name': instance.buyer.full_name,
                'product_name': instance.product.product_name,
                'quantity': instance.quantity_requested,
                'price_offered': instance.price_offered,
                'harvest_date': instance.harvest_date_requested,
                'pickup_date': instance.pickup_delivery_date,
            }
            
            service = NotificationService()
            service.send_notification(
                instance.farmer,
                'reservation_received',
                context
            )
    
    @receiver(pre_save, sender=Reservation)
    def handle_reservation_status_change(sender, instance, **kwargs):
        """
        Track reservation status changes.
        """
        if instance.pk:
            try:
                old_instance = Reservation.objects.get(pk=instance.pk)
                if old_instance.status != instance.status:
                    instance._status_changed = True
                    instance._old_status = old_instance.status
            except Reservation.DoesNotExist:
                pass
    
    @receiver(post_save, sender=Reservation)
    def handle_reservation_status_notification(sender, instance, created, **kwargs):
        """
        Send reservation status notifications.
        """
        if not created and hasattr(instance, '_status_changed'):
            from .services import NotificationService
            
            service = NotificationService()
            
            if instance.status == 'accepted':
                context = {
                    'farmer_name': instance.farmer.full_name,
                    'product_name': instance.product.product_name,
                    'quantity': instance.quantity_requested,
                    'final_price': instance.final_price,
                }
                service.send_notification(
                    instance.buyer,
                    'reservation_accepted',
                    context
                )
            
            elif instance.status == 'rejected':
                context = {
                    'farmer_name': instance.farmer.full_name,
                    'product_name': instance.product.product_name,
                    'farmer_response': instance.farmer_response,
                }
                service.send_notification(
                    instance.buyer,
                    'reservation_rejected',
                    context
                )
            
            elif instance.status == 'counter_offered':
                context = {
                    'farmer_name': instance.farmer.full_name,
                    'product_name': instance.product.product_name,
                    'original_price': instance.price_offered,
                    'counter_price': instance.counter_offer_price,
                    'farmer_response': instance.farmer_response,
                }
                service.send_notification(
                    instance.buyer,
                    'reservation_counter_offer',
                    context
                )
            
            elif instance.status == 'expired':
                context = {
                    'product_name': instance.product.product_name,
                    'farmer_name': instance.farmer.full_name,
                }
                service.send_notification(
                    instance.buyer,
                    'reservation_expired',
                    context
                )
            
            # Clean up temporary attributes
            delattr(instance, '_status_changed')
            delattr(instance, '_old_status')

except ImportError:
    # Orders app not available yet
    pass


# Product-related signals
try:
    from apps.products.models import Product
    
    @receiver(post_save, sender=Product)
    def handle_new_product(sender, instance, created, **kwargs):
        """
        Handle new product creation - notify favorite farmer followers.
        """
        if created and instance.status == 'Available':
            from .tasks import send_new_product_notifications
            
            # Delay to allow for any additional product setup
            send_new_product_notifications.apply_async(countdown=300)  # 5 minutes

except ImportError:
    # Products app not available yet
    pass


# User profile signals
try:
    from apps.farmers.models import FarmerProfile
    from apps.buyers.models import BuyerPreferences
    
    @receiver(post_save, sender=FarmerProfile)
    def handle_farmer_profile_completion(sender, instance, created, **kwargs):
        """
        Handle farmer profile completion.
        """
        if instance.is_complete:
            from .services import send_system_notification
            
            context = {
                'user_name': instance.user.full_name,
                'profile_type': 'Farmer',
            }
            
            send_system_notification(
                instance.user,
                'profile_complete',
                context
            )
    
    @receiver(post_save, sender=BuyerPreferences)
    def handle_buyer_profile_completion(sender, instance, created, **kwargs):
        """
        Handle buyer profile completion.
        """
        if instance.is_complete:
            from .services import send_system_notification
            
            context = {
                'user_name': instance.user.full_name,
                'profile_type': 'Buyer',
            }
            
            send_system_notification(
                instance.user,
                'profile_complete',
                context
            )

except ImportError:
    # Profile apps not available yet
    pass
