from django.urls import path

from config.consumers import UpdatesConsumer

websocket_urlpatterns = [
    path("ws/updates/", UpdatesConsumer.as_asgi()),
]
