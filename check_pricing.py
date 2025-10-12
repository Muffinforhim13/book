#!/usr/bin/env python3
import asyncio
import aiosqlite

async def check_pricing():
    async with aiosqlite.connect('bookai.db') as db:
        async with db.execute('''
            SELECT product, price, currency, upgrade_price_difference, is_active 
            FROM pricing_items 
            ORDER BY created_at DESC
        ''') as cursor:
            rows = await cursor.fetchall()
            print("Текущие цены в базе данных:")
            print("-" * 80)
            for row in rows:
                product, price, currency, upgrade_price_difference, is_active = row
                print(f"Продукт: {product}")
                print(f"Цена: {price} {currency}")
                print(f"Разница для апгрейда: {upgrade_price_difference}")
                print(f"Активен: {is_active}")
                print("-" * 80)

if __name__ == "__main__":
    asyncio.run(check_pricing())
