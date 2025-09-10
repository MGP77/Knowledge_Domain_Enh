#!/bin/bash

# =============================================================================
# SberInfra Knowledge System - Production Run Script
# =============================================================================
# Полный скрипт установки, настройки и управления системой
# Поддерживает корпоративные среды с ограниченными правами
# =============================================================================

set -e  # Выход при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Настройки
APP_NAME="SberInfra Knowledge System"
APP_PORT=8005
APP_HOST="0.0.0.0"
PID_FILE="knowledge_system.pid"
LOG_FILE="knowledge_system.log"
REQUIREMENTS_FILE="requirements.txt"
PYTHON_CMD="python"

# Проверка Python
check_python() {
    echo -e "${BLUE}🔍 Проверка Python...${NC}"
    
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}❌ Python не найден! Установите Python 3.8+${NC}"
        exit 1
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
    echo -e "${GREEN}✅ Python найден: $PYTHON_VERSION${NC}"
}

# Проверка pip
check_pip() {
    echo -e "${BLUE}🔍 Проверка pip...${NC}"
    
    if ! command -v pip &> /dev/null; then
        if ! command -v pip3 &> /dev/null; then
            echo -e "${RED}❌ pip не найден! Установите pip${NC}"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}✅ pip найден${NC}"
}

# Проверка SQLite версии для ChromaDB
check_sqlite() {
    echo -e "${BLUE}🔍 Проверка SQLite для ChromaDB...${NC}"
    
    SQLITE_VERSION=$($PYTHON_CMD -c "import sqlite3; print(sqlite3.sqlite_version)" 2>/dev/null || echo "unknown")
    echo -e "${CYAN}📊 Текущая версия SQLite: $SQLITE_VERSION${NC}"
    
    # Проверяем версию SQLite (требуется >= 3.35.0)
    REQUIRED_VERSION="3.35.0"
    if $PYTHON_CMD -c "
import sqlite3
import sys
current = tuple(map(int, sqlite3.sqlite_version.split('.')))
required = tuple(map(int, '$REQUIRED_VERSION'.split('.')))
sys.exit(0 if current >= required else 1)
" 2>/dev/null; then
        echo -e "${GREEN}✅ SQLite версия поддерживается ChromaDB${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️ SQLite версия $SQLITE_VERSION < $REQUIRED_VERSION${NC}"
        echo -e "${YELLOW}📦 Будет установлена обновленная версия SQLite в виртуальном окружении${NC}"
        return 1
    fi
}

# Установка зависимостей
install_dependencies() {
    echo -e "${BLUE}📦 Установка зависимостей...${NC}"
    
    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        echo -e "${RED}❌ Файл $REQUIREMENTS_FILE не найден!${NC}"
        exit 1
    fi
    
    # Проверяем SQLite перед установкой ChromaDB
    if ! check_sqlite; then
        echo -e "${YELLOW}� Установка обновленного SQLite...${NC}"
        
        # Устанавливаем pysqlite3-binary для замены системного SQLite
        pip install pysqlite3-binary
        
        # Создаем патч для ChromaDB чтобы использовать pysqlite3
        echo -e "${YELLOW}🔧 Настройка ChromaDB для использования обновленного SQLite...${NC}"
        
        # Создаем __init__.py файл для патча SQLite
        mkdir -p ./sqlite_patch
        cat > ./sqlite_patch/__init__.py << 'EOF'
"""
Патч для замены sqlite3 на pysqlite3-binary в ChromaDB
Используется в корпоративных средах с устаревшими версиями SQLite
"""
# Заменяем системный sqlite3 на pysqlite3-binary
import sys
try:
    import pysqlite3 as sqlite3
    sys.modules['sqlite3'] = sqlite3
    print("✅ Используется обновленный SQLite через pysqlite3-binary")
except ImportError:
    import sqlite3
    print("⚠️ Используется системный SQLite")
EOF
        
        # Применяем патч перед импортом ChromaDB
        export PYTHONPATH="./sqlite_patch:$PYTHONPATH"
        
        echo -e "${GREEN}✅ SQLite патч применен${NC}"
    fi
    
    echo -e "${YELLOW}�📋 Устанавливаем пакеты из $REQUIREMENTS_FILE...${NC}"
    
    # Установка с обработкой ошибок
    if pip install -r "$REQUIREMENTS_FILE"; then
        echo -e "${GREEN}✅ Зависимости установлены успешно${NC}"
    else
        echo -e "${YELLOW}⚠️ Некоторые пакеты не установились, пробуем альтернативный метод...${NC}"
        
        # Попытка установки без строгих версий
        pip install --upgrade pip
        
        # Устанавливаем pysqlite3-binary перед ChromaDB
        pip install pysqlite3-binary
        
        # Основные пакеты
        pip install fastapi uvicorn jinja2 python-multipart requests pypdf2 python-docx beautifulsoup4 typing-extensions pydantic aiofiles python-dotenv websockets
        
        # ChromaDB с поддержкой обновленного SQLite
        pip install chromadb
        
        # Попытка установки GigaChat (может не сработать в корпоративной среде)
        pip install langchain-gigachat || echo -e "${YELLOW}⚠️ GigaChat не установлен - будет работать в ограниченном режиме${NC}"
        
        # Попытка установки python-magic (может не сработать)
        pip install python-magic || echo -e "${YELLOW}⚠️ python-magic не установлен - будет использован fallback${NC}"
        
        echo -e "${GREEN}✅ Основные зависимости установлены${NC}"
    fi
}

