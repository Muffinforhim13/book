#!/usr/bin/env python3
"""
Скрипт для миграции данных - заполнения поля total_amount в таблице orders
для уже оплаченных заказов на основе данных из таблицы payments
"""

import asyncio
import aiosqlite
import json
from typing import Optional

DB_PATH = 'bookai.db'

async def migrate_order_amounts():
    """Мигрирует суммы заказов из таблицы payments в таблицу orders"""
    
    print("🔄 Начинаем миграцию сумм заказов...")
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем все оплаченные заказы без total_amount
        async with db.execute('''
            SELECT o.id, o.user_id, o.status, o.order_data, o.created_at
            FROM orders o
            WHERE o.status IN ('paid', 'upsell_paid', 'waiting_draft', 'draft_sent', 'editing', 'ready', 'delivered', 'completed')
            AND (o.total_amount IS NULL OR o.total_amount = 0)
            ORDER BY o.id
        ''') as cursor:
            orders = await cursor.fetchall()
        
        print(f"📊 Найдено {len(orders)} заказов для миграции")
        
        migrated_count = 0
        skipped_count = 0
        
        for order in orders:
            order_id, user_id, status, order_data_json, created_at = order
            
            try:
                # Парсим данные заказа
                order_data = json.loads(order_data_json) if order_data_json else {}
                
                # Получаем сумму из таблицы payments
                async with db.execute('''
                    SELECT amount, status as payment_status
                    FROM payments 
                    WHERE order_id = ? 
                    AND status = 'succeeded'
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (order_id,)) as cursor:
                    payment = await cursor.fetchone()
                
                if payment:
                    amount, payment_status = payment
                    print(f"✅ Заказ {order_id}: найдена сумма {amount} из платежа")
                    
                    # Обновляем total_amount в заказе
                    await db.execute('''
                        UPDATE orders 
                        SET total_amount = ?, updated_at = datetime('now')
                        WHERE id = ?
                    ''', (amount, order_id))
                    
                    migrated_count += 1
                else:
                    # Если нет платежа, пытаемся получить сумму из order_data
                    amount_from_data = order_data.get('amount') or order_data.get('price')
                    if amount_from_data:
                        try:
                            amount = float(amount_from_data)
                            print(f"✅ Заказ {order_id}: найдена сумма {amount} из данных заказа")
                            
                            await db.execute('''
                                UPDATE orders 
                                SET total_amount = ?, updated_at = datetime('now')
                                WHERE id = ?
                            ''', (amount, order_id))
                            
                            migrated_count += 1
                        except (ValueError, TypeError):
                            print(f"⚠️ Заказ {order_id}: не удалось извлечь сумму из данных заказа")
                            skipped_count += 1
                    else:
                        print(f"⚠️ Заказ {order_id}: не найдена сумма ни в платежах, ни в данных заказа")
                        skipped_count += 1
                        
            except Exception as e:
                print(f"❌ Ошибка обработки заказа {order_id}: {e}")
                skipped_count += 1
        
        await db.commit()
        
        print(f"\n📈 Результаты миграции:")
        print(f"✅ Успешно мигрировано: {migrated_count}")
        print(f"⚠️ Пропущено: {skipped_count}")
        print(f"📊 Всего обработано: {len(orders)}")
        
        # Проверяем результат
        async with db.execute('''
            SELECT COUNT(*) as total_orders,
                   COUNT(CASE WHEN total_amount IS NOT NULL AND total_amount > 0 THEN 1 END) as orders_with_amount,
                   SUM(CASE WHEN total_amount IS NOT NULL AND total_amount > 0 THEN total_amount ELSE 0 END) as total_revenue
            FROM orders 
            WHERE status IN ('paid', 'upsell_paid', 'waiting_draft', 'draft_sent', 'editing', 'ready', 'delivered', 'completed')
        ''') as cursor:
            stats = await cursor.fetchone()
            
        print(f"\n📊 Статистика после миграции:")
        print(f"Всего оплаченных заказов: {stats[0]}")
        print(f"Заказов с суммой: {stats[1]}")
        print(f"Общая выручка: {stats[2]:.2f} ₽")

async def main():
    """Главная функция"""
    try:
        await migrate_order_amounts()
        print("\n🎉 Миграция завершена успешно!")
    except Exception as e:
        print(f"\n❌ Ошибка миграции: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
