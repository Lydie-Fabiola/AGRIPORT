import requests
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import json

def fetch_weather_alerts(lat, lon):
    url = (
        f"https://api.openweathermap.org/data/2.5/weather?"
        f"lat={lat}&lon={lon}&appid={settings.OPENWEATHER_API_KEY}&units=metric"
    )
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    # Example: Check for rain or extreme weather
    weather = data.get('weather', [{}])[0].get('main', '')
    description = data.get('weather', [{}])[0].get('description', '')
    if weather.lower() in ['rain', 'storm', 'thunderstorm']:
        return {
            'title': f"Weather Alert: {weather}",
            'message': f"{description.capitalize()} expected in your area.",
            'severity': 'warning'
        }
    return None

# Example pest/disease alert fetcher (replace with real API as needed)
def fetch_pest_alerts(region):
    resp = requests.get(f"https://realpestapi.example.com/alerts?region={region}")
    resp.raise_for_status()
    data = resp.json()
    if data.get('outbreak'):
           return {
               'title': "Pest Alert",
               'message': data['description'],
               'severity': 'danger'
           }
    return None
    # --- DEMO ONLY ---
    if region.lower() == 'northwest':
        return {
            'title': "Pest Alert",
            'message': "Armyworm outbreak detected in your region. Monitor your crops closely.",
            'severity': 'danger'
        }
    return None

def send_notification_ws(user_id, notification):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'notifications_{user_id}',
        {
            'type': 'notify',
            'notification': notification
        }
    )
