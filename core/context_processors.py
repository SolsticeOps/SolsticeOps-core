from .models import Tool
from .plugin_system import plugin_registry

def tools_nav(request):
    if not request.user.is_authenticated:
        return {}
        
    plugin_registry.sync_tools_with_db()
    all_tools = Tool.objects.all()
    tools = []
    for tool in all_tools:
        module = plugin_registry.get_module(tool.name)
        if module:
            tool.module_version = getattr(module, 'version', '1.0.0')
            tool.service_version = module.get_service_version() or tool.version
            tool.actual_service_status = module.get_service_status(tool) if tool.status == 'installed' else 'stopped'
            tools.append(tool)
            
    return {
        'tools_nav': tools,
        'plugin_registry': plugin_registry
    }
