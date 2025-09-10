#!/usr/bin/env python3
"""
Демонстрация функциональности выбора моделей GigaChat

Copyright (c) 2025. All rights reserved.
Author: M.P.
"""

from config import config
from app.services.gigachat_service import GigaChatService
import json

def demo_models():
    """Демонстрация работы с моделями"""
    print("🤖 Демонстрация функциональности выбора моделей GigaChat")
    print("=" * 60)
    
    # Инициализируем сервис
    service = GigaChatService()
    
    print(f"📊 Статус GigaChat: {'✅ Доступен' if service.check_availability() else '❌ Недоступен'}")
    print()
    
    # Показываем конфигурацию моделей
    print("⚙️ Конфигурация моделей:")
    print(f"   По умолчанию: {config.GIGACHAT_MODELS['по_умолчанию']}")
    print(f"   Доступные модели:")
    for model in config.GIGACHAT_MODELS['доступные']:
        is_current = model == config.DEFAULT_GIGACHAT_MODEL
        print(f"   {'✅' if is_current else '  '} {model}")
    print()
    
    # Показываем детальную информацию о моделях
    print("📋 Детальная информация о моделях:")
    if service.check_availability():
        models = service.get_available_models()
        for model in models:
            status = "🟢 АКТИВНА" if model['name'] == service.get_current_model() else "⚪ Доступна"
            default_badge = " [ПО УМОЛЧАНИЮ]" if model['is_default'] else ""
            print(f"   {status} {model['display_name']}{default_badge}")
            print(f"      {model['description']}")
            print()
    else:
        print("   ❌ Сервис недоступен - функция ограничена")
        print("   📝 Демонстрационный список:")
        for model in config.GIGACHAT_MODELS['доступные']:
            display_name = service._get_model_display_name(model)
            description = service._get_model_description(model)
            is_default = model == config.GIGACHAT_MODELS['по_умолчанию']
            is_current = model == config.DEFAULT_GIGACHAT_MODEL
            
            status = "🟢 АКТИВНА" if is_current else "⚪ Доступна"
            default_badge = " [ПО УМОЛЧАНИЮ]" if is_default else ""
            print(f"   {status} {display_name}{default_badge}")
            print(f"      {description}")
            print()
    
    # Демонстрация API ответа
    print("🔌 Пример API ответа /api/admin/models:")
    api_response = {
        "models": [
            {
                "name": model,
                "display_name": service._get_model_display_name(model),
                "description": service._get_model_description(model),
                "is_default": model == config.GIGACHAT_MODELS['по_умолчанию']
            }
            for model in config.GIGACHAT_MODELS['доступные']
        ],
        "current_model": config.DEFAULT_GIGACHAT_MODEL,
        "available": service.check_availability()
    }
    print(json.dumps(api_response, indent=2, ensure_ascii=False))
    print()
    
    # Демонстрация установки модели
    print("🔧 Демонстрация установки модели:")
    print(f"   Текущая модель: {config.DEFAULT_GIGACHAT_MODEL}")
    
    # Пробуем установить другую модель
    test_model = "GigaChat-2-Max"
    print(f"   Попытка установить: {test_model}")
    
    if service.check_availability():
        result = service.set_model(test_model)
        if result:
            print(f"   ✅ Модель успешно установлена: {service.get_current_model()}")
        else:
            print(f"   ❌ Ошибка установки модели")
    else:
        # Симулируем установку для демонстрации
        if test_model in config.GIGACHAT_MODELS['доступные']:
            print(f"   ✅ Модель {test_model} была бы установлена (сервис недоступен)")
        else:
            print(f"   ❌ Модель {test_model} недоступна")
    print()
    
    print("🎯 Функциональность готова!")
    print("💡 Для использования:")
    print("   1. Перейдите в админ панель: http://localhost:8005/admin")
    print("   2. Откройте вкладку '🤖 Модели'")
    print("   3. Выберите нужную модель из списка")
    print("   4. При наличии сертификатов GigaChat модель будет активирована")

if __name__ == "__main__":
    demo_models()
