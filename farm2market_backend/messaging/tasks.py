"""
Celery tasks for messaging system.
"""
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import (
    Conversation, Message, MessageTemplate, TypingIndicator, UserOnlineStatus
)

User = get_user_model()
channel_layer = get_channel_layer()


@shared_task
def send_automated_message(conversation_id, template_name, variables=None, sender_id=None):
    """
    Send automated message using template.
    """
    try:
        conversation = Conversation.objects.get(id=conversation_id)
        template = MessageTemplate.objects.get(name=template_name, is_active=True)
        
        # Use system user if no sender specified
        if sender_id:
            sender = User.objects.get(id=sender_id)
        else:
            # Create or get system user
            sender, created = User.objects.get_or_create(
                username='system',
                defaults={
                    'email': 'system@farm2market.com',
                    'first_name': 'System',
                    'last_name': 'Bot',
                    'user_type': 'Admin',
                    'is_active': False
                }
            )
        
        # Render template content
        content = template.render(**(variables or {}))
        
        # Create message
        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            content=content,
            message_type='system'
        )
        
        # Broadcast message to conversation participants
        async_to_sync(channel_layer.group_send)(
            f'conversation_{conversation_id}',
            {
                'type': 'new_message',
                'message': {
                    'id': message.id,
                    'content': message.content,
                    'sender': {
                        'id': sender.id,
                        'full_name': sender.full_name,
                        'user_type': sender.user_type
                    },
                    'message_type': 'system',
                    'created_at': message.created_at.isoformat()
                },
                'sender_id': sender.id
            }
        )
        
        return f"Automated message sent to conversation {conversation_id}"
        
    except (Conversation.DoesNotExist, MessageTemplate.DoesNotExist, User.DoesNotExist) as e:
        return f"Error sending automated message: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@shared_task
def send_order_confirmation_message(order_id):
    """
    Send order confirmation message to conversation.
    """
    try:
        from apps.orders.models import Order
        
        order = Order.objects.get(id=order_id)
        
        # Find or create conversation between buyer and farmer
        conversation = Conversation.objects.filter(
            participants__in=[order.buyer, order.farmer],
            related_order=order
        ).first()
        
        if not conversation:
            # Create new conversation
            conversation = Conversation.objects.create(
                subject=f"Order {order.order_number}",
                related_order=order
            )
            conversation.add_participant(order.buyer)
            conversation.add_participant(order.farmer)
        
        # Send automated message
        variables = {
            'order_number': order.order_number,
            'buyer_name': order.buyer.full_name,
            'farmer_name': order.farmer.full_name,
            'total_amount': order.total_amount,
            'delivery_date': order.preferred_delivery_date.strftime('%Y-%m-%d') if order.preferred_delivery_date else 'TBD'
        }
        
        send_automated_message.delay(
            conversation.id,
            'Order Confirmation',
            variables,
            order.farmer.id
        )
        
        return f"Order confirmation message sent for order {order.order_number}"
        
    except Exception as e:
        return f"Error sending order confirmation message: {str(e)}"


@shared_task
def send_delivery_update_message(order_id, status_update):
    """
    Send delivery update message to conversation.
    """
    try:
        from apps.orders.models import Order
        
        order = Order.objects.get(id=order_id)
        
        # Find conversation for this order
        conversation = Conversation.objects.filter(
            participants__in=[order.buyer, order.farmer],
            related_order=order
        ).first()
        
        if conversation:
            variables = {
                'order_number': order.order_number,
                'status': order.get_status_display(),
                'status_update': status_update,
                'farmer_name': order.farmer.full_name
            }
            
            send_automated_message.delay(
                conversation.id,
                'Delivery Update',
                variables,
                order.farmer.id
            )
            
            return f"Delivery update message sent for order {order.order_number}"
        else:
            return f"No conversation found for order {order.order_number}"
        
    except Exception as e:
        return f"Error sending delivery update message: {str(e)}"


