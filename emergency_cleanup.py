#!/usr/bin/env python3
"""
ЭКСТРЕННАЯ ЧИСТКА: Удаляем ВСЕ дубликаты из delayed_messages
"""

import asyncio
import aiosqlite

DB_PATH = 'bookai.db'

async def emergency_cleanup():
    """Экстренная чистка дубликатов"""
    print("🚨 ЭКСТРЕННАЯ ЧИСТКА ДУБЛИКАТОВ")
    print("=" * 50)
    
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Подсчитываем что у нас есть
        cursor = await db.execute("SELECT COUNT(*) FROM delayed_messages WHERE is_automatic = 1")
        auto_count = await cursor.fetchone()
        
        cursor = await db.execute("SELECT COUNT(DISTINCT message_type) FROM delayed_messages WHERE is_automatic = 1")
        unique_types = await cursor.fetchone()
        
        print(f"📊 Статистика:")
        print(f"   Автоматических сообщений: {auto_count[0]}")
        print(f"   Уникальных типов: {unique_types[0]}")
        
        # 2. Показываем примеры дубликатов
        cursor = await db.execute("""
            SELECT message_type, COUNT(*) as count
            FROM delayed_messages 
            WHERE is_automatic = 1
            GROUP BY message_type
            HAVING COUNT(*) > 1
            ORDER BY count DESC
            LIMIT 5
        """)
        duplicates = await cursor.fetchall()
        
        print(f"\n🔥 Топ-5 дубликатов:")
        for dup in duplicates:
            print(f"   {dup[0]}: {dup[1]} копий")
        
        # 3. УДАЛЯЕМ ВСЕ автоматические сообщения из delayed_messages
        print(f"\n🗑️ Удаляем ВСЕ автоматические сообщения из delayed_messages...")
        
        # Сначала проверяем, есть ли НЕ автоматические сообщения
        cursor = await db.execute("SELECT COUNT(*) FROM delayed_messages WHERE is_automatic != 1 OR is_automatic IS NULL")
        manual_count = await cursor.fetchone()
        print(f"   Оставляем ручных сообщений: {manual_count[0]}")
        
        # Удаляем только автоматические
        result = await db.execute("DELETE FROM delayed_messages WHERE is_automatic = 1")
        deleted_count = result.rowcount
        
        await db.commit()
        
        print(f"✅ Удалено автоматических записей: {deleted_count}")
        
        # 4. Проверяем что осталось
        cursor = await db.execute("SELECT COUNT(*) FROM delayed_messages")
        remaining = await cursor.fetchone()
        
        cursor = await db.execute("SELECT COUNT(*) FROM message_templates")
        templates = await cursor.fetchone()
        
        print(f"\n📋 Итого:")
        print(f"   В delayed_messages осталось: {remaining[0]} записей")
        print(f"   В message_templates: {templates[0]} шаблонов")
        print(f"   Всего удалено дубликатов: {deleted_count}")
        
        # 5. Показываем что осталось в delayed_messages
        if remaining[0] > 0:
            print(f"\n📝 Что осталось в delayed_messages:")
            cursor = await db.execute("""
                SELECT id, message_type, is_automatic, order_id
                FROM delayed_messages 
                ORDER BY id 
                LIMIT 10
            """)
            remaining_msgs = await cursor.fetchall()
            
            for msg in remaining_msgs:
                print(f"   ID {msg[0]}: {msg[1]} (auto: {msg[2]}, order: {msg[3]})")

async def main():
    try:
        await emergency_cleanup()
        print(f"\n🎉 ГОТОВО! Теперь админка должна работать корректно.")
        print(f"🔄 Перезагрузите страницу админки (Ctrl+F5)")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())
