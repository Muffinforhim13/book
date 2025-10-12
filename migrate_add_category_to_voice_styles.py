#!/usr/bin/env python3
"""
Миграция для добавления колонки category в таблицу voice_styles
"""

import asyncio
import aiosqlite

async def migrate_voice_styles():
    """Добавляет колонку category в таблицу voice_styles"""
    async with aiosqlite.connect('bookai.db') as db:
        try:
            # Проверяем, существует ли уже колонка category
            cursor = await db.execute("PRAGMA table_info(voice_styles)")
            columns = await cursor.fetchall()
            column_names = [column[1] for column in columns]
            
            if 'category' not in column_names:
                print("🔧 Добавляем колонку category в таблицу voice_styles...")
                await db.execute('ALTER TABLE voice_styles ADD COLUMN category TEXT DEFAULT "gentle"')
                await db.commit()
                print("✅ Колонка category успешно добавлена!")
            else:
                print("ℹ️ Колонка category уже существует в таблице voice_styles")
            
            # Проверяем результат
            cursor = await db.execute("PRAGMA table_info(voice_styles)")
            columns = await cursor.fetchall()
            print("\n📋 Структура таблицы voice_styles:")
            for column in columns:
                print(f"  - {column[1]} ({column[2]})")
                
        except Exception as e:
            print(f"❌ Ошибка при миграции: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(migrate_voice_styles())
