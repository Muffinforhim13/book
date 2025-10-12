#!/usr/bin/env python3
import asyncio
import aiosqlite

async def update_gender_message():
    async with aiosqlite.connect('bookai.db') as db:
        # Обновляем сообщение с ключом gender_request
        await db.execute('''
            UPDATE bot_messages 
            SET content = ? 
            WHERE message_key = ?
        ''', (
            "Замечательный выбор ✨\nМы позаботимся о том, чтобы твоя книга получилась душевной и бережно сохранила все важные воспоминания.\n\nОтветь на несколько вопросов и мы начнём собирать твою историю 📖\n\n👤 Выбери свой пол:",
            "gender_request"
        ))
        
        await db.commit()
        print("✅ Сообщение gender_request обновлено!")
        
        # Проверяем результат
        async with db.execute('SELECT message_key, content FROM bot_messages WHERE message_key = ?', ('gender_request',)) as cursor:
            row = await cursor.fetchone()
            print(f"Новое содержимое: {row[1]}")

if __name__ == "__main__":
    asyncio.run(update_gender_message())
