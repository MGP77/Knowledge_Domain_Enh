#!/usr/bin/env python3
"""
ChromaDB Maintenance and Optimization Script
"""

import os
import sys
import json
from datetime import datetime

sys.path.append('.')
from config import config

def check_chromadb_maintenance():
    """Проверка необходимости обслуживания ChromaDB"""
    
    print("🔧 ChromaDB Maintenance Check")
    print("=" * 50)
    
    # ChromaDB автоматически управляет индексами
    print("✅ ChromaDB использует автоматическое управление индексами")
    print("📝 Ре-индексация вручную НЕ ТРЕБУЕТСЯ")
    
    # Проверяем размер базы
    db_path = config.CHROMA_DB_PATH
    if os.path.exists(db_path):
        size_mb = sum(os.path.getsize(os.path.join(dirpath, filename))
                     for dirpath, dirnames, filenames in os.walk(db_path)
                     for filename in filenames) / (1024 * 1024)
        print(f"💾 Размер базы: {size_mb:.2f} MB")
        
        if size_mb > 500:
            print("⚠️ База данных большая - рекомендуется мониторинг")
        else:
            print("✅ Размер базы данных в норме")
    else:
        print("❌ База данных не найдена")
    
    print("\n📋 Рекомендации по обслуживанию:")
    print("1. ✅ Регулярное создание бэкапов")
    print("2. ✅ Мониторинг размера базы данных")
    print("3. ✅ Проверка доступности embedding провайдера")
    print("4. ❌ Ручная ре-индексация НЕ нужна")
    
    return {
        "reindexing_needed": False,
        "automatic_optimization": True,
        "maintenance_type": "monitoring_only"
    }

if __name__ == "__main__":
    result = check_chromadb_maintenance()
    print(f"\n🎯 Результат: {json.dumps(result, indent=2)}")