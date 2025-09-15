#!/usr/bin/env python3
"""
Диагностика RAG базы данных - проверка состояния ChromaDB
Помогает выявить причины пропадания документов из RAG
"""

import os
import sys
import json
from datetime import datetime
import logging

# Добавляем путь к приложению
sys.path.append('.')

# Импортируем конфигурацию
from config import config

def check_chroma_persistence():
    """Проверка персистентности ChromaDB"""
    print("🔍 Проверка состояния ChromaDB...")
    print("=" * 60)
    
    try:
        # Импорт с обходом SQLite (если нужно)
        if os.getenv('CHROMA_SQLITE_OVERRIDE') == '1':
            import sqlite3
            sqlite3.sqlite_version = "3.35.0"
            print("🔧 Применен обход SQLite для корпоративной среды")
        
        import chromadb
        from chromadb.config import Settings
        
        # Проверяем путь к базе
        db_path = config.CHROMA_DB_PATH
        print(f"📂 Путь к базе данных: {db_path}")
        print(f"📊 Имя коллекции: {config.CHROMA_COLLECTION_NAME}")
        
        # Проверяем существование директории
        if os.path.exists(db_path):
            print(f"✅ Директория базы существует")
            
            # Показываем содержимое директории
            files = os.listdir(db_path)
            print(f"📁 Файлы в базе: {files}")
            
            # Проверяем размер файлов
            for file in files:
                file_path = os.path.join(db_path, file)
                if os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    print(f"   📄 {file}: {size} байт")
        else:
            print(f"❌ Директория базы не существует!")
            return
        
        # Подключаемся к базе
        client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        print(f"✅ Подключение к ChromaDB успешно")
        
        # Получаем коллекцию
        try:
            collection = client.get_collection(config.CHROMA_COLLECTION_NAME)
            print(f"✅ Коллекция найдена: {config.CHROMA_COLLECTION_NAME}")
        except Exception as e:
            print(f"❌ Коллекция не найдена: {e}")
            print("🔧 Попробуем создать коллекцию...")
            collection = client.get_or_create_collection(config.CHROMA_COLLECTION_NAME)
            print(f"✅ Коллекция создана: {config.CHROMA_COLLECTION_NAME}")
        
        # Получаем статистику
        count = collection.count()
        print(f"📊 Всего документов в базе: {count}")
        
        if count > 0:
            # Получаем метаданные всех документов
            all_data = collection.get(include=["metadatas", "documents"])
            
            # Анализируем источники
            sources = {}
            confluence_pages = set()
            uploaded_files = set()
            
            for i, metadata in enumerate(all_data['metadatas']):
                source = metadata.get('source', 'unknown')
                timestamp = metadata.get('timestamp', 'unknown')
                
                # Подсчитываем по источникам
                if source not in sources:
                    sources[source] = []
                sources[source].append({
                    'index': i,
                    'timestamp': timestamp,
                    'metadata': metadata
                })
                
                # Специальная обработка для Confluence и файлов
                if source == 'confluence':
                    page_id = metadata.get('page_id', 'unknown')
                    page_title = metadata.get('title', 'Без названия')
                    confluence_pages.add(f"{page_id}: {page_title}")
                elif source == 'file':
                    filename = metadata.get('filename', 'unknown')
                    uploaded_files.add(filename)
            
            print(f"\n📈 Статистика по источникам:")
            for source, items in sources.items():
                print(f"   {source}: {len(items)} чанков")
                
                # Показываем последние документы
                recent_items = sorted(items, key=lambda x: x.get('timestamp', ''), reverse=True)[:3]
                for item in recent_items:
                    timestamp = item['metadata'].get('timestamp', 'unknown')
                    title = item['metadata'].get('title', 'Без названия')
                    print(f"     - {title} ({timestamp})")
            
            print(f"\n📄 Confluence страницы ({len(confluence_pages)}):")
            for page in sorted(confluence_pages):
                print(f"   - {page}")
            
            print(f"\n📁 Загруженные файлы ({len(uploaded_files)}):")
            for file in sorted(uploaded_files):
                print(f"   - {file}")
                
            # Показываем последние 5 документов
            print(f"\n🕒 Последние документы:")
            recent_docs = []
            for i, metadata in enumerate(all_data['metadatas']):
                timestamp = metadata.get('timestamp', '')
                if timestamp:
                    recent_docs.append((timestamp, metadata, all_data['documents'][i][:100]))
            
            recent_docs.sort(reverse=True)
            for i, (timestamp, metadata, content_preview) in enumerate(recent_docs[:5]):
                title = metadata.get('title', 'Без названия')
                source = metadata.get('source', 'unknown')
                print(f"   {i+1}. [{source}] {title} ({timestamp})")
                print(f"      Содержимое: {content_preview}...")
                
        else:
            print("📭 База данных пуста")
            
    except Exception as e:
        print(f"❌ Ошибка при проверке базы: {e}")
        import traceback
        traceback.print_exc()

