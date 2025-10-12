import asyncio
import aiosqlite
from datetime import datetime, timedelta

async def debug_timers():
    async with aiosqlite.connect('bookai.db') as db:
        db.row_factory = aiosqlite.Row
        
        print("=== АКТИВНЫЕ ТАЙМЕРЫ ===")
        cursor = await db.execute('''
            SELECT user_id, order_id, order_step, product_type, step_started_at, is_active
            FROM user_step_timers 
            WHERE is_active = 1
            ORDER BY step_started_at DESC
        ''')
        timers = await cursor.fetchall()
        for timer in timers:
            print(f"User: {timer['user_id']}, Order: {timer['order_id']}, Step: {timer['order_step']}, Product: {timer['product_type']}, Started: {timer['step_started_at']}")
        
        print("\n=== ШАБЛОНЫ ДЛЯ DEMO_RECEIVED_SONG ===")
        cursor = await db.execute('''
            SELECT id, name, message_type, delay_minutes, is_active
            FROM message_templates 
            WHERE order_step = 'demo_received_song'
            ORDER BY delay_minutes
        ''')
        templates = await cursor.fetchall()
        for template in templates:
            print(f"ID: {template['id']}, Name: {template['name']}, Type: {template['message_type']}, Delay: {template['delay_minutes']}, Active: {template['is_active']}")
        
        print("\n=== ГОТОВЫЕ К ОТПРАВКЕ ===")
        cursor = await db.execute('''
            SELECT DISTINCT
                t.id as timer_id,
                t.user_id,
                t.order_id,
                t.order_step,
                t.product_type,
                t.step_started_at,
                mt.id as template_id,
                mt.message_type,
                mt.delay_minutes,
                mt.name as template_name
            FROM user_step_timers t
            JOIN message_templates mt ON (
                (t.order_step = 'demo_received_song' AND mt.order_step = 'demo_received_song')
            )
            WHERE t.is_active = 1 
            AND mt.is_active = 1
            AND datetime(t.step_started_at, '+' || mt.delay_minutes || ' minutes') <= datetime('now')
            ORDER BY t.step_started_at ASC, mt.delay_minutes ASC
        ''')
        ready = await cursor.fetchall()
        for item in ready:
            print(f"Timer: {item['timer_id']}, User: {item['user_id']}, Order: {item['order_id']}, Step: {item['order_step']}, Template: {item['template_name']}, Delay: {item['delay_minutes']}")

if __name__ == "__main__":
    asyncio.run(debug_timers())
