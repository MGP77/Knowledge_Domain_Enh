#!/usr/bin/env python3
"""
Скрипт тестирования GigaChat в корпоративной среде

Этот скрипт выполняет полную диагностику системы для корпоративной среды.
"""

import sys
import os
import requests
import json
from pathlib import Path

# Добавляем пути для импорта
sys.path.append('.')
sys.path.append('./app')

def check_certificates():
    """Проверка сертификатов mTLS"""
    print("🔍 Проверка сертификатов...")
    
    cert_path = "../certificates/cert.pem"
    key_path = "../certificates/key.pem"
    
    cert_exists = os.path.exists(cert_path)
    key_exists = os.path.exists(key_path)
    
    print(f"📄 Сертификат {cert_path}: {'✅ Найден' if cert_exists else '❌ Не найден'}")
    print(f"🔑 Ключ {key_path}: {'✅ Найден' if key_exists else '❌ Не найден'}")
    
    if cert_exists:
        with open(cert_path, 'r') as f:
            cert_content = f.read()
            size = len(cert_content)
            is_placeholder = "# Certificate Placeholder" in cert_content
            print(f"   📏 Размер: {size} байт")
            print(f"   🏷️ Тип: {'Заглушка' if is_placeholder else 'Реальный сертификат'}")
    
    if key_exists:
        with open(key_path, 'r') as f:
            key_content = f.read()
            size = len(key_content)
            is_placeholder = "# Private Key Placeholder" in key_content
            print(f"   📏 Размер: {size} байт")
            print(f"   🏷️ Тип: {'Заглушка' if is_placeholder else 'Реальный ключ'}")
    
    return cert_exists and key_exists

def test_gigachat_connection():
    """Тестирование подключения к GigaChat"""
    print("\n🌐 Тестирование подключения к GigaChat...")
    
    base_url = "https://gigachat-ift.sberdevices.delta.sbrf.ru/v1"
    cert_path = "../certificates/cert.pem"
    key_path = "../certificates/key.pem"
    
    # Тестируем embedding endpoint
    test_data = {
        "model": "EmbeddingsGigaR",
        "input": ["Тестовый текст для проверки подключения"]
    }
    
    url = f"{base_url}/embeddings"
    
    try:
        print(f"🔗 URL: {url}")
        print(f"🤖 Модель: {test_data['model']}")
        print(f"📝 Тестовый текст: {test_data['input'][0]}")
        
        response = requests.post(
            url,
            json=test_data,
            cert=(cert_path, key_path),
            verify=False,  # Отключаем проверку SSL для корпоративной среды
            timeout=60,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )
        
        print(f"📡 HTTP статус: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            if "data" in response_data and len(response_data["data"]) > 0:
                embedding = response_data["data"][0]["embedding"]
                print(f"✅ Embedding получен успешно!")
                print(f"📐 Размерность: {len(embedding)}")
                print(f"🔢 Первые 5 значений: {embedding[:5]}")
                return True
            else:
                print(f"❌ Некорректный формат ответа: {response_data}")
                return False
        else:
            print(f"❌ Ошибка HTTP: {response.status_code}")
            print(f"📄 Ответ: {response.text}")
            return False
            
    except requests.exceptions.SSLError as e:
        print(f"❌ SSL ошибка: {e}")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Ошибка соединения: {e}")
        return False
    except requests.exceptions.Timeout as e:
        print(f"❌ Тайм-аут: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def test_langchain_gigachat():
    """Тестирование langchain-gigachat"""
    print("\n🔧 Тестирование langchain-gigachat...")
    
    try:
        from langchain_gigachat import GigaChatEmbeddings
        print("✅ langchain-gigachat импортирован успешно")
        
        # Пробуем создать провайдер
        embeddings = GigaChatEmbeddings(
            model="EmbeddingsGigaR",
            base_url="https://gigachat-ift.sberdevices.delta.sbrf.ru/v1",
            ca_bundle_file=None,
            cert_file="../certificates/cert.pem",
            key_file="../certificates/key.pem",
            verify_ssl_certs=False
        )
        
        print("✅ GigaChatEmbeddings создан успешно")
        
        # Тестируем получение embedding
        test_text = "Тестовый текст для langchain"
        embedding = embeddings.embed_query(test_text)
        
        print(f"✅ Embedding через langchain получен!")
        print(f"📐 Размерность: {len(embedding)}")
        print(f"🔢 Первые 5 значений: {embedding[:5]}")
        
        return True
        
    except ImportError as e:
        print(f"❌ langchain-gigachat не установлен: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка langchain-gigachat: {e}")
        return False

def test_services():
    """Тестирование сервисов приложения"""
    print("\n🛠️ Тестирование сервисов приложения...")
    
    try:
        from app.services.gigachat_service import GigaChatService
        from app.services.rag_service import RAGService
        
        # Тестируем GigaChat сервис
        print("📦 Инициализация GigaChatService...")
        gigachat_service = GigaChatService()
        
        print(f"   🔧 Клиент инициализирован: {'✅' if gigachat_service.client else '❌'}")
        print(f"   🌐 Доступность: {'✅' if gigachat_service.is_available else '❌'}")
        
        if gigachat_service.is_available:
            test_result = gigachat_service.test_embeddings("Тест сервиса")
            print(f"   🧠 Тест embeddings: {'✅' if test_result['success'] else '❌'}")
            if not test_result['success']:
                print(f"      ❌ Ошибка: {test_result['error']}")
        
        # Тестируем RAG сервис
        print("📦 Инициализация RAGService...")
        rag_service = RAGService()
        
        print(f"   🔧 Сервис доступен: {'✅' if rag_service.is_available else '❌'}")
        if rag_service.embedding_provider:
            provider_type = type(rag_service.embedding_provider).__name__
            print(f"   🧠 Провайдер embeddings: {provider_type}")
        else:
            print("   ❌ Провайдер embeddings не инициализирован")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования сервисов: {e}")
        return False

def main():
    """Основная функция диагностики"""
    print("🚀 Диагностика GigaChat в корпоративной среде")
    print("=" * 50)
    
    all_tests_passed = True
    
    # Проверка сертификатов
    certs_ok = check_certificates()
    all_tests_passed &= certs_ok
    
    # Тестирование прямого подключения
    if certs_ok:
        connection_ok = test_gigachat_connection()
        all_tests_passed &= connection_ok
        
        # Тестирование langchain
        langchain_ok = test_langchain_gigachat()
        all_tests_passed &= langchain_ok
        
        # Тестирование сервисов
        services_ok = test_services()
        all_tests_passed &= services_ok
    else:
        print("\n⚠️ Пропускаем тесты подключения - сертификаты недоступны")
    
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("🎉 Все тесты пройдены успешно!")
        print("✅ Система готова к работе в корпоративной среде")
    else:
        print("❌ Обнаружены проблемы")
        print("🔧 Проверьте сертификаты и сетевое подключение")
    
    return 0 if all_tests_passed else 1

if __name__ == "__main__":
    exit(main())