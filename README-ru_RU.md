<div align="center">
    <picture>
        <source
            srcset="docs/images/logo_dark.png"
            media="(prefers-color-scheme: light), (prefers-color-scheme: no-preference)"
        />
        <source
            srcset="docs/images/logo_light.png"
            media="(prefers-color-scheme: dark)"
        />
        <img src="docs/images/logo_light.png" />
    </picture>
</div>

# SolsticeOps-core

SolsticeOps — это модульная панель управления DevOps.

[English Version](README.md)

## Скриншоты

[Dashboard](docs/images/dashboard/)
[Docker](docs/images/docker/)
[K8s](docs/images/k8s/)
[Jenkins](docs/images/jenkins/)
[Ollama](docs/images/ollama/)

## Архитектура
Это основной компонент, который обеспечивает:
- Аутентификацию пользователей
- Регистрацию и загрузку модулей
- Статистику сервера и дашборд
- Общее управление инструментами
- Управление сессиями терминала

## Документация
Подробная документация доступна в директории `docs/ru_RU/`.
- [Установка](docs/ru_RU/installation.md)
- [Создание модулей](docs/ru_RU/module_creation.md)
- [Справочник API](docs/ru_RU/api_reference.md)

## Зависимости
SolsticeOps использует модульный подход к зависимостям.
- Основные зависимости перечислены в корневом файле `requirements.txt`.
- Каждый модуль поддерживает свой собственный `requirements.txt` для специфической функциональности.
Это гарантирует, что вы устанавливаете только то, что действительно используете.

## Модули
SolsticeOps использует Git-субмодули для своих модулей. Доступные модули:
- [Docker](https://github.com/SolsticeOps/SolsticeOps-docker)
- [Kubernetes](https://github.com/SolsticeOps/SolsticeOps-k8s)
- [Jenkins](https://github.com/SolsticeOps/SolsticeOps-jenkins)
- [Ollama](https://github.com/SolsticeOps/SolsticeOps-ollama)
