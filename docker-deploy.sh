#!/bin/bash

# Скрипт для развертывания BookAI Bot в Docker
# Использование: ./docker-deploy.sh [production|staging]

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

log_info "Начинаем развертывание в Docker окружении: $ENVIRONMENT"

# Проверка наличия Docker и Docker Compose
if ! command -v docker &> /dev/null; then
    log_error "Docker не установлен. Установите Docker и попробуйте снова."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose не установлен. Установите Docker Compose и попробуйте снова."
    exit 1
fi

# Проверка наличия необходимых файлов
if [[ ! -f "docker-compose.yml" ]]; then
    log_error "Файл docker-compose.yml не найден."
    exit 1
fi

if [[ ! -f "requirements.txt" ]]; then
    log_error "Файл requirements.txt не найден."
    exit 1
fi

# Проверка переменных окружения
log_info "Проверка переменных окружения..."
if [[ ! -f ".env" ]]; then
    log_error "Файл .env не найден. Создайте его на основе env_example.txt"
    log_info "Команда: cp env_example.txt .env && nano .env"
    exit 1
fi

# Создание резервной копии
log_info "Создание резервной копии..."
if [[ -f "bookai.db" ]]; then
    BACKUP_NAME="bookai_backup_$(date +%Y%m%d_%H%M%S).db"
    cp bookai.db "$BACKUP_NAME"
    log_success "Резервная копия создана: $BACKUP_NAME"
fi

# Остановка существующих контейнеров
log_info "Остановка существующих контейнеров..."
docker-compose down 2>/dev/null || true
log_success "Контейнеры остановлены"

# Удаление старых образов (опционально)
if [[ "$ENVIRONMENT" == "production" ]]; then
    log_info "Очистка старых образов..."
    docker system prune -f
fi

# Создание необходимых директорий
log_info "Создание директорий..."
mkdir -p uploads covers ssl
log_success "Директории созданы"

# Сборка и запуск контейнеров
log_info "Сборка и запуск контейнеров..."
docker-compose up -d --build

# Ожидание запуска сервисов
log_info "Ожидание запуска сервисов..."
sleep 10

# Проверка статуса контейнеров
log_info "Проверка статуса контейнеров..."
docker-compose ps

# Проверка логов
log_info "Проверка логов..."
echo "=== Логи бота ==="
docker-compose logs --tail=10 bot

echo "=== Логи админ-бэкенда ==="
docker-compose logs --tail=10 admin-backend

echo "=== Логи админ-фронтенда ==="
docker-compose logs --tail=10 admin-frontend

echo "=== Логи nginx ==="
docker-compose logs --tail=10 nginx

# Проверка доступности сервисов
log_info "Проверка доступности сервисов..."

# Проверка nginx
if curl -f http://localhost/health > /dev/null 2>&1; then
    log_success "Nginx доступен"
else
    log_warning "Nginx недоступен"
fi

# Проверка админ-бэкенда
if curl -f http://localhost:8001/health > /dev/null 2>&1; then
    log_success "Админ-бэкенд доступен"
else
    log_warning "Админ-бэкенд недоступен"
fi

log_success "Развертывание в Docker завершено!"
log_info "Доступные сервисы:"
echo "  - Админ-панель: http://localhost"
echo "  - API: http://localhost/api"
echo "  - Статические файлы: http://localhost/uploads/"

log_info "Полезные команды:"
echo "  - Просмотр логов: docker-compose logs -f [service_name]"
echo "  - Остановка: docker-compose down"
echo "  - Перезапуск: docker-compose restart [service_name]"
echo "  - Обновление: docker-compose pull && docker-compose up -d"

