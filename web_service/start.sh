#!/bin/bash

# Скрипт для запуска web-сервиса

echo "🚀 Запуск GigaChat RAG Web Service..."

# Проверяем наличие виртуального окружения
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активируем виртуальное окружение
echo "🔧 Активация виртуального окружения..."
source venv/bin/activate

# Устанавливаем зависимости
echo "📥 Установка зависимостей..."
pip install -r requirements.txt

# Проверяем наличие .env файла
if [ ! -f ".env" ]; then
    echo "⚠️  Файл .env не найден. Копируем из примера..."
    cp .env.example .env
    echo "📝 Отредактируйте файл .env перед запуском!"
    exit 1
fi

# Создаем необходимые директории
echo "📁 Создание директорий..."
mkdir -p storage/chroma_db
mkdir -p storage/uploads

# Проверяем сертификаты
if [ ! -f "../certificates/cert.pem" ] || [ ! -f "../certificates/key.pem" ]; then
    echo "⚠️  Сертификаты GigaChat не найдены в ../certificates/"
    echo "   GigaChat будет недоступен до добавления сертификатов"
fi

# Запускаем сервис
echo "🌟 Запуск веб-сервиса..."
echo "   Сервис будет доступен по адресу: http://localhost:8005"
echo "   Для остановки нажмите Ctrl+C"
echo ""

python main.py
