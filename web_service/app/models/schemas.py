#!/usr/bin/env python3
"""
Модели данных для web-сервиса

Copyright (c) 2025. All rights reserved.
Author: M.P.
"""

from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime

class ChatMessage(BaseModel):
    """Модель сообщения чата"""
    message: str
    use_rag: bool = True

class ChatResponse(BaseModel):
    """Модель ответа чата"""
    response: str
    sources: List[Dict[str, Any]] = []
    timestamp: datetime

class ConfluenceConfig(BaseModel):
    """Конфигурация для подключения к Confluence"""
    url: HttpUrl
    username: str
    password: str
    space_key: Optional[str] = None
    page_ids: Optional[List[str]] = None
    page_urls: Optional[List[str]] = None  # Прямые ссылки на страницы
    parse_levels: int = 1  # Количество уровней для парсинга (1-5)
    verify_ssl: bool = True  # Проверять SSL сертификаты

class ConfluenceParseRequest(BaseModel):
    """Запрос на парсинг Confluence"""
    config: ConfluenceConfig
    max_pages: int = 50
    include_attachments: bool = False
    parse_child_pages: bool = True  # Парсить дочерние страницы

class DocumentUploadResponse(BaseModel):
    """Ответ на загрузку документа"""
    filename: str
    size: int
    status: str
    message: str
    processed_chunks: int = 0

class RAGSearchResult(BaseModel):
    """Результат поиска в RAG базе"""
    text: str
    metadata: Dict[str, Any]
    score: float

class AdminStats(BaseModel):
    """Статистика для админ панели"""
    total_documents: int
    total_chunks: int
    confluence_pages: int
    uploaded_files: int
    last_update: Optional[datetime] = None
