from django.urls import re_path
from . import consumers
from .plugin_system import plugin_registry

websocket_urlpatterns = [
    re_path(r'ws/system/shell/$', consumers.TerminalConsumer.as_asgi(), {'session_type': 'system'}),
]

# Register module WebSocket URLs
for module in plugin_registry.get_all_modules():
    websocket_urlpatterns += module.get_websocket_urls()
