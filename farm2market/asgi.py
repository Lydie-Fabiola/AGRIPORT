"""
ASGI config for farm2market project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
import conversations.routing
import notifications.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'farm2market.settings')

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(
            conversations.routing.websocket_urlpatterns + notifications.routing.websocket_urlpatterns
        )
    ),
})
