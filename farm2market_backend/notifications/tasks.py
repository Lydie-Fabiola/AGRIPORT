"""
Celery tasks for notification system.
"""
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import (
    Notification, NotificationQueue, NotificationDeliveryLog,
    DeviceToken, UserNotificationPreference
)
from .services import NotificationService, send_order_notification, send_system_notification

User = get_user_model()


@shared_task
def process_notification_queue():
    """
    Process pending notifications in the queue.
    """
    # Get pending notifications ordered by priority and schedule time
    pending_items = NotificationQueue.objects.filter(
        status='pending',
        scheduled_at__lte=timezone.now()
    ).order_by('priority', 'scheduled_at')[:100]  # Process in batches
    
    processed_count = 0
    
    for queue_item in pending_items:
        try:
            # Mark as processing
            queue_item.status = 'processing'
            queue_item.save()
            
            # Process the notification
            success = process_single_notification.delay(
                queue_item.notification.id,
                queue_item.channel.name
            )
            
            if success:
                queue_item.status = 'completed'
            else:
                queue_item.status = 'failed'
                queue_item.attempts += 1
            
            queue_item.save()
            processed_count += 1
            
        except Exception as e:
            queue_item.status = 'failed'
            queue_item.error_message = str(e)
            queue_item.attempts += 1
            queue_item.save()
    
    return f"Processed {processed_count} notifications from queue"


@shared_task
def process_single_notification(notification_id, channel_name):
    """
    Process a single notification through a specific channel.
    """
    try:
        notification = Notification.objects.get(id=notification_id)
        service = NotificationService()
        
        success = service._send_to_channel(notification, channel_name)
        
        return success
        
    except Notification.DoesNotExist:
        return False
    except Exception as e:
        return False


@shared_task
def send_bulk_notification(user_ids, notification_type, context=None, channels=None):
    """
    Send notification to multiple users.
    """
    service = NotificationService()
    sent_count = 0
    
    users = User.objects.filter(id__in=user_ids, is_active=True)
    
    for user in users:
        try:
            notification = service.send_notification(
                user, notification_type, context, channels
            )
            if notification:
                sent_count += 1
        except Exception as e:
            continue
    
    return f"Sent notifications to {sent_count} users"


@shared_task
def cleanup_old_notifications():
    """
    Clean up old notifications based on retention policy.
    """
    # Delete notifications older than 6 months
    cutoff_date = timezone.now() - timedelta(days=180)
    
    deleted_count, _ = Notification.objects.filter(
        created_at__lt=cutoff_date
    ).delete()
    
    return f"Cleaned up {deleted_count} old notifications"


@shared_task
def cleanup_expired_notifications():
    """
    Clean up expired notifications.
    """
    expired_count = Notification.objects.filter(
        expires_at__lt=timezone.now(),
        is_deleted=False
    ).update(
        is_deleted=True,
        deleted_at=timezone.now()
    )
    
    return f"Cleaned up {expired_count} expired notifications"


@shared_task
def cleanup_inactive_device_tokens():
    """
    Clean up inactive device tokens.
    """
    # Remove tokens not used in the last 30 days
    cutoff_date = timezone.now() - timedelta(days=30)
    
    deleted_count, _ = DeviceToken.objects.filter(
        last_used__lt=cutoff_date,
        is_active=False
    ).delete()
    
    return f"Cleaned up {deleted_count} inactive device tokens"


@shared_task
def send_order_status_notification(order_id, old_status, new_status):
    """
    Send notification when order status changes.
    """
    try:
        from apps.orders.models import Order
        
        order = Order.objects.get(id=order_id)
        
        # Map status to notification type
        status_notifications = {
            'confirmed': 'order_confirmed',
            'preparing': 'order_preparing',
            'ready': 'order_ready',
            'in_transit': 'order_in_transit',
            'delivered': 'order_delivered',
            'cancelled': 'order_cancelled',
        }
        
        notification_type = status_notifications.get(new_status)
        if notification_type:
            send_order_notification(order, notification_type)
            return f"Sent {notification_type} notification for order {order.order_number}"
        
        return f"No notification configured for status: {new_status}"
        
    except Exception as e:
        return f"Error sending order status notification: {str(e)}"


