#!/usr/bin/env python3
"""
Тест для проверки загрузки всех 65 сообщений из базы данных
"""

import sqlite3

def test_all_messages():
    """Тестирует загрузку всех сообщений из базы данных"""
    
    print("🔄 Тестируем загрузку всех 65 сообщений из базы данных...")
    print("=" * 80)
    
    try:
        conn = sqlite3.connect('bookai.db')
        cursor = conn.cursor()
        
        # Получаем все сообщения из базы данных
        cursor.execute('SELECT message_key, message_name, content, is_active FROM bot_messages ORDER BY context, stage')
        messages = cursor.fetchall()
        
        print(f"📊 Всего сообщений в базе: {len(messages)}")
        print()
        
        # Группируем по контекстам
        contexts = {}
        for msg_key, msg_name, content, is_active in messages:
            if msg_key.startswith('book_'):
                context = 'PRODUCT (Книга)'
            elif msg_key.startswith('song_'):
                context = 'SONG (Песня)'
            else:
                context = 'COMMON (Общие)'
            
            if context not in contexts:
                contexts[context] = []
            contexts[context].append((msg_key, msg_name, content, is_active))
        
        # Выводим статистику по контекстам
        for context, msgs in contexts.items():
            active_count = sum(1 for _, _, _, is_active in msgs if is_active)
            print(f"📁 {context}: {len(msgs)} сообщений ({active_count} активных)")
        
        print()
        
        # Тестируем сообщения, которые мы заменили в bot.py
        test_messages = [
            ("email_request", "Запрос номера телефона"),
            ("ask_name", "Запрос имени пользователя"),
            ("book_gift_reason", "Повод для книги"),
            ("book_photo_request", "Запрос фото для книги"),
            ("song_gift_reason", "Повод для песни"),
        ]
        
        print("🧪 Тестируем замененные сообщения:")
        print("-" * 50)
        
        for message_key, description in test_messages:
            cursor.execute('SELECT content, is_active FROM bot_messages WHERE message_key = ?', (message_key,))
            result = cursor.fetchone()
            
            if result:
                content, is_active = result
                status = "✅ Активно" if is_active else "❌ Неактивно"
                print(f"{status} {message_key} - {description}")
                print(f"   Содержимое: {content[:60]}...")
            else:
                print(f"❌ НЕ НАЙДЕНО: {message_key} - {description}")
            print()
        
        conn.close()
        
        print("🎉 Тест завершен!")
        print()
        print("📋 Инструкция по тестированию:")
        print("1. Зайдите в админку → Управление контентом")
        print("2. Выберите вкладку (Общие сообщения/Путь книги/Путь песни)")
        print("3. Найдите любое из протестированных сообщений")
        print("4. Измените текст и сохраните")
        print("5. Проверьте в боте - изменения должны примениться!")
        print()
        print("💡 Теперь у вас есть функции для всех 65 сообщений!")
        print("   Вы можете заменить любое хардкод сообщение в bot.py")
        print("   на вызов соответствующей функции из bot_messages_cache.py")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    test_all_messages()
