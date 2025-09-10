#!/usr/bin/env python3
"""
Flask альтернатива для корпоративной среды (вместо FastAPI)

Copyright (c) 2025. All rights reserved.
Author: M.P.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
import logging
import os
import sys
from pathlib import Path
import json
from datetime import datetime

# Добавляем путь к модулям приложения
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Создаем Flask приложение
app = Flask(__name__)
CORS(app)

# Глобальные переменные для сервисов
gigachat_service = None
rag_service = None
confluence_service = None
file_service = None

def init_services():
    """Инициализация сервисов"""
    global gigachat_service, rag_service, confluence_service, file_service
    
    try:
        from config import config
        
        # Инициализация GigaChat сервиса
        try:
            from app.services.gigachat_service import GigaChatService
            gigachat_service = GigaChatService()
            logger.info("✅ GigaChat сервис инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации GigaChat: {e}")
        
        # Инициализация RAG сервиса  
        try:
            from app.services.rag_service import RAGService
            rag_service = RAGService()
            logger.info("✅ RAG сервис инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации RAG: {e}")
        
        # Инициализация Confluence сервиса
        try:
            from app.services.confluence_service import ConfluenceService
            confluence_service = ConfluenceService()
            logger.info("✅ Confluence сервис инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Confluence: {e}")
            
        # Инициализация File сервиса
        try:
            from app.services.file_service import FileProcessorService
            file_service = FileProcessorService()
            logger.info("✅ File сервис инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации File service: {e}")
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка инициализации: {e}")

@app.route('/')
def index():
    """Главная страница"""
    gigachat_available = gigachat_service is not None and gigachat_service.is_available()
    rag_available = rag_service is not None and rag_service.is_available()
    
    return render_template('index.html', 
                         app_name="SberInfra Knowledge System",
                         gigachat_available=gigachat_available,
                         rag_available=rag_available)

@app.route('/admin')
def admin():
    """Админ панель"""
    return render_template('admin.html',
                         app_name="SberInfra Knowledge System")

@app.route('/api/chat', methods=['POST'])
def chat():
    """API для чата с GigaChat"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        use_rag = data.get('use_rag', True)
        
        if not message:
            return jsonify({'error': 'Сообщение не может быть пустым'}), 400
        
        # Если GigaChat недоступен
        if not gigachat_service or not gigachat_service.is_available():
            return jsonify({
                'response': '⚠️ GigaChat недоступен. Проверьте настройки сертификатов.',
                'sources': [],
                'timestamp': datetime.now().isoformat()
            })
        
        # Получаем контекст из RAG если нужно
        context = ""
        sources = []
        
        if use_rag and rag_service and rag_service.is_available():
            try:
                search_results = rag_service.search(message, max_results=3)
                context = "\n".join([result['text'] for result in search_results])
                sources = [{'text': r['text'][:200] + '...', 'metadata': r['metadata']} 
                          for r in search_results]
            except Exception as e:
                logger.error(f"Ошибка RAG поиска: {e}")
        
        # Отправляем запрос в GigaChat
        try:
            response = gigachat_service.generate_response(message, context)
            
            return jsonify({
                'response': response,
                'sources': sources,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Ошибка GigaChat: {e}")
            return jsonify({
                'response': f'Ошибка при обращении к GigaChat: {str(e)}',
                'sources': [],
                'timestamp': datetime.now().isoformat()
            })
            
    except Exception as e:
        logger.error(f"Ошибка API чата: {e}")
        return jsonify({'error': f'Внутренняя ошибка сервера: {str(e)}'}), 500

@app.route('/api/admin/stats')
def stats():
    """Статистика системы"""
    try:
        gigachat_available = gigachat_service is not None and gigachat_service.is_available()
        rag_available = rag_service is not None and rag_service.is_available()
        
        # Получаем статистику RAG
        rag_stats = {}
        if rag_service:
            try:
                rag_stats = rag_service.get_statistics()
            except:
                rag_stats = {
                    'total_chunks': 0,
                    'unique_documents': 0,
                    'status': 'unavailable'
                }
        
        return jsonify({
            'gigachat_available': gigachat_available,
            'rag_available': rag_available,
            'total_documents': rag_stats.get('unique_documents', 0),
            'total_chunks': rag_stats.get('total_chunks', 0),
            'embedding_provider': rag_stats.get('embedding_provider', 'N/A'),
            'embedding_model': rag_stats.get('embedding_model', 'N/A')
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return jsonify({
            'gigachat_available': False,
            'rag_available': False,
            'total_documents': 0,
            'total_chunks': 0,
            'error': str(e)
        })

@app.route('/api/confluence/test', methods=['POST'])
def test_confluence():
    """Тестирование подключения к Confluence"""
    try:
        if not confluence_service:
            return jsonify({
                'success': False,
                'message': 'Confluence сервис недоступен'
            })
        
        data = request.get_json()
        
        # Создаем конфигурацию
        from app.models.schemas import ConfluenceConfig
        config = ConfluenceConfig(
            url=data['url'],
            username=data['username'],
            password=data['password']
        )
        
        result = confluence_service.test_connection(config)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Ошибка тестирования Confluence: {e}")
        return jsonify({
            'success': False,
            'message': f'Ошибка тестирования: {str(e)}'
        })

@app.errorhandler(404)
def not_found(error):
    """Обработчик 404 ошибки"""
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_error(error):
    """Обработчик 500 ошибки"""
    logger.error(f"Внутренняя ошибка сервера: {error}")
    return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

if __name__ == '__main__':
    print("🚀 Запуск SberInfra Knowledge System (Flask версия)")
    print("🏢 Корпоративная среда - используется альтернатива FastAPI")
    
    # Инициализируем сервисы
    init_services()
    
    # Запускаем Flask сервер
    port = int(os.environ.get('PORT', 8005))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    print(f"🌐 Сервер будет доступен по адресу: http://localhost:{port}")
    print("📝 Админ панель: http://localhost:{port}/admin")
    print("🔍 Для остановки нажмите Ctrl+C")
    
    app.run(host=host, port=port, debug=debug)