@shared_task
def send_price_inquiry_template(product_id, buyer_id, farmer_id, inquiry_details):
    """
    Send price inquiry message using template.
    """
    try:
        from apps.products.models import Product
        
        product = Product.objects.get(id=product_id)
        buyer = User.objects.get(id=buyer_id)
        farmer = User.objects.get(id=farmer_id)
        
        # Find or create conversation
        conversation = Conversation.objects.filter(
            participants__in=[buyer, farmer],
            related_product=product
        ).first()
        
        if not conversation:
            conversation = Conversation.objects.create(
                subject=f"Inquiry about {product.product_name}",
                related_product=product
            )
            conversation.add_participant(buyer)
            conversation.add_participant(farmer)
        
        # Send inquiry message
        variables = {
            'product_name': product.product_name,
            'buyer_name': buyer.full_name,
            'farmer_name': farmer.full_name,
            'current_price': product.price,
            'quantity_needed': inquiry_details.get('quantity', 'Not specified'),
            'delivery_date': inquiry_details.get('delivery_date', 'Flexible'),
            'additional_notes': inquiry_details.get('notes', '')
        }
        
        send_automated_message.delay(
            conversation.id,
            'Price Inquiry',
            variables,
            buyer.id
        )
        
        return f"Price inquiry sent for product {product.product_name}"
        
    except Exception as e:
        return f"Error sending price inquiry: {str(e)}"


@shared_task
def cleanup_expired_typing_indicators():
    """
    Clean up expired typing indicators.
    """
    expired_indicators = TypingIndicator.objects.filter(
        expires_at__lt=timezone.now()
    )
    
    deleted_count = expired_indicators.count()
    expired_indicators.delete()
    
    return f"Cleaned up {deleted_count} expired typing indicators"


@shared_task
def update_user_offline_status():
    """
    Update users to offline status if they haven't been seen recently.
    """
    # Mark users as offline if they haven't been seen in the last 5 minutes
    cutoff_time = timezone.now() - timedelta(minutes=5)
    
    offline_users = UserOnlineStatus.objects.filter(
        is_online=True,
        last_seen__lt=cutoff_time
    )
    
    updated_count = 0
    
    for user_status in offline_users:
        user_status.is_online = False
        user_status.save()
        
        # Broadcast offline status to user's conversations
        user_conversations = Conversation.objects.filter(
            participants=user_status.user,
            conversationparticipant__is_active=True
        )
        
        for conversation in user_conversations:
            async_to_sync(channel_layer.group_send)(
                f'conversation_{conversation.id}',
                {
                    'type': 'user_status_update',
                    'user_id': user_status.user.id,
                    'is_online': False,
                    'timestamp': timezone.now().isoformat()
                }
            )
        
        updated_count += 1
    
    return f"Updated {updated_count} users to offline status"


@shared_task
def send_message_notification(message_id):
    """
    Send push notification for new message to offline users.
    """
    try:
        message = Message.objects.get(id=message_id)
        conversation = message.conversation
        
        # Get participants who are offline
        offline_participants = []
        for participant in conversation.participants.exclude(id=message.sender.id):
            online_status = getattr(participant, 'online_status', None)
            if not online_status or not online_status.is_online:
                offline_participants.append(participant)
        
        # Send notifications to offline participants
        for participant in offline_participants:
            async_to_sync(channel_layer.group_send)(
                f'user_{participant.id}',
                {
                    'type': 'new_message_notification',
                    'conversation_id': conversation.id,
                    'sender_name': message.sender.full_name,
                    'message_preview': message.content[:100] + '...' if len(message.content) > 100 else message.content,
                    'timestamp': timezone.now().isoformat()
                }
            )
        
        return f"Sent notifications to {len(offline_participants)} offline users"
        
    except Message.DoesNotExist:
        return f"Message {message_id} not found"
    except Exception as e:
        return f"Error sending message notification: {str(e)}"


