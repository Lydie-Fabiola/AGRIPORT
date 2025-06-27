"""
Celery tasks for buyer management.
"""
from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from .models import Wishlist, FavoriteFarmer, BuyerPreferences
from apps.products.models import Product

User = get_user_model()


@shared_task
def send_product_available_notification(buyer_id, product_id):
    """
    Send notification when a wishlisted product becomes available.
    """
    try:
        buyer = User.objects.get(id=buyer_id)
        product = Product.objects.get(id=product_id)
        wishlist_item = Wishlist.objects.get(buyer=buyer, product=product)
        
        # Check buyer preferences
        preferences = getattr(buyer, 'buyer_preferences', None)
        if not preferences or not preferences.new_products_alerts:
            return "Buyer has disabled product availability notifications"
        
        subject = f'Product Available: {product.product_name} - Farm2Market'
        
        context = {
            'buyer': buyer,
            'product': product,
            'wishlist_item': wishlist_item,
        }
        
        # Send email if enabled
        if preferences.email_notifications:
            html_message = render_to_string('emails/product_available.html', context)
            
            send_mail(
                subject=subject,
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[buyer.email],
                html_message=html_message,
                fail_silently=False,
            )
        
        # Send SMS if enabled
        if preferences.sms_notifications and buyer.phone_number:
            message = f"Good news! '{product.product_name}' from {product.farmer.full_name} is now available. Check it out on Farm2Market!"
            # TODO: Implement SMS sending
            # send_sms(buyer.phone_number, message)
        
        return f"Product availability notification sent to {buyer.email}"
        
    except (User.DoesNotExist, Product.DoesNotExist, Wishlist.DoesNotExist):
        return f"User {buyer_id}, Product {product_id}, or Wishlist item not found"
    except Exception as e:
        return f"Error sending product availability notification: {str(e)}"


@shared_task
def send_price_drop_notification(buyer_id, product_id, old_price, new_price):
    """
    Send notification when a wishlisted product price drops.
    """
    try:
        buyer = User.objects.get(id=buyer_id)
        product = Product.objects.get(id=product_id)
        wishlist_item = Wishlist.objects.get(buyer=buyer, product=product)
        
        # Check buyer preferences
        preferences = getattr(buyer, 'buyer_preferences', None)
        if not preferences or not preferences.price_drop_alerts:
            return "Buyer has disabled price drop notifications"
        
        subject = f'Price Drop Alert: {product.product_name} - Farm2Market'
        
        context = {
            'buyer': buyer,
            'product': product,
            'wishlist_item': wishlist_item,
            'old_price': old_price,
            'new_price': new_price,
            'savings': old_price - new_price,
        }
        
        # Send email if enabled
        if preferences.email_notifications:
            html_message = render_to_string('emails/price_drop_alert.html', context)
            
            send_mail(
                subject=subject,
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[buyer.email],
                html_message=html_message,
                fail_silently=False,
            )
        
        # Send SMS if enabled
        if preferences.sms_notifications and buyer.phone_number:
            savings = old_price - new_price
            message = f"Price Drop! '{product.product_name}' is now {new_price} (was {old_price}). Save {savings}! - Farm2Market"
            # TODO: Implement SMS sending
            # send_sms(buyer.phone_number, message)
        
        return f"Price drop notification sent to {buyer.email}"
        
    except (User.DoesNotExist, Product.DoesNotExist, Wishlist.DoesNotExist):
        return f"User {buyer_id}, Product {product_id}, or Wishlist item not found"
    except Exception as e:
        return f"Error sending price drop notification: {str(e)}"


@shared_task
def send_new_products_from_favorite_farmers(buyer_id):
    """
    Send notification about new products from favorite farmers.
    """
    try:
        buyer = User.objects.get(id=buyer_id)
        
        # Check buyer preferences
        preferences = getattr(buyer, 'buyer_preferences', None)
        if not preferences or not preferences.farmer_updates:
            return "Buyer has disabled farmer updates"
        
        # Get favorite farmers
        favorite_farmers = FavoriteFarmer.objects.filter(buyer=buyer)
        
        if not favorite_farmers.exists():
            return "Buyer has no favorite farmers"
        
        # Get new products from the last 24 hours
        from datetime import timedelta
        yesterday = timezone.now() - timedelta(days=1)
        
        new_products = []
        for favorite in favorite_farmers:
            farmer_new_products = Product.objects.filter(
                farmer=favorite.farmer,
                created_at__gte=yesterday,
                status='Available'
            )
            new_products.extend(farmer_new_products)
        
        if not new_products:
            return "No new products from favorite farmers"
        
        subject = f'New Products from Your Favorite Farmers - Farm2Market'
        
        context = {
            'buyer': buyer,
            'new_products': new_products,
            'product_count': len(new_products),
        }
        
        # Send email if enabled
        if preferences.email_notifications:
            html_message = render_to_string('emails/new_products_from_favorites.html', context)
            
            send_mail(
                subject=subject,
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[buyer.email],
                html_message=html_message,
                fail_silently=False,
            )
        
        return f"New products notification sent to {buyer.email} for {len(new_products)} products"
        
    except User.DoesNotExist:
        return f"User {buyer_id} not found"
    except Exception as e:
        return f"Error sending new products notification: {str(e)}"


