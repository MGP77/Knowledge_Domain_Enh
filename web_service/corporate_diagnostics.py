#!/usr/bin/env python3
"""
Скрипт для диагностики проблем в корпоративной среде
"""

import requests
import sys
import json
from datetime import datetime

def test_server_endpoints():
    """Тестирует доступность всех основных endpoint'ов"""
    base_url = "http://localhost:8005"
    
    print("🔍 Диагностика сервера в корпоративной среде")
    print("=" * 50)
    print(f"⏰ Время: {datetime.now()}")
    print(f"🌐 Базовый URL: {base_url}")
    print()
    
    # Список endpoint'ов для тестирования
    endpoints = [
        ("/health", "Простой health check"),
        ("/api/health", "Детальный health check"), 
        ("/", "Главная страница"),
        ("/admin", "Админ панель"),
        ("/docs", "Swagger документация"),
    ]
    
    results = []
    
    for endpoint, description in endpoints:
        url = f"{base_url}{endpoint}"
        print(f"🔗 Тестируем: {description}")
        print(f"   URL: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            status = response.status_code
            content_type = response.headers.get('content-type', 'unknown')
            content_length = len(response.content)
            
            if status == 200:
                print(f"   ✅ Статус: {status}")
                print(f"   📋 Content-Type: {content_type}")
                print(f"   📏 Размер: {content_length} байт")
                
                # Для JSON endpoint'ов показываем содержимое
                if 'json' in content_type and endpoint in ['/health', '/api/health']:
                    try:
                        data = response.json()
                        print(f"   📊 Данные: {json.dumps(data, indent=2)}")
                    except:
                        pass
                        
                # Для HTML endpoint'ов проверяем наличие контента
                elif 'html' in content_type:
                    if content_length < 100:
                        print(f"   ⚠️  Подозрительно маленький размер HTML!")
                        print(f"   📄 Содержимое: {response.text[:200]}...")
                
                results.append((endpoint, True, status, f"{content_length} байт"))
            else:
                print(f"   ❌ Статус: {status}")
                results.append((endpoint, False, status, f"HTTP {status}"))
                
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Ошибка: Не удается подключиться к серверу")
            results.append((endpoint, False, "CONN", "Connection refused"))
        except requests.exceptions.Timeout:
            print(f"   ❌ Ошибка: Таймаут подключения")
            results.append((endpoint, False, "TIMEOUT", "Request timeout"))
        except Exception as e:
            print(f"   ❌ Ошибка: {str(e)}")
            results.append((endpoint, False, "ERROR", str(e)))
        
        print()
    
    # Сводка результатов
    print("📊 СВОДКА РЕЗУЛЬТАТОВ")
    print("=" * 50)
    successful = sum(1 for _, success, _, _ in results if success)
    total = len(results)
    
    for endpoint, success, status, detail in results:
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} {endpoint:15} | {status:8} | {detail}")
    
    print()
    print(f"🎯 Успешных тестов: {successful}/{total}")
    
    if successful == total:
        print("🎉 Все endpoint'ы работают корректно!")
    elif successful == 0:
        print("💥 Сервер недоступен или не запущен")
        print("   Проверьте:")
        print("   1. Запущен ли сервер (python main.py)")
        print("   2. Правильный ли порт (8005)")
        print("   3. Нет ли блокировки firewall")
    else:
        print("⚠️  Некоторые endpoint'ы недоступны")
        print("   Возможные причины:")
        print("   - Проблемы с шаблонами (для HTML страниц)")
        print("   - CORS политики корпоративной среды")
        print("   - Блокировка статических файлов")

def test_curl_commands():
    """Показывает curl команды для ручного тестирования"""
    print("\n🛠️  КОМАНДЫ ДЛЯ РУЧНОГО ТЕСТИРОВАНИЯ")
    print("=" * 50)
    print("Выполните эти команды в терминале корпоративной машины:")
    print()
    
    commands = [
        "curl -v http://localhost:8005/health",
        "curl -v http://localhost:8005/api/health", 
        "curl -v http://localhost:8005/",
        "curl -I http://localhost:8005/",  # Только заголовки
    ]
    
    for cmd in commands:
        print(f"   {cmd}")
    
    print()
    print("📋 Что смотреть в выводе curl:")
    print("   - HTTP/1.1 200 OK - успешный ответ")
    print("   - Content-Type: text/html - правильный тип контента")
    print("   - Content-Length > 0 - есть содержимое")
    print("   - Нет ошибок 'Connection refused'")

if __name__ == "__main__":
    try:
        test_server_endpoints()
        test_curl_commands()
    except KeyboardInterrupt:
        print("\n\n❌ Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Критическая ошибка: {e}")
        sys.exit(1)
