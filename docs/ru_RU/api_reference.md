# Справочник API

## core.plugin_system.BaseModule

Базовый класс для всех модулей.

### Свойства (Абстрактные)
- `module_id`: Уникальный идентификатор модуля (должен совпадать с `Tool.name`).
- `module_name`: Человекочитаемое имя.

### Атрибуты
- `description`: Краткое описание модуля.
- `version`: Версия модуля.

### Методы
- `get_urls()`: Возвращает список паттернов URL Django.
- `get_context_data(request, tool)`: Возвращает словарь данных контекста для детального представления инструмента.
- `handle_hx_request(request, tool, target)`: Обрабатывает HTMX-запросы. Возвращает `HttpResponse`.
- `install(request, tool)`: Логика установки инструмента.
- `get_terminal_session_types()`: Возвращает словарь `{name: session_class}`.

## core.terminal_manager.TerminalSession

Базовый класс для сессий терминала.

### Методы
- `add_history(data)`: Добавить данные в историю и отправить потребителям.
- `send_input(data)`: Отправить ввод в процесс терминала.
- `resize(rows, cols)`: Изменить размер терминала.
- `run()`: Основной цикл чтения из терминала.

## core.plugin_system.ModuleRegistry

Синглтон-реестр для модулей.

### Методы
- `register(module_class)`: Зарегистрировать модуль.
- `get_module(module_id)`: Получить модуль по ID.
- `discover_modules()`: Автоматически находить модули в директории `modules/`.
