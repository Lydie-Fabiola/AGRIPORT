from django.contrib import admin
from .models import FarmerProfile

@admin.register(FarmerProfile)
class FarmerProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'name', 'location', 'contact')
    search_fields = ('name', 'user__email', 'location')
