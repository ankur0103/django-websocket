from django.urls import path
from . import views
from .views import pre_shutdown

app_name = 'chat'

urlpatterns = [
    path("", views.chat_home, name="home"),
    path("info", views.websocket_info, name="websocket_info"),
    path('pre-shutdown/', pre_shutdown),
] 