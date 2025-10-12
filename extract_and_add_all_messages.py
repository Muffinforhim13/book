#!/usr/bin/env python3
"""
Скрипт для извлечения ВСЕХ сообщений из кода бота и добавления их в базу данных
"""

import re
import os
import asyncio
import sys

# Добавляем путь к модулям проекта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import upsert_bot_message

def extract_messages_from_bot():
    """Извлекает все сообщения из файла bot.py"""
    
    print("🔍 Извлекаем все сообщения из bot.py...")
    
    bot_file = "bot.py"
    if not os.path.exists(bot_file):
        print(f"❌ Файл {bot_file} не найден")
        return []
    
    with open(bot_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    found_messages = set()
    
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
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
        for match in matches:
            # Очищаем сообщение
            message = match.strip()
            if len(message) > 5 and not message.startswith('http') and not message.startswith('file_'):
                # Убираем экранированные символы
                message = message.replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'")
                found_messages.add(message)
    
    # Также ищем константы и специальные сообщения
    const_patterns = [
        r'WELCOME_TEXT\s*=\s*["\']([^"\']+)["\']',
        r'["\']([^"\']*Привет[^"\']*)["\']',
        r'["\']([^"\']*выберите[^"\']*)["\']',
        r'["\']([^"\']*отправьте[^"\']*)["\']',
        r'["\']([^"\']*введите[^"\']*)["\']',
        r'["\']([^"\']*расскажите[^"\']*)["\']',
        r'["\']([^"\']*пожалуйста[^"\']*)["\']',
        r'["\']([^"\']*укажите[^"\']*)["\']',
        r'["\']([^"\']*спасибо[^"\']*)["\']',
        r'["\']([^"\']*ошибка[^"\']*)["\']',
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

def categorize_and_create_messages(messages):
    """Категоризирует сообщения и создает структуру для базы данных"""
    
    categorized_messages = []
    sort_order = 1
    
    for message in messages:
        message_lower = message.lower()
        
        # Определяем контекст и этап
        context = "other"
        stage = "general"
        message_name = f"Сообщение {sort_order}"
        
        if any(word in message_lower for word in ['привет', 'добро пожаловать', 'готов начать']):
            context = "welcome"
            stage = "start"
            message_name = "Приветственное сообщение"
        elif any(word in message_lower for word in ['номер телефона', 'контакт']):
            context = "registration"
            stage = "phone"
            message_name = "Запрос номера телефона"
        elif any(word in message_lower for word in ['введите ваше имя', 'ваше имя']):
            context = "registration"
            stage = "name"
            message_name = "Запрос имени"
        elif any(word in message_lower for word in ['фамилию']):
            context = "registration"
            stage = "lastname"
            message_name = "Запрос фамилии"
        elif any(word in message_lower for word in ['данные сохранены', 'спасибо']):
            context = "registration"
            stage = "success"
            message_name = "Регистрация успешна"
        elif any(word in message_lower for word in ['что вы хотите создать']):
            context = "product"
            stage = "selection"
            message_name = "Выбор продукта"
        elif any(word in message_lower for word in ['книга']) and len(message) < 20:
            context = "product"
            stage = "book"
            message_name = "Книга"
        elif any(word in message_lower for word in ['песня']) and len(message) < 20:
            context = "product"
            stage = "song"
            message_name = "Песня"
        elif any(word in message_lower for word in ['выберите ваш пол', 'пол']):
            context = "book"
            stage = "gender"
            message_name = "Запрос пола"
        elif any(word in message_lower for word in ['кому вы хотите подарить', 'отношение']):
            context = "book"
            stage = "relation"
            message_name = "Выбор отношения"
        elif any(word in message_lower for word in ['имя получателя']):
            context = "book"
            stage = "recipient"
            message_name = "Запрос имени получателя"
        elif any(word in message_lower for word in ['расскажите немного о себе', 'герое']):
            context = "hero"
            stage = "intro"
            message_name = "Введение в создание книги"
        elif any(word in message_lower for word in ['повод для подарка', 'день рождения']):
            context = "hero"
            stage = "gift_reason"
            message_name = "Запрос повода для подарка"
        elif any(word in message_lower for word in ['фото', 'отправьте']):
            context = "photo"
            if 'первое фото' in message_lower:
                stage = "main_face_1"
                message_name = "Запрос первого фото"
            elif 'второе фото' in message_lower:
                stage = "main_face_2"
                message_name = "Запрос второго фото"
            elif 'полный рост' in message_lower:
                stage = "main_body"
                message_name = "Запрос фото в полный рост"
            elif 'занятием' in message_lower:
                stage = "main_activity"
                message_name = "Запрос фото активности"
            else:
                stage = "general"
                message_name = "Запрос фото"
        elif any(word in message_lower for word in ['трогательный момент', 'восхищает', 'воспоминания']):
            context = "question"
            stage = "general"
            message_name = "Вопрос пользователю"
        elif any(word in message_lower for word in ['голос', 'пение', 'мелодия']):
            context = "song"
            stage = "voice"
            message_name = "Запрос голосового сообщения"
        elif any(word in message_lower for word in ['ошибка', 'попробуйте еще раз']):
            context = "error"
            stage = "general"
            message_name = "Сообщение об ошибке"
        elif any(word in message_lower for word in ['далее', 'назад', 'да', 'нет']):
            context = "button"
            stage = "general"
            message_name = "Кнопка"
        elif any(word in message_lower for word in ['поддержка', 'помощь']):
            context = "info"
            stage = "help"
            message_name = "Сообщение помощи"
        
        # Создаем ключ сообщения
        message_key = f"{context}_{stage}_{sort_order}"
        
        categorized_messages.append({
            'key': message_key,
            'name': message_name,
            'content': message,
            'context': context,
            'stage': stage,
            'sort_order': sort_order
        })
        
        sort_order += 1
    
    return categorized_messages

async def add_all_messages_to_db():
    """Добавляет все найденные сообщения в базу данных"""
    
    print("🔄 Извлекаем и добавляем все сообщения...")
    
    # Извлекаем сообщения из кода
    messages = extract_messages_from_bot()
    
    if not messages:
        print("❌ Сообщения не найдены")
        return
    
    # Категоризируем сообщения
    categorized_messages = categorize_and_create_messages(messages)
    
    print(f"📝 Добавляем {len(categorized_messages)} сообщений в базу данных...")
    
    added_count = 0
    error_count = 0
    
    for msg in categorized_messages:
        try:
            message_id = await upsert_bot_message(
                msg['key'], 
                msg['name'], 
                msg['content'], 
                msg['context'], 
                msg['stage'], 
                msg['sort_order']
            )
            print(f"✅ Добавлено: {msg['name']} (ID: {message_id})")
            added_count += 1
        except Exception as e:
            print(f"❌ Ошибка добавления {msg['name']}: {e}")
            error_count += 1
    
    print(f"\n🎉 Добавление завершено!")
    print(f"   ✅ Добавлено сообщений: {added_count}")
    print(f"   ❌ Ошибок: {error_count}")
    
    if added_count > 0:
        print(f"\n💡 Теперь в админке будут показаны ВСЕ реальные сообщения бота!")

if __name__ == "__main__":
    asyncio.run(add_all_messages_to_db())
