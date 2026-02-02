from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/system/shell/$', consumers.TerminalConsumer.as_asgi(), {'session_type': 'system'}),
    re_path(r'ws/docker/shell/(?P<container_id>[\w.-]+)/$', consumers.TerminalConsumer.as_asgi(), {'session_type': 'docker'}),
    re_path(r'ws/k8s/shell/(?P<namespace>[\w-]+)/(?P<pod_name>[\w-]+)/$', consumers.TerminalConsumer.as_asgi(), {'session_type': 'k8s'}),
]
