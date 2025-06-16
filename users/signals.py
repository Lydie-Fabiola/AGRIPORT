from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User
from farmer.models import FarmerProfile
from buyer.models import BuyerProfile

@receiver(post_save, sender=User)
def create_farmer_profile(sender, instance, created, **kwargs):
    if created and (instance.role == 'farmer' or instance.is_farmer):
        FarmerProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def create_buyer_profile(sender, instance, created, **kwargs):
    if created and (instance.role == 'buyer' or instance.is_buyer):
        BuyerProfile.objects.get_or_create(user=instance) 