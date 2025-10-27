from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Query, Request, Header
import time
import json
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi import FastAPI

# Инициализируем FastAPI до объявления эндпоинтов song-quiz
try:
    app
except NameError:
    app = FastAPI()
from admin_backend.auth import authenticate_manager, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM
from admin_backend.users import init_managers_db
from datetime import timedelta, datetime, timezone
import pytz
from jose import JWTError, jwt

# Настройка московского времени
MSK_TZ = pytz.timezone('Europe/Moscow')

# Константа для списка оплаченных статусов (используется в метриках, аналитике и выгрузке)
# Все статусы после 'paid' считаются оплаченными
# ВАЖНО: 
# - 'questions_completed' НЕ включен, т.к. происходит ДО оплаты
# - 'draft_sent' включен, т.к. черновик отправляется ПОСЛЕ оплаты
PAID_ORDER_STATUSES = [
    # Основной статус оплаты
    'paid',
    
    # Статусы после оплаты для книг
    'waiting_story_options',
    'waiting_story_choice',
    'story_selected',
    'story_options_sent',
    'pages_selected',
    'covers_sent',
    'waiting_cover_choice',
    'cover_selected',
    'waiting_draft',
    'draft_sent',
    'editing',
    'waiting_feedback',
    'feedback_processed',
    'prefinal_sent',
    'waiting_final',
    'ready',
    'waiting_delivery',
    'print_delivery_pending',
    'final_sent',
    'delivered',
    'completed',
    
    # Статусы для песен после оплаты
    'collecting_facts',
    'waiting_plot_options',
    'plot_selected',
    'waiting_final_version',
    
    # Доплаты (статусы когда доплата оплачена или ожидается)
    'upsell_payment_created',    # Создан платёж за доплату (основная покупка УЖЕ оплачена)
    'upsell_payment_pending',    # Ожидает доплаты (основная покупка УЖЕ оплачена)
    'upsell_paid',               # Доплата оплачена
    'additional_payment_paid'    # Дополнительная оплата получена
]

# Функция для маппинга статусов заказов в понятные названия прогресса
def get_order_progress_status(order_status: str, product_type: str) -> str:
    """
    Маппинг статусов заказов в понятные названия прогресса
    Использует ту же логику, что и в OrderDetails.tsx
    """
    if product_type == "Песня":
        # Отображаем статусы для песни так же, как во вкладке Orders
        song_progress_map = {
            'created': 'Выбран продукт',
            'product_selected': 'Выбран продукт',
            'gender_selected': 'Выбран пол',
            'recipient_selected': 'Выбран получатель',
            'recipient_name_entered': 'Введено имя получателя',
            'gift_reason_entered': 'Указан повод подарка',
            'style_selected': 'Выбран стиль',
            'character_created': 'Создан персонаж',
            'photos_uploaded': 'Загружены фото',
            'voice_selection': 'Выбор голоса',
            'waiting_manager': 'Демо контент',
            'demo_sent': 'Демо контент',
            'demo_content': 'Демо контент',
            'payment_created': 'Создан платеж',
            'waiting_payment': 'Ожидает оплаты',
            'payment_pending': 'Ожидает оплаты',
            'paid': 'Оплачен',
            'collecting_facts': 'Сбор фактов',
            'questions_completed': 'Сбор фактов',
            'waiting_draft': 'Ожидает черновика',
            'draft_sent': 'Черновик отправлен',
            'waiting_feedback': 'Ожидает отзывов',
            'feedback_processed': 'Внесение правок',
            'editing': 'Внесение правок',
            'prefinal_sent': 'Предфинальная версия отправлена',
            'waiting_final': 'Ожидает финальной версии',
            'final_sent': 'Финальная песня отправлена',
            'ready': 'Готово',
            'delivered': 'Завершено',
            'completed': 'Завершено',
            'upsell_payment_pending': 'Доплата в обработке',
            'upsell_paid': 'Завершено'
        }
        return song_progress_map.get(order_status, 'Выбран продукт')
    
    elif product_type in ["Книга", "Книга печатная", "Книга электронная"]:
        # Отображаем статусы для книги так же, как во вкладке Orders (как в translateStatus)
        book_progress_map = {
            'created': 'Создан',
            'product_selected': 'Выбран продукт',
            'gender_selected': 'Выбран пол',
            'recipient_selected': 'Выбран получатель',
            'recipient_name_entered': 'Введено имя получателя',
            'first_name_entered': 'Введено имя',
            'relation_selected': 'Выбран получатель',
            'character_description_entered': 'Описание персонажа',
            'gift_reason_entered': 'Указан повод подарка',
            'main_photos_uploaded': 'Загружены фото основного героя',
            'hero_name_entered': 'Введено имя второго героя',
            'hero_description_entered': 'Описание второго персонажа',
            'hero_photos_uploaded': 'Загружены фото второго героя',
            'joint_photo_uploaded': 'Загружено совместное фото',
            'style_selected': 'Выбран стиль',
            'character_created': 'Создан персонаж',
            'photos_uploaded': 'Загружены фото',
            'collecting_facts': 'Сбор фактов',
            'questions_completed': 'Завершены вопросы',
            'waiting_manager': 'Ожидает менеджера',
            'demo_sent': '✅ Отправлено демо',
            'demo_content': 'Демо контент',
            'story_options_sent': '✅ Отправлены варианты сюжета',
            'waiting_payment': 'Ожидает оплаты',
            'payment_pending': 'Ожидает оплаты',
            'payment_created': 'Создан платеж',
            'paid': 'Оплачен',
            'waiting_story_choice': 'Ожидает выбора сюжета',
            'waiting_story_options': 'Ожидает вариантов сюжета',
            'story_selected': 'Сюжет выбран',
            'pages_selected': 'Страницы выбраны',
            'waiting_draft': 'Ожидает черновика',
            'draft_sent': '✅ Черновик отправлен',
            'waiting_feedback': 'Ожидает отзыва',
            'feedback_processed': 'Обработан отзыв',
            'editing': 'Внесение правок',
            'prefinal_sent': '✅ Предфинальная версия отправлена',
            'waiting_final': 'Ожидает финала',
            'final_sent': '✅ Финальная отправлена',
            'ready': 'Готов',
            'waiting_delivery': 'Ожидает доставки',
            'print_delivery_pending': 'Отправка печатной версии',
            'delivered': 'Доставлен',
            'completed': 'Завершен',
            'waiting_cover_choice': 'Ожидает выбора обложки',
            'cover_selected': 'Обложка выбрана',
            'upsell_payment_created': 'Ожидание доплаты',
            'upsell_payment_pending': 'Ожидание доплаты',
            'upsell_paid': 'Доплата получена',
            'additional_payment_paid': 'Доплата за печатную версию оплачена'
        }
        # По умолчанию возвращаем самый ранний осмысленный шаг
        return book_progress_map.get(order_status, 'Выбран продукт')
    
    else:
        # Общий маппинг для неизвестных типов
        general_progress_map = {
            'created': 'Создание персонажа',
            'character_created': 'Создание персонажа',
            'demo_content': 'Демо контент',
            'paid': 'Оплачено',
            'waiting_draft': 'Ожидает черновика',
            'editing': 'Редактирование',
            'ready': 'Готово',
            'delivered': 'Завершено',
            'completed': 'Завершено',
            'upsell_payment_pending': 'Доплата в обработке',
            'upsell_paid': 'Завершено'
        }
        return general_progress_map.get(order_status, 'Создание персонажа')

# Функция для получения типа продукта из заказа
async def get_order_product_type(order_id: int) -> str:
    """Получает тип продукта из order_data конкретного заказа"""
    try:
        import aiosqlite
        DB_PATH = 'bookai.db'
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('''
                SELECT order_data FROM orders WHERE id = ?
            ''', (order_id,)) as cursor:
                row = await cursor.fetchone()
                if row and row[0]:
                    try:
                        order_data = json.loads(row[0])
                        product_type = order_data.get('product', '')
                        if product_type and product_type not in ['', 'None', 'null', 'undefined']:
                            return product_type
                    except json.JSONDecodeError:
                        pass
                
                # Если не найден в order_data, ищем в event_metrics для этого заказа
                async with db.execute('''
                    SELECT product_type FROM event_metrics 
                    WHERE order_id = ? AND product_type IS NOT NULL AND product_type != ''
                    ORDER BY timestamp ASC
                    LIMIT 1
                ''', (order_id,)) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0]:
                        return row[0]
                
                return 'Неизвестно'
    except Exception as e:
        print(f"❌ Ошибка получения типа продукта для заказа {order_id}: {e}")
        return 'Неизвестно'

# Функция для получения формата продукта
async def get_product_format(order_id: int) -> str:
    """Получает формат продукта из order_data конкретного заказа"""
    try:
        import aiosqlite
        DB_PATH = 'bookai.db'
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('''
                SELECT order_data FROM orders WHERE id = ?
            ''', (order_id,)) as cursor:
                row = await cursor.fetchone()
                if row and row[0]:
                    try:
                        order_data = json.loads(row[0])
                        product = order_data.get('product', '')
                        book_format = order_data.get('book_format', '')
                        format_field = order_data.get('format', '')
                        
                        if product == 'Книга':
                            # Проверяем, есть ли информация о формате
                            if book_format or format_field:
                                # Проверяем формат книги
                                is_electronic = (
                                    book_format == 'Электронная книга' or 
                                    format_field == '📄 Электронная книга' or
                                    'Электронная' in str(book_format) or
                                    'Электронная' in str(format_field)
                                )
                                
                                if is_electronic:
                                    return 'Электронная'
                                else:
                                    return 'Печатная'
                            else:
                                return 'Не выбрано'
                        elif product == 'Песня':
                            return '-'
                        else:
                            return 'Неизвестно'
                    except json.JSONDecodeError:
                        pass
                
                return 'Неизвестно'
    except Exception as e:
        print(f"❌ Ошибка получения формата продукта для заказа {order_id}: {e}")
        return 'Неизвестно'

# Функция для получения детализированного типа продукта с учетом формата книги
async def get_detailed_order_product_type(order_id: int) -> str:
    """Получает детализированный тип продукта из order_data конкретного заказа с учетом формата книги"""
    try:
        import aiosqlite
        DB_PATH = 'bookai.db'
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('''
                SELECT order_data FROM orders WHERE id = ?
            ''', (order_id,)) as cursor:
                row = await cursor.fetchone()
                if row and row[0]:
                    try:
                        order_data = json.loads(row[0])
                        product = order_data.get('product', '')
                        book_format = order_data.get('book_format', '')
                        format_field = order_data.get('format', '')
                        
                        if product == 'Книга':
                            # Проверяем формат книги (проверяем оба поля)
                            is_electronic = (
                                book_format == 'Электронная книга' or 
                                format_field == '📄 Электронная книга' or
                                'Электронная' in str(book_format) or
                                'Электронная' in str(format_field)
                            )
                            # Возвращаем детализированный тип для аналитики
                            return 'Книга электронная' if is_electronic else 'Книга печатная'
                        elif product == 'Песня':
                            return 'Песня'
                        elif product and product not in ['', 'None', 'null', 'undefined']:
                            return product
                    except json.JSONDecodeError:
                        pass
                
                # Если не найден в order_data, ищем в event_metrics для этого заказа
                async with db.execute('''
                    SELECT product_type FROM event_metrics 
                    WHERE order_id = ? AND product_type IS NOT NULL AND product_type != ''
                    ORDER BY timestamp ASC
                    LIMIT 1
                ''', (order_id,)) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0]:
                        return row[0]
                
                return 'Неизвестно'
    except Exception as e:
        print(f"❌ Ошибка получения детализированного типа продукта для заказа {order_id}: {e}")
        return 'Неизвестно'

def get_msk_now():
    """Получает текущее время в московском часовом поясе"""
    return datetime.now(MSK_TZ)

def to_msk_time(dt_str):
    """Конвертирует строку времени в московское время"""
    if not dt_str:
        return None
    try:
        # Если время уже содержит информацию о часовом поясе
        if 'T' in dt_str and ('+' in dt_str or 'Z' in dt_str):
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        else:
            # Предполагаем, что время в UTC
            dt = datetime.fromisoformat(dt_str)
            if dt.tzinfo is None:
                dt = pytz.UTC.localize(dt)
        
        # Конвертируем в московское время
        return dt.astimezone(MSK_TZ)
    except Exception as e:
        print(f"Ошибка конвертации времени {dt_str}: {e}")
        return None

def format_msk_time(dt_str, format_str="%Y-%m-%d %H:%M:%S"):
    """Форматирует время в московском часовом поясе"""
    msk_time = to_msk_time(dt_str)
    if msk_time:
        return msk_time.strftime(format_str)
    return dt_str

async def check_order_has_upsell(order_id: int) -> bool:
    """Проверяет, есть ли у заказа допродажа (событие upsell_purchased)"""
    try:
        async with db.aiosqlite.connect(db.DB_PATH) as conn:
            conn.row_factory = db.aiosqlite.Row
            async with conn.execute('''
                SELECT COUNT(*) as count 
                FROM event_metrics 
                WHERE order_id = ? AND event_type = 'upsell_purchased'
            ''', (order_id,)) as cursor:
                row = await cursor.fetchone()
                return row['count'] > 0 if row else False
    except Exception as e:
        print(f"❌ Ошибка проверки допродажи для заказа {order_id}: {e}")
        return False
from typing import List, Optional, Dict
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db
from aiogram.types import FSInputFile, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from db import get_orders_filtered, log_order_status_change, get_order_status_history, add_message_history, get_message_history, get_order_timeline, get_managers, add_manager, delete_manager, is_super_admin, get_orders_with_permissions, get_orders_filtered_with_permissions, can_access_order, get_all_photos, get_selected_photos, get_complete_photos, get_cover_templates, get_cover_template_by_id, add_cover_template, delete_cover_template, get_book_styles, add_book_style, delete_book_style, update_book_style, get_voice_styles, add_voice_style, delete_voice_style, update_voice_style, get_all_delayed_messages, get_manager_delayed_messages, can_manager_access_delayed_message, delete_delayed_message, add_delayed_message, add_delayed_message_file, get_delayed_message_files, get_pricing_items, create_pricing_item, update_pricing_item, toggle_pricing_item, delete_pricing_item, get_content_steps, create_content_step, update_content_step, toggle_content_step, delete_content_step, get_manager_by_id, get_detailed_revenue_metrics, get_manager_by_email, create_or_update_order_notification, mark_notification_as_read, get_order_notifications, get_notification_by_order_id, update_manager_super_admin_status, get_orders_count_with_permissions, assign_manager_to_order, assign_managers_to_all_orders, check_pages_sent_before, get_funnel_metrics, get_abandonment_metrics, get_revenue_metrics, get_event_metrics, get_order_pages, create_notifications_for_all_orders, get_song_quiz_list, get_song_quiz_item, get_song_quiz_by_id, create_song_quiz_item, update_song_quiz_item, delete_song_quiz_item
import asyncio
import os
import pandas as pd
from yookassa_integration import process_payment_webhook
from pydantic import BaseModel
import shutil
import uuid
from pathlib import Path

# Создаем папку для хранения файлов менеджеров
UPLOAD_DIR = Path("manager_files")
UPLOAD_DIR.mkdir(exist_ok=True)

async def save_uploaded_file(file: UploadFile, order_id: int) -> str:
    """Сохраняет загруженный файл и возвращает путь к нему"""
    # Создаем уникальное имя файла
    file_extension = Path(file.filename).suffix if file.filename else ""
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Создаем папку для заказа если её нет
    order_dir = UPLOAD_DIR / str(order_id)
    order_dir.mkdir(exist_ok=True)
    
    # Путь к файлу
    file_path = order_dir / unique_filename
    
    # Сохраняем файл
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return str(file_path)

async def compress_image_admin(image_path: str, max_size_mb: float = 5.0, quality: int = 85):
    """
    Сжимает изображение до указанного размера (для админки)
    """
    try:
        from PIL import Image
        import io
        
        # Открываем изображение
        with Image.open(image_path) as img:
            # Конвертируем в RGB если нужно
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Проверяем размер файла
            file_size = os.path.getsize(image_path) / (1024 * 1024)  # в МБ
            
            if file_size <= max_size_mb:
                print(f"📸 Файл {image_path} уже подходящего размера ({file_size:.2f} МБ)")
                return
            
            # Сжимаем изображение
            output = io.BytesIO()
            
            # Определяем формат
            if image_path.lower().endswith('.png'):
                img.save(output, format='PNG', optimize=True)
            else:
                img.save(output, format='JPEG', quality=quality, optimize=True)
            
            # Проверяем размер после сжатия
            compressed_size = len(output.getvalue()) / (1024 * 1024)  # в МБ
            
            if compressed_size <= max_size_mb:
                # Сохраняем сжатое изображение
                with open(image_path, 'wb') as f:
                    f.write(output.getvalue())
                print(f"📸 Изображение сжато: {file_size:.2f} МБ → {compressed_size:.2f} МБ")
            else:
                # Если все еще слишком большое, уменьшаем качество
                while compressed_size > max_size_mb and quality > 30:
                    quality -= 10
                    output = io.BytesIO()
                    img.save(output, format='JPEG', quality=quality, optimize=True)
                    compressed_size = len(output.getvalue()) / (1024 * 1024)
                
                if compressed_size <= max_size_mb:
                    with open(image_path, 'wb') as f:
                        f.write(output.getvalue())
                    print(f"📸 Изображение сжато с качеством {quality}: {file_size:.2f} МБ → {compressed_size:.2f} МБ")
                else:
                    print(f"⚠️ Не удалось сжать изображение {image_path} до {max_size_mb} МБ")
                    
    except ImportError:
        print("⚠️ PIL не установлен, сжатие изображений недоступно")
    except Exception as e:
        print(f"❌ Ошибка сжатия изображения {image_path}: {e}")

class Token(BaseModel):
    access_token: str
    token_type: str

class OrderOut(BaseModel):
    id: int
    user_id: int
    telegram_id: Optional[int] = None
    username: Optional[str] = None
    status: str
    order_data: str
    pdf_path: Optional[str] = None
    mp3_path: Optional[str] = None
    email: Optional[str] = None
    assigned_manager_id: Optional[int] = None
    manager_email: Optional[str] = None
    manager_name: Optional[str] = None
    created_at: str
    updated_at: str

class UploadResponse(BaseModel):
    success: bool
    detail: str

class MessageRequest(BaseModel):
    text: str

class FileMessageRequest(BaseModel):
    text: Optional[str] = None
    file_type: str  # pdf, image, video, audio, document
    comment: Optional[str] = None

class OrderEditRequest(BaseModel):
    order_data: Optional[str] = None
    pdf_path: Optional[str] = None
    mp3_path: Optional[str] = None

class StatusUpdateRequest(BaseModel):
    new_status: str

class MessageHistoryRequest(BaseModel):
    message: str
    sender: str  # 'manager' или 'user'

class ManagerOut(BaseModel):
    id: int
    email: str
    full_name: str | None = None
    is_super_admin: bool = False

class ManagerCreate(BaseModel):
    email: str
    password: str
    full_name: str
    is_super_admin: bool = False

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None

app = FastAPI()

# Словарь для отслеживания активных запросов (защита от спама)
active_requests = {}

def check_and_set_request_lock(request_key: str, timeout_seconds: int = 5) -> bool:
    """
    Проверяет, не выполняется ли уже запрос, и устанавливает блокировку
    Возвращает True, если запрос можно выполнить, False - если уже выполняется
    """
    import time
    current_time = time.time()
    
    # Очищаем устаревшие записи
    expired_keys = [key for key, timestamp in active_requests.items() 
                   if current_time - timestamp > timeout_seconds]
    for key in expired_keys:
        del active_requests[key]
    
    # Проверяем, не выполняется ли уже запрос
    if request_key in active_requests:
        return False
    
    # Устанавливаем блокировку
    active_requests[request_key] = current_time
    return True

def release_request_lock(request_key: str):
    """Освобождает блокировку запроса"""
    if request_key in active_requests:
        del active_requests[request_key]

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000", 
        "http://localhost:3001", "http://127.0.0.1:3001", 
        "http://localhost:3002", "http://127.0.0.1:3002",
        "http://localhost:3003", "http://127.0.0.1:3003",
        "https://bookai-bot.ru", "https://www.bookai-bot.ru",
        "https://admin.bookai-bot.ru", "https://api.bookai-bot.ru",
        "http://5.129.222.230:3000",
        "http://45.144.222.230:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_manager(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        print(f"🔍 ОТЛАДКА: Получен токен: {token[:20]}..." if token else "🔍 ОТЛАДКА: Токен не получен")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        print(f"🔍 ОТЛАДКА: Email из токена: {email}")
        if email is None:
            print("❌ ОТЛАДКА: Email не найден в токене")
            raise credentials_exception
    except JWTError as e:
        print(f"❌ ОТЛАДКА: Ошибка JWT: {e}")
        raise credentials_exception
    # Здесь можно добавить проверку в БД
    return email

async def get_super_admin(current_manager: str = Depends(get_current_manager)):
    """Проверяет, является ли текущий менеджер главным админом"""
    print(f"Проверяем права для менеджера: {current_manager}")
    is_admin = await is_super_admin(current_manager)
    print(f"Результат проверки: {is_admin}")
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуются права главного администратора"
        )
    return current_manager

async def get_content_editor(current_manager: str = Depends(get_current_manager)):
    """Проверяет, может ли менеджер редактировать контент (только супер-админы)"""
    print(f"Проверяем права редактирования контента для менеджера: {current_manager}")
    is_admin = await is_super_admin(current_manager)
    print(f"Результат проверки: {is_admin}")
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Только главные администраторы могут редактировать контент"
        )
    return current_manager

@app.on_event("startup")
async def startup_event():
    await db.init_db()
    await init_managers_db()

