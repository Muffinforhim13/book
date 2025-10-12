"""
Функции валидации для Telegram бота
"""
import re
from typing import Dict, Any

def validate_email(email: str) -> Dict[str, Any]:
    """
    Валидация email адреса
    
    Args:
        email: Email адрес для проверки
        
    Returns:
        Dict с ключами 'is_valid' (bool) и 'error' (str)
    """
    if not email:
        return {"is_valid": False, "error": "Email обязателен"}
    
    # Приводим к нижнему регистру и убираем пробелы
    clean_email = email.lower().strip()
    
    # Проверяем базовый формат email
    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if not re.match(email_regex, clean_email):
        return {"is_valid": False, "error": "Неверный формат email"}
    
    # Проверяем длину
    if len(clean_email) > 254:
        return {"is_valid": False, "error": "Email слишком длинный (максимум 254 символа)"}
    
    # Проверяем, что домен не слишком короткий
    parts = clean_email.split('@')
    if len(parts[1]) < 3:
        return {"is_valid": False, "error": "Неверный домен email"}
    
    # Проверяем, что нет двойных точек
    if '..' in clean_email:
        return {"is_valid": False, "error": "Email не может содержать двойные точки"}
    
    return {"is_valid": True, "error": ""}


def validate_phone(phone: str) -> Dict[str, Any]:
    """
    Валидация номера телефона
    
    Args:
        phone: Номер телефона для проверки
        
    Returns:
        Dict с ключами 'is_valid' (bool) и 'error' (str)
    """
    if not phone:
        return {"is_valid": False, "error": "Номер телефона обязателен"}
    
    # Убираем все пробелы, скобки, дефисы и плюсы для проверки
    clean_phone = re.sub(r'[\s\(\)\-\+]', '', phone)
    
    # Проверяем, что остались только цифры
    if not re.match(r'^\d+$', clean_phone):
        return {"is_valid": False, "error": "Номер телефона должен содержать только цифры, пробелы, скобки и дефисы"}
    
    # Проверяем длину (для России: 10-15 цифр)
    if len(clean_phone) < 10 or len(clean_phone) > 15:
        return {"is_valid": False, "error": "Номер телефона должен содержать от 10 до 15 цифр"}
    
    # Проверяем российские номера
    if len(clean_phone) == 11:
        # Номер с кодом страны +7 или 8
        if clean_phone[0] not in ['7', '8']:
            return {"is_valid": False, "error": "Номер должен начинаться с 7 или 8 (код России)"}
        
        # Проверяем код оператора (второй символ должен быть 9)
        if clean_phone[1] != '9':
            return {"is_valid": False, "error": "Неверный код оператора (должен начинаться с 9)"}
    elif len(clean_phone) == 10:
        # Номер без кода страны, должен начинаться с 9
        if clean_phone[0] != '9':
            return {"is_valid": False, "error": "Номер должен начинаться с 9 (код оператора)"}
    
    return {"is_valid": True, "error": ""}


def clean_email(email: str) -> str:
    """
    Очистка email (приведение к нижнему регистру и удаление пробелов)
    
    Args:
        email: Email для очистки
        
    Returns:
        Очищенный email
    """
    return email.lower().strip()


def format_phone(phone: str) -> str:
    """
    Форматирование номера телефона (приведение к стандартному виду)
    
    Args:
        phone: Номер телефона для форматирования
        
    Returns:
        Отформатированный номер телефона
    """
    clean_phone = re.sub(r'[\s\(\)\-\+]', '', phone)
    
    if len(clean_phone) == 11 and clean_phone[0] == '8':
        # Заменяем 8 на +7
        return f"+7 ({clean_phone[1:4]}) {clean_phone[4:7]}-{clean_phone[7:9]}-{clean_phone[9:]}"
    elif len(clean_phone) == 11 and clean_phone[0] == '7':
        # Добавляем +
        return f"+7 ({clean_phone[1:4]}) {clean_phone[4:7]}-{clean_phone[7:9]}-{clean_phone[9:]}"
    elif len(clean_phone) == 10:
        # Добавляем +7
        return f"+7 ({clean_phone[0:3]}) {clean_phone[3:6]}-{clean_phone[6:8]}-{clean_phone[8:]}"
    
    # Возвращаем как есть, если формат неизвестен
    return phone


# Примеры использования:
if __name__ == "__main__":
    # Тестирование валидации email
    emails = ["user@example.com", "invalid.email", "user..name@example.com", "user@ex.com"]
    for email in emails:
        result = validate_email(email)
        print(f"Email: {email} -> Valid: {result['is_valid']}, Error: {result['error']}")
    
    # Тестирование валидации телефона
    phones = ["+7 (999) 123-45-67", "89991234567", "123", "79991234567"]
    for phone in phones:
        result = validate_phone(phone)
        print(f"Phone: {phone} -> Valid: {result['is_valid']}, Error: {result['error']}")
        if result['is_valid']:
            formatted = format_phone(phone)
            print(f"  Formatted: {formatted}")
