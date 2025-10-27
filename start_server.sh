#!/bin/bash

echo "🚀 Запуск BookAI проекта на сервере..."
echo "=================================================="

# Активируем виртуальное окружение
source venv/bin/activate

# Останавливаем старые процессы
echo "🛑 Остановка старых процессов..."
pkill -f 'uvicorn|bot.py|npm|node' 2>/dev/null
sleep 2

# Запуск бэкенда в фоне
echo "📡 Запуск бэкенда..."
nohup python -m uvicorn admin_backend.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ Бэкенд запущен (PID: $BACKEND_PID)"

# Проверяем, что процесс действительно запустился
sleep 1
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ Процесс бэкенда завершился сразу после запуска"
    echo "📋 Лог бэкенда:"
    cat backend.log
    exit 1
fi

# Ждем запуска бэкенда с повторными проверками
echo "⏳ Ожидание запуска бэкенда..."
for i in {1..30}; do
    # Проверяем доступность порта
    if netstat -tuln 2>/dev/null | grep -q ":8000.*LISTEN" || ss -tuln 2>/dev/null | grep -q ":8000.*LISTEN"; then
        # Дополнительно проверяем HTTP ответ
        if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
            echo "✅ Бэкенд доступен (попытка $i/30)"
            break
        fi
    fi
    
    if [ $i -eq 30 ]; then
        echo "❌ Бэкенд не запустился за 30 попыток"
        echo "📋 Статус процесса:"
        if kill -0 $BACKEND_PID 2>/dev/null; then
            echo "  Процесс $BACKEND_PID работает"
        else
            echo "  Процесс $BACKEND_PID завершился"
        fi
        echo "📋 Последние строки лога бэкенда:"
        tail -20 backend.log
        echo "📋 Проверка портов:"
        netstat -tuln 2>/dev/null | grep 8000 || echo "  Порт 8000 не слушается"
        exit 1
    fi
    echo "⏳ Попытка $i/30 - ожидание запуска бэкенда..."
    sleep 2
done

# Запуск бота в фоне
echo "🤖 Запуск бота..."
nohup python bot.py > bot.log 2>&1 &
BOT_PID=$!
echo "✅ Бот запущен (PID: $BOT_PID)"

# Запуск фронтенда в фоне
echo "🌐 Запуск фронтенда..."
cd admin_frontend
nohup npm start > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ Фронтенд запущен (PID: $FRONTEND_PID)"

# Возвращаемся в корневую директорию
cd ..

echo ""
echo "🎉 Все компоненты запущены!"
echo "📱 Бот: Telegram бот"
echo "�� API: http://45.144.222.230:8000"
echo "�� Документация: http://45.144.222.230:8000/docs"
echo "�� Фронтенд: http://45.144.222.230:3000"
echo "=================================================="
echo ""
echo "💡 Для просмотра логов:"
echo "  tail -f backend.log"
echo "  tail -f bot.log"
echo "  tail -f frontend.log"
echo ""
echo "�� Для остановки всех процессов:"
echo "  ./stop_server.sh"
echo ""
echo "📊 Статус процессов:"
ps aux | grep -E "(uvicorn|bot.py|npm)" | grep -v grep