@app.post("/auth/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    print(f"Запрос на вход: {form_data.username}")
    user = await authenticate_manager(form_data.username, form_data.password)
    if not user:
        print(f"Ошибка аутентификации для: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    print(f"Успешный вход для: {form_data.username}")
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/orders", response_model=List[OrderOut])
async def get_orders(current_manager: str = Depends(get_current_manager)):
    orders = await get_orders_with_permissions(current_manager)
    return orders
@app.post("/orders/{order_id}/upload", response_model=UploadResponse)
async def upload_file_to_user(
    order_id: int,
    file: UploadFile = File(...),
    type: str = Form(...),
    comment: Optional[str] = Form(None),
    current_manager: str = Depends(get_current_manager)
):
    # Проверяем права доступа к заказу
    can_access = await can_access_order(current_manager, order_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    order = await db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    user_id = order["user_id"]
    # Сохраняем файл на диск (например, в uploads/)
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    file_ext = os.path.splitext(file.filename)[1]
    save_path = os.path.join(uploads_dir, f"order_{order_id}_{file.filename}")
    with open(save_path, "wb") as f:
        f.write(await file.read())
    # Добавляем сообщение в историю
    message_text = f"Отправлен файл: {file.filename}"
    if comment:
        message_text += f" (Комментарий: {comment})"
    await db.add_message_history(order_id, "manager", message_text)
    
    # Добавляем задание в outbox
    await db.add_outbox_task(
        order_id=order_id,
        user_id=user_id,
        type_="file",
        content=save_path,
        file_type=file_ext.lstrip("."),
        comment=comment
    )
    return {"success": True, "detail": "Файл загружен и задание создано"}

@app.post("/orders/{order_id}/send_cover", response_model=UploadResponse)
async def send_cover_to_user(
    order_id: int,
    cover_id: int = Form(...),
    current_manager: str = Depends(get_current_manager)
):
    """Отправляет обложку из библиотеки пользователю"""
    # Защита от множественных запросов
    request_key = f"send_cover_{order_id}_{cover_id}_{current_manager}"
    if not check_and_set_request_lock(request_key, timeout_seconds=5):
        raise HTTPException(status_code=429, detail="Запрос уже выполняется. Подождите немного.")
    
    try:
        # Проверяем права доступа к заказу
        can_access = await can_access_order(current_manager, order_id)
        if not can_access:
            raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
        
        order = await db.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        user_id = order["user_id"]
        
        # Получаем информацию об обложке
        cover_template = await db.get_cover_template_by_id(cover_id)
        if not cover_template:
            raise HTTPException(status_code=404, detail="Обложка не найдена")
        
        # Путь к файлу обложки
        covers_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "covers")
        file_path = os.path.join(covers_dir, cover_template['filename'])
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Файл обложки не найден")
        
        # Определяем тип файла на основе расширения
        file_extension = os.path.splitext(cover_template['filename'])[1].lower()
        if file_extension in ['.jpg', '.jpeg']:
            file_type = "jpg"
        elif file_extension == '.png':
            file_type = "png"
        elif file_extension == '.gif':
            file_type = "gif"
        else:
            file_type = "jpg"  # По умолчанию
        
        # Добавляем задание в outbox для отправки обложки
        await db.add_outbox_task(
            order_id=order_id,
            user_id=user_id,
            type_="file",
            content=file_path,
            file_type=file_type,
            comment=f"Обложка: {cover_template['name']} ({cover_template.get('category', 'Без категории')})"
        )
        
        return {"success": True, "detail": f"Обложка '{cover_template['name']}' отправлена пользователю"}
    finally:
        # Освобождаем блокировку
        release_request_lock(request_key)

@app.post("/orders/{order_id}/send_all_covers", response_model=UploadResponse)
async def send_all_covers_to_user(
    order_id: int,
    current_manager: str = Depends(get_current_manager)
):
    """Отправляет все обложки пользователю одним сообщением с кнопками выбора"""
    # Защита от множественных запросов
    request_key = f"send_all_covers_{order_id}_{current_manager}"
    if not check_and_set_request_lock(request_key, timeout_seconds=10):
        raise HTTPException(status_code=429, detail="Запрос уже выполняется. Подождите немного.")
    
    try:
        # Проверяем права доступа к заказу
        can_access = await can_access_order(current_manager, order_id)
        if not can_access:
            raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
        
        order = await db.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        user_id = order["user_id"]
        
        # Получаем все обложки
        cover_templates = await db.get_cover_templates()
        if not cover_templates:
            raise HTTPException(status_code=404, detail="Нет доступных обложек")
        
        # Добавляем задание в outbox для отправки всех обложек
        await db.add_outbox_task(
            order_id=order_id,
            user_id=user_id,
            type_="covers_selection",
            content="",  # Пустой контент, так как обложки будут загружены в боте
            file_type="covers",
            comment="Выберите обложку для вашей книги"
        )
        
        return {"success": True, "detail": f"Отправлено {len(cover_templates)} обложек для выбора"}
    finally:
        # Освобождаем блокировку
        release_request_lock(request_key)

@app.post("/orders/{order_id}/message", response_model=UploadResponse)
async def send_message_to_user(
    order_id: int,
    req: MessageRequest,
    current_manager: str = Depends(get_current_manager)
):
    # Проверяем права доступа к заказу
    can_access = await can_access_order(current_manager, order_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    order = await db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    user_id = order["user_id"]
    
    # Валидация user_id
    if not user_id or user_id <= 0:
        raise HTTPException(status_code=400, detail="Некорректный user_id в заказе")
    
    # Проверяем, что пользователь взаимодействовал с ботом
    if user_id in [12345, 0, -1]:  # Тестовые/некорректные ID
        raise HTTPException(status_code=400, detail="Некорректный user_id пользователя")
    
    # Определяем тип сообщения на основе содержимого
    message_type = "text"
    
    # Проверяем, является ли это сюжетами для Главы 11
    if any(char.isdigit() for char in req.text) and ("страница" in req.text.lower() or "сюжет" in req.text.lower()):
        # Это сюжеты для Главы 11
        message_type = "stories"
        
        # Добавляем сообщение в историю
        await db.add_message_history(order_id, "manager", f"Отправлены сюжеты: {req.text[:100]}...")
        
        # Обновляем статус заказа
        await db.update_order_status(order_id, "stories_sent")
    else:
        # Обычное текстовое сообщение от менеджера
        await db.add_message_history(order_id, "manager", req.text)
    
    await db.add_outbox_task(
        order_id=order_id,
        user_id=user_id,
        type_=message_type,
        content=req.text,
        is_general_message=True  # Помечаем как общее сообщение
    )
    return {"success": True, "detail": "Сообщение добавлено в очередь на отправку"}
@app.post("/orders/{order_id}/file", response_model=UploadResponse)
async def send_file_to_user(
    order_id: int,
    file: UploadFile = File(...),
    text: Optional[str] = Form(None),
    comment: Optional[str] = Form(None),
    current_manager: str = Depends(get_current_manager)
):
    """Отправляет файл пользователю"""
    print(f"🔍 ФАЙЛ API: Получен запрос для заказа {order_id}, файл: {file.filename}, текст: {text}")
    # Проверяем права доступа к заказу
    can_access = await can_access_order(current_manager, order_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    order = await db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    user_id = order["user_id"]
    
    # Валидация user_id
    if not user_id or user_id <= 0:
        raise HTTPException(status_code=400, detail="Некорректный user_id в заказе")
    
    # Проверяем, что пользователь взаимодействовал с ботом
    if user_id in [12345, 0, -1]:  # Тестовые/некорректные ID
        raise HTTPException(status_code=400, detail="Некорректный user_id пользователя")
    
    # Определяем тип файла
    file_extension = Path(file.filename).suffix.lower() if file.filename else ""
    file_type = "document"  # по умолчанию
    
    if file_extension in ['.pdf']:
        file_type = "pdf"
    elif file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
        file_type = "image"
    elif file_extension in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
        file_type = "video"
    elif file_extension in ['.mp3', '.wav', '.ogg', '.m4a', '.aac']:
        file_type = "audio"
    
    try:
        # Сохраняем файл
        file_path = await save_uploaded_file(file, order_id)
        
        # Сжимаем изображения только для рабочих файлов, не для общих сообщений
        # Общие сообщения должны отправляться в оригинальном качестве
        if file_type == "image":
            # Пропускаем сжатие для общих сообщений - они должны быть в оригинальном качестве
            pass
        
        # Формируем сообщение для истории
        message_text = f"Отправлен файл: {file.filename}"
        if text:
            message_text += f"\n\n{text}"
        if comment:
            message_text += f"\n\nКомментарий: {comment}"
        
        # Добавляем сообщение в историю
        await db.add_message_history(order_id, "manager", message_text)
        
        # Добавляем задачу в очередь на отправку
        await db.add_outbox_task(
            order_id=order_id,
            user_id=user_id,
            type_="file",
            content=file_path,
            file_type=file_type,
            comment=text or comment,  # Используем text как основной комментарий
            is_general_message=True  # Помечаем как общее сообщение
        )
        
        return {"success": True, "detail": f"Файл {file.filename} добавлен в очередь на отправку"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при сохранении файла: {str(e)}")

@app.get("/admin/orders", response_model=List[OrderOut])
async def get_admin_orders(
    current_manager: str = Depends(get_current_manager),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100)
):
    from fastapi.responses import JSONResponse
    
    # Получаем заказы и общее количество
    orders = await get_orders_with_permissions(current_manager, page=page, limit=limit)
    total_count = await get_orders_count_with_permissions(current_manager)
    
    # Возвращаем ответ с заголовком
    response = JSONResponse(content=orders)
    response.headers["X-Total-Count"] = str(total_count)
    return response

@app.get("/admin/orders/{order_id}", response_model=OrderOut)
async def get_admin_order_details(order_id: int, current_manager: str = Depends(get_current_manager)):
    # Проверяем права доступа к заказу
    can_access = await can_access_order(current_manager, order_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    order = await db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/orders/filtered", response_model=List[OrderOut])
async def get_orders_filtered_api(
    status: Optional[str] = Query(None),
    order_type: Optional[str] = Query(None),
    telegram_id: Optional[str] = Query(None),
    order_id: Optional[int] = Query(None),
    sort_by: str = Query('created_at'),
    sort_dir: str = Query('desc'),
    current_manager: str = Depends(get_current_manager)
):
    return await get_orders_filtered_with_permissions(
        current_manager, status, order_type, telegram_id, order_id, sort_by, sort_dir
    )

@app.patch("/admin/orders/{order_id}", response_model=OrderOut)
async def edit_order(order_id: int, req: OrderEditRequest, current_manager: str = Depends(get_current_manager)):
    # Проверяем права доступа к заказу
    can_access = await can_access_order(current_manager, order_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    order = await db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    update_fields = {}
    if req.order_data is not None:
        update_fields['order_data'] = req.order_data
    if req.pdf_path is not None:
        update_fields['pdf_path'] = req.pdf_path
    if req.mp3_path is not None:
        update_fields['mp3_path'] = req.mp3_path
    if update_fields:
        set_clause = ', '.join([f"{k} = ?" for k in update_fields.keys()])
        values = list(update_fields.values()) + [order_id]
        async with db.aiosqlite.connect(db.DB_PATH) as dbconn:
            await dbconn.execute(f"UPDATE orders SET {set_clause}, updated_at = ? WHERE id = ?", values + [get_msk_now().strftime('%Y-%m-%d %H:%M:%S')])
            await dbconn.commit()
    return await db.get_order(order_id)

@app.post("/admin/orders/{order_id}/status", response_model=dict)
async def update_order_status(order_id: int, req: StatusUpdateRequest, current_manager: str = Depends(get_current_manager)):
    # Проверяем права доступа к заказу
    can_access = await can_access_order(current_manager, order_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    order = await db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    old_status = order['status']
    await db.update_order_status(order_id, req.new_status)
    await log_order_status_change(order_id, old_status, req.new_status)
    return {"success": True, "old_status": old_status, "new_status": req.new_status}

@app.get("/admin/orders/{order_id}/status_history", response_model=List[dict])
async def get_status_history(order_id: int, current_manager: str = Depends(get_current_manager)):
    # Проверяем права доступа к заказу
    can_access = await can_access_order(current_manager, order_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    return await get_order_status_history(order_id)

@app.post("/admin/orders/{order_id}/message_history", response_model=dict)
async def add_message_to_history(order_id: int, req: MessageHistoryRequest, current_manager: str = Depends(get_current_manager)):
    # Проверяем права доступа к заказу
    can_access = await can_access_order(current_manager, order_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    await add_message_history(order_id, req.sender, req.message)
    return {"success": True}

@app.get("/admin/orders/{order_id}/message_history", response_model=List[dict])
async def get_messages_history(order_id: int, current_manager: str = Depends(get_current_manager)):
    # Проверяем права доступа к заказу
    can_access = await can_access_order(current_manager, order_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    return await get_message_history(order_id)

@app.get("/admin/orders/{order_id}/timeline", response_model=dict)
async def get_order_timeline_api(order_id: int, current_manager: str = Depends(get_current_manager)):
    # Проверяем права доступа к заказу
    can_access = await can_access_order(current_manager, order_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    return await get_order_timeline(order_id)

@app.get("/photo/{filename:path}")
async def get_photo(filename: str):
    # Используем абсолютный путь к папке uploads
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    uploads_dir = os.path.join(project_root, "uploads")
    file_path = os.path.join(uploads_dir, filename)
    print(f"Запрос файла: {filename}")
    print(f"Полный путь: {file_path}")
    print(f"Файл существует: {os.path.exists(file_path)}")
    
    if os.path.exists(file_path):
        return FileResponse(file_path)
    
    # Если файл не найден, возможно это Telegram file_id
    # Попробуем скачать его из Telegram
    try:
        # Импортируем бота для скачивания файлов
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from bot import bot
        
        # Скачиваем файл из Telegram
        file_info = await bot.get_file(filename)
        downloaded_file = await bot.download_file(file_info.file_path)
        
        # Сохраняем файл в папку uploads
        os.makedirs(uploads_dir, exist_ok=True)
        save_path = os.path.join(uploads_dir, filename)
        
        with open(save_path, 'wb') as f:
            f.write(downloaded_file)
        
        print(f"Файл скачан из Telegram и сохранен: {save_path}")
        return FileResponse(save_path)
        
    except Exception as e:
        print(f"Ошибка скачивания файла из Telegram: {e}")
        return {"detail": "Not Found"}

@app.get("/covers/{filename}")
async def get_cover(filename: str):
    # Используем абсолютный путь к папке covers
    covers_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "covers")
    file_path = os.path.join(covers_dir, filename)
    
    if os.path.exists(file_path):
        return FileResponse(file_path)
    
    raise HTTPException(status_code=404, detail="Обложка не найдена")

@app.get("/styles/{filename}")
async def get_style(filename: str):
    # Используем абсолютный путь к папке styles
    styles_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "styles")
    file_path = os.path.join(styles_dir, filename)
    
    if os.path.exists(file_path):
        return FileResponse(file_path)
    
    raise HTTPException(status_code=404, detail="Стиль не найден")

@app.get("/voices/{filename}")
async def get_voice(filename: str):
    # Используем абсолютный путь к папке voices
    voices_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "voices")
    file_path = os.path.join(voices_dir, filename)
    
    if os.path.exists(file_path):
        return FileResponse(file_path)
    
    raise HTTPException(status_code=404, detail="Голос не найден")

@app.post("/admin/orders/{order_id}/upload_file", response_model=UploadResponse)
async def upload_file_to_order(
    order_id: int,
    file: UploadFile = File(...),  # Убираем max_length, так как он не работает с UploadFile
    type: Optional[str] = Form(None),
    comment: Optional[str] = Form(None),
    current_manager: str = Depends(get_current_manager)
):
    # Проверяем права доступа к заказу
    can_access = await can_access_order(current_manager, order_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    # Проверка размера файла (100MB лимит)
    file_content = await file.read()
    file_size = len(file_content)
    max_size = 100 * 1024 * 1024  # 100MB
    
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой: {file_size / (1024*1024):.1f}MB. Максимальный размер: 100MB"
        )
    
    # Валидация типа файла
    allowed_types = [
        # Изображения
        'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/tiff', 'image/svg+xml',
        # Видео
        'video/mp4', 'video/mov', 'video/avi', 'video/mkv', 'video/flv', 'video/wmv', 
        'video/m4v', 'video/3gp', 'video/ogv', 'video/webm', 'video/quicktime',
        # Аудио
        'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4', 'audio/m4a', 'audio/wma', 
        'audio/aac', 'audio/flac', 'audio/opus', 'audio/amr', 'audio/midi', 'audio/mid',
        'audio/xmf', 'audio/rtttl', 'audio/smf', 'audio/imy', 'audio/rtx', 'audio/ota',
        'audio/jad', 'audio/jar',
        # Документы
        'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain', 'text/html', 'text/css', 'text/javascript', 'application/json',
        'application/xml', 'text/xml'
    ]
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Неподдерживаемый тип файла: {file.content_type}. Поддерживаемые типы: изображения, видео, аудио, документы"
        )
    
    """Загружает файл для заказа (только для менеджеров)"""
    order = await db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    user_id = order["user_id"]
    
    # Логируем информацию о загрузке
    print(f"🔍 ОТЛАДКА: Загружаем файл для заказа {order_id}")
    print(f"📄 Имя файла: {file.filename}")
    print(f"🔖 Тип из формы: {type}")
    print(f"💬 Комментарий: {comment}")
    print(f"📋 Статус заказа: {order.get('status', 'unknown')}")
    
    # Сохраняем файл на диск
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    file_ext = os.path.splitext(file.filename)[1]
    save_path = os.path.join(uploads_dir, f"order_{order_id}_{file.filename}")
    
    with open(save_path, "wb") as f:
        f.write(file_content)
    
    print(f"💾 Файл сохранен: {save_path}")
    print(f"📦 Расширение файла: {file_ext}")
    
    # Добавляем сообщение в историю
    message_text = f"Отправлен файл: {file.filename}"
    if comment:
        message_text += f" (Комментарий: {comment})"
    await db.add_message_history(order_id, "manager", message_text)
    
    # Добавляем задание в outbox
    await db.add_outbox_task(
        order_id=order_id,
        user_id=user_id,
        type_="file",
        content=save_path,
        file_type=file_ext.lstrip("."),
        comment=comment
    )
    
    # Для MP3 файлов (песни) не обновляем статус - оставляем текущий
    if file_ext.lower() == '.mp3':
        print(f"🔘 MP3 файл загружен для заказа {order_id} (upload_file), статус не изменяется")
    
    print(f"✅ Задание добавлено в outbox для заказа {order_id}")
    
    return {"success": True, "detail": "Файл загружен и задание создано"}

@app.post("/admin/orders/{order_id}/send_multiple_images_with_button", response_model=UploadResponse)
async def send_multiple_files_with_text_and_button(
    order_id: int,
    files: List[UploadFile] = File(...),
    text: str = Form(...),
    button_text: str = Form(...),
    button_callback: str = Form(...),
    current_manager: str = Depends(get_current_manager)
):
    try:
        print(f"🔍 ОТЛАДКА: Получен запрос на отправку демо-контента для заказа {order_id}")
        print(f"🔍 ОТЛАДКА: Количество файлов: {len(files)}")
        print(f"🔍 ОТЛАДКА: Текст: {text}")
        print(f"🔍 ОТЛАДКА: Кнопка: {button_text}")
        print(f"🔍 ОТЛАДКА: Callback: {button_callback}")
        
        # Проверяем права доступа к заказу
        can_access = await can_access_order(current_manager, order_id)
        if not can_access:
            print(f"❌ ОТЛАДКА: Доступ запрещен для менеджера {current_manager}")
            raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
        
        if not files:
            print(f"❌ ОТЛАДКА: Не выбрано файлов")
            raise HTTPException(status_code=400, detail="Не выбрано файлов")
        
        order = await db.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Проверяем статус заказа - демо-контент можно отправлять только в определенных статусах
        current_status = order.get("status")
        allowed_statuses = ["waiting_manager", "demo_content", "questions_completed"]
        
        if current_status not in allowed_statuses:
            print(f"⚠️ ОТЛАДКА: Неподходящий статус для отправки демо-контента: {current_status}")
            raise HTTPException(
                status_code=400, 
                detail=f"Демо-контент можно отправлять только в статусах: {', '.join(allowed_statuses)}. Текущий статус: {current_status}"
            )
        
        # Разрешаем повторную отправку демо-контента
        print(f"✅ ОТЛАДКА: Разрешена отправка демо-контента для заказа {order_id} (повторная отправка разрешена)")
        
        user_id = order["user_id"]
        
        # Дополнительная проверка user_id
        print(f"🔍 ОТЛАДКА: user_id из заказа: {user_id}")
        if not user_id or user_id <= 0 or user_id in [12345, 0, -1]:
            print(f"❌ ОТЛАДКА: Некорректный user_id: {user_id}")
            raise HTTPException(status_code=400, detail=f"Некорректный user_id в заказе: {user_id}")
        
        uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Сохраняем все файлы
        saved_files = []
        for file in files:
            # Проверка размера файла (100MB лимит)
            file_content = await file.read()
            file_size = len(file_content)
            max_size = 100 * 1024 * 1024  # 100MB
            
            if file_size > max_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"Файл {file.filename} слишком большой: {file_size / (1024*1024):.1f}MB. Максимальный размер: 100MB"
                )
            
            # Валидация типа файла
            allowed_types = [
                'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/tiff', 'image/svg+xml',
                'video/mp4', 'video/mov', 'video/avi', 'video/mkv', 'video/flv', 'video/wmv', 
                'video/m4v', 'video/3gp', 'video/ogv', 'video/webm', 'video/quicktime',
                'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4', 'audio/m4a', 'audio/wma', 
                'audio/aac', 'audio/flac', 'audio/opus', 'audio/amr', 'audio/midi', 'audio/mid',
                'audio/xmf', 'audio/rtttl', 'audio/smf', 'audio/imy', 'audio/rtx', 'audio/ota',
                'audio/jad', 'audio/jar',
                'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'text/plain', 'text/html', 'text/css', 'text/javascript', 'application/json',
                'application/xml', 'text/xml'
            ]
            
            file_ext = os.path.splitext(file.filename)[1].lower()
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.svg',
                                 '.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v', '.3gp', '.ogv', '.webm',
                                 '.mp3', '.wav', '.ogg', '.m4a', '.wma', '.aac', '.flac', '.opus', '.amr', '.midi', '.mid',
                                 '.pdf', '.doc', '.docx', '.txt', '.html', '.css', '.js', '.json', '.xml']
            
            if file.content_type not in allowed_types and file_ext not in allowed_extensions:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Неподдерживаемый тип файла {file.filename}: {file.content_type}"
                )
            
            save_path = os.path.join(uploads_dir, f"order_{order_id}_{file.filename}")
            with open(save_path, "wb") as f:
                f.write(file_content)
            
            # Определяем тип файла для демо-контента
            file_type = "demo_photo"
            if file.content_type.startswith("audio/"):
                file_type = "demo_audio"
            elif file.content_type.startswith("video/"):
                file_type = "demo_video"
            elif file.content_type == "application/pdf":
                file_type = "demo_pdf"
            
            # Сохраняем информацию о файле в базу данных
            await db.add_upload(order_id, file.filename, file_type)
            
            saved_files.append(save_path)
    
        print(f"🔍 ОТЛАДКА: Сохранено файлов: {len(saved_files)}")
        print(f"🔍 ОТЛАДКА: Пути файлов: {saved_files}")
        
        # Добавляем задание в outbox для отправки всех файлов одним сообщением
        await db.add_outbox_task(
            order_id=order_id,
            user_id=user_id,
            type_="multiple_images_with_text_and_button",
            content=json.dumps(saved_files),  # Сохраняем список файлов как JSON
            file_type="multiple",
            comment=text,
            button_text=button_text,
            button_callback=button_callback
        )
        
        print(f"✅ ОТЛАДКА: Задание добавлено в outbox для пользователя {user_id}")
        
        return {"success": True, "detail": f"Демо-контент отправлен ({len(saved_files)} файлов)"}
        
    except Exception as e:
        print(f"❌ ОТЛАДКА: Ошибка в send_multiple_files_with_text_and_button: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")

@app.post("/admin/orders/{order_id}/send_pages_for_selection", response_model=UploadResponse)
async def send_pages_for_selection(
    order_id: int,
    files: List[UploadFile] = File(...),
    text: str = Form(...),
    current_manager: str = Depends(get_current_manager)
):
    """Отправляет страницы для выбора пользователем (каждую отдельно с кнопкой)"""
    # Проверяем права доступа к заказу
    can_access = await can_access_order(current_manager, order_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    if not files:
        raise HTTPException(status_code=400, detail="Не выбрано файлов")
    
    order = await db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    user_id = order['user_id']
    uploads_dir = "uploads"
    os.makedirs(uploads_dir, exist_ok=True)
    
    saved_files = []
    for file in files:
        file_content = await file.read()
        
        # Проверка типов файлов (копируем из оригинальной функции)
        allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/tiff', 'image/svg+xml',
            'video/mp4', 'video/mov', 'video/avi', 'video/mkv', 'video/flv', 'video/wmv', 
            'video/m4v', 'video/3gp', 'video/ogv', 'video/webm', 'video/quicktime',
            'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4', 'audio/m4a', 'audio/wma', 
            'audio/aac', 'audio/flac', 'audio/opus', 'audio/amr', 'audio/midi', 'audio/mid',
            'audio/xmf', 'audio/rtttl', 'audio/smf', 'audio/imy', 'audio/rtx', 'audio/ota',
            'audio/jad', 'audio/jar',
            'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain', 'text/html', 'text/css', 'text/javascript', 'application/json',
            'application/xml', 'text/xml'
        ]
        
        file_ext = os.path.splitext(file.filename)[1].lower()
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.svg',
                             '.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v', '.3gp', '.ogv', '.webm',
                             '.mp3', '.wav', '.ogg', '.m4a', '.wma', '.aac', '.flac', '.opus', '.amr', '.midi', '.mid',
                             '.pdf', '.doc', '.docx', '.txt', '.html', '.css', '.js', '.json', '.xml']
        
        if file.content_type not in allowed_types and file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Неподдерживаемый тип файла {file.filename}: {file.content_type}"
            )
        
        save_path = os.path.join(uploads_dir, f"order_{order_id}_{file.filename}")
        with open(save_path, "wb") as f:
            f.write(file_content)
        
        saved_files.append(save_path)
    
    # Убираем лишнюю инструкцию - она не нужна
    
    # Добавляем задания для отправки каждого файла отдельно с кнопкой выбора
    # Используем правильную нумерацию страниц из базы данных
    from db import get_next_page_number, save_page_number
    
    for i, file_path in enumerate(saved_files):
        # Получаем следующий номер страницы из базы данных
        page_number = await get_next_page_number(order_id)
        
        # Сохраняем информацию о странице в базу данных
        filename = os.path.basename(file_path)
        await save_page_number(order_id, page_number, filename, f"Страница {page_number}")
        
        await db.add_outbox_task(
            order_id=order_id,
            user_id=user_id,
            type_="page_selection",
            content=file_path,
            file_type="image",
            comment=f"Страница {page_number}",
            button_text="✅ Выбрать",
            button_callback=f"choose_page_{page_number}"
        )
    
    return {"success": True, "detail": f"Загружено {len(files)} страниц для выбора"}

@app.post("/admin/orders/{order_id}/send_image_with_button", response_model=UploadResponse)
async def send_file_with_text_and_button(
    order_id: int,
    file: UploadFile = File(...),  # Убираем max_length, так как он не работает с UploadFile
    text: str = Form(...),
    button_text: str = Form(...),
    button_callback: str = Form(...),
    current_manager: str = Depends(get_current_manager)
):
    # Проверяем права доступа к заказу
    can_access = await can_access_order(current_manager, order_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    # Проверка размера файла (100MB лимит)
    file_content = await file.read()
    file_size = len(file_content)
    max_size = 100 * 1024 * 1024  # 100MB
    
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой: {file_size / (1024*1024):.1f}MB. Максимальный размер: 100MB"
        )
    
    # Логирование для диагностики
    print(f"🔍 ДИАГНОСТИКА ФАЙЛА:")
    print(f"   Имя файла: {file.filename}")
    print(f"   Content-Type: {file.content_type}")
    print(f"   Размер: {file_size / (1024*1024):.1f}MB")
    
    # Валидация типа файла
    allowed_types = [
        # Изображения
        'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/tiff', 'image/svg+xml',
        # Видео
        'video/mp4', 'video/mov', 'video/avi', 'video/mkv', 'video/flv', 'video/wmv', 
        'video/m4v', 'video/3gp', 'video/ogv', 'video/webm', 'video/quicktime',
        # Аудио
        'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4', 'audio/m4a', 'audio/wma', 
        'audio/aac', 'audio/flac', 'audio/opus', 'audio/amr', 'audio/midi', 'audio/mid',
        'audio/xmf', 'audio/rtttl', 'audio/smf', 'audio/imy', 'audio/rtx', 'audio/ota',
        'audio/jad', 'audio/jar',
        # Документы
        'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain', 'text/html', 'text/css', 'text/javascript', 'application/json',
        'application/xml', 'text/xml'
    ]
    
    # Проверяем расширение файла как fallback
    file_ext = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.svg',
                         '.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v', '.3gp', '.ogv', '.webm',
                         '.mp3', '.wav', '.ogg', '.m4a', '.wma', '.aac', '.flac', '.opus', '.amr', '.midi', '.mid',
                         '.pdf', '.doc', '.docx', '.txt', '.html', '.css', '.js', '.json', '.xml']
    
    if file.content_type not in allowed_types and file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Неподдерживаемый тип файла: {file.content_type} (расширение: {file_ext}). Поддерживаемые типы: изображения, видео, аудио, документы"
        )
    
    print(f"   ✅ Файл прошел валидацию")
    
    """Отправляет файл с текстом и кнопкой пользователю (только для менеджеров)"""
    order = await db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    user_id = order["user_id"]
    # Сохраняем файл на диск
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    file_ext = os.path.splitext(file.filename)[1]
    save_path = os.path.join(uploads_dir, f"order_{order_id}_{file.filename}")
    
    with open(save_path, "wb") as f:
        f.write(file_content)
    
    # Сжимаем фотографию, если это изображение
    try:
        if file.content_type.startswith('image/'):
            await compress_image_admin(save_path)
            print(f"✅ Фотография сжата: {file.filename}")
    except Exception as e:
        print(f"❌ Ошибка сжатия фотографии {file.filename}: {e}")
    
    # Добавляем сообщение в историю
    message_text = f"Отправлен файл с кнопкой: {file.filename}"
    if text:
        message_text += f" (Текст: {text})"
    await db.add_message_history(order_id, "manager", message_text)
    
    # Добавляем задание в outbox
    await db.add_outbox_task(
        order_id=order_id,
        user_id=user_id,
        type_="image_with_text_and_button",
        content=save_path,
        file_type=file_ext.lstrip("."),
        comment=text,
        button_text=button_text,
        button_callback=button_callback
    )
    
    # Обновляем статус заказа в зависимости от типа файла и продукта
    order_data = json.loads(order.get('order_data', '{}'))
    product = order_data.get('product', '')
    
    if file_ext.lower() == '.mp3' and product == 'Песня':
        print(f"🔘 MP3 файл загружен для заказа {order_id}, статус не изменяется")
    elif product == 'Книга' and button_callback in ['book_draft_ok', 'book_draft_edit']:
        # Для черновика книги обновляем статус
        await db.update_order_status(order_id, "draft_sent")
        print(f"📖 Черновик книги отправлен для заказа {order_id}, статус обновлен на 'draft_sent'")
    
    return {"success": True, "detail": "Файл с текстом и кнопкой добавлен в очередь"}

