import json
from channels.generic.websocket import WebsocketConsumer
from .terminal_manager import manager
from .plugin_system import plugin_registry

class TerminalConsumer(WebsocketConsumer):
    def connect(self):
        self.session_type = self.scope['url_route']['kwargs'].get('session_type', 'system')
        self.kwargs = self.scope['url_route']['kwargs'].copy()
        # Remove session_type from kwargs as it's not needed for session initialization
        self.kwargs.pop('session_type', None)
        
        if self.session_type == 'system':
            self.session_id = "system_shell"
        else:
            # Generate a unique session ID based on session type and all kwargs
            sorted_kwargs = sorted(self.kwargs.items())
            kwargs_str = "_".join([f"{k}_{v}" for k, v in sorted_kwargs])
            self.session_id = f"{self.session_type}_{kwargs_str}"

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
