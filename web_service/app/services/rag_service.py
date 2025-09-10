#!/usr/bin/env python3
"""
RAG сервис с поддержкой GigaChat эмбеддингов через langchain-gigachat

Copyright (c) 2025. All rights reserved.
Author: M.P.
"""

import os
import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
import uuid
import re

from config import config

logger = logging.getLogger(__name__)

class SimpleTextSplitter:
    """Простой text splitter без langchain"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def split_text(self, text: str) -> List[str]:
        """Разбивка текста на чанки"""
        if not text:
            return []
        
        chunks = []
        current_chunk = ""
        
        # Разбиваем текст на предложения
        sentences = re.split(r'[.!?]+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Если добавление предложения не превышает размер чанка
            if len(current_chunk) + len(sentence) <= self.chunk_size:
                current_chunk += sentence + ". "
            else:
                # Сохраняем текущий чанк
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # Начинаем новый чанк
                if len(sentence) <= self.chunk_size:
                    current_chunk = sentence + ". "
                else:
                    # Если предложение слишком длинное, разбиваем его
                    words = sentence.split()
                    temp_chunk = ""
                    for word in words:
                        if len(temp_chunk) + len(word) <= self.chunk_size:
                            temp_chunk += word + " "
                        else:
                            if temp_chunk:
                                chunks.append(temp_chunk.strip())
                            temp_chunk = word + " "
                    current_chunk = temp_chunk
        
        # Добавляем последний чанк
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks

class GigaChatEmbeddingsProvider:
    """Провайдер эмбеддингов через langchain-gigachat"""
    
    def __init__(self, model_name: str = "EmbeddingsGigaR"):
        self.model_name = model_name
        self.cert_path = config.MTLS_CLIENT_CERT
        self.key_path = config.MTLS_CLIENT_KEY
        self.verify_ssl = config.MTLS_VERIFY_SSL
        
        # Проверяем наличие сертификатов
        self.is_available = self._check_certificates()
        
        if self.is_available:
            try:
                from langchain_gigachat import GigaChatEmbeddings
                
                # Инициализируем GigaChat эмбеддинги
                self.embeddings = GigaChatEmbeddings(
                    model=model_name,
                    ca_bundle_file=None,  # Используем системные CA
                    cert_file=self.cert_path,
                    key_file=self.key_path,
                    verify_ssl_certs=self.verify_ssl
                )
                
                logger.info(f"✅ GigaChat эмбеддинги инициализированы (модель: {model_name})")
                
            except ImportError as e:
                logger.warning(f"langchain-gigachat не установлен: {e}")
                self.is_available = False
            except Exception as e:
                logger.error(f"Ошибка инициализации GigaChat эмбеддингов: {e}")
                self.is_available = False
    
    def _check_certificates(self) -> bool:
        """Проверка доступности сертификатов"""
        try:
            if not os.path.exists(self.cert_path) or not os.path.exists(self.key_path):
                return False
            
            # Проверяем содержимое сертификатов
            with open(self.cert_path, 'r') as f:
                cert_content = f.read()
                if "# Certificate Placeholder" in cert_content:
                    return False
            
            with open(self.key_path, 'r') as f:
                key_content = f.read()
                if "# Private Key Placeholder" in key_content:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Получение эмбеддингов для списка текстов"""
        if not self.is_available:
            raise ValueError("GigaChat эмбеддинги недоступны - проверьте сертификаты")
        
        try:
            # Используем embed_documents для множественных текстов
            embeddings = self.embeddings.embed_documents(texts)
            return embeddings
        except Exception as e:
            logger.error(f"Ошибка получения эмбеддингов GigaChat: {e}")
            return []
    
    def get_query_embedding(self, query: str) -> List[float]:
        """Получение эмбеддинга для поискового запроса"""
        if not self.is_available:
            raise ValueError("GigaChat эмбеддинги недоступны - проверьте сертификаты")
        
        try:
            # Используем embed_query для запросов (оптимизировано для поиска)
            embedding = self.embeddings.embed_query(query)
            return embedding
        except Exception as e:
            logger.error(f"Ошибка получения эмбеддинга запроса GigaChat: {e}")
            return []

