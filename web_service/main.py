#!/usr/bin/env python3
"""
Главное FastAPI приложение для web-сервиса с GigaChat и RAG

Copyright (c) 2025. All rights reserved.
Author: M.P.
"""

# ВАЖНО: Обходное решение для SQLite в корпоративных средах
# Это решает проблему с устаревшими версиями SQLite без внешних зависимостей
import sys
import os
import warnings

# Подавляем предупреждения о версии SQLite
warnings.filterwarnings("ignore", message=".*sqlite3.*version.*")
warnings.filterwarnings("ignore", message=".*SQLite.*version.*")
warnings.filterwarnings("ignore", category=UserWarning, module="chromadb")

# Проверяем переменную обхода SQLite
if os.getenv('CHROMA_SQLITE_OVERRIDE') == '1':
    print("🔧 Активирован режим обхода проверки SQLite для корпоративной среды")
    
    # Monkey patch для обхода проверки версии SQLite в ChromaDB
    try:
        import sqlite3
        original_version = sqlite3.sqlite_version
        
        # Перезаписываем версию SQLite для обмана ChromaDB
        sqlite3.sqlite_version = "3.35.0"
        sqlite3.version = "2.6.0"
        
        print(f"✅ SQLite версия изменена: {original_version} -> {sqlite3.sqlite_version}")
        
        # Дополнительно патчим sqlite3.sqlite_version_info если есть
        if hasattr(sqlite3, 'sqlite_version_info'):
            sqlite3.sqlite_version_info = (3, 35, 0)
            
    except Exception as e:
        print(f"⚠️ Ошибка применения SQLite патча: {e}")
        print("🔄 Продолжаем без патча...")

import json
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Импорты сервисов
from app.services.gigachat_service import GigaChatService
from app.services.rag_service import RAGService
from app.services.confluence_service import ConfluenceService
from app.services.file_service import FileProcessorService

# Импорты утилит
from app.utils.websocket_logger import setup_websocket_logging, get_websocket_handler

# Импорты моделей
from app.models.schemas import (
    ChatMessage, ChatResponse, ConfluenceConfig, 
    ConfluenceParseRequest, DocumentUploadResponse, AdminStats
)

from config import config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Создание FastAPI приложения
app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description="Web-сервис с GigaChat и RAG базой знаний"
)

# Добавление CORS middleware для корпоративных сред
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене укажите конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация сервисов
gigachat_service = GigaChatService()
rag_service = RAGService()
confluence_service = ConfluenceService()
file_service = FileProcessorService()

# Настройка статических файлов и шаблонов
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Middleware для безопасных заголовков (корпоративная среда)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@app.on_event("startup")
async def startup_event():
    """События при запуске приложения"""
    # Настройка WebSocket логирования
    setup_websocket_logging()
    
    logger.info("🚀 Запуск web-сервиса...")
    logger.info(f"📊 GigaChat доступен: {gigachat_service.check_availability()}")
    logger.info(f"📊 RAG сервис доступен: {rag_service.check_availability()}")
    
    # Создаем необходимые директории
    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

# =============================================================================
# HEALTH ENDPOINTS (для диагностики в корпоративной среде)
# =============================================================================

