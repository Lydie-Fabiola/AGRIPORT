from django.db import models
from farmer.models import FarmerProfile
from django.conf import settings

class Category(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    icon_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('sold', 'Sold'),
    ]
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='available')
    is_organic = models.BooleanField(default=False)
    is_fresh_today = models.BooleanField(default=False)
    harvest_date = models.DateField(blank=True, null=True)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    featured = models.BooleanField(default=False, help_text='Mark as featured product')
    popularity_score = models.FloatField(default=0, help_text='Score for ranking products (views, sales, etc)')

    def __str__(self):
        return self.name
