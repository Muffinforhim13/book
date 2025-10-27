#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для добавления недостающих сообщений в базу данных
"""

import sqlite3
from datetime import datetime

def add_missing_message(message_key, message_name, content, context="book", stage="general"):
    """Добавляет или обновляет сообщение в базе данных"""
    try:
        conn = sqlite3.connect('bookai.db')
        cursor = conn.cursor()
        
        # Проверяем, существует ли сообщение
        cursor.execute("SELECT id FROM bot_messages WHERE message_key = ?", (message_key,))
        existing = cursor.fetchone()
        
        if existing:
            print(f"🔄 Обновляем существующее сообщение: {message_key}")
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
    print("➕ Скрипт для добавления недостающих сообщений")
    print("=" * 50)
    
    # Список недостающих сообщений
    missing_messages = [
        {
            "message_key": "book_last_page_text_saved",
            "message_name": "Подтверждение сохранения текста последней страницы",
            "content": "✅ Текст для последней страницы сохранен!\n\n🎉 Отлично! Первая и последняя страницы готовы! Теперь переходим к выбору обложки.",
            "context": "page_selection",
            "stage": "page_text_saved"
        },
        {
            "message_key": "book_pages_selection_completed",
            "message_name": "Завершение выбора страниц книги",
            "content": "🎉 Выбор страниц завершен!\n\n✅ Выбрано страниц: 24/24\n📚 Ваша книга будет содержать 24 уникальных страниц\n\nВаш выбор отправлен команде сценаристов для создания уникальной книги!",
            "context": "page_selection",
            "stage": "pages_selection_completed"
        }
    ]
    
    print(f"Добавляем {len(missing_messages)} недостающих сообщений...")
    
    success_count = 0
    for msg in missing_messages:
        print(f"\n📝 Обрабатываем: {msg['message_key']}")
        if add_missing_message(
            msg['message_key'], 
            msg['message_name'], 
            msg['content'], 
            msg['context'], 
            msg['stage']
        ):
            success_count += 1
    
    print(f"\n✅ Успешно добавлено/обновлено {success_count} из {len(missing_messages)} сообщений")
    print("🎯 Недостающие сообщения готовы к использованию!")

if __name__ == "__main__":
    main()
