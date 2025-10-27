import os
import json
import logging
from typing import Dict, Optional, List
from yookassa import Configuration, Payment
from yookassa.domain.request import PaymentRequest
from yookassa.domain.models import Amount, Receipt, ReceiptItem
import aiosqlite
from db import DB_PATH, update_order_status

# Принудительно загружаем .env файл
try:
    import dotenv
    dotenv.load_dotenv()
    print("🔧 .env файл загружен в yookassa_integration.py")
except ImportError:
    print("⚠️ python-dotenv не установлен")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация ЮKassa
class YooKassaConfig:
    def __init__(self):
        print("🔧 Загружаем переменные окружения...")
        self.shop_id = os.getenv('YOOKASSA_SHOP_ID')
        self.secret_key = os.getenv('YOOKASSA_SECRET_KEY')
        self.is_test = os.getenv('YOOKASSA_TEST_MODE', 'true').lower() == 'true'
        
        print(f"🔧 YOOKASSA_SHOP_ID: {self.shop_id}")
        print(f"🔧 YOOKASSA_SECRET_KEY: {'*' * len(self.secret_key) if self.secret_key else 'None'}")
        print(f"🔧 YOOKASSA_TEST_MODE: {self.is_test}")
        
        logger.info(f"🔧 Инициализация YooKassa: Shop ID={self.shop_id}, Secret Key={'*' * len(self.secret_key) if self.secret_key else 'None'}, Test Mode={self.is_test}")
        
        if not self.shop_id or not self.secret_key:
            raise ValueError("YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY должны быть установлены в переменных окружения")
        
        # Инициализация конфигурации ЮKassa
        Configuration.account_id = self.shop_id
        Configuration.secret_key = self.secret_key

# Инициализация конфигурации
try:
    yookassa_config = YooKassaConfig()
    logger.info(f"🔧 YooKassa настроен: Shop ID={yookassa_config.shop_id}, Test Mode={yookassa_config.is_test}")
except ValueError as e:
    print(f"❌ Ошибка инициализации YooKassa: {e}")
    yookassa_config = None
    logger.warning("YooKassa не настроен. Платежи будут эмулироваться.")

# Резервные цены (используются если база данных недоступна)
FALLBACK_PRICES = {
    "Книга": {
        "📄 Электронная книга": 1990,
        "📦 Печатная версия": 7639
    },
    "Песня": {
        "💌 Персональная песня": 2990
    }
}

