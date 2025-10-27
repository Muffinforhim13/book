import sqlite3
from datetime import datetime, timedelta

def check_demo_events():
    """Проверяет события демо в базе данных"""
    db = sqlite3.connect('database.d')
    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    
    # Сначала проверим, какие таблицы есть в базе
    print("\n=== Список таблиц в базе данных ===")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    for table in tables:
        print(f"- {table['name']}")
    
    # Проверяем, существует ли таблица event_metrics
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='event_metrics'")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        print("\n❌ Таблица event_metrics не существует!")
        print("Нужно создать таблицу. Проверьте инициализацию базы данных.")
        db.close()
        return
    
    # Проверяем последние события нажатий "Узнать цену"
    print("\n=== Последние события нажатий 'Узнать цену' ===")
    cursor.execute('''
        SELECT user_id, event_type, timestamp, order_id, product_type
        FROM event_metrics 
        WHERE event_type IN ('demo_learn_price_clicked', 'song_demo_learn_price_clicked')
        ORDER BY timestamp DESC 
        LIMIT 10
    ''')
    rows = cursor.fetchall()
    
    if rows:
        for row in rows:
            print(f"User: {row['user_id']}, Type: {row['event_type']}, Time: {row['timestamp']}, Order: {row['order_id']}, Product: {row['product_type']}")
    else:
        print("❌ Нет событий нажатий 'Узнать цену'")
    
    # Проверяем все типы событий за последние 24 часа
    print("\n=== Все типы событий за последние 24 часа ===")
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
        SELECT event_type, COUNT(*) as count
        FROM event_metrics 
        WHERE timestamp > ?
        GROUP BY event_type
        ORDER BY count DESC
    ''', (yesterday,))
    rows = cursor.fetchall()
    
    for row in rows:
        print(f"{row['event_type']}: {row['count']}")
    
    # Проверяем метрики за сегодня
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"\n=== Метрики за сегодня ({today}) ===")
    
    cursor.execute('''
        SELECT COUNT(DISTINCT user_id) as song_demo_users
        FROM event_metrics 
        WHERE event_type = 'song_demo_learn_price_clicked'
        AND DATE(timestamp) = ?
    ''', (today,))
    result = cursor.fetchone()
    print(f"Песня - нажали 'Узнать цену': {result['song_demo_users']}")
    
    cursor.execute('''
        SELECT COUNT(DISTINCT user_id) as book_demo_users
        FROM event_metrics 
        WHERE event_type = 'demo_learn_price_clicked'
        AND DATE(timestamp) = ?
    ''', (today,))
    result = cursor.fetchone()
    print(f"Книга - нажали 'Узнать цену': {result['book_demo_users']}")
    
    db.close()

if __name__ == "__main__":
    check_demo_events()