def check_rag_service_status():
    """Проверка состояния RAG сервиса"""
    print(f"\n🔧 Проверка RAG сервиса...")
    print("=" * 60)
    
    try:
        from app.services.rag_service import RAGService
        
        # Создаем экземпляр RAG сервиса
        rag = RAGService()
        
        print(f"📊 RAG сервис доступен: {rag.is_available}")
        print(f"🔧 Embedding провайдер: {type(rag.embedding_provider).__name__ if rag.embedding_provider else 'None'}")
        
        if rag.is_available:
            # Получаем статистику
            stats = rag.get_stats()
            print(f"📈 Статистика RAG:")
            for key, value in stats.items():
                print(f"   {key}: {value}")
                
            # Тестовый поиск
            print(f"\n🔍 Тестовый поиск...")
            results = rag.search("тест", n_results=3)
            print(f"📊 Найдено результатов: {len(results)}")
            
            for i, result in enumerate(results):
                metadata = result.get('metadata', {})
                title = metadata.get('title', 'Без названия')
                source = metadata.get('source', 'unknown')
                score = result.get('score', 0)
                print(f"   {i+1}. [{source}] {title} (score: {score:.3f})")
        else:
            print("❌ RAG сервис недоступен")
            
    except Exception as e:
        print(f"❌ Ошибка при проверке RAG сервиса: {e}")
        import traceback
        traceback.print_exc()

def check_service_logs():
    """Проверка логов сервиса"""
    print(f"\n📋 Проверка логов...")
    print("=" * 60)
    
    log_file = "knowledge_system.log"
    if os.path.exists(log_file):
        print(f"✅ Лог файл найден: {log_file}")
        
        # Показываем последние строки логов
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            print(f"📊 Всего строк в логе: {len(lines)}")
            
            # Последние 20 строк
            print(f"\n🕒 Последние записи лога:")
            for line in lines[-20:]:
                print(f"   {line.strip()}")
                
            # Ищем ошибки
            error_lines = [line for line in lines if 'ERROR' in line or 'Exception' in line]
            if error_lines:
                print(f"\n❌ Найдены ошибки ({len(error_lines)}):")
                for line in error_lines[-10:]:  # Последние 10 ошибок
                    print(f"   {line.strip()}")
            else:
                print(f"\n✅ Ошибок в логах не найдено")
                
        except Exception as e:
            print(f"❌ Ошибка чтения лога: {e}")
    else:
        print(f"❌ Лог файл не найден: {log_file}")

def main():
    """Основная функция диагностики"""
    print("🔍 ДИАГНОСТИКА RAG СИСТЕМЫ")
    print("=" * 60)
    print(f"🕒 Время: {datetime.now()}")
    print(f"🔧 Python: {sys.version}")
    print(f"📂 Рабочая директория: {os.getcwd()}")
    
    # Проверяем переменные окружения
    print(f"\n🌍 Переменные окружения:")
    env_vars = ['CHROMA_SQLITE_OVERRIDE', 'DEBUG', 'GIGACHAT_MODEL']
    for var in env_vars:
        value = os.getenv(var, 'не установлена')
        print(f"   {var}: {value}")
    
    # Запускаем проверки
    check_chroma_persistence()
    check_rag_service_status()
    check_service_logs()
    
    print(f"\n✅ Диагностика завершена")
    print("=" * 60)

if __name__ == "__main__":
    main()