# Проверка конфигурации
check_config() {
    echo -e "${BLUE}⚙️ Проверка конфигурации...${NC}"
    
    # Создание .env файла если его нет
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            echo -e "${YELLOW}📝 Создание .env файла из примера...${NC}"
            cp .env.example .env
        else
            echo -e "${YELLOW}📝 Создание базового .env файла...${NC}"
            cat > .env << EOF
# Основные настройки
APP_NAME="SberInfra Knowledge System"
APP_VERSION="1.0.0"
HOST=0.0.0.0
PORT=8005
DEBUG=False

# Настройки GigaChat (опционально)
GIGACHAT_BASE_URL=https://gigachat.devices.sberbank.ru/api/v1
GIGACHAT_MODEL=GigaChat

# Настройки ChromaDB
CHROMA_DB_PATH=./storage/chroma_db

# Настройки логирования
LOG_LEVEL=INFO
EOF
        fi
        echo -e "${GREEN}✅ Файл .env создан${NC}"
    fi
    
    # Создание директорий
    mkdir -p storage/chroma_db
    mkdir -p storage/uploads
    
    echo -e "${GREEN}✅ Конфигурация готова${NC}"
}

# Проверка портов
check_port() {
    echo -e "${BLUE}🔌 Проверка порта $APP_PORT...${NC}"
    
    if lsof -Pi :$APP_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️ Порт $APP_PORT уже используется${NC}"
        PID=$(lsof -Pi :$APP_PORT -sTCP:LISTEN -t)
        echo -e "${YELLOW}PID процесса: $PID${NC}"
        
        read -p "Остановить процесс? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kill $PID || true
            sleep 2
        else
            echo -e "${RED}❌ Невозможно запустить на занятом порту${NC}"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}✅ Порт $APP_PORT свободен${NC}"
}

# Запуск сервиса
start_service() {
    echo -e "${BLUE}🚀 Запуск $APP_NAME...${NC}"
    
    check_port
    
    # Запуск в фоновом режиме
    nohup $PYTHON_CMD main.py > $LOG_FILE 2>&1 &
    SERVICE_PID=$!
    echo $SERVICE_PID > $PID_FILE
    
    echo -e "${GREEN}✅ Сервис запущен!${NC}"
    echo -e "${GREEN}📊 PID: $SERVICE_PID${NC}"
    echo -e "${GREEN}🌐 URL: http://localhost:$APP_PORT${NC}"
    echo -e "${GREEN}🖥️ Админ панель: http://localhost:$APP_PORT/admin${NC}"
    echo -e "${GREEN}📋 Логи: tail -f $LOG_FILE${NC}"
    
    # Ждем запуска
    echo -e "${YELLOW}⏳ Ждем запуска сервиса...${NC}"
    sleep 5
    
    # Проверяем что сервис запустился
    if kill -0 $SERVICE_PID 2>/dev/null; then
        echo -e "${GREEN}✅ Сервис работает!${NC}"
        
        # Проверяем доступность HTTP
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:$APP_PORT/ | grep -q "200"; then
            echo -e "${GREEN}🌐 HTTP сервер отвечает${NC}"
        else
            echo -e "${YELLOW}⚠️ HTTP сервер пока не отвечает, проверьте логи${NC}"
        fi
    else
        echo -e "${RED}❌ Ошибка запуска сервиса!${NC}"
        echo -e "${RED}📋 Проверьте логи: cat $LOG_FILE${NC}"
        exit 1
    fi
}

# Остановка сервиса
stop_service() {
    echo -e "${BLUE}🛑 Остановка сервиса...${NC}"
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        if kill -0 $PID 2>/dev/null; then
            echo -e "${YELLOW}🔄 Завершение процесса $PID...${NC}"
            kill $PID
            sleep 3
            
            # Если процесс все еще работает, принудительно завершаем
            if kill -0 $PID 2>/dev/null; then
                echo -e "${YELLOW}💀 Принудительное завершение...${NC}"
                kill -9 $PID
            fi
            
            echo -e "${GREEN}✅ Сервис остановлен${NC}"
        else
            echo -e "${YELLOW}⚠️ Процесс уже не работает${NC}"
        fi
        rm -f $PID_FILE
    else
        echo -e "${YELLOW}⚠️ PID файл не найден${NC}"
        
        # Пробуем найти и остановить по порту
        if lsof -Pi :$APP_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
            PID=$(lsof -Pi :$APP_PORT -sTCP:LISTEN -t)
            echo -e "${YELLOW}🔍 Найден процесс на порту $APP_PORT: $PID${NC}"
            kill $PID || kill -9 $PID
            echo -e "${GREEN}✅ Процесс остановлен${NC}"
        fi
    fi
}

