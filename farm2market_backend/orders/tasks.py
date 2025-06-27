"""
Celery tasks for order management.
"""
from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import Order, Reservation, Cart
from .order_utils import OrderStatusManager

User = get_user_model()


@shared_task
def send_order_confirmation_email(order_id):
    """
    Send order confirmation email to buyer and farmer.
    """
    try:
        order = Order.objects.get(id=order_id)
        
        # Send email to buyer
        buyer_subject = f'Order Confirmation #{order.order_number} - Farm2Market'
        buyer_context = {
            'order': order,
            'user': order.buyer,
            'user_type': 'buyer'
        }
        
        buyer_html_message = render_to_string('emails/order_confirmation_buyer.html', buyer_context)
        
        send_mail(
            subject=buyer_subject,
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.buyer.email],
            html_message=buyer_html_message,
            fail_silently=False,
        )
        
        # Send email to farmer
        farmer_subject = f'New Order Received #{order.order_number} - Farm2Market'
        farmer_context = {
            'order': order,
            'user': order.farmer,
            'user_type': 'farmer'
        }
        
        farmer_html_message = render_to_string('emails/order_confirmation_farmer.html', farmer_context)
        
        send_mail(
            subject=farmer_subject,
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.farmer.email],
            html_message=farmer_html_message,
            fail_silently=False,
        )
        
        return f"Order confirmation emails sent for order {order.order_number}"
        
    except Order.DoesNotExist:
        return f"Order {order_id} not found"
    except Exception as e:
        return f"Error sending order confirmation emails: {str(e)}"