@app.get("/admin/orders/{order_id}/delivery_address", response_model=dict)
async def get_delivery_address(
    order_id: int,
    current_manager: str = Depends(get_current_manager)
):
    # Проверяем права доступа к заказу
    can_access = await can_access_order(current_manager, order_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    from db import get_delivery_address
    address = await get_delivery_address(order_id)
    if not address:
        raise HTTPException(status_code=404, detail="Delivery address not found")
    return address

@app.post("/admin/orders/{order_id}/continue_creation", response_model=dict)
async def continue_book_creation(
    order_id: int,
    current_manager: str = Depends(get_current_manager)
):
    """Продолжает создание книги, переводит к главе 9 (оплата)"""
    # Проверяем права доступа к заказу
    can_access = await can_access_order(current_manager, order_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    try:
        # Обновляем статус заказа на "waiting_payment" (ожидание оплаты)
        await db.update_order_status(order_id, "waiting_payment")
        
        # Логируем изменение статуса
        await log_order_status_change(order_id, "demo_content", "waiting_payment")
        
        return {
            "success": True, 
            "detail": "Создание книги продолжено. Заказ переведен к оплате (глава 9)",
            "new_status": "waiting_payment"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка продолжения создания книги: {str(e)}")
# --- API для работы с менеджерами ---

@app.get("/admin/managers", response_model=List[ManagerOut])
async def get_managers_list(current_manager: str = Depends(get_super_admin)):
    """Получает список всех менеджеров (только для главного админа)"""
    return await get_managers()

@app.post("/admin/managers", response_model=ManagerOut)
async def create_manager_endpoint(
    manager: ManagerCreate,
    current_manager: str = Depends(get_super_admin)
):
    """Создает нового менеджера (только для главного админа)"""
    try:
        manager_id = await add_manager(manager.email, manager.password, manager.full_name, manager.is_super_admin)
        # Получаем созданного менеджера
        managers = await get_managers()
        created_manager = next((m for m in managers if m['id'] == manager_id), None)
        if created_manager:
            return created_manager
        else:
            raise HTTPException(status_code=500, detail="Ошибка создания менеджера")
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(status_code=400, detail="Менеджер с таким email уже существует")
        raise HTTPException(status_code=500, detail=f"Ошибка создания менеджера: {str(e)}")

@app.post("/admin/managers/upload", response_model=dict)
async def upload_managers_file(
    file: UploadFile = File(...),
    current_manager: str = Depends(get_super_admin)
):
    """Загружает менеджеров из Excel файла (только для главного админа)"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Файл должен быть Excel (.xlsx или .xls)")
    
    try:
        # Читаем Excel файл
        contents = await file.read()
        import io
        df = pd.read_excel(io.BytesIO(contents))
        
        # Проверяем наличие необходимых колонок
        required_columns = ['Email', 'Пароль', 'ФИО']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"В файле отсутствуют колонки: {', '.join(missing_columns)}"
            )
        
        # Обрабатываем каждую строку
        added_count = 0
        errors = []
        
        print(f"Начинаем обработку файла с {len(df)} строками")
        
        for index, row in df.iterrows():
            try:
                email = str(row['Email']).strip()
                password = str(row['Пароль']).strip()
                full_name = str(row['ФИО']).strip()
                
                print(f"Обрабатываем строку {index + 1}: email={email}, password={password}, full_name={full_name}")
                
                # Проверяем, что все поля заполнены
                if not email or not password or not full_name:
                    error_msg = f"Строка {index + 1}: Не все поля заполнены (email='{email}', password='{password}', full_name='{full_name}')"
                    errors.append(error_msg)
                    print(error_msg)
                    continue
                
                # Проверяем формат email (более мягкая проверка)
                if '@' not in email or len(email.split('@')[0]) < 1:
                    error_msg = f"Строка {index + 1}: Неверный формат email '{email}'"
                    errors.append(error_msg)
                    print(error_msg)
                    continue
                
                # Добавляем менеджера
                print(f"Добавляем менеджера: {email}")
                await add_manager(email, password, full_name)
                added_count += 1
                print(f"Менеджер {email} успешно добавлен")
                
            except Exception as e:
                error_msg = f"Строка {index + 1}: {str(e)}"
                errors.append(error_msg)
                print(error_msg)
        
        result = {
            "success": True,
            "added_count": added_count,
            "errors": errors,
            "message": f"Успешно добавлено {added_count} менеджеров"
        }
        
        print(f"Результат обработки: {result}")
        return result
        
    except Exception as e:
        print(f"Ошибка обработки файла: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка обработки файла: {str(e)}")

@app.delete("/admin/managers/{manager_id}", response_model=dict)
async def delete_manager_endpoint(
    manager_id: int,
    current_manager: str = Depends(get_super_admin)
):
    """Удаляет менеджера по ID (только для главного админа)"""
    success = await delete_manager(manager_id)
    if not success:
        raise HTTPException(status_code=404, detail="Менеджер не найден")
    
    return {"success": True, "message": "Менеджер успешно удален"}

@app.put("/admin/managers/{manager_id}", response_model=ManagerOut)
async def update_manager_endpoint(
    manager_id: int,
    manager_update: dict,
    current_manager: str = Depends(get_super_admin)
):
    """Обновляет менеджера по ID (только для главного админа)"""
    try:
        # Проверяем, что менеджер существует
        existing_manager = await db.get_manager_by_id(manager_id)
        if not existing_manager:
            raise HTTPException(status_code=404, detail="Менеджер не найден")
        
        # Обновляем данные
        success = await db.update_manager_profile(
            manager_id,
            full_name=manager_update.get("full_name"),
            new_password=None  # Не позволяем менять пароль через этот endpoint
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Ошибка обновления менеджера")
        
        # Обновляем статус супер-админа
        if "is_super_admin" in manager_update:
            await db.update_manager_super_admin_status(manager_id, manager_update["is_super_admin"])
        
        # Получаем обновленного менеджера
        updated_manager = await db.get_manager_by_id(manager_id)
        return ManagerOut(
            id=updated_manager["id"],
            email=updated_manager["email"],
            full_name=updated_manager["full_name"],
            is_super_admin=updated_manager["is_super_admin"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обновления менеджера: {str(e)}")

# --- Профиль менеджера ---

@app.get("/admin/profile", response_model=ManagerOut)
async def get_manager_profile(current_manager: str = Depends(get_current_manager)):
    """Получает профиль текущего менеджера"""
    try:
        manager = await db.get_manager_by_email(current_manager)
        if not manager:
            raise HTTPException(status_code=404, detail="Менеджер не найден")
        
        return ManagerOut(
            id=manager["id"],
            email=manager["email"],
            full_name=manager["full_name"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения профиля: {str(e)}")

@app.get("/admin/profile/permissions", response_model=dict)
async def get_manager_permissions(current_manager: str = Depends(get_current_manager)):
    """Получает права доступа текущего менеджера"""
    try:
        manager = await db.get_manager_by_email(current_manager)
        if not manager:
            raise HTTPException(status_code=404, detail="Менеджер не найден")
        
        return {
            "is_super_admin": bool(manager.get("is_super_admin", False)),
            "email": manager["email"],
            "full_name": manager["full_name"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения прав доступа: {str(e)}")

@app.put("/admin/profile", response_model=ManagerOut)
async def update_manager_profile(
    profile_update: ProfileUpdate,
    current_manager: str = Depends(get_current_manager)
):
    """Обновляет профиль текущего менеджера"""
    try:
        # Получаем текущего менеджера
        manager = await db.get_manager_by_email(current_manager)
        if not manager:
            raise HTTPException(status_code=404, detail="Менеджер не найден")
        
        # Если меняем пароль, проверяем текущий
        if profile_update.new_password:
            if not profile_update.current_password:
                raise HTTPException(status_code=400, detail="Текущий пароль обязателен для смены пароля")
            
            # Проверяем текущий пароль
            from admin_backend.users import verify_password
            if not verify_password(profile_update.current_password, manager["hashed_password"]):
                raise HTTPException(status_code=400, detail="Неверный текущий пароль")
        
        # Обновляем данные
        await db.update_manager_profile(
            manager["id"],
            full_name=profile_update.full_name,
            new_password=profile_update.new_password
        )
        
        # Получаем обновленный профиль
        updated_manager = await db.get_manager_by_email(current_manager)
        return ManagerOut(
            id=updated_manager["id"],
            email=updated_manager["email"],
            full_name=updated_manager["full_name"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обновления профиля: {str(e)}")

@app.get("/admin/profile/orders", response_model=List[OrderOut])
async def get_manager_orders(current_manager: str = Depends(get_current_manager)):
    """Получает заказы текущего менеджера"""
    try:
        # Получаем ID менеджера
        manager = await db.get_manager_by_email(current_manager)
        if not manager:
            raise HTTPException(status_code=404, detail="Менеджер не найден")
        
        # Получаем заказы менеджера
        orders = await db.get_manager_orders(manager["id"])
        return orders
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения заказов: {str(e)}")

# --- API для фотографий ---

class PhotoOut(BaseModel):
    id: int
    order_id: int
    filename: str
    type: str
    created_at: str
    path: str
@app.get("/admin/photos", response_model=List[PhotoOut])
async def get_photos(current_manager: str = Depends(get_current_manager)):
    """Получает фотографии заказов"""
    try:
        print("🔍 Загружаем фотографии...")
        # Сначала попробуем простую загрузку из таблицы order_photos
        photos = await db.get_all_photos()
        print(f"✅ Успешно загружено {len(photos)} фотографий из таблицы order_photos")
        
        # Если таблица пуста, попробуем комплексную загрузку
        if len(photos) == 0:
            print("🔍 Таблица order_photos пуста, пробуем комплексную загрузку...")
            photos = await db.get_complete_photos()
            print(f"✅ Загружено {len(photos)} фотографий через комплексную загрузку")
        
        return photos
    except Exception as e:
        print(f"❌ Ошибка получения фотографий: {str(e)}")
        import traceback
        traceback.print_exc()
        # Возвращаем пустой список вместо ошибки, чтобы интерфейс не ломался
        return []

@app.get("/admin/orders/{order_id}/other-heroes", response_model=List[dict])
async def get_order_other_heroes(
    order_id: int, 
    current_manager: str = Depends(get_current_manager)
):
    """Получает фотографии других героев для заказа"""
    # Проверяем права доступа к заказу
    can_access = await can_access_order(current_manager, order_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    try:
        heroes = await db.get_order_other_heroes(order_id)
        print(f"✅ Найдено {len(heroes)} героев для заказа {order_id}")
        return heroes
    except Exception as e:
        print(f"❌ Ошибка получения героев для заказа {order_id}: {e}")
        # Возвращаем пустой список вместо ошибки
        return []



# --- API для шаблонов обложек ---

class CoverTemplateOut(BaseModel):
    id: int
    name: str
    filename: str
    category: str
    created_at: str

@app.get("/admin/cover-templates", response_model=List[CoverTemplateOut])
async def get_cover_templates(current_manager: str = Depends(get_current_manager)):
    """Получает все шаблоны обложек"""
    try:
        templates = await db.get_cover_templates()
        print(f"✅ Найдено {len(templates)} шаблонов обложек")
        return templates
    except Exception as e:
        print(f"❌ Ошибка получения шаблонов обложек: {e}")
        # Возвращаем пустой список вместо ошибки
        return []

@app.post("/admin/cover-templates", response_model=CoverTemplateOut)
async def create_cover_template(
    name: str = Form(...),
    category: str = Form(...),
    file: UploadFile = File(...),
    current_manager: str = Depends(get_super_admin)
):
    """Создать новый шаблон обложки (только для супер-админов)"""
    try:
        # Проверяем, что файл является изображением
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Файл должен быть изображением")
        
        # Создаем папку для обложек, если её нет
        covers_dir = "covers"
        os.makedirs(covers_dir, exist_ok=True)
        
        # Генерируем уникальное имя файла
        file_extension = os.path.splitext(file.filename)[1] if file.filename else '.jpg'
        import secrets
        unique_filename = f"cover_{int(time.time())}_{secrets.token_hex(4)}{file_extension}"
        file_path = os.path.join(covers_dir, unique_filename)
        
        # Сохраняем файл
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Добавляем запись в базу данных
        template = await db.add_cover_template(name, unique_filename, category)
        return template
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/covers/{cover_id}")
async def delete_cover_template(
    cover_id: int,
    current_manager: str = Depends(get_super_admin)
):
    """Удалить шаблон обложки (только для супер-админов)"""
    try:
        # Получаем информацию об обложке
        template = await db.get_cover_template_by_id(cover_id)
        if not template:
            raise HTTPException(status_code=404, detail="Обложка не найдена")
        
        # Удаляем файл с диска
        covers_dir = "covers"
        file_path = os.path.join(covers_dir, template['filename'])
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Удаляем запись из базы данных
        await db.delete_cover_template(cover_id)
        
        return {"message": f"Обложка '{template['name']}' успешно удалена"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- API для стилей книг ---

class BookStyleOut(BaseModel):
    id: int
    name: str
    description: str
    filename: str
    category: str
    created_at: str

class VoiceStyleOut(BaseModel):
    id: int
    name: str
    description: str
    filename: str
    gender: str
    created_at: str

@app.get("/admin/book-styles", response_model=List[BookStyleOut])
async def get_book_styles(current_manager: str = Depends(get_current_manager)):
    """Получает все стили книг"""
    try:
        styles = await db.get_book_styles()
        print(f"✅ Найдено {len(styles)} стилей книг")
        return styles
    except Exception as e:
        print(f"❌ Ошибка получения стилей книг: {e}")
        # Возвращаем пустой список вместо ошибки
        return []

@app.post("/admin/book-styles", response_model=BookStyleOut)
async def create_book_style(
    name: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    file: UploadFile = File(...),
    current_manager: str = Depends(get_current_manager)
):
    """Создать новый стиль книги"""
    try:
        # Проверяем, что файл является изображением
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Файл должен быть изображением")
        
        # Создаем папку для стилей, если её нет
        styles_dir = "styles"
        os.makedirs(styles_dir, exist_ok=True)
        
        # Генерируем уникальное имя файла
        file_extension = os.path.splitext(file.filename)[1] if file.filename else '.jpg'
        import secrets
        unique_filename = f"style_{int(time.time())}_{secrets.token_hex(4)}{file_extension}"
        file_path = os.path.join(styles_dir, unique_filename)
        
        # Сохраняем файл
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Добавляем запись в базу данных
        style = await db.add_book_style(name, description, unique_filename, category)
        return style
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/book-styles/{style_id}")
async def delete_book_style(
    style_id: int,
    current_manager: str = Depends(get_current_manager)
):
    """Удалить стиль книги"""
    try:
        # Получаем информацию о стиле перед удалением
        styles = await db.get_book_styles()
        style_to_delete = None
        for style in styles:
            if style['id'] == style_id:
                style_to_delete = style
                break
        
        if not style_to_delete:
            raise HTTPException(status_code=404, detail="Стиль не найден")
        
        # Удаляем файл стиля
        styles_dir = "styles"
        file_path = os.path.join(styles_dir, style_to_delete['filename'])
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Удаляем запись из базы данных
        success = await db.delete_book_style(style_id)
        if not success:
            raise HTTPException(status_code=500, detail="Ошибка удаления из базы данных")
        
        return {"success": True, "message": f"Стиль '{style_to_delete['name']}' удален"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/admin/book-styles/{style_id}")
async def update_book_style(
    style_id: int,
    name: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    file: UploadFile = File(None),
    current_manager: str = Depends(get_current_manager)
):
    """Обновить стиль книги"""
    try:
        # Получаем информацию о стиле
        styles = await db.get_book_styles()
        style_to_update = None
        for style in styles:
            if style['id'] == style_id:
                style_to_update = style
                break
        
        if not style_to_update:
            raise HTTPException(status_code=404, detail="Стиль не найден")
        
        # Если загружен новый файл, сохраняем его
        new_filename = style_to_update['filename']  # По умолчанию оставляем старое имя
        if file:
            # Проверяем, что файл является изображением
            if not file.content_type or not file.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="Файл должен быть изображением")
            
            # Создаем папку для стилей, если её нет
            styles_dir = "styles"
            os.makedirs(styles_dir, exist_ok=True)
            
            # Генерируем уникальное имя файла
            file_extension = os.path.splitext(file.filename)[1] if file.filename else '.jpg'
            import secrets
            new_filename = f"style_{int(time.time())}_{secrets.token_hex(4)}{file_extension}"
            file_path = os.path.join(styles_dir, new_filename)
            
            # Сохраняем новый файл
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            # Удаляем старый файл
            old_file_path = os.path.join(styles_dir, style_to_update['filename'])
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
        
        # Обновляем запись в базе данных
        success = await db.update_book_style(style_id, name, description, new_filename, category)
        if not success:
            raise HTTPException(status_code=500, detail="Ошибка обновления в базе данных")
        
        return {"success": True, "message": f"Стиль '{name}' обновлен"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- API для стилей голоса ---

@app.get("/admin/voice-styles", response_model=List[VoiceStyleOut])
async def get_voice_styles(current_manager: str = Depends(get_current_manager)):
    """Получает все стили голоса"""
    try:
        print(f"🔍 Запрос стилей голоса от менеджера: {current_manager}")
        styles = await db.get_voice_styles()
        print(f"✅ Найдено {len(styles)} стилей голоса")
        print(f"📋 Стили: {styles}")
        return styles
    except Exception as e:
        print(f"❌ Ошибка получения стилей голоса: {e}")
        return []

@app.post("/admin/voice-styles", response_model=VoiceStyleOut)
async def create_voice_style(
    name: str = Form(...),
    description: str = Form(...),
    gender: str = Form(...),
    file: UploadFile = File(...),
    current_manager: str = Depends(get_super_admin)
):
    """Создать новый стиль голоса (только для супер-админов)"""
    try:
        # Проверяем, что файл является аудио
        if not file.content_type or not file.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="Файл должен быть аудио")
        
        # Создаем папку для голосов, если её нет
        voices_dir = "voices"
        os.makedirs(voices_dir, exist_ok=True)
        
        # Генерируем уникальное имя файла
        file_extension = os.path.splitext(file.filename)[1] if file.filename else '.mp3'
        import secrets
        unique_filename = f"voice_{int(time.time())}_{secrets.token_hex(4)}{file_extension}"
        file_path = os.path.join(voices_dir, unique_filename)
        
        # Сохраняем файл
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Добавляем запись в базу данных
        style = await db.add_voice_style(name, description, unique_filename, gender)
        return style
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/voice-styles/{style_id}")
async def delete_voice_style(
    style_id: int,
    current_manager: str = Depends(get_super_admin)
):
    """Удалить стиль голоса (только для супер-админов)"""
    try:
        # Получаем информацию о стиле перед удалением
        styles = await db.get_voice_styles()
        style_to_delete = None
        for style in styles:
            if style['id'] == style_id:
                style_to_delete = style
                break
        
        if not style_to_delete:
            raise HTTPException(status_code=404, detail="Стиль голоса не найден")
        
        # Удаляем файл стиля
        voices_dir = "voices"
        file_path = os.path.join(voices_dir, style_to_delete['filename'])
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Удаляем запись из базы данных
        success = await db.delete_voice_style(style_id)
        if not success:
            raise HTTPException(status_code=500, detail="Ошибка удаления из базы данных")
        
        return {"success": True, "message": f"Стиль голоса '{style_to_delete['name']}' удален"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/admin/voice-styles/{style_id}")
async def update_voice_style(
    style_id: int,
    name: str = Form(...),
    description: str = Form(...),
    gender: str = Form(...),
    file: UploadFile = File(None),
    current_manager: str = Depends(get_super_admin)
):
    """Обновить стиль голоса (только для супер-админов)"""
    try:
        # Получаем информацию о стиле
        styles = await db.get_voice_styles()
        style_to_update = None
        for style in styles:
            if style['id'] == style_id:
                style_to_update = style
                break
        
        if not style_to_update:
            raise HTTPException(status_code=404, detail="Стиль голоса не найден")
        
        # Если загружен новый файл, сохраняем его
        new_filename = style_to_update['filename']  # По умолчанию оставляем старое имя
        if file:
            # Проверяем, что файл является аудио
            if not file.content_type or not file.content_type.startswith('audio/'):
                raise HTTPException(status_code=400, detail="Файл должен быть аудио")
            
            # Создаем папку для голосов, если её нет
            voices_dir = "voices"
            os.makedirs(voices_dir, exist_ok=True)
            
            # Генерируем уникальное имя файла
            file_extension = os.path.splitext(file.filename)[1] if file.filename else '.mp3'
            import secrets
            new_filename = f"voice_{int(time.time())}_{secrets.token_hex(4)}{file_extension}"
            file_path = os.path.join(voices_dir, new_filename)
            
            # Сохраняем новый файл
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            # Удаляем старый файл
            old_file_path = os.path.join(voices_dir, style_to_update['filename'])
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
        
        # Обновляем запись в базе данных
        success = await db.update_voice_style(style_id, name, description, new_filename, gender)
        if not success:
            raise HTTPException(status_code=500, detail="Ошибка обновления в базе данных")
        
        return {"success": True, "message": f"Стиль голоса '{name}' обновлен"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- API для отложенных сообщений ---

class DelayedMessageCreate(BaseModel):
    order_id: Optional[int] = None
    message_type: str
    content: str
    delay_minutes: int
    is_automatic: bool = False
    order_step: Optional[str] = None  # Новое поле для выбора шага заказа
    story_batch: int = 0
    story_pages: Optional[str] = None
    selected_stories: Optional[str] = None

class DelayedMessageUpdate(BaseModel):
    name: Optional[str] = None
    content: str
    delay_minutes: int
    message_type: str
    order_step: Optional[str] = None

class DelayedMessageFile(BaseModel):
    file_path: str
    file_type: str
    file_name: str
    file_size: int

class DelayedMessageOut(BaseModel):
    id: int
    name: Optional[str] = None  # Добавляем поле name
    order_id: Optional[int] = None
    user_id: Optional[int] = None
    manager_id: Optional[int] = None
    manager_email: Optional[str] = None
    manager_name: Optional[str] = None
    message_type: str
    content: str
    delay_minutes: int
    status: str
    created_at: str
    scheduled_at: Optional[str] = None  # Может быть NULL для шаблонов
    sent_at: Optional[str] = None
    order_step: Optional[str] = None  # Новое поле для шага заказа
    files: Optional[List[DelayedMessageFile]] = []
    is_active: Optional[bool] = True  # Активен ли шаблон
    usage_count: Optional[int] = 0    # Количество использований
    last_used: Optional[str] = None   # Последнее использование

# Модели для новой системы шаблонов
class MessageTemplateCreate(BaseModel):
    name: str
    message_type: str
    content: str
    order_step: str
    delay_minutes: int = 0

class MessageTemplateOut(BaseModel):
    id: int
    name: str
    message_type: str
    content: str
    order_step: str
    delay_minutes: int
    is_active: bool
    created_at: str
    updated_at: str
    manager_id: Optional[int] = None
    manager_email: Optional[str] = None
    manager_name: Optional[str] = None

@app.get("/admin/delayed-messages", response_model=List[DelayedMessageOut])
async def get_delayed_messages(current_manager: str = Depends(get_current_manager)):
    """Получает шаблоны отложенных сообщений"""
    try:
        # Проверяем, является ли менеджер супер-админом
        is_super = await db.is_super_admin(current_manager)
        
        if is_super:
            # Супер-админ видит все шаблоны
            messages = await db.get_delayed_message_templates()
        else:
            # Обычный менеджер видит только свои шаблоны
            messages = await db.get_manager_delayed_messages(current_manager)
        
        # Добавляем файлы к каждому сообщению
        for message in messages:
            files = await db.get_message_template_files(message["id"])
            message["files"] = files
        
        print(f"✅ Найдено {len(messages)} шаблонов отложенных сообщений")
        return messages
    except Exception as e:
        print(f"❌ Ошибка получения шаблонов отложенных сообщений: {e}")
        # Возвращаем пустой список вместо ошибки
        return []

@app.post("/admin/delayed-messages", response_model=DelayedMessageOut)
async def create_delayed_message(
    message: DelayedMessageCreate,
    current_manager: str = Depends(get_content_editor)
):
    """Создает новое отложенное сообщение"""
    try:
        manager = await db.get_manager_by_email(current_manager)
        if not manager:
            raise HTTPException(status_code=404, detail="Менеджер не найден")
        
        # Для общих сообщений (is_automatic=True) не нужен order_id
        if message.is_automatic:
            if not await db.is_super_admin(current_manager):
                raise HTTPException(status_code=403, detail="Только главный админ может создавать общие сообщения")
            
            # Используем новую систему шаблонов
            message_id = await db.create_message_template(
                name=f"{message.message_type}_{message.delay_minutes}min",  # Генерируем имя
                message_type=message.message_type,
                content=message.content,
                order_step=message.order_step,
                delay_minutes=message.delay_minutes,
                manager_id=manager["id"]
            )
        else:
            # Для личных сообщений проверяем права доступа к заказу
            if not message.order_id:
                raise HTTPException(status_code=400, detail="Для личного сообщения необходимо указать заказ")
            
            can_access = await db.can_access_order(current_manager, message.order_id)
            if not can_access:
                raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
            
            # Получаем order для user_id
            order = await db.get_order(message.order_id)
            if not order:
                raise HTTPException(status_code=404, detail="Заказ не найден")
            
            message_id = await db.add_delayed_message(
                message.order_id,
                order["user_id"],
                message.message_type,
                message.content,
                message.delay_minutes,
                manager["id"],
                False,  # is_automatic = False
                message.order_step,  # order_step для личных сообщений
                0,      # story_batch = 0
                None,   # story_pages = None
                None    # selected_stories = None
            )
        
        # Получаем созданное сообщение
        if message.is_automatic:
            # Для шаблонов получаем из новой таблицы
            templates = await db.get_message_templates()
            created_message = next((tmpl for tmpl in templates if tmpl["id"] == message_id), None)
            
            if not created_message:
                raise HTTPException(status_code=500, detail="Ошибка создания шаблона сообщения")
            
            # Преобразуем в формат DelayedMessageOut
            created_message = {
                "id": created_message["id"],
                "order_id": None,
                "user_id": None,
                "manager_id": created_message.get("manager_id"),
                "message_type": created_message["message_type"],
                "content": created_message["content"],
                "delay_minutes": created_message["delay_minutes"],
                "status": "active",
                "created_at": created_message["created_at"],
                "scheduled_at": None,
                "sent_at": None,
                "is_automatic": True,
                "order_step": created_message.get("order_step"),
                "story_batch": 0,
                "story_pages": None,
                "selected_stories": None,
                "is_active": created_message.get("is_active", True),
                "usage_count": 0,
                "last_used": None,
                "files": []  # Новые шаблоны пока не поддерживают файлы
            }
        else:
            # Для личных сообщений получаем из старой таблицы
            messages = await db.get_manager_delayed_messages(current_manager)
            created_message = next((msg for msg in messages if msg["id"] == message_id), None)
            
            if not created_message:
                raise HTTPException(status_code=500, detail="Ошибка создания отложенного сообщения")
            
            # Добавляем файлы
            files = await db.get_message_template_files(message_id)
            created_message["files"] = files
        
        return created_message
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка создания отложенного сообщения: {str(e)}")

@app.post("/admin/delayed-messages/{message_id}/files", response_model=dict)
async def add_files_to_delayed_message(
    message_id: int,
    files: List[UploadFile] = File(...),
    current_manager: str = Depends(get_content_editor)
):
    """Добавляет файлы к отложенному сообщению"""
    try:
        # Проверяем права доступа к сообщению
        can_access = await db.can_manager_access_delayed_message(current_manager, message_id)
        if not can_access:
            raise HTTPException(status_code=403, detail="Доступ к сообщению запрещен")
        
        # Проверяем количество файлов (максимум 15)
        if len(files) > 15:
            raise HTTPException(status_code=400, detail="Максимальное количество файлов: 15")
        
        # Проверяем типы файлов - расширенный список
        allowed_types = [
            # Изображения
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/tiff', 'image/svg+xml',
            # Аудио
            'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg', 'audio/mp4', 'audio/m4a', 'audio/wma', 'audio/aac', 
            'audio/flac', 'audio/opus', 'audio/amr', 'audio/midi', 'audio/mid', 'audio/xmf', 'audio/rtttl', 
            'audio/smf', 'audio/imy', 'audio/rtx', 'audio/ota', 'audio/jad', 'audio/jar',
            # Видео
            'video/mp4', 'video/avi', 'video/mov', 'video/quicktime', 'video/webm', 'video/x-matroska', 'video/mkv', 
            'video/flv', 'video/wmv', 'video/m4v', 'video/3gp', 'video/ogv',
            # Документы
            'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'text/plain', 'text/csv', 'application/rtf', 'application/zip', 'application/x-rar-compressed',
            'application/x-7z-compressed', 'application/x-tar', 'application/gzip'
        ]
        for file in files:
            if file.content_type not in allowed_types:
                raise HTTPException(status_code=400, detail=f"Неподдерживаемый тип файла: {file.content_type}")
        
        # Сохраняем файлы
        uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        
        saved_files = []
        for file in files:
            file_ext = os.path.splitext(file.filename)[1]
            save_path = os.path.join(uploads_dir, f"delayed_message_{message_id}_{file.filename}")
            
            with open(save_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            # Определяем тип файла
            if file.content_type.startswith("image/"):
                file_type = "photo"
            elif file.content_type.startswith("audio/"):
                file_type = "audio"
            elif file.content_type.startswith("video/"):
                file_type = "video"
            elif file.content_type == "image/gif":
                file_type = "gif"  # GIF как отдельный тип для анимации
            elif file.content_type in ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                     "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                     "application/vnd.ms-powerpoint", "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                     "text/plain", "text/csv", "application/rtf"]:
                file_type = "document"
            elif file.content_type in ["application/zip", "application/x-rar-compressed", "application/x-7z-compressed", 
                                     "application/x-tar", "application/gzip"]:
                file_type = "archive"
            else:
                file_type = "document"  # По умолчанию как документ
            
            # Добавляем файл в базу данных
            await db.add_delayed_message_file(
                message_id,
                save_path,
                file_type,
                file.filename,
                len(content)
            )
            
            saved_files.append({
                "file_name": file.filename,
                "file_type": file_type,
                "file_size": len(content)
            })
        
        return {
            "success": True,
            "message": f"Добавлено {len(saved_files)} файлов",
            "files": saved_files
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка добавления файлов: {str(e)}")

@app.post("/admin/delayed-messages/{message_id}/toggle-active")
async def toggle_template_active(
    message_id: int,
    request: dict,
    current_manager: str = Depends(get_current_manager)
):
    """Переключает активность шаблона отложенного сообщения"""
    try:
        # Проверяем права доступа к сообщению
        can_access = await db.can_manager_access_delayed_message(current_manager, message_id)
        if not can_access:
            raise HTTPException(status_code=403, detail="Доступ к шаблону запрещен")
        
        is_active = request.get("is_active", True)
        
        # Обновляем статус активности
        success = await db.toggle_template_active(message_id, is_active)
        
        if success:
            return {"success": True, "message": f"Шаблон {'активирован' if is_active else 'деактивирован'}"}
        else:
            raise HTTPException(status_code=500, detail="Ошибка изменения статуса шаблона")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка изменения статуса шаблона: {str(e)}")

# --- API для работы с триггерными сообщениями ---

@app.get("/admin/orders/{order_id}/trigger-messages", response_model=List[dict])
async def get_order_trigger_messages(
    order_id: int,
    current_manager: str = Depends(get_current_manager)
):
    """Получает информацию о триггерных сообщениях для заказа"""
    try:
        # Проверяем права доступа к заказу
        can_access = await db.can_access_order(current_manager, order_id)
        if not can_access:
            raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
        
        trigger_messages = await db.get_trigger_messages_for_order(order_id)
        return trigger_messages
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения триггерных сообщений: {str(e)}")

@app.delete("/admin/orders/{order_id}/trigger-messages", response_model=dict)
async def cleanup_order_trigger_messages(
    order_id: int,
    message_types: List[str],
    current_manager: str = Depends(get_current_manager)
):
    """Удаляет триггерные сообщения определенных типов для заказа"""
    try:
        # Проверяем права доступа к заказу
        can_access = await db.can_access_order(current_manager, order_id)
        if not can_access:
            raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
        
        deleted_count = await db.cleanup_trigger_messages_by_type(order_id, message_types)
        return {
            "success": True, 
            "message": f"Удалено {deleted_count} триггерных сообщений",
            "deleted_count": deleted_count
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка удаления триггерных сообщений: {str(e)}")

@app.delete("/admin/delayed-messages/{message_id}/files/{file_id}", response_model=dict)
async def delete_delayed_message_file(
    message_id: int,
    file_id: int,
    current_manager: str = Depends(get_content_editor)
):
    """Удаляет файл отложенного сообщения"""
    try:
        # Проверяем права доступа к сообщению
        can_access = await db.can_manager_access_delayed_message(current_manager, message_id)
        if not can_access and not await db.is_super_admin(current_manager):
            raise HTTPException(status_code=403, detail="Доступ к сообщению запрещен")
        
        success = await db.delete_delayed_message_file(file_id)
        if not success:
            raise HTTPException(status_code=404, detail="Файл не найден")
        
        return {"success": True, "message": "Файл удален"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка удаления файла: {str(e)}")

@app.delete("/admin/delayed-messages/{message_id}/files", response_model=dict)
async def delete_delayed_message_file_by_name(
    message_id: int,
    file_name: str = Query(...),
    current_manager: str = Depends(get_content_editor)
):
    """Удаляет файл отложенного сообщения по имени"""
    try:
        # Проверяем права доступа к сообщению
        can_access = await db.can_manager_access_delayed_message(current_manager, message_id)
        if not can_access and not await db.is_super_admin(current_manager):
            raise HTTPException(status_code=403, detail="Доступ к сообщению запрещен")
        
        success = await db.delete_delayed_message_file_by_name(message_id, file_name)
        if not success:
            raise HTTPException(status_code=404, detail="Файл не найден")
        
        return {"success": True, "message": "Файл удален"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка удаления файла: {str(e)}")

@app.post("/admin/message-templates/{template_id}/files", response_model=dict)
async def add_files_to_message_template(
    template_id: int,
    files: List[UploadFile] = File(...),
    current_manager: str = Depends(get_content_editor)
):
    """Добавляет файлы к шаблону сообщения"""
    try:
        # Проверяем права доступа к шаблону
        can_access = await db.can_manager_access_message_template(current_manager, template_id)
        if not can_access and not await db.is_super_admin(current_manager):
            raise HTTPException(status_code=403, detail="Доступ к шаблону запрещен")
        
        # Создаем директорию для загрузок, если её нет
        uploads_dir = os.path.join(os.getcwd(), "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        
        saved_files = []
        for file in files:
            file_ext = os.path.splitext(file.filename)[1]
            save_path = os.path.join(uploads_dir, f"template_{template_id}_{file.filename}")
            
            with open(save_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            # Определяем тип файла
            if file.content_type.startswith("image/"):
                file_type = "photo"
            elif file.content_type.startswith("audio/"):
                file_type = "audio"
            elif file.content_type.startswith("video/"):
                file_type = "video"
            elif file.content_type == "image/gif":
                file_type = "gif"
            elif file.content_type in ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                     "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                     "application/vnd.ms-powerpoint", "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                     "text/plain", "text/csv", "application/rtf"]:
                file_type = "document"
            elif file.content_type in ["application/zip", "application/x-rar-compressed", "application/x-7z-compressed", 
                                     "application/x-tar", "application/gzip"]:
                file_type = "archive"
            else:
                file_type = "document"
            
            # Добавляем файл в базу данных
            await db.add_message_template_file(
                template_id,
                save_path,
                file_type,
                file.filename,
                len(content)
            )
            
            saved_files.append({
                "filename": file.filename,
                "file_type": file_type,
                "file_size": len(content)
            })
        
        return {"message": f"Загружено {len(saved_files)} файлов", "files": saved_files}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки файлов: {str(e)}")

@app.get("/admin/message-templates/{template_id}/files", response_model=List[dict])
async def get_message_template_files(
    template_id: int,
    current_manager: str = Depends(get_content_editor)
):
    """Получает файлы шаблона сообщения"""
    try:
        # Проверяем права доступа к шаблону
        can_access = await db.can_manager_access_message_template(current_manager, template_id)
        if not can_access and not await db.is_super_admin(current_manager):
            raise HTTPException(status_code=403, detail="Доступ к шаблону запрещен")
        
        files = await db.get_message_template_files(template_id)
        return files
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения файлов: {str(e)}")

@app.delete("/admin/message-templates/{template_id}/files/{file_id}", response_model=dict)
async def delete_message_template_file(
    template_id: int,
    file_id: int,
    current_manager: str = Depends(get_content_editor)
):
    """Удаляет файл шаблона сообщения"""
    try:
        # Проверяем права доступа к шаблону
        can_access = await db.can_manager_access_message_template(current_manager, template_id)
        if not can_access and not await db.is_super_admin(current_manager):
            raise HTTPException(status_code=403, detail="Доступ к шаблону запрещен")
        
        # Получаем информацию о файле перед удалением
        files = await db.get_message_template_files(template_id)
        file_to_delete = next((f for f in files if f['id'] == file_id), None)
        
        if not file_to_delete:
            raise HTTPException(status_code=404, detail="Файл не найден")
        
        # Удаляем физический файл
        try:
            if os.path.exists(file_to_delete['file_path']):
                os.remove(file_to_delete['file_path'])
        except Exception as e:
            logging.warning(f"Не удалось удалить файл {file_to_delete['file_path']}: {e}")
        
        # Удаляем запись из базы данных
        success = await db.delete_message_template_file(file_id)
        if not success:
            raise HTTPException(status_code=404, detail="Файл не найден в базе данных")
        
        return {"message": "Файл успешно удален"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка удаления файла: {str(e)}")

@app.delete("/admin/message-templates/{template_id}/files", response_model=dict)
async def delete_message_template_file_by_name(
    template_id: int,
    file_name: str = Query(...),
    current_manager: str = Depends(get_content_editor)
):
    """Удаляет файл шаблона сообщения по имени файла"""
    try:
        # Проверяем права доступа к шаблону
        can_access = await db.can_manager_access_message_template(current_manager, template_id)
        if not can_access and not await db.is_super_admin(current_manager):
            raise HTTPException(status_code=403, detail="Доступ к шаблону запрещен")
        
        # Получаем информацию о файле перед удалением
        files = await db.get_message_template_files(template_id)
        file_to_delete = next((f for f in files if f.get('file_name') == file_name), None)
        
        if not file_to_delete:
            raise HTTPException(status_code=404, detail="Файл не найден")
        
        # Удаляем файл
        success = await db.delete_message_template_file_by_name(template_id, file_name)
        
        if not success:
            raise HTTPException(status_code=500, detail="Не удалось удалить файл")
        
        return {"message": "Файл успешно удален"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка удаления файла: {str(e)}")

@app.delete("/admin/delayed-messages/{message_id}", response_model=dict)
async def delete_delayed_message(
    message_id: int,
    current_manager: str = Depends(get_content_editor)
):
    """Удаляет отложенное сообщение или шаблон"""
    try:
        # Сначала проверяем, является ли это шаблоном из новой таблицы
        template = await db.get_message_template_by_id(message_id)
        
        if template:
            # Это шаблон из новой таблицы message_templates
            if not await db.is_super_admin(current_manager):
                raise HTTPException(status_code=403, detail="Только главный админ может удалять шаблоны")
            
            success = await db.delete_message_template(message_id)
            if not success:
                raise HTTPException(status_code=404, detail="Шаблон не найден")
            
            return {"success": True, "message": "Шаблон сообщения удален"}
        else:
            # Это старое отложенное сообщение
            can_access = await db.can_manager_access_delayed_message(current_manager, message_id)
            if not can_access:
                raise HTTPException(status_code=403, detail="Доступ к сообщению запрещен")
            
            success = await db.delete_delayed_message(message_id)
            if not success:
                raise HTTPException(status_code=404, detail="Отложенное сообщение не найдено")
            
            return {"success": True, "message": "Отложенное сообщение удалено"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка удаления отложенного сообщения: {str(e)}")

@app.put("/admin/delayed-messages/{message_id}", response_model=DelayedMessageOut)
async def update_delayed_message(
    message_id: int,
    message_update: DelayedMessageUpdate,
    current_manager: str = Depends(get_content_editor)
):
    """Обновляет отложенное сообщение или шаблон"""
    try:
        # Сначала проверяем, является ли это шаблоном из новой таблицы
        template = await db.get_message_template_by_id(message_id)
        
        if template:
            # Это шаблон из новой таблицы message_templates
            if not await db.is_super_admin(current_manager):
                raise HTTPException(status_code=403, detail="Только главный админ может редактировать шаблоны")
            
            # Обновляем шаблон
            # Используем переданное имя или генерируем автоматически
            template_name = message_update.name if message_update.name else f"{message_update.message_type}_{message_update.delay_minutes}min"
            success = await db.update_message_template(
                message_id,
                template_name,
                message_update.content,
                message_update.delay_minutes,
                message_update.message_type,
                message_update.order_step
            )
            
            if not success:
                raise HTTPException(status_code=500, detail="Ошибка обновления шаблона")
            
            # Получаем обновленный шаблон
            updated_template = await db.get_message_template_by_id(message_id)
            if not updated_template:
                raise HTTPException(status_code=500, detail="Ошибка получения обновленного шаблона")
            
            # Преобразуем в формат DelayedMessageOut
            return {
                "id": updated_template["id"],
                "order_id": None,
                "user_id": None,
                "manager_id": updated_template.get("manager_id"),
                "message_type": updated_template["message_type"],
                "content": updated_template["content"],
                "delay_minutes": updated_template["delay_minutes"],
                "status": "active",
                "created_at": updated_template["created_at"],
                "scheduled_at": None,
                "sent_at": None,
                "is_automatic": True,
                "order_step": updated_template.get("order_step"),
                "story_batch": 0,
                "story_pages": None,
                "selected_stories": None,
                "is_active": updated_template.get("is_active", True),
                "usage_count": 0,
                "last_used": None,
                "files": []
            }
        else:
            # Это старое отложенное сообщение
            can_access = await db.can_manager_access_delayed_message(current_manager, message_id)
            if not can_access:
                raise HTTPException(status_code=403, detail="Доступ к сообщению запрещен")
            
            # Получаем текущее сообщение для проверки статуса
            current_message = await db.get_delayed_message_by_id(message_id)
            if not current_message:
                raise HTTPException(status_code=404, detail="Отложенное сообщение не найдено")
            
            # Проверяем, что сообщение еще не отправлено
            if current_message["status"] == "sent":
                raise HTTPException(status_code=400, detail="Нельзя редактировать уже отправленное сообщение")
            
            # Обновляем сообщение
            success = await db.update_delayed_message(
                message_id,
                message_update.content,
                message_update.delay_minutes,
                message_update.message_type
            )
            
            if not success:
                raise HTTPException(status_code=500, detail="Ошибка обновления сообщения")
            
            # Получаем обновленное сообщение
            updated_message = await db.get_delayed_message_by_id(message_id)
            if not updated_message:
                raise HTTPException(status_code=500, detail="Ошибка получения обновленного сообщения")
            
            return updated_message
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обновления отложенного сообщения: {str(e)}")

# --- API для цен (только для супер-админа) ---

class PricingItemCreate(BaseModel):
    product: str
    price: float
    currency: str = "RUB"
    description: str = ""
    upgrade_price_difference: float = 0.0
    is_active: bool = True

class PricingItemUpdate(BaseModel):
    product: str
    price: float
    currency: str
    description: str
    upgrade_price_difference: float = 0.0
    is_active: bool

class PricingItemOut(BaseModel):
    id: int
    product: str
    price: float
    currency: str
    description: str
    upgrade_price_difference: float
    is_active: bool
    created_at: str
    updated_at: str

@app.get("/admin/pricing", response_model=List[PricingItemOut])
async def get_pricing_items(current_manager: str = Depends(get_current_manager)):
    """Получает все цены"""
    try:
        items = await db.get_pricing_items()
        print(f"✅ Найдено {len(items)} цен")
        return items
    except Exception as e:
        print(f"❌ Ошибка получения цен: {e}")
        # Возвращаем пустой список вместо ошибки
        return []

@app.post("/admin/pricing", response_model=PricingItemOut)
async def create_pricing_item(
    item: PricingItemCreate,
    current_manager: str = Depends(get_super_admin)
):
    """Создает новую цену (только для супер-админа)"""
    try:
        item_id = await db.create_pricing_item(
            item.product,
            item.price,
            item.currency,
            item.description,
            item.upgrade_price_difference,
            item.is_active
        )
        
        # Получаем созданную цену
        items = await db.get_pricing_items()
        created_item = next((price for price in items if price["id"] == item_id), None)
        
        if not created_item:
            raise HTTPException(status_code=500, detail="Ошибка создания цены")
        
        return created_item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка создания цены: {str(e)}")

@app.put("/admin/pricing/{item_id}", response_model=PricingItemOut)
async def update_pricing_item(
    item_id: int,
    item: PricingItemUpdate,
    current_manager: str = Depends(get_super_admin)
):
    """Обновляет цену (только для супер-админа)"""
    try:
        success = await db.update_pricing_item(
            item_id,
            item.product,
            item.price,
            item.currency,
            item.description,
            item.upgrade_price_difference,
            item.is_active
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Цена не найдена")
        
        # Получаем обновленную цену
        items = await db.get_pricing_items()
        updated_item = next((price for price in items if price["id"] == item_id), None)
        
        if not updated_item:
            raise HTTPException(status_code=500, detail="Ошибка обновления цены")
        
        return updated_item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обновления цены: {str(e)}")

@app.patch("/admin/pricing/{item_id}/toggle", response_model=dict)
async def toggle_pricing_item(
    item_id: int,
    toggle_data: dict,
    current_manager: str = Depends(get_super_admin)
):
    """Переключает статус цены (только для супер-админа)"""
    try:
        success = await db.toggle_pricing_item(item_id, toggle_data["is_active"])
        if not success:
            raise HTTPException(status_code=404, detail="Цена не найдена")
        
        return {"success": True, "message": "Статус цены изменен"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка изменения статуса цены: {str(e)}")

@app.delete("/admin/pricing/{item_id}", response_model=dict)
async def delete_pricing_item(
    item_id: int,
    current_manager: str = Depends(get_super_admin)
):
    """Удаляет цену (только для супер-админа)"""
    try:
        success = await db.delete_pricing_item(item_id)
        if not success:
            raise HTTPException(status_code=404, detail="Цена не найдена")
        
        return {"success": True, "message": "Цена удалена"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка удаления цены: {str(e)}")
@app.post("/admin/pricing/populate", response_model=dict)
async def populate_pricing_items(current_manager: str = Depends(get_super_admin)):
    """Заполняет таблицу цен начальными данными (только для суперадмина)"""
    try:
        await db.populate_pricing_items()
        return {"success": True, "message": "Цены заполнены начальными данными"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка заполнения цен: {str(e)}")

# --- API для контента ---

class ContentStepCreate(BaseModel):
    step_key: str
    step_name: str
    content_type: str
    content: str
    materials: str = ""
    is_active: bool = True

class ContentStepUpdate(BaseModel):
    step_key: str
    step_name: str
    content_type: str
    content: str
    materials: str
    is_active: bool

class ContentStepOut(BaseModel):
    id: int
    step_key: str
    step_name: str
    content_type: str
    content: str
    materials: str
    is_active: bool
    created_at: str
    updated_at: str

@app.get("/admin/content", response_model=List[ContentStepOut])
async def get_content_steps(current_manager: str = Depends(get_current_manager)):
    """Получает все шаги контента"""
    try:
        steps = await db.get_content_steps()
        print(f"✅ Найдено {len(steps)} шагов контента")
        return steps
    except Exception as e:
        print(f"❌ Ошибка получения контента: {e}")
        # Возвращаем пустой список вместо ошибки
        return []

@app.post("/admin/content", response_model=ContentStepOut)
async def create_content_step(
    step: ContentStepCreate,
    current_manager: str = Depends(get_content_editor)
):
    """Создает новый шаг контента"""
    try:
        step_id = await db.create_content_step(
            step.step_key,
            step.step_name,
            step.content_type,
            step.content,
            step.materials,
            step.is_active
        )
        
        # Получаем созданный шаг
        steps = await db.get_content_steps()
        created_step = next((s for s in steps if s["id"] == step_id), None)
        
        if not created_step:
            raise HTTPException(status_code=500, detail="Ошибка создания шага контента")
        
        return created_step
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка создания шага контента: {str(e)}")

@app.put("/admin/content/{step_id}", response_model=ContentStepOut)
async def update_content_step(
    step_id: int,
    step: ContentStepUpdate,
    current_manager: str = Depends(get_content_editor)
):
    """Обновляет шаг контента"""
    try:
        success = await db.update_content_step(
            step_id,
            step.step_key,
            step.step_name,
            step.content_type,
            step.content,
            step.materials,
            step.is_active
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Шаг контента не найден")
        
        # Получаем обновленный шаг
        steps = await db.get_content_steps()
        updated_step = next((s for s in steps if s["id"] == step_id), None)
        
        if not updated_step:
            raise HTTPException(status_code=500, detail="Ошибка обновления шага контента")
        
        return updated_step
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обновления шага контента: {str(e)}")

@app.patch("/admin/content/{step_id}/toggle", response_model=dict)
async def toggle_content_step(
    step_id: int,
    toggle_data: dict,
    current_manager: str = Depends(get_content_editor)
):
    """Переключает статус шага контента"""
    try:
        success = await db.toggle_content_step(step_id, toggle_data["is_active"])
        if not success:
            raise HTTPException(status_code=404, detail="Шаг контента не найден")
        
        return {"success": True, "message": "Статус шага контента изменен"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка изменения статуса шага контента: {str(e)}")

@app.delete("/admin/content/{step_id}", response_model=dict)
async def delete_content_step(
    step_id: int,
    current_manager: str = Depends(get_content_editor)
):
    """Удаляет шаг контента"""
    try:
        success = await db.delete_content_step(step_id)
        if not success:
            raise HTTPException(status_code=404, detail="Шаг контента не найден")
        
        return {"success": True, "message": "Шаг контента удален"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка удаления шага контента: {str(e)}")

# --- API для работы с сообщениями бота ---

class BotMessageUpdate(BaseModel):
    content: str
    is_active: bool = True

@app.get("/admin/bot-messages", response_model=List[dict])
async def get_bot_messages(current_manager: str = Depends(get_current_manager)):
    """Получает все сообщения бота"""
    try:
        messages = await db.get_bot_messages()
        print(f"✅ Найдено {len(messages)} сообщений бота")
        return messages
    except Exception as e:
        print(f"❌ Ошибка получения сообщений бота: {e}")
        return []

@app.put("/admin/bot-messages/{message_id}", response_model=dict)
async def update_bot_message(
    message_id: int,
    message_update: BotMessageUpdate,
    current_manager: str = Depends(get_content_editor)
):
    """Обновляет сообщение бота"""
    try:
        print(f"🔄 Обновляем сообщение ID: {message_id}")
        print(f"   Контент: {message_update.content[:100]}...")
        print(f"   Активно: {message_update.is_active}")
        print(f"   Менеджер: {current_manager}")
        
        # Проверяем, существует ли сообщение
        existing_message = await db.get_bot_message_by_id(message_id)
        if not existing_message:
            print(f"❌ Сообщение с ID {message_id} не найдено")
            raise HTTPException(status_code=404, detail="Сообщение бота не найдено")
        
        print(f"   Существующее сообщение: {existing_message['message_key']}")
        
        # Обновляем сообщение
        success = await db.update_bot_message(message_id, message_update.content, message_update.is_active)
        print(f"   Результат обновления: {success}")
        
        if not success:
            print(f"❌ Ошибка обновления сообщения {message_id}")
            raise HTTPException(status_code=404, detail="Сообщение бота не найдено")
        
        # Обновляем кэш сообщений
        try:
            from bot_messages_cache import update_message_in_cache, invalidate_message_cache
            if message_update.is_active:
                await update_message_in_cache(existing_message['message_key'], message_update.content)
            else:
                await invalidate_message_cache(existing_message['message_key'])
            print(f"✅ Кэш сообщения {existing_message['message_key']} обновлен")
        except Exception as e:
            print(f"⚠️ Ошибка обновления кэша: {e}")
        
        print(f"✅ Сообщение {message_id} успешно обновлено")
        return {"success": True, "message": "Сообщение бота обновлено"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Исключение при обновлении сообщения {message_id}: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления сообщения бота: {str(e)}")

@app.delete("/admin/bot-messages/{message_id}", response_model=dict)
async def delete_bot_message(
    message_id: int,
    current_manager: str = Depends(get_content_editor)
):
    """Удаляет сообщение бота"""
    try:
        success = await db.delete_bot_message(message_id)
        if not success:
            raise HTTPException(status_code=404, detail="Сообщение бота не найдено")
        
        return {"success": True, "message": "Сообщение бота удалено"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка удаления сообщения бота: {str(e)}")

@app.post("/admin/bot-messages/populate", response_model=dict)
async def populate_bot_messages(current_manager: str = Depends(get_super_admin)):
    """Заполняет таблицу сообщений бота начальными данными (только для суперадмина)"""
    try:
        await db.populate_bot_messages()
        await db.auto_collect_bot_messages()
        return {"success": True, "message": "Сообщения бота заполнены начальными данными"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка заполнения сообщений бота: {str(e)}")

@app.post("/admin/bot-messages/auto-collect", response_model=dict)
async def auto_collect_bot_messages(current_manager: str = Depends(get_super_admin)):
    """Автоматически собирает сообщения из кода бота (только для суперадмина)"""
    try:
        await db.auto_collect_bot_messages()
        return {"success": True, "message": "Дополнительные сообщения бота собраны"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сбора сообщений бота: {str(e)}")

# --- API для сюжетов ---

class StoryProposalCreate(BaseModel):
    order_id: int
    story_batch: int
    stories: List[Dict[str, str]]  # список сюжетов с title и description
    pages: List[int]  # номера страниц

class StorySelectionUpdate(BaseModel):
    selected_stories: List[int]  # индексы выбранных сюжетов

@app.post("/admin/orders/{order_id}/story-proposals", response_model=dict)
async def create_story_proposal(
    order_id: int,
    proposal: StoryProposalCreate,
    current_manager: str = Depends(get_current_manager)
):
    """Создает предложение сюжетов для заказа"""
    try:
        # Проверяем права доступа к заказу
        can_access = await db.can_access_order(current_manager, order_id)
        if not can_access:
            raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
        
        # Сохраняем предложение в базу данных
        proposal_id = await db.add_story_proposal(
            order_id,
            proposal.story_batch,
            proposal.stories,
            proposal.pages
        )
        
        return {"success": True, "proposal_id": proposal_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка создания предложения сюжетов: {str(e)}")

@app.put("/admin/orders/{order_id}/story-proposals/{proposal_id}/selection", response_model=dict)
async def update_story_selection(
    order_id: int,
    proposal_id: int,
    selection: StorySelectionUpdate,
    current_manager: str = Depends(get_current_manager)
):
    """Обновляет выбранные сюжеты для предложения"""
    try:
        # Проверяем права доступа к заказу
        can_access = await db.can_access_order(current_manager, order_id)
        if not can_access:
            raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
        
        # Ограничиваем количество выбираемых сюжетов до 24
        if len(selection.selected_stories) > 24:
            selection.selected_stories = selection.selected_stories[:24]
        
        success = await db.update_story_selection(proposal_id, selection.selected_stories)
        if not success:
            raise HTTPException(status_code=404, detail="Предложение сюжетов не найдено")
        
        return {"success": True, "message": "Выбранные сюжеты обновлены"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обновления выбранных сюжетов: {str(e)}")

@app.get("/admin/orders/{order_id}/story-proposals", response_model=List[dict])
async def get_story_proposals(
    order_id: int,
    current_manager: str = Depends(get_current_manager)
):
    """Получает все предложения сюжетов для заказа"""
    try:
        # Проверяем права доступа к заказу
        can_access = await db.can_access_order(current_manager, order_id)
        if not can_access:
            raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
        
        proposals = await db.get_story_proposals(order_id)
        return proposals
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения предложений сюжетов: {str(e)}")

@app.delete("/admin/orders/{order_id}/story-proposals/{proposal_id}", response_model=dict)
async def delete_story_proposal(
    order_id: int,
    proposal_id: int,
    current_manager: str = Depends(get_current_manager)
):
    """Удаляет предложение сюжетов для заказа"""
    try:
        # Проверяем права доступа к заказу
        can_access = await db.can_access_order(current_manager, order_id)
        if not can_access:
            raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
        
        success = await db.delete_story_proposal(proposal_id)
        if not success:
            raise HTTPException(status_code=404, detail="Предложение сюжетов не найдено")
        
        return {"success": True, "message": "Предложение сюжетов удалено"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка удаления предложения сюжетов: {str(e)}")

# --- Назначение менеджера ---

@app.post("/admin/orders/{order_id}/assign-manager", response_model=dict)
async def assign_manager_to_order_endpoint(
    order_id: int,
    current_manager: str = Depends(get_super_admin)
):
    """Назначает менеджера к заказу автоматически"""
    try:
        success = await assign_manager_to_order(order_id)
        if success:
            return {"success": True, "message": "Менеджер успешно назначен к заказу"}
        else:
            raise HTTPException(status_code=400, detail="Не удалось назначить менеджера. Возможно, нет доступных менеджеров.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка назначения менеджера: {str(e)}")

@app.post("/admin/orders/assign-managers-all", response_model=dict)
async def assign_managers_to_all_orders_endpoint(
    current_manager: str = Depends(get_super_admin)
):
    """Назначает менеджеров ко всем заказам, которые их не имеют"""
    try:
        result = await assign_managers_to_all_orders()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка массового назначения менеджеров: {str(e)}")

# --- Загрузка индивидуальных страниц ---

@app.post("/admin/orders/{order_id}/upload-pages", response_model=UploadResponse)
async def upload_individual_pages(
    order_id: int,
    request: Request,
    current_manager: str = Depends(get_current_manager)
):
    """Загружает индивидуальные страницы для заказа и отправляет их пользователю"""
    print(f"🔍 ОТЛАДКА: Начинаем загрузку страниц для заказа {order_id}")
    
    # Проверяем права доступа к заказу
    if not await can_access_order(current_manager, order_id):
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    # Проверяем состояние бота
    try:
        from bot import bot
        if bot:
            bot_info = await bot.get_me()
            print(f"🔍 ОТЛАДКА: Бот {bot_info.username} активен")
        else:
            print(f"❌ Бот не инициализирован")
    except Exception as e:
        print(f"❌ Ошибка проверки состояния бота: {e}")
    
    try:
        # Получаем данные формы
        form_data = await request.form()
        
        print(f"🔍 ОТЛАДКА: Получены данные формы:")
        print(f"🔍 ОТЛАДКА: Всего ключей в форме: {len(form_data)}")
        for key, value in form_data.items():
            print(f"  - {key}: {type(value).__name__} = {value}")
            if isinstance(value, UploadFile):
                print(f"    Файл: {value.filename}, размер: {value.size if hasattr(value, 'size') else 'неизвестно'}")
        
        # Функция для получения следующего номера страницы
        # Используем функцию из базы данных для получения следующего номера страницы
        from db import get_next_page_number as db_get_next_page_number
        next_page_num = await db_get_next_page_number(order_id)
        print(f"🔍 ОТЛАДКА: Следующий номер страницы из БД: {next_page_num}")
        
        # Проверяем существующие страницы в базе данных
        from db import get_order_pages
        existing_pages = await get_order_pages(order_id)
        print(f"🔍 ОТЛАДКА: Существующие страницы в БД: {existing_pages}")
        
        # Извлекаем файлы и описания
        pages = []
        file_count = 0
        
        # Собираем все файлы страниц из формы
        page_files = []
        for key, value in form_data.items():
            if key.startswith("page_") and not key.startswith("description_"):
                # Извлекаем номер из ключа (например, "page_1" -> 1)
                try:
                    form_page_num = int(key.split("_")[1])
                    page_files.append((form_page_num, key, value))
                except (ValueError, IndexError):
                    continue
        
        # Сортируем по номеру в форме для правильного порядка
        page_files.sort(key=lambda x: x[0])
        
        # Обрабатываем файлы в порядке их появления в форме
        for form_page_num, page_key, file_value in page_files:
            description_key = f"description_{form_page_num}"
            # Всегда используем правильный номер страницы из базы данных
            description = f"Страница {next_page_num}"
            
            print(f"🔍 ОТЛАДКА: Обрабатываем файл {page_key} (form_page_num={form_page_num}) -> page_num={next_page_num}")
            
            pages.append({
                "file": file_value,
                "description": description,
                "page_num": next_page_num
            })
            next_page_num += 1
            file_count += 1
        
        if not pages:
            raise HTTPException(status_code=400, detail="Не найдено файлов для загрузки")
        
        # Сортируем по номеру страницы
        pages.sort(key=lambda x: x["page_num"])
        
        # Сохраняем файлы и отправляем пользователю
        import os
        from datetime import datetime
        
        # Создаем папку для страниц заказа
        pages_dir = f"uploads/order_{order_id}_pages"
        os.makedirs(pages_dir, exist_ok=True)
        
        # Получаем информацию о заказе
        order = await db.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Заказ не найден")
        
        user_id = order["user_id"]
        
                            # Сначала сохраняем все файлы
        saved_pages = []
        for page in pages:
            # Сохраняем файл
            timestamp = get_msk_now().strftime("%Y%m%d_%H%M%S")
            # Очищаем имя файла от проблемных символов
            safe_filename = page['file'].filename.replace('\\', '_').replace('/', '_').replace(':', '_')
            filename = f"page_{page['page_num']}_{timestamp}_{safe_filename}"
            file_path = os.path.join(pages_dir, filename)
            
            print(f"🔍 ОТЛАДКА: Сохраняем файл {page['file'].filename} как {filename}")
            print(f"🔍 ОТЛАДКА: Полный путь: {file_path}")
            
            with open(file_path, "wb") as f:
                content = await page["file"].read()
                f.write(content)
            
            # Проверяем, что файл сохранился
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # в МБ
                print(f"✅ Файл сохранен: {file_path} (размер: {file_size:.2f} МБ)")
            else:
                print(f"❌ Файл не сохранен: {file_path}")
                continue
            
            # Сохраняем информацию о странице в базу данных
            from db import save_page_number
            print(f"🔍 ОТЛАДКА: Сохраняем страницу {page['page_num']} в БД: {filename}")
            try:
                await save_page_number(order_id, page['page_num'], filename, page['description'])
                print(f"✅ Страница {page['page_num']} сохранена в БД")
            except Exception as db_error:
                print(f"❌ Ошибка сохранения страницы {page['page_num']} в БД: {db_error}")
                continue
            
            saved_pages.append({
                'file_path': file_path,
                'page_num': page['page_num'],
                'description': page['description']
            })
        
        # Теперь отправляем все страницы одним блоком
        try:
            from bot import bot
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Проверяем, что бот работает
            if not bot:
                print(f"❌ Бот не инициализирован")
                return {"success": False, "detail": "Бот не инициализирован"}
            
            # Проверяем, что пользователь не заблокировал бота
            try:
                chat_member = await bot.get_chat_member(user_id, bot.id)
                if chat_member.status == "kicked":
                    print(f"❌ Пользователь {user_id} заблокировал бота")
                    return {"success": False, "detail": "Пользователь заблокировал бота"}
            except Exception as e:
                print(f"❌ Не удалось проверить статус пользователя {user_id}: {e}")
            
            # Проверяем, отправлялись ли уже страницы для этого заказа
            pages_sent_before = await db.check_pages_sent_before(order_id)
            
            # Отправляем основное сообщение только при первой отправке страниц
            if not pages_sent_before:
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text="📖 <b>Выберите страницы для вашей книги</b>\n\n"
                         "Здесь представлены сгенерированные страницы и готовые вкладыши.\n"
                         "Выберите минимум <b>24 страницы</b> из предложенных.\n"
                         "После выбора напишите 'Далее' для продолжения.",
                        parse_mode="HTML"
                    )
                    print(f"✅ Основное сообщение отправлено пользователю {user_id}")
                except Exception as instructions_error:
                    print(f"❌ Ошибка отправки основного сообщения: {instructions_error}")
            else:
                print(f"ℹ️ Страницы уже отправлялись для заказа {order_id}, пропускаем основное сообщение")
            
            # Отправляем каждую страницу по отдельности с кнопкой выбора
            print(f"📤 Отправляем {len(saved_pages)} страниц по отдельности с кнопками")
            successful_pages = 0
            
            for page in saved_pages:
                # Проверяем существование файла
                if not os.path.exists(page['file_path']):
                    print(f"❌ Файл {page['file_path']} не существует!")
                    continue
                
                # Проверяем размер файла
                file_size = os.path.getsize(page['file_path']) / (1024 * 1024)  # в МБ
                print(f"🔍 ОТЛАДКА: Размер файла {page['file_path']}: {file_size:.2f} МБ")
                
                if file_size > 10:  # Если файл больше 10 МБ
                    print(f"⚠️ Файл {page['file_path']} слишком большой ({file_size:.2f} МБ), пропускаем...")
                    continue
                
                # Отправляем страницу с кнопкой выбора
                try:
                    await bot.send_photo(
                        chat_id=user_id,
                        photo=FSInputFile(page['file_path']),
                        caption=f"📖 {page['description']}\n\nВыберите эту страницу для вашей книги:",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="✅ Выбрать", callback_data=f"choose_page_{page['page_num']}")]
                        ])
                    )
                    successful_pages += 1
                    print(f"✅ Страница {page['page_num']} отправлена с кнопкой выбора")
                except Exception as single_error:
                    print(f"❌ Ошибка отправки страницы {page['page_num']}: {single_error}")
                    # Добавляем в outbox для отправки позже
                    try:
                        await db.add_outbox_task(
                            order_id=order_id,
                            user_id=user_id,
                            type_="page_selection",
                            content=page['file_path'],
                            file_type="image",
                            comment=f"Страница {page['page_num']}",
                            button_text="✅ Выбрать",
                            button_callback=f"choose_page_{page['page_num']}"
                        )
                        print(f"📝 Страница {page['page_num']} добавлена в outbox для отправки позже")
                    except Exception as outbox_error:
                        print(f"❌ Ошибка добавления в outbox: {outbox_error}")
            
            print(f"✅ Отправлено {successful_pages} из {len(saved_pages)} страниц пользователю {user_id} с кнопками выбора")
        
        except Exception as send_error:
            print(f"❌ Ошибка отправки страниц: {send_error}")
            # Добавляем все оставшиеся страницы в outbox
            for page in saved_pages:
                try:
                    await db.add_outbox_task(
                        order_id=order_id,
                        user_id=user_id,
                        type_="page_selection",
                        content=page['file_path'],
                        file_type="image",
                        comment=f"Страница {page['page_num']}",
                        button_text="✅ Выбрать",
                        button_callback=f"choose_page_{page['page_num']}"
                    )
                except Exception as outbox_error:
                    print(f"❌ Ошибка добавления страницы {page['page_num']} в outbox: {outbox_error}")
        
        print(f"✅ Все файлы обработаны успешно")
        print(f"🔍 ОТЛАДКА: Всего обработано файлов: {len(pages)}")
        print(f"🔍 ОТЛАДКА: Успешно сохранено файлов: {len(saved_pages)}")
        return {"success": True, "detail": f"Загружено и отправлено {len(saved_pages)} страниц"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Критическая ошибка в upload_individual_pages: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки страниц: {str(e)}")

# --- Webhook для ЮKassa ---

@app.post("/webhook/yookassa")
async def yookassa_webhook(request: Request):
    """
    Webhook для обработки уведомлений от ЮKassa
    """
    try:
        # Получаем данные webhook'а
        webhook_data = await request.json()
        
        # Логируем получение webhook'а
        print(f"🔔 Получен webhook от ЮKassa: {webhook_data}")
        
        # Обрабатываем webhook
        success = await process_payment_webhook(webhook_data)
        
        if success:
            print(f"✅ Webhook обработан успешно")
            return {"status": "success"}
        else:
            print(f"❌ Ошибка обработки webhook'а")
            raise HTTPException(status_code=400, detail="Ошибка обработки webhook'а")
            
    except Exception as e:
        print(f"❌ Ошибка обработки webhook'а ЮKassa: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")

@app.get("/admin/orders/{order_id}/photos", response_model=List[dict])
async def get_order_photos(
    order_id: int, 
    current_manager: str = Depends(get_current_manager)
):
    # Проверяем права доступа к заказу
    can_access = await can_access_order(current_manager, order_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    try:
        print(f"🔍 ОТЛАДКА: Запрос фотографий для заказа {order_id}")
        
        # Получаем все полные фотографии
        all_photos = await db.get_complete_photos()
        print(f"🔍 ОТЛАДКА: Получено {len(all_photos)} полных фотографий")
        
        # Фильтруем фотографии для конкретного заказа
        order_photos = [photo for photo in all_photos if photo.get('order_id') == order_id]
        
        print(f"✅ Найдено {len(order_photos)} фотографий для заказа {order_id}")
        print(f"🔍 ОТЛАДКА: Фотографии заказа {order_id}: {order_photos}")
        return order_photos
    except Exception as e:
        print(f"❌ Ошибка получения фотографий для заказа {order_id}: {e}")
        import traceback
        traceback.print_exc()
        # Возвращаем пустой список вместо ошибки
        return []

@app.get("/admin/orders/{order_id}/selected-content", response_model=dict)
async def get_order_selected_content(
    order_id: int, 
    current_manager: str = Depends(get_current_manager)
):
    """Получает выбранные страницы, вкладыши и свои фотографии для заказа"""
    # Проверяем права доступа к заказу
    can_access = await can_access_order(current_manager, order_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    try:
        print(f"🔍 ОТЛАДКА: Запрос выбранного контента для заказа {order_id}")
        
        # Получаем заказ
        order = await db.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Заказ не найден")
        
        order_data = json.loads(order.get('order_data', '{}'))
        
        # Получаем выбранные страницы
        selected_pages = order_data.get('selected_pages', [])
        
        # Получаем вкладыши
        inserts = order_data.get('inserts', [])
        insert_texts = order_data.get('insert_texts', {})
        
        # Получаем свои фотографии
        custom_photos = order_data.get('custom_photos', [])
        
        # Получаем фотографии обложки
        cover_photos = order_data.get('cover_photos', [])
        cover_design = order_data.get('cover_design', None)  # Может быть None, если обложка не выбрана
        
        # Получаем выбранную обложку
        selected_cover = order_data.get('selected_cover', None)
        
        # Получаем данные о первой и последней странице (из order_data и отдельных колонок)
        first_last_design = order_data.get('first_last_design', None) or order.get('first_last_design', None)
        first_page_text = order_data.get('first_page_text', None) or order.get('first_page_text', None)
        last_page_text = order_data.get('last_page_text', None) or order.get('last_page_text', None)
        
        # Формируем результат
        result = {
            "selected_pages": selected_pages,
            "pages_info": [],  # Убираем зависимость от таблицы order_pages
            "inserts": inserts,
            "insert_texts": insert_texts,
            "custom_photos": custom_photos,
            "cover_photos": cover_photos,
            "cover_design": cover_design,
            "selected_cover": selected_cover,
            "first_last_design": first_last_design,
            "first_page_text": first_page_text,
            "last_page_text": last_page_text,
            "total_selected": len(selected_pages),
            "total_inserts": len(inserts),
            "total_custom_photos": len(custom_photos)
        }
        
        print(f"✅ Получен выбранный контент для заказа {order_id}: {result}")
        return result
        
    except Exception as e:
        print(f"❌ Ошибка получения выбранного контента для заказа {order_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка получения контента: {str(e)}")

@app.get("/admin/orders/{order_id}/selected-pages-files")
async def get_selected_pages_files(
    order_id: int, 
    current_manager: str = Depends(get_current_manager)
):
    """Получает файлы выбранных страниц для заказа"""
    # Проверяем права доступа к заказу
    can_access = await can_access_order(current_manager, order_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    try:
        print(f"🔍 ОТЛАДКА: Запрос файлов выбранных страниц для заказа {order_id}")
        
        # Получаем заказ
        order = await db.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Заказ не найден")
        
        order_data = json.loads(order.get('order_data', '{}'))
        selected_pages = order_data.get('selected_pages', [])
        product = order_data.get('product', '')
        
        print(f"🔍 ОТЛАДКА: selected_pages из order_data: {selected_pages}")
        print(f"🔍 ОТЛАДКА: product из order_data: {product}")
        
        # Ищем файлы в папке uploads/order_{order_id}_pages
        import glob
        import os
        from datetime import datetime
        
        selected_pages_files = []
        # Получаем страницы из базы данных с правильной нумерацией
        from db import get_order_pages
        order_pages = await get_order_pages(order_id)
        
        print(f"🔍 ОТЛАДКА: Найдено {len(order_pages)} страниц в БД для заказа {order_id}")
        
        for page_info in order_pages:
            page_num = page_info['page_number']
            filename = page_info['filename']
            description = page_info['description']
            
            print(f"🔍 ОТЛАДКА: Проверяем страницу {page_num}: {filename}")
            
            # Добавляем только если страница выбрана
            if page_num in selected_pages:
                print(f"✅ Страница {page_num} найдена в выбранных")
                
                # Ищем файл в папке
                pages_dir = f"uploads/order_{order_id}_pages"
                file_path = os.path.join(pages_dir, filename)
                
                if os.path.exists(file_path):
                    selected_pages_files.append({
                        'page_num': page_num,
                        'filename': filename,
                        'description': description,
                        'file_path': file_path
                    })
                else:
                    print(f"❌ Файл {filename} не найден в папке {pages_dir}")
            else:
                print(f"❌ Страница {page_num} НЕ найдена в выбранных")
        
        # Сортируем по номеру страницы
        selected_pages_files.sort(key=lambda x: x['page_num'])
        
        print(f"✅ Найдено {len(selected_pages_files)} файлов выбранных страниц для заказа {order_id}")
        return selected_pages_files
        
    except Exception as e:
        print(f"❌ Ошибка получения файлов выбранных страниц для заказа {order_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка получения файлов: {str(e)}")

@app.post("/admin/orders/{order_id}/update-summary", response_model=dict)
async def update_order_summary(
    order_id: int,
    summary_data: dict,
    current_manager: str = Depends(get_current_manager)
):
    """Обновляет сводку заказа"""
    # Проверяем права доступа к заказу
    can_access = await can_access_order(current_manager, order_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    try:
        # Получаем текущий заказ
        order = await db.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Заказ не найден")
        
        # Парсим текущие данные заказа
        order_data = json.loads(order.get("order_data", "{}"))
        
        # Обновляем поля в данных заказа
        for field, value in summary_data.items():
            if value:  # Обновляем только непустые значения
                order_data[field] = value
        
        # Сохраняем обновленные данные
        await db.update_order_field(order_id, "order_data", json.dumps(order_data))
        
        return {"success": True, "detail": "Сводка заказа обновлена"}
        
    except Exception as e:
        print(f"❌ Ошибка обновления сводки заказа {order_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления сводки: {str(e)}")

@app.get("/admin/orders/{order_id}/demo-content-files")
async def get_demo_content_files(
    order_id: int, 
    current_manager: str = Depends(get_current_manager)
):
    """Получает файлы демо-контента для заказа"""
    # Проверяем права доступа к заказу
    can_access = await can_access_order(current_manager, order_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    try:
        print(f"🔍 ОТЛАДКА: Запрос файлов демо-контента для заказа {order_id}")
        
        # Получаем заказ
        order = await db.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Заказ не найден")
        
        # Получаем файлы демо-контента из базы данных
        from db import get_order_demo_content
        demo_files = await get_order_demo_content(order_id)
        
        print(f"🔍 ОТЛАДКА: demo_files из БД: {demo_files}")
        
        # Формируем результат
        demo_content_files = []
        for demo_file in demo_files:
            demo_content_files.append({
                'file_id': demo_file['id'],
                'filename': demo_file['filename'],
                'file_type': demo_file['file_type'],
                'file_path': f"uploads/order_{order_id}_{demo_file['filename']}",
                'created_at': demo_file['uploaded_at']
            })
        
        # Сортируем по дате создания
        demo_content_files.sort(key=lambda x: x['created_at'], reverse=True)
        
        print(f"✅ Найдено {len(demo_content_files)} файлов демо-контента для заказа {order_id}")
        return demo_content_files
        
    except Exception as e:
        print(f"❌ Ошибка получения файлов демо-контента для заказа {order_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка получения файлов демо-контента: {str(e)}")

@app.get("/admin/files/{file_path:path}")
async def get_protected_file(
    file_path: str,
    token: str = Query(None)
):
    """Защищенный endpoint для получения файлов"""
    # Проверяем токен
    if not token:
        raise HTTPException(status_code=401, detail="Токен не предоставлен")
    
    # Проверяем токен
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Недействительный токен")
    except JWTError:
        raise HTTPException(status_code=401, detail="Недействительный токен")
    
    try:
        # Проверяем, что файл находится в разрешенных папках
        allowed_paths = ['uploads', 'covers', 'styles', 'voices']
        if not any(file_path.startswith(allowed_path) for allowed_path in allowed_paths):
            raise HTTPException(status_code=403, detail="Доступ к файлу запрещен")
        
        # Проверяем существование файла
        full_path = file_path
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="Файл не найден")
        
        # Определяем MIME тип
        mime_type = "application/octet-stream"
        if file_path.lower().endswith(('.jpg', '.jpeg')):
            mime_type = "image/jpeg"
        elif file_path.lower().endswith('.png'):
            mime_type = "image/png"
        elif file_path.lower().endswith('.gif'):
            mime_type = "image/gif"
        elif file_path.lower().endswith('.webp'):
            mime_type = "image/webp"
        elif file_path.lower().endswith('.mp3'):
            mime_type = "audio/mpeg"
        elif file_path.lower().endswith('.mp4'):
            mime_type = "video/mp4"
        elif file_path.lower().endswith('.pdf'):
            mime_type = "application/pdf"
        
        # Возвращаем файл
        from fastapi.responses import FileResponse
        return FileResponse(full_path, media_type=mime_type)
        
    except Exception as e:
        print(f"❌ Ошибка получения файла {file_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения файла: {str(e)}")

@app.get("/admin/orders/{order_id}/download-selected-pages")
async def download_selected_pages_archive(
    order_id: int, 
    current_manager: str = Depends(get_current_manager)
):
    """Скачивает архив со всеми выбранными страницами"""
    # Проверяем права доступа к заказу
    can_access = await can_access_order(current_manager, order_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Доступ к заказу запрещен")
    
    try:
        print(f"🔍 ОТЛАДКА: Создание архива выбранных страниц для заказа {order_id}")
        
        # Импортируем необходимые модули
        import zipfile
        import io
        import os
        
        # Получаем файлы выбранных страниц напрямую из базы
        order = await db.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Заказ не найден")
        
        order_data = json.loads(order.get('order_data', '{}'))
        selected_pages = order_data.get('selected_pages', [])
        
        # Получаем страницы из базы данных
        order_pages = await get_order_pages(order_id)
        
        selected_pages_files = []
        for page_info in order_pages:
            page_num = page_info['page_number']
            if page_num in selected_pages:
                pages_dir = f"uploads/order_{order_id}_pages"
                file_path = os.path.join(pages_dir, page_info['filename'])
                if os.path.exists(file_path):
                    selected_pages_files.append({
                        'page_num': page_num,
                        'filename': page_info['filename'],
                        'description': page_info['description'],
                        'file_path': file_path
                    })
        
        files_response = selected_pages_files
        if not files_response:
            raise HTTPException(status_code=404, detail="Файлы выбранных страниц не найдены")
        
        # Создаем архив в памяти
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for page_file in files_response:
                file_path = page_file['file_path']
                if os.path.exists(file_path):
                    # Добавляем файл в архив с понятным именем
                    archive_name = f"Страница_{page_file['page_num']}_{page_file['filename']}"
                    zip_file.write(file_path, archive_name)
                    print(f"✅ Добавлен в архив: {archive_name}")
                else:
                    print(f"⚠️ Файл не найден: {file_path}")
        
        # Подготавливаем ответ
        zip_buffer.seek(0)
        
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            io.BytesIO(zip_buffer.getvalue()),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=selected_pages_order_{order_id}.zip"
            }
        )
        
    except Exception as e:
        print(f"❌ Ошибка создания архива для заказа {order_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка создания архива: {str(e)}")

# --- Обработчик статических файлов ---

@app.get("/uploads/{filename:path}")
async def serve_upload_file(filename: str):
    """Обрабатывает запросы к статическим файлам в папке uploads"""
    try:
        file_path = os.path.join("uploads", filename)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        else:
            raise HTTPException(status_code=404, detail="Файл не найден")
    except Exception as e:
        print(f"❌ Ошибка при обработке файла {filename}: {e}")
        raise HTTPException(status_code=404, detail="Файл не найден")

@app.get("/covers/{filename:path}")
async def serve_cover_file(filename: str):
    """Обрабатывает запросы к статическим файлам в папке covers"""
    try:
        file_path = os.path.join("covers", filename)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        else:
            raise HTTPException(status_code=404, detail="Файл не найден")
    except Exception as e:
        print(f"❌ Ошибка при обработке файла {filename}: {e}")
        raise HTTPException(status_code=404, detail="Файл не найден")

# --- API для работы с шаблоном сводки заказа ---

@app.get("/admin/order-summary-template", response_model=dict)
async def get_order_summary_template(current_manager: str = Depends(get_super_admin)):
    """Получает шаблон сводки заказа (только для главного админа)"""
    try:
        # Возвращаем дефолтные значения для шаблона (названия полей)
        template = {
            "gender_label": "Пол отправителя",
            "recipient_name_label": "Имя получателя",
            "gift_reason_label": "Повод",
            "relation_label": "Отношение",
            "style_label": "Стиль",
            "format_label": "Формат",
            "sender_name_label": "От кого",
            "song_gender_label": "Пол отправителя",
            "song_recipient_name_label": "Имя получателя",
            "song_gift_reason_label": "Повод",
            "song_relation_label": "Отношение",
            "song_style_label": "Стиль",
            "song_voice_label": "Голос"
        }
        return template
    except Exception as e:
        print(f"❌ Ошибка получения шаблона сводки заказа: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения шаблона: {str(e)}")

@app.post("/admin/order-summary-template", response_model=dict)
async def update_order_summary_template(
    template_data: dict,
    current_manager: str = Depends(get_super_admin)
):
    """Обновляет шаблон сводки заказа (только для главного админа)"""
    try:
        # Здесь можно сохранить шаблон в базу данных или файл
        # Пока просто возвращаем успех
        print(f"📋 Обновлен шаблон сводки заказа менеджером {current_manager}: {template_data}")
        return {"success": True, "detail": "Шаблон сводки заказа обновлен"}
    except Exception as e:
        print(f"❌ Ошибка обновления шаблона сводки заказа: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления шаблона: {str(e)}")

# --- API для метрик ---

@app.get("/admin/metrics")
async def get_metrics(
    start_date: str = Query(..., description="Дата начала в формате YYYY-MM-DD"),
    end_date: str = Query(..., description="Дата окончания в формате YYYY-MM-DD"),
    current_manager: str = Depends(get_current_manager)
):
    """Получает метрики за указанный период"""
    try:
        import aiosqlite
        DB_PATH = 'bookai.db'
        # Получаем основные метрики заказов
        orders = await get_orders_filtered_with_permissions(current_manager)
        
        # Фильтруем заказы по дате (в московском времени)
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        # Конвертируем в московское время
        start_dt = MSK_TZ.localize(start_dt)
        end_dt = MSK_TZ.localize(end_dt).replace(hour=23, minute=59, second=59)
        
        filtered_orders = []
        for order in orders:
            # Парсим дату создания заказа и конвертируем в московское время
            order_created_str = order['created_at']
            if 'T' in order_created_str:
                order_date = datetime.fromisoformat(order_created_str.replace('Z', '+00:00'))
            else:
                order_date = datetime.strptime(order_created_str, "%Y-%m-%d %H:%M:%S")
                if order_date.tzinfo is None:
                    order_date = pytz.UTC.localize(order_date)
            
            # Конвертируем в московское время
            order_date_msk = order_date.astimezone(MSK_TZ)
            
            if start_dt <= order_date_msk <= end_dt:
                filtered_orders.append(order)
        
        # Подсчитываем основные метрики - используем данные из базы
        total_orders = len(filtered_orders)  # Пока используем отфильтрованные заказы
        
        # ОТЛАДКА: Проверяем статусы в отфильтрованных заказах
        status_counts = {}
        for order in filtered_orders:
            status = order.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"🔍 ОТЛАДКА метрик: всего заказов {total_orders}")
        print(f"🔍 ОТЛАДКА метрик: статусы в отфильтрованных заказах: {status_counts}")
        
        # Считаем оплаченные заказы и общее количество напрямую из базы (без фильтрации по правам доступа)
        async with aiosqlite.connect(DB_PATH) as db:
            # Сначала считаем все заказы за период
            async with db.execute('''
                SELECT COUNT(*) as total_count, GROUP_CONCAT(status) as all_statuses
                FROM orders 
                WHERE DATE(created_at) BETWEEN ? AND ?
            ''', (start_date, end_date)) as cursor:
                result = await cursor.fetchone()
                total_orders = result[0] if result else 0
                all_statuses = result[1] if result else ""
            
            print(f"🔍 ОТЛАДКА: Все заказы из базы: {total_orders}, статусы: {all_statuses}")
            
            # Считаем оплаченные заказы ПО СТАТУСАМ (как в аналитике)
            status_placeholders = ','.join(['?' for _ in PAID_ORDER_STATUSES])
            async with db.execute(f'''
                SELECT COUNT(*) as paid_count
                FROM orders o
                WHERE o.status IN ({status_placeholders})
                AND DATE(o.created_at) BETWEEN ? AND ?
            ''', (*PAID_ORDER_STATUSES, start_date, end_date)) as cursor:
                result = await cursor.fetchone()
                paid_orders = result[0] if result else 0
            
            print(f"🔍 ОТЛАДКА: Оплаченные заказы (по статусам): {paid_orders}")
            
            # Дополнительная проверка: посмотрим на все заказы с их статусами
            async with db.execute('''
                SELECT id, status, created_at, order_data
                FROM orders 
                WHERE DATE(created_at) BETWEEN ? AND ?
                ORDER BY created_at DESC
            ''', (start_date, end_date)) as cursor:
                all_orders = await cursor.fetchall()
                print(f"🔍 ОТЛАДКА: Детали всех заказов за период:")
                for order in all_orders:
                    order_data_preview = order[3][:50] + "..." if order[3] and len(order[3]) > 50 else (order[3] or "нет данных")
                    print(f"  Заказ {order[0]}: статус={order[1]}, дата={order[2]}, order_data={order_data_preview}")
            
            # Специально ищем заказ #10
            async with db.execute('''
                SELECT id, status, created_at, order_data
                FROM orders 
                WHERE id = 10
            ''') as cursor:
                order_10 = await cursor.fetchone()
                if order_10:
                    print(f"🔍 ОТЛАДКА: Заказ #10 найден: статус={order_10[1]}, дата={order_10[2]}, order_data={order_10[3][:100] if order_10[3] else 'нет данных'}...")
                    
                    # Проверяем, попадает ли заказ #10 в период дат
                    order_date = order_10[2]
                    print(f"🔍 ОТЛАДКА: Заказ #10 дата: {order_date}")
                    print(f"🔍 ОТЛАДКА: Период запроса: {start_date} - {end_date}")
                    
                    # Проверяем, есть ли заказ #10 в списке всех заказов за период
                    order_10_in_period = any(order[0] == 10 for order in all_orders)
                    print(f"🔍 ОТЛАДКА: Заказ #10 в периоде: {order_10_in_period}")
                    
                    # Проверяем статус заказа #10
                    if order_10[1] in ['paid', 'upsell_paid', 'waiting_draft', 'draft_sent', 'editing', 'ready', 'delivered', 'completed', 'waiting_plot_options', 'plot_selected', 'waiting_final_version', 'waiting_story_options']:
                        print(f"🔍 ОТЛАДКА: Заказ #10 имеет статус 'оплачен': {order_10[1]}")
                    else:
                        print(f"🔍 ОТЛАДКА: Заказ #10 НЕ имеет статус 'оплачен': {order_10[1]}")
                        
                    # Проверяем тип продукта в заказе #10
                    if order_10[3]:
                        order_data = order_10[3]
                        if '"product": "Книга"' in order_data or '"product": "\\u041a\\u043d\\u0438\\u0433\\u0430"' in order_data:
                            print(f"🔍 ОТЛАДКА: Заказ #10 содержит 'Книга' в order_data")
                        else:
                            print(f"🔍 ОТЛАДКА: Заказ #10 НЕ содержит 'Книга' в order_data")
                else:
                    print(f"🔍 ОТЛАДКА: Заказ #10 не найден в базе данных")
            
            # Ищем все заказы с книгами в базе данных
            async with db.execute('''
                SELECT id, status, created_at, order_data
                FROM orders 
                WHERE order_data LIKE '%"product": "Книга"%' 
                   OR order_data LIKE '%"product": "\\u041a\\u043d\\u0438\\u0433\\u0430"%'
                ORDER BY id
            ''') as cursor:
                book_orders = await cursor.fetchall()
                print(f"🔍 ОТЛАДКА: Все заказы с книгами в базе данных:")
                for order in book_orders:
                    order_data_preview = order[3][:50] + "..." if order[3] and len(order[3]) > 50 else (order[3] or "нет данных")
                    print(f"  Заказ {order[0]}: статус={order[1]}, дата={order[2]}, order_data={order_data_preview}")
            
            # Ищем все заказы с книгами в выбранном периоде
            async with db.execute('''
                SELECT id, status, created_at, order_data
                FROM orders 
                WHERE (order_data LIKE '%"product": "Книга"%' 
                   OR order_data LIKE '%"product": "\\u041a\\u043d\\u0438\\u0433\\u0430"%')
                AND DATE(created_at) BETWEEN ? AND ?
                ORDER BY id
            ''', (start_date, end_date)) as cursor:
                book_orders_in_period = await cursor.fetchall()
                print(f"🔍 ОТЛАДКА: Заказы с книгами в периоде {start_date} - {end_date}:")
                for order in book_orders_in_period:
                    order_data_preview = order[3][:50] + "..." if order[3] and len(order[3]) > 50 else (order[3] or "нет данных")
                    print(f"  Заказ {order[0]}: статус={order[1]}, дата={order[2]}, order_data={order_data_preview}")
        
        # Доплаты (заказы с событием upsell_purchased)
        upsell_orders = 0
        for order in filtered_orders:
            if await check_order_has_upsell(order['id']):
                upsell_orders += 1
        
        # Завершенные заказы (готовые, доставленные, завершенные)
        # Включаем 'ready' как завершенные, так как это финальная версия
        completed_orders = len([o for o in filtered_orders if o['status'] in ['ready', 'delivered', 'completed']])
        
        print(f"🔍 ОТЛАДКА метрик: оплаченных {paid_orders}, доплат {upsell_orders}, завершенных {completed_orders}")
        
        # Заказы в работе (все кроме завершенных)
        pending_orders = len([o for o in filtered_orders if o['status'] not in ['ready', 'delivered', 'completed']])
        
        # Получаем метрики из трекинга событий
        funnel_metrics = await get_funnel_metrics(start_date, end_date)
        abandonment_metrics = await get_abandonment_metrics(start_date, end_date)
        revenue_metrics = await get_revenue_metrics(start_date, end_date)
        detailed_revenue_metrics = await get_detailed_revenue_metrics(start_date, end_date)
        
        # Подсчитываем выручку из revenue_metrics
        total_revenue = 0
        main_revenue = 0
        if revenue_metrics:
            main_revenue = revenue_metrics.get('main_purchases', {}).get('revenue', 0) or 0
            upsell_revenue = revenue_metrics.get('upsells', {}).get('revenue', 0) or 0
            total_revenue = main_revenue + upsell_revenue
        
        # Если нет данных в revenue_metrics, считаем из заказов
        if total_revenue == 0:
            total_revenue = sum([float(o.get('total_amount', 0)) for o in filtered_orders if o.get('total_amount')])
            main_revenue = total_revenue  # В этом случае считаем все как основную выручку
        
        # Средний чек должен считаться только по основным оплаченным заказам (БЕЗ допродаж)
        average_order_value = main_revenue / paid_orders if paid_orders > 0 else 0
        
        # Статистика по статусам
        orders_by_status = {}
        for order in filtered_orders:
            status = order['status']
            orders_by_status[status] = orders_by_status.get(status, 0) + 1
        
        # Статистика по продуктам (используем детализированные метрики)
        orders_by_product = {}
        if detailed_revenue_metrics:
            orders_by_product = {
                'Книга (общее)': detailed_revenue_metrics.get('Книга (общее)', {}).get('count', 0),
                'Книга печатная': detailed_revenue_metrics.get('Книга печатная', {}).get('count', 0),
                'Книга электронная': detailed_revenue_metrics.get('Книга электронная', {}).get('count', 0),
                'Песня (общее)': detailed_revenue_metrics.get('Песня (общее)', {}).get('count', 0),
                'Песня': detailed_revenue_metrics.get('Песня', {}).get('count', 0)
            }
        else:
            # Fallback на старую логику
            for order in filtered_orders:
                product = order.get('product_type', order.get('product', 'Неизвестно'))
                orders_by_product[product] = orders_by_product.get(product, 0) + 1
        
        # Получаем топ менеджеров
        managers = await get_managers()
        top_managers = []
        for manager in managers:
            # Фильтруем заказы по assigned_manager_id и только оплаченные
            manager_orders = [o for o in filtered_orders if o.get('assigned_manager_id') == manager['id'] and o.get('status') in PAID_ORDER_STATUSES]
            
            # Получаем ID заказов менеджера
            order_ids = [o.get('id') for o in manager_orders if o.get('id')]
            
            # Выручка по основным покупкам (БЕЗ допродаж)
            manager_main_revenue = 0
            manager_upsell_revenue = 0
            
            if order_ids:
                import aiosqlite
                placeholders = ','.join(['?'] * len(order_ids))
                
                async with aiosqlite.connect(DB_PATH) as db:
                    # Получаем начальные суммы покупок из event_metrics (для заказов с допродажами)
                    initial_amounts_query = f'''
                        SELECT 
                            order_id,
                            MIN(amount) as initial_amount
                        FROM event_metrics
                        WHERE event_type = 'purchase_completed'
                        AND order_id IN ({placeholders})
                        AND amount IS NOT NULL
                        AND amount > 0
                        GROUP BY order_id
                    '''
                    async with db.execute(initial_amounts_query, order_ids) as cursor:
                        initial_rows = await cursor.fetchall()
                        initial_amounts = {row[0]: row[1] for row in initial_rows}
                    
                    # Получаем ID заказов с допродажами
                    upsell_order_ids_query = f'''
                        SELECT DISTINCT order_id
                        FROM event_metrics
                        WHERE event_type = 'upsell_purchased'
                        AND order_id IN ({placeholders})
                    '''
                    async with db.execute(upsell_order_ids_query, order_ids) as cursor:
                        upsell_rows = await cursor.fetchall()
                        upsell_order_ids = {row[0] for row in upsell_rows}
                    
                    # Выручка по основным покупкам (ДЛЯ ВСЕХ заказов)
                    for order in manager_orders:
                        order_id = order.get('id')
                        if not order_id:
                            continue
                        
                        # Сначала пытаемся получить сумму из events (приоритет)
                        event_amount = initial_amounts.get(order_id, 0)
                        total_amount = float(order.get('total_amount', 0)) if order.get('total_amount') else 0
                        
                        # Для заказов с допродажами берем ТОЛЬКО начальную сумму из events
                        if order_id in upsell_order_ids:
                            if event_amount > 0:
                                manager_main_revenue += event_amount
                                if manager['email'] == 'kamillakamilevna24@gmail.com':
                                    print(f"🔍 Order #{order_id} (upsell): event_amount={event_amount}, total_amount={total_amount}")
                            elif total_amount > 0:
                                # Если в events нет данных, берем из total_amount
                                manager_main_revenue += total_amount
                                if manager['email'] == 'kamillakamilevna24@gmail.com':
                                    print(f"🔍 Order #{order_id} (upsell, no events): total_amount={total_amount}")
                        # Для заказов без допродаж приоритет events, потом total_amount
                        else:
                            if event_amount > 0:
                                manager_main_revenue += event_amount
                                if manager['email'] == 'kamillakamilevna24@gmail.com':
                                    print(f"🔍 Order #{order_id} (regular from events): event_amount={event_amount}, total_amount={total_amount}")
                            elif total_amount > 0:
                                manager_main_revenue += total_amount
                                if manager['email'] == 'kamillakamilevna24@gmail.com':
                                    print(f"🔍 Order #{order_id} (regular from total): total_amount={total_amount}")
                            else:
                                if manager['email'] == 'kamillakamilevna24@gmail.com':
                                    print(f"⚠️ Order #{order_id}: NO AMOUNT! event_amount=0, total_amount=0")
                    
                    # Выручка по допродажам из event_metrics
                    query = f'''
                        SELECT COALESCE(SUM(amount), 0) as upsell_sum
                        FROM event_metrics
                        WHERE event_type = 'upsell_purchased'
                        AND order_id IN ({placeholders})
                        AND DATE(timestamp) BETWEEN ? AND ?
                        AND amount IS NOT NULL
                        AND amount > 0
                    '''
                    args = (*order_ids, start_date, end_date)
                    async with db.execute(query, args) as cursor:
                        row = await cursor.fetchone()
                        if row and row[0] is not None:
                            manager_upsell_revenue = float(row[0])
            
            total_manager_revenue = manager_main_revenue + manager_upsell_revenue
            
            if manager['email'] == 'kamillakamilevna24@gmail.com':
                print(f"📊 Камилла: orders={len(manager_orders)}, main_revenue={manager_main_revenue}, upsell_revenue={manager_upsell_revenue}, total={total_manager_revenue}")
            
            top_managers.append({
                'name': manager.get('full_name', manager.get('email', 'Неизвестно')),
                'email': manager['email'],
                'ordersCount': len(manager_orders),
                'revenue': total_manager_revenue
            })
        
        # Сортируем менеджеров по выручке
        top_managers.sort(key=lambda x: x['revenue'], reverse=True)
        
        # Дополнительные метрики
        unique_users = funnel_metrics.get('funnel_data', {}).get('bot_entry', 0)
        conversions = funnel_metrics.get('conversions', {})
        
        # Детальные метрики по продуктам
        # Получаем реальные данные о выборах книги и песни
        async with aiosqlite.connect(DB_PATH) as db:
            # Общее количество уникальных пользователей, выбравших любой продукт
            async with db.execute('''
                SELECT COUNT(DISTINCT user_id) as total_unique_users
                FROM event_metrics 
                WHERE event_type = 'product_selected' 
                AND timestamp BETWEEN ? AND ?
            ''', (start_date, end_date)) as cursor:
                total_result = await cursor.fetchone()
                total_unique_users = total_result[0] if total_result and total_result[0] is not None else 0
            
            # Выборы книги (общее количество заказов с книгами)
            async with db.execute('''
                SELECT COUNT(*) as total_orders
                FROM orders 
                WHERE (order_data LIKE '%"product": "Книга"%' 
                   OR order_data LIKE '%"product": "\\u041a\\u043d\\u0438\\u0433\\u0430"%')
                AND DATE(created_at) BETWEEN ? AND ?
            ''', (start_date, end_date)) as cursor:
                book_result = await cursor.fetchone()
                book_selections = book_result[0] if book_result and book_result[0] is not None else 0
            
            print(f"🔍 ОТЛАДКА: Выборы книги: {book_selections}")
            
            # Выборы песни (общее количество заказов с песнями)
            async with db.execute('''
                SELECT COUNT(*) as total_orders
                FROM orders 
                WHERE (order_data LIKE '%"product": "Песня"%' 
                   OR order_data LIKE '%"product": "\\u041f\\u0435\\u0441\\u043d\\u044f"%')
                AND DATE(created_at) BETWEEN ? AND ?
            ''', (start_date, end_date)) as cursor:
                song_result = await cursor.fetchone()
                song_selections = song_result[0] if song_result and song_result[0] is not None else 0
            
            print(f"🔍 ОТЛАДКА: Выборы песни: {song_selections}")
            # Сначала посмотрим на все оплаченные заказы и их order_data (включаем все статусы после оплаты)
            status_placeholders = ','.join(['?' for _ in PAID_ORDER_STATUSES])
            async with db.execute(f'''
                SELECT id, status, order_data, total_amount,
                       (SELECT COUNT(*) FROM payments p WHERE p.order_id = o.id AND p.status = 'succeeded') as payment_count,
                       (SELECT COUNT(*) FROM event_metrics em WHERE em.order_id = o.id AND em.event_type = 'upsell_purchased') as is_upsell
                FROM orders o
                WHERE status IN ({status_placeholders})
                AND DATE(created_at) BETWEEN ? AND ?
                AND order_data IS NOT NULL AND order_data != ""
            ''', (*PAID_ORDER_STATUSES, start_date, end_date)) as cursor:
                all_paid_orders = await cursor.fetchall()
                print(f"🔍 ОТЛАДКА: Всего оплаченных заказов с order_data: {len(all_paid_orders)}")
                for order in all_paid_orders:
                    print(f"  Заказ {order[0]}: статус={order[1]}, order_data={order[2][:100]}...")
            
            # Покупки книги - используем детализированные метрики
            # Они уже правильно учитывают заказы с доплатами (берут начальную сумму)
            book_purchases = (
                detailed_revenue_metrics.get('Книга печатная', {}).get('count', 0) +
                detailed_revenue_metrics.get('Книга электронная', {}).get('count', 0)
            )
            
            print(f"🔍 ОТЛАДКА: Покупки книги (из детализированных метрик): {book_purchases}")
            
            # Подсчёт печатных и электронных книг - используем детализированные метрики
            print_book_purchases = detailed_revenue_metrics.get('Книга печатная', {}).get('count', 0)
            electronic_book_purchases = detailed_revenue_metrics.get('Книга электронная', {}).get('count', 0)
            
            print(f"🔍 ОТЛАДКА: Печатных книг: {print_book_purchases}, Электронных книг: {electronic_book_purchases}")
            
            # ОТЛАДКА: Показываем ВСЕ заказы книг (включая те, что не попали в подсчёт)
            async with db.execute('''
                SELECT o.id, o.status, o.order_data, o.total_amount,
                       (SELECT COUNT(*) FROM payments p WHERE p.order_id = o.id AND p.status = 'succeeded') as payment_count,
                       (SELECT COUNT(*) FROM event_metrics em WHERE em.order_id = o.id AND em.event_type = 'upsell_purchased') as is_upsell
                FROM orders o
                WHERE DATE(o.created_at) BETWEEN ? AND ?
                AND (
                    o.order_data LIKE '%"product": "Книга"%' 
                    OR o.order_data LIKE '%"product":"Книга"%'
                    OR o.order_data LIKE '%"product": "\\u041a\\u043d\\u0438\\u0433\\u0430"%'
                    OR o.order_data LIKE '%"product":"\\u041a\\u043d\\u0438\\u0433\\u0430"%'
                    OR o.order_data LIKE '%Книга%'
                )
                ORDER BY o.id
            ''', (start_date, end_date)) as cursor:
                all_book_orders = await cursor.fetchall()
                print(f"🔍 ОТЛАДКА: ВСЕ заказы книг за период ({len(all_book_orders)} шт.):")
                for order in all_book_orders:
                    order_id, status, order_data_str, total_amount, payment_count, is_upsell = order
                    # Проверяем, учитывается ли заказ (оплачен И НЕ является допродажей)
                    is_paid = status in PAID_ORDER_STATUSES
                    is_counted = is_paid and is_upsell == 0
                    counted_mark = "✅ УЧТЁН" if is_counted else "❌ НЕ УЧТЁН"
                    upsell_mark = " [ДОПРОДАЖА]" if is_upsell > 0 else ""
                    payment_info = f", платежей: {payment_count}, сумма: {total_amount}₽" if payment_count > 0 or total_amount else ""
                    print(f"  Заказ #{order_id}: статус='{status}' {counted_mark}{upsell_mark}{payment_info}")
            
            # Покупки песни - используем детализированные метрики
            song_purchases = detailed_revenue_metrics.get('Песня', {}).get('count', 0)
            
            print(f"🔍 ОТЛАДКА: Покупки песни (из детализированных метрик): {song_purchases}")
            
            # Также проверим все заказы с order_data для отладки
            async with db.execute('''
                SELECT id, status, order_data
                FROM orders 
                WHERE DATE(created_at) BETWEEN ? AND ?
                AND order_data IS NOT NULL AND order_data != ""
                LIMIT 5
            ''', (start_date, end_date)) as cursor:
                sample_orders = await cursor.fetchall()
                print(f"🔍 ОТЛАДКА: Примеры заказов с order_data: {sample_orders}")
            
            # Подсчет уникальных пользователей для книг и песен отдельно
            async with db.execute(f'''
                SELECT COUNT(DISTINCT user_id) as unique_book_users
                FROM orders
                WHERE status IN ({status_placeholders})
                AND DATE(created_at) BETWEEN ? AND ?
                AND (
                    order_data LIKE '%"product": "Книга"%' 
                    OR order_data LIKE '%"product":"Книга"%'
                    OR order_data LIKE '%"product": "\\u041a\\u043d\\u0438\\u0433\\u0430"%'
                    OR order_data LIKE '%"product":"\\u041a\\u043d\\u0438\\u0433\\u0430"%'
                )
                AND id NOT IN (
                    SELECT order_id FROM event_metrics 
                    WHERE event_type = 'upsell_purchased'
                )
            ''', (*PAID_ORDER_STATUSES, start_date, end_date)) as cursor:
                row = await cursor.fetchone()
                unique_book_purchasers = row[0] if row else 0
            
            async with db.execute(f'''
                SELECT COUNT(DISTINCT user_id) as unique_song_users
                FROM orders
                WHERE status IN ({status_placeholders})
                AND DATE(created_at) BETWEEN ? AND ?
                AND (
                    order_data LIKE '%"product": "Песня"%' 
                    OR order_data LIKE '%"product":"Песня"%'
                    OR order_data LIKE '%"product": "\\u041f\\u0435\\u0441\\u043d\\u044f"%'
                    OR order_data LIKE '%"product":"\\u041f\\u0435\\u0441\\u043d\\u044f"%'
                )
                AND id NOT IN (
                    SELECT order_id FROM event_metrics 
                    WHERE event_type = 'upsell_purchased'
                )
            ''', (*PAID_ORDER_STATUSES, start_date, end_date)) as cursor:
                row = await cursor.fetchone()
                unique_song_purchasers = row[0] if row else 0
            
            # Подсчет уникальных пользователей с допродажами
            async with db.execute('''
                SELECT COUNT(DISTINCT user_id) as unique_upsell_users
                FROM event_metrics
                WHERE event_type = 'upsell_purchased'
                AND DATE(timestamp) BETWEEN ? AND ?
                AND order_id IS NOT NULL
            ''', (start_date, end_date)) as cursor:
                row = await cursor.fetchone()
                unique_upsell_purchasers = row[0] if row else 0
        
        # ОТЛАДКА: Выводим финальные значения перед отправкой
        print(f"🔍 ОТЛАДКА ФИНАЛЬНЫЕ ЗНАЧЕНИЯ:")
        print(f"  totalOrders: {total_orders}")
        print(f"  paidOrders: {paid_orders}")
        print(f"  bookPurchases: {book_purchases} (уникальных: {unique_book_purchasers})")
        print(f"  printBookPurchases: {print_book_purchases}")
        print(f"  electronicBookPurchases: {electronic_book_purchases}")
        print(f"  songPurchases: {song_purchases} (уникальных: {unique_song_purchasers})")
        print(f"  upsellOrders: {upsell_orders} (уникальных: {unique_upsell_purchasers})")
        print(f"  totalUniqueUsers: {total_unique_users}")
        
        return {
            'totalOrders': total_orders,
            'paidOrders': paid_orders,
            'upsellOrders': upsell_orders,
            'completedOrders': completed_orders,
            'pendingOrders': pending_orders,
            'totalRevenue': total_revenue,
            'averageOrderValue': average_order_value,
            'ordersByStatus': orders_by_status,
            'ordersByProduct': orders_by_product,
            'ordersByMonth': {},  # Можно добавить позже
            'conversionRate': conversions.get('purchase_rate', 0),
            'topManagers': top_managers,
            'funnelMetrics': funnel_metrics,
            'abandonmentMetrics': abandonment_metrics,
            'revenueMetrics': revenue_metrics,
            'detailedRevenueMetrics': detailed_revenue_metrics,
            'uniqueUsers': unique_users,
            'startRate': conversions.get('start_rate', 0),
            'productSelectionRate': conversions.get('product_selection_rate', 0),
            'orderCreationRate': conversions.get('order_creation_rate', 0),
            'purchaseRate': conversions.get('purchase_rate', 0),
            'bookSelections': book_selections,
            'songSelections': song_selections,
            'bookPurchases': book_purchases,
            'printBookPurchases': print_book_purchases,
            'electronicBookPurchases': electronic_book_purchases,
            'songPurchases': song_purchases,
            'uniqueBookPurchasers': unique_book_purchasers,  # Уникальные покупатели книг
            'uniqueSongPurchasers': unique_song_purchasers,  # Уникальные покупатели песен
            'uniqueUpsellPurchasers': unique_upsell_purchasers,  # Уникальные покупатели допродаж
            'totalUniqueUsers': total_unique_users  # Общее количество уникальных пользователей
        }
        
    except Exception as e:
        import traceback
        print(f"❌ Ошибка получения метрик: {e}")
        print(f"❌ Полный traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения метрик: {str(e)}")
@app.get("/admin/analytics")
async def get_analytics(
    start_date: str = Query(..., description="Дата начала в формате YYYY-MM-DD"),
    end_date: str = Query(..., description="Дата окончания в формате YYYY-MM-DD"),
    source: str = Query(None, description="Фильтр по источнику"),
    product_type: str = Query(None, description="Фильтр по типу продукта"),
    purchase_status: str = Query(None, description="Фильтр по статусу покупки"),
    upsell_status: str = Query(None, description="Фильтр по статусу допродажи"),
    progress: str = Query(None, description="Фильтр по прогрессу"),
    utm_source: str = Query(None, description="Фильтр по UTM source"),
    utm_medium: str = Query(None, description="Фильтр по UTM medium"),
    utm_campaign: str = Query(None, description="Фильтр по UTM campaign"),
    search: str = Query(None, description="Поиск по тексту"),
    current_manager: str = Depends(get_current_manager)
):
    """Получает аналитические данные с фильтрацией"""
    try:
        # Получаем все заказы без фильтрации по правам доступа
        orders = await get_orders_filtered()
        
        # Фильтруем по дате (в московском времени)
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        # Конвертируем в московское время
        start_dt = MSK_TZ.localize(start_dt)
        end_dt = MSK_TZ.localize(end_dt).replace(hour=23, minute=59, second=59)
        
        filtered_orders = []
        upsell_orders_before_date_filter = 0
        for order in orders:
            if order.get('status') == 'upsell_paid':
                upsell_orders_before_date_filter += 1
            
            # Парсим дату создания заказа и конвертируем в московское время
            order_created_str = order['created_at']
            if 'T' in order_created_str:
                order_date = datetime.fromisoformat(order_created_str.replace('Z', '+00:00'))
            else:
                order_date = datetime.strptime(order_created_str, "%Y-%m-%d %H:%M:%S")
                if order_date.tzinfo is None:
                    order_date = pytz.UTC.localize(order_date)
            
            # Конвертируем в московское время
            order_date_msk = order_date.astimezone(MSK_TZ)
            
            if start_dt <= order_date_msk <= end_dt:
                filtered_orders.append(order)
        
        print(f"🔍 ОТЛАДКА: Заказов upsell_paid до фильтрации по дате: {upsell_orders_before_date_filter}")
        print(f"🔍 ОТЛАДКА: Диапазон дат: {start_date} - {end_date}")
        
        # Применяем дополнительные фильтры
        if source and source.strip():
            source_lower = source.lower()
            # Фильтруем по источнику, получая его из event_metrics
            from db import get_order_source
            temp_orders = []
            for order in filtered_orders:
                order_source = await get_order_source(order.get('id'))
                if order_source.lower() == source_lower:
                    temp_orders.append(order)
            filtered_orders = temp_orders
        
        if product_type and product_type.strip():
            product_type_lower = product_type.lower()
            temp_orders = []
            for order in filtered_orders:
                order_product_type = await get_order_product_type(order.get('id'))
                # Проверяем совпадение: для "Книга" ищем "Книга"
                if product_type_lower == 'книга':
                    # Если выбрана общая "Книга", включаем все заказы с типом "Книга"
                    if order_product_type.lower() == 'книга':
                        temp_orders.append(order)
                elif order_product_type.lower() == product_type_lower:
                    # Для остальных фильтров - точное совпадение
                    temp_orders.append(order)
            filtered_orders = temp_orders
        
        if purchase_status and purchase_status.strip():
            # Фильтруем по статусу покупки на основе поля status
            temp_orders = []
            for order in filtered_orders:
                order_status = order.get('status', '')
                if order_status in PAID_ORDER_STATUSES:
                    order_purchase_status = 'Оплачен'
                elif order_status in ['waiting_payment', 'payment_pending', 'payment_created', 'upsell_payment_created', 'upsell_payment_pending']:
                    order_purchase_status = 'Ждет оплаты'
                else:
                    order_purchase_status = 'Не оплачен'
                
                if order_purchase_status == purchase_status:
                    temp_orders.append(order)
            filtered_orders = temp_orders
        
        if upsell_status and upsell_status.strip():
            # Фильтруем по статусу допродажи на основе события upsell_purchased
            temp_orders = []
            for order in filtered_orders:
                has_upsell = await check_order_has_upsell(order['id'])
                order_upsell_status = 'Оплачен' if has_upsell else 'Не оплачен'
                
                if order_upsell_status == upsell_status:
                    temp_orders.append(order)
            filtered_orders = temp_orders
        
        if progress and progress.strip():
            # Фильтруем по прогрессу, определяя его на основе статуса и типа продукта
            temp_orders = []
            for order in filtered_orders:
                order_status = order.get('status', '')
                product_type = order.get('product_type', order.get('product', ''))
                
                # Определяем прогресс на основе статуса и типа продукта
                order_progress = get_order_progress_status(order_status, product_type)
                
                # Специальная обработка для "Завершено" - включаем все завершенные статусы
                if progress == 'Завершено':
                    if order_status in ['ready', 'delivered', 'completed', 'upsell_paid']:
                        temp_orders.append(order)
                elif progress in order_progress:
                    temp_orders.append(order)
            filtered_orders = temp_orders
        
        # Фильтрация по UTM-параметрам
        if utm_source and utm_source.strip():
            from db import get_order_utm_data
            temp_orders = []
            for order in filtered_orders:
                utm_data = await get_order_utm_data(order.get('id'))
                if utm_data['utm_source'].lower() == utm_source.lower():
                    temp_orders.append(order)
            filtered_orders = temp_orders
        
        if utm_medium and utm_medium.strip():
            from db import get_order_utm_data
            temp_orders = []
            for order in filtered_orders:
                utm_data = await get_order_utm_data(order.get('id'))
                if utm_data['utm_medium'].lower() == utm_medium.lower():
                    temp_orders.append(order)
            filtered_orders = temp_orders
        
        if utm_campaign and utm_campaign.strip():
            from db import get_order_utm_data
            temp_orders = []
            for order in filtered_orders:
                utm_data = await get_order_utm_data(order.get('id'))
                if utm_data['utm_campaign'].lower() == utm_campaign.lower():
                    temp_orders.append(order)
            filtered_orders = temp_orders
        
        if search and search.strip():
            search_lower = search.lower()
            filtered_orders = [o for o in filtered_orders if 
                             search_lower in (o.get('username') or '').lower() or
                             search_lower in str(o.get('id') or '').lower() or
                             search_lower in (o.get('created_at') or '').lower()]
        
        # ОТЛАДКА: Проверяем статусы в аналитике
        analytics_status_counts = {}
        upsell_orders_found = 0
        for order in filtered_orders:
            status = order.get('status', 'unknown')
            analytics_status_counts[status] = analytics_status_counts.get(status, 0) + 1
            if status == 'upsell_paid':
                upsell_orders_found += 1
        
        print(f"🔍 ОТЛАДКА аналитики: всего заказов {len(filtered_orders)}")
        print(f"🔍 ОТЛАДКА аналитики: статусы в отфильтрованных заказах: {analytics_status_counts}")
        print(f"🔍 ОТЛАДКА аналитики: найдено заказов upsell_paid: {upsell_orders_found}")
        
        # Формируем ответ
        analytics_data = []
        for order in filtered_orders:
            # Определяем статусы на основе поля status
            order_status = order.get('status', '')
            
            # ОТЛАДКА: Проверяем заказ #10
            if order.get('id') == 10:
                print(f"🔍 ОТЛАДКА АНАЛИТИКИ: Заказ #10 - статус={order_status}")
            
            # Определяем статус покупки
            if order_status in PAID_ORDER_STATUSES:
                purchase_status = 'Оплачен'
                # ОТЛАДКА: Проверяем заказ #10
                if order.get('id') == 10:
                    print(f"🔍 ОТЛАДКА АНАЛИТИКИ: Заказ #10 -> purchase_status = 'Оплачен'")
            elif order_status in ['waiting_payment', 'payment_pending', 'payment_created', 'upsell_payment_created', 'upsell_payment_pending']:
                purchase_status = 'Ждет оплаты'
                # ОТЛАДКА: Проверяем заказ #10
                if order.get('id') == 10:
                    print(f"🔍 ОТЛАДКА АНАЛИТИКИ: Заказ #10 -> purchase_status = 'Ждет оплаты'")
            else:
                purchase_status = 'Не оплачен'
                # ОТЛАДКА: Проверяем заказ #10
                if order.get('id') == 10:
                    print(f"🔍 ОТЛАДКА АНАЛИТИКИ: Заказ #10 -> purchase_status = 'Не оплачен'")
            
            # Определяем статус допродажи - проверяем наличие события upsell_purchased
            order_id = order.get('id')
            has_upsell = await check_order_has_upsell(order_id)
            if has_upsell:
                upsell_status = 'Оплачен'
                print(f"🔍 ОТЛАДКА: Заказ #{order_id} имеет допродажу -> upsell_status = 'Оплачен'")
            else:
                upsell_status = 'Не оплачен'
            
            # Тип продукта без разделения форматов (для экспорта)
            product_type = await get_order_product_type(order.get('id'))
            
            # Получаем формат продукта
            product_format = await get_product_format(order.get('id'))
            
            # Прогресс для аналитики должен совпадать с тем, что видит пользователь во вкладке Orders.
            # Для этого используем карту прогресса/статусов, где значения уже на русском и совпадают
            # с переводами фронтенда. Логика совместима с текущими фильтрами.
            progress = get_order_progress_status(order.get('status', ''), product_type)
            
            # Получаем источник заказа и UTM-данные из event_metrics
            from db import get_order_source, get_order_utm_data
            order_source = await get_order_source(order.get('id'))
            utm_data = await get_order_utm_data(order.get('id'))
            
            # Конвертируем дату создания в московское время для отображения
            order_created_str = order.get('created_at', '')
            if order_created_str:
                if 'T' in order_created_str:
                    order_date = datetime.fromisoformat(order_created_str.replace('Z', '+00:00'))
                else:
                    order_date = datetime.strptime(order_created_str, "%Y-%m-%d %H:%M:%S")
                    if order_date.tzinfo is None:
                        order_date = pytz.UTC.localize(order_date)
                
                # Конвертируем в московское время
                order_date_msk = order_date.astimezone(MSK_TZ)
                created_at_msk = order_date_msk.strftime("%Y-%m-%d %H:%M:%S")
            else:
                created_at_msk = order_created_str

            analytics_data.append({
                'order_id': str(order.get('id', '')),
                'source': order_source,
                'utm_source': utm_data['utm_source'],
                'utm_medium': utm_data['utm_medium'],
                'utm_campaign': utm_data['utm_campaign'],
                'username': order.get('username', ''),
                'product_type': product_type,
                'product_format': product_format,
                'created_at': created_at_msk,
                'purchase_status': purchase_status,
                'upsell_status': upsell_status,
                'progress': progress,
                'manager': order.get('manager_email', ''),
                'phone': order.get('phone', ''),
                'email': order.get('email', '')
            })
        
        return {
            'status': 'success',
            'data': analytics_data,
            'total': len(analytics_data),
            'start_date': start_date,
            'end_date': end_date
        }
        
    except Exception as e:
        print(f"❌ Ошибка получения аналитики: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения аналитики: {str(e)}")

@app.get("/admin/analytics/utm-filters")
async def get_utm_filters(
    current_manager: str = Depends(get_current_manager)
):
    """Получает список уникальных UTM-значений для фильтров из реальных заказов"""
    try:
        # Получаем заказы с правами доступа (те же, что в аналитике)
        orders = await get_orders_filtered_with_permissions(current_manager)
        
        # Получаем UTM данные для всех заказов
        from db import get_order_utm_data
        utm_sources = set()
        utm_mediums = set()
        utm_campaigns = set()
        
        for order in orders:
            try:
                utm_data = await get_order_utm_data(order.get('id'))
                
                # Добавляем значения, если они не пустые и не "Неизвестно"
                if utm_data['utm_source'] and utm_data['utm_source'] not in ['', 'Неизвестно']:
                    utm_sources.add(utm_data['utm_source'])
                
                if utm_data['utm_medium'] and utm_data['utm_medium'] not in ['', 'Неизвестно']:
                    utm_mediums.add(utm_data['utm_medium'])
                
                if utm_data['utm_campaign'] and utm_data['utm_campaign'] not in ['', 'Неизвестно']:
                    utm_campaigns.add(utm_data['utm_campaign'])
                    
            except Exception as e:
                print(f"❌ Ошибка получения UTM данных для заказа {order.get('id')}: {e}")
                continue
        
        return {
            'status': 'success',
            'data': {
                'utm_sources': sorted(list(utm_sources)),
                'utm_mediums': sorted(list(utm_mediums)),
                'utm_campaigns': sorted(list(utm_campaigns))
            }
        }
            
    except Exception as e:
        print(f"❌ Ошибка получения UTM-фильтров: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения UTM-фильтров: {str(e)}")

@app.get("/admin/analytics/export")
async def export_analytics(
    start_date: str = Query(..., description="Дата начала в формате YYYY-MM-DD"),
    end_date: str = Query(..., description="Дата окончания в формате YYYY-MM-DD"),
    format: str = Query(..., description="Формат экспорта: csv или excel"),
    source: str = Query(None, description="Фильтр по источнику"),
    product_type: str = Query(None, description="Фильтр по типу продукта"),
    purchase_status: str = Query(None, description="Фильтр по статусу покупки"),
    upsell_status: str = Query(None, description="Фильтр по статусу допродажи"),
    progress: str = Query(None, description="Фильтр по прогрессу"),
    utm_source: str = Query(None, description="Фильтр по UTM source"),
    utm_medium: str = Query(None, description="Фильтр по UTM medium"),
    utm_campaign: str = Query(None, description="Фильтр по UTM campaign"),
    search: str = Query(None, description="Поиск по тексту"),
    current_manager: str = Depends(get_current_manager)
):
    """Экспортирует аналитические данные в CSV или Excel"""
    try:
        # Получаем данные аналитики напрямую, а не через вызов функции
        # Получаем все заказы без фильтрации по правам доступа
        orders = await get_orders_filtered()
        
        # ОТЛАДКА: Выводим информацию о полученных заказах
        print(f"🔍 ЭКСПОРТ: Получено заказов из БД: {len(orders)}")
        print(f"🔍 ЭКСПОРТ: Параметры фильтрации - start_date={start_date}, end_date={end_date}")
        print(f"🔍 ЭКСПОРТ: Фильтры - product_type={product_type}, purchase_status={purchase_status}, upsell_status={upsell_status}")
        print(f"🔍 ЭКСПОРТ: UTM фильтры - utm_source={utm_source}, utm_medium={utm_medium}, utm_campaign={utm_campaign}")
        print(f"🔍 ЭКСПОРТ: Поиск - search={search}")
        
        # Фильтруем по дате (в московском времени)
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        # Конвертируем в московское время
        start_dt = MSK_TZ.localize(start_dt)
        end_dt = MSK_TZ.localize(end_dt).replace(hour=23, minute=59, second=59)
        
        filtered_orders = []
        for order in orders:
            # Парсим дату создания заказа и конвертируем в московское время
            order_created_str = order['created_at']
            if 'T' in order_created_str:
                order_date = datetime.fromisoformat(order_created_str.replace('Z', '+00:00'))
            else:
                order_date = datetime.strptime(order_created_str, "%Y-%m-%d %H:%M:%S")
                if order_date.tzinfo is None:
                    order_date = pytz.UTC.localize(order_date)
            
            # Конвертируем в московское время
            order_date_msk = order_date.astimezone(MSK_TZ)
            
            if start_dt <= order_date_msk <= end_dt:
                filtered_orders.append(order)
        
        # ОТЛАДКА: Проверяем сколько заказов осталось после фильтрации по дате
        print(f"🔍 ЭКСПОРТ: После фильтрации по дате осталось заказов: {len(filtered_orders)}")
        
        # Применяем дополнительные фильтры (копируем логику из get_analytics)
        if source and source.strip():
            source_lower = source.lower()
            from db import get_order_source
            temp_orders = []
            for order in filtered_orders:
                order_source = await get_order_source(order.get('id'))
                if order_source.lower() == source_lower:
                    temp_orders.append(order)
            filtered_orders = temp_orders
        
        if product_type and product_type.strip():
            product_type_lower = product_type.lower()
            temp_orders = []
            for order in filtered_orders:
                order_product_type = await get_detailed_order_product_type(order.get('id'))
                # Проверяем совпадение: для "Книга" ищем "Книга печатная" или "Книга электронная"
                if product_type_lower == 'книга':
                    # Если выбрана общая "Книга", включаем все типы книг
                    if 'книга' in order_product_type.lower():
                        temp_orders.append(order)
                elif order_product_type.lower() == product_type_lower:
                    # Для остальных фильтров - точное совпадение
                    temp_orders.append(order)
            filtered_orders = temp_orders
            print(f"🔍 ЭКСПОРТ: После фильтрации по типу продукта '{product_type}' осталось: {len(filtered_orders)}")
        
        if purchase_status and purchase_status.strip():
            temp_orders = []
            for order in filtered_orders:
                order_status = order.get('status', '')
                if order_status in PAID_ORDER_STATUSES:
                    order_purchase_status = 'Оплачен'
                elif order_status in ['waiting_payment', 'payment_pending', 'payment_created', 'upsell_payment_created', 'upsell_payment_pending']:
                    order_purchase_status = 'Ждет оплаты'
                else:
                    order_purchase_status = 'Не оплачен'
                
                if order_purchase_status == purchase_status:
                    temp_orders.append(order)
            filtered_orders = temp_orders
            print(f"🔍 ЭКСПОРТ: После фильтрации по статусу покупки '{purchase_status}' осталось: {len(filtered_orders)}")
        
        if upsell_status and upsell_status.strip():
            temp_orders = []
            for order in filtered_orders:
                has_upsell = await check_order_has_upsell(order['id'])
                order_upsell_status = 'Оплачен' if has_upsell else 'Не оплачен'
                
                if order_upsell_status == upsell_status:
                    temp_orders.append(order)
            filtered_orders = temp_orders
            print(f"🔍 ЭКСПОРТ: После фильтрации по upsell статусу '{upsell_status}' осталось: {len(filtered_orders)}")
        
        if progress and progress.strip():
            temp_orders = []
            for order in filtered_orders:
                order_status = order.get('status', '')
                product_type = order.get('product_type', order.get('product', ''))
                
                order_progress = get_order_progress_status(order_status, product_type)
                
                if progress == 'Завершено':
                    if order_status in ['ready', 'delivered', 'completed', 'upsell_paid']:
                        temp_orders.append(order)
                elif progress in order_progress:
                    temp_orders.append(order)
            filtered_orders = temp_orders
            print(f"🔍 ЭКСПОРТ: После фильтрации по прогрессу '{progress}' осталось: {len(filtered_orders)}")
        
        # Фильтрация по UTM-параметрам
        if utm_source and utm_source.strip():
            from db import get_order_utm_data
            temp_orders = []
            for order in filtered_orders:
                utm_data = await get_order_utm_data(order.get('id'))
                if utm_data['utm_source'].lower() == utm_source.lower():
                    temp_orders.append(order)
            filtered_orders = temp_orders
            print(f"🔍 ЭКСПОРТ: После фильтрации по UTM source '{utm_source}' осталось: {len(filtered_orders)}")
        
        if utm_medium and utm_medium.strip():
            from db import get_order_utm_data
            temp_orders = []
            for order in filtered_orders:
                utm_data = await get_order_utm_data(order.get('id'))
                if utm_data['utm_medium'].lower() == utm_medium.lower():
                    temp_orders.append(order)
            filtered_orders = temp_orders
            print(f"🔍 ЭКСПОРТ: После фильтрации по UTM medium '{utm_medium}' осталось: {len(filtered_orders)}")
        
        if utm_campaign and utm_campaign.strip():
            from db import get_order_utm_data
            temp_orders = []
            for order in filtered_orders:
                utm_data = await get_order_utm_data(order.get('id'))
                if utm_data['utm_campaign'].lower() == utm_campaign.lower():
                    temp_orders.append(order)
            filtered_orders = temp_orders
            print(f"🔍 ЭКСПОРТ: После фильтрации по UTM campaign '{utm_campaign}' осталось: {len(filtered_orders)}")
        
        if search and search.strip():
            search_lower = search.lower()
            filtered_orders = [o for o in filtered_orders if 
                             search_lower in (o.get('username') or '').lower() or
                             search_lower in str(o.get('id') or '').lower() or
                             search_lower in (o.get('created_at') or '').lower()]
            print(f"🔍 ЭКСПОРТ: После фильтрации по поиску '{search}' осталось: {len(filtered_orders)}")
        
        # ОТЛАДКА: Финальное количество заказов перед формированием данных для экспорта
        print(f"🔍 ЭКСПОРТ: Финальное количество заказов для экспорта: {len(filtered_orders)}")
        
        # Формируем данные для экспорта
        analytics_data = []
        for order in filtered_orders:
            order_status = order.get('status', '')
            
            if order_status in PAID_ORDER_STATUSES:
                purchase_status = 'Оплачен'
            elif order_status in ['waiting_payment', 'payment_pending', 'payment_created', 'upsell_payment_created', 'upsell_payment_pending']:
                purchase_status = 'Ждет оплаты'
            else:
                purchase_status = 'Не оплачен'
            
            has_upsell = await check_order_has_upsell(order['id'])
            if has_upsell:
                upsell_status = 'Оплачен'
            else:
                upsell_status = 'Не оплачен'
            
            # Тип продукта без разделения форматов (для экспорта)
            product_type = await get_order_product_type(order.get('id'))
            
            # Получаем формат продукта
            product_format = await get_product_format(order.get('id'))
            
            progress = get_order_progress_status(order_status, product_type)
            
            # Получаем UTM-данные из event_metrics
            from db import get_order_utm_data
            utm_data = await get_order_utm_data(order.get('id'))
            
            # Конвертируем дату создания в московское время для отображения
            order_created_str = order.get('created_at', '')
            if order_created_str:
                if 'T' in order_created_str:
                    order_date = datetime.fromisoformat(order_created_str.replace('Z', '+00:00'))
                else:
                    order_date = datetime.strptime(order_created_str, "%Y-%m-%d %H:%M:%S")
                    if order_date.tzinfo is None:
                        order_date = pytz.UTC.localize(order_date)
                
                # Конвертируем в московское время
                order_date_msk = order_date.astimezone(MSK_TZ)
                created_at_msk = order_date_msk.strftime("%Y-%m-%d %H:%M:%S")
            else:
                created_at_msk = order_created_str
            
            analytics_data.append({
                'order_id': str(order.get('id', '')),
                'utm_source': utm_data['utm_source'],
                'utm_medium': utm_data['utm_medium'],
                'utm_campaign': utm_data['utm_campaign'],
                'username': order.get('username', ''),
                'telegram_id': str(order.get('telegram_id', order.get('user_id', ''))),
                'product_type': product_type,
                'product_format': product_format,
                'created_at': created_at_msk,
                'purchase_status': purchase_status,
                'upsell_status': upsell_status,
                'progress': progress,
                'manager': order.get('manager_email', ''),
                'phone': order.get('phone', ''),
                'email': order.get('email', '')
            })
        
        data = analytics_data
        
        # ОТЛАДКА: Проверяем сформированные данные
        print(f"🔍 ЭКСПОРТ: Сформировано записей для экспорта: {len(data)}")
        if data:
            print(f"🔍 ЭКСПОРТ: Пример первой записи: {data[0]}")
        
        if format.lower() == 'csv':
            # Создаем CSV с правильным разделителем
            import io
            import csv
            
            output = io.StringIO()
            if data:
                # Определяем заголовки
                fieldnames = ['order_id', 'utm_source', 'utm_medium', 'utm_campaign', 'username', 'telegram_id', 'product_type', 'product_format', 'created_at', 
                            'purchase_status', 'upsell_status', 'progress', 'manager', 'phone', 'email']
                # Используем точку с запятой как разделитель для лучшей совместимости с Excel
                writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=';', quoting=csv.QUOTE_ALL)
                writer.writeheader()
                writer.writerows(data)
            else:
                # Если нет данных, создаем пустой CSV с заголовками
                fieldnames = ['order_id', 'utm_source', 'utm_medium', 'utm_campaign', 'username', 'telegram_id', 'product_type', 'product_format', 'created_at', 
                            'purchase_status', 'upsell_status', 'progress', 'manager', 'phone', 'email']
                writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=';', quoting=csv.QUOTE_ALL)
                writer.writeheader()
            
            csv_content = output.getvalue()
            output.close()
            
            return StreamingResponse(
                io.BytesIO(csv_content.encode('utf-8-sig')),  # BOM для корректного отображения в Excel
                media_type='text/csv; charset=utf-8',
                headers={"Content-Disposition": f"attachment; filename=analytics_{start_date}_to_{end_date}.csv"}
            )
            
        elif format.lower() == 'excel':
            # Создаем Excel с правильным форматированием
            import io
            
            output = io.BytesIO()
            if data:
                df = pd.DataFrame(data)
                # Устанавливаем правильный порядок колонок
                column_order = ['order_id', 'utm_source', 'utm_medium', 'utm_campaign', 'username', 'telegram_id', 'product_type', 'product_format', 'created_at', 
                              'purchase_status', 'upsell_status', 'progress', 'manager', 'phone', 'email']
                df = df.reindex(columns=column_order)
            else:
                # Если нет данных, создаем пустой DataFrame с заголовками
                df = pd.DataFrame(columns=['order_id', 'utm_source', 'utm_medium', 'utm_campaign', 'username', 'telegram_id', 'product_type', 'product_format', 'created_at', 
                                         'purchase_status', 'upsell_status', 'progress', 'manager', 'phone', 'email'])
            
            # Создаем Excel файл с форматированием
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Analytics')
                
                # Получаем рабочую книгу для форматирования
                workbook = writer.book
                worksheet = writer.sheets['Analytics']
                
                # Автоподбор ширины колонок
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)  # Максимум 50 символов
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            output.seek(0)
            
            return StreamingResponse(
                output,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={"Content-Disposition": f"attachment; filename=analytics_{start_date}_to_{end_date}.xlsx"}
            )
        
        else:
            raise HTTPException(status_code=400, detail="Неподдерживаемый формат экспорта")
            
    except Exception as e:
        print(f"❌ Ошибка экспорта аналитики: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка экспорта: {str(e)}")

# --- API для работы с уведомлениями ---

@app.get("/admin/notifications", response_model=List[dict])
async def get_notifications(current_manager: str = Depends(get_current_manager)):
    """Получает уведомления для текущего менеджера"""
    try:
        # Проверяем, является ли пользователь супер-админом
        is_admin = await is_super_admin(current_manager)
        
        if is_admin:
            # Супер-админ видит все уведомления
            notifications = await get_order_notifications()
        else:
            # Обычный менеджер видит только свои уведомления
            manager = await get_manager_by_email(current_manager)
            if not manager:
                raise HTTPException(status_code=404, detail="Менеджер не найден")
            
            notifications = await get_order_notifications(manager["id"])
        
        return notifications
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка получения уведомлений: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения уведомлений: {str(e)}")
@app.post("/admin/notifications/{order_id}/mark-read", response_model=dict)
async def mark_notification_read(
    order_id: int,
    current_manager: str = Depends(get_current_manager)
):
    """Отмечает уведомление как прочитанное"""
    try:
        # Проверяем доступ к заказу
        if not await can_access_order(current_manager, order_id):
            raise HTTPException(status_code=403, detail="Нет доступа к заказу")
        
        # Отмечаем уведомление как прочитанное
        await mark_notification_as_read(order_id)
        
        return {"message": "Уведомление отмечено как прочитанное"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка отметки уведомления: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка отметки уведомления: {str(e)}")

@app.get("/admin/orders/{order_id}/notification", response_model=dict)
async def get_order_notification(
    order_id: int,
    current_manager: str = Depends(get_current_manager)
):
    """Получает информацию об уведомлении для конкретного заказа"""
    try:
        # Проверяем доступ к заказу
        if not await can_access_order(current_manager, order_id):
            raise HTTPException(status_code=403, detail="Нет доступа к заказу")
        
        notification = await get_notification_by_order_id(order_id)
        
        if not notification:
            return {"has_notification": False}
        
        return {
            "has_notification": True,
            "is_read": notification["is_read"],
            "last_user_message_at": notification["last_user_message_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка получения уведомления заказа: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения уведомления: {str(e)}")

@app.post("/admin/notifications/create-for-all-orders", response_model=dict)
async def create_notifications_for_all_orders_endpoint(
    current_manager: str = Depends(get_current_manager)
):
    """Создает уведомления для всех заказов"""
    try:
        # Проверяем, является ли пользователь супер-админом
        is_admin = await is_super_admin(current_manager)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Доступ запрещен. Требуются права супер-администратора")
        
        created_count = await create_notifications_for_all_orders()
        
        return {
            "message": f"Создано {created_count} уведомлений для всех заказов",
            "created_count": created_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка создания уведомлений: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания уведомлений: {str(e)}")

# API endpoints для новой системы шаблонов сообщений
@app.get("/admin/message-templates", response_model=List[MessageTemplateOut])
async def get_message_templates(current_manager: str = Depends(get_current_manager)):
    """Получает все шаблоны сообщений"""
    try:
        templates = await db.get_message_templates()
        return templates
    except Exception as e:
        print(f"❌ Ошибка получения шаблонов сообщений: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения шаблонов: {str(e)}")

@app.post("/admin/message-templates", response_model=MessageTemplateOut)
async def create_message_template(
    template: MessageTemplateCreate,
    current_manager: str = Depends(get_content_editor)
):
    """Создает новый шаблон сообщения"""
    try:
        manager = await db.get_manager_by_email(current_manager)
        if not manager:
            raise HTTPException(status_code=404, detail="Менеджер не найден")
        
        template_id = await db.create_message_template(
            template.name,
            template.message_type,
            template.content,
            template.order_step,
            template.delay_minutes,
            manager["id"]
        )
        
        # Получаем созданный шаблон
        templates = await db.get_message_templates()
        created_template = next((t for t in templates if t["id"] == template_id), None)
        
        if not created_template:
            raise HTTPException(status_code=500, detail="Ошибка создания шаблона")
        
        return created_template
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка создания шаблона сообщения: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания шаблона: {str(e)}")

# API endpoints для новой системы шаблонов сообщений
@app.get("/admin/message-templates", response_model=List[MessageTemplateOut])
async def get_message_templates(current_manager: str = Depends(get_current_manager)):
    """Получает все шаблоны сообщений"""
    try:
        templates = await db.get_message_templates()
        return templates
    except Exception as e:
        print(f"❌ Ошибка получения шаблонов сообщений: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения шаблонов: {str(e)}")

@app.post("/admin/message-templates", response_model=MessageTemplateOut)
async def create_message_template(
    template: MessageTemplateCreate,
    current_manager: str = Depends(get_content_editor)
):
    """Создает новый шаблон сообщения"""
    try:
        manager = await db.get_manager_by_email(current_manager)
        if not manager:
            raise HTTPException(status_code=404, detail="Менеджер не найден")
        
        template_id = await db.create_message_template(
            template.name,
            template.message_type,
            template.content,
            template.order_step,
            template.delay_minutes,
            manager["id"]
        )
        
        # Получаем созданный шаблон
        templates = await db.get_message_templates()
        created_template = next((t for t in templates if t["id"] == template_id), None)
        
        if not created_template:
            raise HTTPException(status_code=500, detail="Ошибка создания шаблона")
        
        return created_template
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка создания шаблона сообщения: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания шаблона: {str(e)}")

# --- Song Quiz Management ---

class SongQuizOut(BaseModel):
    id: int
    relation_key: str
    author_gender: str
    title: str
    intro: str
    phrases_hint: str
    questions_json: str
    outro: str
    is_active: bool
    created_at: str
    updated_at: str
class SongQuizCreate(BaseModel):
    relation_key: str
    author_gender: str
    title: str
    intro: str
    phrases_hint: str
    questions_json: str
    outro: str
    is_active: bool = True

class SongQuizUpdate(BaseModel):
    relation_key: str
    author_gender: str
    title: str
    intro: str
    phrases_hint: str
    questions_json: str
    outro: str
    is_active: bool

@app.get("/admin/song-quiz", response_model=List[SongQuizOut])
async def get_song_quizzes(current_manager: str = Depends(get_current_manager)):
    """Получает все квизы песни"""
    try:
        quizzes = await get_song_quiz_list()
        print(f"✅ Найдено {len(quizzes)} квизов песни")
        return quizzes
    except Exception as e:
        print(f"❌ Ошибка получения квизов: {e}")
        return []

@app.post("/admin/song-quiz", response_model=SongQuizOut)
async def create_song_quiz(
    quiz: SongQuizCreate,
    current_manager: str = Depends(get_content_editor)
):
    """Создает новый квиз песни"""
    try:
        quiz_id = await create_song_quiz_item(
            quiz.relation_key,
            quiz.author_gender,
            quiz.title,
            quiz.intro,
            quiz.phrases_hint,
            quiz.questions_json,
            quiz.outro,
            quiz.is_active
        )
        
        # Получаем созданный квиз
        created_quiz = await get_song_quiz_item(quiz.relation_key, quiz.author_gender)
        if not created_quiz:
            raise HTTPException(status_code=500, detail="Ошибка создания квиза")
        
        return created_quiz
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка создания квиза: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания квиза: {str(e)}")

@app.put("/admin/song-quiz/{quiz_id}", response_model=SongQuizOut)
async def update_song_quiz(
    quiz_id: int,
    quiz: SongQuizUpdate,
    current_manager: str = Depends(get_content_editor)
):
    """Обновляет квиз песни"""
    try:
        print(f"🔍 Обновление квиза ID: {quiz_id}")
        print(f"🔍 Данные квиза: {quiz.dict()}")
        
        success = await update_song_quiz_item(
            quiz_id,
            quiz.relation_key,
            quiz.author_gender,
            quiz.title,
            quiz.intro,
            quiz.phrases_hint,
            quiz.questions_json,
            quiz.outro,
            quiz.is_active
        )
        
        print(f"🔍 Результат обновления: {success}")
        
        if not success:
            raise HTTPException(status_code=404, detail="Квиз не найден")
        
        # Получаем обновленный квиз
        updated_quiz = await get_song_quiz_by_id(quiz_id)
        if not updated_quiz:
            raise HTTPException(status_code=500, detail="Ошибка обновления квиза")
        
        return updated_quiz
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка обновления квиза: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления квиза: {str(e)}")

@app.delete("/admin/song-quiz/{quiz_id}")
async def delete_song_quiz(
    quiz_id: int,
    current_manager: str = Depends(get_super_admin)
):
    """Удаляет квиз песни"""
    try:
        success = await delete_song_quiz_item(quiz_id)
        if not success:
            raise HTTPException(status_code=404, detail="Квиз не найден")
        
        return {"message": "Квиз успешно удален"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка удаления квиза: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления квиза: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("admin_backend.main:app", host="0.0.0.0", port=8001, reload=True) 