@shared_task
def send_weekly_wishlist_summary(buyer_id):
    """
    Send weekly summary of wishlist status.
    """
    try:
        buyer = User.objects.get(id=buyer_id)
        
        # Check buyer preferences
        preferences = getattr(buyer, 'buyer_preferences', None)
        if not preferences or not preferences.email_notifications:
            return "Buyer has disabled email notifications"
        
        # Get wishlist items
        wishlist_items = Wishlist.objects.filter(buyer=buyer)
        
        if not wishlist_items.exists():
            return "Buyer has no wishlist items"
        
        # Categorize wishlist items
        available_items = [item for item in wishlist_items if item.is_available]
        price_targets_met = [item for item in wishlist_items if item.is_price_target_met]
        out_of_stock_items = [item for item in wishlist_items if not item.is_available]
        
        subject = f'Your Weekly Wishlist Summary - Farm2Market'
        
        context = {
            'buyer': buyer,
            'total_items': wishlist_items.count(),
            'available_items': available_items,
            'price_targets_met': price_targets_met,
            'out_of_stock_items': out_of_stock_items,
        }
        
        html_message = render_to_string('emails/weekly_wishlist_summary.html', context)
        
        send_mail(
            subject=subject,
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[buyer.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return f"Weekly wishlist summary sent to {buyer.email}"
        
    except User.DoesNotExist:
        return f"User {buyer_id} not found"
    except Exception as e:
        return f"Error sending weekly wishlist summary: {str(e)}"


@shared_task
def cleanup_old_wishlist_items():
    """
    Clean up wishlist items for products that no longer exist or are inactive.
    """
    # Remove wishlist items for deleted or inactive products
    deleted_count = Wishlist.objects.filter(
        product__status='Inactive'
    ).delete()[0]
    
    return f"Cleaned up {deleted_count} wishlist items for inactive products"


@shared_task
def send_bulk_notifications_to_buyers():
    """
    Send bulk notifications to all buyers about new products, price drops, etc.
    """
    buyers = User.objects.filter(user_type='Buyer', is_active=True)
    
    notifications_sent = 0
    
    for buyer in buyers:
        try:
            # Send new products from favorite farmers
            send_new_products_from_favorite_farmers.delay(buyer.id)
            notifications_sent += 1
        except Exception as e:
            print(f"Error sending notification to buyer {buyer.id}: {str(e)}")
    
    return f"Queued notifications for {notifications_sent} buyers"


@shared_task
def generate_buyer_recommendations(buyer_id):
    """
    Generate product recommendations for buyer based on preferences and history.
    """
    try:
        buyer = User.objects.get(id=buyer_id)
        preferences = getattr(buyer, 'buyer_preferences', None)
        
        if not preferences:
            return "Buyer has no preferences set"
        
        # Get products based on preferred categories
        recommended_products = []
        
        if preferences.preferred_categories.exists():
            from apps.products.models import ProductCategory
            
            recommended_products = Product.objects.filter(
                product_categories__category__in=preferences.preferred_categories.all(),
                status='Available',
                quantity__gt=0
            ).distinct()
            
            # Filter by organic preference
            if preferences.organic_only:
                recommended_products = recommended_products.filter(organic_certified=True)
            
            # Filter by budget range
            if preferences.budget_range_min:
                recommended_products = recommended_products.filter(
                    price__gte=preferences.budget_range_min
                )
            if preferences.budget_range_max:
                recommended_products = recommended_products.filter(
                    price__lte=preferences.budget_range_max
                )
        
        # TODO: Store recommendations in cache or database
        # cache.set(f"recommendations_{buyer_id}", list(recommended_products.values()), timeout=86400)
        
        return f"Generated {recommended_products.count()} recommendations for buyer {buyer.email}"
        
    except User.DoesNotExist:
        return f"User {buyer_id} not found"
    except Exception as e:
        return f"Error generating recommendations: {str(e)}"