@shared_task
def send_order_status_update_email(order_id, old_status, new_status):
    """
    Send order status update email to buyer.
    """
    try:
        order = Order.objects.get(id=order_id)
        
        subject = f'Order Status Update #{order.order_number} - Farm2Market'
        context = {
            'order': order,
            'old_status': old_status,
            'new_status': new_status,
            'status_display': order.get_status_display()
        }
        
        html_message = render_to_string('emails/order_status_update.html', context)
        
        send_mail(
            subject=subject,
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.buyer.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return f"Order status update email sent for order {order.order_number}"
        
    except Order.DoesNotExist:
        return f"Order {order_id} not found"
    except Exception as e:
        return f"Error sending order status update email: {str(e)}"


@shared_task
def send_reservation_notification_email(reservation_id, notification_type):
    """
    Send reservation notification emails.
    
    notification_type: 'created', 'accepted', 'rejected', 'counter_offered'
    """
    try:
        reservation = Reservation.objects.get(id=reservation_id)
        
        if notification_type == 'created':
            # Notify farmer about new reservation
            subject = f'New Reservation Request - Farm2Market'
            recipient = reservation.farmer.email
            template = 'emails/reservation_created_farmer.html'
            
        elif notification_type == 'accepted':
            # Notify buyer about accepted reservation
            subject = f'Reservation Accepted - Farm2Market'
            recipient = reservation.buyer.email
            template = 'emails/reservation_accepted_buyer.html'
            
        elif notification_type == 'rejected':
            # Notify buyer about rejected reservation
            subject = f'Reservation Rejected - Farm2Market'
            recipient = reservation.buyer.email
            template = 'emails/reservation_rejected_buyer.html'
            
        elif notification_type == 'counter_offered':
            # Notify buyer about counter offer
            subject = f'Counter Offer Received - Farm2Market'
            recipient = reservation.buyer.email
            template = 'emails/reservation_counter_offer_buyer.html'
            
        else:
            return f"Unknown notification type: {notification_type}"
        
        context = {
            'reservation': reservation,
            'notification_type': notification_type
        }
        
        html_message = render_to_string(template, context)
        
        send_mail(
            subject=subject,
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            html_message=html_message,
            fail_silently=False,
        )
        
        return f"Reservation {notification_type} email sent for reservation {reservation.id}"
        
    except Reservation.DoesNotExist:
        return f"Reservation {reservation_id} not found"
    except Exception as e:
        return f"Error sending reservation notification email: {str(e)}"


@shared_task
def auto_expire_reservations():
    """
    Automatically expire reservations that have passed their expiration date.
    """
    expired_reservations = Reservation.objects.filter(
        expires_at__lt=timezone.now(),
        status__in=['pending', 'counter_offered']
    )
    
    expired_count = 0
    
    for reservation in expired_reservations:
        reservation.status = 'expired'
        reservation.save(update_fields=['status', 'updated_at'])
        
        # Notify buyer about expired reservation
        send_reservation_expired_email.delay(reservation.id)
        
        expired_count += 1
    
    return f"Expired {expired_count} reservations"


@shared_task
def send_reservation_expired_email(reservation_id):
    """
    Send email notification about expired reservation.
    """
    try:
        reservation = Reservation.objects.get(id=reservation_id)
        
        subject = f'Reservation Expired - Farm2Market'
        context = {
            'reservation': reservation
        }
        
        html_message = render_to_string('emails/reservation_expired_buyer.html', context)
        
        send_mail(
            subject=subject,
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[reservation.buyer.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return f"Reservation expired email sent for reservation {reservation.id}"
        
    except Reservation.DoesNotExist:
        return f"Reservation {reservation_id} not found"
    except Exception as e:
        return f"Error sending reservation expired email: {str(e)}"


@shared_task
def cleanup_abandoned_carts():
    """
    Clean up carts that haven't been updated in 30 days.
    """
    cutoff_date = timezone.now() - timedelta(days=30)
    
    abandoned_carts = Cart.objects.filter(
        updated_at__lt=cutoff_date
    )
    
    cleaned_count = 0
    
    for cart in abandoned_carts:
        cart.clear()
        cleaned_count += 1
    
    return f"Cleaned {cleaned_count} abandoned carts"


@shared_task
def send_cart_abandonment_reminder(buyer_id):
    """
    Send cart abandonment reminder email.
    """
    try:
        buyer = User.objects.get(id=buyer_id, user_type='Buyer')
        
        # Check if buyer has items in cart
        if hasattr(buyer, 'cart') and not buyer.cart.is_empty:
            subject = f'You have items waiting in your cart - Farm2Market'
            context = {
                'buyer': buyer,
                'cart': buyer.cart
            }
            
            html_message = render_to_string('emails/cart_abandonment_reminder.html', context)
            
            send_mail(
                subject=subject,
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[buyer.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            return f"Cart abandonment reminder sent to {buyer.email}"
        else:
            return f"Buyer {buyer.email} has no items in cart"
        
    except User.DoesNotExist:
        return f"Buyer {buyer_id} not found"
    except Exception as e:
        return f"Error sending cart abandonment reminder: {str(e)}"


@shared_task
def auto_confirm_orders():
    """
    Automatically confirm orders that have been pending for too long.
    """
    # Auto-confirm orders that have been pending for more than 24 hours
    cutoff_time = timezone.now() - timedelta(hours=24)
    
    pending_orders = Order.objects.filter(
        status='pending',
        created_at__lt=cutoff_time
    )
    
    confirmed_count = 0
    
    for order in pending_orders:
        try:
            OrderStatusManager.update_order_status(
                order=order,
                new_status='confirmed',
                changed_by=order.farmer,  # System confirmation
                notes='Auto-confirmed after 24 hours'
            )
            
            # Send notification
            send_order_status_update_email.delay(
                order.id, 'pending', 'confirmed'
            )
            
            confirmed_count += 1
            
        except Exception as e:
            print(f"Error auto-confirming order {order.id}: {str(e)}")
    
    return f"Auto-confirmed {confirmed_count} orders"


@shared_task
def send_delivery_reminder(order_id):
    """
    Send delivery reminder to farmer and buyer.
    """
    try:
        order = Order.objects.get(id=order_id)
        
        if order.preferred_delivery_date:
            # Send reminder to farmer
            farmer_subject = f'Delivery Reminder #{order.order_number} - Farm2Market'
            farmer_context = {
                'order': order,
                'user': order.farmer,
                'user_type': 'farmer'
            }
            
            farmer_html_message = render_to_string('emails/delivery_reminder_farmer.html', farmer_context)
            
            send_mail(
                subject=farmer_subject,
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[order.farmer.email],
                html_message=farmer_html_message,
                fail_silently=False,
            )
            
            # Send reminder to buyer
            buyer_subject = f'Delivery Reminder #{order.order_number} - Farm2Market'
            buyer_context = {
                'order': order,
                'user': order.buyer,
                'user_type': 'buyer'
            }
            
            buyer_html_message = render_to_string('emails/delivery_reminder_buyer.html', buyer_context)
            
            send_mail(
                subject=buyer_subject,
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[order.buyer.email],
                html_message=buyer_html_message,
                fail_silently=False,
            )
            
            return f"Delivery reminders sent for order {order.order_number}"
        else:
            return f"Order {order.order_number} has no preferred delivery date"
        
    except Order.DoesNotExist:
        return f"Order {order_id} not found"
    except Exception as e:
        return f"Error sending delivery reminders: {str(e)}"


@shared_task
def generate_order_analytics_report():
    """
    Generate order analytics report.
    """
    try:
        # Get analytics for the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Total orders
        total_orders = Order.objects.filter(created_at__gte=thirty_days_ago).count()
        
        # Orders by status
        order_statuses = Order.objects.filter(
            created_at__gte=thirty_days_ago
        ).values('status').annotate(
            count=models.Count('id')
        )
        
        # Total revenue
        completed_orders = Order.objects.filter(
            created_at__gte=thirty_days_ago,
            status='delivered'
        )
        total_revenue = sum(order.total_amount for order in completed_orders)
        
        # Average order value
        avg_order_value = total_revenue / completed_orders.count() if completed_orders.count() > 0 else 0
        
        # Top farmers by orders
        top_farmers = Order.objects.filter(
            created_at__gte=thirty_days_ago
        ).values('farmer__full_name').annotate(
            order_count=models.Count('id')
        ).order_by('-order_count')[:10]
        
        analytics_data = {
            'period': '30 days',
            'total_orders': total_orders,
            'order_statuses': list(order_statuses),
            'total_revenue': float(total_revenue),
            'avg_order_value': float(avg_order_value),
            'top_farmers': list(top_farmers),
            'generated_at': timezone.now().isoformat(),
        }
        
        # TODO: Store analytics data or send to admin
        # cache.set('order_analytics_report', analytics_data, timeout=86400)
        
        return f"Generated order analytics report: {total_orders} orders, ${total_revenue:.2f} revenue"
        
    except Exception as e:
        return f"Error generating order analytics report: {str(e)}"
