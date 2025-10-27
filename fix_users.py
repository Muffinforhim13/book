#!/usr/bin/env python3
import sqlite3
import bcrypt

def fix_users():
    """Создает пользователей с правильным bcrypt хешем"""
    # Подключаемся к базе данных
    conn = sqlite3.connect('bookai.db')
    cursor = conn.cursor()
    
    # Удаляем всех пользователей
    cursor.execute('DELETE FROM managers')
    
    # Создаем пользователей с правильным bcrypt хешем
    users = [
        ("admin@example.com", "111111", "Admin User"),
        ("test@mail.ru", "111111", "Test User")
    ]
    
    for email, password, full_name in users:
        # Создаем правильный bcrypt хеш
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute('''
            INSERT INTO managers (email, hashed_password, full_name, is_super_admin, is_active) 
            VALUES (?, ?, ?, ?, ?)
        ''', (email, hashed, full_name, 1, 1))
        print(f'✅ Пользователь {email} создан с bcrypt хешем')
        print(f'   Хеш: {hashed[:50]}...')
    
    conn.commit()
    conn.close()
    print('✅ Все пользователи созданы с правильным bcrypt хешем')

if __name__ == "__main__":
    fix_users()