@app.get("/health")
async def simple_health():
    """Простой health check для корпоративных сред"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# =============================================================================
# WEB PAGES
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Главная страница с чатом"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "app_name": config.APP_NAME,
        "gigachat_available": gigachat_service.check_availability(),
        "rag_available": rag_service.check_availability()
    })

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    """Админ панель"""
    stats = await get_admin_stats()
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "app_name": config.APP_NAME,
        "stats": stats.dict()
    })

@app.get("/manual", response_class=HTMLResponse)
async def manual_page(request: Request):
    """Руководство пользователя"""
    return templates.TemplateResponse("manual_ru.html", {
        "request": request,
        "app_name": config.APP_NAME
    })

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(message: ChatMessage):
    """Эндпоинт для чата с GigaChat"""
    try:
        logger.info(f"💬 Получен вопрос: {message.message[:100]}...")
        
        # Проверяем доступность GigaChat
        if not gigachat_service.check_availability():
            raise HTTPException(
                status_code=503, 
                detail="GigaChat сервис недоступен"
            )
        
        context = ""
        sources = []
        
        # Если включен RAG, ищем в базе знаний
        if message.use_rag and rag_service.check_availability():
            search_results = rag_service.search(message.message)
            if search_results:
                # Формируем контекст из найденных документов
                context_parts = []
                for result in search_results:
                    context_parts.append(result['text'])
                    sources.append({
                        'text': result['text'][:200] + "...",
                        'metadata': result['metadata'],
                        'score': result['score']
                    })
                
                context = "\n\n".join(context_parts)
                logger.info(f"🔍 Найдено {len(search_results)} релевантных документов")
        
        # Получаем ответ от GigaChat
        response_text = await gigachat_service.chat_with_context(message.message, context)
        
        return ChatResponse(
            response=response_text,
            sources=sources,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в чате: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/confluence/test")
async def test_confluence_connection(config_data: ConfluenceConfig):
    """Тестирование подключения к Confluence"""
    try:
        result = confluence_service.test_connection(config_data)
        return result
    except Exception as e:
        logger.error(f"Ошибка тестирования Confluence: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/confluence/parse")
async def parse_confluence(request: ConfluenceParseRequest):
    """Парсинг страниц Confluence и добавление в RAG"""
    try:
        if not rag_service.check_availability():
            raise HTTPException(
                status_code=503,
                detail="RAG сервис недоступен"
            )
        
        logger.info("📥 Начинаем парсинг Confluence...")
        
        # Парсим страницы
        pages = confluence_service.parse_confluence_pages(
            request.config, 
            request.max_pages
        )
        
        if not pages:
            return {
                "success": False,
                "message": "Не удалось получить страницы из Confluence",
                "processed_pages": 0
            }
        
        # Добавляем в RAG базу
        processed_count = 0
        chunks_added = 0
        for page in pages:
            if page['content']:
                metadata = {
                    'source': 'confluence',
                    'page_id': page['id'],
                    'title': page['title'],
                    'space_key': page['space_key'],
                    'space_name': page['space_name'],
                    'url': page['url'],
                    'version': page['version'],
                    'author': page['author'],
                    'last_modified': page['last_modified']
                }
                
                add_result = rag_service.add_document(page['content'], metadata)
                if add_result["success"]:
                    processed_count += 1
                    chunks_added += add_result["chunks_added"]
        
        logger.info(f"✅ Обработано {processed_count} страниц Confluence ({chunks_added} чанков)")
        
        return {
            "success": True,
            "message": f"Успешно обработано {processed_count} страниц ({chunks_added} чанков)",
            "processed_pages": processed_count,
            "total_found": len(pages)
        }
        
    except Exception as e:
        logger.error(f"Ошибка парсинга Confluence: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload", response_model=DocumentUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Загрузка и обработка файла"""
    try:
        logger.info(f"📁 Загружен файл: {file.filename}")
        
        # Проверяем доступность RAG сервиса
        if not rag_service.check_availability():
            logger.warning("⚠️ RAG сервис недоступен - файл будет обработан, но не добавлен в базу")
            return DocumentUploadResponse(
                filename=file.filename,
                size=0,
                status="warning",
                message="RAG сервис недоступен. Проверьте настройки GigaChat и сертификаты. Файл не может быть добавлен в базу знаний.",
                processed_chunks=0
            )
        
        # Читаем содержимое файла
        file_content = await file.read()
        
        # Проверяем размер файла
        if len(file_content) == 0:
            return DocumentUploadResponse(
                filename=file.filename,
                size=0,
                status="error",
                message="Файл пустой или не может быть прочитан"
            )
        
        # Сохраняем файл
        file_path = file_service.save_uploaded_file(file_content, file.filename)
        
        # Обрабатываем файл
        processing_result = file_service.process_file(file_path)
        
        if not processing_result['success']:
            return DocumentUploadResponse(
                filename=file.filename,
                size=len(file_content),
                status="error",
                message=f"Ошибка обработки файла: {processing_result['error']}"
            )
        
        # Добавляем в RAG базу
        add_result = rag_service.add_document(
            processing_result['content'],
            processing_result['metadata']
        )
        
        if add_result["success"]:
            logger.info(f"✅ Файл {file.filename} успешно добавлен в базу знаний ({add_result['chunks_added']} чанков)")
            return DocumentUploadResponse(
                filename=file.filename,
                size=len(file_content),
                status="success",
                message=f"Файл успешно обработан и добавлен в базу знаний ({add_result['chunks_added']} чанков)",
                processed_chunks=add_result["chunks_added"]
            )
        else:
            error_msg = add_result.get("error", "Неизвестная ошибка")
            return DocumentUploadResponse(
                filename=file.filename,
                size=len(file_content),
                status="error",
                message=f"Ошибка добавления в базу знаний: {error_msg}",
                processed_chunks=0
            )
        
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки файла {file.filename}: {e}")
        return DocumentUploadResponse(
            filename=file.filename if file.filename else "unknown",
            size=0,
            status="error",
            message=f"Критическая ошибка: {str(e)}"
        )

