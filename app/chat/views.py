from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings

# Create your views here.

def websocket_info(request):
    """Provide information about WebSocket endpoints."""
    return JsonResponse({
        "websocket_endpoint": "/ws/chat/",
        "heartbeat_interval": settings.HEARTBEAT_INTERVAL,
        "color": settings.APP_COLOR,
        "message_format": {
            "send": {"message": "Your message here"},
            "receive": {"count": 1},
            "heartbeat": {"ts": "2024-01-01T12:00:00Z"},
            "goodbye": {"bye": True, "total": 5}
        }
    })

def chat_home(request):
    """Simple chat home page."""
    return render(request, 'chat/home.html')
