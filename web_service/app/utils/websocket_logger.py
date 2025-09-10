"""
WebSocket логгер для вывода логов в реальном времени
"""

import logging
import asyncio
import json
from datetime import datetime
from typing import Set
from fastapi import WebSocket


class WebSocketHandler(logging.Handler):
    """Обработчик логов для WebSocket"""
    
    def __init__(self):
        super().__init__()
        self.connections: Set[WebSocket] = set()
        
    def add_connection(self, websocket: WebSocket):
        """Добавить WebSocket соединение"""
        self.connections.add(websocket)
        
    def remove_connection(self, websocket: WebSocket):
        """Удалить WebSocket соединение"""
        self.connections.discard(websocket)
        
    def emit(self, record):
        """Отправить лог сообщение в WebSocket"""
        if not self.connections:
            return
            
        try:
            log_entry = self.format(record)
            message = {
                "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
                "level": record.levelname,
                "logger": record.name,
                "message": log_entry,
                "module": getattr(record, 'module', ''),
                "funcName": getattr(record, 'funcName', ''),
                "lineno": getattr(record, 'lineno', 0)
            }
            
            # Асинхронная отправка сообщения всем подключенным клиентам
            asyncio.create_task(self._send_to_all(json.dumps(message)))
            
        except Exception as e:
            # Избегаем рекурсии логирования
            print(f"Ошибка в WebSocketHandler: {e}")
    
    async def _send_to_all(self, message: str):
        """Отправить сообщение всем подключенным WebSocket"""
        if not self.connections:
            return
            
        disconnected = set()
        
        for websocket in self.connections.copy():
            try:
                await websocket.send_text(message)
            except Exception:
                # Соединение разорвано
                disconnected.add(websocket)
        
        # Удаляем разорванные соединения
        for websocket in disconnected:
            self.connections.discard(websocket)


# Глобальный экземпляр WebSocket обработчика
websocket_handler = WebSocketHandler()

# Настройка форматирования
formatter = logging.Formatter(
    '[%(levelname)s] %(name)s: %(message)s'
)
websocket_handler.setFormatter(formatter)


def setup_websocket_logging():
    """Настройка WebSocket логирования"""
    
    # Добавляем обработчик к корневому логгеру
    root_logger = logging.getLogger()
    root_logger.addHandler(websocket_handler)
    
    # Добавляем к основным логгерам приложения
    app_loggers = [
        'main',
        'app.services.gigachat_service',
        'app.services.rag_service', 
        'app.services.confluence_service',
        'app.services.file_service',
        'uvicorn.access',
        'uvicorn.error'
    ]
    
    for logger_name in app_loggers:
        logger = logging.getLogger(logger_name)
        if websocket_handler not in logger.handlers:
            logger.addHandler(websocket_handler)


def get_websocket_handler():
    """Получить экземпляр WebSocket обработчика"""
    return websocket_handler
