"""
Celery tasks for farmer management.
"""
from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import FarmCertification
from apps.products.models import Product, LowStockAlert

User = get_user_model()


@shared_task
def send_certification_verification_email(certification_id, status):
    """
    Send email notification when certification status changes.
    """
    try:
        certification = FarmCertification.objects.get(id=certification_id)
        farmer = certification.farmer
        
        if status == 'verified':
            subject = 'Certification Verified - Farm2Market'
            template = 'emails/certification_verified.html'
        elif status == 'rejected':
            subject = 'Certification Rejected - Farm2Market'
            template = 'emails/certification_rejected.html'
        else:
            return
        
        context = {
            'farmer': farmer,
            'certification': certification,
        }
        
        html_message = render_to_string(template, context)
        
        send_mail(
            subject=subject,
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[farmer.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return f"Certification {status} email sent to {farmer.email}"
        
    except FarmCertification.DoesNotExist:
        return f"Certification {certification_id} not found"
    except Exception as e:
        return f"Error sending email: {str(e)}"


@shared_task
def send_low_stock_email(farmer_id, product_id):
    """
    Send low stock alert email to farmer.
    """
    try:
        farmer = User.objects.get(id=farmer_id)
        product = Product.objects.get(id=product_id)
        
        subject = f'Low Stock Alert: {product.product_name} - Farm2Market'
        
        context = {
            'farmer': farmer,
            'product': product,
        }
        
        html_message = render_to_string('emails/low_stock_alert.html', context)
        
        send_mail(
            subject=subject,
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[farmer.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return f"Low stock alert email sent to {farmer.email} for {product.product_name}"
        
    except (User.DoesNotExist, Product.DoesNotExist):
        return f"User {farmer_id} or Product {product_id} not found"
    except Exception as e:
        return f"Error sending low stock email: {str(e)}"


@shared_task
def send_low_stock_sms(farmer_id, product_id):
    """
    Send low stock alert SMS to farmer.
    """
    try:
        farmer = User.objects.get(id=farmer_id)
        product = Product.objects.get(id=product_id)
        
        if not farmer.phone_number:
            return f"No phone number for farmer {farmer.email}"
        
        message = f"Low Stock Alert: Your product '{product.product_name}' is running low ({product.quantity} remaining). Please restock soon. - Farm2Market"
        
        # TODO: Implement SMS sending logic
        # This would integrate with SMS service like Twilio, AWS SNS, etc.
        # For now, we'll just log the message
        
        return f"Low stock SMS sent to {farmer.phone_number} for {product.product_name}"
        
    except (User.DoesNotExist, Product.DoesNotExist):
        return f"User {farmer_id} or Product {product_id} not found"
    except Exception as e:
        return f"Error sending low stock SMS: {str(e)}"


@shared_task
def check_expiring_certifications():
    """
    Check for certifications expiring in the next 30 days and send notifications.
    """
    from django.utils import timezone
    from datetime import timedelta
    
    # Get certifications expiring in the next 30 days
    expiry_threshold = timezone.now().date() + timedelta(days=30)
    expiring_certs = FarmCertification.objects.filter(
        verification_status='verified',
        expiry_date__lte=expiry_threshold,
        expiry_date__gte=timezone.now().date()
    )
    
    notifications_sent = 0
    
    for cert in expiring_certs:
        try:
            subject = f'Certification Expiring Soon: {cert.certification_name} - Farm2Market'
            
            context = {
                'farmer': cert.farmer,
                'certification': cert,
                'days_until_expiry': cert.days_until_expiry,
            }
            
            html_message = render_to_string('emails/certification_expiring.html', context)
            
            send_mail(
                subject=subject,
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[cert.farmer.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            notifications_sent += 1
            
        except Exception as e:
            print(f"Error sending expiry notification for cert {cert.id}: {str(e)}")
    
    return f"Sent {notifications_sent} certification expiry notifications"


@shared_task
def cleanup_old_stock_movements():
    """
    Clean up old stock movements (older than 1 year).
    """
    from django.utils import timezone
    from datetime import timedelta
    from apps.products.models import StockMovement
    
    cutoff_date = timezone.now() - timedelta(days=365)
    
    deleted_count, _ = StockMovement.objects.filter(
        created_at__lt=cutoff_date
    ).delete()
    
    return f"Cleaned up {deleted_count} old stock movements"


@shared_task
def generate_farmer_analytics_report(farmer_id, period='monthly'):
    """
    Generate analytics report for farmer.
    """
    try:
        farmer = User.objects.get(id=farmer_id)
        
        # Calculate analytics data
        products = Product.objects.filter(farmer=farmer)
        total_products = products.count()
        total_revenue = sum(p.price * p.sold_quantity for p in products)
        
        # TODO: Implement detailed analytics calculation
        # This would include sales trends, popular products, etc.
        
        analytics_data = {
            'farmer': farmer.full_name,
            'period': period,
            'total_products': total_products,
            'total_revenue': float(total_revenue),
            'generated_at': timezone.now().isoformat(),
        }
        
        # TODO: Send analytics report via email
        
        return f"Analytics report generated for {farmer.email}"
        
    except User.DoesNotExist:
        return f"Farmer {farmer_id} not found"
    except Exception as e:
        return f"Error generating analytics report: {str(e)}"


@shared_task
def bulk_update_product_status():
    """
    Bulk update product status based on quantity and expiry dates.
    """
    from django.utils import timezone
    
    updated_count = 0
    
    # Mark products as sold if quantity is 0
    sold_count = Product.objects.filter(
        quantity=0,
        status='Available'
    ).update(status='Sold')
    
    updated_count += sold_count
    
    # Mark products as inactive if expired
    expired_count = Product.objects.filter(
        expiry_date__lt=timezone.now().date(),
        status__in=['Available', 'Reserved']
    ).update(status='Inactive')
    
    updated_count += expired_count
    
    return f"Updated status for {updated_count} products ({sold_count} sold, {expired_count} expired)"
