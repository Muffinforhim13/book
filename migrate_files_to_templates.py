#!/usr/bin/env python3
"""
Перенос файлов из delayed_message_files в message_template_files
"""

import asyncio
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import DB_PATH
import aiosqlite

async def migrate_files_to_templates():
    """Переносит файлы из delayed_message_files в message_template_files"""
    
    print("🔄 Начинаем перенос файлов...")
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Получаем все файлы из delayed_message_files с информацией о сообщениях
        cursor = await db.execute('''
            SELECT dmf.*, dm.message_type, dm.content, dm.status as message_status
            FROM delayed_message_files dmf
            JOIN delayed_messages dm ON dmf.delayed_message_id = dm.id
            WHERE dm.status = 'pending'
        ''')
        files_to_migrate = await cursor.fetchall()
        
        print(f"📊 Найдено {len(files_to_migrate)} файлов для переноса")
        
        migrated_count = 0
        skipped_count = 0
        
        for file_row in files_to_migrate:
            message_type = file_row['message_type']
            content = file_row['content']
            
            print(f"\n🔍 Обрабатываем файл: {file_row['file_name']} (тип: {message_type})")
            
            # Ищем соответствующий шаблон в message_templates
            cursor = await db.execute('''
                SELECT id FROM message_templates 
                WHERE message_type = ? AND content = ? AND is_active = 1
            ''', (message_type, content))
            template = await cursor.fetchone()
            
            if template:
                template_id = template['id']
                print(f"  ✅ Найден шаблон ID: {template_id}")
                
                # Проверяем, нет ли уже такого файла в message_template_files
                cursor = await db.execute('''
                    SELECT id FROM message_template_files 
                    WHERE template_id = ? AND file_name = ? AND file_path = ?
                ''', (template_id, file_row['file_name'], file_row['file_path']))
                existing = await cursor.fetchone()
                
                if existing:
                    print(f"  ⚠️ Файл уже существует в message_template_files, пропускаем")
                    skipped_count += 1
                else:
                    # Добавляем файл в message_template_files
                    await db.execute('''
                        INSERT INTO message_template_files 
                        (template_id, file_path, file_type, file_name, file_size, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        template_id,
                        file_row['file_path'],
                        file_row['file_type'],
                        file_row['file_name'],
                        file_row['file_size'],
                        file_row['created_at']
                    ))
                    print(f"  ✅ Файл добавлен в message_template_files")
                    migrated_count += 1
            else:
                print(f"  ❌ Шаблон не найден для message_type: {message_type}")
                print(f"     Контент: {content[:50]}...")
                skipped_count += 1
        
        await db.commit()
        
        print(f"\n📊 Результат переноса:")
        print(f"  ✅ Перенесено: {migrated_count}")
        print(f"  ⚠️ Пропущено: {skipped_count}")
        print(f"  📁 Всего обработано: {len(files_to_migrate)}")

if __name__ == "__main__":
    asyncio.run(migrate_files_to_templates())