@shared_task
def send_payment_notification(order_id, payment_status):
    """
    Send notification when payment status changes.
    """
    try:
        from apps.orders.models import Order
        
        order = Order.objects.get(id=order_id)
        
        if payment_status == 'paid':
            send_order_notification(order, 'payment_received')
        elif payment_status == 'failed':
            send_order_notification(order, 'payment_failed')
        
        return f"Sent payment notification for order {order.order_number}"
        
    except Exception as e:
        return f"Error sending payment notification: {str(e)}"


@shared_task
def send_product_alert_notifications():
    """
    Send product-related alert notifications.
    """
    from apps.products.models import Product
    from apps.buyers.models import WishlistItem
    
    sent_count = 0
    
    # Price drop alerts for wishlist items
    wishlist_items = WishlistItem.objects.select_related(
        'buyer', 'product'
    ).filter(
        product__status='Available',
        price_alert_enabled=True
    )
    
    for item in wishlist_items:
        if item.product.price < item.target_price:
            context = {
                'product_name': item.product.product_name,
                'old_price': item.target_price,
                'new_price': item.product.price,
                'savings': item.target_price - item.product.price,
            }
            
            service = NotificationService()
            service.send_notification(
                item.buyer,
                'price_drop_wishlist',
                context
            )
            sent_count += 1
    
    # Stock availability alerts
    out_of_stock_items = WishlistItem.objects.select_related(
        'buyer', 'product'
    ).filter(
        product__status='Available',
        product__quantity__gt=0,
        stock_alert_enabled=True
    )
    
    for item in out_of_stock_items:
        # Check if product was previously out of stock
        # This would require additional tracking
        context = {
            'product_name': item.product.product_name,
            'available_quantity': item.product.quantity,
        }
        
        service = NotificationService()
        service.send_notification(
            item.buyer,
            'stock_available_wishlist',
            context
        )
        sent_count += 1
    
    return f"Sent {sent_count} product alert notifications"


@shared_task
def send_new_product_notifications():
    """
    Send notifications about new products from favorite farmers.
    """
    from apps.products.models import Product
    from apps.buyers.models import FavoriteFarmer
    
    # Get products created in the last 24 hours
    yesterday = timezone.now() - timedelta(days=1)
    new_products = Product.objects.filter(
        created_at__gte=yesterday,
        status='Available'
    )
    
    sent_count = 0
    
    for product in new_products:
        # Get buyers who have this farmer as favorite
        favorite_relations = FavoriteFarmer.objects.filter(
            farmer=product.farmer
        ).select_related('buyer')
        
        for favorite in favorite_relations:
            context = {
                'product_name': product.product_name,
                'farmer_name': product.farmer.full_name,
                'price': product.price,
                'description': product.description[:100] + '...' if len(product.description) > 100 else product.description,
            }
            
            service = NotificationService()
            service.send_notification(
                favorite.buyer,
                'new_product_favorite_farmer',
                context
            )
            sent_count += 1
    
    return f"Sent {sent_count} new product notifications"


@shared_task
def send_seasonal_product_notifications():
    """
    Send notifications about seasonal products.
    """
    from apps.products.models import Product
    
    # This would be based on seasonal categories or tags
    # For now, we'll use a simple example
    
    seasonal_products = Product.objects.filter(
        status='Available',
        categories__name__icontains='seasonal'
    ).distinct()
    
    if not seasonal_products.exists():
        return "No seasonal products found"
    
    # Get all active buyers
    buyers = User.objects.filter(user_type='Buyer', is_active=True)
    
    sent_count = 0
    
    for buyer in buyers:
        # Check if user wants seasonal notifications
        try:
            preference = UserNotificationPreference.objects.get(
                user=buyer,
                notification_type='seasonal_products',
                is_enabled=True
            )
            
            context = {
                'product_count': seasonal_products.count(),
                'season': 'Current Season',  # This would be dynamic
            }
            
            service = NotificationService()
            service.send_notification(
                buyer,
                'seasonal_products',
                context
            )
            sent_count += 1
            
        except UserNotificationPreference.DoesNotExist:
            continue
    
    return f"Sent seasonal product notifications to {sent_count} buyers"


