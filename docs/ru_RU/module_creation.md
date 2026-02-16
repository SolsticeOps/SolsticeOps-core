# Создание нового модуля

Модули в SolsticeOps — это автономные приложения Django, расположенные в директории `modules/`. Они спроектированы как модульные компоненты, часто поддерживаемые как отдельные Git-субмодули.

## Структура модуля

Типичный модуль имеет следующую структуру:

```text
modules/my-module/
├── __init__.py
├── apps.py            # Опционально: стандартный AppConfig Django
├── module.py          # Обязательно: класс Module, наследующий BaseModule
├── views.py           # Опционально: специфичные для модуля представления
├── models.py          # Опционально: специфичные для модуля модели БД
├── requirements.txt   # Обязательно: специфичные для модуля зависимости
├── templates/
│   └── core/
│       ├── modules/
│       │   └── my-module.html    # Основной шаблон деталей
│       └── partials/
│           └── my_resource.html  # HTMX-фрагменты
└── static/            # Опционально: статические файлы модуля
```

## Класс Module

Сердцем модуля является класс `Module` в файле `module.py`. Он должен наследоваться от `core.plugin_system.BaseModule`.

### Базовая конфигурация

```python
from core.plugin_system import BaseModule

class Module(BaseModule):
    @property
    def module_id(self):
        return "my-module"  # Должен совпадать с именем директории и Tool.name в БД

    @property
    def module_name(self):
        return "My Module"  # Человекочитаемое имя, отображаемое в UI

    description = "Краткое описание того, что делает этот модуль."
    version = "1.0.0"
```

### Интеграция с UI

#### 1. Контекст детального представления
Добавьте пользовательские данные на страницу деталей инструмента:
```python
def get_context_data(self, request, tool):
    return {
        'status_info': 'Работает стабильно',
        'custom_metric': 42
    }
```

#### 2. Статус сервиса и действия
SolsticeOps предоставляет стандартизированный способ отслеживания состояния сервиса и выполнения действий жизненного цикла (Запуск, Остановка, Перезапуск).

**Отслеживание статуса:**
Реализуйте `get_service_status`, чтобы возвращать текущее рабочее состояние.
```python
def get_service_status(self, tool):
    # Должен возвращать 'running', 'stopped' или 'error'
    try:
        from core.utils import run_command
        # Используйте log_errors=False, чтобы не засорять логи при остановленном сервисе
        status_process = run_command(["systemctl", "is-active", "my-service"], log_errors=False)
        return 'running' if status_process.decode().strip() == "active" else 'stopped'
    except:
        return 'stopped' # По умолчанию остановлен, если команда не удалась
```

**Действия жизненного цикла:**
Реализуйте эти методы для обработки нажатий кнопок в интерфейсе. Если они не реализованы, ядро по умолчанию выполняет `systemctl <action> <module_id>`.
```python
def service_start(self, tool):
    run_command(["systemctl", "start", "my-service"])

def service_stop(self, tool):
    run_command(["systemctl", "stop", "my-service"])

def service_restart(self, tool):
    run_command(["systemctl", "restart", "my-service"])
```

#### 3. Вкладки ресурсов
Определите вкладки, которые появятся на странице деталей. Обычно они загружают контент через HTMX:
```python
def get_resource_tabs(self):
    return [
        {
            'id': 'overview', 
            'label': 'Обзор', 
            'template': 'core/modules/my_overview.html'
        },
        {
            'id': 'logs', 
            'label': 'Логи в реальном времени', 
            'hx_get': '/my-module/logs/', 
            'hx_auto_refresh': 'every 5s'
        },
    ]
```

#### 3. Иконки и шаблоны
Переопределите пути по умолчанию, если это необходимо:
```python
def get_icon_class(self):
    return "simpleicons-name"  # Использует Simple Icons

def get_custom_icon_svg(self):
    return '<svg ...>...</svg>'  # Опционально: кастомная SVG иконка (имеет приоритет)

def get_template_name(self):
    return "core/modules/custom_detail.html"
```

### Динамический контент (HTMX)

SolsticeOps активно использует HTMX для обеспечения плавного взаимодействия без перезагрузки страниц. Вы можете обрабатывать HTMX-запросы прямо в классе модуля:

```python
def handle_hx_request(self, request, tool, target):
    if target == 'status_update':
        context = {'status': 'updated'}
        return render(request, 'core/partials/status.html', context)
    return None
```

### Маршрутизация URL

Зарегистрируйте пользовательские URL для вашего модуля:

```python
from django.urls import path
from . import views

def get_urls(self):
    return [
        path('my-module/action/', views.my_action, name='my_module_action'),
    ]
```

### Логика установки

Если вашему модулю требуется процесс настройки (например, загрузка образа Docker, настройка сервиса), реализуйте метод `install`.

**Примечание:** Если метод `install` не реализован, модуль считается установленным «из коробки» и будет автоматически помечен как `installed` при обнаружении.

