#!/usr/bin/env python3
"""
Скрипт для инициализации таблицы шаблона сводки заказа
"""

import asyncio
import aiosqlite

async def init_order_summary_template():
    """Инициализирует таблицу order_summary_templates и создает дефолтный шаблон"""
    async with aiosqlite.connect('bookai.db') as db:
        # Создаем таблицу
        await db.execute('''
            CREATE TABLE IF NOT EXISTS order_summary_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gender_label TEXT DEFAULT 'Пол отправителя',
                recipient_name_label TEXT DEFAULT 'Имя получателя',
                gift_reason_label TEXT DEFAULT 'Повод',
                relation_label TEXT DEFAULT 'Отношение',
                style_label TEXT DEFAULT 'Стиль',
                format_label TEXT DEFAULT 'Формат',
                sender_name_label TEXT DEFAULT 'От кого',
                song_gender_label TEXT DEFAULT 'Пол отправителя',
                song_recipient_name_label TEXT DEFAULT 'Имя получателя',
                song_gift_reason_label TEXT DEFAULT 'Повод',
                song_relation_label TEXT DEFAULT 'Отношение',
                song_style_label TEXT DEFAULT 'Стиль',
                song_voice_label TEXT DEFAULT 'Голос',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Проверяем, есть ли уже шаблон
        cursor = await db.execute('SELECT COUNT(*) FROM order_summary_templates')
        result = await cursor.fetchone()
        count = result[0] if result else 0
        
        if count == 0:
            # Создаем дефолтный шаблон
            await db.execute('''
                INSERT INTO order_summary_templates (
                    gender_label, recipient_name_label, gift_reason_label,
                    relation_label, style_label, format_label,
                    sender_name_label, song_gender_label, song_recipient_name_label,
                    song_gift_reason_label, song_relation_label, song_style_label,
                    song_voice_label
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                'Пол отправителя',
                'Имя получателя',
                'Повод',
                'Отношение',
                'Стиль',
                'Формат',
                'От кого',
                'Пол отправителя',
                'Имя получателя',
                'Повод',
                'Отношение',
                'Стиль',
                'Голос'
            ))
            print('✅ Создан дефолтный шаблон сводки заказа')
        else:
            print('ℹ️ Шаблон сводки заказа уже существует')
        
        await db.commit()
        print('✅ Таблица order_summary_templates инициализирована')

if __name__ == "__main__":
    asyncio.run(init_order_summary_template())
