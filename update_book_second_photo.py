#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для обновления сообщения book_second_photo_request
"""

import sqlite3
from datetime import datetime

def update_book_second_photo_message():
    """Обновляет сообщение book_second_photo_request с правильным плейсхолдером"""
    try:
        conn = sqlite3.connect('bookai.db')
        cursor = conn.cursor()
        
        message_key = "book_second_photo_request"
        message_name = "Запрос второго фото для книги"
        content = "Благодарим 🙏🏻\n{sender_name}, отправь ещё одно фото лица, можно с другого ракурса — это сделает иллюстрацию ещё точнее 🎯"
        context = "product"
        stage = "photo_request"
        
        # Проверяем, существует ли сообщение
        cursor.execute("SELECT id FROM bot_messages WHERE message_key = ?", (message_key,))
        existing = cursor.fetchone()
        
        if existing:
            print(f"🔄 Обновляем сообщение: {message_key}")
            cursor.execute("""
                UPDATE bot_messages 
                SET message_name = ?, content = ?, context = ?, stage = ?, updated_at = datetime('now')
                WHERE message_key = ?
            """, (message_name, content, context, stage, message_key))
        else:
            print(f"❌ Сообщение {message_key} не найдено в базе данных!")
            return False
            
        conn.commit()
        conn.close()
        print(f"✅ Сообщение '{message_name}' успешно обновлено")
        print(f"📝 Содержимое: {content}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении сообщения {message_key}: {e}")
        return False

def main():
    print("📸 Скрипт для обновления сообщения book_second_photo_request")
    print("=" * 50)
    
    if update_book_second_photo_message():
        print("\n✅ Сообщение обновлено!")
        print("🎯 Теперь плейсхолдер {sender_name} будет правильно заменяться")
    else:
        print("\n❌ Ошибка при обновлении сообщения")

if __name__ == "__main__":
    main()
