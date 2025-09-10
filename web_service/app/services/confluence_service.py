#!/usr/bin/env python3
"""
Сервис для парсинга Confluence страниц

Copyright (c) 2025. All rights reserved.
Author: M.P.
"""

import logging
import requests
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import time
import urllib.parse
import os
import ssl
import urllib3

from ..models.schemas import ConfluenceConfig
from config import config

logger = logging.getLogger(__name__)

class ConfluenceService:
    """Сервис для работы с Confluence"""
    
    def __init__(self):
        self.session = requests.Session()
        self.timeout = config.CONFLUENCE_TIMEOUT
        
        # Настройка для корпоративной среды
        self._setup_corporate_environment()
    
    def _setup_corporate_environment(self):
        """Настройка для работы в корпоративной среде"""
        try:
            # Проверяем переменные окружения для SSL
            ssl_verify = os.getenv('CONFLUENCE_SSL_VERIFY', 'true').lower()
            ca_bundle = os.getenv('CONFLUENCE_CA_BUNDLE', None)
            
            if ssl_verify == 'false':
                # Отключаем проверку SSL для корпоративных сред
                self.session.verify = False
                # Отключаем предупреждения urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                logger.warning("⚠️ SSL проверка отключена для корпоративной среды")
            elif ca_bundle and os.path.exists(ca_bundle):
                # Используем корпоративные сертификаты
                self.session.verify = ca_bundle
                logger.info(f"✅ Используются корпоративные сертификаты: {ca_bundle}")
            else:
                # Пытаемся найти системные сертификаты
                possible_ca_paths = [
                    '/etc/ssl/certs/ca-certificates.crt',  # Ubuntu/Debian
                    '/etc/ssl/certs/ca-bundle.crt',        # CentOS/RHEL
                    '/etc/pki/tls/certs/ca-bundle.crt',    # RHEL/Fedora
                    '/System/Library/OpenSSL/certs/cert.pem'  # macOS
                ]
                
                for ca_path in possible_ca_paths:
                    if os.path.exists(ca_path):
                        self.session.verify = ca_path
                        logger.info(f"✅ Найдены системные сертификаты: {ca_path}")
                        break
                else:
                    # Если ничего не найдено, отключаем SSL для корпоративной среды
                    logger.warning("⚠️ Сертификаты не найдены, отключаем SSL проверку")
                    self.session.verify = False
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # Настройка retry стратегии для корпоративных сетей
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
            
            # Настройка headers для корпоративных прокси
            self.session.headers.update({
                'User-Agent': 'Knowledge-Domain-Enhancement/1.0',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            })
            
        except Exception as e:
            logger.error(f"❌ Ошибка настройки корпоративной среды: {e}")
            # Fallback - отключаем SSL проверку
            self.session.verify = False
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logger.warning("⚠️ Используется fallback конфигурация с отключенным SSL")
    
    def _configure_ssl_for_request(self, confluence_config: ConfluenceConfig):
        """Настройка SSL для конкретного запроса на основе конфигурации"""
        if hasattr(confluence_config, 'verify_ssl') and not confluence_config.verify_ssl:
            # Пользователь явно отключил SSL проверку через UI
            self.session.verify = False
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logger.warning("⚠️ SSL проверка отключена пользователем")
        elif not hasattr(confluence_config, 'verify_ssl'):
            # Для обратной совместимости - если поле отсутствует, используем настройки по умолчанию
            pass
    
    def _clean_html_content(self, html_content: str) -> str:
        """Очистка HTML контента и извлечение текста"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Удаляем скрипты и стили
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Извлекаем текст
            text = soup.get_text()
            
            # Очищаем от лишних пробелов и переносов
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            logger.error(f"Ошибка очистки HTML: {e}")
            return html_content
    
    def test_connection(self, confluence_config: ConfluenceConfig) -> Dict[str, Any]:
        """
        Тестирование подключения к Confluence
        
        Args:
            confluence_config: Конфигурация Confluence
            
        Returns:
            Dict с результатом тестирования
        """
        try:
            # Настраиваем SSL для этого запроса
            self._configure_ssl_for_request(confluence_config)
            
            # Подготавливаем URL для тестирования
            base_url = str(confluence_config.url).rstrip('/')
            test_url = f"{base_url}/rest/api/content"
            
            # Настраиваем аутентификацию
            auth = HTTPBasicAuth(confluence_config.username, confluence_config.password)
            
            # Выполняем тестовый запрос
            response = self.session.get(
                test_url,
                auth=auth,
                params={'limit': 1},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'message': 'Подключение успешно',
                    'total_pages': data.get('size', 0)
                }
            elif response.status_code == 401:
                return {
                    'success': False,
                    'message': 'Ошибка аутентификации. Проверьте логин и пароль.'
                }
            elif response.status_code == 403:
                return {
                    'success': False,
                    'message': 'Доступ запрещен. Проверьте права доступа.'
                }
            else:
                return {
                    'success': False,
                    'message': f'Ошибка HTTP {response.status_code}: {response.text}'
                }
                
        except Exception as e:
            logger.error(f"Ошибка тестирования подключения: {e}")
            return {
                'success': False,
                'message': f'Ошибка подключения: {str(e)}'
            }
    
    def extract_page_id_from_url(self, page_url: str) -> Optional[str]:
        """
        Извлечение ID страницы из URL
        
        Args:
            page_url: URL страницы Confluence
            
        Returns:
            ID страницы или None
        """
        try:
            # Обработка различных форматов URL Confluence
            # Формат 1: /pages/viewpage.action?pageId=123456
            if 'pageId=' in page_url:
                return page_url.split('pageId=')[1].split('&')[0]
            
            # Формат 2: /display/SPACE/Page+Title (требует дополнительного запроса)
            if '/display/' in page_url:
                return self._get_page_id_by_display_url(page_url)
            
            # Формат 3: /spaces/SPACE/pages/123456/Page+Title
            if '/pages/' in page_url:
                parts = page_url.split('/pages/')
                if len(parts) > 1:
                    return parts[1].split('/')[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка извлечения ID страницы из URL {page_url}: {e}")
            return None
    
    def _get_page_id_by_display_url(self, display_url: str) -> Optional[str]:
        """Получение ID страницы по display URL через API"""
        try:
            # Извлекаем space key и title из URL
            parts = display_url.split('/display/')
            if len(parts) < 2:
                return None
            
            space_and_title = parts[1].split('/')
            if len(space_and_title) < 2:
                return None
            
            space_key = space_and_title[0]
            title = urllib.parse.unquote(space_and_title[1].replace('+', ' '))
            
            # Поиск страницы по title и space
            base_url = str(display_url).split('/display/')[0]
            url = f"{base_url}/rest/api/content"
            params = {
                'spaceKey': space_key,
                'title': title,
                'type': 'page',
                'status': 'current'
            }
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                if results:
                    return results[0]['id']
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения ID страницы по display URL: {e}")
            return None

    def get_child_pages(self, confluence_config: ConfluenceConfig, 
                       page_id: str, levels: int = 1) -> List[str]:
        """
        Получение дочерних страниц с заданным количеством уровней
        
        Args:
            confluence_config: Конфигурация Confluence
            page_id: ID родительской страницы
            levels: Количество уровней для парсинга (1-5)
            
        Returns:
            Список ID дочерних страниц
        """
        try:
            if levels <= 0 or levels > 5:
                return []
            
            base_url = str(confluence_config.url).rstrip('/')
            auth = HTTPBasicAuth(confluence_config.username, confluence_config.password)
            
            all_child_pages = []
            current_level_pages = [page_id]
            
            for level in range(levels):
                next_level_pages = []
                
                for current_page_id in current_level_pages:
                    url = f"{base_url}/rest/api/content/{current_page_id}/child/page"
                    params = {
                        'limit': 100,
                        'expand': 'version'
                    }
                    
                    response = self.session.get(url, auth=auth, params=params, timeout=self.timeout)
                    
                    if response.status_code == 200:
                        data = response.json()
                        child_pages = data.get('results', [])
                        
                        for child_page in child_pages:
                            child_id = child_page['id']
                            all_child_pages.append(child_id)
                            next_level_pages.append(child_id)
                        
                        time.sleep(0.1)  # Задержка для избежания rate limiting
                
                current_level_pages = next_level_pages
                
                if not current_level_pages:
                    break
            
            return all_child_pages
            
        except Exception as e:
            logger.error(f"Ошибка получения дочерних страниц для {page_id}: {e}")
            return []

    def get_pages_from_space(self, confluence_config: ConfluenceConfig, 
                           space_key: str, max_pages: int = 50) -> List[Dict[str, Any]]:
        """
        Получение списка страниц из пространства
        
        Args:
            confluence_config: Конфигурация Confluence
            space_key: Ключ пространства
            max_pages: Максимальное количество страниц
            
        Returns:
            List страниц
        """
        try:
            base_url = str(confluence_config.url).rstrip('/')
            auth = HTTPBasicAuth(confluence_config.username, confluence_config.password)
            
            pages = []
            start = 0
            limit = min(25, max_pages)  # Confluence API лимит
            
            while len(pages) < max_pages:
                url = f"{base_url}/rest/api/content"
                params = {
                    'spaceKey': space_key,
                    'type': 'page',
                    'status': 'current',
                    'start': start,
                    'limit': limit,
                    'expand': 'version,space'
                }
                
                response = self.session.get(url, auth=auth, params=params, timeout=self.timeout)
                
                if response.status_code != 200:
                    logger.error(f"Ошибка получения страниц: {response.status_code}")
                    break
                
                data = response.json()
                batch_pages = data.get('results', [])
                
                if not batch_pages:
                    break
                
                pages.extend(batch_pages)
                
                if len(batch_pages) < limit:
                    break
                    
                start += limit
                
                # Задержка между запросами
                time.sleep(0.5)
            
            return pages[:max_pages]
            
        except Exception as e:
            logger.error(f"Ошибка получения страниц из пространства: {e}")
            return []
    
    def get_page_content(self, confluence_config: ConfluenceConfig, 
                        page_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение контента страницы
        
        Args:
            confluence_config: Конфигурация Confluence
            page_id: ID страницы
            
        Returns:
            Dict с контентом страницы или None
        """
        try:
            base_url = str(confluence_config.url).rstrip('/')
            auth = HTTPBasicAuth(confluence_config.username, confluence_config.password)
            
            url = f"{base_url}/rest/api/content/{page_id}"
            params = {
                'expand': 'body.storage,version,space,ancestors'
            }
            
            response = self.session.get(url, auth=auth, params=params, timeout=self.timeout)
            
            if response.status_code != 200:
                logger.error(f"Ошибка получения страницы {page_id}: {response.status_code}")
                return None
            
            data = response.json()
            
            # Извлекаем HTML контент
            html_content = data.get('body', {}).get('storage', {}).get('value', '')
            
            # Конвертируем в чистый текст
            text_content = self._clean_html_content(html_content)
            
            # Формируем метаданные
            space = data.get('space', {})
            version = data.get('version', {})
            
            # Построение иерархии страниц
            breadcrumbs = []
            for ancestor in data.get('ancestors', []):
                breadcrumbs.append(ancestor.get('title', ''))
            
            return {
                'id': data.get('id'),
                'title': data.get('title', ''),
                'content': text_content,
                'html_content': html_content,
                'space_key': space.get('key', ''),
                'space_name': space.get('name', ''),
                'version': version.get('number', 1),
                'url': f"{base_url}/pages/viewpage.action?pageId={page_id}",
                'breadcrumbs': breadcrumbs,
                'last_modified': version.get('when', ''),
                'author': version.get('by', {}).get('displayName', '')
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения контента страницы {page_id}: {e}")
            return None
    
    def parse_confluence_pages(self, confluence_config: ConfluenceConfig, 
                             max_pages: int = 50) -> List[Dict[str, Any]]:
        """
        Расширенный парсинг страниц Confluence с поддержкой URL и уровней
        
        Args:
            confluence_config: Конфигурация Confluence
            max_pages: Максимальное количество страниц
            
        Returns:
            List обработанных страниц
        """
        processed_pages = []
        all_page_ids = set()
        
        try:
            # Настраиваем SSL для этого запроса
            self._configure_ssl_for_request(confluence_config)
            
            # 1. Обработка прямых URL страниц
            if confluence_config.page_urls:
                logger.info(f"Обработка прямых URL: {len(confluence_config.page_urls)} ссылок")
                for page_url in confluence_config.page_urls:
                    page_id = self.extract_page_id_from_url(page_url)
                    if page_id:
                        all_page_ids.add(page_id)
                        logger.info(f"Извлечён ID {page_id} из URL: {page_url}")
                        
                        # Получаем дочерние страницы если нужно
                        if confluence_config.parse_levels > 1:
                            child_ids = self.get_child_pages(
                                confluence_config, 
                                page_id, 
                                confluence_config.parse_levels - 1
                            )
                            all_page_ids.update(child_ids)
                            logger.info(f"Найдено {len(child_ids)} дочерних страниц для {page_id}")
                    else:
                        logger.warning(f"Не удалось извлечь ID из URL: {page_url}")
            
            # 2. Обработка конкретных ID страниц
            if confluence_config.page_ids:
                logger.info(f"Обработка указанных ID: {confluence_config.page_ids}")
                for page_id in confluence_config.page_ids:
                    all_page_ids.add(page_id)
                    
                    # Получаем дочерние страницы если нужно
                    if confluence_config.parse_levels > 1:
                        child_ids = self.get_child_pages(
                            confluence_config, 
                            page_id, 
                            confluence_config.parse_levels - 1
                        )
                        all_page_ids.update(child_ids)
                        logger.info(f"Найдено {len(child_ids)} дочерних страниц для {page_id}")
            
            # 3. Обработка пространства (space_key)
            if confluence_config.space_key:
                logger.info(f"Получение страниц из пространства: {confluence_config.space_key}")
                pages = self.get_pages_from_space(
                    confluence_config, 
                    confluence_config.space_key, 
                    max_pages
                )
                
                for page in pages:
                    all_page_ids.add(page['id'])
                    
                    # Для каждой страницы из space получаем дочерние если нужно
                    if confluence_config.parse_levels > 1:
                        child_ids = self.get_child_pages(
                            confluence_config, 
                            page['id'], 
                            confluence_config.parse_levels - 1
                        )
                        all_page_ids.update(child_ids)
            
            # 4. Получение контента всех найденных страниц
            if not all_page_ids:
                logger.warning("Не найдено ни одной страницы для обработки")
                return []
            
            logger.info(f"Начинаем обработку {len(all_page_ids)} уникальных страниц")
            
            for i, page_id in enumerate(list(all_page_ids)[:max_pages]):
                logger.info(f"Обработка страницы {i+1}/{min(len(all_page_ids), max_pages)}: {page_id}")
                
                page_content = self.get_page_content(confluence_config, page_id)
                if page_content:
                    processed_pages.append(page_content)
                    logger.info(f"✅ Страница {page_id} обработана: '{page_content['title']}'")
                else:
                    logger.warning(f"❌ Не удалось получить контент страницы {page_id}")
                
                # Задержка между запросами для избежания rate limiting
                time.sleep(0.5)
            
            logger.info(f"🎉 Успешно обработано {len(processed_pages)} страниц Confluence")
            return processed_pages
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга Confluence: {e}")
            return processed_pages
