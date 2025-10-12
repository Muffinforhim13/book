#!/usr/bin/env python3
"""
Скрипт для очистки страниц, привязанных к несуществующим заказам
"""

import asyncio
import aiosqlite
from db import DB_PATH

async def cleanup_orphaned_pages():
    """
    Удаляет страницы, которые привязаны к несуществующим заказам
    """
    print("🧹 Начинаем очистку страниц, привязанных к несуществующим заказам...")
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Находим страницы, привязанные к несуществующим заказам
        cursor = await db.execute('''
            SELECT op.id, op.order_id, op.page_number, op.filename, op.description, op.created_at
            FROM order_pages op
            LEFT JOIN orders o ON op.order_id = o.id
            WHERE o.id IS NULL
        ''')
        
        orphaned_pages = await cursor.fetchall()
        
        if not orphaned_pages:
            print("✅ Висящих страниц не найдено")
            return
        
        print(f"🔍 Найдено {len(orphaned_pages)} висящих страниц:")
        
        for page in orphaned_pages:
            print(f"  - ID: {page[0]}, Order ID: {page[1]}, Page: {page[2]}, File: {page[3]}, Desc: {page[4]}, Date: {page[5]}")
        
        # Удаляем висящие страницы
        cursor = await db.execute('''
            DELETE FROM order_pages
            WHERE id IN (
                SELECT op.id
                FROM order_pages op
                LEFT JOIN orders o ON op.order_id = o.id
                WHERE o.id IS NULL
            )
        ''')
        
        deleted_count = cursor.rowcount
        await db.commit()
        
        print(f"✅ Удалено {deleted_count} висящих страниц")

async def show_pages_stats():
    """
    Показывает статистику по страницам
    """
    print("\n📊 Статистика по страницам:")
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Общее количество страниц
        cursor = await db.execute('SELECT COUNT(*) FROM order_pages')
        total_pages = (await cursor.fetchone())[0]
        print(f"  Всего страниц: {total_pages}")
        
        # Количество страниц с существующими заказами
        cursor = await db.execute('''
            SELECT COUNT(*)
            FROM order_pages op
            INNER JOIN orders o ON op.order_id = o.id
        ''')
        valid_pages = (await cursor.fetchone())[0]
        print(f"  Страниц с существующими заказами: {valid_pages}")
        
        # Количество висящих страниц
        cursor = await db.execute('''
            SELECT COUNT(*)
            FROM order_pages op
            LEFT JOIN orders o ON op.order_id = o.id
            WHERE o.id IS NULL
        ''')
        orphaned_pages = (await cursor.fetchone())[0]
        print(f"  Висящих страниц: {orphaned_pages}")

if __name__ == "__main__":
    async def main():
        await show_pages_stats()
        await cleanup_orphaned_pages()
        await show_pages_stats()
        print("\n🎉 Очистка завершена!")
    
    asyncio.run(main())
