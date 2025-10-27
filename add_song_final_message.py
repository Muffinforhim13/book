#!/usr/bin/env python3
"""
Скрипт для добавления финального сообщения песни в базу данных
"""

import sqlite3
import sys
from datetime import datetime

def add_song_final_message(message_key, message_name, content, stage="general"):
    """Добавляет финальное сообщение песни в базу данных"""
    try:
        conn = sqlite3.connect('bookai.db')
        cursor = conn.cursor()
        
        # Проверяем, существует ли уже сообщение
        cursor.execute("SELECT id FROM bot_messages WHERE message_key = ?", (message_key,))
        existing = cursor.fetchone()
        
        if existing:
            print(f"⚠️  Сообщение {message_key} уже существует, обновляем...")
            cursor.execute("""
                UPDATE bot_messages 
                SET message_name = ?, content = ?, context = ?, stage = ?, updated_at = datetime('now')
                WHERE message_key = ?
            """, (message_name, content, 'song', stage, message_key))
        else:
            print(f"➕ Добавляем новое сообщение: {message_key}")
            cursor.execute("""
                INSERT INTO bot_messages 
                (message_key, message_name, content, context, stage, sort_order, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 0, 1, datetime('now'), datetime('now'))
            """, (message_key, message_name, content, 'song', stage))
        
        conn.commit()
        conn.close()
        print(f"✅ Сообщение '{message_name}' успешно добавлено/обновлено")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при добавлении сообщения {message_key}: {e}")
        return False

def main():
    print("🎵 Скрипт для добавления финального сообщения песни")
    print("=" * 50)
    
    # Добавляем финальное сообщение песни
    message_key = "song_final_goodbye"
    message_name = "Финальное прощание песни"
    content = "Спасибо, что выбрал именно нас для создания своего сокровенного подарка💝\n\nКогда захочешь снова подарить эмоции и тронуть сердце близкого человека — возвращайся 🫶🏻\n\nМы будем здесь для тебя,\nКоманда \"В самое сердце\" 💖"
    stage = "final_goodbye"
    
    print(f"Добавляем финальное сообщение песни...")
    
    if add_song_final_message(message_key, message_name, content, stage):
        print(f"\n✅ Финальное сообщение песни успешно добавлено!")
        print("🎵 Сообщение готово к редактированию в админке!")
    else:
        print(f"\n❌ Ошибка при добавлении финального сообщения")

if __name__ == "__main__":
    main()
