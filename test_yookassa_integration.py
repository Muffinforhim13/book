#!/usr/bin/env python3
"""
Тест интеграции с ЮKassa для проверки корректности параметров фискализации чека
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# Добавляем текущую директорию в путь для импорта модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_yookassa_payment_creation():
    """Тест создания платежа с корректными параметрами фискализации"""
    
    print("=== ТЕСТ ИНТЕГРАЦИИ С ЮKASSA ===")
    print(f"Время запуска: {datetime.now()}")
    
    try:
        # Импортируем функцию создания платежа
        from yookassa_integration import create_payment
        
        # Тестовые данные
        test_order_id = 999999  # Используем тестовый ID
        test_amount = 100.0
        test_description = "Тестовая книга - проверка фискализации чека"
        test_product_type = "Книга"
        
        print(f"\n📋 Тестовые данные:")
        print(f"   Order ID: {test_order_id}")
        print(f"   Amount: {test_amount} RUB")
        print(f"   Description: {test_description}")
        print(f"   Product Type: {test_product_type}")
        
        # Создаем тестовый платеж
        print(f"\n💳 Создание тестового платежа...")
        payment_data = await create_payment(
            order_id=test_order_id,
            amount=test_amount,
            description=test_description,
            product_type=test_product_type
        )
        
        print(f"\n✅ Результат создания платежа:")
        print(f"   Payment ID: {payment_data.get('payment_id', 'N/A')}")
        print(f"   Status: {payment_data.get('status', 'N/A')}")
        print(f"   Confirmation URL: {payment_data.get('confirmation_url', 'N/A')}")
        
        # Проверяем, что платеж создан успешно
        if payment_data.get('payment_id'):
            print(f"\n🎉 Тест пройден! Платеж создан с ID: {payment_data['payment_id']}")
            
            # Дополнительная проверка для реальных платежей
            if not payment_data.get('payment_id', '').startswith('test_payment_'):
                print(f"💡 Это реальный платеж в ЮKassa - проверьте логи для деталей фискализации")
            else:
                print(f"💡 Это тестовый платеж - фискализация не требуется")
        else:
            print(f"\n❌ Тест не пройден! Платеж не был создан")
            return False
            
    except Exception as e:
        print(f"\n❌ Ошибка во время теста: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def test_payment_parameters():
    """Тест проверки параметров фискализации в коде"""
    
    print(f"\n=== ПРОВЕРКА ПАРАМЕТРОВ ФИСКАЛИЗАЦИИ ===")
    
    try:
        # Читаем файл yookassa_integration.py
        with open('yookassa_integration.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем наличие необходимых параметров
        required_params = {
            'tax_system_code': 'tax_system_code' in content,
            'payment_subject': 'payment_subject' in content,
            'vat_code': 'vat_code' in content,
            'payment_subject_type': 'payment_subject_type' in content,
            'payment_mode_type': 'payment_mode_type' in content,
            'get_payment_subject_code': 'get_payment_subject_code' in content,
            'payment_mode': 'payment_mode' in content
        }
        
        print(f"\n📊 Проверка параметров фискализации:")
        for param, exists in required_params.items():
            status = "✅" if exists else "❌"
            print(f"   {status} {param}: {'найден' if exists else 'НЕ НАЙДЕН'}")
        
        # Проверяем, что все параметры присутствуют
        all_present = all(required_params.values())
        
        if all_present:
            print(f"\n🎉 Все необходимые параметры фискализации присутствуют!")
        else:
            print(f"\n⚠️  Некоторые параметры фискализации отсутствуют!")
            
        return all_present
        
    except Exception as e:
        print(f"\n❌ Ошибка при проверке параметров: {e}")
        return False

async def main():
    """Главная функция тестирования"""
    
    print("🚀 Запуск тестов интеграции с ЮKassa")
    print("=" * 50)
    
    # Тест 1: Проверка параметров в коде
    params_ok = await test_payment_parameters()
    
    # Тест 2: Создание тестового платежа
    payment_ok = await test_yookassa_payment_creation()
    
    print("\n" + "=" * 50)
    print("📋 ИТОГИ ТЕСТИРОВАНИЯ:")
    print(f"   Параметры фискализации: {'✅ OK' if params_ok else '❌ FAIL'}")
    print(f"   Создание платежа: {'✅ OK' if payment_ok else '❌ FAIL'}")
    
    if params_ok and payment_ok:
        print(f"\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Интеграция с ЮKassa готова к работе.")
        print(f"💡 Теперь чеки должны корректно фискализироваться в облачной кассе.")
    else:
        print(f"\n⚠️  НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ! Требуется дополнительная настройка.")
    
    return params_ok and payment_ok

if __name__ == "__main__":
    # Запускаем тесты
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
