"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.shortcuts import redirect, render
from django.conf import settings
from monitoring import views as monitoring_views
from monitoring import metrics

def test_view(request):
    """Test view that passes base URL to template."""
    return render(request, 'test.html', {
        'ws_base_url': settings.WS_BASE_URL,
    })

def redirect_to_test(request):
    """Redirect root to test page."""
    return redirect('/test/')

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", redirect_to_test, name="home"),
    path("test/", test_view, name="test"),
    
    # Include chat app URLs
    path("chat/", include("chat.urls")),
    
    # Health endpoints - handle both with and without trailing slash
    path("healthz", monitoring_views.healthz_view, name="healthz"),
    path("healthz/", monitoring_views.healthz_view, name="healthz_slash"),
    path("readyz", monitoring_views.readyz_view, name="readyz"),
    path("readyz/", monitoring_views.readyz_view, name="readyz_slash"),
    path("status", monitoring_views.status_view, name="status"),
    path("status/", monitoring_views.status_view, name="status_slash"),
    path("metrics", metrics.metrics_view, name="metrics"),
    path("metrics/", metrics.metrics_view, name="metrics_slash"),
]
