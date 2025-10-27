import sqlite3
import json
from datetime import datetime, timedelta

conn = sqlite3.connect('bookai.db')
cursor = conn.cursor()

# Получаем период из метрик (последние 30 дней или всё время)
# Для начала просто берём ВСЕ заказы без фильтра по дате
print("🔍 Ищем все оплаченные заказы за всё время...\n")

PAID_STATUSES = [
    'paid', 'waiting_story_options', 'waiting_story_choice', 'story_selected', 
    'story_options_sent', 'pages_selected', 'covers_sent', 'waiting_cover_choice', 
    'cover_selected', 'waiting_draft', 'draft_sent', 'editing', 'waiting_feedback', 
    'feedback_processed', 'prefinal_sent', 'waiting_final', 'ready', 'waiting_delivery', 
    'print_delivery_pending', 'final_sent', 'delivered', 'completed', 'collecting_facts', 
    'questions_completed', 'waiting_plot_options', 'plot_selected', 'waiting_final_version',
    'upsell_payment_created', 'upsell_payment_pending', 'upsell_paid', 'additional_payment_paid'
]

placeholders = ','.join(['?' for _ in PAID_STATUSES])

# Сначала проверим, есть ли вообще заказы
cursor.execute('SELECT COUNT(*) FROM orders')
total_orders = cursor.fetchone()[0]
print(f"📦 Всего заказов в базе: {total_orders}")

cursor.execute(f'SELECT COUNT(*) FROM orders WHERE status IN ({placeholders})', PAID_STATUSES)
paid_orders = cursor.fetchone()[0]
print(f"💰 Оплаченных заказов (по статусу): {paid_orders}\n")

cursor.execute(f'''
    SELECT 
        o.id, 
        o.status, 
        o.order_data, 
        o.total_amount,
        o.created_at,
        (SELECT COUNT(*) FROM event_metrics em 
         WHERE em.order_id = o.id AND em.event_type = "upsell_purchased") as is_upsell
    FROM orders o
    WHERE o.status IN ({placeholders})
    ORDER BY o.id
''', PAID_STATUSES)

rows = cursor.fetchall()
print(f'📋 Найдено оплаченных заказов: {len(rows)}\n')

book_print = 0
book_electronic = 0
song = 0
upsells = 0
other = 0

for row in rows:
    order_id, status, order_data_str, total_amount, created_at, is_upsell = row
    is_upsell_flag = '🔴 ДОПРОДАЖА' if is_upsell > 0 else '✅ ОСНОВНАЯ'
    
    try:
        if not order_data_str:
            print(f'#{order_id:04d} | {status:25s} | {"НЕТ order_data":30s} | {total_amount or 0:6.0f}₽ | ⚠️  ПРОПУЩЕН')
            continue
            
        order_data = json.loads(order_data_str)
        product = order_data.get('product', '')
        
        if not product:
            print(f'#{order_id:04d} | {status:25s} | {"НЕТ product":30s} | {total_amount or 0:6.0f}₽ | ⚠️  ПРОПУЩЕН')
            continue
        
        book_format = order_data.get('book_format', '')
        format_field = order_data.get('format', '')
        
        product_display = product
        
        if product == 'Книга':
            is_electronic = (
                'Электронная' in str(book_format) or 
                'Электронная' in str(format_field) or
                'электронная' in str(format_field).lower()
            )
            product_display = f'Книга ({"Электронная" if is_electronic else "Печатная"})'
            
            if is_upsell == 0:
                if is_electronic:
                    book_electronic += 1
                else:
                    book_print += 1
        elif product == 'Песня':
            if is_upsell == 0:
                song += 1
        else:
            other += 1
            product_display = f'{product} (другое)'
        
        if is_upsell > 0:
            upsells += 1
        
        amount_str = f'{total_amount:6.0f}₽' if total_amount else '     0₽'
        print(f'#{order_id:04d} | {status:25s} | {product_display:30s} | {amount_str} | {is_upsell_flag}')
    except Exception as e:
        print(f'#{order_id:04d} | {status:25s} | ERROR: {str(e)[:30]:30s} | {total_amount or 0:6.0f}₽ | ❌ ОШИБКА')

print(f'\n📊 ИТОГО:')
print(f'Книга печатная: {book_print}')
print(f'Книга электронная: {book_electronic}')
print(f'Песня: {song}')
print(f'Другие продукты: {other}')
print(f'Допродажи (исключены из подсчёта): {upsells}')
print(f'\n✅ ОСНОВНЫХ ПОКУПОК: {book_print + book_electronic + song}')
print(f'   (должно быть 30 согласно метрикам)')

conn.close()

