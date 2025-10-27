#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для обновления конкретных сообщений в базе данных
"""

import sqlite3
from datetime import datetime

def update_specific_message(message_key, message_name, content, context="book", stage="general"):
    """Обновляет конкретное сообщение в базе данных"""
    try:
        conn = sqlite3.connect('bookai.db')
        cursor = conn.cursor()
        
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
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении сообщения {message_key}: {e}")
        return False

def main():
    print("🔧 Скрипт для обновления конкретных сообщений")
    print("=" * 50)
    
    # Список сообщений для обновления
    messages_to_update = [
        {
            "message_key": "book_payment_success_delivery",
            "message_name": "Успешная оплата и запрос доставки",
            "content": "✅ Доплата прошла успешно!\n\nТеперь нам нужны ваши данные для доставки печатной книги.\n\nПожалуйста, введите адрес доставки, например: 455000, Республика Татарстан, г. Казань, ул. Ленина, д. 52, кв. 43",
            "context": "book",
            "stage": "payment_success"
        },
        {
            "message_key": "book_invalid_phone",
            "message_name": "Некорректный номер телефона",
            "content": "❌ Неверный формат номера телефона!\n\nПожалуйста, введите номер в одном из форматов:\n• +7 (999) 123-45-67\n• 89991234567\n• 9991234567\n\nПопробуйте еще раз:",
            "context": "book",
            "stage": "delivery_phone"
        }
    ]
    
    print(f"Обновляем {len(messages_to_update)} сообщений...")
    
    success_count = 0
    for msg in messages_to_update:
        print(f"\n📝 Обновляем: {msg['message_key']}")
        if update_specific_message(
            msg['message_key'], 
            msg['message_name'], 
            msg['content'], 
            msg['context'], 
            msg['stage']
        ):
            success_count += 1
    
    print(f"\n✅ Успешно обновлено {success_count} из {len(messages_to_update)} сообщений")
    print("🎯 Конкретные сообщения обновлены!")

if __name__ == "__main__":
    main()
