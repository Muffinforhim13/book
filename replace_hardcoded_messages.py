#!/usr/bin/env python3
"""
Скрипт для замены хардкод сообщений в bot.py на вызовы из базы данных
"""

import re
import sqlite3

# Маппинг хардкод сообщений на ключи в базе данных
MESSAGE_MAPPING = {
    # Регистрация
    "Пожалуйста, отправьте ваш номер телефона, нажав кнопку ниже, а затем отправьте контакт вручную.": "phone_request",
    "Поделись, как тебя зовут 💌 Нам важно знать, чтобы обращаться к тебе лично": "ask_name",
    "Спасибо! Данные сохранены.": "registration_success",
    
    # Email
    "❌ Пожалуйста, введите корректный email адрес.": "email_invalid",
    "✅ Email сохранен! Теперь мы можем продолжить создание вашей песни.": "email_saved",
    "✅ Email сохранен! Теперь мы можем продолжить создание вашей книги.": "email_saved",
    
    # Ошибки
    "❌ Произошла ошибка при получении вопросов. Попробуйте еще раз.": "error_questions",
    "Произошла ошибка при обработке email. Попробуйте еще раз.": "error_email",
    "Произошла ошибка. Попробуйте еще раз.": "error_general",
    "Произошла ошибка при создании заказа. Попробуйте еще раз или обратитесь в поддержку.": "error_order_creation",
    "Произошла ошибка при сохранении данных. Попробуйте еще раз или обратитесь в поддержку.": "error_save_data",
    
    # Книга
    "Напиши по какому поводу мы создаём книгу 📔\nИли это просто подарок без повода?": "book_gift_reason",
    "Отлично, теперь нам нужно твое фото, важно, чтобы на нём хорошо было видно лицо.\nТак иллюстрация получится максимально похожей 💯": "book_photo_request",
    
    # Песня
    "Пожалуйста, сначала напиши по какому поводу мы создаём песню🎶\nИли это просто подарок без повода? А потом отправь фото.": "song_gift_reason",
    
    # Приветствие
    "👋 Привет! Готов начать создание подарка?": "welcome_ready",
}

def check_message_exists(message_key: str) -> bool:
    """Проверяет, существует ли сообщение в базе данных"""
    try:
        conn = sqlite3.connect('bookai.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM bot_messages WHERE message_key = ?', (message_key,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception as e:
        print(f"Ошибка проверки сообщения {message_key}: {e}")
        return False

def replace_hardcoded_messages():
    """Заменяет хардкод сообщения на вызовы из базы данных"""
    
    # Читаем файл bot.py
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    replacements_made = 0
    
    # Заменяем каждое хардкод сообщение
    for hardcoded_text, message_key in MESSAGE_MAPPING.items():
        # Экранируем специальные символы для regex
        escaped_text = re.escape(hardcoded_text)
        
        # Паттерн для поиска await message.answer("текст")
        pattern = rf'await\s+message\.answer\(\s*["\']({escaped_text})["\']\s*([^)]*)\)'
        
        # Замена на вызов из базы данных
        replacement = f'await message.answer(await get_message_content("{message_key}", "{hardcoded_text}"), \\2)'
        
        # Выполняем замену
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
        
        if new_content != content:
            print(f"✅ Заменено: {message_key}")
            print(f"   Текст: {hardcoded_text[:50]}...")
            replacements_made += 1
            content = new_content
    
    # Также заменяем await callback.answer() сообщения
    callback_messages = {
        "Произошла ошибка. Попробуйте еще раз.": "error_general",
    }
    
    for hardcoded_text, message_key in callback_messages.items():
        escaped_text = re.escape(hardcoded_text)
        pattern = rf'await\s+callback\.answer\(\s*["\']({escaped_text})["\']\s*\)'
        replacement = f'await callback.answer(await get_message_content("{message_key}", "{hardcoded_text}"))'
        
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
        
        if new_content != content:
            print(f"✅ Заменено callback: {message_key}")
            replacements_made += 1
            content = new_content
    
    # Если были изменения, сохраняем файл
    if content != original_content:
        # Создаем резервную копию
        with open('bot.py.backup', 'w', encoding='utf-8') as f:
            f.write(original_content)
        print(f"\n📁 Создана резервная копия: bot.py.backup")
        
        # Сохраняем обновленный файл
        with open('bot.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"\n🎉 Заменено {replacements_made} хардкод сообщений!")
        print("📝 Файл bot.py обновлен")
        
        # Добавляем импорт get_message_content если его нет
        if 'from bot_messages_cache import get_message_content' not in content:
            print("\n⚠️  Необходимо добавить импорт:")
            print("from bot_messages_cache import get_message_content")
    else:
        print("ℹ️  Хардкод сообщения не найдены или уже заменены")

def main():
    """Основная функция"""
    print("🔄 Замена хардкод сообщений на вызовы из базы данных...")
    print("=" * 60)
    
    # Проверяем, какие сообщения существуют в базе
    print("🔍 Проверяем сообщения в базе данных...")
    missing_messages = []
    
    for hardcoded_text, message_key in MESSAGE_MAPPING.items():
        exists = check_message_exists(message_key)
        if not exists:
            missing_messages.append(message_key)
            print(f"❌ Сообщение не найдено: {message_key}")
        else:
            print(f"✅ Сообщение найдено: {message_key}")
    
    if missing_messages:
        print(f"\n⚠️  Найдено {len(missing_messages)} отсутствующих сообщений в базе данных")
        print("Рекомендуется добавить их в базу данных перед заменой")
        
        response = input("\nПродолжить замену? (y/N): ")
        if response.lower() != 'y':
            print("Отменено")
            return
    
    # Выполняем замену
    print(f"\n🔄 Выполняем замену...")
    replace_hardcoded_messages()
    
    print(f"\n✅ Готово! Теперь бот будет использовать сообщения из базы данных.")
    print("💡 Изменения в админке будут применяться в реальном времени!")

if __name__ == "__main__":
    main()
