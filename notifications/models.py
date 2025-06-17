from django.db import models
from django.db import models
from users.models import User
from farmer.models import FarmerProfile

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('message', 'Message'),
        ('reservation', 'Reservation'),
        ('price_change', 'Price Change'),
        ('weather', 'Weather'),
        ('pest', 'Pest'),
        ('other', 'Other'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=100)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    related_entity_type = models.CharField(max_length=50, blank=True, null=True)
    related_entity_id = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} ({self.notification_type})"

class Alert(models.Model):
    ALERT_TYPES = [
        ('weather', 'Weather'),
        ('pest', 'Pest'),
        ('system', 'System'),
    ]
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES)
    title = models.CharField(max_length=100)
    message = models.TextField()
    severity = models.CharField(max_length=20)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} ({self.alert_type})"

# Create your models here.
