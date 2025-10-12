#!/usr/bin/env python3
"""
Скрипт для очистки фотографий заказов, оставляя только стили книг, обложки и стили песен
"""

import asyncio
import aiosqlite
import json
import os
import glob

DB_PATH = 'bookai.db'

async def analyze_photo_types():
    """Анализирует типы фотографий в системе"""
    async with aiosqlite.connect(DB_PATH) as db:
        print("🔍 Анализ типов фотографий в системе...")
        
        # Анализируем таблицу uploads
        async with db.execute('''
            SELECT file_type, COUNT(*) as count
            FROM uploads
            GROUP BY file_type
            ORDER BY count DESC
        ''') as cursor:
            upload_types = await cursor.fetchall()
            print("\n📊 Типы файлов в таблице uploads:")
            for file_type, count in upload_types:
                print(f"  {file_type}: {count} файлов")
        
        # Анализируем order_data для понимания типов фотографий
        async with db.execute('''
            SELECT order_data
            FROM orders
            WHERE order_data IS NOT NULL AND order_data != ''
        ''') as cursor:
            orders = await cursor.fetchall()
            print(f"\n📊 Анализ {len(orders)} заказов с order_data...")
            
            photo_types = set()
            for order_data_str, in orders:
                try:
                    order_data = json.loads(order_data_str)
                    
                    # Собираем все типы фотографий
                    main_hero_photos = order_data.get('main_hero_photos', [])
                    if isinstance(main_hero_photos, list):
                        for photo_obj in main_hero_photos:
                            if isinstance(photo_obj, dict):
                                photo_type = photo_obj.get('type', 'main_hero')
                                photo_types.add(photo_type)
                    
                    # Проверяем отдельные поля
                    if order_data.get('main_face_1'):
                        photo_types.add('main_face_1')
                    if order_data.get('main_face_2'):
                        photo_types.add('main_face_2')
                    if order_data.get('main_full'):
                        photo_types.add('main_full')
                    if order_data.get('joint_photo'):
                        photo_types.add('joint_photo')
                    
                    # Проверяем других героев
                    other_heroes = order_data.get('other_heroes', [])
                    for hero in other_heroes:
                        if hero.get('face_1'):
                            photo_types.add('other_hero_face_1')
                        if hero.get('face_2'):
                            photo_types.add('other_hero_face_2')
                        if hero.get('full'):
                            photo_types.add('other_hero_full')
                            
                except json.JSONDecodeError:
                    continue
            
            print(f"\n📊 Типы фотографий в заказах:")
            for photo_type in sorted(photo_types):
                print(f"  {photo_type}")

