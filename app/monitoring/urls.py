from django.urls import path
from . import views, metrics

urlpatterns = [
    path('healthz/', views.healthz_view, name='healthz'),
    path('readyz/', views.readyz_view, name='readyz'),
    path('status/', views.status_view, name='status'),
    path('metrics/', metrics.metrics_view, name='metrics'),
] 