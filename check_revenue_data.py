#!/usr/bin/env python3
"""
Скрипт для проверки и исправления данных о выручке в базе данных
"""

import asyncio
import aiosqlite
import json
from datetime import datetime, timedelta

DB_PATH = 'bookai.db'

async def check_revenue_data():
    """Проверяет данные о выручке в базе данных"""
    print("🔍 Проверяем данные о выручке...")
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем все заказы с total_amount
        async with db.execute('''
            SELECT id, status, total_amount, order_data, created_at
            FROM orders 
            WHERE total_amount IS NOT NULL AND total_amount > 0
            ORDER BY created_at DESC
        ''') as cursor:
            orders = await cursor.fetchall()
        
        print(f"📊 Найдено {len(orders)} заказов с total_amount > 0")
        
        total_revenue = 0
        for order in orders:
            order_id, status, total_amount, order_data_str, created_at = order
            total_revenue += total_amount
            
            # Парсим order_data для получения типа продукта
            product_type = "Неизвестно"
            if order_data_str:
                try:
                    order_data = json.loads(order_data_str)
                    product_type = order_data.get('product', 'Неизвестно')
                except:
                    pass
            
            print(f"  - Заказ {order_id}: {status}, {total_amount}₽, {product_type}, {created_at}")
        
        print(f"💰 Общая выручка: {total_revenue}₽")
        
        # Проверяем заказы без total_amount
        async with db.execute('''
            SELECT id, status, order_data, created_at
            FROM orders 
            WHERE (total_amount IS NULL OR total_amount = 0)
            AND status IN ('paid', 'upsell_paid', 'waiting_draft', 'draft_sent', 'editing', 'ready', 'delivered', 'completed')
            ORDER BY created_at DESC
        ''') as cursor:
            orders_without_amount = await cursor.fetchall()
        
        print(f"⚠️ Найдено {len(orders_without_amount)} оплаченных заказов без total_amount:")
        for order in orders_without_amount:
            order_id, status, order_data_str, created_at = order
            print(f"  - Заказ {order_id}: {status}, {created_at}")
        
        # Проверяем платежи
        async with db.execute('''
            SELECT order_id, amount, status, created_at
            FROM payments 
            WHERE status = 'succeeded'
            ORDER BY created_at DESC
        ''') as cursor:
            payments = await cursor.fetchall()
        
        print(f"💳 Найдено {len(payments)} успешных платежей:")
        for payment in payments:
            order_id, amount, status, created_at = payment
            print(f"  - Заказ {order_id}: {amount}₽, {status}, {created_at}")

async def fix_missing_amounts():
    """Исправляет отсутствующие total_amount из платежей"""
    print("🔧 Исправляем отсутствующие total_amount...")
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Находим заказы без total_amount, но с успешными платежами
        async with db.execute('''
            SELECT o.id, o.status, p.amount, p.created_at
            FROM orders o
            JOIN payments p ON o.id = p.order_id
            WHERE (o.total_amount IS NULL OR o.total_amount = 0)
            AND o.status IN ('paid', 'upsell_paid', 'waiting_draft', 'draft_sent', 'editing', 'ready', 'delivered', 'completed')
            AND p.status = 'succeeded'
            ORDER BY o.id
        ''') as cursor:
            orders_to_fix = await cursor.fetchall()
        
        print(f"🔧 Найдено {len(orders_to_fix)} заказов для исправления")
        
        fixed_count = 0
        for order_id, status, amount, created_at in orders_to_fix:
            try:
                await db.execute('''
                    UPDATE orders 
                    SET total_amount = ?, updated_at = datetime('now')
                    WHERE id = ?
                ''', (amount, order_id))
                print(f"✅ Исправлен заказ {order_id}: {amount}₽")
                fixed_count += 1
            except Exception as e:
                print(f"❌ Ошибка исправления заказа {order_id}: {e}")
        
        await db.commit()
        print(f"✅ Исправлено {fixed_count} заказов")

async def main():
    """Основная функция"""
    print("🚀 Запуск проверки данных о выручке")
    print("=" * 50)
    
    await check_revenue_data()
    print("\n" + "=" * 50)
    
    await fix_missing_amounts()
    print("\n" + "=" * 50)
    
    print("🔍 Повторная проверка после исправлений:")
    await check_revenue_data()

if __name__ == "__main__":
    asyncio.run(main())
