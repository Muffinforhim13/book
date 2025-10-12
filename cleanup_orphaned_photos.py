#!/usr/bin/env python3
"""
Скрипт для удаления фотографий, связанных с несуществующими заказами
"""

import asyncio
import aiosqlite
import os

DB_PATH = 'bookai.db'

async def cleanup_orphaned_photos():
    """Удаляет фотографии, связанные с несуществующими заказами"""
    async with aiosqlite.connect(DB_PATH) as db:
        print("🧹 Очистка фотографий от несуществующих заказов...")
        
        # Находим фотографии, связанные с несуществующими заказами
        async with db.execute('''
            SELECT u.id, u.filename, u.file_type, u.order_id
            FROM uploads u
            LEFT JOIN orders o ON u.order_id = o.id
            WHERE u.order_id IS NOT NULL AND o.id IS NULL
        ''') as cursor:
            orphaned_photos = await cursor.fetchall()
        
        print(f"📊 Найдено {len(orphaned_photos)} фотографий от несуществующих заказов")
        
        if orphaned_photos:
            deleted_count = 0
            for photo_id, filename, file_type, order_id in orphaned_photos:
                print(f"🗑️  Удаляем: {filename} (заказ {order_id} не существует)")
                
                # Удаляем файл физически
                file_path = os.path.join('uploads', filename)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"   ✅ Файл удален: {filename}")
                    except Exception as e:
                        print(f"   ❌ Ошибка удаления файла {filename}: {e}")
                else:
                    print(f"   ⚠️  Файл не найден: {filename}")
                
                # Удаляем запись из БД
                await db.execute('DELETE FROM uploads WHERE id = ?', (photo_id,))
                deleted_count += 1
            
            await db.commit()
            print(f"✅ Удалено {deleted_count} фотографий от несуществующих заказов")
        else:
            print("✅ Фотографий от несуществующих заказов не найдено")
        
        # Также проверим другие таблицы с фотографиями
        tables_to_check = ['main_hero_photos', 'hero_photos', 'joint_photos']
        
        for table in tables_to_check:
            print(f"\n🔍 Проверяем таблицу {table}...")
            async with db.execute(f'''
                SELECT p.id, p.filename, p.order_id
                FROM {table} p
                LEFT JOIN orders o ON p.order_id = o.id
                WHERE p.order_id IS NOT NULL AND o.id IS NULL
            ''') as cursor:
                orphaned = await cursor.fetchall()
            
            if orphaned:
                print(f"📊 Найдено {len(orphaned)} записей в {table} от несуществующих заказов")
                for record_id, filename, order_id in orphaned:
                    print(f"🗑️  Удаляем: {filename} (заказ {order_id} не существует)")
                    await db.execute(f'DELETE FROM {table} WHERE id = ?', (record_id,))
                await db.commit()
            else:
                print(f"✅ В таблице {table} нет записей от несуществующих заказов")

async def main():
    await cleanup_orphaned_photos()

if __name__ == "__main__":
    asyncio.run(main())
