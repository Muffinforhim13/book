#!/usr/bin/env python3
"""
Скрипт для проверки метрик в базе данных
"""

import asyncio
import aiosqlite
import json
from datetime import datetime, timedelta

DB_PATH = "bookai_bot.db"

async def check_event_metrics():
    """Проверяет данные в таблице event_metrics"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # Проверяем общее количество событий
            async with db.execute('SELECT COUNT(*) as total FROM event_metrics') as cursor:
                total_events = await cursor.fetchone()
                print(f"📊 Общее количество событий: {total_events['total']}")
            
            # Проверяем события по типам
            async with db.execute('''
                SELECT event_type, COUNT(*) as count 
                FROM event_metrics 
                GROUP BY event_type 
                ORDER BY count DESC
            ''') as cursor:
                events_by_type = await cursor.fetchall()
                print("\n📈 События по типам:")
                for event in events_by_type:
                    print(f"  {event['event_type']}: {event['count']}")
            
            # Проверяем выборы продуктов
            async with db.execute('''
                SELECT product_type, COUNT(*) as count 
                FROM event_metrics 
                WHERE event_type = 'product_selected'
                GROUP BY product_type
            ''') as cursor:
                product_selections = await cursor.fetchall()
                print("\n🛍️ Выборы продуктов:")
                for selection in product_selections:
                    print(f"  {selection['product_type']}: {selection['count']}")
            
            # Проверяем покупки
            async with db.execute('''
                SELECT product_type, COUNT(*) as count 
                FROM event_metrics 
                WHERE event_type = 'purchase_completed'
                GROUP BY product_type
            ''') as cursor:
                purchases = await cursor.fetchall()
                print("\n💳 Покупки:")
                for purchase in purchases:
                    print(f"  {purchase['product_type']}: {purchase['count']}")
            
            # Проверяем последние события
            async with db.execute('''
                SELECT user_id, event_type, product_type, timestamp 
                FROM event_metrics 
                ORDER BY timestamp DESC 
                LIMIT 10
            ''') as cursor:
                recent_events = await cursor.fetchall()
                print("\n🕐 Последние 10 событий:")
                for event in recent_events:
                    print(f"  {event['timestamp']} - User {event['user_id']}: {event['event_type']} ({event['product_type']})")
            
            # Проверяем события за последние 7 дней
            week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            async with db.execute('''
                SELECT event_type, product_type, COUNT(*) as count 
                FROM event_metrics 
                WHERE timestamp >= ?
                GROUP BY event_type, product_type
                ORDER BY count DESC
            ''', (week_ago,)) as cursor:
                week_events = await cursor.fetchall()
                print(f"\n📅 События за последние 7 дней (с {week_ago}):")
                for event in week_events:
                    print(f"  {event['event_type']} ({event['product_type']}): {event['count']}")
                    
    except Exception as e:
        print(f"❌ Ошибка при проверке метрик: {e}")

if __name__ == "__main__":
    asyncio.run(check_event_metrics())


