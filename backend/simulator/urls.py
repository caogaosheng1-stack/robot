from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("api/start", views.api_start),
    path("api/stop", views.api_stop),
    path("api/data", views.api_data),
    path("api/stats", views.api_stats),
    path("api/items", views.api_items),
    path("api/robots", views.api_robots),
    path("api/bins", views.api_bins),
    path("api/time", views.api_time),
    path("api/history", views.api_history),
]

