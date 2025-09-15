#!/usr/bin/env python3
"""
Адаптированный GigaChat клиент для web-сервиса

Copyright (c) 2025. All rights reserved.
Author: M.P.
"""

import os
import requests
import json
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime

from config import config

logger = logging.getLogger(__name__)

class GigaChatService:
    """Сервис для работы с GigaChat"""
    
    def __init__(self):
        self.client = None
        self.is_available = False
        self.base_url = config.GIGACHAT_BASE_URL
        self.cert_path = config.MTLS_CLIENT_CERT
        self.key_path = config.MTLS_CLIENT_KEY
        self.verify_ssl = config.MTLS_VERIFY_SSL
        self._initialize_client()
    
    def _initialize_client(self):
        """Инициализация клиента GigaChat"""
        try:
            # Проверяем наличие сертификатов
            if not os.path.exists(self.cert_path) or not os.path.exists(self.key_path):
                logger.warning(f"❌ Сертификаты GigaChat не найдены: {self.cert_path}, {self.key_path}")
                return
            
            # Проверяем содержимое сертификатов
            with open(self.cert_path, 'r') as f:
                cert_content = f.read()
                if "# Certificate Placeholder" in cert_content:
                    logger.warning("⚠️ Обнаружен файл-заглушка сертификата")
                    return
            
            with open(self.key_path, 'r') as f:
                key_content = f.read()
                if "# Private Key Placeholder" in key_content:
                    logger.warning("⚠️ Обнаружен файл-заглушка ключа")
                    return
            
            self.is_available = True
            logger.info("✅ GigaChat клиент успешно инициализирован")
            logger.info(f"🔗 Базовый URL: {self.base_url}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации GigaChat: {e}")
            self.is_available = False
    
    def check_availability(self) -> bool:
        """Проверка доступности GigaChat"""
        return self.is_available
    
    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Выполнение запроса к GigaChat API"""
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            
            response = requests.post(
                url,
                json=data,
                cert=(self.cert_path, self.key_path),
                verify=self.verify_ssl,
                timeout=60,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"GigaChat API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка запроса к GigaChat: {e}")
            return None
    
    async def chat_with_context(self, message: str, context: str = "") -> str:
        """
        Отправка сообщения в GigaChat с контекстом
        
        Args:
            message: Сообщение пользователя
            context: Контекст из RAG базы
            
        Returns:
            Ответ от GigaChat
        """
        if not self.check_availability():
            return "❌ GigaChat недоступен. Проверьте настройки аутентификации."
        
        try:
            # Формируем промпт с контекстом
            if context:
                prompt = f"""Контекст из базы знаний:
{context}

Вопрос пользователя: {message}

Ответь на вопрос, используя предоставленный контекст. Если информация в контексте недостаточна, так и скажи. Отвечай на русском языке и используй markdown форматирование для лучшей читаемости."""
            else:
                prompt = f"Вопрос: {message}\n\nОтветь на русском языке, используя markdown форматирование."
            
            # Подготавливаем данные для запроса
            request_data = {
                "model": config.DEFAULT_GIGACHAT_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": config.CHAT_TEMPERATURE,
                "max_tokens": config.CHAT_MAX_TOKENS
            }
            
            # Отправляем запрос к GigaChat
            response = self._make_request("chat/completions", request_data)
            
            if response and 'choices' in response and len(response['choices']) > 0:
                return response['choices'][0]['message']['content']
            else:
                return "❌ Получен некорректный ответ от GigaChat"
                
        except Exception as e:
            logger.error(f"Ошибка при обращении к GigaChat: {e}")
            return f"❌ Ошибка при обращении к GigaChat: {str(e)}"
    
    async def simple_chat(self, message: str) -> str:
        """
        Простой чат без контекста RAG
        
        Args:
            message: Сообщение пользователя
            
        Returns:
            Ответ от GigaChat
        """
        return await self.chat_with_context(message, "")
    
    def get_available_models(self) -> List[Dict[str, str]]:
        """Получение списка доступных моделей"""
        if not self.check_availability():
            return []
        
        models_info = []
        for model in config.GIGACHAT_MODELS["доступные"]:
            model_info = {
                "name": model,
                "display_name": self._get_model_display_name(model),
                "description": self._get_model_description(model),
                "is_default": model == config.GIGACHAT_MODELS["по_умолчанию"]
            }
            models_info.append(model_info)
        
        return models_info
    
    def _get_model_display_name(self, model_name: str) -> str:
        """Получение отображаемого имени модели"""
        display_names = {
            "GigaChat-2": "GigaChat 2",
            "GigaChat-2-Pro": "GigaChat 2 Pro", 
            "GigaChat-2-Max": "GigaChat 2 Max"
        }
        return display_names.get(model_name, model_name)
    
    def _get_model_description(self, model_name: str) -> str:
        """Получение описания модели"""
        descriptions = {
            "GigaChat-2": "Базовая модель для повседневных задач",
            "GigaChat-2-Pro": "Усовершенствованная модель для сложных задач и аналитики",
            "GigaChat-2-Max": "Максимально мощная модель для самых сложных запросов"
        }
        return descriptions.get(model_name, "Модель GigaChat")
    
    def set_model(self, model_name: str) -> bool:
        """Установка активной модели"""
        if model_name not in config.GIGACHAT_MODELS["доступные"]:
            logger.warning(f"❌ Неизвестная модель: {model_name}")
            return False
        
        config.DEFAULT_GIGACHAT_MODEL = model_name
        logger.info(f"✅ Установлена модель: {model_name}")
        return True
    
    def get_current_model(self) -> str:
        """Получение текущей модели"""
        if not self.check_availability():
            return "Недоступно"
        
        return config.DEFAULT_GIGACHAT_MODEL

    def test_embeddings(self, text: str) -> Dict[str, Any]:
        """Тестирование embedding провайдера"""
        try:
            if not self.client:
                return {"success": False, "error": "Клиент не инициализирован"}
            
            # Тестовый запрос к embedding API
            data = {
                "model": config.GIGACHAT_EMBEDDING_MODEL,
                "input": [text]
            }
            
            response = self._make_request("embeddings", data)
            
            if response and "data" in response and len(response["data"]) > 0:
                embedding = response["data"][0]["embedding"]
                return {
                    "success": True,
                    "embedding": embedding,
                    "model": config.GIGACHAT_EMBEDDING_MODEL
                }
            else:
                return {
                    "success": False,
                    "error": "Некорректный ответ от API"
                }
                
        except Exception as e:
            logger.error(f"Ошибка тестирования embeddings: {e}")
            return {
                "success": False,
                "error": str(e)
            }
