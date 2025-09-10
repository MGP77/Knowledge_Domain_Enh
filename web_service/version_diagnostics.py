#!/usr/bin/env python3
"""
Диагностика проблем с версиями пакетов в корпоративной среде
"""

import sys
import importlib
import pkg_resources
from datetime import datetime

def check_package_versions():
    """Проверяет версии ключевых пакетов"""
    
    print("🔍 ДИАГНОСТИКА ВЕРСИЙ ПАКЕТОВ")
    print("=" * 50)
    print(f"⏰ Время: {datetime.now()}")
    print(f"🐍 Python: {sys.version}")
    print()
    
    # Критически важные пакеты
    critical_packages = [
        'fastapi',
        'uvicorn', 
        'jinja2',
        'pydantic',
        'requests'
    ]
    
    # Дополнительные пакеты
    additional_packages = [
        'python-multipart',
        'chromadb',
        'pypdf2',
        'python-docx',
        'beautifulsoup4',
        'python-magic',
        'typing-extensions',
        'aiofiles',
        'python-dotenv',
        'langchain-gigachat'
    ]
    
    all_packages = critical_packages + additional_packages
    
    print("📦 КРИТИЧЕСКИ ВАЖНЫЕ ПАКЕТЫ:")
    print("-" * 30)
    
    critical_ok = True
    for package in critical_packages:
        try:
            version = pkg_resources.get_distribution(package).version
            print(f"✅ {package:20} v{version}")
        except pkg_resources.DistributionNotFound:
            print(f"❌ {package:20} НЕ УСТАНОВЛЕН")
            critical_ok = False
        except Exception as e:
            print(f"⚠️  {package:20} ОШИБКА: {e}")
            critical_ok = False
    
    print()
    print("📚 ДОПОЛНИТЕЛЬНЫЕ ПАКЕТЫ:")
    print("-" * 30)
    
    additional_ok = True
    for package in additional_packages:
        try:
            version = pkg_resources.get_distribution(package).version
            print(f"✅ {package:20} v{version}")
        except pkg_resources.DistributionNotFound:
            print(f"❌ {package:20} НЕ УСТАНОВЛЕН")
            additional_ok = False
        except Exception as e:
            print(f"⚠️  {package:20} ОШИБКА: {e}")
    
    print()
    print("🔄 ТЕСТ ИМПОРТОВ:")
    print("-" * 30)
    
    # Тестируем импорты
    import_tests = [
        ('fastapi', 'FastAPI'),
        ('uvicorn', 'uvicorn'),
        ('jinja2', 'Jinja2'),
        ('pydantic', 'Pydantic'),
        ('requests', 'HTTP клиент'),
    ]
    
    import_ok = True
    for module, description in import_tests:
        try:
            importlib.import_module(module)
            print(f"✅ {module:20} {description}")
        except ImportError as e:
            print(f"❌ {module:20} ОШИБКА ИМПОРТА: {e}")
            import_ok = False
        except Exception as e:
            print(f"⚠️  {module:20} ОШИБКА: {e}")
            import_ok = False
    
    print()
    print("🎯 РЕЗУЛЬТАТ ДИАГНОСТИКИ:")
    print("=" * 50)
    
    if critical_ok and import_ok:
        print("🎉 ВСЕ КРИТИЧЕСКИ ВАЖНЫЕ ПАКЕТЫ В ПОРЯДКЕ!")
        print("   Проблема с белой страницей НЕ связана с версиями пакетов.")
        print()
        print("🔍 Возможные другие причины:")
        print("   - CORS политики (уже исправлено)")
        print("   - Content Security Policy (уже исправлено)")
        print("   - Проблемы с шаблонами или статическими файлами")
        print("   - Корпоративный firewall")
        
    elif not critical_ok:
        print("💥 КРИТИЧЕСКИЕ ПАКЕТЫ ОТСУТСТВУЮТ!")
        print("   Переустановите зависимости:")
        print("   pip install -r requirements-corporate-flexible.txt")
        
    elif not import_ok:
        print("⚠️  ПРОБЛЕМЫ С ИМПОРТАМИ!")
        print("   Возможные конфликты версий.")
        print("   Рекомендуется:")
        print("   1. pip uninstall fastapi uvicorn jinja2 pydantic")
        print("   2. pip install -r requirements-corporate-flexible.txt")
    
    if not additional_ok:
        print()
        print("📚 Некоторые дополнительные пакеты отсутствуют")
        print("   Это может влиять на функциональность, но не на белую страницу")

def check_fastapi_compatibility():
    """Проверяет совместимость FastAPI компонентов"""
    
    print()
    print("🚀 ПРОВЕРКА СОВМЕСТИМОСТИ FASTAPI:")
    print("=" * 50)
    
    try:
        import fastapi
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import HTMLResponse
        from fastapi.templating import Jinja2Templates
        
        print(f"✅ FastAPI v{fastapi.__version__}")
        print("✅ CORSMiddleware импортирован")
        print("✅ HTMLResponse импортирован")
        print("✅ Jinja2Templates импортирован")
        
        # Тестируем создание приложения
        app = FastAPI(title="Test App")
        app.add_middleware(CORSMiddleware, allow_origins=["*"])
        
        print("✅ Тестовое FastAPI приложение создано")
        print("✅ CORS middleware добавлен")
        
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта FastAPI: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка создания FastAPI приложения: {e}")
        return False

def version_compatibility_recommendations():
    """Рекомендации по версиям для корпоративной среды"""
    
    print()
    print("💡 РЕКОМЕНДАЦИИ ПО ВЕРСИЯМ:")
    print("=" * 50)
    
    recommendations = {
        "fastapi": ">=0.100.0 (стабильная ветка)",
        "uvicorn": ">=0.20.0 (совместимость с корп. сетями)",
        "jinja2": ">=3.0.0 (поддержка async)",
        "pydantic": ">=2.0.0 (новый API)",
        "requests": ">=2.28.0 (поддержка корп. прокси)"
    }
    
    for package, recommendation in recommendations.items():
        print(f"📦 {package:15} → {recommendation}")
    
    print()
    print("⚠️  ВАЖНО для корпоративной среды:")
    print("   - Используйте >=версии вместо == для гибкости")
    print("   - Старые версии могут иметь проблемы с CORS")
    print("   - Новые версии лучше работают с корп. прокси")

if __name__ == "__main__":
    try:
        check_package_versions()
        fastapi_ok = check_fastapi_compatibility()
        version_compatibility_recommendations()
        
        print()
        print("🎯 ЗАКЛЮЧЕНИЕ:")
        print("=" * 50)
        
        if fastapi_ok:
            print("✅ FastAPI компоненты работают корректно")
            print("   Проблема с белой страницей скорее всего НЕ в версиях пакетов")
        else:
            print("❌ Проблемы с FastAPI компонентами")
            print("   ВОЗМОЖНАЯ ПРИЧИНА белой страницы!")
            print()
            print("🔧 РЕШЕНИЕ:")
            print("   pip install -r requirements-corporate-flexible.txt")
            
    except KeyboardInterrupt:
        print("\n\n❌ Диагностика прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Критическая ошибка: {e}")
        sys.exit(1)
