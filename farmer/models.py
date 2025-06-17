from django.db import models
from users.models import User
from django.utils.text import slugify

# FarmerProfile stores extended info for each farmer
class FarmerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='farmer_profile')
    name = models.CharField(max_length=100, help_text='Full name of the farmer')
    bio = models.TextField(blank=True, help_text='Short biography')
    location = models.CharField(max_length=255, blank=True, help_text='Village or address')
    contact = models.CharField(max_length=50, blank=True, help_text='Contact phone or email')
    profile_image = models.ImageField(upload_to='farmer_profiles/', blank=True, null=True, help_text='Profile image')
    slug = models.SlugField(unique=True, blank=True, help_text='URL slug for profile')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, help_text='Latitude')
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, help_text='Longitude')

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name or self.user.email

    def average_rating(self):
        from reservations.models import Review
        reviews = self.reviews.all()
        if reviews.exists():
            return round(sum(r.rating for r in reviews) / reviews.count(), 2)
        return None
