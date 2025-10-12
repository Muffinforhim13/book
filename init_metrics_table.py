#!/usr/bin/env python3
"""
Скрипт для инициализации таблицы event_metrics
"""
import asyncio
import aiosqlite

async def init_metrics_table():
    """Инициализирует таблицу event_metrics"""
    try:
        async with aiosqlite.connect('bookai.db') as db:
            # Создаем таблицу event_metrics
            await db.execute('''
                CREATE TABLE IF NOT EXISTS event_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    event_data TEXT, -- JSON данные события
                    step_name TEXT, -- Название шага (для отвалов)
                    product_type TEXT, -- Тип продукта (книга/песня)
                    order_id INTEGER, -- ID заказа (если применимо)
                    amount REAL, -- Сумма (для покупок)
                    source TEXT, -- Источник (канал/кампания)
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Создаем индексы для быстрого поиска
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_event_metrics_user_id ON event_metrics(user_id)
            ''')
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_event_metrics_event_type ON event_metrics(event_type)
            ''')
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_event_metrics_timestamp ON event_metrics(timestamp)
            ''')
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_event_metrics_order_id ON event_metrics(order_id)
            ''')
            
            await db.commit()
            print("✅ Таблица event_metrics успешно создана")
            
            # Проверяем, что таблица создана
            cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='event_metrics'")
            result = await cursor.fetchone()
            if result:
                print("✅ Таблица event_metrics существует")
            else:
                print("❌ Таблица event_metrics не найдена")
                
    except Exception as e:
        print(f"❌ Ошибка создания таблицы event_metrics: {e}")

if __name__ == "__main__":
    asyncio.run(init_metrics_table())
