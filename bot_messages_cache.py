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
    
    # ВСЕГДА проверяем базу данных для актуальных данных
    # Это обеспечивает работу в реальном времени при изменениях в админке
    try:
        message_data = await get_bot_message_by_key(message_key)
        if message_data and message_data.get('is_active', False):
            content = message_data.get('content', '')
            # Обновляем кэш актуальными данными
            _messages_cache[message_key] = content
            logging.info(f"Загружено сообщение {message_key} из базы (реальное время): {content[:50]}...")
            return content
        elif message_data and not message_data.get('is_active', False):
            # Сообщение неактивно - удаляем из кэша
            if message_key in _messages_cache:
                del _messages_cache[message_key]
            logging.warning(f"Сообщение {message_key} неактивно, удалено из кэша")
            return fallback if fallback else f"❌ Сообщение {message_key} неактивно"
        else:
            logging.warning(f"Сообщение {message_key} не найдено в базе данных")
            # Если сообщение не найдено в базе, удаляем из кэша
            if message_key in _messages_cache:
                del _messages_cache[message_key]
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

async def get_message_content_realtime(message_key: str, fallback: str = None) -> str:
    """Получает сообщение с принудительным обновлением из базы данных (как get_welcome_message)"""
    # Принудительно обновляем кэш
    await invalidate_message_cache(message_key)
    
    return await get_message_content(message_key, fallback, True)

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
    # Принудительно обновляем кэш для актуальных данных
    if force_refresh:
        await invalidate_message_cache(MESSAGE_KEYS['PHONE_REQUEST'])
    
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

# === ВСЕ 65 СООБЩЕНИЙ ИЗ БАЗЫ ДАННЫХ ===

# COMMON сообщения (8)
async def get_ask_name(force_refresh: bool = False) -> str:
    return await get_message_content("ask_name", None, force_refresh)

async def get_email_request(force_refresh: bool = False) -> str:
    return await get_message_content("email_request", None, force_refresh)

async def get_email_saved(force_refresh: bool = False) -> str:
    return await get_message_content("email_saved", None, force_refresh)

async def get_privacy_consent_request(force_refresh: bool = False) -> str:
    return await get_message_content("privacy_consent_request", None, force_refresh)

async def get_privacy_consent_confirmed(force_refresh: bool = False) -> str:
    return await get_message_content("privacy_consent_confirmed", None, force_refresh)

async def get_privacy_reassurance(force_refresh: bool = False) -> str:
    return await get_message_content("privacy_reassurance", None, force_refresh)

# PRODUCT сообщения (40) - Книга
async def get_book_cover_format_choice(force_refresh: bool = False) -> str:
    return await get_message_content("book_cover_format_choice", None, force_refresh)

async def get_book_cover_selection(force_refresh: bool = False) -> str:
    return await get_message_content("book_cover_selection", None, force_refresh)

async def get_book_delivery_address_request(force_refresh: bool = False) -> str:
    return await get_message_content("book_delivery_address_request", None, force_refresh)

async def get_book_delivery_confirmed(force_refresh: bool = False) -> str:
    return await get_message_content("book_delivery_confirmed", None, force_refresh)

async def get_book_demo_ready(force_refresh: bool = False) -> str:
    return await get_message_content("book_demo_ready", None, force_refresh)

async def get_book_edit_confirmation(force_refresh: bool = False) -> str:
    return await get_message_content("book_edit_confirmation", None, force_refresh)

async def get_book_edit_request(force_refresh: bool = False) -> str:
    return await get_message_content("book_edit_request", None, force_refresh)

async def get_book_final_creation(force_refresh: bool = False) -> str:
    return await get_message_content("book_final_creation", None, force_refresh)

async def get_book_final_version(force_refresh: bool = False) -> str:
    return await get_message_content("book_final_version", None, force_refresh)

async def get_book_first_page_photo_request(force_refresh: bool = False) -> str:
    return await get_message_content("book_first_page_photo_request", None, force_refresh)

async def get_book_first_page_text_request(force_refresh: bool = False) -> str:
    return await get_message_content("book_first_page_text_request", None, force_refresh)

