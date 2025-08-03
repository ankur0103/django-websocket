import json
import structlog
from django.http import JsonResponse
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .metrics import connection_tracker
import time

logger = structlog.get_logger(__name__)

def healthz_view(request):
    """Liveness probe - always returns 200 if the app is running."""
    return JsonResponse({
        "status": "healthy",
        "color": getattr(settings, 'APP_COLOR', 'unknown'),
        "timestamp": time.time()
    })

def readyz_view(request):
    """Readiness probe - returns 200 if the app is ready to serve traffic."""
    try:
        # Check if Redis is available
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_add)("health_check", "health_check")
        async_to_sync(channel_layer.group_discard)("health_check", "health_check")
        
        return JsonResponse({
            "status": "ready",
            "color": getattr(settings, 'APP_COLOR', 'unknown'),
            "active_connections": connection_tracker.get_active_connections(),
            "timestamp": time.time()
        })
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        return JsonResponse({
            "status": "not_ready",
            "error": str(e),
            "color": getattr(settings, 'APP_COLOR', 'unknown'),
            "timestamp": time.time()
        }, status=503)

def status_view(request):
    """Status endpoint with detailed application information."""
    return JsonResponse({
        "status": "running",
        "color": getattr(settings, 'APP_COLOR', 'unknown'),
        "active_connections": connection_tracker.get_active_connections(),
        "heartbeat_interval": getattr(settings, 'HEARTBEAT_INTERVAL', 30),
        "graceful_shutdown_timeout": getattr(settings, 'GRACEFUL_SHUTDOWN_TIMEOUT', 10),
        "timestamp": time.time()
    }) 