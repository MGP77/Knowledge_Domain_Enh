#!/usr/bin/env python3
"""
Конфигурационный файл для web-сервиса с GigaChat и RAG

Copyright (c) 2025. All rights reserved.
Author: M.P.
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

class Config:
    """Конфигурация web-сервиса"""
    
    # Основные настройки
    APP_NAME = "GigaChat RAG Web Service"
    APP_VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # Сервер
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8005))
    
    # GigaChat настройки - только mTLS
    GIGACHAT_BASE_URL = "https://gigachat-ift.sberdevices.delta.sbrf.ru/v1"
    GIGACHAT_SCOPE = "GIGACHAT_API_CORP"
    
    # Настройки mTLS сертификатов
    MTLS_CLIENT_CERT = os.getenv("MTLS_CLIENT_CERT", "../certificates/cert.pem")
    MTLS_CLIENT_KEY = os.getenv("MTLS_CLIENT_KEY", "../certificates/key.pem")
    MTLS_VERIFY_SSL = os.getenv("MTLS_VERIFY_SSL", "false").lower() == "true"
    
    # Модели GigaChat
    DEFAULT_GIGACHAT_MODEL = "GigaChat-2"
    FALLBACK_MODEL = "GigaChat"
    
    # GigaChat Embeddings
    GIGACHAT_EMBEDDING_MODEL = os.getenv("GIGACHAT_EMBEDDING_MODEL", "EmbeddingsGigaR")  # или "Embeddings"
    
    # Chroma настройки
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./storage/chroma_db")
    CHROMA_COLLECTION_NAME = "knowledge_base"
    
    # Настройки RAG
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1024))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))
    MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", 5))
    
    # Confluence настройки
    CONFLUENCE_TIMEOUT = int(os.getenv("CONFLUENCE_TIMEOUT", 30))
    
    # Загрузка файлов
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "./storage/uploads")
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 50 * 1024 * 1024))  # 50MB
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'txt'}
    
    # Настройки чата
    CHAT_TEMPERATURE = float(os.getenv("CHAT_TEMPERATURE", 0.3))
    CHAT_MAX_TOKENS = int(os.getenv("CHAT_MAX_TOKENS", 2000))
    
    # Безопасность
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

# Создаем экземпляр конфигурации
config = Config()
