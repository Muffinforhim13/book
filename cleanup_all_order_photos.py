#!/usr/bin/env python3
"""
Скрипт для полной очистки всех фотографий заказов из всех таблиц
"""

import asyncio
import aiosqlite
import os

DB_PATH = 'bookai.db'

async def cleanup_all_order_photos():
    """Удаляет все фотографии заказов из всех таблиц"""
    async with aiosqlite.connect(DB_PATH) as db:
        print("🧹 Полная очистка всех фотографий заказов...")
        
        # Очищаем main_hero_photos
        async with db.execute('SELECT COUNT(*) FROM main_hero_photos') as cursor:
            main_hero_count = (await cursor.fetchone())[0]
        print(f"📊 main_hero_photos: {main_hero_count} записей")
        
        # Очищаем hero_photos
        async with db.execute('SELECT COUNT(*) FROM hero_photos') as cursor:
            hero_count = (await cursor.fetchone())[0]
        print(f"📊 hero_photos: {hero_count} записей")
        
        # Очищаем joint_photos
        async with db.execute('SELECT COUNT(*) FROM joint_photos') as cursor:
            joint_count = (await cursor.fetchone())[0]
        print(f"📊 joint_photos: {joint_count} записей")
        
        # Удаляем все записи из таблиц с фотографиями заказов
        await db.execute('DELETE FROM main_hero_photos')
        await db.execute('DELETE FROM hero_photos')
        await db.execute('DELETE FROM joint_photos')
        
        await db.commit()
        
        print("✅ Все фотографии заказов удалены из базы данных")
        
        # Проверяем результат
        async with db.execute('SELECT COUNT(*) FROM main_hero_photos') as cursor:
            main_hero_after = (await cursor.fetchone())[0]
        async with db.execute('SELECT COUNT(*) FROM hero_photos') as cursor:
            hero_after = (await cursor.fetchone())[0]
        async with db.execute('SELECT COUNT(*) FROM joint_photos') as cursor:
            joint_after = (await cursor.fetchone())[0]
            
        print(f"📊 После очистки:")
        print(f"   main_hero_photos: {main_hero_after} записей")
        print(f"   hero_photos: {hero_after} записей")
        print(f"   joint_photos: {joint_after} записей")

async def main():
    await cleanup_all_order_photos()

if __name__ == "__main__":
    asyncio.run(main())
