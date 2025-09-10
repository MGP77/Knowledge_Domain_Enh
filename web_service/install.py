#!/usr/bin/env python3
"""
Скрипт установки и настройки web-сервиса

Copyright (c) 2025. All rights reserved.
Author: M.P.
"""

import os
import sys
import subprocess

def run_command(command, description):
    """Выполнение команды с выводом"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - завершено")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - ошибка: {e}")
        print(f"   Вывод: {e.stdout}")
        print(f"   Ошибки: {e.stderr}")
        return False

def create_directories():
    """Создание необходимых директорий"""
    print("📁 Создание директорий...")
    
    directories = [
        "storage",
        "storage/chroma_db",
        "storage/uploads",
        "app/templates",
        "app/static"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ {directory}")

def setup_environment():
    """Настройка окружения"""
    print("🌍 Настройка окружения...")
    
    # Проверяем Python версию
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8 или выше")
        return False
    
    print(f"✅ Python {sys.version}")
    
    # Создаем .env файл если не существует
    if not os.path.exists('.env'):
        print("📝 Создание .env файла...")
        with open('.env.example', 'r') as src, open('.env', 'w') as dst:
            dst.write(src.read())
        print("✅ .env файл создан из примера")
        print("⚠️  ВАЖНО: Отредактируйте .env файл")
    
    return True

def install_dependencies():
    """Установка зависимостей"""
    print("📦 Установка зависимостей...")
    
    # Обновляем pip
    if not run_command("python -m pip install --upgrade pip", "Обновление pip"):
        return False
    
    # Устанавливаем основные зависимости
    if not run_command("pip install -r requirements.txt", "Установка зависимостей"):
        print("⚠️  Пробуем установить по одной...")
        
        # Пробуем установить критически важные пакеты
        critical_packages = [
            "fastapi",
            "uvicorn[standard]",
            "jinja2",
            "python-multipart",
            "requests",
            "python-dotenv",
            "pydantic"
        ]
        
        for package in critical_packages:
            run_command(f"pip install {package}", f"Установка {package}")
    
    return True

def check_optional_dependencies():
    """Проверка опциональных зависимостей"""
    print("🔍 Проверка опциональных зависимостей...")
    
    optional_deps = {
        "chromadb": "Chroma векторная база данных", 
        "PyPDF2": "Обработка PDF файлов",
        "python-docx": "Обработка DOCX файлов",
        "beautifulsoup4": "Парсинг HTML",
        "python-magic": "Определение типов файлов",
        "langchain-gigachat": "GigaChat эмбеддинги"
    }
    
    for package, description in optional_deps.items():
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} - {description}")
        except ImportError:
            print(f"⚠️  {package} - {description} - НЕ УСТАНОВЛЕН")
            run_command(f"pip install {package}", f"Установка {package}")

def main():
    """Главная функция установки"""
    print("🚀 Установка и настройка GigaChat RAG Web Service\n")
    
    # Создаем директории
    create_directories()
    
    # Настраиваем окружение
    if not setup_environment():
        return
    
    # Устанавливаем зависимости
    if not install_dependencies():
        print("❌ Критические ошибки установки зависимостей")
        return
    
    # Проверяем опциональные зависимости
    check_optional_dependencies()
    
    print("\n✅ Установка завершена!")
    print("\n📝 Следующие шаги:")
    print("1. Отредактируйте файл .env (настройте GigaChat)")
    print("2. Добавьте сертификаты GigaChat в ../certificates/")
    print("3. Запустите тестирование: python test_setup.py")
    print("4. Запустите сервис: python main.py")
    print("5. Откройте в браузере: http://localhost:8005")

if __name__ == "__main__":
    main()
