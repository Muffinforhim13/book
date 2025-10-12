#!/bin/bash

# Скрипт для автоматического развертывания BookAI Bot на сервер
# Использование: ./deploy.sh [production|staging]

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для вывода
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка аргументов
ENVIRONMENT=${1:-production}
if [[ "$ENVIRONMENT" != "production" && "$ENVIRONMENT" != "staging" ]]; then
    log_error "Неверное окружение. Используйте 'production' или 'staging'"
    exit 1
fi

log_info "Начинаем развертывание в окружении: $ENVIRONMENT"

# Проверка наличия необходимых файлов
if [[ ! -f "main.py" ]]; then
    log_error "Файл main.py не найден. Убедитесь, что вы находитесь в корневой директории проекта."
    exit 1
fi

if [[ ! -f "requirements.txt" ]]; then
    log_error "Файл requirements.txt не найден."
    exit 1
fi

# Создание резервной копии
log_info "Создание резервной копии..."
if [[ -f "bookai.db" ]]; then
    BACKUP_NAME="bookai_backup_$(date +%Y%m%d_%H%M%S).db"
    cp bookai.db "$BACKUP_NAME"
    log_success "Резервная копия создана: $BACKUP_NAME"
fi

# Остановка сервисов
log_info "Остановка сервисов..."
if command -v supervisorctl &> /dev/null; then
    sudo supervisorctl stop bookai-bot 2>/dev/null || true
    sudo supervisorctl stop bookai-admin 2>/dev/null || true
    log_success "Сервисы остановлены"
fi

# Обновление зависимостей Python
log_info "Обновление зависимостей Python..."
if [[ -d "venv" ]]; then
    source venv/bin/activate
else
    log_info "Создание виртуального окружения..."
    python3 -m venv venv
    source venv/bin/activate
fi

pip install --upgrade pip
pip install -r requirements.txt
log_success "Зависимости Python обновлены"

# Настройка админ-панели
log_info "Настройка админ-панели..."
if [[ -d "admin_frontend" ]]; then
    cd admin_frontend
    
    # Установка зависимостей Node.js
    if [[ ! -d "node_modules" ]]; then
        log_info "Установка зависимостей Node.js..."
        npm install
    else
        log_info "Обновление зависимостей Node.js..."
        npm install
    fi
    
    # Сборка для продакшена
    log_info "Сборка frontend..."
    npm run build
    
    cd ..
    log_success "Админ-панель настроена"
else
    log_warning "Директория admin_frontend не найдена, пропускаем настройку frontend"
fi

# Проверка переменных окружения
log_info "Проверка переменных окружения..."
if [[ ! -f ".env" ]]; then
    log_error "Файл .env не найден. Создайте его на основе .env.example"
    exit 1
fi

# Проверка базы данных
log_info "Проверка базы данных..."
if [[ ! -f "bookai.db" ]]; then
    log_info "База данных не найдена, создаем новую..."
    python -c "from db import init_db; init_db()" 2>/dev/null || log_warning "Не удалось инициализировать базу данных"
fi

# Настройка прав доступа
log_info "Настройка прав доступа..."
sudo chown -R www-data:www-data /var/www/bookai-bot 2>/dev/null || true
sudo chmod -R 755 /var/www/bookai-bot
sudo chmod 664 bookai.db 2>/dev/null || true

# Создание директорий для загрузок
mkdir -p uploads covers
sudo chown -R www-data:www-data uploads covers 2>/dev/null || true

# Обновление конфигурации supervisor
log_info "Обновление конфигурации supervisor..."
if command -v supervisorctl &> /dev/null; then
    sudo supervisorctl reread
    sudo supervisorctl update
    log_success "Конфигурация supervisor обновлена"
fi

# Запуск сервисов
log_info "Запуск сервисов..."
if command -v supervisorctl &> /dev/null; then
    sudo supervisorctl start bookai-bot
    sudo supervisorctl start bookai-admin
    
    # Проверка статуса
    sleep 3
    sudo supervisorctl status
    
    log_success "Сервисы запущены"
else
    log_warning "Supervisor не найден. Запустите сервисы вручную:"
    echo "source venv/bin/activate"
    echo "python main.py &"
    echo "python admin_backend/main.py &"
fi

# Проверка nginx
log_info "Проверка nginx..."
if command -v nginx &> /dev/null; then
    sudo nginx -t
    sudo systemctl reload nginx
    log_success "Nginx перезагружен"
else
    log_warning "Nginx не найден"
fi

# Финальная проверка
log_info "Проверка работоспособности..."
sleep 5

# Проверка процессов
if pgrep -f "main.py" > /dev/null; then
    log_success "Бот запущен"
else
    log_error "Бот не запущен"
fi

if pgrep -f "admin_backend/main.py" > /dev/null; then
    log_success "Админ-панель запущена"
else
    log_warning "Админ-панель не запущена"
fi

log_success "Развертывание завершено успешно!"
log_info "Проверьте логи для диагностики:"
echo "  sudo tail -f /var/log/bookai-bot.out.log"
echo "  sudo tail -f /var/log/bookai-admin.out.log"
echo "  sudo supervisorctl status"

