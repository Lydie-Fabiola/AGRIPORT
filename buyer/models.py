from django.db import models
from users.models import User
from products.models import Product

# Create your models here.

class BuyerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='buyer_profile')
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=255, blank=True, help_text='Preferred delivery location')
    profile_image = models.ImageField(upload_to='buyer_profiles/', blank=True, null=True)
    bio = models.TextField(blank=True, help_text='Short biography')

    def __str__(self):
        return self.full_name or self.user.email

class WishlistItem(models.Model):
    buyer = models.ForeignKey('buyer.BuyerProfile', on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('buyer', 'product')

    def __str__(self):
        return f"{self.buyer.user.email} wishes {self.product.name}"