async def get_book_first_page_text_only_request(force_refresh: bool = False) -> str:
    return await get_message_content("book_first_page_text_only_request", None, force_refresh)

async def get_book_first_page_text_saved(force_refresh: bool = False) -> str:
    return await get_message_content("book_first_page_text_saved", None, force_refresh)

async def get_book_ready_message(force_refresh: bool = False) -> str:
    return await get_message_content("book_ready_message", None, force_refresh)

async def get_book_full_body_photo_request(force_refresh: bool = False) -> str:
    return await get_message_content("book_full_body_photo_request", None, force_refresh)

async def get_book_gender_selection(force_refresh: bool = False) -> str:
    return await get_message_content("book_gender_selection", None, force_refresh)

async def get_book_gift_reason(force_refresh: bool = False) -> str:
    return await get_message_content("book_gift_reason", None, force_refresh)

async def get_book_hero_description_request(force_refresh: bool = False) -> str:
    return await get_message_content("book_hero_description_request", None, force_refresh)

async def get_book_hero_full_body_photo_request(force_refresh: bool = False) -> str:
    return await get_message_content("book_hero_full_body_photo_request", None, force_refresh)

async def get_book_hero_intro(force_refresh: bool = False) -> str:
    return await get_message_content("book_hero_intro", None, force_refresh)

async def get_book_hero_name_request(force_refresh: bool = False) -> str:
    return await get_message_content("book_hero_name_request", None, force_refresh)

async def get_book_hero_photo_request(force_refresh: bool = False) -> str:
    return await get_message_content("book_hero_photo_request", None, force_refresh)

async def get_book_hero_second_photo_request(force_refresh: bool = False) -> str:
    return await get_message_content("book_hero_second_photo_request", None, force_refresh)

async def get_book_second_photo_request(force_refresh: bool = False) -> str:
    return await get_message_content("book_second_photo_request", None, force_refresh)

async def get_book_in_production(order_id: int = None, force_refresh: bool = False) -> str:
    content = await get_message_content("book_in_production", None, force_refresh)
    # Подставляем номер заказа, если он передан
    if order_id is not None and content:
        content = content.replace("{order_id}", str(order_id))
    return content

async def get_book_invalid_phone(force_refresh: bool = False) -> str:
    return await get_message_content("book_invalid_phone", None, force_refresh)

async def get_book_last_page_photo_request(force_refresh: bool = False) -> str:
    return await get_message_content("book_last_page_photo_request", None, force_refresh)

async def get_book_last_page_text_request(force_refresh: bool = False) -> str:
    return await get_message_content("book_last_page_text_request", None, force_refresh)

async def get_book_last_page_text_request_alt(force_refresh: bool = False) -> str:
    return await get_message_content("book_last_page_text_request_alt", None, force_refresh)

async def get_book_page_selection_intro(force_refresh: bool = False) -> str:
    return await get_message_content("book_page_selection_intro", None, force_refresh)

async def get_book_pages_completed(force_refresh: bool = False) -> str:
    return await get_message_content("book_pages_completed", None, force_refresh)

async def get_book_pages_selected(force_refresh: bool = False) -> str:
    return await get_message_content("book_pages_selected", None, force_refresh)

async def get_book_payment_success_delivery(force_refresh: bool = False) -> str:
    return await get_message_content("book_payment_success_delivery", None, force_refresh)

async def get_book_photo_request(force_refresh: bool = False) -> str:
    return await get_message_content("book_photo_request", None, force_refresh)

async def get_book_price_request(force_refresh: bool = False) -> str:
    return await get_message_content("book_price_request", None, force_refresh)

async def get_book_pricing_info(force_refresh: bool = False) -> str:
    return await get_message_content("book_pricing_info", None, force_refresh)

async def get_book_recipient_name_request(force_refresh: bool = False) -> str:
    return await get_message_content("book_recipient_name_request", None, force_refresh)

async def get_book_recipient_phone_request(force_refresh: bool = False) -> str:
    return await get_message_content("book_recipient_phone_request", None, force_refresh)

