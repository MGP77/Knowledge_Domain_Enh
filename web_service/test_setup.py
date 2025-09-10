#!/usr/bin/env python3
"""
Тестовый скрипт для проверки компонентов web-сервиса

Copyright (c) 2025. All rights reserved.
Author: M.P.
"""

import os
import sys
import asyncio
import logging

# Добавляем текущую директорию в path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Тестирование импортов"""
    print("🧪 Тестирование импортов...")
    
    try:
        from config import config
        print("✅ config - OK")
    except Exception as e:
        print(f"❌ config - FAIL: {e}")
        return False
    
    try:
        from app.services.gigachat_service import GigaChatService
        print("✅ GigaChatService - OK")
    except Exception as e:
        print(f"❌ GigaChatService - FAIL: {e}")
        return False
    
    try:
        from app.services.rag_service import RAGService
        print("✅ RAGService - OK")
    except Exception as e:
        print(f"❌ RAGService - FAIL: {e}")
        return False
    
    try:
        from app.services.confluence_service import ConfluenceService
        print("✅ ConfluenceService - OK")
    except Exception as e:
        print(f"❌ ConfluenceService - FAIL: {e}")
        return False
    
    try:
        from app.services.file_service import FileProcessorService
        print("✅ FileProcessorService - OK")
    except Exception as e:
        print(f"❌ FileProcessorService - FAIL: {e}")
        return False
    
    return True

def test_config():
    """Тестирование конфигурации"""
    print("\n📋 Тестирование конфигурации...")
    
    from config import config
    
    print(f"App Name: {config.APP_NAME}")
    print(f"Host: {config.HOST}:{config.PORT}")
    print(f"GigaChat URL: {config.GIGACHAT_BASE_URL}")
    print(f"Cert Path: {config.MTLS_CLIENT_CERT}")
    print(f"Key Path: {config.MTLS_CLIENT_KEY}")
    print(f"GigaChat Embedding Model: {config.GIGACHAT_EMBEDDING_MODEL}")
    print(f"Chroma DB: {config.CHROMA_DB_PATH}")

def test_services():
    """Тестирование сервисов"""
    print("\n🔧 Тестирование сервисов...")
    
    from app.services.gigachat_service import GigaChatService
    from app.services.rag_service import RAGService
    from app.services.confluence_service import ConfluenceService
    from app.services.file_service import FileProcessorService
    
    # GigaChat
    gigachat = GigaChatService()
    print(f"GigaChat доступен: {gigachat.check_availability()}")
    
    # RAG
    rag = RAGService()
    print(f"RAG доступен: {rag.check_availability()}")
    
    # Confluence
    confluence = ConfluenceService()
    print("Confluence сервис создан")
    
    # File processor
    file_processor = FileProcessorService()
    print("File processor сервис создан")
    
    return gigachat, rag, confluence, file_processor

async def test_basic_functionality():
    """Тестирование базовой функциональности"""
    print("\n⚡ Тестирование базовой функциональности...")
    
    gigachat, rag, confluence, file_processor = test_services()
    
    # Тест RAG статистики
    if rag.check_availability():
        stats = rag.get_stats()
        print(f"RAG статистика: {stats}")
    
    # Тест GigaChat (только если доступен)
    if gigachat.check_availability():
        print("Тестирование GigaChat...")
        try:
            response = await gigachat.simple_chat("Привет!")
            print(f"GigaChat ответ: {response[:100]}...")
        except Exception as e:
            print(f"Ошибка GigaChat: {e}")

def test_directories():
    """Проверка необходимых директорий"""
    print("\n📁 Проверка директорий...")
    
    directories = [
        "storage",
        "storage/chroma_db", 
        "storage/uploads",
        "app/templates",
        "app/static"
    ]
    
    for dir_path in directories:
        if os.path.exists(dir_path):
            print(f"✅ {dir_path} - существует")
        else:
            print(f"❌ {dir_path} - не существует")
            os.makedirs(dir_path, exist_ok=True)
            print(f"📁 {dir_path} - создан")

def test_certificates():
    """Проверка сертификатов"""
    print("\n🔐 Проверка сертификатов...")
    
    cert_files = [
        "../certificates/cert.pem",
        "../certificates/key.pem"
    ]
    
    for cert_file in cert_files:
        if os.path.exists(cert_file):
            print(f"✅ {cert_file} - найден")
            # Проверяем содержимое
            with open(cert_file, 'r') as f:
                content = f.read()
                if "Placeholder" in content:
                    print(f"⚠️  {cert_file} - файл-заглушка")
                else:
                    print(f"✅ {cert_file} - валидный")
        else:
            print(f"❌ {cert_file} - не найден")

async def main():
    """Главная функция тестирования"""
    print("🚀 Запуск тестирования web-сервиса...\n")
    
    # Проверяем директории
    test_directories()
    
    # Проверяем сертификаты
    test_certificates()
    
    # Проверяем импорты
    if not test_imports():
        print("\n❌ Критические ошибки импортов. Проверьте зависимости.")
        return
    
    # Проверяем конфигурацию
    test_config()
    
    # Тестируем функциональность
    await test_basic_functionality()
    
    print("\n✅ Тестирование завершено!")
    print("\n📝 Рекомендации:")
    print("1. Добавьте валидные сертификаты GigaChat для полного функционала")
    print("2. Запустите сервис командой: python main.py")

if __name__ == "__main__":
    asyncio.run(main())
