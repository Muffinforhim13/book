#!/usr/bin/env python3
"""
Скрипт для принудительного обновления кэша сообщений
"""

import asyncio
import sys
import os

# Добавляем путь к модулям проекта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot_messages_cache import clear_cache, refresh_cache, _messages_cache

async def force_update_cache():
    """Принудительно обновляет кэш сообщений"""
    
    print("🔄 Принудительно обновляем кэш сообщений...")
    
    # Показываем текущее состояние
    print(f"📊 Текущее состояние кэша: {len(_messages_cache)} сообщений")
    
    # Очищаем кэш
    print("🧹 Очищаем кэш...")
    clear_cache()
    
    # Перезагружаем кэш
    print("📥 Перезагружаем кэш из базы данных...")
    await refresh_cache()
    
    # Показываем новое состояние
    print(f"📊 Новое состояние кэша: {len(_messages_cache)} сообщений")
    
    if _messages_cache:
        print("\n📋 Обновленные сообщения в кэше:")
        for key, content in list(_messages_cache.items())[:5]:  # Показываем первые 5
            print(f"   {key}: {content[:50]}...")
        
        if len(_messages_cache) > 5:
            print(f"   ... и еще {len(_messages_cache) - 5} сообщений")
    
    print("\n✅ Кэш обновлен! Теперь бот должен использовать актуальные сообщения.")

if __name__ == "__main__":
    asyncio.run(force_update_cache())