@app.get("/api/admin/stats", response_model=AdminStats)
async def get_admin_stats():
    """Получение статистики для админ панели"""
    try:
        rag_stats = rag_service.get_stats()
        
        return AdminStats(
            total_documents=rag_stats.get('unique_documents', 0),
            total_chunks=rag_stats.get('total_chunks', 0),
            confluence_pages=rag_stats.get('confluence_pages', 0),
            uploaded_files=rag_stats.get('uploaded_files', 0),
            last_update=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/models")
async def get_available_models():
    """Получение списка доступных моделей GigaChat"""
    try:
        models = gigachat_service.get_available_models()
        current_model = gigachat_service.get_current_model()
        
        return {
            "models": models,
            "current_model": current_model,
            "available": gigachat_service.check_availability()
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения списка моделей: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/models/set")
async def set_model(model_name: str = Form(...)):
    """Установка активной модели GigaChat"""
    try:
        if not gigachat_service.check_availability():
            raise HTTPException(
                status_code=503,
                detail="GigaChat сервис недоступен"
            )
        
        success = gigachat_service.set_model(model_name)
        
        if success:
            return {
                "success": True,
                "message": f"Модель {model_name} установлена",
                "current_model": gigachat_service.get_current_model()
            }
        else:
            return {
                "success": False,
                "message": f"Ошибка установки модели {model_name}"
            }
            
    except Exception as e:
        logger.error(f"Ошибка установки модели: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/admin/clear-db")
async def clear_database():
    """Очистка RAG базы данных"""
    try:
        if not rag_service.check_availability():
            raise HTTPException(
                status_code=503,
                detail="RAG сервис недоступен"
            )
        
        success = rag_service.clear_database()
        
        if success:
            return {"success": True, "message": "База данных очищена"}
        else:
            return {"success": False, "message": "Ошибка очистки базы данных"}
            
    except Exception as e:
        logger.error(f"Ошибка очистки базы данных: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# MAINTENANCE AND DIAGNOSTICS API ENDPOINTS
# =============================================================================

@app.post("/api/admin/diagnostics")
async def run_diagnostics():
    """Полная диагностика системы"""
    try:
        # Проверяем ChromaDB
        chromadb_status = "OK" if rag_service.check_availability() else "ERROR"
        chromadb_info = {"status": chromadb_status}
        
        # Получаем размер базы данных
        try:
            import os
            db_path = config.CHROMA_DB_PATH
            if os.path.exists(db_path):
                size_bytes = sum(os.path.getsize(os.path.join(dirpath, filename))
                               for dirpath, dirnames, filenames in os.walk(db_path)
                               for filename in filenames)
                chromadb_info["size_mb"] = round(size_bytes / (1024 * 1024), 2)
            else:
                chromadb_info["size_mb"] = 0.0
        except Exception:
            chromadb_info["size_mb"] = 0.0
        
        # Проверяем embedding сервис  
        embedding_basic_check = gigachat_service.check_availability()
        embedding_test_result = gigachat_service.test_embeddings("Тестовый запрос")
        
        if embedding_test_result.get("success", False):
            embedding_status = "OK"
            embedding_error = None
        else:
            embedding_status = "ERROR"
            embedding_error = embedding_test_result.get("error", "Неизвестная ошибка")
        
        embedding_info = {
            "status": embedding_status,
            "model": config.GIGACHAT_EMBEDDING_MODEL,
            "basic_available": embedding_basic_check,
            "error": embedding_error
        }
        
        # Получаем статистику документов
        stats = rag_service.get_statistics()
        documents_info = {
            "total": stats.get("total_documents", 0),
            "chunks": stats.get("total_chunks", 0)
        }
        
        # Формируем рекомендации
        recommendations = []
        if chromadb_status != "OK":
            recommendations.append("Проверьте доступность ChromaDB")
        if embedding_status != "OK":
            if embedding_error:
                recommendations.append(f"Проверьте настройки GigaChat Embeddings: {embedding_error}")
            else:
                recommendations.append("Проверьте настройки GigaChat Embeddings")
        
        db_size = chromadb_info.get("size_mb", 0.0)
        if isinstance(db_size, (int, float)) and db_size > 500:
            recommendations.append("Рассмотрите создание резервной копии базы данных")
        if documents_info["total"] == 0:
            recommendations.append("Загрузите документы в систему")
        
        return {
            "success": True,
            "data": {
                "chromadb": chromadb_info,
                "embedding": embedding_info,
                "documents": documents_info,
                "recommendations": recommendations
            }
        }
        
    except Exception as e:
        logger.error(f"Ошибка диагностики: {e}")
        return {"success": False, "message": f"Ошибка диагностики: {str(e)}"}

@app.get("/api/admin/embedding-health")
async def check_embedding_health():
    """Проверка здоровья embedding провайдера"""
    try:
        start_time = datetime.now()
        
        # Проверяем базовую доступность
        basic_available = gigachat_service.check_availability()
        
        # Тестируем embedding
        test_result = gigachat_service.test_embeddings("Тестовый запрос для проверки")
        
        end_time = datetime.now()
        response_time = int((end_time - start_time).total_seconds() * 1000)
        
        if test_result.get("success", False):
            vector_dimensions = len(test_result.get("embedding", []))
            
            return {
                "success": True,
                "data": {
                    "model": config.GIGACHAT_EMBEDDING_MODEL,
                    "response_time": response_time,
                    "vector_dimensions": vector_dimensions,
                    "status": "healthy",
                    "basic_available": basic_available
                }
            }
        else:
            error_details = test_result.get("error", "Неизвестная ошибка")
            return {
                "success": False,
                "message": f"Embedding провайдер недоступен: {error_details}",
                "data": {
                    "basic_available": basic_available,
                    "response_time": response_time,
                    "error": error_details,
                    "model": config.GIGACHAT_EMBEDDING_MODEL
                }
            }
        
    except Exception as e:
        logger.error(f"Ошибка проверки embedding: {e}")
        return {"success": False, "message": f"Ошибка: {str(e)}"}

@app.get("/api/admin/gigachat-debug")
async def debug_gigachat():
    """Подробная диагностика GigaChat для отладки"""
    try:
        debug_info = {
            "client_initialized": gigachat_service.client is not None,
            "mtls_cert_path": config.MTLS_CLIENT_CERT,
            "mtls_key_path": config.MTLS_CLIENT_KEY,
            "embedding_model": config.GIGACHAT_EMBEDDING_MODEL,
            "base_url": config.GIGACHAT_BASE_URL,
            "mtls_verify_ssl": config.MTLS_VERIFY_SSL
        }
        
        # Проверяем сертификаты
        import os
        cert_path = config.MTLS_CLIENT_CERT
        key_path = config.MTLS_CLIENT_KEY
        
        debug_info["cert_file_exists"] = os.path.exists(cert_path)
        debug_info["key_file_exists"] = os.path.exists(key_path)
        
        if debug_info["cert_file_exists"]:
            debug_info["cert_file_size"] = os.path.getsize(cert_path)
        if debug_info["key_file_exists"]:
            debug_info["key_file_size"] = os.path.getsize(key_path)
        
        # Тестируем базовую доступность
        debug_info["basic_availability"] = gigachat_service.check_availability()
        
        # Тестируем embedding с подробностями
        if debug_info["basic_availability"]:
            test_result = gigachat_service.test_embeddings("Тест")
            debug_info["embedding_test"] = test_result
        else:
            debug_info["embedding_test"] = {"success": False, "error": "Базовая проверка не прошла"}
        
        return {"success": True, "debug_info": debug_info}
        
    except Exception as e:
        logger.error(f"Ошибка отладки GigaChat: {e}")
        return {"success": False, "message": f"Ошибка отладки: {str(e)}"}

@app.get("/api/admin/validate-db")
async def validate_database():
    """Валидация базы данных ChromaDB"""
    try:
        if not rag_service.check_availability():
            return {"success": False, "message": "ChromaDB недоступна"}
        
        # Получаем статистику
        stats = rag_service.get_statistics()
        
        # Проверяем размер базы данных
        import os
        db_path = config.CHROMA_DB_PATH
        size_mb = 0.0
        if os.path.exists(db_path):
            size_bytes = sum(os.path.getsize(os.path.join(dirpath, filename))
                           for dirpath, dirnames, filenames in os.walk(db_path)
                           for filename in filenames)
            size_mb = round(size_bytes / (1024 * 1024), 2)
        
        # Проверяем коллекции
        collections_count = 1  # У нас одна коллекция по умолчанию
        
        return {
            "success": True,
            "data": {
                "collections_count": collections_count,
                "documents_count": stats.get("total_documents", 0),
                "index_status": "Автоматический (HNSW)",
                "size_mb": size_mb,
                "chunks_count": stats.get("total_chunks", 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Ошибка валидации БД: {e}")
        return {"success": False, "message": f"Ошибка валидации: {str(e)}"}

@app.get("/api/admin/maintenance-check")
async def check_maintenance_needs():
    """Проверка потребностей обслуживания"""
    try:
        # Простая проверка без импорта внешнего модуля
        # ChromaDB автоматически управляет индексами
        
        # Проверяем размер базы
        import os
        db_path = config.CHROMA_DB_PATH
        size_mb = 0.0
        if os.path.exists(db_path):
            size_bytes = sum(os.path.getsize(os.path.join(dirpath, filename))
                           for dirpath, dirnames, filenames in os.walk(db_path)
                           for filename in filenames)
            size_mb = round(size_bytes / (1024 * 1024), 2)
        
        # Формируем результат
        result = {
            "reindexing_needed": False,
            "automatic_optimization": True,
            "maintenance_type": "monitoring_only",
            "recommendations": "ChromaDB автоматически управляет индексами. Ре-индексация не требуется.",
            "database_size_mb": size_mb
        }
        
        if size_mb > 500:
            result["recommendations"] += " База данных большая - рекомендуется создание резервных копий."
        
        return {"success": True, "data": result}
        
    except Exception as e:
        logger.error(f"Ошибка проверки обслуживания: {e}")
        return {"success": False, "message": f"Ошибка: {str(e)}"}

@app.get("/api/admin/export-metadata")
async def export_database_metadata():
    """Экспорт метаданных базы данных"""
    try:
        if not rag_service.check_availability():
            return {"success": False, "message": "RAG сервис недоступен"}
        
        # Получаем статистику
        stats = rag_service.get_statistics()
        
        # Формируем метаданные
        metadata = {
            "export_date": datetime.now().isoformat(),
            "database_stats": stats,
            "configuration": {
                "chunk_size": config.CHUNK_SIZE,
                "chunk_overlap": config.CHUNK_OVERLAP,
                "embedding_model": config.GIGACHAT_EMBEDDING_MODEL,
                "max_search_results": config.MAX_SEARCH_RESULTS
            },
            "system_info": {
                "app_version": config.APP_VERSION,
                "db_path": config.CHROMA_DB_PATH
            }
        }
        
        return {"success": True, "data": metadata}
        
    except Exception as e:
        logger.error(f"Ошибка экспорта метаданных: {e}")
        return {"success": False, "message": f"Ошибка экспорта: {str(e)}"}

@app.get("/api/admin/document-sources")
async def get_document_sources():
    """Получение информации об источниках документов"""
    try:
        if not rag_service.check_availability():
            return {"success": False, "message": "RAG сервис недоступен"}
        
        # Получаем статистику по источникам
        sources_info = rag_service.get_sources_statistics()
        
        # Формируем ответ
        sources = []
        
        confluence_count = sources_info.get("confluence_pages", 0)
        if confluence_count > 0:
            sources.append({
                "source_type": "Confluence",
                "count": confluence_count,
                "details": f"Страницы из различных пространств"
            })
        
        uploaded_count = sources_info.get("uploaded_files", 0)
        if uploaded_count > 0:
            sources.append({
                "source_type": "Загруженные файлы",
                "count": uploaded_count,
                "details": f"PDF, DOCX, TXT файлы"
            })
        
        if not sources:
            sources.append({
                "source_type": "Нет источников",
                "count": 0,
                "details": "Документы не загружены"
            })
        
        return {"success": True, "data": {"sources": sources}}
        
    except Exception as e:
        logger.error(f"Ошибка получения источников: {e}")
        return {"success": False, "message": f"Ошибка: {str(e)}"}

@app.get("/api/admin/chunk-analysis")
async def analyze_chunk_distribution():
    """Анализ распределения фрагментов"""
    try:
        if not rag_service.check_availability():
            return {"success": False, "message": "RAG сервис недоступен"}
        
        # Получаем анализ фрагментов
        analysis = rag_service.analyze_chunks()
        
        return {"success": True, "data": analysis}
        
    except Exception as e:
        logger.error(f"Ошибка анализа фрагментов: {e}")
        return {"success": False, "message": f"Ошибка анализа: {str(e)}"}

@app.get("/api/admin/embedding-compatibility")
async def check_embedding_compatibility():
    """Проверка совместимости размерности эмбеддингов"""
    try:
        compatibility = rag_service.check_embedding_dimension_compatibility()
        return {"success": True, "data": compatibility}
    except Exception as e:
        logger.error(f"Ошибка проверки совместимости эмбеддингов: {e}")
        return {"success": False, "message": f"Ошибка: {str(e)}"}

@app.post("/api/admin/migrate-embeddings")
async def migrate_embeddings(force: bool = False):
    """Миграция эмбеддингов при изменении размерности"""
    try:
        logger.info(f"🔄 Запрос миграции эмбеддингов (force={force})")
        
        migration_result = rag_service.migrate_embedding_dimensions(force=force)
        
        if migration_result.get("success"):
            logger.info("✅ Миграция эмбеддингов завершена успешно")
        else:
            logger.warning(f"⚠️ Миграция не выполнена: {migration_result.get('message')}")
        
        return {"success": True, "data": migration_result}
        
    except Exception as e:
        logger.error(f"Ошибка миграции эмбеддингов: {e}")
        return {"success": False, "message": f"Ошибка миграции: {str(e)}"}

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint для получения логов в реальном времени"""
    await websocket.accept()
    
    # Получаем WebSocket обработчик
    ws_handler = get_websocket_handler()
    
    # Добавляем соединение
    ws_handler.add_connection(websocket)
    
    try:
        logger.info("🔌 Новое WebSocket соединение для логов")
        
        # Отправляем приветственное сообщение
        welcome_msg = {
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "level": "INFO",
            "logger": "websocket",
            "message": "🔌 WebSocket соединение установлено. Ожидание логов...",
            "module": "",
            "funcName": "",
            "lineno": 0
        }
        await websocket.send_text(json.dumps(welcome_msg))
        
        # Держим соединение открытым
        while True:
            try:
                # Ожидаем сообщения от клиента (пинг)
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Ошибка в WebSocket: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info("🔌 WebSocket соединение закрыто")
    except Exception as e:
        logger.error(f"Ошибка WebSocket логов: {e}")
    finally:
        # Удаляем соединение
        ws_handler.remove_connection(websocket)

@app.get("/api/health")
async def health_check():
    """Проверка состояния сервисов"""
    return {
        "status": "ok",
        "services": {
            "gigachat": gigachat_service.check_availability(),
            "rag": rag_service.check_availability()
        },
        "timestamp": datetime.now()
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG
    )
