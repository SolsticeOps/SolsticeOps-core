# Руководство по установке

SolsticeOps-core — это центральная система управления. Модули добавляются как Git-субмодули.

## Предварительные требования
- Python 3.12+
- Docker (опционально, но рекомендуется для некоторых модулей)
- Git

## Настройка

1. Клонируйте основной репозиторий:
   ```bash
   git clone https://github.com/SolsticeOps/SolsticeOps-core.git
   cd SolsticeOps-core
   ```

2. Создайте и активируйте виртуальное окружение:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Установите основные зависимости:
   ```bash
   pip install -r requirements.txt
   ```

4. Инициализируйте базу данных:
   ```bash
   python setup_db.py
   python manage.py migrate
   ```

5. Добавьте и инициализируйте модули:
   ```bash
   # Добавление нового субмодуля
   git submodule add {module_repo_url} modules/{module_name}
   
   # Или если вы только что клонировали ядро с существующими субмодулями:
   git submodule update --init --recursive

   # Установка зависимостей конкретного модуля
   pip install -r modules/{module_name}/requirements.txt
   ```

6. Запустите сервер (от имени `root`):
   ```bash
   sudo .venv/bin/python manage.py runserver
   ```
