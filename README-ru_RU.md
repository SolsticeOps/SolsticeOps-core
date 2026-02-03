# SolsticeOps-core

SolsticeOps — это модульная панель управления DevOps.

[English Version](README.md)

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
