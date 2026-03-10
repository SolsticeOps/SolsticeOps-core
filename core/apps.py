from django.apps import AppConfig
import os
import threading
import time
import logging

logger = logging.getLogger(__name__)

def background_worker():
    """Background worker to poll tools and update cache."""
    from .models import Tool
    from .plugin_system import plugin_registry
    from django import db
    
    # Wait a bit for the server to start
    time.sleep(5)
    
    while True:
        try:
            # Refresh DB connection for this thread
            db.connections.close_all()
            
            tools = list(Tool.objects.all())
            for tool in tools:
                module = plugin_registry.get_module(tool.name)
                if module and tool.status == 'installed':
                    try:
                        logger.debug(f"Background polling for tool: {tool.name}")
                        module.background_poll(tool)
                    except Exception as e:
                        logger.error(f"Error polling tool {tool.name}: {e}")
            
            # Global HW stats polling
            from .views import get_server_stats
            from django.core.cache import cache
            stats = get_server_stats()
            cache.set('bg_server_stats', stats, 30)
            
        except Exception as e:
            logger.error(f"Background worker error: {e}")
        
        # Poll every 15 seconds
        time.sleep(15)

class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        from .plugin_system import plugin_registry
        plugin_registry.discover_modules()
        
        # Start background worker only if not in reloader and not in management command
        # or if specifically enabled
        if os.environ.get('RUN_MAIN') == 'true' or not os.environ.get('DJANGO_SETTINGS_MODULE'):
            return

        # Avoid starting multiple threads in daphne/gunicorn if possible
        # In this project, daphne is used, which is usually single process
        # But we check for RUN_MAIN to handle runserver
        
        # To ensure it only runs once even in production, we could use a lock or a specific process
        # For now, a simple thread in ready() is a good start as requested
        if not any(arg in __import__('sys').argv for arg in ['migrate', 'makemigrations', 'collectstatic', 'shell', 'test']):
            threading.Thread(target=background_worker, daemon=True, name="SolsticeOpsBackgroundWorker").start()
            logger.info("Started background worker thread")
