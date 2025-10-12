#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для очистки таблицы заказов и сброса счетчика ID
ВНИМАНИЕ: Это удалит ВСЕ заказы из базы данных!
"""

import asyncio
import aiosqlite
import os
import sys

# Настройка кодировки для корректной работы с русскими символами
import locale
import codecs

# Устанавливаем UTF-8 кодировку
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

DB_PATH = 'bookai.db'

async def clear_orders_table():
    """Очищает таблицу заказов и сбрасывает счетчик ID"""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ База данных {DB_PATH} не найдена!")
        return
    
    print("⚠️  ВНИМАНИЕ: Вы собираетесь удалить ВСЕ заказы из базы данных!")
    print("⚠️  Это действие НЕОБРАТИМО!")
    
    # Запрашиваем подтверждение
    confirm = input("\nAre you sure? Type 'YES' to confirm: ")
    
    if confirm != 'YES':
        print("❌ Операция отменена")
        return
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Настраиваем соединение
            await db.execute("PRAGMA foreign_keys = ON")
            await db.execute("PRAGMA journal_mode = WAL")
            await db.execute("PRAGMA synchronous = NORMAL")
            await db.execute("PRAGMA cache_size = 1000")
            await db.execute("PRAGMA temp_store = MEMORY")
            
            # Получаем количество заказов перед удалением
            async with db.execute("SELECT COUNT(*) FROM orders") as cursor:
                count_before = (await cursor.fetchone())[0]
            
            print(f"📊 Найдено заказов в базе: {count_before}")
            
            if count_before == 0:
                print("ℹ️  В таблице заказов нет данных для удаления")
                return
            
            # Отключаем проверку внешних ключей временно
            print("🔧 Отключаем проверку внешних ключей...")
            await db.execute("PRAGMA foreign_keys = OFF")
            
            # Очищаем связанные таблицы, которые ссылаются на заказы
            print("🧹 Очищаем связанные таблицы...")
            
            # Таблицы с прямыми ссылками на orders
            related_tables = [
                'sent_messages_log',
                'delayed_messages', 
                'timer_messages_sent',
                'early_user_messages'
            ]
            
            # Таблицы с метриками, которые нужно очистить
            metrics_tables = [
                'event_metrics'  # Основная таблица метрик (клики, выручка и т.д.)
            ]
            
            for table in related_tables:
                try:
                    async with db.execute(f"SELECT COUNT(*) FROM {table}") as cursor:
                        count = (await cursor.fetchone())[0]
                    if count > 0:
                        print(f"   Очищаем таблицу {table} ({count} записей)...")
                        await db.execute(f"DELETE FROM {table}")
                except Exception as e:
                    print(f"   ⚠️  Таблица {table} не найдена или ошибка: {e}")
            
            # Очищаем таблицы с метриками
            print("📊 Очищаем таблицы метрик...")
            for table in metrics_tables:
                try:
                    async with db.execute(f"SELECT COUNT(*) FROM {table}") as cursor:
                        count = (await cursor.fetchone())[0]
                    if count > 0:
                        print(f"   Очищаем таблицу {table} ({count} записей)...")
                        await db.execute(f"DELETE FROM {table}")
                        # Сбрасываем счетчик для таблиц метрик
                        await db.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
                except Exception as e:
                    print(f"   ⚠️  Таблица {table} не найдена или ошибка: {e}")
            
            # Удаляем все заказы
            print("🗑️  Удаляем все заказы...")
            await db.execute("DELETE FROM orders")
            
            # Сбрасываем счетчик AUTOINCREMENT
            print("🔄 Сбрасываем счетчик ID...")
            await db.execute("DELETE FROM sqlite_sequence WHERE name='orders'")
            
            # Включаем обратно проверку внешних ключей
            print("🔧 Включаем обратно проверку внешних ключей...")
            await db.execute("PRAGMA foreign_keys = ON")
            
            # Подтверждаем изменения
            await db.commit()
            
            # Проверяем результат
            async with db.execute("SELECT COUNT(*) FROM orders") as cursor:
                count_after = (await cursor.fetchone())[0]
            
            print(f"✅ Успешно удалено {count_before} заказов")
            print(f"✅ Счетчик ID сброшен. Следующий заказ будет иметь ID = 1")
            print(f"📊 Заказов в базе после очистки: {count_after}")
            
    except Exception as e:
        print(f"❌ Ошибка при очистке базы данных: {e}")
        return

async def show_orders_info():
    """Показывает информацию о заказах в базе"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Получаем общую информацию
            async with db.execute("SELECT COUNT(*) FROM orders") as cursor:
                total_orders = (await cursor.fetchone())[0]
            
            if total_orders == 0:
                print("📊 В базе данных нет заказов")
                return
            
            # Получаем диапазон ID
            async with db.execute("SELECT MIN(id), MAX(id) FROM orders") as cursor:
                min_id, max_id = await cursor.fetchone()
            
            print(f"📊 Информация о заказах:")
            print(f"   Всего заказов: {total_orders}")
            print(f"   Диапазон ID: {min_id} - {max_id}")
            
            # Показываем последние 5 заказов
            async with db.execute("""
                SELECT id, status, created_at, user_id 
                FROM orders 
                ORDER BY id DESC 
                LIMIT 5
            """) as cursor:
                rows = await cursor.fetchall()
                print(f"\n📋 Последние 5 заказов:")
                for row in rows:
                    print(f"   #{row[0]} | {row[1]} | {row[2]} | User: {row[3]}")
                    
    except Exception as e:
        print(f"❌ Ошибка при получении информации: {e}")

