"""
Management command to create default notification templates.
"""
from django.core.management.base import BaseCommand
from apps.notifications.models import NotificationTemplate, NotificationChannel


class Command(BaseCommand):
    help = 'Create default notification templates'
    
    def handle(self, *args, **options):
        templates = [
            # Order notifications
            {
                'name': 'New Order Received',
                'notification_type': 'order_received',
                'subject_template': 'New Order #{order_number} - Farm2Market',
                'content_template': 'You have received a new order #{order_number} from {buyer_name}. Total amount: ${total_amount}. Please review and confirm the order.',
                'variables': {
                    'order_number': 'Order number',
                    'buyer_name': 'Buyer full name',
                    'total_amount': 'Order total amount',
                    'order_status': 'Current order status'
                },
                'channels': ['EMAIL', 'IN_APP', 'PUSH']
            },
            {
                'name': 'Order Confirmed',
                'notification_type': 'order_confirmed',
                'subject_template': 'Order #{order_number} Confirmed - Farm2Market',
                'content_template': 'Great news! Your order #{order_number} has been confirmed by {farmer_name}. Total: ${total_amount}. We\'ll keep you updated on the progress.',
                'variables': {
                    'order_number': 'Order number',
                    'farmer_name': 'Farmer full name',
                    'total_amount': 'Order total amount'
                },
                'channels': ['EMAIL', 'IN_APP', 'PUSH']
            },
            {
                'name': 'Order Being Prepared',
                'notification_type': 'order_preparing',
                'subject_template': 'Order #{order_number} Being Prepared - Farm2Market',
                'content_template': 'Your order #{order_number} is now being prepared by {farmer_name}. We\'ll notify you when it\'s ready for pickup/delivery.',
                'variables': {
                    'order_number': 'Order number',
                    'farmer_name': 'Farmer full name'
                },
                'channels': ['IN_APP', 'PUSH']
            },
            {
                'name': 'Order Ready',
                'notification_type': 'order_ready',
                'subject_template': 'Order #{order_number} Ready - Farm2Market',
                'content_template': 'Your order #{order_number} is ready for pickup/delivery! Please contact {farmer_name} to arrange collection.',
                'variables': {
                    'order_number': 'Order number',
                    'farmer_name': 'Farmer full name'
                },
                'channels': ['EMAIL', 'IN_APP', 'PUSH', 'SMS']
            },
            {
                'name': 'Order In Transit',
                'notification_type': 'order_in_transit',
                'subject_template': 'Order #{order_number} On Its Way - Farm2Market',
                'content_template': 'Your order #{order_number} is now on its way to you! Expected delivery soon.',
                'variables': {
                    'order_number': 'Order number',
                    'tracking_number': 'Delivery tracking number'
                },
                'channels': ['IN_APP', 'PUSH', 'SMS']
            },
            {
                'name': 'Order Delivered',
                'notification_type': 'order_delivered',
                'subject_template': 'Order #{order_number} Delivered - Farm2Market',
                'content_template': 'Your order #{order_number} has been delivered! Thank you for choosing Farm2Market. Please rate your experience.',
                'variables': {
                    'order_number': 'Order number',
                    'farmer_name': 'Farmer full name'
                },
                'channels': ['EMAIL', 'IN_APP', 'PUSH']
            },
            {
                'name': 'Order Cancelled',
                'notification_type': 'order_cancelled',
                'subject_template': 'Order #{order_number} Cancelled - Farm2Market',
                'content_template': 'Your order #{order_number} has been cancelled. If you have any questions, please contact support.',
                'variables': {
                    'order_number': 'Order number',
                    'cancellation_reason': 'Reason for cancellation'
                },
                'channels': ['EMAIL', 'IN_APP', 'PUSH']
            },
            
            # Payment notifications
            {
                'name': 'Payment Received',
                'notification_type': 'payment_received',
                'subject_template': 'Payment Received for Order #{order_number} - Farm2Market',
                'content_template': 'Payment of ${total_amount} has been received for order #{order_number}. Thank you!',
                'variables': {
                    'order_number': 'Order number',
                    'total_amount': 'Payment amount'
                },
                'channels': ['EMAIL', 'IN_APP']
            },
            {
                'name': 'Payment Failed',
                'notification_type': 'payment_failed',
                'subject_template': 'Payment Failed for Order #{order_number} - Farm2Market',
                'content_template': 'Payment for order #{order_number} could not be processed. Please update your payment method.',
                'variables': {
                    'order_number': 'Order number',
                    'failure_reason': 'Payment failure reason'
                },
                'channels': ['EMAIL', 'IN_APP', 'PUSH']
            },
            
            # Product notifications
            {
                'name': 'New Product from Favorite Farmer',
                'notification_type': 'new_product_favorite_farmer',
                'subject_template': 'New Product from {farmer_name} - Farm2Market',
                'content_template': '{farmer_name} has added a new product: {product_name} at ${price}. Check it out now!',
                'variables': {
                    'farmer_name': 'Farmer full name',
                    'product_name': 'Product name',
                    'price': 'Product price'
                },
                'channels': ['EMAIL', 'IN_APP', 'PUSH']
            },
            {
                'name': 'Price Drop Alert',
                'notification_type': 'price_drop_wishlist',
                'subject_template': 'Price Drop Alert: {product_name} - Farm2Market',
                'content_template': 'Great news! {product_name} is now ${new_price} (was ${old_price}). Save ${savings}!',
                'variables': {
                    'product_name': 'Product name',
                    'old_price': 'Previous price',
                    'new_price': 'Current price',
                    'savings': 'Amount saved'
                },
                'channels': ['EMAIL', 'IN_APP', 'PUSH']
            },
            {
                'name': 'Stock Available Alert',
                'notification_type': 'stock_available_wishlist',
                'subject_template': 'Back in Stock: {product_name} - Farm2Market',
                'content_template': '{product_name} is back in stock! {available_quantity} units available. Order now before it sells out again.',
                'variables': {
                    'product_name': 'Product name',
                    'available_quantity': 'Available quantity'
                },
                'channels': ['EMAIL', 'IN_APP', 'PUSH']
            },
            {
                'name': 'Seasonal Products',
                'notification_type': 'seasonal_products',
                'subject_template': 'Seasonal Products Now Available - Farm2Market',
                'content_template': 'Fresh seasonal products are now available! Discover {product_count} new seasonal items from local farmers.',
                'variables': {
                    'product_count': 'Number of seasonal products',
                    'season': 'Current season'
                },
                'channels': ['EMAIL', 'IN_APP']
            },
            
            # Reservation notifications
            {
                'name': 'Reservation Request Received',
                'notification_type': 'reservation_received',
                'subject_template': 'New Reservation Request - Farm2Market',
                'content_template': '{buyer_name} has requested to reserve {quantity} units of {product_name} at ${price_offered} per unit.',
                'variables': {
                    'buyer_name': 'Buyer full name',
                    'product_name': 'Product name',
                    'quantity': 'Requested quantity',
                    'price_offered': 'Offered price per unit'
                },
                'channels': ['EMAIL', 'IN_APP', 'PUSH']
            },
            {
                'name': 'Reservation Accepted',
                'notification_type': 'reservation_accepted',
                'subject_template': 'Reservation Accepted - Farm2Market',
                'content_template': 'Great! {farmer_name} has accepted your reservation for {product_name}. Final price: ${final_price} per unit.',
                'variables': {
                    'farmer_name': 'Farmer full name',
                    'product_name': 'Product name',
                    'final_price': 'Final agreed price'
                },
                'channels': ['EMAIL', 'IN_APP', 'PUSH']
            },
            {
                'name': 'Reservation Rejected',
                'notification_type': 'reservation_rejected',
                'subject_template': 'Reservation Not Available - Farm2Market',
                'content_template': 'Unfortunately, {farmer_name} cannot fulfill your reservation for {product_name}. {farmer_response}',
                'variables': {
                    'farmer_name': 'Farmer full name',
                    'product_name': 'Product name',
                    'farmer_response': 'Farmer response message'
                },
                'channels': ['EMAIL', 'IN_APP', 'PUSH']
            },
            {
                'name': 'Reservation Counter Offer',
                'notification_type': 'reservation_counter_offer',
                'subject_template': 'Counter Offer for Reservation - Farm2Market',
                'content_template': '{farmer_name} has made a counter offer for {product_name}: ${counter_price} per unit (you offered ${original_price}).',
                'variables': {
                    'farmer_name': 'Farmer full name',
                    'product_name': 'Product name',
                    'original_price': 'Original offered price',
                    'counter_price': 'Counter offer price'
                },
                'channels': ['EMAIL', 'IN_APP', 'PUSH']
            },
            {
                'name': 'Reservation Expired',
                'notification_type': 'reservation_expired',
                'subject_template': 'Reservation Expired - Farm2Market',
                'content_template': 'Your reservation for {product_name} from {farmer_name} has expired. You can create a new reservation if still interested.',
                'variables': {
                    'product_name': 'Product name',
                    'farmer_name': 'Farmer full name'
                },
                'channels': ['EMAIL', 'IN_APP']
            },
            
            # System notifications
            {
                'name': 'Account Verification',
                'notification_type': 'account_verification',
                'subject_template': 'Verify Your Account - Farm2Market',
                'content_template': 'Welcome to Farm2Market! Please verify your account by clicking the link in this email.',
                'variables': {
                    'user_name': 'User full name',
                    'verification_link': 'Account verification link'
                },
                'channels': ['EMAIL']
            },
            {
                'name': 'Password Reset',
                'notification_type': 'password_reset',
                'subject_template': 'Password Reset Request - Farm2Market',
                'content_template': 'You requested a password reset. Click the link to reset your password. If you didn\'t request this, please ignore.',
                'variables': {
                    'user_name': 'User full name',
                    'reset_link': 'Password reset link'
                },
                'channels': ['EMAIL', 'SMS']
            },
            {
                'name': 'Security Alert',
                'notification_type': 'security_alert',
                'subject_template': 'Security Alert - Farm2Market',
                'content_template': 'We detected unusual activity on your account. Please review your recent activity and contact support if needed.',
                'variables': {
                    'user_name': 'User full name',
                    'activity_details': 'Suspicious activity details'
                },
                'channels': ['EMAIL', 'IN_APP', 'PUSH', 'SMS']
            },
            {
                'name': 'Welcome Message',
                'notification_type': 'welcome_message',
                'subject_template': 'Welcome to Farm2Market!',
                'content_template': 'Welcome to Farm2Market, {user_name}! We\'re excited to have you as a {user_type}. Start exploring fresh, local produce today.',
                'variables': {
                    'user_name': 'User full name',
                    'user_type': 'User type (Buyer/Farmer)'
                },
                'channels': ['EMAIL', 'IN_APP']
            },
            {
                'name': 'Profile Incomplete',
                'notification_type': 'profile_incomplete',
                'subject_template': 'Complete Your Profile - Farm2Market',
                'content_template': 'Hi {user_name}! Complete your profile to get the most out of Farm2Market. It only takes a few minutes.',
                'variables': {
                    'user_name': 'User full name',
                    'profile_url': 'Profile completion URL'
                },
                'channels': ['EMAIL', 'IN_APP']
            },
            {
                'name': 'Maintenance Announcement',
                'notification_type': 'maintenance_announcement',
                'subject_template': 'Scheduled Maintenance - Farm2Market',
                'content_template': 'Farm2Market will undergo scheduled maintenance on {maintenance_date}. Expected downtime: {duration}.',
                'variables': {
                    'maintenance_date': 'Maintenance date and time',
                    'duration': 'Expected downtime duration'
                },
                'channels': ['EMAIL', 'IN_APP']
            }
        ]
        
        created_count = 0
        
        for template_data in templates:
            channels = template_data.pop('channels', [])
            
            template, created = NotificationTemplate.objects.get_or_create(
                name=template_data['name'],
                notification_type=template_data['notification_type'],
                defaults=template_data
            )
            
            if created:
                # Add channels
                for channel_name in channels:
                    try:
                        channel = NotificationChannel.objects.get(name=channel_name)
                        template.channels.add(channel)
                    except NotificationChannel.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'Channel {channel_name} not found')
                        )
                
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created template: {template.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Template already exists: {template.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} notification templates')
        )
