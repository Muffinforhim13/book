import sqlite3
import json

conn = sqlite3.connect('bookai.db')
cursor = conn.cursor()

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

cursor.execute(f'''
    SELECT 
        o.id, 
        o.status, 
        o.order_data, 
        o.total_amount,
        (SELECT COUNT(*) FROM event_metrics em 
         WHERE em.order_id = o.id AND em.event_type = "upsell_purchased") as is_upsell,
        (SELECT COUNT(*) FROM payments p 
         WHERE p.order_id = o.id AND p.status = 'succeeded') as payment_count
    FROM orders o
    WHERE o.status IN ({placeholders})
    AND (o.total_amount IS NULL OR o.total_amount = 0)
    ORDER BY o.id
''', PAID_STATUSES)

rows = cursor.fetchall()
print(f'🔍 Заказы в "оплаченном" статусе, но с total_amount = 0:\n')

for row in rows:
    order_id, status, order_data_str, total_amount, is_upsell, payment_count = row
    
    try:
        order_data = json.loads(order_data_str) if order_data_str else {}
        product = order_data.get('product', 'НЕТ')
        
        is_upsell_flag = '🔴 ДОПРОДАЖА' if is_upsell > 0 else '✅ ОСНОВНАЯ'
        payment_info = f'✅ {payment_count} платежей' if payment_count > 0 else '❌ НЕТ платежей'
        
        print(f'#{order_id:04d} | {status:25s} | {product:15s} | {payment_info:20s} | {is_upsell_flag}')
    except Exception as e:
        print(f'#{order_id:04d} | {status:25s} | ERROR: {e}')

print(f'\n📊 Всего таких заказов: {len(rows)}')
print(f'\n⚠️ Эти заказы НЕ должны считаться оплаченными!')

conn.close()