async def show_preserved_data():
    """Показывает данные, которые останутся нетронутыми"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            print("\n🛡️  ДАННЫЕ, КОТОРЫЕ ОСТАНУТСЯ НЕТРОНУТЫМИ:")
            print("=" * 60)
            
            # Менеджеры
            async with db.execute("SELECT COUNT(*) FROM managers") as cursor:
                managers_count = (await cursor.fetchone())[0]
            print(f"👥 Менеджеры: {managers_count} записей")
            
            # Профили пользователей
            async with db.execute("SELECT COUNT(*) FROM user_profiles") as cursor:
                profiles_count = (await cursor.fetchone())[0]
            print(f"👤 Профили пользователей: {profiles_count} записей")
            
            # Шаблоны сообщений
            async with db.execute("SELECT COUNT(*) FROM message_templates") as cursor:
                templates_count = (await cursor.fetchone())[0]
            print(f"📝 Шаблоны сообщений: {templates_count} записей")
            
            # Отложенные сообщения
            async with db.execute("SELECT COUNT(*) FROM delayed_messages") as cursor:
                delayed_count = (await cursor.fetchone())[0]
            print(f"⏰ Отложенные сообщения: {delayed_count} записей")
            
            # Стили книг
            async with db.execute("SELECT COUNT(*) FROM book_styles") as cursor:
                book_styles_count = (await cursor.fetchone())[0]
            print(f"📚 Стили книг: {book_styles_count} записей")
            
            # Стили голоса
            async with db.execute("SELECT COUNT(*) FROM voice_styles") as cursor:
                voice_styles_count = (await cursor.fetchone())[0]
            print(f"🎵 Стили голоса: {voice_styles_count} записей")
            
            # Шаблоны обложек
            async with db.execute("SELECT COUNT(*) FROM cover_templates") as cursor:
                covers_count = (await cursor.fetchone())[0]
            print(f"🎨 Шаблоны обложек: {covers_count} записей")
            
            # Шаги контента
            async with db.execute("SELECT COUNT(*) FROM content_steps") as cursor:
                content_steps_count = (await cursor.fetchone())[0]
            print(f"📄 Шаги контента: {content_steps_count} записей")
            
            # Сообщения бота
            async with db.execute("SELECT COUNT(*) FROM bot_messages") as cursor:
                bot_messages_count = (await cursor.fetchone())[0]
            print(f"🤖 Сообщения бота: {bot_messages_count} записей")
            
            # Шаблоны сводки заказа
            async with db.execute("SELECT COUNT(*) FROM order_summary_templates") as cursor:
                summary_templates_count = (await cursor.fetchone())[0]
            print(f"📋 Шаблоны сводки заказа: {summary_templates_count} записей")
            
            # Показываем таблицы, которые будут очищены
            print("\n🗑️  ТАБЛИЦЫ, КОТОРЫЕ БУДУТ ОЧИЩЕНЫ:")
            print("-" * 40)
            
            # Связанные таблицы
            related_tables = [
                'sent_messages_log',
                'delayed_messages', 
                'timer_messages_sent',
                'early_user_messages'
            ]
            
            for table in related_tables:
                try:
                    async with db.execute(f"SELECT COUNT(*) FROM {table}") as cursor:
                        count = (await cursor.fetchone())[0]
                    print(f"📋 {table}: {count} записей")
                except:
                    print(f"📋 {table}: таблица не найдена")
            
            # Таблицы метрик
            metrics_tables = ['event_metrics', 'orders']
            for table in metrics_tables:
                try:
                    async with db.execute(f"SELECT COUNT(*) FROM {table}") as cursor:
                        count = (await cursor.fetchone())[0]
                    print(f"📊 {table}: {count} записей")
                except:
                    print(f"📊 {table}: таблица не найдена")
            
            print("\n✅ ВСЕ ОСТАЛЬНЫЕ ДАННЫЕ ОСТАНУТСЯ НЕТРОНУТЫМИ!")
            print("=" * 60)
                    
    except Exception as e:
        print(f"❌ Ошибка при получении информации о сохраненных данных: {e}")

async def main():
    print("🔧 Утилита для очистки таблицы заказов")
    print("=" * 50)
    
    # Показываем текущую информацию
    await show_orders_info()
    
    # Показываем данные, которые останутся нетронутыми
    await show_preserved_data()
    
    print("\n" + "=" * 50)
    print("Выберите действие:")
    print("1. Очистить таблицу заказов (удалить ВСЕ заказы)")
    print("2. Показать информацию о заказах")
    print("3. Показать сохраненные данные")
    print("4. Выход")
    
    choice = input("\nEnter action number (1-4): ").strip()
    
    if choice == "1":
        await clear_orders_table()
    elif choice == "2":
        await show_orders_info()
    elif choice == "3":
        await show_preserved_data()
    elif choice == "4":
        print("👋 До свидания!")
    else:
        print("❌ Неверный выбор")

if __name__ == "__main__":
    asyncio.run(main())
