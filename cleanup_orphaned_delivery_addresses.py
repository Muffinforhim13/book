#!/usr/bin/env python3
"""
Скрипт для очистки адресов доставки, привязанных к несуществующим заказам
"""

import asyncio
import aiosqlite
from db import DB_PATH

async def cleanup_orphaned_delivery_addresses():
    """
    Удаляет адреса доставки, которые привязаны к несуществующим заказам
    """
    print("🧹 Начинаем очистку адресов доставки, привязанных к несуществующим заказам...")
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Находим адреса доставки, привязанные к несуществующим заказам
        cursor = await db.execute('''
            SELECT da.id, da.order_id, da.address, da.recipient_name, da.created_at
            FROM delivery_addresses da
            LEFT JOIN orders o ON da.order_id = o.id
            WHERE o.id IS NULL
        ''')
        
        orphaned_addresses = await cursor.fetchall()
        
        if not orphaned_addresses:
            print("✅ Висящих адресов доставки не найдено")
            return
        
        print(f"🔍 Найдено {len(orphaned_addresses)} висящих адресов доставки:")
        
        for addr in orphaned_addresses:
            print(f"  - ID: {addr[0]}, Order ID: {addr[1]}, Адрес: {addr[2]}, Получатель: {addr[3]}, Дата: {addr[4]}")
        
        # Удаляем висящие адреса
        cursor = await db.execute('''
            DELETE FROM delivery_addresses
            WHERE id IN (
                SELECT da.id
                FROM delivery_addresses da
                LEFT JOIN orders o ON da.order_id = o.id
                WHERE o.id IS NULL
            )
        ''')
        
        deleted_count = cursor.rowcount
        await db.commit()
        
        print(f"✅ Удалено {deleted_count} висящих адресов доставки")

async def show_delivery_addresses_stats():
    """
    Показывает статистику по адресам доставки
    """
    print("\n📊 Статистика по адресам доставки:")
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Общее количество адресов
        cursor = await db.execute('SELECT COUNT(*) FROM delivery_addresses')
        total_addresses = (await cursor.fetchone())[0]
        print(f"  Всего адресов доставки: {total_addresses}")
        
        # Количество адресов с существующими заказами
        cursor = await db.execute('''
            SELECT COUNT(*)
            FROM delivery_addresses da
            INNER JOIN orders o ON da.order_id = o.id
        ''')
        valid_addresses = (await cursor.fetchone())[0]
        print(f"  Адресов с существующими заказами: {valid_addresses}")
        
        # Количество висящих адресов
        cursor = await db.execute('''
            SELECT COUNT(*)
            FROM delivery_addresses da
            LEFT JOIN orders o ON da.order_id = o.id
            WHERE o.id IS NULL
        ''')
        orphaned_addresses = (await cursor.fetchone())[0]
        print(f"  Висящих адресов: {orphaned_addresses}")

if __name__ == "__main__":
    async def main():
        await show_delivery_addresses_stats()
        await cleanup_orphaned_delivery_addresses()
        await show_delivery_addresses_stats()
        print("\n🎉 Очистка завершена!")
    
    asyncio.run(main())
