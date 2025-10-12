#!/usr/bin/env python3
"""
Скрипт для очистки метрик отвалов по этапам из таблицы event_metrics
"""

import asyncio
import aiosqlite
from db import DB_PATH

async def cleanup_abandonment_metrics():
    """Удаляет все метрики отвалов из таблицы event_metrics"""
    async with aiosqlite.connect(DB_PATH) as db:
        print("🧹 Очистка метрик отвалов по этапам...")
        
        # Проверяем, существует ли таблица event_metrics
        async with db.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='event_metrics'
        """) as cursor:
            table_exists = await cursor.fetchone()
        
        if not table_exists:
            print("❌ Таблица event_metrics не существует")
            return
        
        # Получаем статистику до очистки
        async with db.execute("""
            SELECT 
                event_type,
                COUNT(*) as count
            FROM event_metrics 
            GROUP BY event_type
            ORDER BY count DESC
        """) as cursor:
            before_stats = await cursor.fetchall()
        
        print("📊 Статистика ДО очистки:")
        for event_type, count in before_stats:
            print(f"  {event_type}: {count} событий")
        
        # Удаляем все события отвалов
        async with db.execute("""
            DELETE FROM event_metrics 
            WHERE event_type IN ('step_abandoned', 'demo_abandoned_book')
        """) as cursor:
            deleted_count = cursor.rowcount
        
        await db.commit()
        
        # Получаем статистику после очистки
        async with db.execute("""
            SELECT 
                event_type,
                COUNT(*) as count
            FROM event_metrics 
            GROUP BY event_type
            ORDER BY count DESC
        """) as cursor:
            after_stats = await cursor.fetchall()
        
        print(f"\n✅ Удалено {deleted_count} событий отвалов")
        print("\n📊 Статистика ПОСЛЕ очистки:")
        for event_type, count in after_stats:
            print(f"  {event_type}: {count} событий")
        
        # Проверяем, что отвалы действительно удалены
        async with db.execute("""
            SELECT COUNT(*) FROM event_metrics 
            WHERE event_type IN ('step_abandoned', 'demo_abandoned_book')
        """) as cursor:
            remaining_abandonments = (await cursor.fetchone())[0]
        
        if remaining_abandonments == 0:
            print("\n🎉 Все метрики отвалов успешно очищены!")
        else:
            print(f"\n⚠️ Осталось {remaining_abandonments} событий отвалов")

async def show_abandonment_metrics():
    """Показывает текущие метрики отвалов"""
    async with aiosqlite.connect(DB_PATH) as db:
        print("📊 Текущие метрики отвалов:")
        
        # Проверяем, существует ли таблица
        async with db.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='event_metrics'
        """) as cursor:
            table_exists = await cursor.fetchone()
        
        if not table_exists:
            print("❌ Таблица event_metrics не существует")
            return
        
        # Показываем отвалы по этапам
        async with db.execute("""
            SELECT 
                step_name,
                COUNT(*) as abandonment_count,
                COUNT(DISTINCT user_id) as unique_users
            FROM event_metrics 
            WHERE event_type = 'step_abandoned'
            GROUP BY step_name
            ORDER BY abandonment_count DESC
        """) as cursor:
            abandonment_data = await cursor.fetchall()
        
        if abandonment_data:
            print("\n📈 Отвалы по этапам:")
            for step_name, count, unique_users in abandonment_data:
                print(f"  {step_name}: {count} отвалов ({unique_users} уникальных пользователей)")
        else:
            print("✅ Событий отвалов не найдено")
        
        # Показываем демо отвалы для книг
        async with db.execute("""
            SELECT 
                COUNT(*) as demo_abandoned_count,
                COUNT(DISTINCT user_id) as demo_abandoned_unique_users
            FROM event_metrics 
            WHERE event_type = 'demo_abandoned_book'
        """) as cursor:
            demo_result = await cursor.fetchone()
            demo_count, demo_unique = demo_result if demo_result else (0, 0)
        
        if demo_count > 0:
            print(f"\n📚 Демо отвалы для книг: {demo_count} отвалов ({demo_unique} уникальных пользователей)")
        else:
            print("\n📚 Демо отвалы для книг: 0")

async def main():
    print("🧹 Скрипт очистки метрик отвалов по этапам")
    print("=" * 50)
    
    # Показываем текущие метрики
    await show_abandonment_metrics()
    
    print("\n" + "=" * 50)
    print("⚠️  ВНИМАНИЕ: Этот скрипт удалит ВСЕ метрики отвалов!")
    print("   Это действие НЕОБРАТИМО!")
    
    # Автоматическое подтверждение для сервера
    print("\n🔄 Продолжаем автоматически...")
    
    # Выполняем очистку
    await cleanup_abandonment_metrics()
    
    print("\n🎉 Очистка метрик отвалов завершена!")

if __name__ == "__main__":
    asyncio.run(main())
