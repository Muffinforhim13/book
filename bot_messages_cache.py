#!/usr/bin/env python3
"""
Модуль для кэширования и получения сообщений бота из базы данных
"""

import asyncio
import logging
from typing import Optional, Dict
from db import get_bot_message_by_key

# Кэш сообщений
_messages_cache: Dict[str, str] = {}
_cache_loaded = False

async def get_message_content(message_key: str, fallback: str = None, force_refresh: bool = False) -> str:
    """
    Получает содержимое сообщения по ключу из базы данных
    Если сообщение не найдено или неактивно, возвращает fallback
    
    Args:
        message_key: Ключ сообщения
        fallback: Резервный текст
        force_refresh: Принудительно обновить из базы (игнорировать кэш)
    """
    global _cache_loaded
    
    # Загружаем кэш при первом обращении
    if not _cache_loaded:
        await _load_messages_cache()
    
    # ВСЕГДА проверяем базу данных для критически важных сообщений
    # Это обеспечивает работу в реальном времени
    try:
        message_data = await get_bot_message_by_key(message_key)
        if message_data and message_data.get('is_active', False):
            content = message_data.get('content', '')
            # Обновляем кэш
            _messages_cache[message_key] = content
            logging.info(f"Загружено сообщение {message_key} из базы (реальное время): {content[:50]}...")
            return content
        else:
            logging.warning(f"Сообщение {message_key} неактивно или не найдено")
    except Exception as e:
        logging.error(f"Ошибка получения сообщения {message_key}: {e}")
        # В случае ошибки, не прерываем выполнение, продолжаем с кэшем
    
    # Если не удалось получить из базы, проверяем кэш
    if message_key in _messages_cache:
        cached_content = _messages_cache[message_key]
        logging.info(f"Использовано сообщение {message_key} из кэша: {cached_content[:50]}...")
        return cached_content
    
    # Возвращаем fallback или сообщение об ошибке
    if fallback:
        return fallback
    
    return f"❌ Сообщение {message_key} не найдено"

async def _load_messages_cache():
    """Загружает все активные сообщения в кэш"""
    global _cache_loaded, _messages_cache
    
    try:
        from db import get_bot_messages
        messages = await get_bot_messages()
        
        for message in messages:
            if message.get('is_active', False):
                _messages_cache[message['message_key']] = message['content']
        
        _cache_loaded = True
        logging.info(f"Загружено {len(_messages_cache)} сообщений в кэш")
        
    except Exception as e:
        logging.error(f"Ошибка загрузки кэша сообщений: {e}")
        _cache_loaded = True  # Помечаем как загруженный, чтобы не пытаться снова

def clear_cache():
    """Очищает кэш сообщений (для обновления после редактирования)"""
    global _messages_cache, _cache_loaded
    _messages_cache.clear()
    _cache_loaded = False
    logging.info("Кэш сообщений очищен")

async def refresh_cache():
    """Обновляет кэш сообщений"""
    clear_cache()
    await _load_messages_cache()

async def update_message_in_cache(message_key: str, new_content: str):
    """Обновляет конкретное сообщение в кэше"""
    global _messages_cache
    _messages_cache[message_key] = new_content
    logging.info(f"Обновлено сообщение {message_key} в кэше: {new_content[:50]}...")

async def invalidate_message_cache(message_key: str):
    """Удаляет сообщение из кэша (заставит перезагрузить из базы)"""
    global _messages_cache
    if message_key in _messages_cache:
        del _messages_cache[message_key]
        logging.info(f"Удалено сообщение {message_key} из кэша")

async def force_refresh_message(message_key: str):
    """Принудительно обновляет конкретное сообщение из базы данных"""
    global _messages_cache
    try:
        message_data = await get_bot_message_by_key(message_key)
        if message_data and message_data.get('is_active', False):
            content = message_data.get('content', '')
            _messages_cache[message_key] = content
            logging.info(f"Принудительно обновлено сообщение {message_key}: {content[:50]}...")
            return content
        else:
            # Если сообщение неактивно, удаляем из кэша
            if message_key in _messages_cache:
                del _messages_cache[message_key]
            logging.info(f"Сообщение {message_key} неактивно, удалено из кэша")
            return None
    except Exception as e:
        logging.error(f"Ошибка принудительного обновления сообщения {message_key}: {e}")
        return None

# Предопределенные ключи сообщений для удобства
MESSAGE_KEYS = {
    'WELCOME': 'welcome_message',
    'PHONE_REQUEST': 'phone_request', 
    'NAME_REQUEST': 'name_request',
    'LASTNAME_REQUEST': 'lastname_request',
    'REGISTRATION_SUCCESS': 'registration_success',
    'PRODUCT_SELECTION': 'product_selection',
    'PRODUCT_BOOK': 'product_book',
    'PRODUCT_SONG': 'product_song',
    'GENDER_REQUEST': 'gender_request',
    'RELATION_CHOICE': 'relation_choice',
    'RECIPIENT_NAME_REQUEST': 'recipient_name_request',
    'BOOK_INTRO': 'book_intro',
    'GIFT_REASON_REQUEST': 'gift_reason_request',
    'MAIN_FACE_1_REQUEST': 'main_face_1_request',
    'MAIN_FACE_2_REQUEST': 'main_face_2_request',
    'ERROR_MESSAGE': 'error_message',
    'HELP_MESSAGE': 'help_message',
}

# Удобные функции для получения конкретных сообщений
async def get_welcome_message(force_refresh: bool = False) -> str:
    # Принудительно обновляем кэш
    await invalidate_message_cache(MESSAGE_KEYS['WELCOME'])
    
    return await get_message_content(MESSAGE_KEYS['WELCOME'], 
        None,  # Убираем hardcoded fallback
        True)  # Всегда принудительно обновляем

async def get_phone_request(force_refresh: bool = False) -> str:
    return await get_message_content(MESSAGE_KEYS['PHONE_REQUEST'],
        None,  # Убираем hardcoded fallback
        force_refresh)

async def get_name_request(force_refresh: bool = False) -> str:
    return await get_message_content(MESSAGE_KEYS['NAME_REQUEST'],
        None,  # Убираем hardcoded fallback
        force_refresh)

async def get_product_selection(force_refresh: bool = False) -> str:
    return await get_message_content(MESSAGE_KEYS['PRODUCT_SELECTION'],
        None,  # Убираем hardcoded fallback
        force_refresh)

async def get_gender_request(force_refresh: bool = False) -> str:
    return await get_message_content(MESSAGE_KEYS['GENDER_REQUEST'],
        None,  # Убираем hardcoded fallback
        force_refresh)

async def get_book_intro(force_refresh: bool = False) -> str:
    return await get_message_content(MESSAGE_KEYS['BOOK_INTRO'],
        None,  # Убираем hardcoded fallback
        force_refresh)

async def get_error_message(force_refresh: bool = False) -> str:
    return await get_message_content(MESSAGE_KEYS['ERROR_MESSAGE'],
        None,  # Убираем hardcoded fallback
        force_refresh)