# API Reference

## core.plugin_system.BaseModule

Base class for all modules.

### Properties (Abstract)
- `module_id`: Unique identifier for the module (matches `Tool.name`).
- `module_name`: Human-readable name.

### Attributes
- `description`: Short description of the module.
- `version`: Module version.

### Methods
- `get_urls()`: Returns a list of Django URL patterns.
- `get_context_data(request, tool)`: Returns a dictionary of context data for the tool detail view.
- `handle_hx_request(request, tool, target)`: Handles HTMX requests. Returns an `HttpResponse`.
- `install(request, tool)`: Logic for installing the tool.
- `get_terminal_session_types()`: Returns a dict of `{name: session_class}`.

## core.terminal_manager.TerminalSession

Base class for terminal sessions.

### Methods
- `add_history(data)`: Add data to history and send to consumers.
- `send_input(data)`: Send input to the terminal process.
- `resize(rows, cols)`: Resize the terminal.
- `run()`: The main loop for reading from the terminal.

## core.plugin_system.ModuleRegistry

Singleton registry for modules.

### Methods
- `register(module_class)`: Register a module.
- `get_module(module_id)`: Get a module by ID.
- `discover_modules()`: Automatically find modules in the `modules/` directory.
