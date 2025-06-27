# This file makes Python treat the directory as a package

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
# Temporarily commented out until Celery is installed
# from .celery import app as celery_app

# __all__ = ('celery_app',)
