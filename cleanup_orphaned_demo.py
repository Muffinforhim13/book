#!/usr/bin/env python3
"""
Скрипт для очистки orphaned записей демо-контента из таблицы outbox.
Эти записи остались после удаления заказов и блокируют повторную отправку демо.
"""

import asyncio
import aiosqlite
import sys
from datetime import datetime

DB_PATH = 'bookai.db'

async def cleanup_orphaned_demo_records():
    """Удаляет orphaned записи демо-контента из таблицы outbox"""
    
    print("🧹 Начинаем очистку orphaned записей демо-контента...")
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Сначала подсчитываем количество записей для удаления
        count_cursor = await db.execute('''
            SELECT COUNT(*) as count
            FROM outbox o
            LEFT JOIN orders ord ON o.order_id = ord.id
            WHERE o.type = 'multiple_images_with_text_and_button' AND ord.id IS NULL
        ''')
        count_result = await count_cursor.fetchone()
        orphaned_count = count_result[0] if count_result else 0
        
        print(f"📊 Найдено {orphaned_count} orphaned записей демо-контента для удаления")
        
        if orphaned_count == 0:
            print("✅ Orphaned записи не найдены, очистка не требуется")
            return
        
        # Подтверждение от пользователя
        confirm = input(f"❓ Удалить {orphaned_count} orphaned записей демо-контента? (y/N): ")
        if confirm.lower() != 'y':
            print("❌ Операция отменена пользователем")
            return
        
        # Удаляем orphaned записи
        delete_cursor = await db.execute('''
            DELETE FROM outbox 
            WHERE id IN (
                SELECT o.id
                FROM outbox o
                LEFT JOIN orders ord ON o.order_id = ord.id
                WHERE o.type = 'multiple_images_with_text_and_button' AND ord.id IS NULL
            )
        ''')
        
        deleted_count = delete_cursor.rowcount
        await db.commit()
        
        print(f"✅ Успешно удалено {deleted_count} orphaned записей демо-контента")
        
        # Проверяем результат
        verify_cursor = await db.execute('''
            SELECT COUNT(*) as count
            FROM outbox o
            LEFT JOIN orders ord ON o.order_id = ord.id
            WHERE o.type = 'multiple_images_with_text_and_button' AND ord.id IS NULL
        ''')
        verify_result = await verify_cursor.fetchone()
        remaining_orphaned = verify_result[0] if verify_result else 0
        
        if remaining_orphaned == 0:
            print("🎉 Все orphaned записи успешно удалены!")
        else:
            print(f"⚠️ Осталось {remaining_orphaned} orphaned записей")

async def show_demo_statistics():
    """Показывает статистику по демо-контенту"""
    
    print("\n📈 Статистика по демо-контенту:")
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Общее количество записей демо-контента
        total_cursor = await db.execute('''
            SELECT COUNT(*) as count
            FROM outbox 
            WHERE type = 'multiple_images_with_text_and_button'
        ''')
        total_result = await total_cursor.fetchone()
        total_count = total_result[0] if total_result else 0
        
        # Количество orphaned записей
        orphaned_cursor = await db.execute('''
            SELECT COUNT(*) as count
            FROM outbox o
            LEFT JOIN orders ord ON o.order_id = ord.id
            WHERE o.type = 'multiple_images_with_text_and_button' AND ord.id IS NULL
        ''')
        orphaned_result = await orphaned_cursor.fetchone()
        orphaned_count = orphaned_result[0] if orphaned_result else 0
        
        # Количество валидных записей
        valid_count = total_count - orphaned_count
        
        print(f"  📊 Всего записей демо-контента: {total_count}")
        print(f"  ✅ Валидных записей: {valid_count}")
        print(f"  ❌ Orphaned записей: {orphaned_count}")
        
        if orphaned_count > 0:
            print(f"  🚨 Проблема: {orphaned_count} orphaned записей блокируют повторную отправку демо")
        else:
            print(f"  🎉 Проблем нет: все записи демо-контента связаны с существующими заказами")

async def main():
    """Основная функция"""
    
    print("🔧 Скрипт очистки orphaned записей демо-контента")
    print("=" * 50)
    
    try:
        # Показываем статистику
        await show_demo_statistics()
        
        # Выполняем очистку
        await cleanup_orphaned_demo_records()
        
        # Показываем финальную статистику
        print("\n📈 Финальная статистика:")
        await show_demo_statistics()
        
        print("\n✅ Скрипт завершен успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
