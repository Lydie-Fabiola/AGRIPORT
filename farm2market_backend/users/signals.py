from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, FarmerProfile, BuyerProfile, AdminProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create appropriate profile when a user is created
    """
    if created:
        if instance.user_type == 'farmer':
            FarmerProfile.objects.create(farmer=instance)
        elif instance.user_type == 'buyer':
            BuyerProfile.objects.create(buyer=instance)
        elif instance.user_type == 'admin':
            AdminProfile.objects.create(admin=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Save the user profile when the user is saved
    """
    try:
        if instance.user_type == 'farmer' and hasattr(instance, 'farmer_profile'):
            instance.farmer_profile.save()
        elif instance.user_type == 'buyer' and hasattr(instance, 'buyer_profile'):
            instance.buyer_profile.save()
        elif instance.user_type == 'admin' and hasattr(instance, 'admin_profile'):
            instance.admin_profile.save()
    except Exception:
        # Profile doesn't exist yet, will be created by create_user_profile signal
        pass