async def get_pricing_items_from_db() -> Dict:
    """
    Получает актуальные цены из базы данных
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('''
                SELECT product, price, currency, upgrade_price_difference, is_active 
                FROM pricing_items 
                WHERE is_active = 1
            ''') as cursor:
                rows = await cursor.fetchall()
                
                pricing = {}
                for row in rows:
                    product, price, currency, upgrade_price_difference, is_active = row
                    
                    # Определяем категорию продукта
                    logger.info(f"🔍 Определение категории для продукта: '{product}'")
                    
                    if "книга" in product.lower() or "📦" in product or "печатная" in product.lower():
                        category = "Книга"
                        logger.info(f"✅ Продукт '{product}' отнесен к категории 'Книга'")
                    elif "песня" in product.lower():
                        category = "Песня"
                        logger.info(f"✅ Продукт '{product}' отнесен к категории 'Песня'")
                    else:
                        category = "Другое"
                        logger.info(f"⚠️ Продукт '{product}' отнесен к категории 'Другое'")
                    
                    if category not in pricing:
                        pricing[category] = {}
                    
                    pricing[category][product] = price
                
                return pricing if pricing else FALLBACK_PRICES
    except Exception as e:
        logger.error(f"Ошибка получения цен из БД: {e}")
        return FALLBACK_PRICES

def get_product_price(product: str, format_type: str = None) -> float:
    """
    Получает цену продукта (синхронная версия для обратной совместимости)
    """
    # Используем резервные цены для синхронных вызовов
    if product not in FALLBACK_PRICES:
        raise ValueError(f"Неизвестный продукт: {product}")
    
    if format_type:
        if format_type not in FALLBACK_PRICES[product]:
            raise ValueError(f"Неизвестный формат {format_type} для продукта {product}")
        return FALLBACK_PRICES[product][format_type]
    
    # Для песен возвращаем единственную цену
    if product == "Песня":
        return FALLBACK_PRICES[product]["💌 Песня"]
    
    # Для книг возвращаем минимальную цену
    return min(FALLBACK_PRICES[product].values())

async def get_product_price_async(product: str, format_type: str = None) -> float:
    """
    Получает актуальную цену продукта из базы данных
    """
    pricing = await get_pricing_items_from_db()
    
    # Добавляем отладочную информацию
    logger.info(f"🔍 get_product_price_async: product={product}, format_type={format_type}")
    logger.info(f"🔍 pricing keys: {list(pricing.keys())}")
    
    # Если продукт не найден в БД, используем резервные цены
    if product not in pricing:
        logger.warning(f"⚠️ Продукт '{product}' не найден в БД, используем резервные цены")
        if product not in FALLBACK_PRICES:
            raise ValueError(f"Неизвестный продукт: {product}")
        pricing = FALLBACK_PRICES
    
    if format_type:
        if format_type not in pricing[product]:
            logger.error(f"❌ Формат '{format_type}' не найден для продукта '{product}'")
            logger.error(f"❌ Доступные форматы: {list(pricing[product].keys())}")
            raise ValueError(f"Неизвестный формат {format_type} для продукта {product}")
        return pricing[product][format_type]
    
    # Для песен возвращаем единственную цену
    if product == "Песня":
        return pricing[product]["💌 Персональная песня"]
    
    # Для книг возвращаем минимальную цену
    return min(pricing[product].values())

async def get_upgrade_price_difference(product: str, from_format: str, to_format: str) -> float:
    """
    Получает разницу в цене для апгрейда с одного формата на другой
    """
    try:
        from db import get_pricing_items
        pricing_items = await get_pricing_items()
        
        # Ищем целевой формат (куда апгрейдим)
        target_item = None
        for item in pricing_items:
            if item['product'] == to_format:
                target_item = item
                break
        
        if target_item and target_item.get('upgrade_price_difference', 0) > 0:
            return target_item['upgrade_price_difference']
        
        # Если разница не задана в БД, вычисляем её
        from_price = await get_product_price_async(product, from_format)
        to_price = await get_product_price_async(product, to_format)
        return to_price - from_price
        
    except Exception as e:
        logger.error(f"Ошибка получения разницы в цене: {e}")
        # Возвращаем фиксированную разницу для книги
        if product == "Книга" and from_format == "📄 Электронная книга" and to_format == "📦 Печатная версия":
            return 4000.0
        return 0.0

async def init_payments_table():
    """Инициализация таблицы платежей в базе данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                payment_id TEXT UNIQUE,
                amount REAL,
                currency TEXT DEFAULT 'RUB',
                status TEXT,
                payment_method TEXT,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(order_id) REFERENCES orders(id)
            )
        ''')
        await db.commit()

async def create_payment(order_id: int, amount: float, description: str, product_type: str, is_upsell: bool = False) -> Dict:
    """
    Создает платеж в ЮKassa
    
    Args:
        order_id: ID заказа
        amount: Сумма платежа
        description: Описание платежа
        product_type: Тип продукта (книга/песня)
        is_upsell: True если это доплата за печатную версию
    
    Returns:
        Dict с данными платежа
    """
    
    # Если YooKassa не настроен, эмулируем платеж
    if yookassa_config is None:
        logger.info(f"🔧 Эмуляция платежа для заказа {order_id}: {amount} RUB (YooKassa не настроен)")
        logger.info(f"🔧 yookassa_config is None, используем эмуляцию")
        payment_id = f"test_payment_{order_id}_{int(amount)}"
        
        # Сохраняем тестовый платеж в БД
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT OR REPLACE INTO payments 
                (order_id, payment_id, amount, currency, status, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (order_id, payment_id, amount, "RUB", "pending", description))
            await db.commit()
        
        logger.info(f"✅ Тестовый платеж создан: {payment_id}")
        
        # Для тестовых платежей сразу помечаем как успешные
        try:
            await asyncio.sleep(1)  # Ждем 1 секунду
            await update_payment_status(payment_id, 'succeeded')
            
            # Обрабатываем успешный тестовый платеж
            webhook_data = {
                'event': 'payment.succeeded',
                'object': {
                    'id': payment_id,
                    'status': 'succeeded',
                    'amount': {'value': amount},
                    'description': description
                }
            }
            await process_payment_webhook(webhook_data)
            logger.info(f"🚀 TEST PAYMENT: Тестовый платеж {payment_id} обработан немедленно!")
        except Exception as test_error:
            logger.error(f"❌ TEST PAYMENT: Ошибка обработки тестового платежа: {test_error}")
        
        return {
            "payment_id": payment_id,
            "confirmation_url": f"https://yoomoney.ru/checkout/payments/v2/contract?orderId={payment_id}",
            "status": "succeeded"
        }
    
    try:
        logger.info(f"💳 Создание реального платежа в YooKassa для заказа {order_id}: {amount} RUB")
        logger.info(f"💳 yookassa_config настроен: Shop ID={yookassa_config.shop_id}, Test Mode={yookassa_config.is_test}")
        
        # Получаем email пользователя из заказа
        customer_email = "customer@test.com"  # По умолчанию тестовый email
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute('SELECT email FROM orders WHERE id = ?', (order_id,)) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0] and row[0] != "None":
                        customer_email = row[0]
                        logger.info(f"💳 Найден email пользователя: {customer_email}")
                    else:
                        logger.warning(f"💳 Email пользователя не найден для заказа {order_id}, используем тестовый")
        except Exception as e:
            logger.error(f"💳 Ошибка получения email пользователя: {e}")
        
        # Определяем предмет расчета для фискализации
        payment_subject = get_payment_subject(product_type)
        
        # Создаем запрос на платеж
        payment_request = PaymentRequest(
            amount=Amount(value=str(amount), currency="RUB"),
            description=description,
            confirmation={
                "type": "redirect",
                "return_url": f"https://t.me/vsamoeserdce_bot"  # URL вашего бота без параметров
            },
            capture=True,
            receipt={
                "customer": {
                    "email": customer_email  # Реальный email пользователя
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
                        "vat_code": 6,  # НДС не облагается
                        "payment_subject": get_payment_subject_code(product_type),  # Предмет расчета
                        "payment_mode": get_payment_mode()  # Способ расчета
                    }
                ]
            }
        )
        
        # Логируем JSON запрос для отладки
        try:
            # Преобразуем PaymentRequest в словарь для логирования
            request_dict = {
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
                    "tax_system_code": get_tax_system_code(),
                    "items": [
                        {
                            "description": description,
                            "quantity": "1",
                            "amount": {
                                "value": str(amount),
                                "currency": "RUB"
                            },
                            "vat_code": 6,
                            "payment_subject": get_payment_subject_code(product_type),
                            "payment_mode": get_payment_mode()
                        }
                    ]
                }
            }
            logger.info(f"💳 JSON запрос к ЮКассе: {json.dumps(request_dict, ensure_ascii=False, indent=2)}")
        except Exception as e:
            logger.error(f"💳 Ошибка логирования JSON запроса: {e}")
        
        logger.info(f"💳 Данные платежа: сумма={amount}, описание={description}, email={customer_email}")
        logger.info(f"💳 Return URL: https://t.me/vsamoeserdce_bot")
        
        # Создаем платеж в ЮKassa
        logger.info(f"💳 Отправляем запрос в YooKassa...")
        payment = Payment.create(payment_request)
        logger.info(f"💳 Ответ от YooKassa получен: {payment.id}")
        
        # Логируем ответ от ЮКассы
        try:
            response_dict = {
                "id": payment.id,
                "status": payment.status,
                "amount": {
                    "value": str(payment.amount.value),  # Преобразуем Decimal в строку
                    "currency": payment.amount.currency
                },
                "confirmation": {
                    "type": payment.confirmation.type,
                    "confirmation_url": payment.confirmation.confirmation_url
                },
                "created_at": payment.created_at.isoformat() if hasattr(payment.created_at, 'isoformat') else str(payment.created_at),
                "paid": payment.paid
            }
            logger.info(f"💳 Ответ от ЮКассы: {json.dumps(response_dict, ensure_ascii=False, indent=2)}")
        except Exception as e:
            logger.error(f"💳 Ошибка логирования ответа от ЮКассы: {e}")
        
        # Сохраняем платеж в базу данных
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT INTO payments (order_id, payment_id, amount, status, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            ''', (order_id, payment.id, amount, payment.status, description))
            await db.commit()
        
        # Обновляем статус заказа в зависимости от типа платежа
        if is_upsell:
            await update_order_status(order_id, "upsell_payment_created")
        else:
            await update_order_status(order_id, "payment_created")
        
        logger.info(f"✅ Реальный платеж создан в YooKassa: {payment.id}, URL: {payment.confirmation.confirmation_url}")
        
        # Немедленно проверяем статус платежа (для тестирования)
        try:
            import asyncio
            await asyncio.sleep(2)  # Ждем 2 секунды
            payment_status = await get_payment_status(payment.id)
            if payment_status and payment_status.get('status') == 'succeeded':
                logger.info(f"🚀 IMMEDIATE CHECK: Платеж {payment.id} уже успешен!")
                # Обрабатываем успешный платеж немедленно
                webhook_data = {
                    'event': 'payment.succeeded',
                    'object': {
                        'id': payment.id,
                        'status': 'succeeded',
                        'amount': {'value': amount},
                        'description': description
                    }
                }
                await process_payment_webhook(webhook_data)
                await update_payment_status(payment.id, 'succeeded')
        except Exception as immediate_error:
            logger.error(f"❌ IMMEDIATE CHECK: Ошибка немедленной проверки: {immediate_error}")
        
        return {
            "payment_id": payment.id,
            "confirmation_url": payment.confirmation.confirmation_url,
            "status": payment.status,
            "amount": amount
        }
        
    except Exception as e:
        logger.error(f"Ошибка создания платежа: {e}")
        raise