async def cleanup_order_photos():
    """Удаляет фотографии заказов, оставляя только стили книг, обложки и стили песен"""
    async with aiosqlite.connect(DB_PATH) as db:
        print("🧹 Начинаем очистку фотографий заказов...")
        
        # Типы файлов, которые нужно СОХРАНИТЬ (стили книг, обложки, стили песен)
        keep_types = {
            'book_style', 'book_cover', 'song_style', 'style', 'cover', 
            'template', 'background', 'design', 'artwork'
        }
        
        # Типы файлов, которые нужно УДАЛИТЬ (фотографии заказов)
        # Основываясь на анализе, удаляем demo_photo, first_page_photo, last_page_photo, custom_photo
        remove_types = {
            'demo_photo', 'first_page_photo', 'last_page_photo', 'custom_photo',
            'main_hero', 'main_face_1', 'main_face_2', 'main_full', 
            'joint_photo', 'other_hero_face_1', 'other_hero_face_2', 
            'other_hero_full', 'page_1', 'page_2', 'page_3', 'page_4',
            'page_5', 'page_6', 'page_7', 'page_8', 'page_9', 'page_10',
            'demo_audio', 'demo_video', 'demo_pdf'  # Добавляем демо файлы
        }
        
        deleted_count = 0
        kept_count = 0
        
        # 1. Очищаем таблицу uploads
        print("\n🗑️ Очистка таблицы uploads...")
        async with db.execute('''
            SELECT id, filename, file_type, order_id
            FROM uploads
        ''') as cursor:
            uploads = await cursor.fetchall()
            
            for upload_id, filename, file_type, order_id in uploads:
                should_delete = False
                
                # Проверяем по типу файла
                if file_type in remove_types:
                    should_delete = True
                # Проверяем по имени файла для удаления (фотографии заказов)
                elif any(remove_pattern in filename.lower() for remove_pattern in [
                    'main_', 'joint_', 'hero_', 'page_', 'order_', 'face_', 'full_',
                    'demo_', 'обложка', 'нарезка', 'пробная', 'демо'
                ]):
                    should_delete = True
                # Проверяем по имени файла для сохранения (стили, обложки, шаблоны)
                elif any(keep_type in filename.lower() for keep_type in keep_types):
                    should_delete = False
                
                if should_delete:
                    # Удаляем файл физически
                    file_path = os.path.join('uploads', filename)
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            print(f"  🗑️ Удален файл: {filename}")
                        except Exception as e:
                            print(f"  ❌ Ошибка удаления файла {filename}: {e}")
                    
                    # Удаляем запись из БД
                    await db.execute('DELETE FROM uploads WHERE id = ?', (upload_id,))
                    deleted_count += 1
                else:
                    print(f"  ✅ Сохранен файл: {filename} (тип: {file_type})")
                    kept_count += 1
        
        # 2. Очищаем order_data от фотографий
        print("\n🗑️ Очистка order_data от фотографий...")
        async with db.execute('''
            SELECT id, order_data
            FROM orders
            WHERE order_data IS NOT NULL AND order_data != ''
        ''') as cursor:
            orders = await cursor.fetchall()
            
            for order_id, order_data_str in orders:
                try:
                    order_data = json.loads(order_data_str)
                    original_data = order_data.copy()
                    
                    # Удаляем поля с фотографиями
                    photo_fields = [
                        'main_hero_photos', 'main_face_1', 'main_face_2', 'main_full',
                        'joint_photo', 'other_heroes'
                    ]
                    
                    for field in photo_fields:
                        if field in order_data:
                            del order_data[field]
                    
                    # Если данные изменились, обновляем БД
                    if order_data != original_data:
                        await db.execute('''
                            UPDATE orders 
                            SET order_data = ?
                            WHERE id = ?
                        ''', (json.dumps(order_data), order_id))
                        print(f"  🗑️ Очищен order_data для заказа {order_id}")
                    
                except json.JSONDecodeError as e:
                    print(f"  ❌ Ошибка парсинга order_data для заказа {order_id}: {e}")
        
        # 3. Очищаем папки с фотографиями заказов
        print("\n🗑️ Очистка папок с фотографиями заказов...")
        
        # Удаляем папки order_*_pages
        pages_dirs = glob.glob("uploads/order_*_pages")
        for pages_dir in pages_dirs:
            try:
                import shutil
                shutil.rmtree(pages_dir)
                print(f"  🗑️ Удалена папка: {pages_dir}")
            except Exception as e:
                print(f"  ❌ Ошибка удаления папки {pages_dir}: {e}")
        
        await db.commit()
        
        print(f"\n✅ Очистка завершена!")
        print(f"  🗑️ Удалено файлов: {deleted_count}")
        print(f"  ✅ Сохранено файлов: {kept_count}")

async def main():
    """Основная функция"""
    print("🧹 Скрипт очистки фотографий заказов")
    print("=" * 50)
    
    # Сначала анализируем
    await analyze_photo_types()
    
    # Автоматическое подтверждение для сервера
    print("\n⚠️  ВНИМАНИЕ: Этот скрипт удалит ВСЕ фотографии заказов!")
    print("   Будут сохранены только стили книг, обложки и стили песен.")
    print("   Продолжаем автоматически...")
    
    # Выполняем очистку
    await cleanup_order_photos()

if __name__ == "__main__":
    asyncio.run(main())
