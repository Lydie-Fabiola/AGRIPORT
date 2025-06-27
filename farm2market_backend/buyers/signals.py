"""
Signals for buyer management.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import BuyerPreferences, Wishlist
from apps.products.models import Product

User = get_user_model()


@receiver(post_save, sender=User)
def create_buyer_preferences(sender, instance, created, **kwargs):
    """
    Create buyer preferences when a buyer user is created.
    """
    if created and instance.user_type == 'Buyer':
        BuyerPreferences.objects.get_or_create(buyer=instance)


@receiver(post_save, sender=Product)
def check_wishlist_notifications(sender, instance, created, **kwargs):
    """
    Check wishlist items for notifications when product is updated.
    """
    if not created:  # Only for product updates
        # Get all wishlist items for this product
        wishlist_items = Wishlist.objects.filter(product=instance)
        
        for item in wishlist_items:
            # Check if product became available
            if (instance.is_in_stock and instance.status == 'Available' and 
                item.notify_when_available):
                # TODO: Send availability notification
                # send_product_available_notification.delay(item.buyer.id, instance.id)
                pass
            
            # Check if price dropped below target
            if (item.target_price and instance.price <= item.target_price and 
                item.notify_on_price_drop):
                # TODO: Send price drop notification
                # send_price_drop_notification.delay(item.buyer.id, instance.id, item.target_price)
                pass


@receiver(pre_save, sender=Product)
def track_price_changes(sender, instance, **kwargs):
    """
    Track price changes for wishlist notifications.
    """
    if instance.pk:  # Only for existing products
        try:
            old_instance = Product.objects.get(pk=instance.pk)
            old_price = old_instance.price
            new_price = instance.price
            
            if old_price != new_price:
                # Store the change for post_save signal
                instance._price_changed = True
                instance._old_price = old_price
                instance._new_price = new_price
        except Product.DoesNotExist:
            pass


@receiver(post_save, sender=Product)
def notify_price_changes(sender, instance, created, **kwargs):
    """
    Notify buyers about price changes on wishlisted products.
    """
    if not created and hasattr(instance, '_price_changed') and instance._price_changed:
        old_price = instance._old_price
        new_price = instance._new_price
        
        if new_price < old_price:  # Price dropped
            # Get wishlist items with price targets
            wishlist_items = Wishlist.objects.filter(
                product=instance,
                notify_on_price_drop=True,
                target_price__gte=new_price
            )
            
            for item in wishlist_items:
                # TODO: Send price drop notification
                # send_price_drop_notification.delay(
                #     item.buyer.id, 
                #     instance.id, 
                #     old_price, 
                #     new_price
                # )
                pass
        
        # Clean up temporary attributes
        delattr(instance, '_price_changed')
        delattr(instance, '_old_price')
        delattr(instance, '_new_price')
