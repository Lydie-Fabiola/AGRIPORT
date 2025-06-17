from celery import shared_task
from farmer.models import FarmerProfile
from .models import Alert
from .utils import fetch_weather_alerts, fetch_pest_alerts

def broadcast_weather_alerts():
    farmers = FarmerProfile.objects.all()
    for farmer in farmers:
        if farmer.latitude and farmer.longitude:
            alert_data = fetch_weather_alerts(farmer.latitude, farmer.longitude)
            if alert_data:
                Alert.objects.create(
                    farmer=farmer,
                    alert_type='weather',
                    title=alert_data['title'],
                    message=alert_data['message'],
                    severity=alert_data['severity']
                )

def broadcast_pest_alerts():
    farmers = FarmerProfile.objects.all()
    for farmer in farmers:
        # Use location/region field; here we use 'location' as region
        region = farmer.location or ''
        alert_data = fetch_pest_alerts(region)
        if alert_data:
            Alert.objects.create(
                farmer=farmer,
                alert_type='pest',
                title=alert_data['title'],
                message=alert_data['message'],
                severity=alert_data['severity']
            )

@shared_task
def scheduled_weather_alerts():
    broadcast_weather_alerts()

@shared_task
def scheduled_pest_alerts():
    broadcast_pest_alerts()
