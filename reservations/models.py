from django.db import models
from products.models import Product
from users.models import User

class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reservations')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations')
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    pickup_time = models.DateTimeField(blank=True, null=True)
    delivery_option = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    note_to_farmer = models.TextField(blank=True, help_text='Optional note from buyer to farmer')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'buyer'],
                condition=~models.Q(status__in=['rejected', 'completed']),
                name='unique_unresolved_reservation_per_buyer_product'
            )
        ]

    def __str__(self):
        return f"Reservation #{self.id} for {self.product.name} by {self.buyer.email}"

class Review(models.Model):
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name='review')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    farmer = models.ForeignKey('farmer.FarmerProfile', on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.reviewer.email} for {self.farmer.user.email} ({self.rating})"
