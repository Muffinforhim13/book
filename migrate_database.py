#!/usr/bin/env python3
"""
Скрипт для миграции базы данных - добавление новых полей для системы шаблонов
"""

import asyncio
import aiosqlite

DB_PATH = 'bookai.db'

async def migrate_database():
    """Добавляет новые поля в таблицу delayed_messages"""
    print("🔄 Начинаем миграцию базы данных...")
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем структуру таблицы
        cursor = await db.execute("PRAGMA table_info(delayed_messages)")
        columns = await cursor.fetchall()
        existing_columns = [col[1] for col in columns]
        
        print(f"📋 Существующие колонки: {existing_columns}")
        
        # Добавляем новые поля, если их нет
        new_fields = [
            ('is_active', 'BOOLEAN DEFAULT 1'),
            ('usage_count', 'INTEGER DEFAULT 0'),
            ('last_used', 'DATETIME')
        ]
        
        for field_name, field_type in new_fields:
            if field_name not in existing_columns:
                try:
                    await db.execute(f'ALTER TABLE delayed_messages ADD COLUMN {field_name} {field_type}')
                    print(f"✅ Добавлена колонка: {field_name}")
                except Exception as e:
                    print(f"❌ Ошибка добавления колонки {field_name}: {e}")
            else:
                print(f"⏭️ Колонка {field_name} уже существует")
        
        await db.commit()
        
        # Проверяем финальную структуру
        cursor = await db.execute("PRAGMA table_info(delayed_messages)")
        columns = await cursor.fetchall()
        final_columns = [col[1] for col in columns]
        
        print(f"\n📋 Финальные колонки: {final_columns}")
        
        # Обновляем существующие записи, устанавливая is_active = 1 для всех
        cursor = await db.execute('UPDATE delayed_messages SET is_active = 1 WHERE is_active IS NULL')
        updated_rows = cursor.rowcount
        print(f"✅ Обновлено {updated_rows} записей (установлен is_active = 1)")
        
        await db.commit()
        
        print("\n🎉 Миграция базы данных завершена!")

async def show_migration_status():
    """Показывает статус миграции"""
    print("\n📊 Статус миграции:")
    print("=" * 50)
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем количество записей
        cursor = await db.execute('SELECT COUNT(*) FROM delayed_messages')
        total_count = (await cursor.fetchone())[0]
        
        cursor = await db.execute('SELECT COUNT(*) FROM delayed_messages WHERE order_id IS NULL')
        template_count = (await cursor.fetchone())[0]
        
        cursor = await db.execute('SELECT COUNT(*) FROM delayed_messages WHERE is_active = 1')
        active_count = (await cursor.fetchone())[0]
        
        print(f"📝 Всего записей в delayed_messages: {total_count}")
        print(f"📋 Шаблонов (order_id IS NULL): {template_count}")
        print(f"🟢 Активных записей: {active_count}")
        
        # Показываем примеры шаблонов
        if template_count > 0:
            print(f"\n📋 Примеры шаблонов:")
            cursor = await db.execute('''
                SELECT message_type, is_active, usage_count, last_used
                FROM delayed_messages 
                WHERE order_id IS NULL
                LIMIT 5
            ''')
            templates = await cursor.fetchall()
            
            for template in templates:
                status = "🟢 Активен" if template[1] else "⚫ Неактивен"
                usage = f"📊 {template[2]} использований" if template[2] > 0 else "📊 Не использовался"
                last_used = f"🕒 {template[3]}" if template[3] else "🕒 Никогда"
                print(f"   {template[0]} - {status} | {usage} | {last_used}")

async def main():
    """Основная функция"""
    print("🚀 Скрипт миграции базы данных для системы шаблонов")
    print("=" * 60)
    
    try:
        # Выполняем миграцию
        await migrate_database()
        
        # Показываем статус
        await show_migration_status()
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
