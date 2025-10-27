#!/usr/bin/env python3
"""
Скрипт для добавления общих сообщений в базу данных
"""

import sqlite3
import sys
from datetime import datetime

def add_general_message(message_key, message_name, content, stage="general"):
    """Добавляет общее сообщение в базу данных"""
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
            """, (message_name, content, 'common', stage, message_key))
        else:
            print(f"➕ Добавляем новое сообщение: {message_key}")
            cursor.execute("""
                INSERT INTO bot_messages 
                (message_key, message_name, content, context, stage, sort_order, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 0, 1, datetime('now'), datetime('now'))
            """, (message_key, message_name, content, 'common', stage))
        
        conn.commit()
        conn.close()
        print(f"✅ Сообщение '{message_name}' успешно добавлено/обновлено")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при добавлении сообщения {message_key}: {e}")
        return False

def main():
    print("📝 Скрипт для добавления общих сообщений")
    print("=" * 50)
    
    # Добавляем все общие сообщения
    messages = [
        ("welcome_message", "Приветственное сообщение", 
         "❌ Сообщение welcome_message не найдено", 
         "welcome"),
        
        ("ask_name", "Запрос имени пользователя", 
         "Поделись, как тебя зовут 💌 Нам важно знать, чтобы обращаться к тебе лично", 
         "name_request"),
        
        ("privacy_consent_request", "Запрос согласия на обработку персональных данных", 
         "✅ Спасибо за доверие! Ваш заказ №0458 уже в работе ❤️\nЧтобы мы могли создать ваш особенный подарок, нам нужно ваше согласие на обработку персональных данных.\n\n📋 Вся информация о том, как мы бережно храним ваши данные, здесь:\n1. Согласие на обработку персональных данных\n2. Оферта о заключении договора оказания услуг, Политика конфиденциальности и обработки персональных данных\n\nДаете согласие на обработку персональных данных? 💕", 
         "privacy_consent"),
        
        ("privacy_reassurance", "Успокоение по поводу конфиденциальности", 
         "📋 Понимаем твои опасения — доверие очень важно ❤️\nМы храним данные так же бережно, как создаем подарки. ✨ За все годы работы ни одна личная информация не была передана третьим лицам — мы дорожим каждой семьей, которая нам доверяет и репутацией компании 💕\nМожет, все же попробуем создать что-то особенное вместе? Мы гарантируем, что твой подарок тронет до мурашек📖", 
         "privacy_reassurance"),
        
        ("privacy_consent_confirmed", "Подтверждение получения согласия", 
         "✅ Спасибо! Ваше согласие получено.", 
         "privacy_consent"),
        
        ("email_request", "Запрос email адреса", 
         "Оставь, пожалуйста, свой email адрес. 📩 ✨ Это нужно для того, чтобы гарантированно отправить вам все материалы — на случай, если с Телеграмом что-то случится, мы всегда сможем с вами связаться 🩷", 
         "email_request"),
        
        ("email_saved", "Подтверждение сохранения email", 
         "✅ Email сохранен! Теперь мы можем продолжить создание вашей книги.", 
         "email_request")
    ]
    
    print(f"Добавляем {len(messages)} общих сообщений...")
    
    success_count = 0
    for message_key, message_name, content, stage in messages:
        if add_general_message(message_key, message_name, content, stage):
            success_count += 1
    
    print(f"\n✅ Успешно добавлено {success_count} из {len(messages)} сообщений")
    print("📝 Общие сообщения готовы к редактированию в админке!")

if __name__ == "__main__":
    main()
