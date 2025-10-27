#!/usr/bin/env python3
"""
Скрипт для добавления сообщения book_pricing_info в базу данных
"""

import sqlite3
import sys

DB_PATH = "bookai.db"

def add_book_pricing_info_message():
    """Добавляет сообщение book_pricing_info в базу данных"""
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем, существует ли таблица bot_messages
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='bot_messages'"
        )
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("❌ Таблица bot_messages не существует!")
            print("💡 Запустите сначала: python init_db.py")
            conn.close()
            sys.exit(1)
        
        # Проверяем, существует ли уже это сообщение
        cursor.execute(
            "SELECT id FROM bot_messages WHERE message_key = ?",
            ("book_pricing_info",)
        )
        existing = cursor.fetchone()
        
        if existing:
            print("❌ Сообщение book_pricing_info уже существует в базе данных")
            conn.close()
            return
        
        # Добавляем сообщение
        content = """✨ <b>Авторская книга по вашей уникальной истории</b> ✨

📖 Книга создана специально для вас — с иллюстрациями ваших героев и трогательными словами, собранными из ваших воспоминаний 💝

<b>Что входит:</b>
• 26 уникальных страниц с вашей историей
• Профессиональные иллюстрации героев
• Качественная печать и твердый переплет
• Доставка в любой регион

Нажмите кнопку ниже, чтобы перейти к оплате 👇"""
        
        cursor.execute(
            """INSERT INTO bot_messages 
               (message_key, message_name, content, context, stage, is_editable, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                "book_pricing_info",
                "Информация о книге при оплате",
                content,
                "payment",
                "book_payment",
                1,  # is_editable = True
                1   # is_active = True
            )
        )
        
        conn.commit()
        print("✅ Сообщение book_pricing_info успешно добавлено в базу данных")
        print(f"📝 Содержимое:\n{content}")
        
    except sqlite3.Error as e:
        print(f"❌ Ошибка SQLite: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    add_book_pricing_info_message()
