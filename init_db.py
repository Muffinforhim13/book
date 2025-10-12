#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных
"""

import asyncio
import sys
import os

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import init_db, populate_bot_messages, auto_collect_bot_messages, populate_pricing_items

async def main():
    """Основная функция"""
    print("🚀 Начинаем инициализацию базы данных...")
    
    try:
        # Инициализируем базу данных (создаем все таблицы)
        print("📊 Создаем таблицы базы данных...")
        await init_db()
        print("✅ База данных инициализирована!")
        
        # Заполняем сообщениями бота
        print("📝 Заполняем сообщениями бота...")
        await populate_bot_messages()
        
        # Автоматически собираем дополнительные сообщения
        print("🔍 Автоматически собираем дополнительные сообщения...")
        await auto_collect_bot_messages()
        
        # Заполняем цены
        print("💰 Заполняем цены...")
        await populate_pricing_items()
        
        print("🎉 Инициализация завершена успешно!")
        print("📝 Теперь вы можете редактировать сообщения и цены в админ-панели")
        
    except Exception as e:
        print(f"❌ Ошибка при инициализации: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
