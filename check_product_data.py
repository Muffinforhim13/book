#!/usr/bin/env python3
"""
Скрипт для проверки данных о типах продуктов в базе данных
"""

import asyncio
import aiosqlite
import json

DB_PATH = 'bookai.db'

async def check_product_data():
    """Проверяет данные о типах продуктов в базе данных"""
    print("🔍 Проверка данных о типах продуктов...")
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем таблицу user_profiles
        print("\n📊 Таблица user_profiles:")
        async with db.execute('''
            SELECT user_id, product, username, first_name, last_name
            FROM user_profiles
            ORDER BY user_id DESC
            LIMIT 10
        ''') as cursor:
            profiles = await cursor.fetchall()
            print(f"Найдено {len(profiles)} профилей:")
            for profile in profiles:
                user_id, product, username, first_name, last_name = profile
                print(f"  User ID: {user_id}, Product: '{product}', Username: '{username}', Name: '{first_name} {last_name}'")
        
        # Проверяем таблицу orders
        print("\n📊 Таблица orders:")
        async with db.execute('''
            SELECT id, user_id, status, order_data
            FROM orders
            ORDER BY id DESC
            LIMIT 10
        ''') as cursor:
            orders = await cursor.fetchall()
            print(f"Найдено {len(orders)} заказов:")
            for order in orders:
                order_id, user_id, status, order_data = order
                print(f"  Order ID: {order_id}, User ID: {user_id}, Status: '{status}'")
                
                # Парсим order_data
                try:
                    if order_data:
                        data = json.loads(order_data)
                        product = data.get('product', 'НЕТ')
                        print(f"    Order Data Product: '{product}'")
                    else:
                        print(f"    Order Data: пустое")
                except Exception as e:
                    print(f"    Order Data: ошибка парсинга - {e}")
        
        # Проверяем JOIN между orders и user_profiles
        print("\n📊 JOIN orders + user_profiles:")
        async with db.execute('''
            SELECT o.id, o.user_id, o.status, u.product as user_product, u.username
            FROM orders o
            LEFT JOIN user_profiles u ON o.user_id = u.user_id
            ORDER BY o.id DESC
            LIMIT 10
        ''') as cursor:
            joined = await cursor.fetchall()
            print(f"Найдено {len(joined)} записей:")
            for record in joined:
                order_id, user_id, status, user_product, username = record
                print(f"  Order ID: {order_id}, User ID: {user_id}, Status: '{status}', User Product: '{user_product}', Username: '{username}'")
        
        # Проверяем, есть ли данные в event_metrics
        print("\n📊 Таблица event_metrics (product_selected):")
        async with db.execute('''
            SELECT user_id, event_type, product_type, timestamp
            FROM event_metrics
            WHERE event_type = 'product_selected'
            ORDER BY timestamp DESC
            LIMIT 10
        ''') as cursor:
            events = await cursor.fetchall()
            print(f"Найдено {len(events)} событий product_selected:")
            for event in events:
                user_id, event_type, product_type, timestamp = event
                print(f"  User ID: {user_id}, Event: '{event_type}', Product Type: '{product_type}', Time: '{timestamp}'")

async def main():
    """Основная функция"""
    print("🚀 Проверка данных о типах продуктов")
    print("=" * 60)
    
    await check_product_data()
    
    print("\n" + "=" * 60)
    print("✅ Проверка завершена")
    print("\n💡 Возможные причины проблемы:")
    print("  1. Поле 'product' в user_profiles не заполняется")
    print("  2. Поле 'product' в order_data не заполняется")
    print("  3. JOIN между таблицами работает неправильно")
    print("  4. SQL запрос выбирает неправильные поля")

if __name__ == "__main__":
    asyncio.run(main())
