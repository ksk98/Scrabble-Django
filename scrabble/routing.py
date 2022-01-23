from django.urls import re_path

from scrabble import consumers

websocket_urlpatterns = [
    re_path(r'ws/scrabble/(?P<room_id>\w+)/$', consumers.PlayerConsumer.as_asgi()),
]
