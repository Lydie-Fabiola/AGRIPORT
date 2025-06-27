"""
Celery configuration for Farm2Market backend.
"""
import os
from celery import Celery
from django.conf import settings
from decouple import config

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'farm2market_backend.settings')

app = Celery('farm2market_backend')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Celery Configuration
app.conf.update(
    broker_url=config('CELERY_BROKER_URL', default='redis://127.0.0.1:6379/0'),
    result_backend=config('CELERY_RESULT_BACKEND', default='redis://127.0.0.1:6379/0'),
    accept_content=['json'],
    task_serializer='json',
    result_serializer='json',
    timezone='Africa/Douala',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Celery Beat Schedule for periodic tasks
app.conf.beat_schedule = {
    'cleanup-expired-tokens': {
        'task': 'apps.accounts.tasks.cleanup_expired_tokens',
        'schedule': 3600.0,  # Run every hour
    },
    'send-daily-analytics': {
        'task': 'apps.analytics.tasks.send_daily_analytics',
        'schedule': 86400.0,  # Run daily
    },
    'cleanup-old-notifications': {
        'task': 'apps.notifications.tasks.cleanup_old_notifications',
        'schedule': 86400.0,  # Run daily
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
