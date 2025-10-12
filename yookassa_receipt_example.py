#!/usr/bin/env python3
"""
Пример правильного запроса к ЮKassa с корректными параметрами чека
согласно документации https://yookassa.ru/developers/api#receipt
"""

import json
from typing import Dict, Any

def create_yookassa_payment_request(amount: float, description: str, customer_email: str, product_type: str) -> Dict[str, Any]:
    """
    Создает правильный запрос к ЮKassa с корректными параметрами чека
    
    Args:
        amount: Сумма платежа
        description: Описание платежа
        customer_email: Email покупателя
        product_type: Тип продукта ("Книга" или "Песня")
    
    Returns:
        Словарь с данными запроса к ЮKassa
    """
    
    # Определяем параметры чека согласно 54-ФЗ
    def get_payment_subject(product: str) -> str:
        """Предмет расчета"""
        if product == "Книга":
            return "commodity"  # Товар
        elif product == "Песня":
            return "service"    # Услуга
        else:
            return "service"    # По умолчанию услуга
    
    def get_payment_mode() -> str:
        """Способ расчета"""
        return "full_payment"  # Полный расчет
    
    def get_tax_system_code() -> int:
        """Система налогообложения"""
        return 2  # Упрощенная система налогообложения (УСН, доходы)
    
    # Формируем запрос
    request_data = {
        "amount": {
            "value": str(amount),
            "currency": "RUB"
        },
        "description": description,
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/vsamoeserdce_bot"
        },
        "capture": True,
        "receipt": {
            "customer": {
                "email": customer_email
            },
            "tax_system_code": get_tax_system_code(),  # Система налогообложения
            "items": [
                {
                    "description": description,
                    "quantity": "1.00",
                    "amount": {
                        "value": str(amount),
                        "currency": "RUB"
                    },
                    "vat_code": 4,  # Без НДС
                    "payment_subject": get_payment_subject(product_type),  # Предмет расчета
                    "payment_mode": get_payment_mode()  # Способ расчета
                }
            ]
        }
    }
    
    return request_data

def main():
    """Демонстрация использования"""
    
    # Пример для книги
    book_request = create_yookassa_payment_request(
        amount=1000.00,
        description="Персональная книга 'В самое сердце'",
        customer_email="user@example.com",
        product_type="Книга"
    )
    
    print("=== Запрос для книги ===")
    print(json.dumps(book_request, ensure_ascii=False, indent=2))
    
    print("\n" + "="*50 + "\n")
    
    # Пример для песни
    song_request = create_yookassa_payment_request(
        amount=500.00,
        description="Персональная песня 'В самое сердце'",
        customer_email="user@example.com",
        product_type="Песня"
    )
    
    print("=== Запрос для песни ===")
    print(json.dumps(song_request, ensure_ascii=False, indent=2))
    
    print("\n" + "="*50 + "\n")
    
    # Объяснение параметров
    print("=== Объяснение параметров чека ===")
    print("tax_system_code: 2 - Упрощенная система налогообложения (УСН, доходы)")
    print("payment_subject: 'commodity' - для товаров, 'service' - для услуг")
    print("payment_mode: 'full_payment' - полный расчет")
    print("vat_code: 4 - без НДС")
    print("\nДополнительные коды систем налогообложения:")
    print("1 - Общая система налогообложения")
    print("2 - Упрощенная (УСН, доходы)")
    print("3 - Упрощенная (УСН, доходы минус расходы)")
    print("4 - Единый налог на вмененный доход (ЕНВД)")
    print("5 - Единый сельскохозяйственный налог (ЕСХН)")
    print("6 - Патентная система налогообложения")

if __name__ == "__main__":
    main()
