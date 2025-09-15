#!/usr/bin/env python3
"""
Скрипт запуска для корпоративной среды

Этот скрипт обеспечивает правильную инициализацию системы
исключительно с GigaChat компонентами.
"""

import os
import sys
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def check_corporate_environment():
    """Проверка корпоративной среды"""
    logger.info("🔍 Проверка корпоративной среды...")
    
    # Проверяем сертификаты
    cert_path = "../certificates/cert.pem"
    key_path = "../certificates/key.pem"
    
    if not os.path.exists(cert_path):
        logger.error(f"❌ Сертификат не найден: {cert_path}")
        return False
    
    if not os.path.exists(key_path):
        logger.error(f"❌ Ключ не найден: {key_path}")
        return False
    
    # Проверяем содержимое
    with open(cert_path, 'r') as f:
        cert_content = f.read()
        if "# Certificate Placeholder" in cert_content:
            logger.error("❌ Найден файл-заглушка сертификата")
            return False
    
    with open(key_path, 'r') as f:
        key_content = f.read()
        if "# Private Key Placeholder" in key_content:
            logger.error("❌ Найден файл-заглушка ключа")
            return False
    
    logger.info("✅ Сертификаты корпоративной среды проверены")
    return True

def setup_environment():
    """Настройка переменных окружения для корпоративной среды"""
    logger.info("⚙️ Настройка переменных окружения...")
    
    # Принудительно устанавливаем корпоративные настройки
    os.environ["GIGACHAT_BASE_URL"] = "https://gigachat-ift.sberdevices.delta.sbrf.ru/v1"
    os.environ["GIGACHAT_EMBEDDING_MODEL"] = "EmbeddingsGigaR"
    os.environ["MTLS_VERIFY_SSL"] = "false"  # В корпоративной среде часто нужно отключать
    
    # Убираем любые fallback настройки
    if "FALLBACK_EMBEDDINGS" in os.environ:
        del os.environ["FALLBACK_EMBEDDINGS"]
    
    logger.info("✅ Переменные окружения настроены для корпоративной среды")

def import_and_check_services():
    """Импорт и проверка сервисов"""
    logger.info("📦 Инициализация сервисов...")
    
    try:
        from app.services.gigachat_service import GigaChatService
        from app.services.rag_service import RAGService
        
        # Инициализируем GigaChat сервис
        gigachat_service = GigaChatService()
        
        if not gigachat_service.is_available:
            logger.error("❌ GigaChat сервис недоступен")
            return None, None
        
        if not gigachat_service.client:
            logger.error("❌ GigaChat клиент не инициализирован")
            return None, None
        
        logger.info("✅ GigaChat сервис инициализирован")
        
        # Инициализируем RAG сервис
        try:
            rag_service = RAGService()
            
            if not rag_service.is_available:
                logger.error("❌ RAG сервис недоступен")
                return gigachat_service, None
            
            if not rag_service.embedding_provider:
                logger.error("❌ Embedding провайдер не инициализирован")
                return gigachat_service, None
            
            provider_type = type(rag_service.embedding_provider).__name__
            if "Simple" in provider_type:
                logger.error("❌ Используется fallback провайдер вместо GigaChat")
                return gigachat_service, None
            
            logger.info(f"✅ RAG сервис инициализирован с провайдером: {provider_type}")
            return gigachat_service, rag_service
            
        except RuntimeError as e:
            logger.error(f"❌ Ошибка инициализации RAG: {e}")
            return gigachat_service, None
        
    except Exception as e:
        logger.error(f"❌ Ошибка импорта сервисов: {e}")
        return None, None

def start_application():
    """Запуск приложения"""
    logger.info("🚀 Запуск приложения в корпоративной среде...")
    
    try:
        import uvicorn
        from main import app
        
        logger.info("🌐 Запуск web-сервера...")
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000,
            log_level="info"
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска приложения: {e}")
        return False
    
    return True

def main():
    """Основная функция запуска"""
    logger.info("🏢 Запуск системы в корпоративной среде")
    logger.info("=" * 50)
    
    # 1. Проверяем корпоративную среду
    if not check_corporate_environment():
        logger.error("❌ Корпоративная среда не готова")
        return 1
    
    # 2. Настраиваем окружение
    setup_environment()
    
    # 3. Проверяем сервисы
    gigachat_service, rag_service = import_and_check_services()
    
    if not gigachat_service:
        logger.error("❌ GigaChat сервис не может быть инициализирован")
        logger.error("🔧 Проверьте сертификаты и сетевое подключение")
        return 1
    
    if not rag_service:
        logger.error("❌ RAG сервис не может быть инициализирован")
        logger.error("🔧 Проверьте GigaChat embeddings")
        return 1
    
    logger.info("🎉 Все сервисы успешно инициализированы")
    logger.info("✅ Система готова к работе в корпоративной среде")
    
    # 4. Запускаем приложение
    if not start_application():
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())