#!/bin/bash

echo "🛑 Остановка всех процессов BookAI..."

# Останавливаем процессы
pkill -f 'uvicorn|bot.py|npm|node'

echo "✅ Все процессы остановлены"