class RAGService:
    """Сервис для работы с векторной базой данных и GigaChat эмбеддингами"""
    
    def __init__(self):
        self.client = None
        self.collection = None
        self.text_splitter = None
        self.embedding_provider = None
        self.is_available = False
        self._initialize()
    
    def _initialize(self):
        """Инициализация Chroma и embedding провайдера"""
        try:
            # Создаем директорию для Chroma если не существует
            os.makedirs(config.CHROMA_DB_PATH, exist_ok=True)
            
            # Инициализация Chroma
            self.client = chromadb.PersistentClient(
                path=config.CHROMA_DB_PATH,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Получаем или создаем коллекцию
            self.collection = self.client.get_or_create_collection(
                name=config.CHROMA_COLLECTION_NAME,
                metadata={"description": "Knowledge base for RAG"}
            )
            
            # Инициализация text splitter
            self.text_splitter = SimpleTextSplitter(
                chunk_size=config.CHUNK_SIZE,
                chunk_overlap=config.CHUNK_OVERLAP
            )
            
            # Выбираем провайдера эмбеддингов
            self._initialize_embedding_provider()
            
            if self.embedding_provider:
                self.is_available = True
                logger.info("✅ RAG сервис успешно инициализирован")
                logger.info(f"📊 Документов в базе: {self.collection.count()}")
                logger.info(f"🔧 Провайдер эмбеддингов: {type(self.embedding_provider).__name__}")
            else:
                logger.warning("⚠️ Ни один провайдер эмбеддингов недоступен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации RAG сервиса: {e}")
            self.is_available = False
    
    def _initialize_embedding_provider(self):
        """Инициализация провайдера эмбеддингов"""
        # Используем только GigaChat эмбеддинги
        gigachat_provider = GigaChatEmbeddingsProvider(
            model_name=getattr(config, 'GIGACHAT_EMBEDDING_MODEL', 'EmbeddingsGigaR')
        )
        
        if gigachat_provider.is_available:
            self.embedding_provider = gigachat_provider
            logger.info("🔧 Используем GigaChat эмбеддинги")
        else:
            logger.error("❌ GigaChat эмбеддинги недоступны - проверьте сертификаты")
            self.embedding_provider = None
    
    def check_availability(self) -> bool:
        """Проверка доступности RAG сервиса"""
        return self.is_available and self.collection is not None and self.embedding_provider is not None
    
    def add_document(self, content: str, metadata: Dict[str, Any]) -> bool:
        """Добавление документа в RAG базу"""
        if not self.check_availability():
            logger.error("RAG сервис недоступен")
            return False
        
        try:
            # Разбиваем текст на чанки
            chunks = self.text_splitter.split_text(content)
            
            if not chunks:
                logger.warning("Не удалось разбить текст на чанки")
                return False
            
            # Получаем эмбеддинги для всех чанков
            chunk_texts = [chunk for chunk in chunks if chunk.strip()]
            if not chunk_texts:
                logger.warning("Нет валидных чанков")
                return False
            
            embeddings = self.embedding_provider.get_embeddings(chunk_texts)
            if not embeddings or len(embeddings) != len(chunk_texts):
                logger.error("Не удалось получить эмбеддинги для всех чанков")
                return False
            
            # Подготавливаем данные для добавления
            documents = []
            metadatas = []
            ids = []
            chunk_embeddings = []
            
            for i, (chunk, embedding) in enumerate(zip(chunk_texts, embeddings)):
                # Генерируем уникальный ID
                chunk_id = str(uuid.uuid4())
                
                # Создаем метаданные для чанка
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    "chunk_index": i,
                    "chunk_size": len(chunk),
                    "total_chunks": len(chunk_texts)
                })
                
                documents.append(chunk)
                metadatas.append(chunk_metadata)
                ids.append(chunk_id)
                chunk_embeddings.append(embedding)
            
            # Добавляем в коллекцию
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=chunk_embeddings
            )
            
            logger.info(f"✅ Добавлено {len(documents)} чанков из документа '{metadata.get('title', 'Без названия')}'")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка добавления документа: {e}")
            return False
    
    def search(self, query: str, n_results: Optional[int] = None) -> List[Dict[str, Any]]:
        """Поиск по RAG базе"""
        if not self.check_availability():
            logger.error("RAG сервис недоступен")
            return []
        
        if n_results is None:
            n_results = config.MAX_SEARCH_RESULTS
        
        try:
            # Получаем эмбеддинг для запроса
            query_embedding = self.embedding_provider.get_query_embedding(query)
            if not query_embedding:
                logger.error("Не удалось получить эмбеддинг для запроса")
                return []
            
            # Выполняем поиск
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, self.collection.count()),
                include=["documents", "metadatas", "distances"]
            )
            
            # Форматируем результаты
            formatted_results = []
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'score': 1 - results['distances'][0][i]  # Преобразуем distance в score
                })
            
            logger.info(f"🔍 Найдено {len(formatted_results)} результатов для запроса: '{query[:50]}...'")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики RAG базы"""
        if not self.check_availability():
            return {
                "total_documents": 0,
                "status": "unavailable",
                "embedding_provider": "none"
            }
        
        try:
            count = self.collection.count()
            
            # Получаем дополнительную статистику
            all_metadata = self.collection.get(include=["metadatas"])
            
            # Подсчитываем уникальные документы
            unique_sources = set()
            for metadata in all_metadata['metadatas']:
                source = metadata.get('source', 'unknown')
                unique_sources.add(source)
            
            return {
                "total_chunks": count,
                "unique_documents": len(unique_sources),
                "status": "available",
                "embedding_provider": type(self.embedding_provider).__name__,
                "embedding_model": getattr(self.embedding_provider, 'model_name', 'GigaChat')
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {
                "total_documents": 0,
                "status": "error",
                "error": str(e),
                "embedding_provider": "error"
            }
    
    def clear_database(self) -> bool:
        """Очистка RAG базы"""
        if not self.check_availability():
            return False
        
        try:
            # Удаляем коллекцию
            self.client.delete_collection(config.CHROMA_COLLECTION_NAME)
            
            # Создаем новую
            self.collection = self.client.get_or_create_collection(
                name=config.CHROMA_COLLECTION_NAME,
                metadata={"description": "Knowledge base for RAG"}
            )
            
            logger.info("✅ RAG база данных очищена")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка очистки базы данных: {e}")
            return False
