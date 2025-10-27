#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import signal
import threading
from pathlib import Path

def start_process(command, name):
    """Запускает процесс в фоне"""
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"✅ {name} запущен (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"❌ Ошибка запуска {name}: {e}")
        return None

def wait_for_service(port, service_name, max_wait=30):
    """Ждет, пока сервис станет доступным"""
    import socket
    import time
    
    print(f"⏳ Ожидание запуска {service_name} на порту {port}...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('bookai-admin-backend', port))
            sock.close()
            if result == 0:
                print(f"✅ {service_name} доступен на порту {port}")
                return True
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Ошибка проверки {service_name}: {e}")
            time.sleep(1)
    
    print(f"⚠️ {service_name} не стал доступен за {max_wait} секунд")
    return False

def main():
    """Основная функция"""
    print("🚀 Запуск BookAI проекта...")
    print("=" * 50)
    
    # Проверяем переменные окружения
    print("🔧 Загруженные переменные окружения:")
    print(f"   BOT_TOKEN: {os.getenv('BOT_TOKEN', 'НЕ НАЙДЕН')}")
    print(f"   YOOKASSA_SHOP_ID: {os.getenv('YOOKASSA_SHOP_ID', 'НЕ НАЙДЕН')}")
    
    processes = []
    
    # 1. Запуск бэкенда
    print("\n📡 Запуск бэкенда...")
    backend_process = start_process(
        [sys.executable, "-m", "uvicorn", "admin_backend.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"],
        "FastAPI Backend"
    )
    if backend_process:
        processes.append(backend_process)
        
        # Ждем запуска бэкенда
        if not wait_for_service(8001, "FastAPI Backend"):
            print("❌ Бэкенд не запустился, останавливаем все процессы")
            for p in processes:
                p.terminate()
            sys.exit(1)
    
    # 2. Запуск бота
    print("\n🤖 Запуск Telegram бота...")
    print(f"📁 Текущая директория: {os.getcwd()}")
    print(f"🔑 Проверяем переменную BOT_TOKEN: {os.getenv('BOT_TOKEN', 'НЕ НАЙДЕН')}")
    
    bot_process = start_process(
        [sys.executable, "bot.py"],
        "Telegram Bot"
    )
    if bot_process:
        processes.append(bot_process)
    
    print("\n" + "=" * 50)
    print("🎉 Все компоненты запущены!")
    print("📱 Бот: Telegram бот")
    print("🔧 API: http://bookai-admin-backend:8001")
    print("=" * 50)
    print("💡 Для остановки нажмите Ctrl+C")
    
    # Ждем завершения
    try:
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Остановка всех процессов...")
        for process in processes:
            process.terminate()
        print("✅ Все процессы остановлены")

if __name__ == "__main__":
    main()
