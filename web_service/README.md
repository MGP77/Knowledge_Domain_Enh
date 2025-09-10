# 🚀 SberInfra Knowledge Management System

Веб-сервис на базе FastAPI с интеграцией GigaChat и RAG базой знаний с российскими эмбеддингами.

## ✨ Новые возможности (v2.0)

### 🎨 SberInfra Брендинг
- **Зелёный логотип SberInfra** на всех страницах
- Корпоративный дизайн в стиле SberInfra
- Современный SVG логотип с градиентом

### 🔗 Расширенная поддержка Confluence
- **Прямые ссылки**: Вставляйте URL страниц вместо поиска ID
- **Многоуровневый парсинг**: От 1 до 5 уровней вложенности  
- **Умная обработка**: Автоматическое извлечение ID из любых URL форматов
- **Гибкая конфигурация**: Комбинирование Space + URL + Page IDs

## 🛠️ Основные возможности

- 💬 Чат с GigaChat с поддержкой markdown
- 🇷🇺 **RAG база знаний с GigaChat эмбеддингами**
- 🌐 **Продвинутый парсинг Confluence** с поддержкой URL и уровней
- 📁 Загрузка и обработка PDF, DOCX, TXT файлов
- ⚙️ Админ панель для управления данными
- 🔐 mTLS аутентификация для GigaChat

## 🇷🇺 GigaChat Эмбеддинги

### Поддерживаемые модели:
- **Embeddings**: Базовая модель (512 измерений)
- **EmbeddingsGigaR**: Расширенная модель (до 4096 измерений) ⭐ Рекомендуется

### Преимущества:
- **Автоматические инструкции**: Оптимизация запросов для лучшего поиска
- **Русская локализация**: Оптимизированы для русскоязычных текстов
- **Полная независимость**: Российская технологическая экосистема

## 📋 Требования

- Python 3.8+
- **Обязательно**: Сертификаты для GigaChat (cert.pem, key.pem)
- langchain-gigachat 0.3.12+

## 🚀 Установка

1. Клонируйте репозиторий и перейдите в папку web_service:
```bash
cd web_service
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройте переменные окружения:
```bash
cp .env.example .env
```

4. Отредактируйте .env файл:
```bash
# GigaChat Embeddings
GIGACHAT_EMBEDDING_MODEL=EmbeddingsGigaR

# mTLS сертификаты
MTLS_CLIENT_CERT=../certificates/cert.pem
MTLS_CLIENT_KEY=../certificates/key.pem
```

5. Убедитесь, что сертификаты GigaChat находятся в папке `../certificates/`:
- cert.pem (ваш клиентский сертификат)
- key.pem (ваш приватный ключ)

## 🏃 Запуск

```bash
python main.py
```

Или с помощью uvicorn:
```bash
uvicorn main:app --host 0.0.0.0 --port 8005 --reload
```

Сервис будет доступен по адресу: http://localhost:8005

## Использование

### Чат с GigaChat
1. Откройте главную страницу
2. Включите/выключите использование базы знаний
3. Задавайте вопросы в чате

### Админ панель
1. Перейдите на вкладку "Админ панель"
2. **Confluence**: Настройте подключение и парсите страницы
3. **Файлы**: Загружайте PDF, DOCX, TXT документы
4. **База данных**: Просматривайте статистику и управляйте данными

### 🔗 Новые возможности Confluence

#### Прямые ссылки на страницы
```
https://company.atlassian.net/wiki/pages/viewpage.action?pageId=123456
https://company.atlassian.net/wiki/spaces/PROJ/pages/789012/Page+Title  
https://company.atlassian.net/wiki/display/PROJ/Page+Name
```

#### Многоуровневый парсинг
- **1 уровень**: Только указанные страницы
- **2-5 уровней**: Автоматический поиск дочерних страниц
- **Умная обработка**: Исключение дубликатов

#### Гибкая конфигурация
- Комбинирование Space Key + URL + Page IDs
- Настройка глубины парсинга
- Rate limiting для защиты от блокировки API

## Конфигурация

### GigaChat Certificates
Получите mTLS сертификаты через корпоративные каналы Сбербанка

### Confluence (расширенные настройки)
- **URL**: `https://company.atlassian.net/wiki`
- **Аутентификация**: Email + API Token (Basic Auth)
- **Space Key**: `PROJ` - для парсинга всего пространства
- **Page IDs**: `123456,789012` - конкретные страницы через запятую
- **Прямые URL**: Список ссылок (по одной на строку)
- **Уровни парсинга**: 1-5 уровней вложенности

### GigaChat
- Поместите сертификаты в папку `certificates/`
- cert.pem - клиентский сертификат
- key.pem - приватный ключ

## Структура проекта

```
web_service/
├── main.py                 # Главное FastAPI приложение
├── config.py              # Конфигурация
├── requirements.txt       # Зависимости
├── .env.example          # Пример переменных окружения
├── app/
│   ├── services/         # Бизнес-логика
│   │   ├── gigachat_service.py    # Сервис GigaChat
│   │   ├── rag_service.py         # Сервис RAG/Chroma
│   │   ├── confluence_service.py  # Сервис Confluence
│   │   └── file_service.py        # Сервис файлов
│   ├── models/
│   │   └── schemas.py     # Pydantic модели
│   ├── templates/         # HTML шаблоны
│   │   ├── base.html
│   │   ├── index.html     # Главная страница
│   │   └── admin.html     # Админ панель
│   └── static/           # Статические файлы
└── storage/              # Хранилище данных
    ├── chroma_db/        # Chroma база данных
    └── uploads/          # Загруженные файлы
```

## API Endpoints

- `GET /` - Главная страница с чатом
- `GET /admin` - Админ панель  
- `POST /api/chat` - Чат с GigaChat
- `POST /api/confluence/test` - Тест подключения к Confluence
- `POST /api/confluence/parse` - Парсинг Confluence
- `POST /api/upload` - Загрузка файлов
- `GET /api/admin/stats` - Статистика
- `DELETE /api/admin/clear-db` - Очистка базы данных
- `GET /api/health` - Проверка состояния сервисов

## Troubleshooting

### GigaChat недоступен
- Проверьте наличие сертификатов в папке `certificates/`
- Убедитесь, что сертификаты валидны и не являются заглушками
- Проверьте сетевое подключение к GigaChat API

### RAG база недоступна
- Убедитесь, что сертификаты GigaChat настроены корректно
- Проверьте доступность GigaChat Embeddings API
- Убедитесь, что папка `storage/chroma_db` доступна для записи

### Ошибки парсинга Confluence
- Проверьте URL (должен заканчиваться на `/wiki`)
- Убедитесь в правильности логина и пароля/API токена
- Проверьте права доступа к пространству или страницам

### Ошибки загрузки файлов
- Убедитесь, что папка `storage/uploads` доступна для записи
- Проверьте размер файла (максимум 50MB)
- Убедитесь, что файл имеет поддерживаемый формат

## Лицензия

Copyright (c) 2025. All rights reserved.
