from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        from .plugin_system import plugin_registry
        plugin_registry.discover_modules()
        try:
            plugin_registry.sync_tools_with_db()
        except:
            # Might fail during initial migrations
            pass
