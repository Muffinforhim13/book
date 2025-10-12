import subprocess
import sys
import os
import time
import signal
import dotenv

# Загружаем переменные окружения из .env файла
dotenv.load_dotenv()

# Отладочная информация о загрузке переменных
print(f"🔧 Загруженные переменные окружения:")
print(f"   TELEGRAM_BOT_TOKEN: {os.getenv('TELEGRAM_BOT_TOKEN', 'НЕ НАЙДЕН')}")
print(f"   YOOKASSA_SHOP_ID: {os.getenv('YOOKASSA_SHOP_ID', 'НЕ НАЙДЕН')}")

def run_process(command, cwd=None, name=""):
    """Запускает процесс и возвращает его объект"""
    try:
        # Передаем переменные окружения в subprocess
        env = os.environ.copy()
        process = subprocess.Popen(command, cwd=cwd, shell=True, env=env)
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
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if result == 0:
                print(f"✅ {service_name} доступен на порту {port}")
                return True
        except:
            pass
        time.sleep(1)
    
    print(f"⚠️ {service_name} не стал доступен за {max_wait} секунд")
    return False

if __name__ == "__main__":
    processes = []
    
    print("🚀 Запуск BookAI проекта...")
    print("=" * 50)
    
    # 1. Запуск бэкенда (FastAPI)
    print("\n📡 Запуск бэкенда...")
    backend_process = run_process(
        [sys.executable, "-m", "uvicorn", "admin_backend.main:app", "--host", "0.0.0.0", "--port", "8002", "--reload"],
        name="FastAPI Backend"
    )
    if backend_process:
        processes.append(backend_process)
        
        # Ждем запуска бэкенда
        if not wait_for_service(8002, "FastAPI Backend"):
            print("❌ Бэкенд не запустился, останавливаем все процессы")
            for p in processes:
                p.terminate()
            sys.exit(1)
    
    # 2. Запуск бота
    print("\n🤖 Запуск Telegram бота...")
    print(f"📁 Текущая директория: {os.getcwd()}")
    print(f"🔑 Проверяем переменную TELEGRAM_BOT_TOKEN: {os.getenv('TELEGRAM_BOT_TOKEN', 'НЕ НАЙДЕН')}")
    
    bot_process = run_process(
        [sys.executable, "bot.py"],
        name="Telegram Bot"
    )
    if bot_process:
        processes.append(bot_process)
    
    # 3. Запуск фронтенда
    print("\n🌐 Запуск фронтенда...")
    frontend_process = run_process(
        ["npm", "start"],
        cwd="admin_frontend",
        name="React Frontend"
    )
    if frontend_process:
        processes.append(frontend_process)
    
    print("\n" + "=" * 50)
    print("🎉 Все компоненты запущены!")
    print("📱 Бот: Telegram бот")
    print("🔧 API: http://localhost:8002")
    print("🌐 Фронтенд: http://localhost:3002")
    print("=" * 50)
    print("💡 Для остановки нажмите Ctrl+C")
    
    try:
        # Ждем завершения всех процессов
        for p in processes:
            if p:
                p.wait()
    except KeyboardInterrupt:
        print("\n\n🛑 Получен сигнал остановки...")
        print("⏳ Остановка всех процессов...")
        
        for p in processes:
            if p and p.poll() is None:  # Если процесс еще работает
                try:
                    p.terminate()
                    p.wait(timeout=5)  # Ждем корректного завершения
                except subprocess.TimeoutExpired:
                    p.kill()  # Принудительно завершаем
                    print(f"⚠️ Процесс {p.pid} принудительно завершен")
        
        print("✅ Все процессы остановлены")
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        for p in processes:
            if p:
                p.terminate() 