@shared_task
def create_default_message_templates():
    """
    Create default message templates if they don't exist.
    """
    templates = [
        {
            'name': 'Order Confirmation',
            'template_type': 'order_confirmation',
            'content': 'Hello {{buyer_name}}, your order {{order_number}} has been confirmed! Total amount: ${{total_amount}}. Expected delivery: {{delivery_date}}. Thank you for choosing our farm!',
            'variables': {
                'buyer_name': 'Buyer\'s full name',
                'order_number': 'Order number',
                'total_amount': 'Total order amount',
                'delivery_date': 'Expected delivery date'
            }
        },
        {
            'name': 'Delivery Update',
            'template_type': 'delivery_update',
            'content': 'Hi! Update on your order {{order_number}}: {{status_update}}. Current status: {{status}}. We\'ll keep you posted on any changes. - {{farmer_name}}',
            'variables': {
                'order_number': 'Order number',
                'status': 'Current order status',
                'status_update': 'Status update message',
                'farmer_name': 'Farmer\'s name'
            }
        },
        {
            'name': 'Price Inquiry',
            'template_type': 'price_inquiry',
            'content': 'Hello {{farmer_name}}, I\'m interested in your {{product_name}} (currently ${{current_price}}). I need {{quantity_needed}} for {{delivery_date}}. {{additional_notes}} Could you please let me know your best price? Thanks! - {{buyer_name}}',
            'variables': {
                'farmer_name': 'Farmer\'s name',
                'product_name': 'Product name',
                'current_price': 'Current product price',
                'quantity_needed': 'Quantity needed',
                'delivery_date': 'Delivery date needed',
                'additional_notes': 'Additional notes',
                'buyer_name': 'Buyer\'s name'
            }
        },
        {
            'name': 'Negotiation Response',
            'template_type': 'negotiation',
            'content': 'Thank you for your inquiry about {{product_name}}. For the quantity you mentioned ({{quantity_needed}}), I can offer ${{offered_price}} per {{unit}}. This includes {{included_services}}. Let me know if this works for you! - {{farmer_name}}',
            'variables': {
                'product_name': 'Product name',
                'quantity_needed': 'Quantity requested',
                'offered_price': 'Offered price',
                'unit': 'Unit of measurement',
                'included_services': 'Included services',
                'farmer_name': 'Farmer\'s name'
            }
        }
    ]
    
    created_count = 0
    
    for template_data in templates:
        template, created = MessageTemplate.objects.get_or_create(
            name=template_data['name'],
            defaults=template_data
        )
        if created:
            created_count += 1
    
    return f"Created {created_count} default message templates"


@shared_task
def generate_messaging_analytics():
    """
    Generate messaging analytics report.
    """
    try:
        # Get analytics for the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Total messages
        total_messages = Message.objects.filter(
            created_at__gte=thirty_days_ago
        ).count()
        
        # Active conversations
        active_conversations = Conversation.objects.filter(
            last_message_at__gte=thirty_days_ago,
            is_active=True
        ).count()
        
        # Messages by type
        message_types = Message.objects.filter(
            created_at__gte=thirty_days_ago
        ).values('message_type').annotate(
            count=models.Count('id')
        )
        
        # Most active users
        active_users = Message.objects.filter(
            created_at__gte=thirty_days_ago
        ).values('sender__full_name').annotate(
            message_count=models.Count('id')
        ).order_by('-message_count')[:10]
        
        # Response time analysis (simplified)
        conversations_with_responses = Conversation.objects.filter(
            last_message_at__gte=thirty_days_ago,
            messages__created_at__gte=thirty_days_ago
        ).distinct().count()
        
        analytics_data = {
            'period': '30 days',
            'total_messages': total_messages,
            'active_conversations': active_conversations,
            'message_types': list(message_types),
            'active_users': list(active_users),
            'conversations_with_responses': conversations_with_responses,
            'generated_at': timezone.now().isoformat(),
        }
        
        # TODO: Store analytics data or send to admin
        # cache.set('messaging_analytics_report', analytics_data, timeout=86400)
        
        return f"Generated messaging analytics: {total_messages} messages, {active_conversations} active conversations"
        
    except Exception as e:
        return f"Error generating messaging analytics: {str(e)}"
