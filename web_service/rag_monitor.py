#!/usr/bin/env python3
"""
Мониторинг состояния RAG базы данных
Периодически проверяет и логирует состояние ChromaDB
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
import schedule

# Добавляем путь к приложению
sys.path.append('.')

from config import config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rag_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def check_rag_health():
    """Проверка здоровья RAG системы"""
    try:
        # Обход SQLite если нужно
        if os.getenv('CHROMA_SQLITE_OVERRIDE') == '1':
            import sqlite3
            sqlite3.sqlite_version = "3.35.0"
        
        import chromadb
        from chromadb.config import Settings
        
        # Подключаемся к базе
        client = chromadb.PersistentClient(
            path=config.CHROMA_DB_PATH,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        collection = client.get_collection(config.CHROMA_COLLECTION_NAME)
        count = collection.count()
        
        # Получаем статистику
        stats = {
            "timestamp": datetime.now().isoformat(),
            "total_documents": count,
            "db_path_exists": os.path.exists(config.CHROMA_DB_PATH),
            "collection_name": config.CHROMA_COLLECTION_NAME
        }
        
        if count > 0:
            # Получаем метаданные для анализа
            all_data = collection.get(include=["metadatas"])
            
            # Анализируем источники
            sources = {}
            confluence_pages = set()
            uploaded_files = set()
            
            for metadata in all_data['metadatas']:
                source = metadata.get('source', 'unknown')
                timestamp = metadata.get('timestamp', 'unknown')
                
                if source not in sources:
                    sources[source] = 0
                sources[source] += 1
                
                if source == 'confluence':
                    page_id = metadata.get('page_id', 'unknown')
                    confluence_pages.add(page_id)
                elif source == 'file':
                    filename = metadata.get('filename', 'unknown')
                    uploaded_files.add(filename)
            
            stats.update({
                "sources": sources,
                "confluence_pages": len(confluence_pages),
                "uploaded_files": len(uploaded_files)
            })
        
        # Логируем статистику
        logger.info(f"📊 RAG Health Check: {json.dumps(stats, ensure_ascii=False)}")
        
        # Сохраняем в файл для истории
        with open('rag_health_history.jsonl', 'a', encoding='utf-8') as f:
            f.write(json.dumps(stats, ensure_ascii=False) + '\n')
        
        return stats
        
    except Exception as e:
        error_stats = {
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "status": "error"
        }
        logger.error(f"❌ RAG Health Check Error: {json.dumps(error_stats, ensure_ascii=False)}")
        
        with open('rag_health_history.jsonl', 'a', encoding='utf-8') as f:
            f.write(json.dumps(error_stats, ensure_ascii=False) + '\n')
        
        return error_stats

def main():
    """Запуск мониторинга"""
    logger.info("🚀 Запуск мониторинга RAG системы...")
    
    # Планируем проверки каждые 5 минут
    schedule.every(5).minutes.do(check_rag_health)
    
    # Первая проверка сразу
    check_rag_health()
    
    # Основной цикл
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Проверяем каждую минуту, выполняем по расписанию
    except KeyboardInterrupt:
        logger.info("🛑 Мониторинг остановлен")

if __name__ == "__main__":
    main()