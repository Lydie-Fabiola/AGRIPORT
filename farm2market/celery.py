from notifications.tasks import scheduled_weather_alerts

CELERY_BEAT_SCHEDULE = {
        'weather-alerts-every-6-hours': {
            'task': 'notifications.tasks.scheduled_weather_alerts',
            'schedule': 21600,  # every 6 hours
        },
        'pest-alerts-every-12-hours': {
            'task': 'notifications.tasks.scheduled_pest_alerts',
            'schedule': 43200,  # every 12 hours
        },
    }
