# Creating a New Module

Modules in SolsticeOps are standalone Django applications located in the `modules/` directory. They are designed to be modular, often maintained as separate Git submodules.

## Module Structure

A complete module typically follows this structure:

```text
modules/my-module/
├── __init__.py
├── apps.py            # Optional: Standard Django AppConfig
├── module.py          # Required: Contains the Module class inheriting from BaseModule
├── views.py           # Optional: Module-specific view functions
├── models.py          # Optional: Module-specific database models
├── requirements.txt   # Required: Module-specific dependencies
├── templates/
│   └── core/
│       ├── modules/
│       │   └── my-module.html    # Main detail template
│       └── partials/
│           └── my_resource.html  # HTMX partials
└── static/            # Optional: Module-specific assets
```

## The Module Class

The heart of a module is the `Module` class in `module.py`. It must inherit from `core.plugin_system.BaseModule`.

### Basic Configuration

```python
from core.plugin_system import BaseModule

class Module(BaseModule):
    @property
    def module_id(self):
        return "my-module"  # Must match the directory name and Tool.name in DB

    @property
    def module_name(self):
        return "My Module"  # Human-readable name shown in UI

    description = "A brief description of what this module does."
    version = "1.0.0"
```

### UI Integration

#### 1. Detail View Context
Add custom data to the tool's detail page:
```python
def get_context_data(self, request, tool):
    return {
        'status_info': 'Running smoothly',
        'custom_metric': 42
    }
```

#### 2. Resource Tabs
Define tabs that appear on the detail page. These usually load content via HTMX:
```python
def get_resource_tabs(self):
    return [
        {
            'id': 'overview', 
            'label': 'Overview', 
            'template': 'core/modules/my_overview.html'
        },
        {
            'id': 'logs', 
            'label': 'Live Logs', 
            'hx_get': '/my-module/logs/', 
            'hx_auto_refresh': 'every 5s'
        },
    ]
```

#### 3. Icons and Templates
Override default paths if necessary:
```python
def get_icon_class(self):
    return "simpleicons-name"  # Uses Simple Icons

def get_custom_icon_svg(self):
    return '<svg ...>...</svg>'  # Optional: Custom SVG icon (takes precedence)

def get_template_name(self):
    return "core/modules/custom_detail.html"
```

### Dynamic Content (HTMX)

SolsticeOps heavily relies on HTMX for a smooth, "no-refresh" experience. You can handle HTMX requests directly in your module class:

```python
def handle_hx_request(self, request, tool, target):
    if target == 'status_update':
        context = {'status': 'updated'}
        return render(request, 'core/partials/status.html', context)
    return None
```

### URL Routing

Register custom URLs for your module:

```python
from django.urls import path
from . import views

def get_urls(self):
    return [
        path('my-module/action/', views.my_action, name='my_module_action'),
    ]
```

### Installation Logic

If your module requires a setup process (e.g., pulling a Docker image, configuring a service), implement the `install` method.

**Note:** If the `install` method is not implemented, the module is considered "out-of-the-box" and will be automatically marked as `installed` when discovered.

```python
import threading

def install(self, request, tool):
    tool.status = 'installing'
    tool.save()
    
    def run_setup():
        try:
            # Perform long-running tasks here
            tool.current_stage = "Downloading assets..."
            tool.save()
            # ...
            tool.status = 'installed'
        except Exception as e:
            tool.status = 'error'
            tool.config_data['error_log'] = str(e)
        tool.save()

    threading.Thread(target=run_setup).start()
```

### Terminal Integration

To provide an interactive terminal (like Docker exec or SSH), inherit from `TerminalSession` and register it:

```python
from core.terminal_manager import TerminalSession

class MySession(TerminalSession):
    def run(self):
        # Implementation of the terminal loop
        pass

def get_terminal_session_types(self):
    return {'my-session': MySession}
```

### System Commands and Sudo

If your module needs to run system commands that require root privileges, use the `run_sudo_command` utility. This utility automatically handles the `SUDO_PASSWORD` from the `.env` file, ensuring a seamless experience without interactive password prompts in the terminal.

```python
from core.utils import run_sudo_command

# Running a simple command
try:
    output = run_sudo_command(['apt-get', 'update'])
    print(output.decode())
except Exception as e:
    logger.error(f"Command failed: {e}")

# Running a command through shell (e.g., with pipes)
run_sudo_command("curl -fsSL https://example.com/install.sh | sh", shell=True)

# Providing input data to a command (e.g., fdisk)
input_data = "n\np\n\n\n+1G\nw\n"
run_sudo_command(['fdisk', '/dev/sdb'], input_data=input_data)
```

The utility will:
1. Use `sudo -S` if `SUDO_PASSWORD` is set in `.env`.
2. Fallback to `sudo -n` (non-interactive) if no password is set.

## Dependency Management

Each module **must** have its own `requirements.txt`. 
- Only include libraries specific to your module (e.g., `python-jenkins` for Jenkins).
- Do not include core dependencies (Django, DRF, etc.) unless your module requires a specific version.

## Registration

The core automatically discovers modules in the `modules/` directory if:
1. The directory contains an `__init__.py`.
2. The directory contains a `module.py` with a `Module` class.
3. The module is added to `INSTALLED_APPS` (the core does this automatically during discovery).

## Best Practices

1. **Isolation**: Keep module logic within the module directory. Avoid modifying files in `core/`.
2. **Submodules**: Use Git submodules for modules to keep the core repository clean.
3. **Templates**: Place templates in `templates/core/modules/` or `templates/core/partials/` to follow the project's layout.
4. **Error Handling**: Always wrap API calls in try-except blocks and provide feedback via `tool.config_data['error_log']`.
