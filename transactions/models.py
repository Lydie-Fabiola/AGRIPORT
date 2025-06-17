from django.db import models
from users.models import User
from reservations.models import Reservation
from products.models import Product
from farmer.models import FarmerProfile

class Transaction(models.Model):
    TYPE_CHOICES = [
        ('collection', 'Collection'),
        ('disbursement', 'Disbursement'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    reservation = models.ForeignKey(Reservation, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='buyer_transactions')
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name='farmer_transactions')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='transactions')
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='XAF')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reference_id = models.CharField(max_length=100, unique=True)
    momo_reference = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message = models.TextField(blank=True)

    def __str__(self):
        return f"{self.type.title()} {self.amount} {self.currency} for {self.buyer.email} ({self.status})"

# Create your models here.
