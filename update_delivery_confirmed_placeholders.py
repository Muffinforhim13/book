#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для обновления плейсхолдеров в сообщении book_delivery_confirmed
"""

import sqlite3
from datetime import datetime

def update_delivery_confirmed_placeholders():
    """Обновляет плейсхолдеры в сообщении book_delivery_confirmed"""
    try:
        conn = sqlite3.connect('bookai.db')
        cursor = conn.cursor()
        
        message_key = "book_delivery_confirmed"
        content = "✅ Данные доставки сохранены!\n\n📦 Адрес: г. щшовылтдьм\n👤🏼 Получатель: иапмт\n📞 Телефон: 89068714014\n\nТеперь мы отправляем книгу в печать 📖, и она будет доставлена тебе в течение 1–2 недель ✨"
        
        # Обновляем сообщение
        cursor.execute("""
            UPDATE bot_messages 
            SET content = ?, updated_at = datetime('now')
            WHERE message_key = ?
        """, (content, message_key))
        
        conn.commit()
        conn.close()
        print(f"✅ Плейсхолдеры в сообщении '{message_key}' обновлены")
        print(f"📝 Новое содержимое: {content}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении сообщения {message_key}: {e}")
        return False

def main():
    print("🔧 Скрипт для обновления плейсхолдеров в book_delivery_confirmed")
    print("=" * 50)
    
    if update_delivery_confirmed_placeholders():
        print("\n✅ Плейсхолдеры обновлены!")
        print("🎯 Теперь данные пользователя будут правильно подставляться")
    else:
        print("\n❌ Ошибка при обновлении плейсхолдеров")

if __name__ == "__main__":
    main()