```python
import threading

def install(self, request, tool):
    tool.status = 'installing'
    tool.save()
    
    def run_setup():
        try:
            # Выполнение длительных задач здесь
            tool.current_stage = "Загрузка ресурсов..."
            tool.save()
            # ...
            tool.status = 'installed'
        except Exception as e:
            tool.status = 'error'
            tool.config_data['error_log'] = str(e)
        tool.save()

    threading.Thread(target=run_setup).start()
```

### Интеграция терминала

Чтобы предоставить интерактивный терминал (например, Docker exec или SSH), наследуйтесь от `TerminalSession` и зарегистрируйте его:

```python
from core.terminal_manager import TerminalSession

class MySession(TerminalSession):
    def run(self):
        # Реализация цикла терминала
        pass

def get_terminal_session_types(self):
    return {'my-session': MySession}
```

### Системные команды

Если вашему модулю необходимо выполнять системные команды, используйте утилиту `run_command`. 

**Важно:** Приложение SolsticeOps должно запускаться от имени пользователя **root**. Утилита `run_command` выполняет команды напрямую в системе с правами root.

```python
from core.utils import run_command

# Выполнение простой команды
try:
    output = run_command(['apt-get', 'update'])
    print(output.decode())
except Exception as e:
    logger.error(f"Команда не удалась: {e}")

# Выполнение команды через shell (например, с пайпами)
run_command("curl -fsSL https://example.com/install.sh | sh", shell=True)

# Передача входных данных в команду (например, для fdisk)
input_data = "n\np\n\n\n+1G\nw\n"
run_command(['fdisk', '/dev/sdb'], input_data=input_data)
```

### Интеграция с Docker

Если ваш модуль взаимодействует с Docker, вы можете использовать встроенную обертку `DockerCLI`, предоставляемую ядром. Она использует команды на основе `sudo` для управления контейнерами, образами, томами и сетями.

```python
from core.docker_cli_wrapper import DockerCLI

client = DockerCLI()

# Список контейнеров
containers = client.containers.list(all=True)

# Запуск контейнера
container = client.containers.get('my-container')
if container:
    container.start()

# Загрузка образа
client.images.pull('nginx', tag='latest')

# Запуск нового контейнера
client.containers.run(
    'nginx:latest',
    name='my-nginx',
    ports={'80/tcp': '8080'},
    detach=True
)
```

### Интеграция с Kubernetes

Аналогично Docker, вы можете использовать обертку `K8sCLI` для взаимодействия с кластером Kubernetes, которая использует `kubectl` внутри.

```python
from core.k8s_cli_wrapper import K8sCLI

k8s = K8sCLI()

# Список подов во всех пространствах имен
pods = k8s.pods.list(all_namespaces=True)

# Список развертываний в конкретном пространстве имен
deployments = k8s.deployments.list(namespace='default')

# Масштабирование развертывания
k8s.deployments.scale('my-deployment', replicas=3, namespace='default')

# Перезапуск развертывания (rollout restart)
k8s.deployments.restart('my-deployment', namespace='default')

# Получение текущего контекста
context = k8s.get_context()
```

#### Статус и действия для Docker-контейнеров
Если ваш модуль основан на Docker-контейнере, вам следует переопределить методы сервиса для использования `DockerCLI` вместо `systemctl`.

```python
from core.docker_cli_wrapper import DockerCLI

def get_service_status(self, tool):
    try:
        client = DockerCLI()
        container = client.containers.get(tool.config_data.get('container_name'))
        if container:
            return 'running' if container.status == 'running' else 'stopped'
        return 'stopped'
    except:
        return 'stopped'

def service_start(self, tool):
    client = DockerCLI()
    container = client.containers.get(tool.config_data.get('container_name'))
    if container:
        container.start()

def service_stop(self, tool):
    client = DockerCLI()
    container = client.containers.get(tool.config_data.get('container_name'))
    if container:
        container.stop()

def service_restart(self, tool):
    client = DockerCLI()
    container = client.containers.get(tool.config_data.get('container_name'))
    if container:
        container.restart()
```

## Управление зависимостями

Каждый модуль **должен** иметь свой собственный файл `requirements.txt`.
- Включайте только библиотеки, специфичные для вашего модуля (например, `python-jenkins` для Jenkins).
- Не включайте основные зависимости ядра (Django, DRF и т.д.), если вашему модулю не требуется конкретная версия.

## Регистрация

Ядро автоматически обнаруживает модули в директории `modules/`, если:
1. Директория содержит `__init__.py`.
2. Директория содержит `module.py` с классом `Module`.
3. Модуль добавлен в `INSTALLED_APPS` (ядро делает это автоматически во время обнаружения).

## Лучшие практики

1. **Изоляция**: Держите логику модуля внутри его директории. Избегайте изменения файлов в `core/`.
2. **Субмодули**: Используйте Git-субмодули для модулей, чтобы держать репозиторий ядра чистым.
3. **Шаблоны**: Размещайте шаблоны в `templates/core/modules/` или `templates/core/partials/`, следуя структуре проекта.
4. **Обработка ошибок**: Всегда оборачивайте вызовы API в блоки try-except и предоставляйте обратную связь через `tool.config_data['error_log']`.