async def get_payment_status(payment_id: str) -> Optional[Dict]:
    """
    Получает статус платежа из ЮKassa
    
    Args:
        payment_id: ID платежа в ЮKassa
    
    Returns:
        Dict с данными платежа или None
    """
    
    # Если это тестовый платеж
    if payment_id.startswith("test_payment_"):
        # Получаем данные из БД
        payment_data = await get_payment_by_payment_id(payment_id)
        if payment_data:
            return {
                "payment_id": payment_data["payment_id"],
                "status": payment_data["status"],
                "amount": payment_data["amount"],
                "currency": payment_data["currency"],
                "paid": payment_data["status"] == "succeeded",
                "created_at": payment_data["created_at"]
            }
        return None
    
    # Если YooKassa не настроен, возвращаем None
    if yookassa_config is None:
        logger.warning("YooKassa не настроен, невозможно получить статус платежа")
        return None
    
    try:
        payment = Payment.find_one(payment_id)
        return {
            "payment_id": payment.id,
            "status": payment.status,
            "amount": payment.amount.value,
            "currency": payment.amount.currency,
            "paid": payment.paid,
            "created_at": payment.created_at if isinstance(payment.created_at, str) else (payment.created_at.isoformat() if payment.created_at else None)
        }
    except Exception as e:
        logger.error(f"Ошибка получения статуса платежа {payment_id}: {e}")
        return None

