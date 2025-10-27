#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для добавления сообщения о совместном фото в путь книги
"""

import sqlite3
from datetime import datetime

def add_joint_photo_message(message_key, message_name, content, context, stage="general"):
    """Добавляет сообщение о совместном фото"""
    try:
        conn = sqlite3.connect('bookai.db')
        cursor = conn.cursor()
        
        # Проверяем, существует ли сообщение
        cursor.execute("SELECT id FROM bot_messages WHERE message_key = ?", (message_key,))
        existing = cursor.fetchone()
        
        if existing:
            print(f"⚠️  Сообщение {message_key} уже существует, обновляем...")
            cursor.execute("""
                UPDATE bot_messages 
                SET message_name = ?, content = ?, context = ?, stage = ?, updated_at = datetime('now')
                WHERE message_key = ?
            """, (message_name, content, context, stage, message_key))
        else:
            print(f"➕ Добавляем новое сообщение: {message_key}")
            cursor.execute("""
                INSERT INTO bot_messages 
                (message_key, message_name, content, context, stage, sort_order, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 0, 1, datetime('now'), datetime('now'))
            """, (message_key, message_name, content, context, stage))
        
        conn.commit()
        conn.close()
        print(f"✅ Сообщение '{message_name}' успешно добавлено/обновлено")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при добавлении сообщения {message_key}: {e}")
        return False

def main():
    print("📸 Скрипт для добавления сообщения о совместном фото")
    print("=" * 50)
    
    message_key = "book_joint_photo_request"
    message_name = "Запрос совместного фото"
    content = "Какие вы красивые!\n\nЕсли у вас есть совместное фото, которое ты готов нам отправить, пришли его нам"
    context = "book"
    stage = "joint_photo_request"
    
    print(f"Добавляем сообщение о совместном фото...")
    if add_joint_photo_message(message_key, message_name, content, context, stage):
        pass  # Success message already printed
    
    print(f"\n✅ Сообщение о совместном фото готово к редактированию в админке!")

if __name__ == "__main__":
    main()
