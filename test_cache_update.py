#!/usr/bin/env python3
"""
Тест для проверки обновления кэша сообщений
"""

import asyncio
import sqlite3
from bot_messages_cache import refresh_cache, get_song_gift_reason, update_message_in_cache

async def test_cache_update():
    """Тестирует обновление кэша сообщений"""
    
    print("🔄 Тестируем обновление кэша сообщений...")
    print("=" * 60)
    
    try:
        # 1. Инициализируем кэш
        print("1️⃣ Инициализируем кэш...")
        await refresh_cache()
        print("✅ Кэш инициализирован")
        
        # 2. Получаем текущее сообщение
        print("\n2️⃣ Получаем текущее сообщение...")
        current_message = await get_song_gift_reason()
        print(f"📝 Текущее сообщение: {current_message[:100]}...")
        
        # 3. Обновляем сообщение в базе данных
        print("\n3️⃣ Обновляем сообщение в базе данных...")
        conn = sqlite3.connect('bookai.db')
        cursor = conn.cursor()
        
        # Получаем ID сообщения
        cursor.execute('SELECT id FROM bot_messages WHERE message_key = ?', ('song_gift_reason',))
        result = cursor.fetchone()
        
        if result:
            message_id = result[0]
            new_content = "ТЕСТ: Напиши по какому поводу мы создаём песню 🎶\nИли это просто подарок без повода? ТЕСТ ОБНОВЛЕНИЯ"
            
            cursor.execute('''
                UPDATE bot_messages 
                SET content = ?, updated_at = datetime('now')
                WHERE id = ?
            ''', (new_content, message_id))
            conn.commit()
            print(f"✅ Сообщение обновлено в базе (ID: {message_id})")
        else:
            print("❌ Сообщение song_gift_reason не найдено в базе")
            return
        
        conn.close()
        
        # 4. Обновляем кэш
        print("\n4️⃣ Обновляем кэш...")
        await update_message_in_cache('song_gift_reason', new_content)
        print("✅ Кэш обновлен")
        
        # 5. Проверяем, что сообщение изменилось
        print("\n5️⃣ Проверяем обновленное сообщение...")
        updated_message = await get_song_gift_reason()
        print(f"📝 Обновленное сообщение: {updated_message[:100]}...")
        
        if "ТЕСТ ОБНОВЛЕНИЯ" in updated_message:
            print("🎉 УСПЕХ! Кэш обновился корректно!")
        else:
            print("❌ ОШИБКА! Кэш не обновился")
        
        print("\n" + "=" * 60)
        print("📋 Инструкция:")
        print("1. Перезапустите бота")
        print("2. Измените сообщение в админке")
        print("3. Проверьте в боте - изменения должны примениться!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_cache_update())
