#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для добавления сообщения о готовности книги
"""

import sqlite3
from datetime import datetime

def add_book_ready_message():
    """Добавляет сообщение о готовности книги"""
    try:
        conn = sqlite3.connect('bookai.db')
        cursor = conn.cursor()
        
        message_key = "book_ready_message"
        message_name = "Сообщение о готовности книги"
        content = "🎉 Ваша книга готова! Спасибо, что выбрали нас ❤️\n\nМы подготовили для вас электронную версию (PDF). Ссылка для скачивания будет отправлена в ближайшее время!"
        context = "product"
        stage = "book_ready"
        
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
    print("📚 Скрипт для добавления сообщения о готовности книги")
    print("=" * 50)
    
    if add_book_ready_message():
        print("\n✅ Сообщение добавлено!")
        print("🎯 Теперь сообщение будет редактироваться через админку")
    else:
        print("\n❌ Ошибка при добавлении сообщения")

if __name__ == "__main__":
    main()
