# chat/routing.py
from django.urls import path

from chatgroup import xconsumers

websocket_urlpatterns = [
    path(r'ws/chat/', xconsumers.ChatConsumer),
]
