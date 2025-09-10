#!/usr/bin/env python3
"""
Тест новых функций Confluence парсинга

Copyright (c) 2025. All rights reserved.
Author: M.P.
"""

from app.services.confluence_service import ConfluenceService
from app.models.schemas import ConfluenceConfig

def test_url_extraction():
    """Тест извлечения ID страниц из различных URL"""
    print("🧪 Тестирование извлечения ID страниц из URL...")
    
    service = ConfluenceService()
    
    test_urls = [
        "https://company.atlassian.net/wiki/pages/viewpage.action?pageId=123456",
        "https://company.atlassian.net/wiki/spaces/PROJ/pages/789012/Page+Title",
        "https://company.atlassian.net/wiki/display/PROJ/Another+Page"
    ]
    
    for url in test_urls:
        page_id = service.extract_page_id_from_url(url)
        print(f"  URL: {url}")
        print(f"  Извлечённый ID: {page_id}")
        print()

def demo_confluence_config():
    """Демонстрация новой конфигурации Confluence"""
    print("📋 Демонстрация новой конфигурации Confluence...")
    
    # Пример конфигурации с прямыми URL
    config_with_urls = ConfluenceConfig(
        url="https://company.atlassian.net/wiki",
        username="user@company.com",
        password="api_token_here",
        page_urls=[
            "https://company.atlassian.net/wiki/pages/viewpage.action?pageId=123456",
            "https://company.atlassian.net/wiki/spaces/PROJ/pages/789012/Page+Title"
        ],
        parse_levels=3  # Парсим 3 уровня вглубь
    )
    
    print("✅ Конфигурация с прямыми URL:")
    print(f"  URL: {config_with_urls.url}")
    print(f"  Прямые ссылки: {len(config_with_urls.page_urls)} URL")
    print(f"  Уровни парсинга: {config_with_urls.parse_levels}")
    print()
    
    # Пример конфигурации с Space Key
    config_with_space = ConfluenceConfig(
        url="https://company.atlassian.net/wiki",
        username="user@company.com", 
        password="api_token_here",
        space_key="PROJ",
        parse_levels=2  # Парсим основные страницы + 1 уровень дочерних
    )
    
    print("✅ Конфигурация с пространством:")
    print(f"  Space Key: {config_with_space.space_key}")
    print(f"  Уровни парсинга: {config_with_space.parse_levels}")
    print()

def show_features():
    """Показать новые возможности"""
    print("🎉 Новые возможности системы:")
    print()
    
    print("1. 🎨 Зелёный логотип SberInfra:")
    print("   - Стильный SVG логотип с градиентом")
    print("   - Отображается на всех страницах")
    print("   - Брендинг корпоративной системы")
    print()
    
    print("2. 🔗 Поддержка прямых ссылок на страницы Confluence:")
    print("   - URL формата: /pages/viewpage.action?pageId=123456")
    print("   - URL формата: /spaces/SPACE/pages/123456/Title")
    print("   - URL формата: /display/SPACE/Page+Title")
    print("   - Автоматическое извлечение ID страниц")
    print()
    
    print("3. 📊 Многоуровневый парсинг:")
    print("   - От 1 до 5 уровней вложенности")
    print("   - Автоматический поиск дочерних страниц")
    print("   - Умная обработка иерархии контента")
    print()
    
    print("4. 🎯 Гибкая конфигурация:")
    print("   - Комбинирование Space Key + URL + Page IDs")
    print("   - Настройка глубины парсинга")
    print("   - Обработка дубликатов страниц")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 ДЕМОНСТРАЦИЯ НОВЫХ ФУНКЦИЙ CONFLUENCE ПАРСИНГА")
    print("=" * 60)
    print()
    
    show_features()
    test_url_extraction()
    demo_confluence_config()
    
    print("🎯 Запустите веб-сервис и откройте http://localhost:8005")
    print("   для тестирования нового интерфейса!")
