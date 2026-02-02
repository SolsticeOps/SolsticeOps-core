import json
from channels.generic.websocket import WebsocketConsumer
from .terminal_manager import manager

class TerminalConsumer(WebsocketConsumer):
    def connect(self):
        self.session_type = self.scope['url_route']['kwargs'].get('session_type', 'system')
        
        if self.session_type == 'docker':
            container_id = self.scope['url_route']['kwargs']['container_id']
            self.session_id = f"docker_{container_id}"
            self.kwargs = {'container_id': container_id}
        elif self.session_type == 'k8s':
            namespace = self.scope['url_route']['kwargs']['namespace']
            pod_name = self.scope['url_route']['kwargs']['pod_name']
            self.session_id = f"k8s_{namespace}_{pod_name}"
            self.kwargs = {'namespace': namespace, 'pod_name': pod_name}
        else:
            self.session_id = "system_shell"
            self.kwargs = {}

        self.accept()
        self.session = manager.get_session(self.session_id, self.session_type, **self.kwargs)
        if self.session:
            self.session.register_consumer(self)
        else:
            self.close()

    def receive(self, text_data=None, bytes_data=None):
        if text_data:
            try:
                data = json.loads(text_data)
                if 'input' in data:
                    self.session.send_input(data['input'])
                elif 'resize' in data:
                    self.session.resize(data['resize']['rows'], data['resize']['cols'])
                elif 'restart' in data:
                    manager.restart_session(self.session_id)
                elif 'heartbeat' in data:
                    pass
            except:
                pass

    def disconnect(self, close_code):
        if hasattr(self, 'session'):
            self.session.unregister_consumer(self)
