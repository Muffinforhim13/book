#!/usr/bin/env python3
"""
Скрипт для миграции: добавление поля email в таблицу orders
"""

import asyncio
import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bookai.db')

async def migrate_add_email():
    """Добавляет поле email в таблицу orders если его нет"""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            # Проверяем, существует ли поле email в таблице orders
            cursor = await db.execute("PRAGMA table_info(orders)")
            columns = await cursor.fetchall()
            column_names = [column[1] for column in columns]
            
            # Если поле email не существует, добавляем его
            if 'email' not in column_names:
                print("📧 Добавляем поле email в таблицу orders...")
                await db.execute('ALTER TABLE orders ADD COLUMN email TEXT')
                await db.commit()
                print("✅ Поле email успешно добавлено!")
            else:
                print("✅ Поле email уже существует в таблице orders")
                
        except Exception as e:
            print(f"❌ Ошибка при миграции: {e}")
            raise

if __name__ == "__main__":
    print("🚀 Начинаем миграцию: добавление поля email...")
    asyncio.run(migrate_add_email())
    print("🎉 Миграция завершена!")
