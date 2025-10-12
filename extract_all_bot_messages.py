#!/usr/bin/env python3
"""
Скрипт для извлечения ВСЕХ сообщений из кода бота
"""

import re
import os

def extract_messages_from_bot():
    """Извлекает все сообщения из файла bot.py"""
    
    print("🔍 Извлекаем все сообщения из bot.py...")
    
    bot_file = "bot.py"
    if not os.path.exists(bot_file):
        print(f"❌ Файл {bot_file} не найден")
        return []
    
    with open(bot_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    messages = []
    
    # Паттерны для поиска сообщений
    patterns = [
        # await message.answer("текст")
        r'await\s+\w+\.answer\(["\']([^"\']+)["\']',
        # await callback.message.answer("текст")
        r'await\s+\w+\.message\.answer\(["\']([^"\']+)["\']',
        # await callback.message.edit_text("текст")
        r'await\s+\w+\.message\.edit_text\(["\']([^"\']+)["\']',
        # await message.edit_text("текст")
        r'await\s+\w+\.edit_text\(["\']([^"\']+)["\']',
        # Трехстрочные строки
        r'["\']([^"\']*\n[^"\']*\n[^"\']*)["\']',
        # Многострочные строки с \n
        r'["\']([^"\']*\\n[^"\']*)["\']',
    ]
    
    found_messages = set()
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
        for match in matches:
            # Очищаем сообщение
            message = match.strip()
            if len(message) > 5 and not message.startswith('http') and not message.startswith('file_'):
                # Убираем экранированные символы
                message = message.replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'")
                found_messages.add(message)
    
    # Также ищем константы
    const_patterns = [
        r'WELCOME_TEXT\s*=\s*["\']([^"\']+)["\']',
        r'["\']([^"\']*Привет[^"\']*)["\']',
        r'["\']([^"\']*выберите[^"\']*)["\']',
        r'["\']([^"\']*отправьте[^"\']*)["\']',
        r'["\']([^"\']*введите[^"\']*)["\']',
        r'["\']([^"\']*расскажите[^"\']*)["\']',
        r'["\']([^"\']*пожалуйста[^"\']*)["\']',
    ]
    
    for pattern in const_patterns:
        matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
        for match in matches:
            message = match.strip()
            if len(message) > 5:
                message = message.replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'")
                found_messages.add(message)
    
    # Преобразуем в список и сортируем
    messages = list(found_messages)
    messages.sort()
    
    print(f"📊 Найдено {len(messages)} уникальных сообщений")
    
    return messages

def categorize_messages(messages):
    """Категоризирует сообщения по типам"""
    
    categories = {
        'welcome': [],
        'registration': [],
        'product_selection': [],
        'book_flow': [],
        'song_flow': [],
        'photo_requests': [],
        'questions': [],
        'errors': [],
        'buttons': [],
        'other': []
    }
    
    for message in messages:
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['привет', 'добро пожаловать', 'готов начать']):
            categories['welcome'].append(message)
        elif any(word in message_lower for word in ['номер телефона', 'имя', 'фамилия', 'контакт']):
            categories['registration'].append(message)
        elif any(word in message_lower for word in ['что вы хотите создать', 'книга', 'песня', 'выберите']):
            categories['product_selection'].append(message)
        elif any(word in message_lower for word in ['пол', 'отношение', 'получатель', 'расскажите', 'повод']):
            categories['book_flow'].append(message)
        elif any(word in message_lower for word in ['голос', 'пение', 'мелодия']):
            categories['song_flow'].append(message)
        elif any(word in message_lower for word in ['фото', 'отправьте', 'лицом', 'полный рост']):
            categories['photo_requests'].append(message)
        elif any(word in message_lower for word in ['вопрос', 'трогательный', 'восхищает', 'воспоминания']):
            categories['questions'].append(message)
        elif any(word in message_lower for word in ['ошибка', 'попробуйте еще раз', 'поддержка']):
            categories['errors'].append(message)
        elif any(word in message_lower for word in ['далее', 'назад', 'да', 'нет']):
            categories['buttons'].append(message)
        else:
            categories['other'].append(message)
    
    return categories

def main():
    """Основная функция"""
    
    messages = extract_messages_from_bot()
    
    if not messages:
        print("❌ Сообщения не найдены")
        return
    
    print("\n📋 Все найденные сообщения:")
    print("=" * 80)
    
    for i, message in enumerate(messages, 1):
        print(f"{i:3d}. {message}")
        print("-" * 80)
    
    print(f"\n📊 Категоризация:")
    categories = categorize_messages(messages)
    
    for category, msgs in categories.items():
        if msgs:
            print(f"\n{category.upper()} ({len(msgs)} сообщений):")
            for msg in msgs:
                print(f"  - {msg[:100]}{'...' if len(msg) > 100 else ''}")

if __name__ == "__main__":
    main()
