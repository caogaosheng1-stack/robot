from django.urls import re_path

from .consumers import SimulationConsumer

websocket_urlpatterns = [
    re_path(r"ws/sim/?$", SimulationConsumer.as_asgi()),
]

