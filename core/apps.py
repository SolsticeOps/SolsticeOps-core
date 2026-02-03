from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        from .plugin_system import plugin_registry
        plugin_registry.discover_modules()
