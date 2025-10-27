#!/usr/bin/env python3
import sqlite3
import hashlib

def add_user(email, password, full_name="Test User"):
    """Добавляет пользователя в базу данных"""
    # Подключаемся к базе данных
    conn = sqlite3.connect('bookai.db')
    cursor = conn.cursor()
    
    # Удаляем существующего пользователя с таким email
    cursor.execute('DELETE FROM managers WHERE email = ?', (email,))
    
    # Создаем простой хеш пароля
    hashed = hashlib.sha256(password.encode()).hexdigest()
    
    # Добавляем пользователя
    cursor.execute('''
        INSERT INTO managers (email, hashed_password, full_name, is_super_admin, is_active) 
        VALUES (?, ?, ?, ?, ?)
    ''', (email, hashed, full_name, 1, 1))
    
    conn.commit()
    print(f'✅ Пользователь {email} создан успешно')
    print(f'📧 Email: {email}')
    print(f'🔑 Пароль: {password}')
    print(f'🔐 Хеш: {hashed[:50]}...')
    conn.close()

if __name__ == "__main__":
    # Добавляем пользователя
    add_user("test@mail.ru", "111111", "Test User")
    
    # Показываем всех пользователей
    conn = sqlite3.connect('bookai.db')
    cursor = conn.cursor()
    cursor.execute('SELECT email, full_name, is_super_admin FROM managers;')
    rows = cursor.fetchall()
    print('\n📋 Все пользователи в базе:')
    for row in rows:
        print(f'  - {row[0]} ({row[1]}) - Super Admin: {bool(row[2])}')
    conn.close()