async def get_book_relation_choice(force_refresh: bool = False) -> str:
    return await get_message_content("book_relation_choice", None, force_refresh)

async def get_book_second_photo_request(force_refresh: bool = False) -> str:
    return await get_message_content("book_second_photo_request", None, force_refresh)

async def get_book_song_upsell(force_refresh: bool = False) -> str:
    return await get_message_content("book_song_upsell", None, force_refresh)

async def get_book_style_options(force_refresh: bool = False) -> str:
    return await get_message_content("book_style_options", None, force_refresh)

async def get_book_joint_photo_request(force_refresh: bool = False) -> str:
    return await get_message_content("book_joint_photo_request", None, force_refresh)

async def get_book_style_selection(force_refresh: bool = False) -> str:
    return await get_message_content("book_style_selection", None, force_refresh)

async def get_book_wrong_file_type(force_refresh: bool = False) -> str:
    return await get_message_content("book_wrong_file_type", None, force_refresh)

async def get_book_last_page_text_saved(force_refresh: bool = False) -> str:
    return await get_message_content("book_last_page_text_saved", None, force_refresh)

async def get_book_pages_selection_completed(force_refresh: bool = False) -> str:
    return await get_message_content("book_pages_selection_completed", None, force_refresh)

# SONG сообщения (18) - Песня
async def get_song_book_upsell(force_refresh: bool = False) -> str:
    return await get_message_content("song_book_upsell", None, force_refresh)

async def get_song_completed(force_refresh: bool = False) -> str:
    return await get_message_content("song_completed", None, force_refresh)

async def get_song_demo_creation(force_refresh: bool = False) -> str:
    return await get_message_content("song_demo_creation", None, force_refresh)

async def get_song_demo_ready(force_refresh: bool = False) -> str:
    return await get_message_content("song_demo_ready", None, force_refresh)

async def get_song_edit_confirmation(force_refresh: bool = False) -> str:
    return await get_message_content("song_edit_confirmation", None, force_refresh)

async def get_song_edit_request(force_refresh: bool = False) -> str:
    return await get_message_content("song_edit_request", None, force_refresh)

async def get_song_final_version(force_refresh: bool = False) -> str:
    return await get_message_content("song_final_version", None, force_refresh)

async def get_song_gender_selection(force_refresh: bool = False) -> str:
    return await get_message_content("song_gender_selection", None, force_refresh)

async def get_song_gift_reason(force_refresh: bool = False) -> str:
    return await get_message_content("song_gift_reason", None, force_refresh)

async def get_song_in_production(order_id: int = None, force_refresh: bool = False) -> str:
    content = await get_message_content("song_in_production", None, force_refresh)
    # Подставляем номер заказа, если он передан
    if order_id is not None and content:
        content = content.replace("{order_id}", str(order_id))
    return content

async def get_song_memories_count(force_refresh: bool = False) -> str:
    return await get_message_content("song_memories_count", None, force_refresh)

async def get_song_memory_added(force_refresh: bool = False) -> str:
    return await get_message_content("song_memory_added", None, force_refresh)

async def get_song_price_request(force_refresh: bool = False) -> str:
    return await get_message_content("song_price_request", None, force_refresh)

async def get_song_pricing_info(force_refresh: bool = False) -> str:
    return await get_message_content("song_pricing_info", None, force_refresh)

async def get_song_recipient_name(force_refresh: bool = False) -> str:
    return await get_message_content("song_recipient_name", None, force_refresh)

async def get_song_relation_choice(force_refresh: bool = False) -> str:
    return await get_message_content("song_relation_choice", None, force_refresh)

async def get_song_style_selection(force_refresh: bool = False) -> str:
    return await get_message_content("song_style_selection", None, force_refresh)

async def get_song_thank_you(force_refresh: bool = False) -> str:
    return await get_message_content("song_thank_you", None, force_refresh)

async def get_song_final_goodbye(force_refresh: bool = False) -> str:
    return await get_message_content("song_final_goodbye", None, force_refresh)