from django.urls import path, re_path
from . import views, consumers
from .views import pre_shutdown

app_name = 'chat'

# HTTP URL patterns
urlpatterns = [
    path("", views.chat_home, name="home"),
    path("info", views.websocket_info, name="websocket_info"),
    path('pre-shutdown/', pre_shutdown),
]

# WebSocket URL patterns
websocket_urlpatterns = [
    re_path(r'^ws/chat/$', consumers.ChatConsumer.as_asgi())
] 