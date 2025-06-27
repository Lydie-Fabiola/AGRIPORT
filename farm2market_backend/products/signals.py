"""
Signals for product and inventory management.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Product, StockMovement, LowStockAlert, InventorySettings

User = get_user_model()


@receiver(post_save, sender=Product)
def create_inventory_settings(sender, instance, created, **kwargs):
    """
    Create inventory settings for farmer when first product is created.
    """
    if created:
        InventorySettings.objects.get_or_create(farmer=instance.farmer)


@receiver(pre_save, sender=Product)
def track_quantity_changes(sender, instance, **kwargs):
    """
    Track quantity changes and create stock movements.
    """
    if instance.pk:  # Only for existing products
        try:
            old_instance = Product.objects.get(pk=instance.pk)
            old_quantity = old_instance.quantity
            new_quantity = instance.quantity
            
            if old_quantity != new_quantity:
                # Store the change for post_save signal
                instance._quantity_changed = True
                instance._old_quantity = old_quantity
                instance._new_quantity = new_quantity
        except Product.DoesNotExist:
            pass


@receiver(post_save, sender=Product)
def create_stock_movement_on_quantity_change(sender, instance, created, **kwargs):
    """
    Create stock movement when product quantity changes.
    """
    if not created and hasattr(instance, '_quantity_changed') and instance._quantity_changed:
        old_quantity = instance._old_quantity
        new_quantity = instance._new_quantity
        quantity_diff = new_quantity - old_quantity
        
        # Determine movement type
        if quantity_diff > 0:
            movement_type = 'IN'
        elif quantity_diff < 0:
            movement_type = 'OUT'
        else:
            return  # No change
        
        # Create stock movement
        StockMovement.objects.create(
            product=instance,
            movement_type=movement_type,
            quantity=quantity_diff,
            notes='Automatic stock tracking',
            created_by=instance.farmer,
            stock_after=new_quantity
        )
        
        # Clean up temporary attributes
        delattr(instance, '_quantity_changed')
        delattr(instance, '_old_quantity')
        delattr(instance, '_new_quantity')


@receiver(post_save, sender=Product)
def check_low_stock_alert(sender, instance, **kwargs):
    """
    Check for low stock and create alerts if needed.
    """
    try:
        settings = InventorySettings.objects.get(farmer=instance.farmer)
        
        if settings.auto_low_stock_alerts and instance.is_low_stock:
            # Check if there's already an active alert
            existing_alert = LowStockAlert.objects.filter(
                product=instance,
                status='active'
            ).first()
            
            if not existing_alert:
                # Calculate threshold based on settings
                original_quantity = instance.quantity + instance.sold_quantity
                threshold = int(original_quantity * (settings.low_stock_threshold_percentage / 100))
                
                LowStockAlert.objects.create(
                    product=instance,
                    threshold_quantity=threshold,
                    current_quantity=instance.quantity,
                    status='active'
                )
                
                # TODO: Send notification
                # if settings.email_notifications:
                #     send_low_stock_email.delay(instance.farmer.id, instance.id)
                # if settings.sms_notifications:
                #     send_low_stock_sms.delay(instance.farmer.id, instance.id)
        
        # Resolve existing alerts if stock is no longer low
        elif not instance.is_low_stock:
            LowStockAlert.objects.filter(
                product=instance,
                status='active'
            ).update(status='resolved')
            
    except InventorySettings.DoesNotExist:
        # Create default settings
        InventorySettings.objects.create(farmer=instance.farmer)


@receiver(post_save, sender=StockMovement)
def update_product_quantity_on_movement(sender, instance, created, **kwargs):
    """
    Update product quantity when stock movement is created manually.
    """
    if created and instance.movement_type in ['IN', 'OUT', 'ADJUSTMENT']:
        product = instance.product
        
        # Prevent recursive signal calls
        if not hasattr(instance, '_updating_product'):
            instance._updating_product = True
            
            # Update product quantity
            if instance.movement_type == 'IN':
                product.quantity += abs(instance.quantity)
            elif instance.movement_type == 'OUT':
                product.quantity = max(0, product.quantity - abs(instance.quantity))
            elif instance.movement_type == 'ADJUSTMENT':
                # For adjustments, the quantity field contains the difference
                if instance.quantity > 0:
                    product.quantity += instance.quantity
                else:
                    product.quantity = max(0, product.quantity + instance.quantity)
            
            # Update stock_after field
            instance.stock_after = product.quantity
            
            # Save both without triggering signals again
            Product.objects.filter(pk=product.pk).update(quantity=product.quantity)
            StockMovement.objects.filter(pk=instance.pk).update(stock_after=instance.stock_after)
            
            delattr(instance, '_updating_product')


@receiver(post_save, sender=User)
def create_farmer_inventory_settings(sender, instance, created, **kwargs):
    """
    Create inventory settings when a farmer user is created.
    """
    if created and instance.user_type == 'Farmer':
        InventorySettings.objects.get_or_create(farmer=instance)
