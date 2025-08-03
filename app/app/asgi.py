"""
ASGI config for app project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more below information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import asyncio
import structlog
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from chat.routing import websocket_urlpatterns
from chat.consumers import send_goodbye_to_all_consumers
from chat.signals import setup_signal_handlers

logger = structlog.get_logger(__name__)

# Set Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

# Setup signal handlers for graceful shutdown
setup_signal_handlers()

# Create the ASGI application
django_asgi_app = get_asgi_application()

# Create final application
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