@shared_task
def send_welcome_notification(user_id):
    """
    Send welcome notification to new user.
    """
    try:
        user = User.objects.get(id=user_id)
        
        context = {
            'user_name': user.full_name,
            'user_type': user.get_user_type_display(),
            'platform_name': 'Farm2Market',
        }
        
        send_system_notification(user, 'welcome_message', context)
        
        return f"Sent welcome notification to {user.full_name}"
        
    except User.DoesNotExist:
        return f"User {user_id} not found"
    except Exception as e:
        return f"Error sending welcome notification: {str(e)}"


@shared_task
def send_profile_incomplete_reminder(user_id):
    """
    Send reminder to complete profile.
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Check if profile is incomplete
        profile_complete = True
        
        if user.user_type == 'Farmer':
            if not hasattr(user, 'farmer_profile') or not user.farmer_profile.is_complete:
                profile_complete = False
        elif user.user_type == 'Buyer':
            if not hasattr(user, 'buyer_preferences') or not user.buyer_preferences.is_complete:
                profile_complete = False
        
        if not profile_complete:
            context = {
                'user_name': user.full_name,
                'profile_url': f'/profile/{user.id}/',
            }
            
            send_system_notification(user, 'profile_incomplete', context)
            
            return f"Sent profile incomplete reminder to {user.full_name}"
        
        return f"Profile is complete for {user.full_name}"
        
    except User.DoesNotExist:
        return f"User {user_id} not found"
    except Exception as e:
        return f"Error sending profile reminder: {str(e)}"


@shared_task
def generate_notification_analytics():
    """
    Generate notification analytics report.
    """
    try:
        # Get analytics for the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Total notifications sent
        total_sent = Notification.objects.filter(
            created_at__gte=thirty_days_ago
        ).count()
        
        # Notifications by type
        by_type = dict(Notification.objects.filter(
            created_at__gte=thirty_days_ago
        ).values('notification_type').annotate(
            count=models.Count('id')
        ).values_list('notification_type', 'count'))
        
        # Delivery success rates by channel
        delivery_stats = {}
        for channel in ['EMAIL', 'SMS', 'PUSH', 'IN_APP']:
            total_attempts = NotificationDeliveryLog.objects.filter(
                created_at__gte=thirty_days_ago,
                channel__name=channel
            ).count()
            
            successful_deliveries = NotificationDeliveryLog.objects.filter(
                created_at__gte=thirty_days_ago,
                channel__name=channel,
                status__in=['sent', 'delivered']
            ).count()
            
            success_rate = (successful_deliveries / total_attempts * 100) if total_attempts > 0 else 0
            
            delivery_stats[channel] = {
                'total_attempts': total_attempts,
                'successful_deliveries': successful_deliveries,
                'success_rate': round(success_rate, 2)
            }
        
        # Read rates
        total_notifications = Notification.objects.filter(
            created_at__gte=thirty_days_ago
        ).count()
        
        read_notifications = Notification.objects.filter(
            created_at__gte=thirty_days_ago,
            is_read=True
        ).count()
        
        read_rate = (read_notifications / total_notifications * 100) if total_notifications > 0 else 0
        
        analytics_data = {
            'period': '30 days',
            'total_sent': total_sent,
            'by_type': by_type,
            'delivery_stats': delivery_stats,
            'read_rate': round(read_rate, 2),
            'generated_at': timezone.now().isoformat(),
        }
        
        # TODO: Store analytics data or send to admin
        # cache.set('notification_analytics_report', analytics_data, timeout=86400)
        
        return f"Generated notification analytics: {total_sent} notifications sent, {read_rate:.1f}% read rate"
        
    except Exception as e:
        return f"Error generating notification analytics: {str(e)}"