async def update_payment_status(payment_id: str, status: str):
    """
    Обновляет статус платежа в базе данных
    
    Args:
        payment_id: ID платежа
        status: Новый статус
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            UPDATE payments SET status = ?, updated_at = datetime('now') WHERE payment_id = ?
        ''', (status, payment_id))
        await db.commit()

async def get_payment_by_order_id(order_id: int) -> Optional[Dict]:
    """
    Получает платеж по ID заказа
    
    Args:
        order_id: ID заказа
    
    Returns:
        Dict с данными платежа или None
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT * FROM payments WHERE order_id = ? ORDER BY created_at DESC LIMIT 1
        ''', (order_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None

async def process_payment_webhook(webhook_data: Dict) -> bool:
    """
    Обрабатывает webhook от ЮKassa
    
    Args:
        webhook_data: Данные webhook'а
    
    Returns:
        True если обработка прошла успешно
    """
    try:
        logger.info(f"🔔 Обрабатываем webhook: {webhook_data}")
        
        event = webhook_data.get('event')
        payment_data = webhook_data.get('object', {})
        payment_id = payment_data.get('id')
        status = payment_data.get('status')
        
        logger.info(f"🔍 Event: {event}, Payment ID: {payment_id}, Status: {status}")
        
        if not payment_id or not status:
            logger.error("Неверные данные webhook'а")
            return False
        
        # Обновляем статус платежа в базе данных
        await update_payment_status(payment_id, status)
        
        # Получаем заказ по платежу
        payment = await get_payment_by_payment_id(payment_id)
        if not payment:
            logger.error(f"Платеж {payment_id} не найден в базе данных")
            return False
        
        order_id = payment['order_id']
        
        # Обрабатываем статус платежа
        if status == 'succeeded':
            # Проверяем, является ли это доплатой
            description = payment.get('description', '')
            is_additional_payment = 'доплата' in description.lower() or 'доплата за печатную версию' in description
            
            if is_additional_payment:
                logger.info(f"Доплата {payment_id} для заказа {order_id} оплачена")
                # Обновляем статус заказа на upsell_paid для доплаты
                await update_order_status(order_id, "upsell_paid")
                logger.info(f"✅ Статус заказа {order_id} обновлен на 'upsell_paid' после доплаты")
                
                # Записываем событие доплаты
                try:
                    from db import track_event, get_order, add_outbox_task
                    order = await get_order(order_id)
                    if order:
                        user_id = order.get('user_id')
                        product_type = order.get('product_type', order.get('product', 'Неизвестно'))
                        # Безопасное получение суммы платежа
                        payment_amount = payment.get('amount', 0)
                        if isinstance(payment_amount, dict):
                            amount = float(payment_amount.get('value', 0))
                        else:
                            amount = float(payment_amount)
                        
                        await track_event(
                            user_id=user_id,
                            event_type='upsell_purchased',
                            event_data={
                                'order_id': order_id,
                                'payment_id': payment_id,
                                'amount': amount,
                                'product': product_type
                            },
                            product_type=product_type,
                            order_id=order_id,
                            amount=amount
                        )
                        logger.info(f"✅ Записано событие upsell_purchased для заказа {order_id}")
                        
                        # Отправляем уведомление пользователю о успешной доплате
                        upsell_message = "✅ <b>Доплата прошла успешно!</b>\n\n"
                        
                        if 'печатную версию' in description:
                            upsell_message += (
                                "Теперь нам нужны ваши данные для доставки печатной книги.\n\n"
                                "Пожалуйста, введите адрес доставки, например: 455000, Республика Татарстан, г. Казань, ул. Ленина, д. 52, кв. 43"
                            )
                            
                            # Добавляем задачу для отправки сообщения с запросом адреса
                            await add_outbox_task(
                                order_id=order_id,
                                user_id=user_id,
                                type_="text_message",
                                content=upsell_message
                            )
                            
                            # Добавляем задачу для перехода к состоянию ввода адреса
                            await add_outbox_task(
                                order_id=order_id,
                                user_id=user_id,
                                type_="set_state",
                                content="DeliveryStates.waiting_for_address"
                            )
                            
                            logger.info(f"✅ WEBHOOK: Добавлены задачи для печатной версии для заказа {order_id}")
                        else:
                            upsell_message += "Ваша услуга будет предоставлена в ближайшее время."
                            
                            # Добавляем задачу для отправки сообщения
                            await add_outbox_task(
                                order_id=order_id,
                                user_id=user_id,
                                type_="text_with_buttons",
                                content=upsell_message,
                                button_text="💌 Создать песню|✅ Завершить",
                                button_callback="create_song|finish_order"
                            )
                            
                            logger.info(f"✅ WEBHOOK: Добавлены задачи для дополнительной услуги для заказа {order_id}")
                        
                        logger.info(f"✅ WEBHOOK: Добавлено уведомление о доплате для заказа {order_id}")
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка записи события доплаты: {e}")
            else:
                # СНАЧАЛА добавляем задачу с кнопками, ПОТОМ обновляем статус
                logger.info(f"Основной платеж {payment_id} для заказа {order_id} оплачен")
                
                # Отправляем уведомление пользователю о согласии на обработку данных
                try:
                    from db import add_outbox_task, get_order
                    order = await get_order(order_id)
                    if order:
                        user_id = order.get('user_id')
                        order_data = order.get('order_data', '{}')
                        
                        # Парсим order_data для определения типа продукта
                        import json
                        try:
                            parsed_data = json.loads(order_data) if isinstance(order_data, str) else order_data
                            product_type = parsed_data.get('product', 'подарок')
                        except:
                            product_type = 'подарок'
                        
                        # Формируем сообщение с кнопками согласия
                        consent_message = (
                            f"✅ Спасибо за доверие! Ваш заказ №{order_id:04d} уже в работе ❤️\n"
                            f"Чтобы мы могли создать ваш особенный подарок, нам нужно ваше согласие на обработку персональных данных.\n\n"
                            f"📋 Вся информация о том, как мы бережно храним ваши данные, здесь:\n"
                            f"1. <a href='https://vsamoeserdtse.ru/approval'>Согласие на обработку персональных данных</a>\n"
                            f"2. <a href='https://vsamoeserdtse.ru/oferta'>Оферта о заключении договора оказания услуг, Политика конфиденциальности и обработки персональных данных</a>\n\n"
                            f"Даете согласие на обработку персональных данных? 💕"
                        )
                        
                        # Добавляем задачу в outbox для отправки с кнопками
                        await add_outbox_task(
                            order_id=order_id,
                            user_id=user_id,
                            type_="text_with_buttons",
                            content=consent_message,
                            button_text="✅ Согласен|❌ Не согласен",
                            button_callback="personal_data_consent_yes|personal_data_consent_no"
                        )
                        logger.info(f"✅ WEBHOOK: Добавлено уведомление о согласии text_with_buttons для заказа {order_id}, user_id={user_id}")
                        logger.info(f"🚀 АВТОМАТИЧЕСКИЙ ПОТОК: Пользователь {user_id} получит сообщение автоматически без нажатия кнопки!")
                        
                        # Теперь обновляем статус заказа (после добавления задачи)
                        # Безопасное получение суммы платежа
                        payment_amount = payment.get('amount', 0)
                        if isinstance(payment_amount, dict):
                            amount = float(payment_amount.get('value', 0))
                        else:
                            amount = float(payment_amount)
                        await update_order_status(order_id, "paid", amount)
                        logger.info(f"✅ WEBHOOK: Статус заказа {order_id} обновлен на 'paid' с суммой {amount}")
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки уведомления о согласии: {e}")
                    # Если не удалось добавить задачу, все равно обновляем статус
                    # Безопасное получение суммы платежа
                    payment_amount = payment.get('amount', 0)
                    if isinstance(payment_amount, dict):
                        amount = float(payment_amount.get('value', 0))
                    else:
                        amount = float(payment_amount)
                    await update_order_status(order_id, "paid", amount)
                logger.info(f"Заказ {order_id} оплачен")
                
                # Записываем событие покупки
                try:
                    from db import track_event, get_order
                    order = await get_order(order_id)
                    if order:
                        user_id = order.get('user_id')
                        product_type = order.get('product_type', order.get('product', 'Неизвестно'))
                        # Безопасное получение суммы платежа
                        payment_amount = payment.get('amount', 0)
                        if isinstance(payment_amount, dict):
                            amount = float(payment_amount.get('value', 0))
                        else:
                            amount = float(payment_amount)
                        
                        await track_event(
                            user_id=user_id,
                            event_type='purchase_completed',
                            event_data={
                                'order_id': order_id,
                                'payment_id': payment_id,
                                'amount': amount,
                                'product': product_type
                            },
                            product_type=product_type,
                            order_id=order_id,
                            amount=amount
                        )
                        logger.info(f"✅ Записано событие purchase_completed для заказа {order_id}")
                except Exception as e:
                    logger.error(f"❌ Ошибка записи события покупки: {e}")
            
            # Отменяем прогревочные сообщения при успешной оплате
            try:
                from db import cleanup_trigger_messages_by_type
                await cleanup_trigger_messages_by_type(order_id, ['song_warming_example', 'song_warming_motivation'])
                logger.info(f"✅ Отменены прогревочные сообщения для заказа {order_id}")
            except Exception as e:
                logger.error(f"❌ Ошибка отмены прогревочных сообщений: {e}")
        elif status == 'canceled':
            # Проверяем, является ли это доплатой
            description = payment.get('description', '')
            is_additional_payment = 'доплата' in description.lower() or 'доплата за печатную версию' in description
            
            if is_additional_payment:
                logger.info(f"Доплата {payment_id} для заказа {order_id} отменена")
            else:
                await update_order_status(order_id, "payment_canceled")
                logger.info(f"Платеж для заказа {order_id} отменен")
        elif status == 'pending':
            # Проверяем, является ли это доплатой
            description = payment.get('description', '')
            is_additional_payment = 'доплата' in description.lower() or 'доплата за печатную версию' in description
            
            if is_additional_payment:
                await update_order_status(order_id, "upsell_payment_pending")
                logger.info(f"Доплата для заказа {order_id} в обработке")
            else:
                await update_order_status(order_id, "payment_pending")
                logger.info(f"Платеж для заказа {order_id} в обработке")
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка обработки webhook'а: {e}")
        return False

async def get_payment_by_payment_id(payment_id: str) -> Optional[Dict]:
    """
    Получает платеж по ID платежа
    
    Args:
        payment_id: ID платежа в ЮKassa
    
    Returns:
        Dict с данными платежа или None
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT * FROM payments WHERE payment_id = ? ORDER BY created_at DESC LIMIT 1
        ''', (payment_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None

async def refund_payment(payment_id: str, amount: Optional[float] = None) -> bool:
    """
    Возвращает платеж
    
    Args:
        payment_id: ID платежа
        amount: Сумма возврата (если None, возвращается полная сумма)
    
    Returns:
        True если возврат прошел успешно
    """
    try:
        payment = Payment.find_one(payment_id)
        
        if amount is None:
            amount = float(payment.amount.value)
        
        refund = payment.create_refund({
            "amount": {
                "value": str(amount),
                "currency": "RUB"
            }
        })
        
        logger.info(f"Возврат {amount} RUB для платежа {payment_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка возврата платежа {payment_id}: {e}")
        return False

async def get_payment_history(order_id: int) -> List[Dict]:
    """
    Получает историю платежей для заказа
    
    Args:
        order_id: ID заказа
    
    Returns:
        Список платежей
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT * FROM payments WHERE order_id = ? ORDER BY created_at DESC
        ''', (order_id,)) as cursor:
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

def get_payment_subject(product: str, format_type: str = None) -> str:
    """
    Определяет предмет расчета для фискализации чека (устаревшая функция)
    
    Args:
        product: Тип продукта
        format_type: Формат (для книг)
    
    Returns:
        Предмет расчета (commodity/service)
    """
    if product == "Книга":
        return "commodity"  # Книги - это товары
    elif product == "Песня":
        return "service"    # Песни - это услуги
    else:
        return "service"    # По умолчанию услуга

def get_payment_subject_code(product: str, format_type: str = None) -> str:
    """
    Определяет предмет расчета для фискализации чека согласно 54-ФЗ
    
    Args:
        product: Тип продукта
        format_type: Формат (для книг)
    
    Returns:
        Предмет расчета (commodity/service)
    """
    if product == "Книга":
        return "commodity"  # Товар
    elif product == "Песня":
        return "service"    # Услуга
    else:
        return "service"    # По умолчанию услуга

def get_payment_mode() -> str:
    """
    Определяет способ расчета для фискализации чека
    
    Returns:
        Способ расчета (full_payment/full_prepayment)
    """
    return "full_payment"  # Полный расчет

def get_tax_system_code() -> int:
    """
    Определяет систему налогообложения
    
    Returns:
        Код системы налогообложения (1-6)
    """
    return 2  # Упрощенная система налогообложения (УСН, доходы)

def format_payment_description(product: str, format_type: str = None, order_id: int = None) -> str:
    """
    Формирует описание платежа
    
    Args:
        product: Тип продукта
        format_type: Формат (для книг)
        order_id: ID заказа
    
    Returns:
        Описание платежа
    """
    if product == "Книга":
        if format_type == "Электронная книга":
            return f"Электронная книга - заказ #{order_id}" if order_id else "Электронная книга"
        elif format_type == "Электронная + Печатная версия":
            return f"Книга (электронная + печатная) - заказ #{order_id}" if order_id else "Книга (электронная + печатная)"
        else:
            return f"Книга - заказ #{order_id}" if order_id else "Книга"
    elif product == "Песня":
        return f"Персональная песня - заказ #{order_id}" if order_id else "Персональная песня"
    else:
        return f"{product} - заказ #{order_id}" if order_id else product

# Импорт функции обновления статуса заказа
from db import update_order_status 