# Перезапуск сервиса
restart_service() {
    echo -e "${BLUE}🔄 Перезапуск сервиса...${NC}"
    stop_service
    sleep 2
    start_service
}

# Статус сервиса
status_service() {
    echo -e "${BLUE}📊 Статус сервиса...${NC}"
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        if kill -0 $PID 2>/dev/null; then
            echo -e "${GREEN}✅ Сервис работает (PID: $PID)${NC}"
            echo -e "${GREEN}🌐 URL: http://localhost:$APP_PORT${NC}"
            
            # Проверяем HTTP доступность
            if command -v curl &> /dev/null; then
                if curl -s -o /dev/null -w "%{http_code}" http://localhost:$APP_PORT/ | grep -q "200"; then
                    echo -e "${GREEN}🌐 HTTP сервер отвечает${NC}"
                else
                    echo -e "${YELLOW}⚠️ HTTP сервер не отвечает${NC}"
                fi
            fi
            
            return 0
        else
            echo -e "${RED}❌ Процесс не найден${NC}"
            rm -f $PID_FILE
            return 1
        fi
    else
        echo -e "${RED}❌ Сервис не запущен${NC}"
        return 1
    fi
}

# Просмотр логов
show_logs() {
    echo -e "${BLUE}📋 Просмотр логов...${NC}"
    
    if [ -f "$LOG_FILE" ]; then
        if [ "$1" = "follow" ]; then
            echo -e "${YELLOW}📺 Слежение за логами (Ctrl+C для выхода):${NC}"
            tail -f $LOG_FILE
        else
            echo -e "${YELLOW}📄 Последние 50 строк логов:${NC}"
            tail -50 $LOG_FILE
        fi
    else
        echo -e "${RED}❌ Файл логов не найден${NC}"
    fi
}

# Полная установка
full_install() {
    echo -e "${PURPLE}🎯 Полная установка $APP_NAME${NC}"
    echo -e "${PURPLE}==========================================${NC}"
    
    check_python
    check_pip
    install_dependencies
    check_config
    
    echo -e "${GREEN}🎉 Установка завершена!${NC}"
    echo -e "${GREEN}Запустите сервис: $0 start${NC}"
}

# Показать помощь
show_help() {
    echo -e "${CYAN}🛠️ SberInfra Knowledge System - Управление${NC}"
    echo -e "${CYAN}==========================================${NC}"
    echo
    echo -e "${YELLOW}Использование: $0 {команда}${NC}"
    echo
    echo -e "${GREEN}📋 Доступные команды:${NC}"
    echo -e "  ${BLUE}install${NC}    - Полная установка системы"
    echo -e "  ${BLUE}start${NC}      - Запуск сервиса"
    echo -e "  ${BLUE}stop${NC}       - Остановка сервиса"
    echo -e "  ${BLUE}restart${NC}    - Перезапуск сервиса"
    echo -e "  ${BLUE}status${NC}     - Статус сервиса"
    echo -e "  ${BLUE}logs${NC}       - Просмотр логов"
    echo -e "  ${BLUE}logs-live${NC}  - Слежение за логами в реальном времени"
    echo -e "  ${BLUE}help${NC}       - Эта справка"
    echo
    echo -e "${GREEN}🌐 После запуска доступно:${NC}"
    echo -e "  • Главная страница: http://localhost:$APP_PORT"
    echo -e "  • Админ панель: http://localhost:$APP_PORT/admin"
    echo -e "  • Консоль логов: http://localhost:$APP_PORT/admin → вкладка 'Консоль'"
    echo
    echo -e "${GREEN}📋 Примеры использования:${NC}"
    echo -e "  $0 install     # Установить все зависимости"
    echo -e "  $0 start       # Запустить сервис"
    echo -e "  $0 logs-live   # Смотреть логи в реальном времени"
    echo
}

# Основная логика
case "${1:-help}" in
    install)
        full_install
        ;;
    start)
        if ! status_service >/dev/null 2>&1; then
            start_service
        else
            echo -e "${YELLOW}⚠️ Сервис уже запущен${NC}"
            status_service
        fi
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        status_service
        ;;
    logs)
        show_logs
        ;;
    logs-live)
        show_logs follow
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}❌ Неизвестная команда: $1${NC}"
        echo
        show_help
        exit 1
        ;;
esac
