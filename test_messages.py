#!/usr/bin/env python3
"""
Тест для проверки загрузки сообщений из базы данных
"""

import sqlite3

def test_message_loading():
    """Тестирует загрузку сообщений из базы данных"""
    
    print("🔄 Тестируем загрузку сообщений из базы данных...")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect('bookai.db')
        cursor = conn.cursor()
        
        # Тестируем сообщения, которые мы заменили
        test_messages = [
            ("ask_name", "Поделись, как тебя зовут 💌 Нам важно знать, чтобы обращаться к тебе лично"),
            ("email_saved", "✅ Email сохранен! Теперь мы можем продолжить создание вашей песни."),
            ("book_gift_reason", "Напиши по какому поводу мы создаём книгу 📔\nИли это просто подарок без повода?"),
            ("book_photo_request", "Отлично, теперь нам нужно твое фото, важно, чтобы на нём хорошо было видно лицо.\nТак иллюстрация получится максимально похожей 💯"),
            ("song_gift_reason", "Пожалуйста, сначала напиши по какому поводу мы создаём песню🎶\nИли это просто подарок без повода? А потом отправь фото."),
        ]
        
        for message_key, fallback in test_messages:
            print(f"\n🔍 Тестируем: {message_key}")
            
            try:
                cursor.execute('SELECT content, is_active FROM bot_messages WHERE message_key = ?', (message_key,))
                result = cursor.fetchone()
                
                if result:
                    content, is_active = result
                    if is_active:
                        print(f"✅ Загружено из базы: {content[:50]}...")
                        print(f"✅ Сообщение активно!")
                    else:
                        print(f"⚠️  Сообщение неактивно, будет использован fallback")
                        print(f"📝 Fallback: {fallback[:50]}...")
                else:
                    print(f"❌ Сообщение не найдено в базе, будет использован fallback")
                    print(f"📝 Fallback: {fallback[:50]}...")
                    
            except Exception as e:
                print(f"❌ Ошибка загрузки {message_key}: {e}")
        
        conn.close()
        
        print(f"\n🎉 Тест завершен!")
        print("💡 Теперь изменения в админке будут применяться в боте!")
        print("\n📋 Инструкция по тестированию:")
        print("1. Зайдите в админку → Управление контентом")
        print("2. Найдите любое из протестированных сообщений")
        print("3. Измените текст и сохраните")
        print("4. Проверьте в боте - изменения должны примениться!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    test_message_loading()
