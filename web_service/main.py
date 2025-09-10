#!/usr/bin/env python3
"""
Главное FastAPI приложение для web-сервиса с GigaChat и RAG

Copyright (c) 2025. All rights reserved.
Author: M.P.
"""

import os
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
                
                if rag_service.add_document(page['content'], metadata):
                    processed_count += 1
        
        logger.info(f"✅ Обработано {processed_count} страниц Confluence")
        
        return {
            "success": True,
            "message": f"Успешно обработано {processed_count} страниц",
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
        success = rag_service.add_document(
            processing_result['content'],
            processing_result['metadata']
        )
        
        if success:
            logger.info(f"✅ Файл {file.filename} успешно добавлен в базу знаний")
            return DocumentUploadResponse(
                filename=file.filename,
                size=len(file_content),
                status="success",
                message="Файл успешно обработан и добавлен в базу знаний",
                processed_chunks=1  # TODO: получить реальное количество чанков
            )
        else:
            return DocumentUploadResponse(
                filename=file.filename,
                size=len(file_content),
                status="error",
                message="Ошибка добавления в базу знаний. Проверьте настройки GigaChat."
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
            confluence_pages=0,  # TODO: подсчет Confluence страниц
            uploaded_files=0,    # TODO: подсчет загруженных файлов
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
