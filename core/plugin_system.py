import logging
import importlib
import os
from abc import ABC, abstractmethod
from django.conf import settings

logger = logging.getLogger(__name__)

class BaseModule(ABC):
    """Abstract base class for all SolsticeOps modules."""
    
    @property
    @abstractmethod
    def module_id(self):
        """Unique identifier for the module."""
        pass

    @property
    @abstractmethod
    def module_name(self):
        """Human-readable name of the module."""
        pass

    description = ""
    version = "1.0.0"

    def get_service_version(self):
        """Return the version of the actual service (e.g., '0.15.4' for Ollama)."""
        return None

    def get_urls(self):
        """Return a list of URL patterns for this module."""
        return []

    def get_websocket_urls(self):
        """Return a list of WebSocket URL patterns for this module."""
        return []

    def get_icon_class(self):
        """Return the Simple Icons class name for this module."""
        return self.module_id

    def get_custom_icon_svg(self):
        """Return a custom SVG icon for this module as a string."""
        return None

    def get_template_name(self):
        """Return the template name for the tool detail view."""
        return f"core/modules/{self.module_id}.html"

    def get_install_template_name(self):
        """Return the template name for the installation view."""
        return None

    def get_logs_url(self, tool):
        """Return the URL for fetching service logs."""
        return None

    def get_extra_actions_template_name(self):
        """Return the template name for extra actions in tool detail."""
        return None

    def get_extra_content_template_name(self):
        """Return the template name for extra content (like modals) in tool detail."""
        return None

    def get_resource_header_template_name(self):
        """Return the template name for the resource section header."""
        return None

    def get_resource_tabs(self):
        """Return a list of resource tabs: [{'id': '...', 'label': '...', 'template': '...', 'hx_get': '...', 'hx_auto_refresh': '...'}]"""
        return []

    def get_context_data(self, request, tool):
        """Return additional context data for the tool detail view."""
        return {}

    def handle_hx_request(self, request, tool, target):
        """Handle HTMX requests for this module."""
        return None

    def install(self, request, tool):
        """Handle tool installation."""
        pass

    def get_terminal_session_types(self):
        """Return a dictionary of terminal session types {name: class}."""
        return {}

class ModuleRegistry:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModuleRegistry, cls).__new__(cls)
            cls._instance.modules = {}
        return cls._instance

    def register(self, module_class):
        module = module_class()
        self.modules[module.module_id] = module
        logger.info(f"Registered module: {module.module_id}")

    def get_module(self, module_id):
        return self.modules.get(module_id)

    def get_all_modules(self):
        return self.modules.values()

    def discover_modules(self):
        """Discover modules in the 'modules' directory."""
        modules_dir = os.path.join(settings.BASE_DIR, 'modules')
        if not os.path.exists(modules_dir):
            os.makedirs(modules_dir)
            return

        for item in os.listdir(modules_dir):
            item_path = os.path.join(modules_dir, item)
            if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, '__init__.py')):
                try:
                    # Try to import 'module' from the package
                    module_pkg = importlib.import_module(f'modules.{item}.module')
                    if hasattr(module_pkg, 'Module'):
                        self.register(module_pkg.Module)
                except Exception as e:
                    logger.error(f"Failed to load module {item}: {e}")

    def sync_tools_with_db(self):
        """Ensure all discovered modules have a corresponding Tool record in the DB."""
        from .models import Tool
        for module in self.get_all_modules():
            try:
                Tool.objects.get_or_create(
                    name=module.module_id,
                    defaults={
                        'status': 'not_installed',
                        'version': getattr(module, 'version', '1.0.0')
                    }
                )
            except Exception as e:
                logger.debug(f"Could not sync module {module.module_id} with DB: {e}")

plugin_registry = ModuleRegistry()
