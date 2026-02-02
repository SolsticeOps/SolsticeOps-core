# Creating a New Module

Modules in SolsticeOps are standalone packages located in the `modules/` directory.

## Module Structure
A typical module should have the following structure:
```
modules/my-module/
├── __init__.py
├── module.py      # Contains the Module class inheriting from BaseModule
├── views.py       # (Optional) Module-specific views
└── templates/     # (Optional) Module-specific templates
```

## The Module Class
In `module.py`, you must define a `Module` class that inherits from `core.plugin_system.BaseModule`.

```python
from core.plugin_system import BaseModule

class Module(BaseModule):
    module_id = "my-module"
    module_name = "My Module"
    description = "Description of my module"

    def get_context_data(self, request, tool):
        # Return data to be added to tool_detail context
        return {'my_data': 'hello'}

    def handle_hx_request(self, request, tool, target):
        # Handle HTMX requests
        if target == 'my-tab':
            return render(request, 'my_template.html', {'tool': tool})
        return None
```

## Registration
The core automatically discovers modules that have a `module.py` with a `Module` class.
Ensure your module directory is in `modules/` and has an `__init__.py`.
