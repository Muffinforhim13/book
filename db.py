import aiosqlite
import json
import os
import glob
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
from passlib.context import CryptContext

def get_moscow_time():
    """Возвращает текущее время в московском часовом поясе"""
    return "datetime('now', '+3 hours')"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

DB_PATH = 'bookai.db'

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

async def init_db():
    """Инициализирует базу данных, создавая все необходимые таблицы"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Настройки SQLite для лучшей производительности и предотвращения блокировок
        await configure_db_connection(db)
        
        # Автоматически назначаем менеджеров к существующим заказам при инициализации
        try:
            print("🔧 Автоматическое назначение менеджеров к существующим заказам...")
            result = await assign_managers_to_all_orders()
            print(f"✅ {result['message']}")
        except Exception as e:
            print(f"❌ Ошибка автоматического назначения менеджеров: {e}")
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                product TEXT,
                relation TEXT,
                main_hero_intro TEXT,
                main_hero_photos TEXT,
                heroes TEXT,
                generated_book TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                status TEXT DEFAULT 'created',
                order_data TEXT,
                pdf_path TEXT,
                mp3_path TEXT,
                assigned_manager_id INTEGER,
                first_last_design TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES user_profiles(user_id),
                FOREIGN KEY(assigned_manager_id) REFERENCES managers(id)
            )
        ''')
        
        # Добавляем колонку first_last_design если её нет
        try:
            await db.execute('ALTER TABLE orders ADD COLUMN first_last_design TEXT')
            print("✅ Колонка first_last_design добавлена в таблицу orders")
        except aiosqlite.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️ Колонка first_last_design уже существует")
            else:
                print(f"ℹ️ Колонка first_last_design: {e}")
        
        # Добавляем колонку first_page_text если её нет
        try:
            await db.execute('ALTER TABLE orders ADD COLUMN first_page_text TEXT')
            print("✅ Колонка first_page_text добавлена в таблицу orders")
        except aiosqlite.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️ Колонка first_page_text уже существует")
            else:
                print(f"ℹ️ Колонка first_page_text: {e}")
        
        # Добавляем колонку last_page_text если её нет
        try:
            await db.execute('ALTER TABLE orders ADD COLUMN last_page_text TEXT')
            print("✅ Колонка last_page_text добавлена в таблицу orders")
        except aiosqlite.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️ Колонка last_page_text уже существует")
            else:
                print(f"ℹ️ Колонка last_page_text: {e}")
        
        # Добавляем колонку total_amount если её нет
        try:
            await db.execute('ALTER TABLE orders ADD COLUMN total_amount REAL')
            print("✅ Колонка total_amount добавлена в таблицу orders")
        except aiosqlite.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️ Колонка total_amount уже существует")
            else:
                print(f"ℹ️ Колонка total_amount: {e}")
        
        # Добавляем колонку sender_name если её нет
        try:
            await db.execute('ALTER TABLE orders ADD COLUMN sender_name TEXT')
            print("✅ Колонка sender_name добавлена в таблицу orders")
        except aiosqlite.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️ Колонка sender_name уже существует")
            else:
                print(f"ℹ️ Колонка sender_name: {e}")
        
        # Добавляем колонку email если её нет
        try:
            await db.execute('ALTER TABLE orders ADD COLUMN email TEXT')
            print("✅ Колонка email добавлена в таблицу orders")
        except aiosqlite.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️ Колонка email уже существует")
            else:
                print(f"ℹ️ Колонка email: {e}")
        
        # Добавляем колонку song_style_message_sent если её нет
        try:
            await db.execute('ALTER TABLE orders ADD COLUMN song_style_message_sent INTEGER DEFAULT 0')
            print("✅ Колонка song_style_message_sent добавлена в таблицу orders")
        except aiosqlite.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️ Колонка song_style_message_sent уже существует")
            else:
                print(f"ℹ️ Колонка song_style_message_sent: {e}")
        
        # Добавляем колонку files если её нет в message_templates
        try:
            await db.execute('ALTER TABLE message_templates ADD COLUMN files TEXT')
            print("✅ Колонка files добавлена в таблицу message_templates")
        except aiosqlite.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️ Колонка files уже существует")
            else:
                print(f"ℹ️ Колонка files: {e}")
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS outbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                user_id INTEGER,
                type TEXT, -- 'file', 'text', 'image_with_text_and_button' или 'manager_notification'
                content TEXT, -- путь к файлу или текст сообщения
                file_type TEXT, -- тип файла (если есть): pdf/mp3/jpg/итд
                comment TEXT, -- комментарий к файлу (если есть)
                button_text TEXT, -- текст кнопки (для image_with_text_and_button)
                button_callback TEXT, -- callback_data кнопки (для image_with_text_and_button)
                is_general_message INTEGER DEFAULT 0, -- флаг для общих сообщений (0=обычный файл, 1=общее сообщение)
                status TEXT DEFAULT 'pending', -- pending/sent/failed
                retry_count INTEGER DEFAULT 0, -- количество попыток отправки
                max_retries INTEGER DEFAULT 5, -- максимальное количество попыток
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                sent_at DATETIME,
                FOREIGN KEY(order_id) REFERENCES orders(id),
                FOREIGN KEY(user_id) REFERENCES user_profiles(user_id)
            )
        ''')
        
        # Добавляем колонки retry_count и max_retries если их нет
        try:
            await db.execute('ALTER TABLE outbox ADD COLUMN retry_count INTEGER DEFAULT 0')
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                print(f"ℹ️ Колонка retry_count: {e}")
        
        try:
            await db.execute('ALTER TABLE outbox ADD COLUMN max_retries INTEGER DEFAULT 5')
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                print(f"ℹ️ Колонка max_retries: {e}")
        
        try:
            await db.execute('ALTER TABLE outbox ADD COLUMN is_general_message INTEGER DEFAULT 0')
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                print(f"ℹ️ Колонка is_general_message: {e}")
        # Новые таблицы для структуры заказа
        await db.execute('''
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                name TEXT,
                intro TEXT,
                face_1 TEXT,
                face_2 TEXT,
                full TEXT,
                FOREIGN KEY(order_id) REFERENCES orders(id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                question TEXT,
                answer TEXT,
                FOREIGN KEY(order_id) REFERENCES orders(id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS main_hero_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                filename TEXT,
                FOREIGN KEY(order_id) REFERENCES orders(id)
            )
        ''')
        
        # Таблица для фотографий других героев
        await db.execute('''
            CREATE TABLE IF NOT EXISTS hero_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                filename TEXT,
                photo_type TEXT,
                hero_name TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(order_id) REFERENCES orders(id)
            )
        ''')
        
        # Таблица для загруженных файлов
        await db.execute('''
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                filename TEXT,
                file_type TEXT,
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(order_id) REFERENCES orders(id)
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS joint_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                filename TEXT,
                FOREIGN KEY(order_id) REFERENCES orders(id)
            )
        ''')
        
        # Таблица для предложений сюжетов
        await db.execute('''
            CREATE TABLE IF NOT EXISTS story_proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                story_batch INTEGER,
                stories TEXT, -- JSON с массивом сюжетов
                pages TEXT, -- JSON с номерами страниц
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(order_id) REFERENCES orders(id)
            )
        ''')
        
        # Таблица для отслеживания номеров страниц
        await db.execute('''
            CREATE TABLE IF NOT EXISTS order_pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                page_number INTEGER,
                filename TEXT,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(order_id) REFERENCES orders(id)
            )
        ''')
        
        # Таблица для шаблонов отложенных сообщений (новая система)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS message_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL, -- название шаблона
                message_type TEXT NOT NULL, -- тип сообщения
                content TEXT NOT NULL, -- текст сообщения
                order_step TEXT, -- шаг заказа, на котором отправляется
                delay_minutes INTEGER DEFAULT 0, -- задержка в минутах от начала шага
                is_active BOOLEAN DEFAULT 1, -- активен ли шаблон
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                manager_id INTEGER, -- ID менеджера, создавшего шаблон
                FOREIGN KEY(manager_id) REFERENCES managers(id)
            )
        ''')
        
        # Таблица для файлов шаблонов сообщений
        await db.execute('''
            CREATE TABLE IF NOT EXISTS message_template_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER, -- ID шаблона сообщения
                file_path TEXT, -- путь к файлу
                file_type TEXT, -- тип файла (photo, audio, document, video, gif)
                file_name TEXT, -- оригинальное имя файла
                file_size INTEGER, -- размер файла в байтах
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(template_id) REFERENCES message_templates(id) ON DELETE CASCADE
            )
        ''')
        
        # Таблица для отслеживания отправленных сообщений пользователям
        await db.execute('''
            CREATE TABLE IF NOT EXISTS sent_messages_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER, -- ID шаблона сообщения
                user_id INTEGER, -- ID пользователя
                order_id INTEGER, -- ID заказа
                sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(template_id) REFERENCES message_templates(id),
                FOREIGN KEY(user_id) REFERENCES user_profiles(user_id),
                FOREIGN KEY(order_id) REFERENCES orders(id)
            )
        ''')
        
        # Старая таблица для отложенных сообщений (оставляем для совместимости)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS delayed_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                user_id INTEGER,
                manager_id INTEGER, -- ID менеджера, создавшего сообщение
                message_type TEXT, -- 'demo_example', 'payment_reminder', 'final_reminder', 'auto_order_created', 'story_proposal', 'story_selection'
                content TEXT, -- текст сообщения
                delay_minutes INTEGER, -- задержка в минутах
                status TEXT DEFAULT 'pending', -- pending/sent/failed
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                scheduled_at DATETIME,
                sent_at DATETIME,
                is_automatic BOOLEAN DEFAULT 0, -- автоматическое сообщение при создании заказа
                order_step TEXT, -- шаг заказа для общих сообщений
                story_batch INTEGER DEFAULT 0, -- номер партии сюжетов (1-5)
                story_pages TEXT, -- номера страниц для сюжетов (JSON)
                selected_stories TEXT, -- выбранные пользователем сюжеты (JSON)
                is_active BOOLEAN DEFAULT 1, -- активен ли шаблон
                usage_count INTEGER DEFAULT 0, -- количество использований
                last_used DATETIME, -- последнее использование
                FOREIGN KEY(order_id) REFERENCES orders(id),
                FOREIGN KEY(user_id) REFERENCES user_profiles(user_id),
                FOREIGN KEY(manager_id) REFERENCES managers(id)
            )
        ''')
        
        # Добавляем поле order_step, если его нет
        try:
            await db.execute('ALTER TABLE delayed_messages ADD COLUMN order_step TEXT')
        except:
            pass  # Поле уже существует
        
        # Добавляем новые поля для системы шаблонов
        try:
            await db.execute('ALTER TABLE delayed_messages ADD COLUMN is_active BOOLEAN DEFAULT 1')
        except:
            pass  # Поле уже существует
        
        try:
            await db.execute('ALTER TABLE delayed_messages ADD COLUMN usage_count INTEGER DEFAULT 0')
        except:
            pass  # Поле уже существует
        
        try:
            await db.execute('ALTER TABLE delayed_messages ADD COLUMN last_used DATETIME')
        except:
            pass  # Поле уже существует
        
        # Таблица для файлов отложенных сообщений
        await db.execute('''
            CREATE TABLE IF NOT EXISTS delayed_message_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                delayed_message_id INTEGER,
                file_path TEXT, -- путь к файлу
                file_type TEXT, -- тип файла (photo, audio, document)
                file_name TEXT, -- оригинальное имя файла
                file_size INTEGER, -- размер файла в байтах
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(delayed_message_id) REFERENCES delayed_messages(id) ON DELETE CASCADE
            )
        ''')
        
        # Таблица для отслеживания времени пользователей на этапах
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_step_timers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                order_id INTEGER NOT NULL,
                order_step TEXT NOT NULL, -- этап на котором находится пользователь
                product_type TEXT, -- тип продукта (Песня/Книга)
                step_started_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- когда пользователь попал на этап
                step_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- последнее обновление
                is_active BOOLEAN DEFAULT 1, -- активен ли таймер
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, order_id, order_step), -- один таймер на пользователя/заказ/этап
                FOREIGN KEY(user_id) REFERENCES user_profiles(user_id),
                FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
            )
        ''')
        
        # Таблица для отслеживания отправленных сообщений по таймерам
        await db.execute('''
            CREATE TABLE IF NOT EXISTS timer_messages_sent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timer_id INTEGER NOT NULL,
                template_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                order_id INTEGER NOT NULL,
                message_type TEXT NOT NULL,
                delay_minutes INTEGER NOT NULL,
                sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timer_id, template_id, delay_minutes), -- одно сообщение на таймер/шаблон/задержку
                FOREIGN KEY(timer_id) REFERENCES user_step_timers(id) ON DELETE CASCADE,
                FOREIGN KEY(template_id) REFERENCES message_templates(id),
                FOREIGN KEY(user_id) REFERENCES user_profiles(user_id),
                FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
            )
        ''')
        
        # Таблица для отслеживания отправленных общих сообщений
        await db.execute('''
            CREATE TABLE IF NOT EXISTS general_message_sent_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                delayed_message_id INTEGER,
                user_id INTEGER,
                order_id INTEGER,
                sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(delayed_message_id) REFERENCES delayed_messages(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES user_profiles(user_id),
                FOREIGN KEY(order_id) REFERENCES orders(id),
                UNIQUE(delayed_message_id, user_id, order_id)
            )
        ''')
        
        # Таблица для адресов доставки
        await db.execute('''
            CREATE TABLE IF NOT EXISTS delivery_addresses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                user_id INTEGER,
                address TEXT,
                recipient_name TEXT,
                phone TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(order_id) REFERENCES orders(id),
                FOREIGN KEY(user_id) REFERENCES user_profiles(user_id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS order_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                old_status TEXT,
                new_status TEXT,
                changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(order_id) REFERENCES orders(id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS message_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                sender TEXT, -- 'manager' или 'user'
                message TEXT,
                sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(order_id) REFERENCES orders(id)
            )
        ''')
        
        # Таблица для ранних сообщений пользователей (до создания заказа)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS early_user_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS managers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                is_super_admin BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1
            )
        ''')

        # Таблица для шаблонов обложек
        await db.execute('''
            CREATE TABLE IF NOT EXISTS cover_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                filename TEXT NOT NULL,
                category TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для стилей книг
        await db.execute('''
            CREATE TABLE IF NOT EXISTS book_styles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                filename TEXT NOT NULL,
                category TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для стилей голоса
        await db.execute('''
            CREATE TABLE IF NOT EXISTS voice_styles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                filename TEXT NOT NULL,
                gender TEXT DEFAULT 'male',
                category TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для шаблона сводки заказа
        await db.execute('''
            CREATE TABLE IF NOT EXISTS order_summary_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gender_label TEXT DEFAULT 'Пол отправителя',
                recipient_name_label TEXT DEFAULT 'Имя получателя',
                gift_reason_label TEXT DEFAULT 'Повод',
                relation_label TEXT DEFAULT 'Отношение',
                style_label TEXT DEFAULT 'Стиль',
                format_label TEXT DEFAULT 'Формат',
                sender_name_label TEXT DEFAULT 'От кого',
                song_gender_label TEXT DEFAULT 'Пол отправителя',
                song_recipient_name_label TEXT DEFAULT 'Имя получателя',
                song_gift_reason_label TEXT DEFAULT 'Повод',
                song_relation_label TEXT DEFAULT 'Отношение',
                song_style_label TEXT DEFAULT 'Стиль',
                song_voice_label TEXT DEFAULT 'Голос',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Добавляем поле gender, если его нет
        try:
            await db.execute('ALTER TABLE voice_styles ADD COLUMN gender TEXT DEFAULT "male"')
        except:
            pass  # Поле уже существует
        await db.execute('''
            CREATE TABLE IF NOT EXISTS manager_queue (
                id INTEGER PRIMARY KEY,
                last_manager_id INTEGER DEFAULT 0
            )
        ''')
        
        # Таблица для цен
        await db.execute('''
            CREATE TABLE IF NOT EXISTS pricing_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product TEXT NOT NULL,
                price REAL NOT NULL,
                currency TEXT DEFAULT 'RUB',
                description TEXT,
                upgrade_price_difference REAL DEFAULT 0, -- Разница в цене при апгрейде
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Добавляем колонку upgrade_price_difference если её нет
        try:
            await db.execute('ALTER TABLE pricing_items ADD COLUMN upgrade_price_difference REAL DEFAULT 0')
            print("✅ Колонка upgrade_price_difference добавлена в таблицу pricing_items")
        except aiosqlite.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️ Колонка upgrade_price_difference уже существует")
            else:
                print(f"ℹ️ Колонка upgrade_price_difference: {e}")
        
        # Таблица для шагов контента
        await db.execute('''
            CREATE TABLE IF NOT EXISTS content_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                step_key TEXT NOT NULL UNIQUE,
                step_name TEXT NOT NULL,
                content_type TEXT DEFAULT 'text',
                content TEXT NOT NULL,
                materials TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица квиза для песни (редактируемые тексты вопросов по связям)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS song_quiz (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                relation_key TEXT NOT NULL,
                author_gender TEXT NOT NULL, -- 'male' | 'female'
                title TEXT DEFAULT '',
                intro TEXT NOT NULL,
                phrases_hint TEXT DEFAULT '',
                questions_json TEXT NOT NULL, -- JSON массив из 8 пунктов
                outro TEXT DEFAULT '',
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(relation_key, author_gender)
            )
        ''')
        
        # Таблица для автоматического сбора всех сообщений бота
        await db.execute('''
            CREATE TABLE IF NOT EXISTS bot_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_key TEXT UNIQUE NOT NULL,
                message_name TEXT NOT NULL,
                content TEXT NOT NULL,
                context TEXT, -- Контекст сообщения (например: "welcome", "photo_upload", "payment")
                stage TEXT, -- Этап бота (например: "start", "character_creation", "payment")
                sort_order INTEGER DEFAULT 0, -- Порядок сортировки
                is_editable BOOLEAN NOT NULL DEFAULT 1,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                usage_count INTEGER DEFAULT 0, -- Сколько раз использовалось
                last_used DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Таблица для трекинга метрик событий
        await db.execute('''
            CREATE TABLE IF NOT EXISTS event_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT, -- JSON данные события
                step_name TEXT, -- Название шага (для отвалов)
                product_type TEXT, -- Тип продукта (книга/песня)
                order_id INTEGER, -- ID заказа (если применимо)
                amount REAL, -- Сумма (для покупок)
                source TEXT, -- Источник (канал/кампания)
                utm_source TEXT, -- UTM source
                utm_medium TEXT, -- UTM medium
                utm_campaign TEXT, -- UTM campaign
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Добавляем UTM-колонки если их нет
        try:
            await db.execute('ALTER TABLE event_metrics ADD COLUMN utm_source TEXT')
            print("✅ Колонка utm_source добавлена в таблицу event_metrics")
        except aiosqlite.OperationalError as e:
            if "duplicate column name" not in str(e):
                print(f"⚠️ Ошибка добавления utm_source: {e}")
        
        try:
            await db.execute('ALTER TABLE event_metrics ADD COLUMN utm_medium TEXT')
            print("✅ Колонка utm_medium добавлена в таблицу event_metrics")
        except aiosqlite.OperationalError as e:
            if "duplicate column name" not in str(e):
                print(f"⚠️ Ошибка добавления utm_medium: {e}")
        
        try:
            await db.execute('ALTER TABLE event_metrics ADD COLUMN utm_campaign TEXT')
            print("✅ Колонка utm_campaign добавлена в таблицу event_metrics")
        except aiosqlite.OperationalError as e:
            if "duplicate column name" not in str(e):
                print(f"⚠️ Ошибка добавления utm_campaign: {e}")
        
        # Добавляем UTM-колонки в таблицу orders если их нет
        try:
            await db.execute('ALTER TABLE orders ADD COLUMN source TEXT')
            print("✅ Колонка source добавлена в таблицу orders")
        except aiosqlite.OperationalError as e:
            if "duplicate column name" not in str(e):
                print(f"⚠️ Ошибка добавления source: {e}")
        
        try:
            await db.execute('ALTER TABLE orders ADD COLUMN utm_source TEXT')
            print("✅ Колонка utm_source добавлена в таблицу orders")
        except aiosqlite.OperationalError as e:
            if "duplicate column name" not in str(e):
                print(f"⚠️ Ошибка добавления utm_source: {e}")
        
        try:
            await db.execute('ALTER TABLE orders ADD COLUMN utm_medium TEXT')
            print("✅ Колонка utm_medium добавлена в таблицу orders")
        except aiosqlite.OperationalError as e:
            if "duplicate column name" not in str(e):
                print(f"⚠️ Ошибка добавления utm_medium: {e}")
        
        try:
            await db.execute('ALTER TABLE orders ADD COLUMN utm_campaign TEXT')
            print("✅ Колонка utm_campaign добавлена в таблицу orders")
        except aiosqlite.OperationalError as e:
            if "duplicate column name" not in str(e):
                print(f"⚠️ Ошибка добавления utm_campaign: {e}")

        # Создаем индексы для быстрого поиска
        await db.execute('''
            CREATE INDEX IF NOT EXISTS idx_event_metrics_user_id ON event_metrics(user_id)
        ''')
        await db.execute('''
            CREATE INDEX IF NOT EXISTS idx_event_metrics_event_type ON event_metrics(event_type)
        ''')
        await db.execute('''
            CREATE INDEX IF NOT EXISTS idx_event_metrics_timestamp ON event_metrics(timestamp)
        ''')
        await db.execute('''
            CREATE INDEX IF NOT EXISTS idx_event_metrics_order_id ON event_metrics(order_id)
        ''')
        
        # Таблица для уведомлений о новых сообщениях от пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS order_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                manager_id INTEGER, -- ID менеджера, которому назначен заказ
                is_read BOOLEAN DEFAULT 0, -- прочитано ли уведомление
                last_user_message_at DATETIME, -- время последнего сообщения от пользователя
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY(manager_id) REFERENCES managers(id) ON DELETE SET NULL,
                UNIQUE(order_id) -- один заказ = одно уведомление
            )
        ''')
        
        # Создаем индексы для быстрого поиска уведомлений
        await db.execute('''
            CREATE INDEX IF NOT EXISTS idx_order_notifications_manager_id ON order_notifications(manager_id)
        ''')
        await db.execute('''
            CREATE INDEX IF NOT EXISTS idx_order_notifications_is_read ON order_notifications(is_read)
        ''')
        await db.execute('''
            CREATE INDEX IF NOT EXISTS idx_order_notifications_order_id ON order_notifications(order_id)
        ''')
        
        # Вставляем начальную запись, если её нет
        await db.execute('''
            INSERT OR IGNORE INTO manager_queue (id, last_manager_id) VALUES (1, 0)
        ''')
        await db.commit()

async def save_user_profile(user_data: dict, generated_book: str = None):
    """Сохраняет профиль пользователя и сгенерированную книгу"""
    async def _save_operation():
        async with aiosqlite.connect(DB_PATH) as db:
            # Настраиваем соединение
            await configure_db_connection(db)
            
            # Очищаем None значения
            username = user_data.get('username') if user_data.get('username') and user_data.get('username') != "None" else None
            first_name = user_data.get('first_name') if user_data.get('first_name') and user_data.get('first_name') != "None" else None
            last_name = user_data.get('last_name') if user_data.get('last_name') and user_data.get('last_name') != "None" else None
            
            await db.execute('''
                INSERT OR REPLACE INTO user_profiles 
                (user_id, username, first_name, last_name, product, relation, 
                 main_hero_intro, main_hero_photos, heroes, generated_book, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (
                user_data.get('user_id'),
                username,
                first_name,
                last_name,
                user_data.get('product'),
                user_data.get('relation'),
                user_data.get('main_hero_intro'),
                json.dumps(user_data.get('main_hero_photos', [])),
                json.dumps(user_data.get('heroes', [])),
                generated_book
            ))
            await db.commit()
    
    await safe_db_operation(_save_operation)
async def get_user_book(user_id: int) -> Dict:
    """Получает книгу пользователя из базы данных"""
    async def _get_operation():
        async with aiosqlite.connect(DB_PATH) as db:
            # Настраиваем соединение
            await configure_db_connection(db)
            
            async with db.execute('''
                SELECT generated_book, created_at FROM user_profiles 
                WHERE user_id = ?
            ''', (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        'generated_book': row[0],
                        'created_at': row[1]
                    }
                return None
    
    return await safe_db_operation(_get_operation)

# --- Работа с заказами ---

async def create_order(user_id: int, order_data: dict) -> int:
    print(f"🔍 ОТЛАДКА: create_order вызвана с user_id={user_id}, order_data={order_data}")
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Если username не передан, подтягиваем из профиля пользователя (НЕ из предыдущих заказов)
        if not order_data.get('username'):
            try:
                async with db.execute('''
                    SELECT username 
                    FROM user_profiles 
                    WHERE user_id = ? 
                    LIMIT 1
                ''', (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0]:
                        order_data['username'] = row[0]
                        print(f"🔍 ОТЛАДКА: Подтянули username из профиля пользователя: {row[0]}")
            except Exception as e:
                print(f"❌ Ошибка получения username из профиля пользователя: {e}")
        
        cursor = await db.execute('''
            INSERT INTO orders (user_id, order_data, status, source, utm_source, utm_medium, utm_campaign, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ''', (user_id, json.dumps(order_data), 'pending', order_data.get('source'), order_data.get('utm_source'), order_data.get('utm_medium'), order_data.get('utm_campaign')))
        
        order_id = cursor.lastrowid
        print(f"🔍 ОТЛАДКА: Создан заказ #{order_id} для пользователя {user_id}")
        
        # Сохраняем профиль пользователя в таблицу user_profiles
        try:
            print(f"🔍 ОТЛАДКА: Сохраняем профиль для заказа #{order_id}")
            print(f"🔍 ОТЛАДКА: user_id={user_id}, username={order_data.get('username')}, first_name={order_data.get('first_name')}, last_name={order_data.get('last_name')}, product={order_data.get('product')}")
            
            # Очищаем None значения
            username = order_data.get('username') if order_data.get('username') and order_data.get('username') != "None" else None
            first_name = order_data.get('first_name') if order_data.get('first_name') and order_data.get('first_name') != "None" else None
            last_name = order_data.get('last_name') if order_data.get('last_name') and order_data.get('last_name') != "None" else None
            
            await db.execute('''
                INSERT OR REPLACE INTO user_profiles 
                (user_id, username, first_name, last_name, product, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            ''', (
                user_id,
                username,
                first_name,
                last_name,
                order_data.get('product')
            ))
            print(f"🔍 ОТЛАДКА: Профиль пользователя сохранен для заказа #{order_id}")
        except Exception as e:
            print(f"❌ Ошибка сохранения профиля пользователя: {e}")
        
        # Автоматически назначаем менеджера к новому заказу
        try:
            # Простой способ - берем менеджера по порядку
            async with db.execute('''
                SELECT id FROM managers WHERE is_super_admin = 0 ORDER BY id ASC
            ''') as cursor:
                managers = await cursor.fetchall()
            
            if managers:
                # Получаем количество заказов для определения следующего менеджера
                async with db.execute('SELECT COUNT(*) FROM orders') as cursor:
                    order_count = (await cursor.fetchone())[0]
                
                # Выбираем менеджера по принципу round-robin
                manager_index = (order_count - 1) % len(managers)
                selected_manager_id = managers[manager_index][0]
                
                await db.execute('''
                    UPDATE orders
                    SET assigned_manager_id = ?
                    WHERE id = ?
                ''', (selected_manager_id, order_id))
                print(f"🔍 ОТЛАДКА: Менеджер ID {selected_manager_id} назначен к заказу #{order_id}")
            else:
                print(f"🔍 ОТЛАДКА: Нет доступных менеджеров для заказа #{order_id}")
        except Exception as e:
            print(f"❌ Ошибка автоматического назначения менеджера к заказу {order_id}: {e}")
        
        await db.commit()
        return order_id

async def get_orders(status: Optional[str] = None) -> List[Dict]:
    async def _get_operation():
        async with aiosqlite.connect(DB_PATH) as db:
            # Настраиваем соединение
            await configure_db_connection(db)
            
            if status:
                query = '''
                    SELECT o.*, o.user_id as telegram_id, u.username, m.email as manager_email, m.full_name as manager_name 
                    FROM orders o 
                    LEFT JOIN user_profiles u ON o.user_id = u.user_id 
                    LEFT JOIN managers m ON o.assigned_manager_id = m.id 
                    WHERE o.status = ? 
                    ORDER BY o.created_at DESC
                '''
                args = (status,)
            else:
                query = '''
                    SELECT o.*, o.user_id as telegram_id, u.username, m.email as manager_email, m.full_name as manager_name 
                    FROM orders o 
                    LEFT JOIN user_profiles u ON o.user_id = u.user_id 
                    LEFT JOIN managers m ON o.assigned_manager_id = m.id 
                    ORDER BY o.created_at DESC
                '''
                args = ()
            async with db.execute(query, args) as cursor:
                rows = await cursor.fetchall()
                return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]
    
    return await safe_db_operation(_get_operation)

async def get_orders_filtered(
    status: Optional[str] = None,
    order_type: Optional[str] = None,
    telegram_id: Optional[str] = None,
    order_id: Optional[int] = None,
    sort_by: str = 'created_at',
    sort_dir: str = 'desc',
) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        query = '''
            SELECT o.*, o.user_id as telegram_id, u.product, u.username, m.email as manager_email, m.full_name as manager_name, d.phone
            FROM orders o 
            LEFT JOIN user_profiles u ON o.user_id = u.user_id 
            LEFT JOIN managers m ON o.assigned_manager_id = m.id 
            LEFT JOIN delivery_addresses d ON o.id = d.order_id
            WHERE 1=1
        '''
        args = []
        if status:
            query += ' AND o.status = ?'
            args.append(status)
        if order_type:
            query += ' AND u.product = ?'
            args.append(order_type)
        if telegram_id:
            query += ' AND o.user_id = ?'
            args.append(int(telegram_id))
        if order_id:
            query += ' AND o.id = ?'
            args.append(order_id)
        if sort_by not in ['created_at', 'status', 'id']:
            sort_by = 'created_at'
        if sort_dir.lower() not in ['asc', 'desc']:
            sort_dir = 'desc'
        query += f' ORDER BY o.{sort_by} {sort_dir.upper()}'
        async with db.execute(query, args) as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def get_order(order_id: int) -> Optional[Dict]:
    async def _get_operation():
        async with aiosqlite.connect(DB_PATH) as db:
            # Настраиваем соединение
            await configure_db_connection(db)
            
            async with db.execute('''
                SELECT o.*, o.user_id as telegram_id, u.username, u.first_name, u.last_name, m.email as manager_email, m.full_name as manager_name 
                FROM orders o 
                LEFT JOIN user_profiles u ON o.user_id = u.user_id 
                LEFT JOIN managers m ON o.assigned_manager_id = m.id 
                WHERE o.id = ?
            ''', (order_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(zip([column[0] for column in cursor.description], row))
                return None
    
    return await safe_db_operation(_get_operation)

async def get_user_active_order_by_user_id(user_id: int) -> Optional[Dict]:
    """Получает последний активный заказ пользователя (любого типа)"""
    async def _get_operation():
        async with aiosqlite.connect(DB_PATH) as db:
            # Настраиваем соединение
            await configure_db_connection(db)
            
            # Ищем последний заказ пользователя, который не завершен
            async with db.execute('''
                SELECT o.*, o.user_id as telegram_id, u.username, u.first_name, u.last_name, m.email as manager_email, m.full_name as manager_name 
                FROM orders o 
                LEFT JOIN user_profiles u ON o.user_id = u.user_id 
                LEFT JOIN managers m ON o.assigned_manager_id = m.id 
                WHERE o.user_id = ? 
                AND o.status NOT IN ('delivered', 'cancelled', 'completed')
                ORDER BY o.created_at DESC
                LIMIT 1
            ''', (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(zip([column[0] for column in cursor.description], row))
                return None
    
    return await safe_db_operation(_get_operation)

async def get_user_active_order(user_id: int, product: str) -> Optional[Dict]:
    """Получает активный заказ пользователя для указанного продукта"""
    async def _get_operation():
        async with aiosqlite.connect(DB_PATH) as db:
            # Настраиваем соединение
            await configure_db_connection(db)
            
            # Ищем заказ с указанным продуктом и статусом, который не является завершенным
            async with db.execute('''
                SELECT o.*, o.user_id as telegram_id, u.username, u.first_name, u.last_name, m.email as manager_email, m.full_name as manager_name 
                FROM orders o 
                LEFT JOIN user_profiles u ON o.user_id = u.user_id 
                LEFT JOIN managers m ON o.assigned_manager_id = m.id 
                WHERE o.user_id = ? 
                AND json_extract(o.order_data, '$.product') = ?
                AND o.status NOT IN ('completed', 'cancelled', 'refunded')
                ORDER BY o.created_at DESC
                LIMIT 1
            ''', (user_id, product)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(zip([column[0] for column in cursor.description], row))
                return None
    
    return await safe_db_operation(_get_operation)

async def get_last_order_by_user_and_product(user_id: int, product: str) -> Optional[Dict]:
    """Получает последний заказ пользователя для указанного продукта (включая завершенные)"""
    async def _get_operation():
        async with aiosqlite.connect(DB_PATH) as db:
            # Настраиваем соединение
            await configure_db_connection(db)
            
            # Ищем последний заказ с указанным продуктом (включая завершенные)
            async with db.execute('''
                SELECT o.*, o.user_id as telegram_id, u.username, u.first_name, u.last_name, m.email as manager_email, m.full_name as manager_name 
                FROM orders o 
                LEFT JOIN user_profiles u ON o.user_id = u.user_id 
                LEFT JOIN managers m ON o.assigned_manager_id = m.id 
                WHERE o.user_id = ? 
                AND json_extract(o.order_data, '$.product') = ?
                ORDER BY o.created_at DESC
                LIMIT 1
            ''', (user_id, product)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(zip([column[0] for column in cursor.description], row))
                return None
    
    return await safe_db_operation(_get_operation)

async def update_order_status(order_id: int, status: str, total_amount: float = None):
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем данные заказа до обновления
        cursor = await db.execute('''
            SELECT user_id, order_data, status as old_status FROM orders WHERE id = ?
        ''', (order_id,))
        order_data = await cursor.fetchone()
        
        if not order_data:
            return
        
        user_id, order_json, old_status = order_data
        
        # Обновляем статус заказа и total_amount если передан
        if total_amount is not None:
            await db.execute('''
                UPDATE orders SET status = ?, total_amount = ?, updated_at = datetime('now') WHERE id = ?
            ''', (status, total_amount, order_id))
        else:
            await db.execute('''
                UPDATE orders SET status = ?, updated_at = datetime('now') WHERE id = ?
            ''', (status, order_id))
        await db.commit()
        
        # Если статус изменился, обрабатываем таймеры
        if old_status != status:
            try:
                import json
                order_info = json.loads(order_json) if order_json else {}
                product_type = order_info.get('product', 'Unknown')
                
                # Создаем или обновляем таймер для нового этапа
                if status == 'demo_sent':
                    # Сначала деактивируем ВСЕ старые таймеры для этого заказа
                    await deactivate_user_timers(user_id, order_id)
                    
                    # Для статуса demo_sent создаем правильный таймер в зависимости от типа продукта
                    if product_type == 'Песня':
                        await create_or_update_user_timer(user_id, order_id, 'demo_received_song', product_type)
                    else:
                        await create_or_update_user_timer(user_id, order_id, 'demo_received_book', product_type)
                else:
                    await create_or_update_user_timer(user_id, order_id, status, product_type)
                
                # Деактивируем таймеры при завершающих статусах
                if status in ['paid', 'upsell_paid', 'ready', 'delivered', 'completed', 'cancelled', 'refunded']:
                    await deactivate_user_timers(user_id, order_id)
                    print(f"🔕 Таймеры деактивированы для заказа {order_id} при статусе {status}")
                
            except Exception as e:
                print(f"❌ Ошибка обработки таймеров для заказа {order_id}: {e}")

async def cleanup_trigger_messages_for_order(db, order_id: int, new_status: str):
    """
    Автоматически удаляет триггерные сообщения для заказа, которые больше не нужны
    при изменении статуса заказа
    """
    try:
        # Определяем, какие типы сообщений нужно удалить при определенных статусах
        messages_to_remove = []
        
        if new_status in ['paid', 'upsell_paid', 'ready', 'delivered', 'completed', 'payment_pending', 'waiting_draft', 'waiting_final', 'final_sent']:
            # Если заказ оплачен или в процессе работы, удаляем напоминания об оплате
            messages_to_remove.extend(['payment_reminder', 'final_reminder', 'payment_reminder_24h', 'payment_reminder_48h', 'abandoned_cart', 'payment_delay'])
        
        if new_status in ['cancelled', 'refunded']:
            # Если заказ отменен или возвращен, удаляем все триггерные сообщения
            messages_to_remove.extend(['demo_example', 'payment_reminder', 'final_reminder', 'payment_reminder_24h', 'payment_reminder_48h', 'delivery_reminder', 'abandoned_cart', 'payment_delay'])
        
        if new_status in ['demo_sent', 'draft_sent']:
            # Если демо или черновик уже отправлен, удаляем напоминания о демо
            messages_to_remove.extend(['demo_example', 'demo_reminder'])
        
        if new_status in ['waiting_feedback', 'feedback_processed']:
            # Если ожидается или обработан фидбек, удаляем напоминания о черновике
            messages_to_remove.extend(['draft_reminder', 'feedback_delay'])
        
        if new_status in ['waiting_delivery', 'delivered']:
            # Если заказ доставляется или доставлен, удаляем напоминания о доставке
            messages_to_remove.extend(['delivery_reminder', 'delivery_delay'])
        
        if new_status in ['waiting_cover_choice', 'cover_selected']:
            # Если обложка выбрана, удаляем напоминания о выборе обложки
            messages_to_remove.extend(['cover_reminder', 'cover_choice_delay'])
        
        if new_status in ['waiting_story_choice', 'story_selected']:
            # Если сюжет выбран, удаляем напоминания о выборе сюжета
            messages_to_remove.extend(['story_reminder', 'story_choice_delay'])
        
        if messages_to_remove:
            # Удаляем сообщения с указанными типами для данного заказа
            placeholders = ','.join(['?' for _ in messages_to_remove])
            await db.execute(f'''
                DELETE FROM delayed_messages 
                WHERE order_id = ? AND message_type IN ({placeholders})
            ''', [order_id] + messages_to_remove)
            
    except Exception as e:
        # Логируем ошибку, но не прерываем обновление статуса заказа
        print(f"⚠️ Ошибка при очистке триггерных сообщений для заказа {order_id}: {e}")

# Словарь для хранения локов для каждого заказа
_order_locks = {}

# Глобальный лок для базы данных
_db_lock = asyncio.Lock()

async def configure_db_connection(db):
    """Настраивает соединение с базой данных для лучшей производительности"""
    await db.execute('PRAGMA journal_mode=WAL')
    await db.execute('PRAGMA synchronous=NORMAL')
    await db.execute('PRAGMA cache_size=10000')
    await db.execute('PRAGMA temp_store=MEMORY')
    await db.execute('PRAGMA mmap_size=268435456')  # 256MB
    await db.execute('PRAGMA busy_timeout=30000')  # 30 секунд таймаут

async def safe_db_operation(operation, max_retries=3, delay=0.1):
    """Безопасно выполняет операцию с базой данных с повторными попытками"""
    for attempt in range(max_retries):
        try:
            async with _db_lock:
                return await operation()
        except aiosqlite.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                print(f"⚠️ База данных заблокирована, повторная попытка {attempt + 1}/{max_retries}")
                await asyncio.sleep(delay * (attempt + 1))
                continue
            else:
                print(f"❌ Ошибка базы данных: {e}")
                raise e
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
            raise e

async def update_order_data(order_id: int, order_data: dict):
    """Обновляет данные заказа, мерджа с существующими данными"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем существующие данные
        cursor = await db.execute('SELECT order_data FROM orders WHERE id = ?', (order_id,))
        row = await cursor.fetchone()
        
        if row and row[0]:
            try:
                existing_data = json.loads(row[0])
            except json.JSONDecodeError:
                existing_data = {}
        else:
            existing_data = {}
        
        # Мерджим новые данные с существующими
        merged_data = {**existing_data, **order_data}
        
        # Подготавливаем данные для обновления
        update_data = [json.dumps(merged_data), order_id]
        update_query = 'UPDATE orders SET order_data = ?, updated_at = datetime(\'now\')'
        
        # Если есть sender_name, добавляем его в отдельную колонку
        if 'sender_name' in order_data:
            update_query += ', sender_name = ?'
            update_data.insert(1, order_data['sender_name'])
        
        update_query += ' WHERE id = ?'
        
        await db.execute(update_query, update_data)
        await db.commit()

async def get_order_data_debug(order_id: int) -> dict:
    """Функция для отладки - возвращает данные заказа с информацией о пользователе"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем данные заказа и пользователя, включая отдельные колонки
        cursor = await db.execute('''
            SELECT o.order_data, o.first_page_text, o.last_page_text, o.first_last_design, o.sender_name,
                   u.username, u.first_name, u.last_name
            FROM orders o 
            LEFT JOIN user_profiles u ON o.user_id = u.user_id 
            WHERE o.id = ?
        ''', (order_id,))
        row = await cursor.fetchone()
        
        if row:
            order_data, first_page_text, last_page_text, first_last_design, sender_name, username, first_name, last_name = row
            print(f"🔍 ОТЛАДКА get_order_data_debug: first_page_text='{first_page_text}', last_page_text='{last_page_text}'")
            
            # Парсим order_data
            if order_data:
                try:
                    data = json.loads(order_data)
                except json.JSONDecodeError:
                    data = {}
            else:
                data = {}
            
            # Добавляем данные пользователя
            data['username'] = username
            data['first_name'] = first_name
            data['last_name'] = last_name
            
            # Добавляем данные из отдельных колонок
            if first_page_text:
                data['first_page_text'] = first_page_text
            if last_page_text:
                data['last_page_text'] = last_page_text
            if first_last_design:
                data['first_last_design'] = first_last_design
            if sender_name:
                data['sender_name'] = sender_name
            
            return data
        return {}
async def save_selected_pages(order_id: int, selected_pages: list):
    """Сохраняет выбранные пользователем страницы в базу данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем текущие данные заказа
        cursor = await db.execute('SELECT order_data FROM orders WHERE id = ?', (order_id,))
        row = await cursor.fetchone()
        if row and row[0]:
            try:
                existing_data = json.loads(row[0])
            except json.JSONDecodeError:
                existing_data = {}
        else:
            existing_data = {}
        
        # Добавляем выбранные страницы
        existing_data["selected_pages"] = selected_pages
        existing_data["pages_selection_completed"] = True
        existing_data["pages_selection_date"] = datetime.now().isoformat()
        
        # Обновляем заказ
        await db.execute('''
            UPDATE orders SET order_data = ?, updated_at = datetime('now') WHERE id = ?
        ''', (json.dumps(existing_data), order_id))
        await db.commit()
        
        # Логируем изменение статуса
        await log_order_status_change(order_id, "pages_selected", f"Выбрано {len(selected_pages)} страниц")

async def update_order_files(order_id: int, pdf_path: str = None, mp3_path: str = None):
    async def _update_operation():
        async with aiosqlite.connect(DB_PATH) as db:
            # Настраиваем соединение
            await configure_db_connection(db)
            
            if pdf_path:
                await db.execute("UPDATE orders SET pdf_path = ?, updated_at = datetime('now') WHERE id = ?", (pdf_path, order_id))
            if mp3_path:
                await db.execute("UPDATE orders SET mp3_path = ?, updated_at = datetime('now') WHERE id = ?", (mp3_path, order_id))
            await db.commit()
    
    await safe_db_operation(_update_operation) 

# --- Работа с outbox (очередь отправки) ---

async def add_outbox_task(order_id: int, user_id: int, type_: str, content: str, file_type: str = None, comment: str = None, button_text: str = None, button_callback: str = None, is_general_message: bool = False):
    async def _add_operation():
        async with aiosqlite.connect(DB_PATH) as db:
            # Настраиваем соединение
            await configure_db_connection(db)
            
            await db.execute('''
                INSERT INTO outbox (order_id, user_id, type, content, file_type, comment, button_text, button_callback, is_general_message, status, created_at, retry_count, max_retries)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', datetime('now'), 0, 3)
            ''', (order_id, user_id, type_, content, file_type, comment, button_text, button_callback, 1 if is_general_message else 0))
            await db.commit()
    
    await safe_db_operation(_add_operation)

async def get_pending_outbox_tasks():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Логируем все задачи в outbox для диагностики
        debug_cursor = await db.execute('''
            SELECT id, order_id, user_id, type, status, retry_count, max_retries, created_at 
            FROM outbox 
            ORDER BY created_at DESC 
            LIMIT 10
        ''')
        debug_tasks = await debug_cursor.fetchall()
        print(f"🔍 ДИАГНОСТИКА OUTBOX: всего последних 10 задач:")
        for task in debug_tasks:
            print(f"   ID={task['id']}, status={task['status']}, retry={task['retry_count']}, max={task['max_retries']}, type={task['type']}")
        
        cursor = await db.execute('''
            SELECT id, order_id, user_id, type, content, file_type, comment, button_text, button_callback, 
                   COALESCE(is_general_message, 0) as is_general_message, created_at, COALESCE(retry_count, 0) as retry_count, COALESCE(max_retries, 3) as max_retries
            FROM outbox 
            WHERE status = 'pending' AND (COALESCE(retry_count, 0) < COALESCE(max_retries, 3))
            ORDER BY created_at ASC
        ''')
        tasks = await cursor.fetchall()
        print(f"🔍 НАЙДЕНО PENDING ЗАДАЧ: {len(tasks)}")
        return [dict(task) for task in tasks]

async def update_outbox_task_status(task_id: int, status: str):
    async def _update_operation():
        async with aiosqlite.connect(DB_PATH) as db:
            # Настраиваем соединение
            await configure_db_connection(db)
            
            await db.execute('''
                UPDATE outbox SET status = ?, sent_at = datetime('now') WHERE id = ?
            ''', (status, task_id))
            await db.commit()
    
    await safe_db_operation(_update_operation)

async def increment_outbox_retry_count(task_id: int):
    """Увеличивает счетчик попыток для задачи"""
    async def _increment_operation():
        async with aiosqlite.connect(DB_PATH) as db:
            await configure_db_connection(db)
            
            await db.execute('''
                UPDATE outbox SET retry_count = retry_count + 1 WHERE id = ?
            ''', (task_id,))
            await db.commit()
    
    await safe_db_operation(_increment_operation)

# --- Работа с шаблонами сообщений (новая система) ---

async def create_message_template(name: str, message_type: str, content: str, order_step: str, delay_minutes: int = 0, manager_id: int = None):
    """Создает новый шаблон сообщения"""
    async def _create_operation():
        async with aiosqlite.connect(DB_PATH) as db:
            await configure_db_connection(db)
            
            await db.execute('''
                INSERT INTO message_templates 
                (name, message_type, content, order_step, delay_minutes, manager_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, message_type, content, order_step, delay_minutes, manager_id))
            await db.commit()
            
            cursor = await db.execute('SELECT last_insert_rowid()')
            result = await cursor.fetchone()
            return result[0] if result else None
    
    return await safe_db_operation(_create_operation)

async def get_message_templates() -> List[Dict]:
    """Получает все активные шаблоны сообщений"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT mt.*, m.email as manager_email, m.full_name as manager_name
            FROM message_templates mt
            LEFT JOIN managers m ON mt.manager_id = m.id
            WHERE mt.is_active = 1
            ORDER BY mt.order_step, mt.delay_minutes
        ''')
        rows = await cursor.fetchall()
        return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def get_message_template_by_id(template_id: int) -> Optional[Dict]:
    """Получает шаблон сообщения по ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT mt.*, m.email as manager_email, m.full_name as manager_name
            FROM message_templates mt
            LEFT JOIN managers m ON mt.manager_id = m.id
            WHERE mt.id = ?
        ''', (template_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def update_message_template(template_id: int, name: str, content: str, delay_minutes: int, message_type: str, order_step: str = None) -> bool:
    """Обновляет шаблон сообщения"""
    async def _update_operation():
        async with aiosqlite.connect(DB_PATH) as db:
            await configure_db_connection(db)
            
            if order_step is not None:
                await db.execute('''
                    UPDATE message_templates 
                    SET name = ?, content = ?, delay_minutes = ?, message_type = ?, order_step = ?, updated_at = datetime('now')
                    WHERE id = ?
                ''', (name, content, delay_minutes, message_type, order_step, template_id))
            else:
                await db.execute('''
                    UPDATE message_templates 
                    SET name = ?, content = ?, delay_minutes = ?, message_type = ?, updated_at = datetime('now')
                    WHERE id = ?
                ''', (name, content, delay_minutes, message_type, template_id))
            await db.commit()
            
            return True
    
    return await safe_db_operation(_update_operation)

async def delete_message_template(template_id: int) -> bool:
    """Удаляет шаблон сообщения"""
    async def _delete_operation():
        async with aiosqlite.connect(DB_PATH) as db:
            await configure_db_connection(db)
            
            await db.execute('DELETE FROM message_templates WHERE id = ?', (template_id,))
            await db.commit()
            
            return True
    
    return await safe_db_operation(_delete_operation)

async def get_template_by_step_and_delay(order_step: str, delay_minutes: int) -> Optional[Dict]:
    """Получает шаблон сообщения для определенного шага и задержки"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM message_templates 
            WHERE order_step = ? AND delay_minutes = ? AND is_active = 1
            LIMIT 1
        ''', (order_step, delay_minutes))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def is_message_sent_to_user(template_id: int, user_id: int, order_id: int) -> bool:
    """Проверяет, было ли сообщение уже отправлено пользователю"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            SELECT COUNT(*) FROM sent_messages_log 
            WHERE template_id = ? AND user_id = ? AND order_id = ?
        ''', (template_id, user_id, order_id))
        result = await cursor.fetchone()
        return result[0] > 0 if result else False

async def log_message_sent(template_id: int, user_id: int, order_id: int):
    """Записывает факт отправки сообщения пользователю"""
    async def _log_operation():
        async with aiosqlite.connect(DB_PATH) as db:
            await configure_db_connection(db)
            
            await db.execute('''
                INSERT INTO sent_messages_log (template_id, user_id, order_id)
                VALUES (?, ?, ?)
            ''', (template_id, user_id, order_id))
            await db.commit()
    
    return await safe_db_operation(_log_operation)

async def get_users_on_step(order_step: str, delay_minutes: int = 0) -> List[Dict]:
    """Получает всех пользователей, которые находятся на определенном шаге заказа указанное время"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Вычисляем время, когда пользователь должен был попасть на этот шаг
        target_time = datetime.now() - timedelta(minutes=delay_minutes)
        
        # Определяем реальный статус и тип продукта из order_step
        if order_step == "song_collecting_facts":
            # Для песен ищем статус collecting_facts с продуктом "Песня"
            logging.info(f"🔍 Ищем пользователей для song_collecting_facts, delay_minutes={delay_minutes}, target_time={target_time}")
            cursor = await db.execute('''
                SELECT DISTINCT o.id as order_id, o.user_id, o.order_data, o.created_at, o.updated_at
                FROM orders o
                WHERE o.status = 'collecting_facts'
                AND o.updated_at <= ?
                AND o.status NOT IN ('completed', 'cancelled', 'failed', 'paid', 'upsell_paid', 'ready', 'delivered')
                AND JSON_EXTRACT(o.order_data, '$.product') = 'Песня'
            ''', (target_time.isoformat(),))
        elif order_step == "book_collecting_facts":
            # Для книг ищем статус collecting_facts с продуктом "Книга"
            cursor = await db.execute('''
                SELECT DISTINCT o.id as order_id, o.user_id, o.order_data, o.created_at, o.updated_at
                FROM orders o
                WHERE o.status = 'collecting_facts'
                AND o.updated_at <= ?
                AND o.status NOT IN ('completed', 'cancelled', 'failed', 'paid', 'upsell_paid', 'ready', 'delivered')
                AND JSON_EXTRACT(o.order_data, '$.product') = 'Книга'
            ''', (target_time.isoformat(),))
        else:
            # Для остальных шагов используем старую логику
            cursor = await db.execute('''
                SELECT DISTINCT o.id as order_id, o.user_id, o.order_data, o.created_at, o.updated_at
                FROM orders o
                WHERE o.status = ? 
                AND o.updated_at <= ?
                AND o.status NOT IN ('completed', 'cancelled', 'failed', 'paid', 'upsell_paid', 'ready', 'delivered')
            ''', (order_step, target_time.isoformat()))
        
        rows = await cursor.fetchall()
        result = [dict(zip([column[0] for column in cursor.description], row)) for row in rows]
        logging.info(f"🔍 Найдено {len(result)} пользователей для order_step={order_step}, delay_minutes={delay_minutes}")
        return result

# --- Работа с отложенными сообщениями (старая система) ---

async def add_delayed_message(order_id: Optional[int], user_id: Optional[int], message_type: str, content: str, delay_minutes: int, manager_id: int = None, is_automatic: bool = False, order_step: str = None, story_batch: int = 0, story_pages: str = None, selected_stories: str = None):
    print(f"🔍 ОТЛАДКА: add_delayed_message вызвана с параметрами:")
    print(f"🔍 order_id: {order_id}, user_id: {user_id}, message_type: {message_type}")
    print(f"🔍 delay_minutes: {delay_minutes}, content: {content[:100]}...")
    
    async def _add_operation():
        async with aiosqlite.connect(DB_PATH) as db:
            # Настраиваем соединение
            await configure_db_connection(db)
            
            # Вычисляем scheduled_at на основе delay_minutes
            if delay_minutes > 0:
                scheduled_time = datetime.now() + timedelta(minutes=delay_minutes)
            else:
                scheduled_time = datetime.now()
            
            # Устанавливаем статус на основе задержки
            if delay_minutes > 0:
                status = 'pending'  # Ожидает отправки
            else:
                status = 'pending'   # Для немедленной отправки тоже используем pending
            
            await db.execute('''
                INSERT INTO delayed_messages 
                (order_id, user_id, manager_id, message_type, content, delay_minutes, status, scheduled_at, is_automatic, order_step, story_batch, story_pages, selected_stories)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (order_id, user_id, manager_id, message_type, content, delay_minutes, status, scheduled_time, is_automatic, order_step, story_batch, story_pages, selected_stories))
            await db.commit()
            
            cursor = await db.execute('SELECT last_insert_rowid()')
            result = await cursor.fetchone()
            return result[0] if result else None
    
    return await safe_db_operation(_add_operation)
async def add_delayed_message_file(delayed_message_id: int, file_path: str, file_type: str, file_name: str, file_size: int):
    """Добавляет файл к отложенному сообщению (сохраняет в обе таблицы)"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Сохраняем в delayed_message_files (старая система)
        await db.execute('''
            INSERT INTO delayed_message_files (delayed_message_id, file_path, file_type, file_name, file_size, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        ''', (delayed_message_id, file_path, file_type, file_name, file_size))
        
        # Также сохраняем в message_template_files (новая система)
        # Сначала получаем данные отложенного сообщения
        cursor = await db.execute('''
            SELECT message_type, content FROM delayed_messages WHERE id = ?
        ''', (delayed_message_id,))
        delayed_msg = await cursor.fetchone()
        
        if delayed_msg:
            message_type = delayed_msg[0]
            content = delayed_msg[1]
            
            # Ищем соответствующий шаблон
            cursor = await db.execute('''
                SELECT id FROM message_templates 
                WHERE message_type = ? AND content = ? AND is_active = 1
            ''', (message_type, content))
            template = await cursor.fetchone()
            
            template_id = None
            if template:
                template_id = template[0]
            else:
                # Создаем шаблон, если его нет
                # Определяем order_step по типу сообщения
                order_step = None
                if 'book_filling_reminder' in message_type:
                    order_step = 'book_collecting_facts'
                elif 'song_filling_reminder' in message_type:
                    order_step = 'song_collecting_facts'
                elif 'song_warming' in message_type:
                    order_step = 'waiting_full_song'
                elif 'payment_reminder' in message_type:
                    order_step = 'waiting_payment'
                elif 'demo_example' in message_type:
                    order_step = 'waiting_demo_song'
                elif 'answering_questions' in message_type:
                    order_step = 'answering_questions'
                else:
                    order_step = 'product_selected'  # По умолчанию
                
                # Создаем шаблон
                cursor = await db.execute('''
                    INSERT INTO message_templates 
                    (name, message_type, content, order_step, delay_minutes, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?, 1, datetime('now'))
                ''', (f"Авто-шаблон {message_type}", message_type, content, order_step, 0))
                template_id = cursor.lastrowid
            
            if template_id:
                # Проверяем, нет ли уже такого файла
                cursor = await db.execute('''
                    SELECT id FROM message_template_files 
                    WHERE template_id = ? AND file_name = ? AND file_path = ?
                ''', (template_id, file_name, file_path))
                existing = await cursor.fetchone()
                
                if not existing:
                    await db.execute('''
                        INSERT INTO message_template_files (template_id, file_path, file_type, file_name, file_size, created_at)
                        VALUES (?, ?, ?, ?, ?, datetime('now'))
                    ''', (template_id, file_path, file_type, file_name, file_size))
        
        await db.commit()

async def create_payment_reminder_messages(order_id: int, user_id: int):
    """Создает отложенные напоминания об оплате
    
    Args:
        order_id: ID заказа
        user_id: ID пользователя
    """
    try:
        # Получаем данные заказа для персонализации
        order = await get_order(order_id)
        if not order:
            logging.warning(f"⚠️ Заказ {order_id} не найден при создании напоминаний об оплате")
            return
        
        # Текст напоминания об оплате
        reminder_text = """💳 <b>Напоминание об оплате</b>

Вы начали оформление заказа, но не завершили оплату.

Для завершения заказа нажмите кнопку ниже 👇"""
        
        # Создаем напоминания с разными интервалами
        # Обычно: через 30 минут, 2 часа, 6 часов, 24 часа
        reminders = [
            (30, "payment_reminder_30min"),
            (120, "payment_reminder_2h"),
            (360, "payment_reminder_6h"),
            (1440, "payment_reminder_24h")
        ]
        
        for delay_minutes, message_type in reminders:
            await add_delayed_message(
                order_id=order_id,
                user_id=user_id,
                message_type=message_type,
                content=reminder_text,
                delay_minutes=delay_minutes,
                is_automatic=True,
                order_step='waiting_payment'
            )
        
        logging.info(f"✅ Созданы напоминания об оплате для заказа {order_id}, пользователь {user_id}")
        
    except Exception as e:
        logging.error(f"❌ Ошибка создания напоминаний об оплате для заказа {order_id}: {e}")

async def get_delayed_message_files(delayed_message_id: int) -> List[Dict]:
    """Получает все файлы отложенного сообщения"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT * FROM delayed_message_files WHERE delayed_message_id = ? ORDER BY created_at ASC
        ''', (delayed_message_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def get_delayed_message_files_by_type(message_type: str) -> List[Dict]:
    """Получает все файлы отложенных сообщений по типу сообщения"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT dmf.* FROM delayed_message_files dmf
            JOIN delayed_messages dm ON dmf.delayed_message_id = dm.id
            WHERE dm.message_type = ? AND dm.status = 'pending'
            ORDER BY dmf.created_at ASC
        ''', (message_type,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def get_delayed_messages_by_type(message_type: str) -> List[Dict]:
    """Получает все отложенные сообщения по типу сообщения"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT * FROM delayed_messages WHERE message_type = ? AND status = 'pending'
            ORDER BY created_at ASC
        ''', (message_type,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def get_delayed_message_files_by_content(content: str) -> List[Dict]:
    """Получает файлы отложенного сообщения по содержимому"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT dmf.* FROM delayed_message_files dmf
            JOIN delayed_messages dm ON dmf.delayed_message_id = dm.id
            WHERE dm.content = ? AND dm.status = 'pending'
            ORDER BY dmf.created_at ASC
        ''', (content,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def get_delayed_message_files_by_message_type(message_type: str) -> List[Dict]:
    """Получает файлы отложенного сообщения по типу сообщения"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT dmf.* FROM delayed_message_files dmf
            JOIN delayed_messages dm ON dmf.delayed_message_id = dm.id
            WHERE dm.message_type = ? AND dm.status = 'pending'
            ORDER BY dmf.created_at ASC
        ''', (message_type,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def add_message_template_file(template_id: int, file_path: str, file_type: str, file_name: str, file_size: int):
    """Добавляет файл к шаблону сообщения"""
    import logging
    logging.info(f"🔧 Добавляем файл к шаблону {template_id}: {file_name} ({file_type})")
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем текущие файлы из колонки files
        cursor = await db.execute('SELECT files FROM message_templates WHERE id = ?', (template_id,))
        row = await cursor.fetchone()
        current_files = []
        
        import json
        
        if row and row[0]:
            try:
                current_files = json.loads(row[0])
                logging.info(f"📁 Найдено {len(current_files)} существующих файлов в колонке 'files'")
            except Exception as e:
                logging.warning(f"⚠️ Ошибка парсинга существующих файлов: {e}")
                current_files = []
        else:
            logging.info(f"📁 Колонка 'files' пустая, создаем новый список")
        
        # Добавляем новый файл
        new_file = {
            "file_path": file_path,
            "file_type": file_type,
            "file_name": file_name,
            "file_size": file_size,
            "created_at": "now"
        }
        current_files.append(new_file)
        
        # Сохраняем обновленный список файлов в колонку files
        files_json = json.dumps(current_files)
        await db.execute('''
            UPDATE message_templates SET files = ? WHERE id = ?
        ''', (files_json, template_id))
        logging.info(f"✅ Сохранено {len(current_files)} файлов в колонку 'files'")
        
        # Также сохраняем в старую таблицу для совместимости (если она существует)
        try:
            # Проверяем, существует ли таблица
            cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='message_template_files'")
            table_exists = await cursor.fetchone()
            
            if table_exists:
                await db.execute('''
                    INSERT INTO message_template_files (template_id, file_path, file_type, file_name, file_size, created_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                ''', (template_id, file_path, file_type, file_name, file_size))
                logging.info(f"✅ Файл также сохранен в старую таблицу 'message_template_files'")
            else:
                logging.info(f"ℹ️ Таблица 'message_template_files' не существует, пропускаем")
        except Exception as e:
            logging.warning(f"⚠️ Ошибка сохранения в старую таблицу: {e}")
        
        await db.commit()
        logging.info(f"✅ Файл успешно добавлен к шаблону {template_id}")

async def get_message_template_files(template_id: int) -> List[Dict]:
    """Получает все файлы шаблона сообщения (объединяет из новой колонки и старой таблицы)"""
    async with aiosqlite.connect(DB_PATH) as db:
        all_files = []
        
        # Получаем файлы из новой колонки files
        async with db.execute('''
            SELECT files FROM message_templates WHERE id = ?
        ''', (template_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                import json
                try:
                    files_data = json.loads(row[0])
                    if isinstance(files_data, list):
                        all_files.extend(files_data)
                        logging.info(f"📁 Найдено {len(files_data)} файлов в новой колонке 'files' для шаблона {template_id}")
                except Exception as e:
                    logging.warning(f"⚠️ Ошибка парсинга JSON файлов для шаблона {template_id}: {e}")
        
        # Получаем файлы из старой таблицы message_template_files (если она существует)
        # Но только если их нет в новой колонке files
        try:
            cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='message_template_files'")
            table_exists = await cursor.fetchone()
            
            if table_exists:
                # Получаем имена файлов из новой колонки для проверки дублирования
                new_file_names = {f.get('file_name', '') for f in all_files}
                
                async with db.execute('''
                    SELECT * FROM message_template_files WHERE template_id = ? ORDER BY created_at ASC
                ''', (template_id,)) as cursor:
                    rows = await cursor.fetchall()
                    old_files = [dict(zip([column[0] for column in cursor.description], row)) for row in rows]
                    
                    # Добавляем только те файлы, которых нет в новой колонке
                    unique_old_files = []
                    for old_file in old_files:
                        old_file_name = old_file.get('file_name', '')
                        if old_file_name not in new_file_names:
                            unique_old_files.append(old_file)
                    
                    all_files.extend(unique_old_files)
                    if unique_old_files:
                        logging.info(f"📁 Найдено {len(unique_old_files)} уникальных файлов в старой таблице 'message_template_files' для шаблона {template_id}")
                    elif old_files:
                        logging.info(f"ℹ️ Все файлы из старой таблицы уже есть в новой колонке, пропускаем дублирование")
            else:
                logging.info(f"ℹ️ Таблица 'message_template_files' не существует, пропускаем")
        except Exception as e:
            logging.warning(f"⚠️ Ошибка при обращении к старой таблице: {e}")
        
        # Получаем файлы из таблицы delayed_message_files по содержимому
        async with db.execute('''
            SELECT content FROM message_templates WHERE id = ?
        ''', (template_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                content = row[0]
                
                async with db.execute('''
                    SELECT dmf.* FROM delayed_message_files dmf
                    JOIN delayed_messages dm ON dmf.delayed_message_id = dm.id
                    WHERE dm.content = ?
                    ORDER BY dmf.created_at ASC
                ''', (content,)) as cursor:
                    rows = await cursor.fetchall()
                    delayed_files = [dict(zip([column[0] for column in cursor.description], row)) for row in rows]
                    
                    # Проверяем дублирование по пути к файлу
                    existing_paths = {f.get('file_path', '') for f in all_files}
                    unique_delayed_files = []
                    
                    for delayed_file in delayed_files:
                        delayed_file_path = delayed_file.get('file_path', '')
                        if delayed_file_path not in existing_paths:
                            unique_delayed_files.append(delayed_file)
                            existing_paths.add(delayed_file_path)
                    
                    all_files.extend(unique_delayed_files)
                    if unique_delayed_files:
                        logging.info(f"📁 Найдено {len(unique_delayed_files)} уникальных файлов в таблице 'delayed_message_files' для шаблона {template_id}")
                    elif delayed_files:
                        logging.info(f"ℹ️ Все файлы из delayed_message_files уже есть в других источниках, пропускаем дублирование")
        
        logging.info(f"📁 Итого файлов для шаблона {template_id}: {len(all_files)}")
        return all_files

async def delete_message_template_files(template_id: int):
    """Удаляет все файлы шаблона сообщения"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Сначала удаляем физические файлы
        files = await get_message_template_files(template_id)
        for file_info in files:
            try:
                if os.path.exists(file_info['file_path']):
                    os.remove(file_info['file_path'])
            except Exception as e:
                logging.warning(f"Не удалось удалить файл {file_info['file_path']}: {e}")
        
        # Очищаем колонку files в message_templates
        await db.execute('UPDATE message_templates SET files = NULL WHERE id = ?', (template_id,))
        
        # Удаляем записи из старой таблицы
        await db.execute('DELETE FROM message_template_files WHERE template_id = ?', (template_id,))
        await db.commit()

async def delete_message_template_file(file_id: int) -> bool:
    """Удаляет файл шаблона сообщения по ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM message_template_files WHERE id = ?', (file_id,))
        await db.commit()
        return True

async def delete_message_template_file_by_name(template_id: int, file_name: str) -> bool:
    """Удаляет файл шаблона сообщения по имени файла"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем текущие файлы из колонки files
        cursor = await db.execute('SELECT files FROM message_templates WHERE id = ?', (template_id,))
        row = await cursor.fetchone()
        current_files = []
        
        if row and row[0]:
            import json
            try:
                current_files = json.loads(row[0])
            except:
                current_files = []
        
        # Удаляем файл из списка
        updated_files = [f for f in current_files if f.get('file_name') != file_name]
        
        # Сохраняем обновленный список
        files_json = json.dumps(updated_files)
        await db.execute('''
            UPDATE message_templates SET files = ? WHERE id = ?
        ''', (files_json, template_id))
        
        # Также удаляем из старой таблицы
        await db.execute('''
            DELETE FROM message_template_files 
            WHERE template_id = ? AND file_name = ?
        ''', (template_id, file_name))
        
        await db.commit()
        return True
async def delete_delayed_message_file(file_id: int) -> bool:
    """Удаляет файл отложенного сообщения"""
    async def _delete_operation():
        async with aiosqlite.connect(DB_PATH) as db:
            await configure_db_connection(db)
            
            # Сначала получаем информацию о файле для удаления с диска
            cursor = await db.execute('''
                SELECT file_path FROM delayed_message_files WHERE id = ?
            ''', (file_id,))
            file_row = await cursor.fetchone()
            
            if file_row:
                file_path = file_row[0]
                # Удаляем файл с диска
                try:
                    import os
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f"Ошибка удаления файла с диска: {e}")
                
                # Удаляем запись из базы данных
                await db.execute('''
                    DELETE FROM delayed_message_files WHERE id = ?
                ''', (file_id,))
                await db.commit()
                return True
            return False
    
    return await safe_db_operation(_delete_operation)

async def delete_delayed_message_file_by_name(delayed_message_id: int, file_name: str) -> bool:
    """Удаляет файл отложенного сообщения по имени"""
    async def _delete_operation():
        async with aiosqlite.connect(DB_PATH) as db:
            await configure_db_connection(db)
            
            # Сначала получаем информацию о файле для удаления с диска
            cursor = await db.execute('''
                SELECT id, file_path FROM delayed_message_files 
                WHERE delayed_message_id = ? AND file_name = ?
            ''', (delayed_message_id, file_name))
            file_row = await cursor.fetchone()
            
            if file_row:
                file_id, file_path = file_row
                # Удаляем файл с диска
                try:
                    import os
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f"Ошибка удаления файла с диска: {e}")
                
                # Удаляем запись из базы данных
                await db.execute('''
                    DELETE FROM delayed_message_files WHERE id = ?
                ''', (file_id,))
                await db.commit()
                return True
            return False
    
    return await safe_db_operation(_delete_operation)

# --- Работа с таймерами пользователей на этапах ---

async def create_or_update_user_timer(user_id: int, order_id: int, order_step: str, product_type: str = None) -> bool:
    """Создает или обновляет таймер пользователя на этапе"""
    async def _timer_operation():
        async with aiosqlite.connect(DB_PATH) as db:
            await configure_db_connection(db)
            
            # Проверяем, есть ли уже таймер для этого пользователя/заказа/этапа (активный или нет)
            cursor = await db.execute('''
                SELECT id, is_active FROM user_step_timers 
                WHERE user_id = ? AND order_id = ? AND order_step = ?
            ''', (user_id, order_id, order_step))
            existing = await cursor.fetchone()
            
            if existing:
                # Обновляем существующий таймер (делаем активным, обновляем время)
                await db.execute('''
                    UPDATE user_step_timers 
                    SET step_started_at = CURRENT_TIMESTAMP,
                        step_updated_at = CURRENT_TIMESTAMP,
                        product_type = COALESCE(?, product_type),
                        is_active = 1
                    WHERE id = ?
                ''', (product_type, existing[0]))
                print(f"✅ Обновлен таймер для пользователя {user_id}, заказ {order_id}, этап {order_step}")
            else:
                # Деактивируем старые таймеры для этого пользователя/заказа
                await db.execute('''
                    UPDATE user_step_timers 
                    SET is_active = 0 
                    WHERE user_id = ? AND order_id = ? AND is_active = 1
                ''', (user_id, order_id))
                
                # Создаем новый таймер
                await db.execute('''
                    INSERT INTO user_step_timers 
                    (user_id, order_id, order_step, product_type, step_started_at, step_updated_at, is_active)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
                ''', (user_id, order_id, order_step, product_type))
                print(f"✅ Создан новый таймер для пользователя {user_id}, заказ {order_id}, этап {order_step}")
            
            await db.commit()
            return True
    
    return await safe_db_operation(_timer_operation)

async def get_users_ready_for_messages() -> List[Dict]:
    """Получает пользователей, готовых для получения отложенных сообщений"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Получаем все активные таймеры с шаблонами сообщений, исключая уже отправленные
        cursor = await db.execute('''
            SELECT DISTINCT
                t.id as timer_id,
                t.user_id,
                t.order_id,
                t.order_step,
                t.product_type,
                t.step_started_at,
                mt.id as template_id,
                mt.message_type,
                mt.content,
                mt.delay_minutes,
                mt.name as template_name
            FROM user_step_timers t
            JOIN message_templates mt ON (
                (t.order_step = 'product_selected' AND mt.order_step = 'product_selected') OR
                (t.order_step = 'collecting_facts' AND t.product_type = 'Песня' AND mt.order_step = 'song_collecting_facts') OR
                (t.order_step = 'collecting_facts' AND t.product_type = 'Книга' AND mt.order_step = 'book_collecting_facts') OR
                (t.order_step = 'waiting_demo_song' AND mt.order_step = 'waiting_demo_song') OR
                (t.order_step = 'waiting_demo_book' AND mt.order_step = 'waiting_demo_book') OR
                (t.order_step = 'demo_received_song' AND mt.order_step = 'demo_received_song') OR
                (t.order_step = 'demo_received_book' AND mt.order_step = 'demo_received_book') OR
                (t.order_step = 'story_selection' AND mt.order_step = 'story_selection') OR
                (t.order_step = 'answering_questions' AND mt.order_step = 'answering_questions') OR
                (t.order_step = 'waiting_full_song' AND mt.order_step = 'waiting_full_song') OR
                (t.order_step = 'waiting_main_book' AND mt.order_step = 'waiting_main_book') OR
                (t.order_step = mt.order_step)
            )
            LEFT JOIN timer_messages_sent tms ON (
                t.id = tms.timer_id AND 
                mt.id = tms.template_id AND 
                mt.delay_minutes = tms.delay_minutes
            )
            WHERE t.is_active = 1 
            AND mt.is_active = 1
            AND datetime(t.step_started_at, '+' || mt.delay_minutes || ' minutes') <= datetime('now')
            AND tms.id IS NULL
            ORDER BY t.step_started_at ASC, mt.delay_minutes ASC
        ''')
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def is_timer_message_sent(timer_id: int, template_id: int, delay_minutes: int) -> bool:
    """Проверяет, было ли уже отправлено сообщение для данного таймера/шаблона/задержки"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            SELECT id FROM timer_messages_sent 
            WHERE timer_id = ? AND template_id = ? AND delay_minutes = ?
        ''', (timer_id, template_id, delay_minutes))
        result = await cursor.fetchone()
        return result is not None

async def log_timer_message_sent(timer_id: int, template_id: int, user_id: int, order_id: int, message_type: str, delay_minutes: int) -> bool:
    """Записывает факт отправки сообщения по таймеру"""
    async def _log_operation():
        async with aiosqlite.connect(DB_PATH) as db:
            await configure_db_connection(db)
            
            await db.execute('''
                INSERT OR IGNORE INTO timer_messages_sent 
                (timer_id, template_id, user_id, order_id, message_type, delay_minutes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (timer_id, template_id, user_id, order_id, message_type, delay_minutes))
            await db.commit()
            return True
    
    return await safe_db_operation(_log_operation)

async def deactivate_user_timers(user_id: int, order_id: int) -> bool:
    """Деактивирует все таймеры пользователя для заказа (при оплате или завершении)"""
    async def _deactivate_operation():
        async with aiosqlite.connect(DB_PATH) as db:
            await configure_db_connection(db)
            
            await db.execute('''
                UPDATE user_step_timers 
                SET is_active = 0 
                WHERE user_id = ? AND order_id = ?
            ''', (user_id, order_id))
            await db.commit()
            
            cursor = await db.execute('SELECT changes()')
            changes = await cursor.fetchone()
            print(f"✅ Деактивировано {changes[0]} таймеров для пользователя {user_id}, заказ {order_id}")
            return True
    
    return await safe_db_operation(_deactivate_operation)

async def get_active_timers_for_order(order_id: int) -> List[Dict]:
    """Получает все активные таймеры для заказа"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT id, user_id, order_id, order_step, product_type, step_started_at, is_active
            FROM user_step_timers 
            WHERE order_id = ? AND is_active = 1
            ORDER BY step_started_at DESC
        ''', (order_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_pending_delayed_messages():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT id, order_id, user_id, message_type, content, delay_minutes, created_at, scheduled_at, is_automatic, order_step, is_active, usage_count, last_used
            FROM delayed_messages 
            WHERE status = 'pending' AND scheduled_at <= datetime('now') AND is_active = 1
            ORDER BY scheduled_at ASC
        ''')
        messages = await cursor.fetchall()
        print(f"🔍 ОТЛАДКА: get_pending_delayed_messages найдено: {len(messages)}")
        for message in messages:
            print(f"🔍 ОТЛАДКА: Сообщение {message['id']}, тип: {message['message_type']}, автоматическое: {message['is_automatic']}, шаг: {message['order_step']}, активен: {message['is_active']}, запланировано: {message['scheduled_at']}")
        return [dict(message) for message in messages]

async def get_delayed_message_templates() -> List[Dict]:
    """Получает все шаблоны отложенных сообщений из новой таблицы message_templates"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Сначала проверяем, существует ли таблица message_templates
        cursor = await db.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='message_templates'
        """)
        table_exists = await cursor.fetchone()
        
        if table_exists:
            # Получаем шаблоны из новой таблицы message_templates
            cursor = await db.execute('''
                SELECT mt.id, NULL as order_id, NULL as user_id, mt.manager_id, 
                       mt.message_type, mt.content, mt.delay_minutes, 
                       'active' as status, mt.created_at, NULL as scheduled_at, NULL as sent_at, 
                       1 as is_automatic, mt.order_step, 
                       0 as story_batch, NULL as story_pages, NULL as selected_stories, 
                       mt.is_active, 0 as usage_count, NULL as last_used, mt.name
                FROM message_templates mt
                WHERE mt.is_active = 1
                ORDER BY mt.order_step, mt.delay_minutes, mt.created_at DESC
            ''')
        else:
            # Если новой таблицы нет, используем старую для обратной совместимости
            cursor = await db.execute('''
                SELECT id, order_id, user_id, manager_id, message_type, content, delay_minutes, 
                       status, created_at, scheduled_at, sent_at, is_automatic, order_step, 
                       story_batch, story_pages, selected_stories, is_active, usage_count, last_used,
                       message_type as name
                FROM delayed_messages 
                WHERE order_id IS NULL
                ORDER BY message_type, created_at DESC
            ''')
        
        messages = await cursor.fetchall()
        result = []
        for message in messages:
            msg_dict = dict(message)
            # Преобразуем None в None для JSON сериализации
            if msg_dict['scheduled_at'] is None:
                msg_dict['scheduled_at'] = None
            if msg_dict['sent_at'] is None:
                msg_dict['sent_at'] = None
            if msg_dict['last_used'] is None:
                msg_dict['last_used'] = None
            result.append(msg_dict)
        return result

async def toggle_template_active(template_id: int, is_active: bool) -> bool:
    """Переключает активность шаблона"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            UPDATE delayed_messages 
            SET is_active = ? 
            WHERE id = ?
        ''', (is_active, template_id))
        await db.commit()
        return True

async def increment_template_usage(template_id: int) -> bool:
    """Увеличивает счетчик использований шаблона"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            UPDATE delayed_messages 
            SET usage_count = usage_count + 1, last_used = datetime('now')
            WHERE id = ?
        ''', (template_id,))
        await db.commit()
        return True

async def get_all_orders() -> List[Dict]:
    """Получает все заказы для диагностики"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT id, user_id, status, order_data, created_at
            FROM orders 
            ORDER BY created_at DESC
        ''')
        orders = await cursor.fetchall()
        return [dict(order) for order in orders]

async def get_active_orders_by_step(order_step: str) -> List[Dict]:
    """Получает все активные заказы на определенном шаге"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Маппинг шагов заказа на статусы
        step_to_status = {
            'waiting_for_payment': ['pending'],
            'waiting_for_email': ['paid', 'demo_sent', 'waiting_draft'],  # Добавляем возможные статусы после оплаты
            'waiting_for_privacy_consent': ['email_received'],
            'waiting_for_hero_photos': ['privacy_consent_received'],
            'waiting_for_other_heroes': ['hero_photos_received'],
            'waiting_for_story_selection': ['other_heroes_received'],
            'waiting_for_style_selection': ['story_selected'],
            'waiting_for_voice_selection': ['style_selected'],
            'waiting_for_draft': ['voice_selected'],
            'waiting_for_final': ['draft_received'],
            'completed': ['ready', 'delivered']
        }
        
        statuses = step_to_status.get(order_step, [])
        print(f"🔍 ОТЛАДКА: Шаг {order_step} -> статусы: {statuses}")
        
        if not statuses:
            print(f"🔍 ОТЛАДКА: Нет статусов для шага {order_step}")
            return []
        
        placeholders = ','.join(['?' for _ in statuses])
        query = f'''
            SELECT id, user_id, status, order_data
            FROM orders 
            WHERE status IN ({placeholders}) AND status NOT IN ('completed', 'cancelled', 'failed')
            ORDER BY created_at DESC
        '''
        print(f"🔍 ОТЛАДКА: SQL запрос: {query}")
        print(f"🔍 ОТЛАДКА: Параметры: {statuses}")
        
        cursor = await db.execute(query, statuses)
        
        orders = await cursor.fetchall()
        print(f"🔍 ОТЛАДКА: Найдено заказов: {len(orders)}")
        for order in orders:
            print(f"🔍 ОТЛАДКА: Заказ {order['id']}, статус: {order['status']}, user_id: {order['user_id']}")
        
        return [dict(order) for order in orders]

async def update_delayed_message_status(message_id: int, status: str):
    async def _update_operation():
        async with aiosqlite.connect(DB_PATH) as db:
            # Настраиваем соединение
            await configure_db_connection(db)
            
            await db.execute('''
                UPDATE delayed_messages SET status = ?, sent_at = datetime('now') WHERE id = ?
            ''', (status, message_id))
            await db.commit()
    
    await safe_db_operation(_update_operation)

async def log_general_message_sent(delayed_message_id: int, user_id: int, order_id: int):
    """Записывает в лог отправку общего сообщения пользователю"""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute('''
                INSERT OR IGNORE INTO general_message_sent_log (delayed_message_id, user_id, order_id)
                VALUES (?, ?, ?)
            ''', (delayed_message_id, user_id, order_id))
            await db.commit()
        except Exception as e:
            print(f"Ошибка записи в лог отправки общего сообщения: {e}")

async def is_general_message_sent_to_user(delayed_message_id: int, user_id: int, order_id: int) -> bool:
    """Проверяет, было ли общее сообщение уже отправлено пользователю"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT id FROM general_message_sent_log 
            WHERE delayed_message_id = ? AND user_id = ? AND order_id = ?
        ''', (delayed_message_id, user_id, order_id))
        row = await cursor.fetchone()
        return row is not None

# --- Работа с адресами доставки ---

async def save_delivery_address(order_id: int, user_id: int, address: str, recipient_name: str = None, phone: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO delivery_addresses (order_id, user_id, address, recipient_name, phone, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        ''', (order_id, user_id, address, recipient_name, phone))
        await db.commit()

async def get_delivery_address(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Сначала проверяем, существует ли заказ
        cursor = await db.execute('''
            SELECT id FROM orders WHERE id = ?
        ''', (order_id,))
        order_exists = await cursor.fetchone()
        
        if not order_exists:
            print(f"🔍 ОТЛАДКА: Заказ {order_id} не существует, адрес доставки не найден")
            return None
        
        # Если заказ существует, ищем адрес доставки
        cursor = await db.execute('''
            SELECT * FROM delivery_addresses WHERE order_id = ? ORDER BY created_at DESC LIMIT 1
        ''', (order_id,))
        address = await cursor.fetchone()
        return dict(address) if address else None

async def log_order_status_change(order_id: int, old_status: str, new_status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await log_order_status_change_with_db(db, order_id, old_status, new_status)
        await db.commit()

async def log_order_status_change_with_db(db, order_id: int, old_status: str, new_status: str):
    """Логирует изменение статуса заказа, используя переданное соединение с базой данных"""
    await db.execute('''
        INSERT INTO order_status_history (order_id, old_status, new_status, changed_at)
        VALUES (?, ?, ?, datetime('now'))
    ''', (order_id, old_status, new_status))

async def get_order_status_history(order_id: int) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT * FROM order_status_history WHERE order_id = ? ORDER BY changed_at ASC
        ''', (order_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def add_message_history(order_id: int, sender: str, message: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f'''
            INSERT INTO message_history (order_id, sender, message, sent_at)
            VALUES (?, ?, ?, {get_moscow_time()})
        ''', (order_id, sender, message))
        await db.commit()
async def save_early_user_message(user_id: int, message: str):
    """Сохраняет ранние сообщения пользователя до создания заказа"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f'''
            INSERT INTO early_user_messages (user_id, message, sent_at)
            VALUES (?, ?, {get_moscow_time()})
        ''', (user_id, message))
        await db.commit()

async def get_early_user_messages(user_id: int) -> List[Dict]:
    """Получает ранние сообщения пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT message, sent_at FROM early_user_messages 
            WHERE user_id = ? 
            ORDER BY sent_at ASC
        ''', (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def transfer_early_messages_to_order(user_id: int, order_id: int):
    """Переносит ранние сообщения пользователя в историю заказа"""
    early_messages = await get_early_user_messages(user_id)
    for msg in early_messages:
        await add_message_history(order_id, "user", msg['message'])
    
    # Удаляем перенесенные сообщения
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            DELETE FROM early_user_messages WHERE user_id = ?
        ''', (user_id,))
        await db.commit()

async def get_message_history(order_id: int) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT * FROM message_history WHERE order_id = ? ORDER BY sent_at ASC
        ''', (order_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows] 

async def get_order_timeline(order_id: int) -> dict:
    # Определяем стандартные этапы
    STAGES = [
        ("created", "Старт"),
        ("product_selected", "Выбор продукта"),
        ("payment_pending", "Ожидание оплаты"),
        ("paid", "Оплачен"),
        ("waiting_draft", "Ожидание черновика"),
        ("draft_sent", "Черновик отправлен"),
        ("editing", "Внесение правок"),
        ("waiting_final", "Ожидание финала"),
        ("ready", "Финальная готова"),
        ("delivered", "Доставка")
    ]
    # Получаем историю статусов
    history = await get_order_status_history(order_id)
    # Получаем заказ
    order = await get_order(order_id)
    timeline = []
    last_time = order["created_at"] if order else None
    now = datetime.utcnow()
    active_found = False
    for stage_code, stage_name in STAGES:
        # Найти первую запись в истории, где new_status == stage_code
        entry = next((h for h in history if h["new_status"] == stage_code), None)
        if entry:
            timeline.append({
                "code": stage_code,
                "name": stage_name,
                "status": "completed",
                "changed_at": entry["changed_at"],
                "inactive_for": None
            })
            last_time = entry["changed_at"]
        elif not active_found:
            # Первый не найденный этап — активный
            active_found = True
            # inactive_for = now - last_time
            if last_time:
                last_dt = datetime.strptime(last_time, "%Y-%m-%d %H:%M:%S")
                inactive_for = (now - last_dt).total_seconds()
            else:
                inactive_for = None
            timeline.append({
                "code": stage_code,
                "name": stage_name,
                "status": "active",
                "changed_at": last_time,
                "inactive_for": inactive_for
            })
        else:
            timeline.append({
                "code": stage_code,
                "name": stage_name,
                "status": "pending",
                "changed_at": None,
                "inactive_for": None
            })
    return {
        "timeline": timeline,
        "active_stage": next((t for t in timeline if t["status"] == "active"), None),
        "last_action_time": last_time,
        "inactive_for": timeline[-1]["inactive_for"] if timeline and timeline[-1]["status"] == "active" else None
    }

# --- Работа с менеджерами ---

async def get_managers() -> List[Dict]:
    """Получает список всех менеджеров для админки (без паролей)"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT id, email, COALESCE(full_name, '') as full_name, is_super_admin FROM managers ORDER BY id DESC
        ''') as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def get_managers_for_auth() -> List[Dict]:
    """Получает список всех менеджеров для аутентификации (с хешированными паролями)"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT id, email, hashed_password, full_name, is_super_admin FROM managers ORDER BY id DESC
        ''') as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def get_regular_managers() -> List[Dict]:
    """Получает только обычных менеджеров (не главных админов)"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT id, email, COALESCE(full_name, '') as full_name, is_super_admin FROM managers 
            WHERE is_super_admin = 0 ORDER BY id DESC
        ''') as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def add_manager(email: str, password: str, full_name: str, is_super_admin: bool = False) -> int:
    """Добавляет нового менеджера"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Хешируем пароль перед сохранением
        hashed_password = get_password_hash(password)
        cursor = await db.execute('''
            INSERT INTO managers (email, hashed_password, full_name, is_super_admin)
            VALUES (?, ?, ?, ?)
        ''', (email, hashed_password, full_name, is_super_admin))
        await db.commit()
        return cursor.lastrowid

async def delete_manager(manager_id: int) -> bool:
    """Удаляет менеджера по ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('DELETE FROM managers WHERE id = ?', (manager_id,))
        await db.commit()
        return cursor.rowcount > 0

async def get_manager_by_email(email: str) -> Optional[Dict]:
    """Получает менеджера по email"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT id, email, hashed_password, full_name, is_super_admin FROM managers WHERE email = ?
        ''', (email,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(zip([column[0] for column in cursor.description], row))
            return None

async def get_manager_by_id(manager_id: int) -> Optional[Dict]:
    """Получает менеджера по ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT id, email, hashed_password, full_name, is_super_admin FROM managers WHERE id = ?
        ''', (manager_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(zip([column[0] for column in cursor.description], row))
            return None
async def update_manager_profile(manager_id: int, full_name: Optional[str] = None, new_password: Optional[str] = None) -> bool:
    """Обновляет профиль менеджера"""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            # Формируем SQL запрос динамически
            updates = []
            params = []
            
            if full_name is not None:
                updates.append("full_name = ?")
                params.append(full_name)
            
            if new_password is not None:
                updates.append("hashed_password = ?")
                params.append(get_password_hash(new_password))
            
            if not updates:
                return True  # Нет изменений
            
            params.append(manager_id)
            query = f"UPDATE managers SET {', '.join(updates)} WHERE id = ?"
            
            await db.execute(query, params)
            await db.commit()
            return True
        except Exception as e:
            print(f"Ошибка обновления профиля менеджера: {e}")
            return False

async def update_manager_super_admin_status(manager_id: int, is_super_admin: bool) -> bool:
    """Обновляет статус супер-админа для менеджера"""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute('''
                UPDATE managers SET is_super_admin = ? WHERE id = ?
            ''', (is_super_admin, manager_id))
            await db.commit()
            return True
        except Exception as e:
            print(f"Ошибка обновления статуса супер-админа: {e}")
            return False

async def get_next_manager_in_queue() -> Optional[int]:
    """Получает ID следующего менеджера в очереди для назначения заказа"""
    print("🔍 ОТЛАДКА: get_next_manager_in_queue() вызвана")
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем только обычных менеджеров (НЕ супер-админов)
        async with db.execute('''
            SELECT id FROM managers WHERE is_super_admin = 0 ORDER BY id ASC
        ''') as cursor:
            managers = await cursor.fetchall()
        
        print(f"🔍 ОТЛАДКА: Найдено менеджеров (не супер-админов): {len(managers)}")
        
        if not managers:
            print("🔍 ОТЛАДКА: Нет обычных менеджеров, пробуем всех менеджеров")
            # Если нет обычных менеджеров, берем всех
            async with db.execute('''
                SELECT id FROM managers ORDER BY id ASC
            ''') as cursor:
                managers = await cursor.fetchall()
            
            if not managers:
                print("🔍 ОТЛАДКА: Нет менеджеров вообще")
                return None
        
        manager_ids = [m[0] for m in managers]
        print(f"🔍 ОТЛАДКА: Доступные менеджеры для назначения: {manager_ids}")
        
        # Получаем последний назначенный менеджер из очереди
        async with db.execute('''
            SELECT last_manager_id FROM manager_queue WHERE id = 1
        ''') as cursor:
            result = await cursor.fetchone()
            last_manager_id = result[0] if result else 0
        
        print(f"🔍 ОТЛАДКА: Последний назначенный менеджер: {last_manager_id}")
        
        # Находим следующего менеджера
        if last_manager_id == 0:
            next_manager_id = manager_ids[0]
        else:
            try:
                current_index = manager_ids.index(last_manager_id)
                next_index = (current_index + 1) % len(manager_ids)
                next_manager_id = manager_ids[next_index]
            except ValueError:
                next_manager_id = manager_ids[0]
        
        print(f"🔍 ОТЛАДКА: Выбран менеджер ID {next_manager_id} для назначения")
        
        # Обновляем последнего назначенного менеджера
        await db.execute('''
            UPDATE manager_queue SET last_manager_id = ? WHERE id = 1
        ''', (next_manager_id,))
        await db.commit()
        
        return next_manager_id

async def is_super_admin(email: str) -> bool:
    """Проверяет, является ли менеджер главным админом"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT is_super_admin FROM managers WHERE email = ?
        ''', (email,)) as cursor:
            row = await cursor.fetchone()
            return row[0] == 1 if row else False

async def get_manager_orders(manager_id: int) -> List[Dict]:
    """Получает заказы конкретного менеджера"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT o.*, o.user_id as telegram_id, u.product, m.email as manager_email, m.full_name as manager_name 
            FROM orders o 
            LEFT JOIN user_profiles u ON o.user_id = u.user_id 
            LEFT JOIN managers m ON o.assigned_manager_id = m.id 
            WHERE o.assigned_manager_id = ? 
            ORDER BY o.created_at DESC
        ''', (manager_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows] 

async def get_orders_with_permissions(manager_email: str, status: Optional[str] = None, page: int = 1, limit: int = 50) -> List[Dict]:
    """Получает заказы с учетом прав доступа менеджера"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, является ли менеджер главным админом
        is_admin = await is_super_admin(manager_email)
        
        # Добавляем пагинацию
        offset = (page - 1) * limit
        
        if is_admin:
            # Главный админ видит все заказы
            if status:
                query = '''
                    SELECT o.*, o.user_id as telegram_id, u.username, u.first_name, u.last_name, m.email as manager_email, m.full_name as manager_name,
                           notif.id as notification_id, notif.is_read as notification_is_read, notif.last_user_message_at as notification_last_message_at
                    FROM orders o 
                    LEFT JOIN user_profiles u ON o.user_id = u.user_id 
                    LEFT JOIN managers m ON o.assigned_manager_id = m.id 
                    LEFT JOIN order_notifications notif ON o.id = notif.order_id
                    WHERE o.status = ? 
                    ORDER BY o.created_at DESC
                    LIMIT ? OFFSET ?
                '''
                args = (status, limit, offset)
            else:
                query = '''
                    SELECT o.*, o.user_id as telegram_id, u.username, u.first_name, u.last_name, m.email as manager_email, m.full_name as manager_name,
                           notif.id as notification_id, notif.is_read as notification_is_read, notif.last_user_message_at as notification_last_message_at
                    FROM orders o 
                    LEFT JOIN user_profiles u ON o.user_id = u.user_id 
                    LEFT JOIN managers m ON o.assigned_manager_id = m.id 
                    LEFT JOIN order_notifications notif ON o.id = notif.order_id
                    ORDER BY o.created_at DESC
                    LIMIT ? OFFSET ?
                '''
                args = (limit, offset)
        else:
            # Обычный менеджер видит только свои заказы
            manager = await get_manager_by_email(manager_email)
            if not manager:
                return []
            
            if status:
                query = '''
                    SELECT o.*, o.user_id as telegram_id, u.username, u.first_name, u.last_name, m.email as manager_email, m.full_name as manager_name,
                           notif.id as notification_id, notif.is_read as notification_is_read, notif.last_user_message_at as notification_last_message_at
                    FROM orders o 
                    LEFT JOIN managers m ON o.assigned_manager_id = m.id 
                    LEFT JOIN user_profiles u ON o.user_id = u.user_id 
                    LEFT JOIN order_notifications notif ON o.id = notif.order_id AND notif.manager_id = ?
                    WHERE o.assigned_manager_id = ? AND o.status = ? 
                    ORDER BY o.created_at DESC
                    LIMIT ? OFFSET ?
                '''
                args = (manager["id"], manager["id"], status, limit, offset)
            else:
                query = '''
                    SELECT o.*, o.user_id as telegram_id, u.username, u.first_name, u.last_name, m.email as manager_email, m.full_name as manager_name,
                           notif.id as notification_id, notif.is_read as notification_is_read, notif.last_user_message_at as notification_last_message_at
                    FROM orders o 
                    LEFT JOIN managers m ON o.assigned_manager_id = m.id 
                    LEFT JOIN user_profiles u ON o.user_id = u.user_id 
                    LEFT JOIN order_notifications notif ON o.id = notif.order_id AND notif.manager_id = ?
                    WHERE o.assigned_manager_id = ? 
                    ORDER BY o.created_at DESC
                    LIMIT ? OFFSET ?
                '''
                args = (manager["id"], manager["id"], limit, offset)
        
        async with db.execute(query, args) as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def get_last_order_username(user_id: int) -> Optional[str]:
    """Получает username из последнего заказа пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT u.username 
            FROM orders o 
            LEFT JOIN user_profiles u ON o.user_id = u.user_id 
            WHERE o.user_id = ? 
            ORDER BY o.created_at DESC 
            LIMIT 1
        ''', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None

async def get_orders_filtered_with_permissions(
    manager_email: str,
    status: Optional[str] = None,
    order_type: Optional[str] = None,
    telegram_id: Optional[str] = None,
    order_id: Optional[int] = None,
    sort_by: str = 'created_at',
    sort_dir: str = 'desc',
) -> List[Dict]:
    """Получает отфильтрованные заказы с учетом прав доступа менеджера"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, является ли менеджер главным админом
        is_admin = await is_super_admin(manager_email)
        
        query = '''
            SELECT o.*, o.user_id as telegram_id, u.product, u.username, u.first_name, u.last_name, m.email as manager_email, m.full_name as manager_name, d.phone
            FROM orders o 
            LEFT JOIN user_profiles u ON o.user_id = u.user_id 
            LEFT JOIN managers m ON o.assigned_manager_id = m.id 
            LEFT JOIN delivery_addresses d ON o.id = d.order_id
            WHERE 1=1
        '''
        args = []
        
        if not is_admin:
            # Обычный менеджер видит только свои заказы
            manager = await get_manager_by_email(manager_email)
            if not manager:
                return []
            query += ' AND o.assigned_manager_id = ?'
            args.append(manager["id"])
        
        if status:
            query += ' AND o.status = ?'
            args.append(status)
        if order_type:
            query += ' AND u.product = ?'
            args.append(order_type)
        if telegram_id:
            query += ' AND o.user_id = ?'
            args.append(int(telegram_id))
        if order_id:
            query += ' AND o.id = ?'
            args.append(order_id)
        if sort_by not in ['created_at', 'status', 'id']:
            sort_by = 'created_at'
        if sort_dir.lower() not in ['asc', 'desc']:
            sort_dir = 'desc'
        query += f' ORDER BY o.{sort_by} {sort_dir.upper()}'
        
        # ОТЛАДКА: Выводим SQL запрос
        print(f"🔍 ОТЛАДКА SQL запрос: {query}")
        print(f"🔍 ОТЛАДКА SQL аргументы: {args}")
        
        async with db.execute(query, args) as cursor:
            rows = await cursor.fetchall()
            result = [dict(zip([column[0] for column in cursor.description], row)) for row in rows]
            
            # ОТЛАДКА: Выводим информацию о полученных заказах
            print(f"🔍 ОТЛАДКА get_orders_filtered_with_permissions: получено {len(result)} заказов")
            for i, order in enumerate(result[:3]):  # Показываем первые 3 заказа
                print(f"  Заказ {i+1}: ID={order.get('id')}, product={order.get('product')}, user_id={order.get('user_id')}")
            
            return result

async def can_access_order(manager_email: str, order_id: int) -> bool:
    """Проверяет, может ли менеджер получить доступ к заказу"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, является ли менеджер главным админом
        is_admin = await is_super_admin(manager_email)
        
        if is_admin:
            return True
        
        # Обычный менеджер может получить доступ только к своим заказам
        manager = await get_manager_by_email(manager_email)
        if not manager:
            return False
        
        async with db.execute('''
            SELECT assigned_manager_id FROM orders WHERE id = ?
        ''', (order_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False
            
            return row[0] == manager["id"] 

# --- Функции для работы с фотографиями ---

async def get_all_photos() -> List[Dict]:
    """Получает все фотографии из всех таблиц и order_data"""
    import glob
    import os
    from datetime import datetime
    
    print("🔍 ОТЛАДКА: Начинаем загрузку всех фотографий")
    
    async with aiosqlite.connect(DB_PATH) as db:
        photos = []
        processed_files = set()  # Для отслеживания уже обработанных файлов
        
        # Helper функция для добавления фото с правильным путем
        def add_photo(id, order_id, filename, type, created_at, base_dir="uploads"):
            # Проверяем, не добавляли ли мы уже этот файл
            file_key = f"{order_id}_{filename}_{type}"
            if file_key in processed_files:
                print(f"🔍 ОТЛАДКА: Пропускаем дубликат {file_key}")
                return
            processed_files.add(file_key)
            
            # Проверяем, существует ли файл физически
            file_path = os.path.join(base_dir, filename)
            if not os.path.exists(file_path):
                print(f"⚠️ Файл не найден: {file_path}")
                return
            
            photo_data = {
                "id": id,
                "order_id": order_id,
                "filename": filename,
                "type": type,
                "created_at": created_at,
                "path": f"{base_dir}/{filename}"  # Используем прямые слеши для веб-путей
            }
            photos.append(photo_data)
            print(f"🔍 ОТЛАДКА: Добавлена фотография в массив: {photo_data}")
        
        # Получаем фотографии из order_data (основной источник фотографий героев)
        async with db.execute('''
            SELECT id, id as order_id, order_data, created_at
            FROM orders
            WHERE order_data IS NOT NULL AND order_data != ''
        ''') as cursor:
            rows = await cursor.fetchall()
            print(f"🔍 ОТЛАДКА: Найдено {len(rows)} заказов с order_data")
            for row in rows:
                order_id = row[1]
                order_data_str = row[2]
                created_at = row[3]
                print(f"🔍 ОТЛАДКА: Обрабатываем заказ {order_id}")
                
                try:
                    order_data = json.loads(order_data_str)
                    print(f"🔍 ОТЛАДКА: Заказ {order_id}, order_data ключи: {list(order_data.keys())}")
                    
                    # Фотографии главного героя
                    main_hero_photos = order_data.get('main_hero_photos', [])
                    print(f"🔍 ОТЛАДКА: Заказ {order_id}, main_hero_photos: {main_hero_photos}")
                    
                    # Также проверяем отдельные поля фотографий
                    main_face_1 = order_data.get('main_face_1')
                    main_face_2 = order_data.get('main_face_2')
                    main_full = order_data.get('main_full')
                    joint_photo = order_data.get('joint_photo')
                    print(f"🔍 ОТЛАДКА: Заказ {order_id}, main_face_1: {main_face_1}, main_face_2: {main_face_2}, main_full: {main_full}, joint_photo: {joint_photo}")
                    
                    # Обрабатываем новую структуру main_hero_photos (массив объектов)
                    if isinstance(main_hero_photos, list):
                        for photo_obj in main_hero_photos:
                            if isinstance(photo_obj, dict):
                                # Новая структура: {'type': 'face_1', 'filename': '...'}
                                photo_filename = photo_obj.get('filename')
                                photo_type = photo_obj.get('type', 'main_hero')
                                if photo_filename and photo_filename != "-":
                                    print(f"🔍 ОТЛАДКА: Добавляем фото {photo_filename} с типом {photo_type}")
                                    add_photo(len(photos) + 1, order_id, photo_filename, photo_type, created_at)
                            elif isinstance(photo_obj, str):
                                # Старая структура: просто строка с именем файла
                                photo_filename = photo_obj
                                if photo_filename and photo_filename != "-":
                                    # Определяем тип фотографии на основе имени файла
                                    if "main_face_1" in photo_filename:
                                        photo_type = "main_hero"
                                    elif "main_face_2" in photo_filename:
                                        photo_type = "main_hero"
                                    elif "main_full" in photo_filename:
                                        photo_type = "main_hero"
                                    else:
                                        photo_type = f"main_hero"
                                    print(f"🔍 ОТЛАДКА: Добавляем фото {photo_filename} с типом {photo_type}")
                                    add_photo(len(photos) + 1, order_id, photo_filename, photo_type, created_at)
                    
                    # Обрабатываем отдельные поля фотографий (если они есть)
                    if main_face_1 and main_face_1 != "-":
                        print(f"🔍 ОТЛАДКА: Добавляем main_face_1 {main_face_1}")
                        add_photo(len(photos) + 1, order_id, main_face_1, "main_face_1", created_at)
                    
                    if main_face_2 and main_face_2 != "-":
                        print(f"🔍 ОТЛАДКА: Добавляем main_face_2 {main_face_2}")
                        add_photo(len(photos) + 1, order_id, main_face_2, "main_face_2", created_at)
                    
                    if main_full and main_full != "-":
                        print(f"🔍 ОТЛАДКА: Добавляем main_full {main_full}")
                        add_photo(len(photos) + 1, order_id, main_full, "main_full", created_at)
                    
                    # Совместное фото
                    joint_photo = order_data.get('joint_photo')
                    print(f"🔍 ОТЛАДКА: Заказ {order_id}, joint_photo: {joint_photo}")
                    if joint_photo and joint_photo != "-":
                        print(f"🔍 ОТЛАДКА: Добавляем совместное фото {joint_photo}")
                        add_photo(len(photos) + 1, order_id, joint_photo, "joint_photo", created_at)
                    
                    # Фотографии других героев
                    other_heroes = order_data.get('other_heroes', [])
                    print(f"🔍 ОТЛАДКА: Заказ {order_id}, other_heroes: {other_heroes}")
                    for hero_index, hero in enumerate(other_heroes):
                        hero_name = hero.get('name', f'hero_{hero_index+1}')
                        print(f"🔍 ОТЛАДКА: Обрабатываем героя {hero_name}")
                        
                        # Фото лица 1
                        face_1 = hero.get('face_1')
                        if face_1 and face_1 != "-":
                            print(f"🔍 ОТЛАДКА: Добавляем фото второго героя {face_1} с типом {hero_name}_face_1")
                            add_photo(len(photos) + 1, order_id, face_1, f"{hero_name}_face_1", created_at)
                        
                        # Фото лица 2
                        face_2 = hero.get('face_2')
                        if face_2 and face_2 != "-":
                            print(f"🔍 ОТЛАДКА: Добавляем фото второго героя {face_2} с типом {hero_name}_face_2")
                            add_photo(len(photos) + 1, order_id, face_2, f"{hero_name}_face_2", created_at)
                        
                        # Полное фото
                        full = hero.get('full')
                        if full and full != "-":
                            print(f"🔍 ОТЛАДКА: Добавляем фото второго героя {full} с типом {hero_name}_full")
                            add_photo(len(photos) + 1, order_id, full, f"{hero_name}_full", created_at)
                    
                except json.JSONDecodeError as e:
                    print(f"Ошибка парсинга order_data для заказа {order_id}: {e}")
                    continue
        
        # Получаем фотографии из папки uploads/order_{id}_pages (индивидуальные страницы)
        try:
            pages_dirs = glob.glob("uploads/order_*_pages")
            for pages_dir in pages_dirs:
                try:
                    # Извлекаем ID заказа из имени папки
                    order_id = int(pages_dir.split("order_")[1].split("_pages")[0])
                    
                    # Получаем все файлы из папки
                    page_files = glob.glob(os.path.join(pages_dir, "*"))
                    for i, file_path in enumerate(page_files):
                        if os.path.isfile(file_path):
                            filename = os.path.basename(file_path)
                            # Для page_X типа используем полный путь к папке
                            add_photo(len(photos) + 1, order_id, filename, f"page_{i+1}", datetime.now().isoformat(), pages_dir)
                except Exception as e:
                    print(f"Ошибка обработки папки {pages_dir}: {e}")
        except Exception as e:
            print(f"Ошибка при поиске папок страниц: {e}")
        
        # Получаем фотографии из таблицы uploads (фотографии первой и последней страницы и другие)
        try:
            async with db.execute('''
                SELECT id, order_id, filename, file_type, uploaded_at
                FROM uploads
                ORDER BY uploaded_at DESC
            ''') as cursor:
                upload_rows = await cursor.fetchall()
                print(f"🔍 ОТЛАДКА: Найдено {len(upload_rows)} записей в таблице uploads")
                
                for row in upload_rows:
                    upload_id, order_id, filename, file_type, uploaded_at = row
                    print(f"🔍 ОТЛАДКА: Обрабатываем upload: order_id={order_id}, filename={filename}, file_type={file_type}")
                    add_photo(upload_id, order_id, filename, file_type, uploaded_at)
        except Exception as e:
            print(f"Ошибка при получении данных из таблицы uploads: {e}")
        
        # Сортируем по дате создания (новые сначала)
        photos.sort(key=lambda x: x["created_at"], reverse=True)
        
        print(f"🔍 ОТЛАДКА: Всего найдено фотографий: {len(photos)}")
        print(f"🔍 ОТЛАДКА: Пример фотографий: {photos[:3] if photos else 'Нет фотографий'}")
        
        return photos
async def get_selected_photos() -> List[Dict]:
    """Получает только выбранные фотографии из order_data"""
    import glob
    import os
    from datetime import datetime
    
    print("🔍 ОТЛАДКА: Начинаем загрузку выбранных фотографий")
    
    async with aiosqlite.connect(DB_PATH) as db:
        photos = []
        processed_files = set()  # Для отслеживания уже обработанных файлов
        
        # Helper функция для добавления фото с правильным путем
        def add_photo(id, order_id, filename, type, created_at, base_dir="uploads"):
            # Проверяем, не добавляли ли мы уже этот файл
            file_key = f"{order_id}_{filename}_{type}"
            if file_key in processed_files:
                print(f"🔍 ОТЛАДКА: Пропускаем дубликат {file_key}")
                return
            processed_files.add(file_key)
            
            # Проверяем, существует ли файл физически
            file_path = os.path.join(base_dir, filename)
            if not os.path.exists(file_path):
                print(f"⚠️ Файл не найден: {file_path}")
                return
            
            photo_data = {
                "id": id,
                "order_id": order_id,
                "filename": filename,
                "type": type,
                "created_at": created_at,
                "path": f"{base_dir}/{filename}"  # Используем прямые слеши для веб-путей
            }
            photos.append(photo_data)
            print(f"🔍 ОТЛАДКА: Добавлена выбранная фотография: {photo_data}")
        
        # Получаем фотографии из order_data (основной источник фотографий героев)
        async with db.execute('''
            SELECT id, id as order_id, order_data, created_at
            FROM orders
            WHERE order_data IS NOT NULL AND order_data != ''
        ''') as cursor:
            rows = await cursor.fetchall()
            print(f"🔍 ОТЛАДКА: Найдено {len(rows)} заказов с order_data")
            for row in rows:
                order_id = row[1]
                order_data_str = row[2]
                created_at = row[3]
                print(f"🔍 ОТЛАДКА: Обрабатываем заказ {order_id}")
                
                try:
                    order_data = json.loads(order_data_str)
                    print(f"🔍 ОТЛАДКА: Заказ {order_id}, order_data ключи: {list(order_data.keys())}")
                    
                    # Получаем выбранные страницы
                    selected_pages = order_data.get('selected_pages', [])
                    print(f"🔍 ОТЛАДКА: Заказ {order_id}, выбранные страницы: {selected_pages}")
                    
                    # Фотографии главного героя (всегда показываем)
                    main_hero_photos = order_data.get('main_hero_photos', [])
                    print(f"🔍 ОТЛАДКА: Заказ {order_id}, main_hero_photos: {main_hero_photos}")
                    
                    # Также проверяем отдельные поля фотографий
                    main_face_1 = order_data.get('main_face_1')
                    main_face_2 = order_data.get('main_face_2')
                    main_full = order_data.get('main_full')
                    joint_photo = order_data.get('joint_photo')
                    print(f"🔍 ОТЛАДКА: Заказ {order_id}, main_face_1: {main_face_1}, main_face_2: {main_face_2}, main_full: {main_full}, joint_photo: {joint_photo}")
                    
                    # Обрабатываем новую структуру main_hero_photos (массив объектов)
                    if isinstance(main_hero_photos, list):
                        for photo_obj in main_hero_photos:
                            if isinstance(photo_obj, dict):
                                # Новая структура: {'type': 'face_1', 'filename': '...'}
                                photo_filename = photo_obj.get('filename')
                                photo_type = photo_obj.get('type', 'main_hero')
                                if photo_filename and photo_filename != "-":
                                    print(f"🔍 ОТЛАДКА: Добавляем фото главного героя {photo_filename} с типом {photo_type}")
                                    add_photo(len(photos) + 1, order_id, photo_filename, photo_type, created_at)
                            elif isinstance(photo_obj, str):
                                # Старая структура: просто строка с именем файла
                                photo_filename = photo_obj
                                if photo_filename and photo_filename != "-":
                                    # Определяем тип фотографии на основе имени файла
                                    if "main_face_1" in photo_filename:
                                        photo_type = "main_hero"
                                    elif "main_face_2" in photo_filename:
                                        photo_type = "main_hero"
                                    elif "main_full" in photo_filename:
                                        photo_type = "main_hero"
                                    else:
                                        photo_type = f"main_hero"
                                    print(f"🔍 ОТЛАДКА: Добавляем фото главного героя {photo_filename} с типом {photo_type}")
                                    add_photo(len(photos) + 1, order_id, photo_filename, photo_type, created_at)
                    
                    # Обрабатываем отдельные поля фотографий (если они есть)
                    if main_face_1 and main_face_1 != "-":
                        print(f"🔍 ОТЛАДКА: Добавляем main_face_1 {main_face_1}")
                        add_photo(len(photos) + 1, order_id, main_face_1, "main_face_1", created_at)
                    
                    if main_face_2 and main_face_2 != "-":
                        print(f"🔍 ОТЛАДКА: Добавляем main_face_2 {main_face_2}")
                        add_photo(len(photos) + 1, order_id, main_face_2, "main_face_2", created_at)
                    
                    if main_full and main_full != "-":
                        print(f"🔍 ОТЛАДКА: Добавляем main_full {main_full}")
                        add_photo(len(photos) + 1, order_id, main_full, "main_full", created_at)
                    
                    # Совместное фото
                    joint_photo = order_data.get('joint_photo')
                    print(f"🔍 ОТЛАДКА: Заказ {order_id}, joint_photo: {joint_photo}")
                    if joint_photo and joint_photo != "-":
                        print(f"🔍 ОТЛАДКА: Добавляем совместное фото {joint_photo}")
                        add_photo(len(photos) + 1, order_id, joint_photo, "joint_photo", created_at)
                    
                    # Фотографии других героев
                    other_heroes = order_data.get('other_heroes', [])
                    print(f"🔍 ОТЛАДКА: Заказ {order_id}, other_heroes: {other_heroes}")
                    for hero_index, hero in enumerate(other_heroes):
                        hero_name = hero.get('name', f'hero_{hero_index+1}')
                        print(f"🔍 ОТЛАДКА: Обрабатываем героя {hero_name}")
                        
                        # Фото лица 1
                        face_1 = hero.get('face_1')
                        if face_1 and face_1 != "-":
                            print(f"🔍 ОТЛАДКА: Добавляем фото второго героя {face_1} с типом {hero_name}_face_1")
                            add_photo(len(photos) + 1, order_id, face_1, f"{hero_name}_face_1", created_at)
                        
                        # Фото лица 2
                        face_2 = hero.get('face_2')
                        if face_2 and face_2 != "-":
                            print(f"🔍 ОТЛАДКА: Добавляем фото второго героя {face_2} с типом {hero_name}_face_2")
                            add_photo(len(photos) + 1, order_id, face_2, f"{hero_name}_face_2", created_at)
                        
                        # Полное фото
                        full = hero.get('full')
                        if full and full != "-":
                            print(f"🔍 ОТЛАДКА: Добавляем фото второго героя {full} с типом {hero_name}_full")
                            add_photo(len(photos) + 1, order_id, full, f"{hero_name}_full", created_at)
                    
                except json.JSONDecodeError as e:
                    print(f"Ошибка парсинга order_data для заказа {order_id}: {e}")
                    continue
        
        # Получаем ТОЛЬКО ВЫБРАННЫЕ страницы из папки uploads/order_{id}_pages
        try:
            pages_dirs = glob.glob("uploads/order_*_pages")
            for pages_dir in pages_dirs:
                try:
                    # Извлекаем ID заказа из имени папки
                    order_id = int(pages_dir.split("order_")[1].split("_pages")[0])
                    
                    # Получаем выбранные страницы для этого заказа
                    cursor = await db.execute('SELECT order_data FROM orders WHERE id = ?', (order_id,))
                    row = await cursor.fetchone()
                    if row and row[0]:
                        try:
                            order_data = json.loads(row[0])
                            selected_pages = order_data.get('selected_pages', [])
                            print(f"🔍 ОТЛАДКА: Заказ {order_id}, выбранные страницы: {selected_pages}")
                        except json.JSONDecodeError:
                            selected_pages = []
                            print(f"🔍 ОТЛАДКА: Заказ {order_id}, ошибка парсинга order_data")
                    else:
                        selected_pages = []
                        print(f"🔍 ОТЛАДКА: Заказ {order_id}, нет order_data")
                    
                    # Получаем все файлы из папки
                    # Получаем страницы из базы данных с правильной нумерацией
                    order_pages = await get_order_pages(order_id)
                    
                    for page_info in order_pages:
                        page_num = page_info['page_number']
                        filename = page_info['filename']
                        
                        # Проверяем, существует ли файл
                        file_path = os.path.join(pages_dir, filename)
                        if os.path.isfile(file_path):
                            # Добавляем только если страница выбрана
                            if page_num in selected_pages:
                                print(f"🔍 ОТЛАДКА: Добавляем выбранную страницу {page_num}: {filename}")
                                add_photo(len(photos) + 1, order_id, filename, f"page_{page_num}", datetime.now().isoformat(), pages_dir)
                            else:
                                print(f"🔍 ОТЛАДКА: Пропускаем невыбранную страницу {page_num}: {filename}")
                                
                except Exception as e:
                    print(f"Ошибка обработки папки {pages_dir}: {e}")
        except Exception as e:
            print(f"Ошибка при поиске папок страниц: {e}")
        
        # Сортируем по дате создания (новые сначала)
        photos.sort(key=lambda x: x["created_at"], reverse=True)
        
        print(f"🔍 ОТЛАДКА: Всего найдено выбранных фотографий: {len(photos)}")
        print(f"🔍 ОТЛАДКА: Пример выбранных фотографий: {photos[:3] if photos else 'Нет фотографий'}")
        
        return photos

async def get_complete_photos() -> List[Dict]:
    """Получает все фотографии: выбранные страницы + вкладыши + свои фото + обложки"""
    import glob
    import os
    from datetime import datetime
    
    async with aiosqlite.connect(DB_PATH) as db:
        photos = []
        processed_files = set()
        
        def add_photo(id, order_id, filename, type, created_at, base_dir="uploads"):
            # Проверяем, что filename - это строка
            if not isinstance(filename, str):
                print(f"🔍 ОТЛАДКА: filename не является строкой: {filename}")
                return
                
            file_key = f"{order_id}_{filename}_{type}"
            if file_key in processed_files:
                print(f"🔍 ОТЛАДКА: Файл уже обработан: {file_key}")
                return
            processed_files.add(file_key)
            
            file_path = os.path.join(base_dir, filename)
            if not os.path.exists(file_path):
                print(f"🔍 ОТЛАДКА: Файл не существует: {file_path}")
                return
            
            # Кодируем filename для URL
            from urllib.parse import quote
            encoded_filename = quote(filename)
            
            photo_data = {
                "id": id,
                "order_id": order_id,
                "filename": filename,
                "type": type,
                "created_at": created_at,
                "path": f"{base_dir}/{encoded_filename}"
            }
            photos.append(photo_data)
            print(f"🔍 ОТЛАДКА: Добавлена фотография: {photo_data}")
        
        # Получаем фотографии из order_data
        async with db.execute('''
            SELECT id, id as order_id, order_data, created_at
            FROM orders
            WHERE order_data IS NOT NULL AND order_data != ''
        ''') as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                order_id = row[1]
                order_data_str = row[2]
                created_at = row[3]
                
                try:
                    order_data = json.loads(order_data_str)
                    
                    # Фотографии главного героя
                    main_hero_photos = order_data.get('main_hero_photos', [])
                    
                    # Обрабатываем main_hero_photos
                    if isinstance(main_hero_photos, list):
                        for photo_obj in main_hero_photos:
                            if isinstance(photo_obj, dict):
                                photo_filename = photo_obj.get('filename')
                                photo_type = photo_obj.get('type', 'main_hero')
                                if photo_filename and photo_filename != "-":
                                    add_photo(len(photos) + 1, order_id, photo_filename, photo_type, created_at)
                            elif isinstance(photo_obj, str):
                                photo_filename = photo_obj
                                if photo_filename and photo_filename != "-":
                                    photo_type = "main_hero"
                                    add_photo(len(photos) + 1, order_id, photo_filename, photo_type, created_at)
                    
                    # Отдельные поля фотографий
                    main_face_1 = order_data.get('main_face_1')
                    main_face_2 = order_data.get('main_face_2')
                    main_full = order_data.get('main_full')
                    joint_photo = order_data.get('joint_photo')
                    
                    if main_face_1 and main_face_1 != "-":
                        add_photo(len(photos) + 1, order_id, main_face_1, "main_face_1", created_at)
                    
                    if main_face_2 and main_face_2 != "-":
                        add_photo(len(photos) + 1, order_id, main_face_2, "main_face_2", created_at)
                    
                    if main_full and main_full != "-":
                        add_photo(len(photos) + 1, order_id, main_full, "main_full", created_at)
                    
                    # Совместное фото
                    if joint_photo and joint_photo != "-":
                        add_photo(len(photos) + 1, order_id, joint_photo, "joint_photo", created_at)
                    
                    # Фотографии других героев
                    other_heroes = order_data.get('other_heroes', [])
                    for hero_index, hero in enumerate(other_heroes):
                        hero_name = hero.get('name', f'hero_{hero_index+1}')
                        
                        # Фото лица 1
                        face_1 = hero.get('face_1')
                        if face_1 and face_1 != "-":
                            add_photo(len(photos) + 1, order_id, face_1, f"{hero_name}_face_1", created_at)
                        
                        # Фото лица 2
                        face_2 = hero.get('face_2')
                        if face_2 and face_2 != "-":
                            add_photo(len(photos) + 1, order_id, face_2, f"{hero_name}_face_2", created_at)
                        
                        # Полное фото
                        full = hero.get('full')
                        if full and full != "-":
                            add_photo(len(photos) + 1, order_id, full, f"{hero_name}_full", created_at)
                    
                    # Вкладыши (inserts)
                    inserts = order_data.get('inserts', [])
                    for insert_filename in inserts:
                        if insert_filename and insert_filename != "-":
                            add_photo(len(photos) + 1, order_id, insert_filename, "insert", created_at)
                    
                    # Свои фотографии (custom_photos)
                    custom_photos = order_data.get('custom_photos', [])
                    for custom_photo_filename in custom_photos:
                        if custom_photo_filename and custom_photo_filename != "-":
                            add_photo(len(photos) + 1, order_id, custom_photo_filename, "custom_photo", created_at)
                    
                    # Выбранная обложка
                    selected_cover = order_data.get('selected_cover', {})
                    if selected_cover and isinstance(selected_cover, dict):
                        cover_filename = selected_cover.get('filename')
                        if cover_filename and cover_filename != "-":
                            add_photo(len(photos) + 1, order_id, cover_filename, "selected_cover", created_at)
                    
                except json.JSONDecodeError as e:
                    continue
        
        # Получаем выбранные страницы из папки uploads/order_{id}_pages
        try:
            pages_dirs = glob.glob("uploads/order_*_pages")
            for pages_dir in pages_dirs:
                try:
                    order_id = int(pages_dir.split("order_")[1].split("_pages")[0])
                    
                    cursor = await db.execute('SELECT order_data FROM orders WHERE id = ?', (order_id,))
                    row = await cursor.fetchone()
                    if row and row[0]:
                        try:
                            order_data = json.loads(row[0])
                            selected_pages = order_data.get('selected_pages', [])
                        except json.JSONDecodeError:
                            selected_pages = []
                    else:
                        selected_pages = []
                    
                    page_files = glob.glob(os.path.join(pages_dir, "*"))
                    page_files.sort()
                    
                    for i, file_path in enumerate(page_files):
                        if os.path.isfile(file_path):
                            filename = os.path.basename(file_path)
                            page_num = i + 1
                            
                            if page_num in selected_pages:
                                add_photo(len(photos) + 1, order_id, filename, f"page_{page_num}", datetime.now().isoformat(), pages_dir)
                                
                except Exception as e:
                    continue
        except Exception as e:
            pass
        
        # Добавляем фотографии героев из таблицы hero_photos
        try:
            async with db.execute('''
                SELECT id, order_id, filename, photo_type, hero_name, created_at
                FROM hero_photos
                ORDER BY created_at DESC
            ''') as cursor:
                hero_photo_rows = await cursor.fetchall()
                
                for row in hero_photo_rows:
                    photo_id, order_id, filename, photo_type, hero_name, created_at = row
                    
                    if hero_name:
                        display_type = f"{hero_name}_{photo_type}"
                    else:
                        display_type = f"hero_{photo_type}"
                    
                    add_photo(photo_id, order_id, filename, display_type, created_at)
        
        except Exception as e:
            pass
        
        # Добавляем фотографии из таблицы uploads (фотографии первой и последней страницы и другие)
        try:
            async with db.execute('''
                SELECT id, order_id, filename, file_type, uploaded_at
                FROM uploads
                ORDER BY uploaded_at DESC
            ''') as cursor:
                upload_rows = await cursor.fetchall()
                print(f"🔍 ОТЛАДКА: Найдено {len(upload_rows)} записей в таблице uploads")
                
                for row in upload_rows:
                    upload_id, order_id, filename, file_type, uploaded_at = row
                    print(f"🔍 ОТЛАДКА: Обрабатываем upload: order_id={order_id}, filename={filename}, file_type={file_type}")
                    add_photo(upload_id, order_id, filename, file_type, uploaded_at)
        except Exception as e:
            print(f"❌ Ошибка при получении данных из таблицы uploads: {e}")
            pass
        
        # Сортируем по дате создания (новые сначала)
        photos.sort(key=lambda x: x["created_at"], reverse=True)
        
        return photos

# --- Функции для сохранения фотографий в базу данных ---

async def save_main_hero_photo(order_id: int, filename: str) -> int:
    """Сохраняет фотографию главного героя в базу данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO main_hero_photos (order_id, filename)
            VALUES (?, ?)
        ''', (order_id, filename))
        await db.commit()
        return cursor.lastrowid

async def save_hero_photo(order_id: int, filename: str, photo_type: str, hero_name: str = None) -> int:
    """Сохраняет фотографию другого героя в базу данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO hero_photos (order_id, filename, photo_type, hero_name, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        ''', (order_id, filename, photo_type, hero_name))
        await db.commit()
        return cursor.lastrowid

async def save_joint_photo(order_id: int, filename: str) -> int:
    """Сохраняет совместное фото в базу данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO joint_photos (order_id, filename)
            VALUES (?, ?)
        ''', (order_id, filename))
        await db.commit()
        return cursor.lastrowid

async def save_uploaded_file(order_id: int, filename: str, file_type: str = "image") -> int:
    """Сохраняет загруженный файл в базу данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO uploads (order_id, filename, file_type, uploaded_at)
            VALUES (?, ?, ?, datetime('now'))
        ''', (order_id, filename, file_type))
        await db.commit()
        return cursor.lastrowid

# --- Функции для работы с шаблонами обложек ---

async def get_cover_templates() -> List[Dict]:
    """Получает все шаблоны обложек"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT id, name, filename, category, created_at
            FROM cover_templates
            ORDER BY created_at ASC
        ''') as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def get_cover_template_by_id(template_id: int) -> Dict:
    """Получает шаблон обложки по ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT id, name, filename, category, created_at
            FROM cover_templates
            WHERE id = ?
        ''', (template_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(zip([column[0] for column in cursor.description], row))
            return None

async def add_cover_template(name: str, filename: str, category: str) -> Dict:
    """Добавляет новый шаблон обложки"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO cover_templates (name, filename, category, created_at)
            VALUES (?, ?, ?, datetime('now'))
        ''', (name, filename, category))
        await db.commit()
        
        # Получаем созданный шаблон
        template_id = cursor.lastrowid
        async with db.execute('''
            SELECT id, name, filename, category, created_at
            FROM cover_templates
            WHERE id = ?
        ''', (template_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(zip([column[0] for column in cursor.description], row))

async def delete_cover_template(template_id: int) -> bool:
    """Удаляет шаблон обложки по ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            DELETE FROM cover_templates
            WHERE id = ?
        ''', (template_id,))
        await db.commit()
        return cursor.rowcount > 0

# --- Функции для работы со стилями книг ---

async def get_book_styles() -> List[Dict]:
    """Получает все стили книг"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT id, name, description, filename, category, created_at
            FROM book_styles
            ORDER BY 
                CASE 
                    WHEN name LIKE '%Pixar%' THEN 1
                    WHEN name LIKE '%Ghibli%' THEN 2
                    WHEN name LIKE '%Love is%' THEN 3
                    ELSE 4
                END,
                created_at ASC
        ''') as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def add_book_style(name: str, description: str, filename: str, category: str) -> Dict:
    """Добавляет новый стиль книги"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO book_styles (name, description, filename, category, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        ''', (name, description, filename, category))
        await db.commit()
        
        # Получаем созданный стиль
        style_id = cursor.lastrowid
        async with db.execute('''
            SELECT id, name, description, filename, category, created_at
            FROM book_styles
            WHERE id = ?
        ''', (style_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(zip([column[0] for column in cursor.description], row))

async def delete_book_style(style_id: int) -> bool:
    """Удаляет стиль книги по ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('DELETE FROM book_styles WHERE id = ?', (style_id,))
        await db.commit()
        return cursor.rowcount > 0

async def update_book_style(style_id: int, name: str, description: str, filename: str, category: str) -> bool:
    """Обновляет стиль книги"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            UPDATE book_styles 
            SET name = ?, description = ?, filename = ?, category = ?
            WHERE id = ?
        ''', (name, description, filename, category, style_id))
        await db.commit()
        return cursor.rowcount > 0

# --- Функции для работы со стилями голоса ---

async def get_voice_styles() -> List[Dict]:
    """Получает все стили голоса"""
    async with aiosqlite.connect(DB_PATH) as db:
        print(f"🔍 Выполняем запрос к таблице voice_styles")
        async with db.execute('''
            SELECT id, name, description, filename, gender, created_at
            FROM voice_styles
            ORDER BY created_at DESC
        ''') as cursor:
            rows = await cursor.fetchall()
            result = [dict(zip([column[0] for column in cursor.description], row)) for row in rows]
            print(f"✅ Получено {len(result)} записей из voice_styles: {result}")
            return result

async def add_voice_style(name: str, description: str, filename: str, gender: str = "male") -> Dict:
    """Добавляет новый стиль голоса"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO voice_styles (name, description, filename, gender, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        ''', (name, description, filename, gender))
        await db.commit()
        
        # Получаем созданный стиль
        style_id = cursor.lastrowid
        async with db.execute('''
            SELECT id, name, description, filename, gender, created_at
            FROM voice_styles
            WHERE id = ?
        ''', (style_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(zip([column[0] for column in cursor.description], row))

async def delete_voice_style(style_id: int) -> bool:
    """Удаляет стиль голоса"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            DELETE FROM voice_styles WHERE id = ?
        ''', (style_id,))
        await db.commit()
        return cursor.rowcount > 0

async def update_voice_style(style_id: int, name: str, description: str, filename: str, gender: str = "male") -> bool:
    """Обновляет стиль голоса"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            UPDATE voice_styles 
            SET name = ?, description = ?, filename = ?, gender = ?
            WHERE id = ?
        ''', (name, description, filename, gender, style_id))
        await db.commit()
        return cursor.rowcount > 0

async def get_all_delayed_messages() -> List[Dict]:
    """Получает все отложенные сообщения с информацией о менеджере"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT dm.*, m.email as manager_email, m.full_name as manager_name
            FROM delayed_messages dm
            LEFT JOIN managers m ON dm.manager_id = m.id
            ORDER BY dm.created_at DESC
        ''') as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def get_manager_delayed_messages(manager_email: str) -> List[Dict]:
    """Получает отложенные сообщения только для заказов менеджера"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT dm.*, m.email as manager_email, m.full_name as manager_name
            FROM delayed_messages dm
            LEFT JOIN managers m ON dm.manager_id = m.id
            WHERE m.email = ? OR dm.manager_id IS NULL
            ORDER BY dm.created_at DESC
        ''', (manager_email,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]
async def can_manager_access_delayed_message(manager_email: str, message_id: int) -> bool:
    """Проверяет, может ли менеджер получить доступ к отложенному сообщению"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, является ли пользователь администратором (is_super_admin = 1)
        async with db.execute('''
            SELECT is_super_admin FROM managers WHERE email = ?
        ''', (manager_email,)) as cursor:
            row = await cursor.fetchone()
            if not row or row[0] != 1:
                return False  # Только администраторы имеют доступ
        
        # Администраторы имеют доступ ко всем сообщениям и шаблонам
        return True

async def can_manager_access_message_template(manager_email: str, template_id: int) -> bool:
    """Проверяет, может ли менеджер получить доступ к шаблону сообщения"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, является ли пользователь администратором (is_super_admin = 1)
        async with db.execute('''
            SELECT is_super_admin FROM managers WHERE email = ?
        ''', (manager_email,)) as cursor:
            row = await cursor.fetchone()
            if not row or row[0] != 1:
                return False  # Только администраторы имеют доступ
        
        # Администраторы имеют доступ ко всем шаблонам
        return True

async def delete_delayed_message(message_id: int) -> bool:
    """Удаляет отложенное сообщение"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            DELETE FROM delayed_messages WHERE id = ?
        ''', (message_id,))
        await db.commit()
        return cursor.rowcount > 0

async def get_delayed_message_by_id(message_id: int) -> Optional[Dict]:
    """Получает отложенное сообщение по ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT dm.*, m.email as manager_email, m.full_name as manager_name
            FROM delayed_messages dm
            LEFT JOIN managers m ON dm.manager_id = m.id
            WHERE dm.id = ?
        ''', (message_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                message = dict(row)
                # Получаем файлы для сообщения
                files = await get_delayed_message_files(message_id)
                message['files'] = files
                return message
            return None

async def update_delayed_message(message_id: int, content: str, delay_minutes: int, message_type: str) -> bool:
    """Обновляет отложенное сообщение"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Пересчитываем scheduled_at на основе новой задержки
        cursor = await db.execute('''
            UPDATE delayed_messages 
            SET content = ?, delay_minutes = ?, message_type = ?, scheduled_at = datetime(created_at, '+' || ? || ' minutes')
            WHERE id = ?
        ''', (content, delay_minutes, message_type, delay_minutes, message_id))
        await db.commit()
        return cursor.rowcount > 0

async def cleanup_trigger_messages_by_type(order_id: int, message_types: List[str]) -> int:
    """
    Удаляет триггерные сообщения определенных типов для заказа
    Возвращает количество удаленных сообщений
    """
    async with aiosqlite.connect(DB_PATH) as db:
        if not message_types:
            return 0
            
        placeholders = ','.join(['?' for _ in message_types])
        cursor = await db.execute(f'''
            DELETE FROM delayed_messages 
            WHERE order_id = ? AND message_type IN ({placeholders}) AND status = 'pending'
        ''', [order_id] + message_types)
        await db.commit()
        return cursor.rowcount

async def get_trigger_messages_for_order(order_id: int) -> List[Dict]:
    """
    Получает все триггерные сообщения для заказа с группировкой по типам
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT message_type, COUNT(*) as count, 
                   GROUP_CONCAT(id) as message_ids,
                   MIN(scheduled_at) as next_scheduled
            FROM delayed_messages 
            WHERE order_id = ? AND status = 'pending'
            GROUP BY message_type
            ORDER BY message_type
        ''', (order_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

# --- Функции для работы с ценами ---

async def get_pricing_items() -> List[Dict]:
    """Получает все цены"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT * FROM pricing_items ORDER BY created_at DESC
        ''') as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def create_pricing_item(product: str, price: float, currency: str, description: str, upgrade_price_difference: float = 0.0, is_active: bool = True) -> int:
    """Создает новую цену"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO pricing_items (product, price, currency, description, upgrade_price_difference, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        ''', (product, price, currency, description, upgrade_price_difference, is_active))
        await db.commit()
        return cursor.lastrowid

async def update_pricing_item(item_id: int, product: str, price: float, currency: str, description: str, upgrade_price_difference: float = 0.0, is_active: bool = True) -> bool:
    """Обновляет цену"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            UPDATE pricing_items 
            SET product = ?, price = ?, currency = ?, description = ?, upgrade_price_difference = ?, is_active = ?, updated_at = datetime('now')
            WHERE id = ?
        ''', (product, price, currency, description, upgrade_price_difference, is_active, item_id))
        await db.commit()
        return cursor.rowcount > 0

async def toggle_pricing_item(item_id: int, is_active: bool) -> bool:
    """Переключает статус цены"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            UPDATE pricing_items 
            SET is_active = ?, updated_at = datetime('now')
            WHERE id = ?
        ''', (is_active, item_id))
        await db.commit()
        return cursor.rowcount > 0
async def delete_pricing_item(item_id: int) -> bool:
    """Удаляет цену"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            DELETE FROM pricing_items WHERE id = ?
        ''', (item_id,))
        await db.commit()
        return cursor.rowcount > 0

async def populate_pricing_items() -> None:
    """Заполняет таблицу цен начальными данными"""
    prices = [
        ("📄 Электронная книга", 1990.0, "RUB", "Персональная книга в электронном формате", 0.0, True),  # Разница 0, так как это базовая версия
        ("📦 Электронная + Печатная версия", 7639.0, "RUB", "Электронная книга + печатная версия с доставкой", 4000.0, True),  # Разница 4000 для апгрейда
        ("💌 Персональная песня", 2990.0, "RUB", "Уникальная песня с вашим голосом", 0.0, True),  # Разница 0, так как нет апгрейда
    ]
    
    # Проверяем, есть ли уже цены в базе
    existing_items = await get_pricing_items()
    if existing_items:
        print("💰 Цены уже существуют в базе данных, пропускаем заполнение")
        return
    
    for product, price, currency, description, upgrade_difference, is_active in prices:
        await create_pricing_item(product, price, currency, description, upgrade_difference, is_active)

# --- Функции для работы с контентом ---

async def get_content_steps() -> List[Dict]:
    """Получает все шаги контента"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT * FROM content_steps ORDER BY created_at DESC
        ''') as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def create_content_step(step_key: str, step_name: str, content_type: str, content: str, materials: str, is_active: bool) -> int:
    """Создает новый шаг контента"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO content_steps (step_key, step_name, content_type, content, materials, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        ''', (step_key, step_name, content_type, content, materials, is_active))
        await db.commit()
        return cursor.lastrowid

async def update_content_step(step_id: int, step_key: str, step_name: str, content_type: str, content: str, materials: str, is_active: bool) -> bool:
    """Обновляет шаг контента"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            UPDATE content_steps 
            SET step_key = ?, step_name = ?, content_type = ?, content = ?, materials = ?, is_active = ?, updated_at = datetime('now')
            WHERE id = ?
        ''', (step_key, step_name, content_type, content, materials, is_active, step_id))
        await db.commit()
        return cursor.rowcount > 0

async def toggle_content_step(step_id: int, is_active: bool) -> bool:
    """Переключает статус шага контента"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            UPDATE content_steps 
            SET is_active = ?, updated_at = datetime('now')
            WHERE id = ?
        ''', (is_active, step_id))
        await db.commit()
        return cursor.rowcount > 0

async def delete_content_step(step_id: int) -> bool:
    """Удаляет шаг контента"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            DELETE FROM content_steps WHERE id = ?
        ''', (step_id,))
        await db.commit()
        return cursor.rowcount > 0

# --- Функции для работы с сообщениями бота ---

# --- Функции для работы с квизом песни ---
async def get_song_quiz_list() -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT * FROM song_quiz ORDER BY relation_key, author_gender
        ''') as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def get_song_quiz_item(relation_key: str, author_gender: str) -> Dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT * FROM song_quiz WHERE relation_key = ? AND author_gender = ? AND is_active = 1
        ''', (relation_key, author_gender)) as cursor:
            row = await cursor.fetchone()
            return dict(zip([column[0] for column in cursor.description], row)) if row else None

async def get_song_quiz_by_id(quiz_id: int) -> Dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT * FROM song_quiz WHERE id = ?
        ''', (quiz_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(zip([column[0] for column in cursor.description], row)) if row else None

async def create_song_quiz_item(relation_key: str, author_gender: str, title: str, intro: str, phrases_hint: str, questions_json: str, outro: str, is_active: bool = True) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            INSERT OR REPLACE INTO song_quiz (relation_key, author_gender, title, intro, phrases_hint, questions_json, outro, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        ''', (relation_key, author_gender, title, intro, phrases_hint, questions_json, outro, is_active))
        await db.commit()
        return cursor.lastrowid

async def update_song_quiz_item(item_id: int, relation_key: str, author_gender: str, title: str, intro: str, phrases_hint: str, questions_json: str, outro: str, is_active: bool) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        print(f"🔍 Обновление квиза в БД: ID={item_id}, relation_key={relation_key}, author_gender={author_gender}")
        print(f"🔍 intro (полный): {repr(intro)}")
        print(f"🔍 phrases_hint: {phrases_hint}")
        print(f"🔍 questions_json: {questions_json}")
        print(f"🔍 outro (полный): {repr(outro)}")
        
        cursor = await db.execute('''
            UPDATE song_quiz
            SET relation_key = ?, author_gender = ?, title = ?, intro = ?, phrases_hint = ?, questions_json = ?, outro = ?, is_active = ?, updated_at = datetime('now')
            WHERE id = ?
        ''', (relation_key, author_gender, title, intro, phrases_hint, questions_json, outro, is_active, item_id))
        await db.commit()
        
        print(f"🔍 Обновлено строк: {cursor.rowcount}")
        return cursor.rowcount > 0

async def delete_song_quiz_item(item_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('DELETE FROM song_quiz WHERE id = ?', (item_id,))
        await db.commit()
        return cursor.rowcount > 0

async def get_bot_messages() -> List[Dict]:
    """Получает все сообщения бота"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT * FROM bot_messages ORDER BY sort_order, context, stage, message_name
        ''') as cursor:
            rows = await cursor.fetchall()
            messages = [dict(zip([column[0] for column in cursor.description], row)) for row in rows]
            
            # Для определенных сообщений подставляем примеры данных
            for message in messages:
                if message['message_key'] == 'book_delivery_confirmed':
                    # Подставляем пример данных для админки
                    example_content = message['content'].replace("г. щшовылтдьм", "г. Москва, ул. Тверская, д. 1, кв. 10")
                    example_content = example_content.replace("иапмт", "Иванов Иван Иванович")
                    example_content = example_content.replace("89068714014", "+7 (999) 123-45-67")
                    message['content'] = example_content
                elif message['message_key'] == 'book_pages_selection_completed':
                    # Подставляем пример количества страниц
                    example_content = message['content'].replace("24/24", "15/24")
                    example_content = example_content.replace("24 уникальных", "15 уникальных")
                    message['content'] = example_content
                elif message['message_key'] == 'privacy_consent_request':
                    # Подставляем пример номера заказа
                    example_content = message['content'].replace("№0458", "№1234")
                    message['content'] = example_content
            
            return messages

async def upsert_bot_message(message_key: str, message_name: str, content: str, context: str = None, stage: str = None, sort_order: int = 0) -> int:
    """Добавляет или обновляет сообщение бота"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            INSERT OR REPLACE INTO bot_messages 
            (message_key, message_name, content, context, stage, sort_order, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        ''', (message_key, message_name, content, context, stage, sort_order))
        await db.commit()
        return cursor.lastrowid

async def update_bot_message(message_id: int, content: str, is_active: bool = True) -> bool:
    """Обновляет сообщение бота"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Сначала получаем ключ сообщения для логирования
            message_key = None
            try:
                cursor = await db.execute('SELECT message_key FROM bot_messages WHERE id = ?', (message_id,))
                row = await cursor.fetchone()
                if row:
                    message_key = row[0]
            except Exception as e:
                logging.error(f"Ошибка получения ключа сообщения: {e}")
            
            # Конвертируем примеры обратно в плейсхолдеры для определенных сообщений
            processed_content = content
            if message_key == 'book_delivery_confirmed':
                # Конвертируем примеры обратно в плейсхолдеры
                processed_content = processed_content.replace("г. Москва, ул. Тверская, д. 1, кв. 10", "г. щшовылтдьм")
                processed_content = processed_content.replace("Иванов Иван Иванович", "иапмт")
                processed_content = processed_content.replace("+7 (999) 123-45-67", "89068714014")
            elif message_key == 'book_pages_selection_completed':
                # Конвертируем пример количества страниц обратно
                processed_content = processed_content.replace("15/24", "24/24")
                processed_content = processed_content.replace("15 уникальных", "24 уникальных")
            elif message_key == 'privacy_consent_request':
                # Конвертируем пример номера заказа обратно
                processed_content = processed_content.replace("№1234", "№0458")
            
            # Обновляем сообщение
            cursor = await db.execute('''
                UPDATE bot_messages 
                SET content = ?, is_active = ?, updated_at = datetime('now')
                WHERE id = ?
            ''', (processed_content, is_active, message_id))
            await db.commit()
            
            # Логируем успешное обновление
            if message_key:
                logging.info(f"Сообщение {message_key} обновлено в базе данных")
            else:
                logging.info(f"Сообщение с ID {message_id} обновлено в базе данных")
            
            return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"Ошибка обновления сообщения {message_id}: {e}")
        return False

async def delete_bot_message(message_id: int) -> bool:
    """Удаляет сообщение бота"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            DELETE FROM bot_messages 
            WHERE id = ?
        ''', (message_id,))
        await db.commit()
        return cursor.rowcount > 0

async def increment_message_usage(message_key: str) -> bool:
    """Увеличивает счетчик использования сообщения"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            UPDATE bot_messages 
            SET usage_count = usage_count + 1, last_used = datetime('now')
            WHERE message_key = ?
        ''', (message_key,))
        await db.commit()
        return cursor.rowcount > 0

async def get_bot_message_by_key(message_key: str) -> Dict:
    """Получает сообщение бота по ключу"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT * FROM bot_messages WHERE message_key = ?
        ''', (message_key,)) as cursor:
            row = await cursor.fetchone()
            return dict(zip([column[0] for column in cursor.description], row)) if row else None

async def get_bot_message_by_id(message_id: int) -> Dict:
    """Получает сообщение бота по ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT * FROM bot_messages WHERE id = ?
        ''', (message_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(zip([column[0] for column in cursor.description], row)) if row else None
async def populate_bot_messages() -> None:
    """Заполняет таблицу сообщений бота начальными данными"""
    # Проверяем, есть ли уже сообщения в базе
    existing_messages = await get_bot_messages()
    if existing_messages:
        print("📝 Сообщения бота уже существуют в базе данных, пропускаем заполнение")
        return
    
    messages = [
        # === ПРИВЕТСТВИЕ И НАЧАЛО ===
        ("welcome_message", "Приветственное сообщение", 
         "👋 Привет!\n\nЯ помогу тебе создать уникальный подарок — персональную книгу или песню с твоим голосом, лицом и теплом — для любимого человека.\n\nЭто будет история или мелодия, в которой ты — главный герой.\n\nГотов начать? 💌", 
         "welcome", "start", 1),
        
        ("welcome_ready", "Готов начать", 
         "👋 Привет! Готов начать создание подарка?", 
         "welcome", "start", 2),
        
        # === РЕГИСТРАЦИЯ ===
        ("phone_request", "Запрос номера телефона", 
         "Пожалуйста, отправьте ваш номер телефона, нажав кнопку ниже, а затем отправьте контакт вручную.", 
         "registration", "phone"),
        
        ("name_request", "Запрос имени", 
         "Пожалуйста, введите ваше имя:", 
         "registration", "name"),
        
        ("lastname_request", "Запрос фамилии", 
         "Пожалуйста, введите вашу фамилию:", 
         "registration", "lastname"),
        
        ("registration_success", "Регистрация успешна", 
         "Спасибо! Данные сохранены.", 
         "registration", "success"),
        
        # === ВЫБОР ПРОДУКТА ===
        ("product_selection", "Выбор продукта", 
         "Выберите, что хотите создать:", 
         "product", "selection"),
        
        ("product_book", "Книга", 
         "📖 Персональная книга", 
         "product", "book"),
        
        ("product_song", "Песня", 
         "🎵 Персональная песня", 
         "product", "song"),
        
        # === ПУТЬ СОЗДАНИЯ ПЕСНИ ===
        ("song_intro", "Введение к созданию песни", 
         "🎵 Отлично! Вы выбрали создание персональной песни.\n\nМы создадим уникальную песню с вашим голосом, которая будет посвящена вашему любимому человеку.", 
         "song", "intro"),
        
        ("song_voice_request", "Запрос голосового сообщения", 
         "🎤 Теперь запишите голосовое сообщение с вашим пением.\n\nСпойте любую песню, которая вам нравится, или просто напойте мелодию. Это поможет нам понять ваш голос и стиль.", 
         "song", "voice"),
        
        ("song_voice_instructions", "Инструкции для записи голоса", 
         "📝 Советы для записи:\n• Найдите тихое место\n• Говорите четко и эмоционально\n• Запись должна быть 10-30 секунд\n• Можно спеть куплет любимой песни", 
         "song", "voice_instructions"),
        
        ("song_voice_received", "Голосовое сообщение получено", 
         "✅ Ваше голосовое сообщение получено! Мы анализируем ваш голос...", 
         "song", "voice_received"),
        
        ("song_style_request", "Запрос стиля песни", 
         "🎼 Какой стиль песни вы предпочитаете?\n\nВыберите один из вариантов:", 
         "song", "style"),
        
        ("song_style_pop", "Поп-стиль", 
         "🎵 Поп - легкая, мелодичная песня", 
         "song", "style_pop"),
        
        ("song_style_romantic", "Романтический стиль", 
         "💕 Романтическая - нежная, лирическая песня", 
         "song", "style_romantic"),
        
        ("song_style_fun", "Веселая песня", 
         "😊 Веселая - позитивная, энергичная песня", 
         "song", "style_fun"),
        
        ("song_style_ballad", "Баллада", 
         "🎭 Баллада - медленная, душевная песня", 
         "song", "style_ballad"),
        
        ("song_style_custom", "Свой стиль", 
         "🎨 Свой стиль - опишите, какой стиль вы хотите", 
         "song", "style_custom"),
        
        ("song_custom_style_request", "Запрос описания стиля", 
         "Опишите, какой стиль песни вы хотите (например: рок, джаз, электронная музыка и т.д.):", 
         "song", "custom_style"),
        
        ("song_mood_request", "Запрос настроения", 
         "🎭 Какое настроение должна передавать песня?", 
         "song", "mood"),
        
        ("song_mood_love", "Любовное настроение", 
         "💕 Любовное - нежные чувства и признания", 
         "song", "mood_love"),
        
        ("song_mood_friendship", "Дружеское настроение", 
         "🤝 Дружеское - теплая дружба и поддержка", 
         "song", "mood_friendship"),
        
        ("song_mood_gratitude", "Благодарность", 
         "🙏 Благодарность - признательность и уважение", 
         "song", "mood_gratitude"),
        
        ("song_mood_celebration", "Праздничное", 
         "🎉 Праздничное - радость и веселье", 
         "song", "mood_celebration"),
        
        ("song_mood_nostalgic", "Ностальгическое", 
         "📸 Ностальгическое - воспоминания о прошлом", 
         "song", "mood_nostalgic"),
        
        ("song_instrument_request", "Запрос инструментов", 
         "🎸 Какие инструменты вы хотели бы слышать в песне?", 
         "song", "instruments"),
        
        ("song_instrument_piano", "Фортепиано", 
         "🎹 Фортепиано - классическое звучание", 
         "song", "instrument_piano"),
        
        ("song_instrument_guitar", "Гитара", 
         "🎸 Гитара - акустическое или электрическое звучание", 
         "song", "instrument_guitar"),
        
        ("song_instrument_orchestra", "Оркестр", 
         "🎻 Оркестр - богатое, классическое звучание", 
         "song", "instrument_orchestra"),
        
        ("song_instrument_electronic", "Электронная музыка", 
         "🎧 Электронная музыка - современное звучание", 
         "song", "instrument_electronic"),
        
        ("song_instrument_mixed", "Смешанные инструменты", 
         "🎼 Смешанные инструменты - комбинация разных стилей", 
         "song", "instrument_mixed"),
        
        ("song_duration_request", "Запрос длительности", 
         "⏱️ Какой длительности должна быть песня?", 
         "song", "duration"),
        
        ("song_duration_short", "Короткая (1-2 минуты)", 
         "⏱️ Короткая - 1-2 минуты", 
         "song", "duration_short"),
        
        ("song_duration_medium", "Средняя (2-3 минуты)", 
         "⏱️ Средняя - 2-3 минуты", 
         "song", "duration_medium"),
        
        ("song_duration_long", "Длинная (3-4 минуты)", 
         "⏱️ Длинная - 3-4 минуты", 
         "song", "duration_long"),
        
        ("song_language_request", "Запрос языка", 
         "🌍 На каком языке должна быть песня?", 
         "song", "language"),
        
        ("song_language_russian", "Русский", 
         "🇷🇺 Русский", 
         "song", "language_russian"),
        
        ("song_language_english", "Английский", 
         "🇺🇸 Английский", 
         "song", "language_english"),
        
        ("song_language_mixed", "Смешанный", 
         "🌍 Смешанный - русский и английский", 
         "song", "language_mixed"),
        
        ("song_special_requests", "Запрос особых пожеланий", 
         "💭 Есть ли особые пожелания к песне?\n\nНапример:\n• Ссылки на любимые песни\n• Особые слова или фразы\n• Стиль исполнения\n• Или просто напишите 'Нет'", 
         "song", "special_requests"),
        
        ("song_processing", "Обработка песни", 
         "🎵 Создаем вашу персональную песню...\n\nЭто займет некоторое время. Мы уведомим вас, когда песня будет готова!", 
         "song", "processing"),
        
        ("song_demo_ready", "Демо песни готово", 
         "🎵 Ваша демо-версия песни готова!\n\nПослушайте и скажите, что думаете:", 
         "song", "demo_ready"),
        
        ("song_demo_feedback", "Запрос отзыва о демо", 
         "Как вам демо-версия? Хотите что-то изменить?", 
         "song", "demo_feedback"),
        
        ("song_final_ready", "Финальная версия готова", 
         "🎵 Ваша персональная песня готова!\n\nЭто уникальная песня, созданная специально для вас и вашего любимого человека.", 
         "song", "final_ready"),
        
        ("song_download_ready", "Скачивание готово", 
         "📥 Ваша песня готова к скачиванию!\n\nВы получите:\n• Аудиофайл в высоком качестве\n• Текст песни\n• Инструкции по использованию", 
         "song", "download_ready"),
        
        ("song_error_voice", "Ошибка записи голоса", 
         "❌ Не удалось обработать голосовое сообщение. Попробуйте записать еще раз.", 
         "song", "error_voice"),
        
        ("song_error_processing", "Ошибка обработки песни", 
         "❌ Произошла ошибка при создании песни. Попробуйте еще раз или обратитесь в поддержку.", 
         "song", "error_processing"),
        
        # === ВЫБОР ОТНОШЕНИЯ ===
        ("relation_selection", "Выбор отношения", 
         "Кому вы хотите сделать подарок?", 
         "relation", "selection"),
        
        # === ИНФОРМАЦИЯ О ГЕРОЕ ===
        ("hero_name_request", "Запрос имени героя", 
         "Пожалуйста, введите имя получателя:", 
         "hero", "name"),
        
        ("hero_intro_request", "Запрос описания героя", 
         "Нам важно узнать чуть больше о том, кому будет посвящена книга ❤️\nЧтобы персонаж был максимально похож, расскажи: сколько ему лет, какого цвета у него глаза и есть ли особенные детали, которые важно указать 🩷\nЭти детали помогут художнику передать его уникальность на страницах книги 💞", 
         "hero", "intro"),
        
        ("gift_reason_request", "Запрос повода подарка", 
         "Напиши по какому поводу мы создаём песню🎶\nИли это просто подарок без повода?", 
         "gift", "reason"),
        
        # === ЗАГРУЗКА ФОТОГРАФИЙ ===
        ("photo_face_1", "Запрос первого фото лица", 
         "Пожалуйста, отправьте первое фото основного героя (лицом):", 
         "photo", "face_1"),
        
        ("photo_face_2", "Запрос второго фото лица", 
         "Отправьте второе фото основного героя (лицом):", 
         "photo", "face_2"),
        
        ("photo_full", "Запрос фото в полный рост", 
         "Отправьте фото основного героя в полный рост:", 
         "photo", "full"),
        
        ("photo_joint", "Запрос совместного фото", 
         "Отлично! Теперь отправьте совместное фото всех героев:", 
         "photo", "joint"),
        
        # === ДОПОЛНИТЕЛЬНЫЕ ГЕРОИ ===
        ("add_hero_prompt", "Предложение добавить героя", 
         "Теперь добавьте второго героя:", 
         "hero", "add"),
        
        ("new_hero_name", "Запрос имени нового героя", 
         "Введите имя нового героя:", 
         "hero", "new_name"),
        
        ("new_hero_intro", "Описание нового героя", 
         "Расскажите немного о герое {hero_name}:\n\nПример: Это мой друг, ему 27 лет, он профессионально занимается хокеем, работает в такси и любит собак.", 
         "hero", "new_intro"),
        
        ("new_hero_photo_1", "Фото нового героя 1", 
         "Отправьте первое фото героя {hero_name} (лицом):", 
         "hero", "new_photo_1"),
        
        ("new_hero_photo_2", "Фото нового героя 2", 
         "Отправьте второе фото героя {hero_name} (лицом):", 
         "hero", "new_photo_2"),
        
        ("new_hero_photo_full", "Фото нового героя в полный рост", 
         "Отправьте фото героя {hero_name} в полный рост:", 
         "hero", "new_photo_full"),
        
        # === ВОПРОСЫ ПО ОТНОШЕНИЮ ===
        ("question_1_intro", "Введение к первому вопросу", 
         "Отлично! Теперь ответьте на несколько вопросов о ваших отношениях с {relation}.\n\nВопрос 1 из 3:", 
         "question", "intro"),
        
        ("question_1_text", "Первый вопрос", 
         "Что вы обычно делаете вместе с {relation}?", 
         "question", "q1"),
        
        ("question_2_text", "Второй вопрос", 
         "Вопрос 2 из 3:\n\nКакой момент с {relation} вы считаете самым трогательным?", 
         "question", "q2"),
        
        ("question_3_text", "Третий вопрос", 
         "Вопрос 3 из 3:\n\nЧто бы вы хотели пожелать {relation}?", 
         "question", "q3"),
        
        ("answer_request", "Запрос ответа", 
         "Пожалуйста, напишите ваш ответ:", 
         "question", "answer"),
        
        # === ОПЛАТА ===
        ("payment_intro", "Введение к оплате", 
         "Отлично! Теперь давайте перейдем к оплате.", 
         "payment", "intro"),
        
        ("payment_success", "Оплата успешна", 
         "✅ Оплата прошла успешно! Ваш заказ принят в работу.", 
         "payment", "success"),
        
        ("payment_error", "Ошибка оплаты", 
         "❌ Произошла ошибка при оплате. Попробуйте еще раз или обратитесь в поддержку.", 
         "payment", "error"),
        
        # === ВЫБОР СТРАНИЦ ===
        ("page_selection_intro", "Введение к выбору страниц", 
         "Теперь выберите страницы для вашей книги. Вам нужно выбрать минимум 19 страниц.", 
         "page_selection", "intro"),
        
        ("page_selection_minimum", "Минимум страниц", 
         "❌ Сначала выберите минимум 19 страниц, затем напишите 'Далее'.", 
         "page_selection", "minimum"),
        
        ("page_selection_continue", "Продолжение выбора", 
         "ℹ️ Напишите 'Далее' когда выберете минимум 19 страниц и будете готовы продолжить.", 
         "page_selection", "continue"),
        
        ("page_selected", "Страница выбрана", 
         "✅ Страница выбрана!", 
         "page_selection", "selected"),
        
        ("page_removed", "Страница убрана", 
         "❌ Страница убрана из выбранных", 
         "page_selection", "removed"),
        
        # === ДЕМО-КОНТЕНТ ===
        ("demo_content_intro", "Введение демо-контента", 
         "🎨 Вот примеры оформления вашей книги:", 
         "demo", "intro"),
        
        ("demo_content_continue", "Продолжение после демо", 
         "Как вам такие варианты? Готовы продолжить?", 
         "demo", "continue"),
        
        # === ЧЕРНОВИК ===
        ("draft_review_intro", "Введение черновика", 
         "📖 Вот черновик вашей книги. Как вам результат?", 
         "draft", "intro"),
        
        ("draft_feedback_request", "Запрос отзыва о черновике", 
         "Если все устраивает, нажмите 'Всё супер'. Если хотите что-то изменить, нажмите 'Внести правки'.", 
         "draft", "feedback"),
        
        ("draft_edit_request", "Запрос правок", 
         "Опишите, что хотите изменить в книге:", 
         "draft", "edit"),
        
        ("draft_approved", "Черновик одобрен", 
         "Отлично! Ваш черновик одобрен.", 
         "draft", "approved"),
        
        # === ВЫБОР ОБЛОЖКИ ===
        ("cover_selection_intro", "Введение к выбору обложки", 
         "🎨 Варианты обложек для вашей книги:", 
         "cover", "intro"),
        
        ("cover_selected", "Обложка выбрана", 
         "✅ Обложка выбрана: {cover_id}", 
         "cover", "selected"),
        
        # === ДОСТАВКА ===
        ("delivery_address_request", "Запрос адреса доставки", 
         "📦 <b>Для печатной версии нужен адрес доставки</b>\n\nПожалуйста, введите ваш полный адрес доставки в формате:\n• Индекс\n• Город\n• Улица, дом, квартира\n• ФИО получателя\n• Телефон для связи", 
         "delivery", "address"),
        
        ("delivery_confirmed", "Доставка подтверждена", 
         "✅ Адрес доставки сохранен!", 
         "delivery", "confirmed"),
        
        # === ЗАВЕРШЕНИЕ ===
        ("order_completed", "Заказ завершен", 
         "🎉 <b>Ваша книга готова!</b>\n\nМы создали уникальную книгу специально для вас. Надеемся, что она принесет радость и теплые воспоминания!", 
         "completion", "finished"),
        
        ("order_in_progress", "Заказ в работе", 
         "🔄 Ваш заказ принят в работу. Мы уведомим вас о прогрессе.", 
         "completion", "in_progress"),
        
        # === ОШИБКИ ===
        ("error_photo_expected", "Ошибка - ожидается фото", 
         "Пожалуйста, отправьте фото, а не текст.", 
         "error", "photo_expected"),
        
        ("error_text_expected", "Ошибка - ожидается текст", 
         "Пожалуйста, отправьте текст, а не фото.", 
         "error", "text_expected"),
        
        ("error_general", "Общая ошибка", 
         "Произошла ошибка. Попробуйте еще раз или обратитесь в поддержку.", 
         "error", "general"),
        
        ("error_photo_processing", "Ошибка обработки фото", 
         "Произошла ошибка при обработке фото. Попробуйте еще раз.", 
         "error", "photo_processing"),
        
        ("error_order_creation", "Ошибка создания заказа", 
         "Произошла ошибка при создании заказа. Попробуйте еще раз или обратитесь в поддержку.", 
         "error", "order_creation"),
        
        ("error_payment", "Ошибка оплаты", 
         "Произошла ошибка при переходе к оплате. Попробуйте еще раз или обратитесь в поддержку.", 
         "error", "payment"),
        
        # === ИНФОРМАЦИОННЫЕ СООБЩЕНИЯ ===
        ("info_photo_received", "Фото получено", 
         "Фото получено, но сейчас не ожидается загрузка фотографий.", 
         "info", "photo_received"),
        
        ("info_waiting", "Ожидание", 
         "Пожалуйста, подождите...", 
         "info", "waiting"),
        
        ("info_processing", "Обработка", 
         "Обрабатываем ваш запрос...", 
         "info", "processing"),
        
        # === НАПОМИНАНИЯ ===
        ("reminder_payment_24h", "Напоминание об оплате 24ч", 
         "Возможно, цена вас смутила? Мы можем предложить другие варианты — напишите нам.", 
         "reminder", "payment_24h"),
        
        ("reminder_payment_48h", "Напоминание об оплате 48ч", 
         "Готовы сделать книгу проще, но не менее искренней. Дайте знать, если вам это интересно.", 
         "reminder", "payment_48h"),
        
        # === КНОПКИ И ИНТЕРФЕЙС ===
        ("button_yes", "Кнопка Да", 
         "Да", 
         "button", "yes"),
        
        ("button_no", "Кнопка Нет", 
         "Нет", 
         "button", "no"),
        
        ("button_next", "Кнопка Далее", 
         "Далее", 
         "button", "next"),
        
        ("button_back", "Кнопка Назад", 
         "Назад", 
         "button", "back"),
        
        ("button_edit", "Кнопка Редактировать", 
         "Редактировать", 
         "button", "edit"),
        
        ("button_approve", "Кнопка Одобрить", 
         "Одобрить", 
         "button", "approve"),
        
        ("button_select", "Кнопка Выбрать", 
         "Выбрать", 
         "button", "select"),
        
        ("button_remove", "Кнопка Убрать", 
         "Убрать", 
         "button", "remove"),
    ]
    
    for i, (message_key, message_name, content, context, stage) in enumerate(messages, 1):
        await upsert_bot_message(message_key, message_name, content, context, stage, i)
async def auto_collect_bot_messages() -> None:
    """Автоматически собирает сообщения из кода бота"""
    # Проверяем, есть ли уже сообщения в базе
    existing_messages = await get_bot_messages()
    if existing_messages:
        print("🔍 Сообщения бота уже существуют в базе данных, пропускаем автособирание")
        return
    
    # Этот список можно расширять по мере добавления новых сообщений в код
    auto_messages = [
        # Приветствие из WELCOME_TEXT
        ("welcome_text", "Приветственный текст", 
         "👋 Привет!\n\nЯ помогу тебе создать уникальный подарок — персональную книгу или песню с твоим голосом, лицом и теплом — для любимого человека.\n\nЭто будет история или мелодия, в которой ты — главный герой.\n\nГотов начать? 💌", 
         "welcome", "start"),
        
        # Сообщения из кода бота
        ("phone_contact_request", "Запрос контакта", 
         "Пожалуйста, отправьте ваш номер телефона, нажав кнопку ниже, а затем отправьте контакт вручную.", 
         "registration", "phone"),
        
        ("ready_to_start", "Готов начать", 
         "👋 Привет! Готов начать создание подарка?", 
         "welcome", "start"),
        
        ("first_name_request", "Запрос имени", 
         "Пожалуйста, введите вашу фамилию:", 
         "registration", "name"),
        
        ("last_name_request", "Запрос фамилии", 
         "Пожалуйста, введите ваше имя:", 
         "registration", "name"),
        
        ("data_saved", "Данные сохранены", 
         "Спасибо! Данные сохранены.", 
         "registration", "success"),
        
        ("recipient_name_request", "Запрос имени получателя", 
         "Пожалуйста, введите имя получателя:", 
         "hero", "name"),
        
        ("hero_description_request", "Запрос описания героя", 
         "Нам важно узнать чуть больше о том, кому будет посвящена книга ❤️\nЧтобы персонаж был максимально похож, расскажи: сколько ему лет, какого цвета у него глаза и есть ли особенные детали, которые важно указать 🩷\nЭти детали помогут художнику передать его уникальность на страницах книги 💞", 
         "hero", "intro"),
        
        ("gift_occasion_request", "Запрос повода", 
         "Напиши по какому поводу мы создаём песню🎶\nИли это просто подарок без повода?", 
         "gift", "reason"),
        
        ("first_face_photo", "Первое фото лица", 
         "Пожалуйста, отправьте первое фото основного героя (лицом):", 
         "photo", "face_1"),
        
        ("second_face_photo", "Второе фото лица", 
         "Отправьте второе фото основного героя (лицом):", 
         "photo", "face_2"),
        
        ("full_body_photo", "Фото в полный рост", 
         "Отправьте фото основного героя в полный рост:", 
         "photo", "full"),
        
        ("add_second_hero", "Добавить второго героя", 
         "Теперь добавьте второго героя:", 
         "hero", "add"),
        
        ("new_hero_name_input", "Имя нового героя", 
         "Введите имя нового героя:", 
         "hero", "new_name"),
        
        ("new_hero_description", "Описание нового героя", 
         "Расскажите немного о герое {hero_name}:\n\nПример: Это мой друг, ему 27 лет, он профессионально занимается хокеем, работает в такси и любит собак.", 
         "hero", "new_intro"),
        
        ("new_hero_face_1", "Первое фото нового героя", 
         "Отправьте первое фото героя {hero_name} (лицом):", 
         "hero", "new_photo_1"),
        
        ("new_hero_face_2", "Второе фото нового героя", 
         "Отправьте второе фото героя {hero_name} (лицом):", 
         "hero", "new_photo_2"),
        
        ("new_hero_full", "Фото нового героя в полный рост", 
         "Отправьте фото героя {hero_name} в полный рост:", 
         "hero", "new_photo_full"),
        
        ("joint_photo_request", "Совместное фото", 
         "Отлично! Теперь отправьте совместное фото всех героев:", 
         "photo", "joint"),
        
        ("questions_intro", "Введение к вопросам", 
         "Отлично! Теперь ответьте на несколько вопросов о ваших отношениях с {relation}.\n\nВопрос 1 из 3:", 
         "question", "intro"),
        
        ("question_1", "Первый вопрос", 
         "Что вы обычно делаете вместе с {relation}?", 
         "question", "q1"),
        
        ("question_2", "Второй вопрос", 
         "Вопрос 2 из 3:\n\nКакой момент с {relation} вы считаете самым трогательным?", 
         "question", "q2"),
        
        ("question_3", "Третий вопрос", 
         "Вопрос 3 из 3:\n\nЧто бы вы хотели пожелать {relation}?", 
         "question", "q3"),
        
        ("answer_input", "Ввод ответа", 
         "Пожалуйста, напишите ваш ответ:", 
         "question", "answer"),
        
        ("payment_transition", "Переход к оплате", 
         "Отлично! Теперь давайте перейдем к оплате.", 
         "payment", "intro"),
        
        ("page_selection_intro", "Введение к выбору страниц", 
         "Теперь выберите страницы для вашей книги. Вам нужно выбрать минимум 19 страниц.", 
         "page_selection", "intro"),
        
        ("minimum_pages_error", "Ошибка минимума страниц", 
         "❌ Сначала выберите минимум 19 страниц, затем напишите 'Далее'.", 
         "page_selection", "minimum"),
        
        ("continue_prompt", "Продолжение", 
         "ℹ️ Напишите 'Далее' когда выберете минимум 19 страниц и будете готовы продолжить.", 
         "page_selection", "continue"),
        
        ("demo_intro", "Введение демо", 
         "🎨 Вот примеры оформления вашей книги:", 
         "demo", "intro"),
        
        ("demo_continue", "Продолжение после демо", 
         "Как вам такие варианты? Готовы продолжить?", 
         "demo", "continue"),
        
        ("draft_intro", "Введение черновика", 
         "📖 Вот черновик вашей книги. Как вам результат?", 
         "draft", "intro"),
        
        ("draft_feedback", "Отзыв о черновике", 
         "Если все устраивает, нажмите 'Всё супер'. Если хотите что-то изменить, нажмите 'Внести правки'.", 
         "draft", "feedback"),
        
        ("cover_intro", "Введение к обложкам", 
         "🎨 <b>Варианты обложек для вашей книги:</b>", 
         "cover", "intro"),
        
        ("cover_selected", "Обложка выбрана", 
         "✅ Обложка выбрана: {cover_id}", 
         "cover", "selected"),
        
        ("delivery_address", "Запрос адреса доставки", 
         "📦 <b>Для печатной версии нужен адрес доставки</b>\n\nПожалуйста, введите ваш полный адрес доставки в формате:\n• Индекс\n• Город\n• Улица, дом, квартира\n• ФИО получателя\n• Телефон для связи", 
         "delivery", "address"),
        
        ("order_finished", "Заказ завершен", 
         "🎉 <b>Ваша книга готова!</b>\n\nМы создали уникальную книгу специально для вас. Надеемся, что она принесет радость и теплые воспоминания!", 
         "completion", "finished"),
        
        # Ошибки
        ("photo_expected_error", "Ошибка - ожидается фото", 
         "Пожалуйста, отправьте фото, а не текст.", 
         "error", "photo_expected"),
        
        ("text_expected_error", "Ошибка - ожидается текст", 
         "Пожалуйста, отправьте текст, а не фото.", 
         "error", "text_expected"),
        
        ("photo_processing_error", "Ошибка обработки фото", 
         "Произошла ошибка при обработке фото. Попробуйте еще раз или обратитесь в поддержку.", 
         "error", "photo_processing"),
        
        ("order_creation_error", "Ошибка создания заказа", 
         "Произошла ошибка при создании заказа. Попробуйте еще раз или обратитесь в поддержку.", 
         "error", "order_creation"),
        
        ("payment_error", "Ошибка оплаты", 
         "Произошла ошибка при переходе к оплате. Попробуйте еще раз или обратитесь в поддержку.", 
         "error", "payment"),
        
        ("cover_loading_error", "Ошибка загрузки обложек", 
         "Произошла ошибка при загрузке библиотеки обложек. Попробуйте позже.", 
         "error", "cover_loading"),
        
        # Информационные сообщения
        ("photo_received_info", "Фото получено", 
         "Фото получено, но сейчас не ожидается загрузка фотографий.", 
         "info", "photo_received"),
        
        ("processing_info", "Обработка", 
         "Обрабатываем ваш запрос...", 
         "info", "processing"),
        
        # === СООБЩЕНИЯ ДЛЯ ПЕСНИ (автоматический сбор) ===
        ("song_voice_processing", "Обработка голоса", 
         "🎤 Анализируем ваш голос...", 
         "song", "voice_processing"),
        
        ("song_style_selected", "Стиль выбран", 
         "✅ Стиль песни выбран!", 
         "song", "style_selected"),
        
        ("song_mood_selected", "Настроение выбрано", 
         "✅ Настроение песни выбрано!", 
         "song", "mood_selected"),
        
        ("song_instruments_selected", "Инструменты выбраны", 
         "✅ Инструменты выбраны!", 
         "song", "instruments_selected"),
        
        ("song_duration_selected", "Длительность выбрана", 
         "✅ Длительность песни выбрана!", 
         "song", "duration_selected"),
        
        ("song_language_selected", "Язык выбран", 
         "✅ Язык песни выбран!", 
         "song", "language_selected"),
        
        ("song_special_requests_saved", "Особые пожелания сохранены", 
         "✅ Ваши особые пожелания сохранены!", 
         "song", "special_requests_saved"),
        
        ("song_creation_started", "Создание песни началось", 
         "🎵 Начинаем создание вашей персональной песни...", 
         "song", "creation_started"),
        
        ("song_lyrics_ready", "Текст песни готов", 
         "📝 Текст вашей песни готов!", 
         "song", "lyrics_ready"),
        
        ("song_melody_ready", "Мелодия готова", 
         "🎼 Мелодия вашей песни готова!", 
         "song", "melody_ready"),
        
        ("song_arrangement_ready", "Аранжировка готова", 
         "🎹 Аранжировка вашей песни готова!", 
         "song", "arrangement_ready"),
        
        ("song_recording_ready", "Запись готова", 
         "🎤 Запись вашей песни готова!", 
         "song", "recording_ready"),
        
        ("song_mixing_ready", "Сведение готово", 
         "🎧 Сведение вашей песни готово!", 
         "song", "mixing_ready"),
        
        ("song_mastering_ready", "Мастеринг готов", 
         "🎚️ Мастеринг вашей песни готов!", 
         "song", "mastering_ready"),
        
        ("song_quality_check", "Проверка качества", 
         "🔍 Проверяем качество вашей песни...", 
         "song", "quality_check"),
        
        ("song_upload_ready", "Загрузка готова", 
         "📤 Загружаем вашу песню...", 
         "song", "upload_ready"),
        
        ("song_complete", "Песня завершена", 
         "🎉 Ваша персональная песня полностью готова!", 
         "song", "complete"),
        
        ("song_share_ready", "Готово к отправке", 
         "📤 Ваша песня готова к отправке получателю!", 
         "song", "share_ready"),
        
        # === ОБЩИЕ СООБЩЕНИЯ ДЛЯ КНИГИ И ПЕСНИ ===
        ("product_selection_confirmation", "Подтверждение выбора продукта", 
         "Отлично! Вы выбрали: {product}", 
         "common", "product_confirmation"),
        
        ("order_summary", "Сводка заказа", 
         "📋 Сводка вашего заказа:\n\nПродукт: {product}\nПолучатель: {recipient}\nПовод: {occasion}\n\nВсе верно?", 
         "common", "order_summary"),
        
        ("order_confirmed", "Заказ подтвержден", 
         "✅ Заказ подтвержден! Начинаем работу...", 
         "common", "order_confirmed"),
        
        ("progress_update", "Обновление прогресса", 
         "🔄 Прогресс: {progress}%", 
         "common", "progress_update"),
        
        ("estimated_time", "Ориентировочное время", 
         "⏱️ Ориентировочное время создания: {time}", 
         "common", "estimated_time"),
        
        ("contact_support", "Обращение в поддержку", 
         "📞 Если у вас есть вопросы, обратитесь в поддержку: @support", 
         "common", "contact_support"),
        
        ("thank_you", "Благодарность", 
         "🙏 Спасибо за ваш заказ! Мы создадим для вас что-то особенное.", 
         "common", "thank_you"),
        
        ("feedback_request", "Запрос отзыва", 
         "💭 Как вам результат? Оставьте отзыв о нашей работе!", 
         "common", "feedback_request"),
        
        ("recommendation_request", "Запрос рекомендации", 
         "🌟 Понравился результат? Порекомендуйте нас друзьям!", 
         "common", "recommendation_request"),
        
        # === ВЫБОР ПОЛА ===
        ("gender_request", "Запрос выбора пола", 
         "Замечательный выбор ✨\nМы позаботимся о том, чтобы твоя книга получилась душевной и бережно сохранила все важные воспоминания.\n\nОтветь на несколько вопросов и мы начнём собирать твою историю 📖\n\n👤 Выбери свой пол:", 
         "gender", "selection"),
    ]
    
    for message_key, message_name, content, context, stage in auto_messages:
        await upsert_bot_message(message_key, message_name, content, context, stage) 
async def get_order_other_heroes(order_id: int) -> List[Dict]:
    """Получает фотографии других героев для заказа из hero_photos таблицы и order_data"""
    async with aiosqlite.connect(DB_PATH) as db:
        heroes = {}
        
        # Сначала получаем фотографии из таблицы hero_photos
        print(f"🔍 ОТЛАДКА: Получаем фотографии героев для заказа {order_id} из таблицы hero_photos")
        async with db.execute('''
            SELECT filename, photo_type, hero_name, created_at
            FROM hero_photos
            WHERE order_id = ?
            ORDER BY created_at ASC
        ''', (order_id,)) as cursor:
            hero_photo_rows = await cursor.fetchall()
            print(f"🔍 ОТЛАДКА: Найдено {len(hero_photo_rows)} фотографий героев")
            
            for filename, photo_type, hero_name, created_at in hero_photo_rows:
                # Исправляем имя героя, заменяя обратный слеш на прямой
                clean_hero_name = hero_name.replace('\\', '/') if hero_name else ''
                
                if clean_hero_name not in heroes:
                    heroes[clean_hero_name] = {
                        'id': len(heroes) + 1,
                        'hero_name': clean_hero_name,
                        'hero_intro': '',
                        'face_1': '',
                        'face_2': '',
                        'full': '',
                        'created_at': created_at
                    }
                
                # Исправляем имя файла, заменяя обратный слеш на прямой
                clean_filename = filename.replace('\\', '/') if filename else ''
                
                # Кодируем filename для URL
                from urllib.parse import quote
                encoded_filename = quote(clean_filename)
                
                # Устанавливаем фотографию в соответствующее поле
                if photo_type == 'face_1':
                    heroes[clean_hero_name]['face_1'] = f"uploads/{encoded_filename}"
                elif photo_type == 'face_2':
                    heroes[clean_hero_name]['face_2'] = f"uploads/{encoded_filename}"
                elif photo_type == 'full':
                    heroes[clean_hero_name]['full'] = f"uploads/{encoded_filename}"
        
        # Теперь дополняем информацией из order_data (для получения intro)
        async with db.execute('SELECT order_data FROM orders WHERE id = ?', (order_id,)) as cursor:
            row = await cursor.fetchone()
            
            if row and row[0]:
                try:
                    order_data = json.loads(row[0])
                    other_heroes = order_data.get('other_heroes', [])
                    print(f"🔍 ОТЛАДКА: Найдено {len(other_heroes)} героев в order_data")
                    
                    # Дополняем информацию о героях из order_data
                    for hero in other_heroes:
                        hero_name = hero.get('name', '')
                        hero_intro = hero.get('intro', '')
                        
                        # Исправляем имя героя, заменяя обратный слеш на прямой
                        clean_hero_name = hero_name.replace('\\', '/') if hero_name else ''
                        
                        if clean_hero_name in heroes:
                            heroes[clean_hero_name]['hero_intro'] = hero_intro
                        elif hero_intro:  # Если есть описание, но нет фотографий
                            heroes[clean_hero_name] = {
                                'id': len(heroes) + 1,
                                'hero_name': clean_hero_name,
                                'hero_intro': hero_intro,
                                'face_1': '',
                                'face_2': '',
                                'full': '',
                                'created_at': ''
                            }
                            
                except json.JSONDecodeError:
                    print(f"❌ Ошибка парсинга order_data для заказа {order_id}")
        
        result = list(heroes.values())
        print(f"✅ Итого найдено {len(result)} героев для заказа {order_id}")
        print(f"🔍 ОТЛАДКА: Результат для заказа {order_id}: {result}")
        return result



async def assign_manager_to_order(order_id: int) -> bool:
    """Автоматически назначает менеджера к заказу по принципу round-robin, исключая супер-админов"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем следующего менеджера в очереди
        selected_manager_id = await get_next_manager_in_queue()
        
        if not selected_manager_id:
            return False
        
        # Назначаем менеджера к заказу
        await db.execute('''
            UPDATE orders
            SET assigned_manager_id = ?
            WHERE id = ?
        ''', (selected_manager_id, order_id))
        
        await db.commit()
        return True

async def assign_managers_to_all_orders() -> dict:
    """Назначает менеджеров ко всем заказам, которые их не имеют"""
    print("🔍 ОТЛАДКА: assign_managers_to_all_orders() вызвана")
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем заказы без назначенных менеджеров
        async with db.execute('''
            SELECT id FROM orders WHERE assigned_manager_id IS NULL
        ''') as cursor:
            unassigned_orders = await cursor.fetchall()
        
        if not unassigned_orders:
            return {"success": True, "message": "Все заказы уже имеют назначенных менеджеров", "assigned_count": 0}
        
        print(f"🔍 ОТЛАДКА: Найдено заказов без менеджеров: {len(unassigned_orders)}")
        
        # Проверяем доступных менеджеров
        async with db.execute('''
            SELECT id, email, is_super_admin FROM managers ORDER BY id
        ''') as cursor:
            managers = await cursor.fetchall()
        
        print(f"🔍 ОТЛАДКА: Доступных менеджеров: {len(managers)}")
        for manager in managers:
            print(f"   ID: {manager[0]}, Email: {manager[1]}, Супер-админ: {manager[2]}")
        
        success_count = 0
        for (order_id,) in unassigned_orders:
            try:
                print(f"🔍 ОТЛАДКА: Назначаем менеджера к заказу {order_id}")
                success = await assign_manager_to_order(order_id)
                if success:
                    success_count += 1
                    print(f"   ✅ Менеджер назначен к заказу {order_id}")
                else:
                    print(f"   ❌ Не удалось назначить менеджера к заказу {order_id}")
            except Exception as e:
                print(f"   ❌ Ошибка назначения менеджера к заказу {order_id}: {e}")
        
        print(f"🔍 ОТЛАДКА: Итого назначено: {success_count}/{len(unassigned_orders)}")
        
        return {
            "success": True, 
            "message": f"Назначено менеджеров к {success_count} заказам из {len(unassigned_orders)}", 
            "assigned_count": success_count,
            "total_unassigned": len(unassigned_orders)
        }

async def get_next_page_number(order_id: int) -> int:
    """Получает следующий номер страницы для заказа из базы данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT MAX(page_number) as max_page FROM order_pages 
            WHERE order_id = ?
        ''', (order_id,)) as cursor:
            row = await cursor.fetchone()
            print(f"🔍 ОТЛАДКА: get_next_page_number для заказа {order_id}: row={row}")
            if row and row['max_page'] is not None:
                next_num = row['max_page'] + 1
                print(f"🔍 ОТЛАДКА: Максимальный номер страницы: {row['max_page']}, следующий: {next_num}")
                return next_num
            print(f"🔍 ОТЛАДКА: Нет страниц в БД, возвращаем 1")
            return 1

async def save_page_number(order_id: int, page_number: int, filename: str, description: str):
    """Сохраняет информацию о странице в базу данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        print(f"🔍 ОТЛАДКА: save_page_number: order_id={order_id}, page_number={page_number}, filename={filename}")
        await db.execute('''
            INSERT INTO order_pages (order_id, page_number, filename, description, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (order_id, page_number, filename, description))
        await db.commit()
        print(f"🔍 ОТЛАДКА: Страница {page_number} успешно сохранена в БД")
async def get_order_pages(order_id: int) -> List[Dict]:
    """Получает все страницы для заказа"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Сначала проверяем, существует ли заказ
        cursor = await db.execute('''
            SELECT id FROM orders WHERE id = ?
        ''', (order_id,))
        order_exists = await cursor.fetchone()
        
        if not order_exists:
            print(f"🔍 ОТЛАДКА: Заказ {order_id} не существует, страницы не найдены")
            return []
        
        # Если заказ существует, ищем страницы
        async with db.execute('''
            SELECT page_number, filename, description, created_at
            FROM order_pages 
            WHERE order_id = ?
            ORDER BY page_number ASC
        ''', (order_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def get_order_demo_content(order_id: int) -> List[Dict]:
    """Получает файлы демо-контента для заказа"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT id, filename, file_type, uploaded_at
            FROM uploads 
            WHERE order_id = ? AND file_type IN ('demo_photo', 'demo_audio', 'demo_video', 'demo_pdf')
            ORDER BY uploaded_at DESC
        ''', (order_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def update_order_email(order_id: int, email: str) -> bool:
    """Обновляет email в заказе"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            UPDATE orders
            SET email = ?
            WHERE id = ?
        ''', (email, order_id))
        await db.commit()
        return cursor.rowcount > 0

async def add_upload(order_id: int, filename: str, file_type: str) -> bool:
    """Добавляет информацию о загруженном файле в базу данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO uploads (order_id, filename, file_type, uploaded_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (order_id, filename, file_type))
        await db.commit()
        return True

async def update_order_field(order_id: int, field_name: str, value: str) -> bool:
    """Обновляет поле в заказе"""
    print(f"🔍 ОТЛАДКА update_order_field: order_id={order_id}, field_name={field_name}, value={value}")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f'''
            UPDATE orders 
            SET {field_name} = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (value, order_id))
        await db.commit()
        print(f"✅ Поле {field_name} успешно обновлено для заказа {order_id}")
        return True

async def check_pages_sent_before(order_id: int) -> bool:
    """Проверяет, отправлялись ли уже страницы для этого заказа"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT id FROM outbox 
            WHERE order_id = ? AND type_ = 'page_selection' 
            LIMIT 1
        ''', (order_id,)) as cursor:
            row = await cursor.fetchone()
            return row is not None

async def check_demo_content_sent_before(order_id: int) -> bool:
    """Проверяет, отправлялся ли уже демо-контент для этого заказа"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT id FROM outbox 
            WHERE order_id = ? AND type = 'multiple_images_with_text_and_button' 
            LIMIT 1
        ''', (order_id,)) as cursor:
            row = await cursor.fetchone()
            return row is not None

# --- Функции трекинга метрик событий ---

async def track_event(
    user_id: int,
    event_type: str,
    event_data: dict = None,
    step_name: str = None,
    product_type: str = None,
    order_id: int = None,
    amount: float = None,
    source: str = None,
    utm_source: str = None,
    utm_medium: str = None,
    utm_campaign: str = None
) -> bool:
    """
    Записывает событие в таблицу метрик
    
    Типы событий:
    - 'bot_entry' - вход в бота
    - 'start_clicked' - нажатие кнопки старт
    - 'product_selected' - выбор книги/песни
    - 'step_abandoned' - отвал на шаге
    - 'order_created' - создание заказа
    - 'purchase_completed' - завершение покупки
    - 'upsell_purchased' - дополнительная покупка
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Проверяем, не было ли уже записано такое событие в последние 5 минут
            # Это предотвращает дублирование событий
            async with db.execute('''
                SELECT COUNT(*) FROM event_metrics 
                WHERE user_id = ? AND event_type = ? 
                AND timestamp > datetime('now', '-5 minutes')
                AND (order_id = ? OR (order_id IS NULL AND ? IS NULL))
            ''', (user_id, event_type, order_id, order_id)) as cursor:
                recent_count = await cursor.fetchone()
                if recent_count and recent_count[0] > 0:
                    print(f"⚠️ Событие {event_type} для пользователя {user_id} уже записано недавно, пропускаем")
                    return True
            
            await db.execute('''
                INSERT INTO event_metrics 
                (user_id, event_type, event_data, step_name, product_type, order_id, amount, source, utm_source, utm_medium, utm_campaign, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (
                user_id,
                event_type,
                json.dumps(event_data) if event_data else None,
                step_name,
                product_type,
                order_id,
                amount,
                source,
                utm_source,
                utm_medium,
                utm_campaign
            ))
            await db.commit()
            print(f"✅ Записано событие {event_type} для пользователя {user_id}")
            return True
    except Exception as e:
        print(f"❌ Ошибка записи события {event_type} для пользователя {user_id}: {e}")
        return False

async def get_order_source(order_id: int) -> str:
    """Получает источник заказа из таблицы event_metrics"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # Ищем источник в событиях для этого заказа
            async with db.execute('''
                SELECT source 
                FROM event_metrics 
                WHERE order_id = ? AND source IS NOT NULL AND source != ''
                ORDER BY timestamp ASC
                LIMIT 1
            ''', (order_id,)) as cursor:
                row = await cursor.fetchone()
                if row and row['source']:
                    return row['source']
            
            # Если не найден по order_id, ищем по user_id из заказа
            async with db.execute('''
                SELECT o.user_id, em.source
                FROM orders o
                JOIN event_metrics em ON o.user_id = em.user_id
                WHERE o.id = ? AND em.source IS NOT NULL AND em.source != ''
                ORDER BY em.timestamp ASC
                LIMIT 1
            ''', (order_id,)) as cursor:
                row = await cursor.fetchone()
                if row and row['source']:
                    return row['source']
            
            return 'Неизвестно'
    except Exception as e:
        print(f"❌ Ошибка получения источника для заказа {order_id}: {e}")
        return 'Неизвестно'

async def get_order_utm_data(order_id: int) -> dict:
    """Получает UTM-данные заказа из таблицы event_metrics"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # Ищем UTM-данные в событиях для этого заказа
            async with db.execute('''
                SELECT utm_source, utm_medium, utm_campaign 
                FROM event_metrics 
                WHERE order_id = ? AND (utm_source IS NOT NULL OR utm_medium IS NOT NULL OR utm_campaign IS NOT NULL)
                ORDER BY timestamp ASC
                LIMIT 1
            ''', (order_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        'utm_source': row['utm_source'] or 'Неизвестно',
                        'utm_medium': row['utm_medium'] or 'Неизвестно',
                        'utm_campaign': row['utm_campaign'] or 'Неизвестно'
                    }
            
            # Если не найден по order_id, ищем по user_id только события ДО создания заказа
            async with db.execute('''
                SELECT o.user_id, o.created_at, em.utm_source, em.utm_medium, em.utm_campaign
                FROM orders o
                JOIN event_metrics em ON o.user_id = em.user_id
                WHERE o.id = ? AND (em.utm_source IS NOT NULL OR em.utm_medium IS NOT NULL OR em.utm_campaign IS NOT NULL)
                AND em.timestamp <= o.created_at
                ORDER BY em.timestamp DESC
                LIMIT 1
            ''', (order_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        'utm_source': row['utm_source'] or 'Неизвестно',
                        'utm_medium': row['utm_medium'] or 'Неизвестно',
                        'utm_campaign': row['utm_campaign'] or 'Неизвестно'
                    }
            
            return {
                'utm_source': 'Неизвестно',
                'utm_medium': 'Неизвестно',
                'utm_campaign': 'Неизвестно'
            }
    except Exception as e:
        print(f"❌ Ошибка получения UTM-данных заказа {order_id}: {e}")
        return {
            'utm_source': 'Неизвестно',
            'utm_medium': 'Неизвестно',
            'utm_campaign': 'Неизвестно'
        }

async def get_event_metrics(
    start_date: str = None,
    end_date: str = None,
    event_type: str = None,
    user_id: int = None
) -> List[Dict]:
    """Получает метрики событий с фильтрацией"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            query = "SELECT * FROM event_metrics WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND DATE(timestamp) >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND DATE(timestamp) <= ?"
                params.append(end_date)
            
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            query += " ORDER BY timestamp DESC"
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]
    except Exception as e:
        print(f"❌ Ошибка получения метрик событий: {e}")
        return []

async def get_funnel_metrics(start_date: str, end_date: str) -> Dict:
    """Получает метрики воронки конверсии"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Уникальные пользователи по событиям
            events = [
                'bot_entry',
                'start_clicked', 
                'product_selected',
                'order_created',
                'purchase_completed'
            ]
            
            funnel_data = {}
            
            for event in events:
                # Получаем уникальных пользователей
                async with db.execute('''
                    SELECT COUNT(DISTINCT user_id) as unique_users
                    FROM event_metrics 
                    WHERE event_type = ? 
                    AND DATE(timestamp) BETWEEN ? AND ?
                ''', (event, start_date, end_date)) as cursor:
                    result = await cursor.fetchone()
                    unique_users = result[0] if result else 0
                
                # Получаем общее количество нажатий
                async with db.execute('''
                    SELECT COUNT(*) as total_clicks
                    FROM event_metrics 
                    WHERE event_type = ? 
                    AND DATE(timestamp) BETWEEN ? AND ?
                ''', (event, start_date, end_date)) as cursor:
                    result = await cursor.fetchone()
                    total_clicks = result[0] if result else 0
                
                # Для всех событий показываем уникальных пользователей по user_id
                funnel_data[event] = {
                    'unique_users': unique_users,  # Всегда показываем уникальных пользователей по user_id
                    'total_clicks': total_clicks
                }
            
            # Корректировка: уникальные входы в бота не должны быть меньше, чем нажатия Старт
            # Пользователь мог зайти в бот до периода, а нажать Старт в периоде.
            # Считаем объединение пользователей по событиям bot_entry и start_clicked за период.
            async with db.execute('''
                SELECT COUNT(DISTINCT user_id) as union_users
                FROM event_metrics
                WHERE event_type IN ('bot_entry', 'start_clicked')
                AND DATE(timestamp) BETWEEN ? AND ?
            ''', (start_date, end_date)) as cursor:
                result = await cursor.fetchone()
                union_users = result[0] if result else 0
                if union_users > funnel_data['bot_entry']['unique_users']:
                    funnel_data['bot_entry']['unique_users'] = union_users
            
            # Получаем раздельные метрики для демо песни и книги
            # НОВАЯ ЛОГИКА: считаем демо пройденным, когда пользователь нажал "Узнать цену" после демо
            
            # Демо песни - пользователи, которые нажали "Узнать цену" после демо песни
            async with db.execute('''
                SELECT COUNT(DISTINCT user_id) as song_demo_users
                FROM event_metrics 
                WHERE event_type = 'song_demo_learn_price_clicked'
                AND DATE(timestamp) BETWEEN ? AND ?
            ''', (start_date, end_date)) as cursor:
                result = await cursor.fetchone()
                song_demo_users = result[0] if result else 0
            
            # Демо книги - пользователи, которые нажали "Узнать цену" после демо книги
            async with db.execute('''
                SELECT COUNT(DISTINCT user_id) as book_demo_users
                FROM event_metrics 
                WHERE event_type = 'demo_learn_price_clicked'
                AND DATE(timestamp) BETWEEN ? AND ?
            ''', (start_date, end_date)) as cursor:
                result = await cursor.fetchone()
                book_demo_users = result[0] if result else 0
            
            # Если нет событий order_created, используем данные из заказов
            if funnel_data['order_created']['unique_users'] == 0:
                # Получаем количество уникальных пользователей и общее количество заказов
                async with db.execute('''
                    SELECT COUNT(DISTINCT user_id) as unique_users, COUNT(*) as total_orders
                    FROM orders 
                    WHERE DATE(created_at) BETWEEN ? AND ?
                ''', (start_date, end_date)) as cursor:
                    result = await cursor.fetchone()
                    unique_users = result[0] if result else 0
                    total_orders = result[1] if result else 0
                    funnel_data['order_created'] = {
                        'unique_users': unique_users,  # Показываем уникальных пользователей
                        'total_clicks': total_orders
                    }
            
            # Если нет событий purchase_completed, используем данные из заказов
            if funnel_data['purchase_completed']['unique_users'] == 0:
                # Получаем количество уникальных пользователей и общее количество оплаченных заказов
                status_placeholders = ','.join(['?' for _ in PAID_ORDER_STATUSES])
                async with db.execute(f'''
                    SELECT COUNT(DISTINCT user_id) as unique_users, COUNT(*) as paid_orders
                    FROM orders 
                    WHERE status IN ({status_placeholders})
                    AND DATE(created_at) BETWEEN ? AND ?
                ''', (*PAID_ORDER_STATUSES, start_date, end_date)) as cursor:
                    result = await cursor.fetchone()
                    unique_users = result[0] if result else 0
                    paid_orders = result[1] if result else 0
                    funnel_data['purchase_completed'] = {
                        'unique_users': unique_users,  # Показываем уникальных пользователей
                        'total_clicks': paid_orders
                    }
            
            # Получаем метрики апсейла для "Перешло во второй заказ"
            # Считаем все события purchase_completed, но исключаем доплаты за печатную версию
            # Фильтруем нулевые суммы и события без order_id
            async with db.execute('''
                SELECT COUNT(DISTINCT user_id) as unique_users, COUNT(DISTINCT order_id) as total_clicks
                FROM event_metrics 
                WHERE event_type = 'purchase_completed'
                AND (event_data NOT LIKE '%"upsell_type": "print"%' OR event_data IS NULL)
                AND DATE(timestamp) BETWEEN ? AND ?
                AND amount IS NOT NULL 
                AND amount > 0
                AND order_id IS NOT NULL
            ''', (start_date, end_date)) as cursor:
                result = await cursor.fetchone()
                upsell_unique_users = result[0] if result else 0
                upsell_total_clicks = result[1] if result else 0
            
            # Добавляем метрику апсейла в funnel_data
            funnel_data['upsell_clicked'] = {
                'unique_users': upsell_unique_users,
                'total_clicks': upsell_total_clicks
            }
            
            # Вычисляем конверсии
            conversions = {}
            if funnel_data['bot_entry']['unique_users'] > 0:
                conversions['start_rate'] = funnel_data['start_clicked']['unique_users'] / funnel_data['bot_entry']['unique_users']
                conversions['product_selection_rate'] = funnel_data['product_selected']['unique_users'] / funnel_data['bot_entry']['unique_users']
                conversions['order_creation_rate'] = funnel_data['order_created']['unique_users'] / funnel_data['bot_entry']['unique_users']
                conversions['purchase_rate'] = funnel_data['purchase_completed']['unique_users'] / funnel_data['bot_entry']['unique_users']
            
            return {
                'funnel_data': funnel_data,
                'conversions': conversions,
                'song_demo_users': song_demo_users,
                'book_demo_users': book_demo_users
            }
    except Exception as e:
        print(f"❌ Ошибка получения метрик воронки: {e}")
        return {'funnel_data': {}, 'conversions': {}, 'song_demo_users': 0, 'book_demo_users': 0}
async def get_abandonment_metrics(start_date: str, end_date: str) -> Dict:
    """Получает метрики отвалов по шагам на основе реальных статусов заказов
    
    Считает количество ЗАКАЗОВ (не уникальных пользователей) на каждом этапе.
    Это позволяет корректно отображать метрики, когда у одного пользователя несколько заказов.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # Глава 1: Создание заказа (product_selection)
            # Прошло шаг = все созданные заказы
            async with db.execute('''
                SELECT COUNT(*) as total_orders
                FROM orders
                WHERE DATE(created_at) BETWEEN ? AND ?
            ''', (start_date, end_date)) as cursor:
                row = await cursor.fetchone()
                product_selection_total = row[0] if row else 0
            
            # Отвалились = заказы, которые остались на начальных статусах
            async with db.execute('''
                SELECT COUNT(*) as abandoned_orders
                FROM orders
                WHERE status IN ('created', 'product_selected', 'gender_selected', 'relation_selected', 'collecting_facts')
                AND DATE(created_at) BETWEEN ? AND ?
            ''', (start_date, end_date)) as cursor:
                row = await cursor.fetchone()
                product_selection_abandoned = row[0] if row else 0
            
            # Глава 2: Демо-версия ПЕСНИ (demo_sent)
            # Прошло шаг = заказы песни, достигшие demo_sent или дальше (включая ВСЕ статусы после демо)
            async with db.execute('''
                SELECT COUNT(*) as total_orders
                FROM orders
                WHERE JSON_EXTRACT(order_data, '$.product') = 'Песня'
                AND status IN ('demo_sent', 'demo_content', 'waiting_payment', 'payment_created', 'payment_pending',
                               'paid', 'upsell_paid', 'upsell_payment_created', 'upsell_payment_pending', 'additional_payment_paid',
                               'collecting_facts', 'waiting_plot_options', 'plot_selected', 'waiting_final_version',
                               'waiting_draft', 'draft_sent', 'editing', 'waiting_feedback', 'feedback_processed',
                               'prefinal_sent', 'waiting_final', 'final_sent', 'ready', 'delivered', 'completed')
                AND DATE(created_at) BETWEEN ? AND ?
            ''', (start_date, end_date)) as cursor:
                row = await cursor.fetchone()
                demo_sent_song_total = row[0] if row else 0
            
            # Отвалились = заказы песни в статусе demo_sent или demo_content, которые НЕ оплачены
            async with db.execute('''
                SELECT COUNT(*) as abandoned_orders
                FROM orders
                WHERE JSON_EXTRACT(order_data, '$.product') = 'Песня'
                AND status IN ('demo_sent', 'demo_content')
                AND DATE(created_at) BETWEEN ? AND ?
            ''', (start_date, end_date)) as cursor:
                row = await cursor.fetchone()
                demo_sent_song_abandoned = row[0] if row else 0
            
            # Глава 2: Демо-версия КНИГИ (demo_sent_book)
            # Прошло шаг = заказы книги, достигшие demo_sent или дальше (включая ВСЕ статусы после демо)
            async with db.execute('''
                SELECT COUNT(*) as total_orders
                FROM orders
                WHERE JSON_EXTRACT(order_data, '$.product') = 'Книга'
                AND status IN ('demo_sent', 'demo_content', 'answering_questions', 'questions_completed', 
                               'waiting_payment', 'payment_created', 'payment_pending', 'paid', 'upsell_paid',
                               'story_selection', 'waiting_story_options', 'waiting_story_choice', 'story_selected', 'story_options_sent',
                               'pages_selected', 'covers_sent', 'waiting_cover_choice', 'cover_selected',
                               'waiting_draft', 'draft_sent', 'editing', 'waiting_feedback', 'feedback_processed',
                               'prefinal_sent', 'waiting_final', 'final_sent',
                               'waiting_delivery', 'print_delivery_pending', 'ready', 'delivered', 'completed',
                               'upsell_payment_created', 'upsell_payment_pending', 'additional_payment_paid')
                AND DATE(created_at) BETWEEN ? AND ?
            ''', (start_date, end_date)) as cursor:
                row = await cursor.fetchone()
                demo_sent_book_total = row[0] if row else 0
            
            # Отвалились = заказы книги на этапе демо или вопросов, но НЕ оплатившие
            async with db.execute('''
                SELECT COUNT(*) as abandoned_orders
                FROM orders
                WHERE JSON_EXTRACT(order_data, '$.product') = 'Книга'
                AND status IN ('demo_sent', 'demo_content', 'answering_questions', 'questions_completed')
                AND DATE(created_at) BETWEEN ? AND ?
            ''', (start_date, end_date)) as cursor:
                row = await cursor.fetchone()
                demo_sent_book_abandoned = row[0] if row else 0
            
            # Глава 3: Оплата заказа (payment)
            # Прошло шаг = все заказы, достигшие этапа оплаты (включая статусы ожидания оплаты и все оплаченные)
            # Используем динамический список всех оплаченных статусов + статусы ожидания оплаты
            payment_statuses = ['waiting_payment', 'payment_created', 'payment_pending'] + PAID_ORDER_STATUSES
            status_placeholders = ','.join(['?' for _ in payment_statuses])
            async with db.execute(f'''
                SELECT COUNT(*) as total_orders
                FROM orders
                WHERE status IN ({status_placeholders})
                AND DATE(created_at) BETWEEN ? AND ?
            ''', (*payment_statuses, start_date, end_date)) as cursor:
                row = await cursor.fetchone()
                payment_total = row[0] if row else 0
            
            # Отвалились = заказы в ожидании оплаты (НЕ оплачены)
            async with db.execute('''
                SELECT COUNT(*) as abandoned_orders
                FROM orders
                WHERE status IN ('waiting_payment', 'payment_created', 'payment_pending')
                AND DATE(created_at) BETWEEN ? AND ?
            ''', (start_date, end_date)) as cursor:
                row = await cursor.fetchone()
                payment_abandoned = row[0] if row else 0
            
            # Глава 4: Предфинальная версия (prefinal_sent)
            # Прошло шаг = оплаченные заказы (используем все статусы из PAID_ORDER_STATUSES)
            status_placeholders_paid = ','.join(['?' for _ in PAID_ORDER_STATUSES])
            async with db.execute(f'''
                SELECT COUNT(*) as total_orders
                FROM orders
                WHERE status IN ({status_placeholders_paid})
                AND DATE(created_at) BETWEEN ? AND ?
            ''', (*PAID_ORDER_STATUSES, start_date, end_date)) as cursor:
                row = await cursor.fetchone()
                prefinal_total = row[0] if row else 0
            
            # Отвалились = оплаченные заказы, не достигшие prefinal_sent
            # Это заказы в начальных статусах после оплаты
            async with db.execute('''
                SELECT COUNT(*) as abandoned_orders
                FROM orders
                WHERE status IN ('paid', 'upsell_paid', 'story_selection', 'waiting_story_options', 
                                 'waiting_story_choice', 'story_selected', 'story_options_sent',
                                 'waiting_draft', 'draft_sent', 'collecting_facts', 
                                 'waiting_plot_options', 'plot_selected')
                AND DATE(created_at) BETWEEN ? AND ?
            ''', (start_date, end_date)) as cursor:
                row = await cursor.fetchone()
                prefinal_abandoned = row[0] if row else 0
            
            # Глава 5: Правки и доработки (editing)
            # Прошло шаг = заказы, достигшие prefinal_sent или дальше (включая все промежуточные статусы)
            async with db.execute('''
                SELECT COUNT(*) as total_orders
                FROM orders
                WHERE status IN ('prefinal_sent', 'editing', 'waiting_feedback', 'feedback_processed',
                                 'waiting_final', 'final_sent', 'waiting_delivery', 'print_delivery_pending',
                                 'ready', 'delivered', 'completed')
                AND DATE(created_at) BETWEEN ? AND ?
            ''', (start_date, end_date)) as cursor:
                row = await cursor.fetchone()
                editing_total = row[0] if row else 0
            
            # Отвалились = заказы в статусах prefinal_sent, editing и промежуточных (не завершенные)
            async with db.execute('''
                SELECT COUNT(*) as abandoned_orders
                FROM orders
                WHERE status IN ('prefinal_sent', 'editing', 'waiting_feedback', 'feedback_processed',
                                 'waiting_final', 'final_sent', 'waiting_delivery', 'print_delivery_pending')
                AND DATE(created_at) BETWEEN ? AND ?
            ''', (start_date, end_date)) as cursor:
                row = await cursor.fetchone()
                editing_abandoned = row[0] if row else 0
            
            # Глава 6: Завершение проекта (completed)
            # Прошло шаг = заказы в финальных статусах (включая waiting_delivery и print_delivery_pending)
            async with db.execute('''
                SELECT COUNT(*) as total_orders
                FROM orders
                WHERE status IN ('ready', 'waiting_delivery', 'print_delivery_pending', 'delivered', 'completed')
                AND DATE(created_at) BETWEEN ? AND ?
            ''', (start_date, end_date)) as cursor:
                row = await cursor.fetchone()
                completed_total = row[0] if row else 0
            
            # Отвалились = заказы готовые, но не завершенные (включая промежуточные статусы доставки)
            async with db.execute('''
                SELECT COUNT(*) as abandoned_orders
                FROM orders
                WHERE status IN ('ready', 'waiting_delivery', 'print_delivery_pending', 'delivered')
                AND DATE(created_at) BETWEEN ? AND ?
            ''', (start_date, end_date)) as cursor:
                row = await cursor.fetchone()
                completed_abandoned = row[0] if row else 0
            
            abandonment_data = [
                {
                    'step_name': 'product_selection',
                    'abandonment_count': product_selection_abandoned,
                    'unique_users': product_selection_total
                },
                {
                    'step_name': 'demo_sent',
                    'abandonment_count': demo_sent_song_abandoned,
                    'unique_users': demo_sent_song_total
                },
                {
                    'step_name': 'demo_sent_book',
                    'abandonment_count': demo_sent_book_abandoned,
                    'unique_users': demo_sent_book_total
                },
                {
                    'step_name': 'payment',
                    'abandonment_count': payment_abandoned,
                    'unique_users': payment_total
                },
                {
                    'step_name': 'prefinal_sent',
                    'abandonment_count': prefinal_abandoned,
                    'unique_users': prefinal_total
                },
                {
                    'step_name': 'editing',
                    'abandonment_count': editing_abandoned,
                    'unique_users': editing_total
                },
                {
                    'step_name': 'completed',
                    'abandonment_count': completed_abandoned,
                    'unique_users': completed_total
                }
            ]
            
            return abandonment_data
    except Exception as e:
        print(f"❌ Ошибка получения метрик отвалов: {e}")
        import traceback
        traceback.print_exc()
        return []

async def get_revenue_metrics(start_date: str, end_date: str) -> Dict:
    """Получает метрики выручки"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Количество основных покупок считаем ПО СТАТУСАМ (как в аналитике)
            # Это убирает расхождения, когда событие purchase_completed отсутствует, а статус уже оплачен
            status_placeholders = ','.join(['?' for _ in PAID_ORDER_STATUSES])
            async with db.execute(f'''
                SELECT 
                    COUNT(*) as purchase_count
                FROM orders 
                WHERE status IN ({status_placeholders})
                AND DATE(created_at) BETWEEN ? AND ?
            ''', (*PAID_ORDER_STATUSES, start_date, end_date)) as cursor:
                status_count_row = await cursor.fetchone()
                purchases_count_by_status = status_count_row[0] if status_count_row else 0
            
            # Основная выручка из событий
            async with db.execute('''
                SELECT 
                    COALESCE(SUM(amount), 0) as total_revenue
                FROM event_metrics 
                WHERE event_type = 'purchase_completed'
                AND DATE(timestamp) BETWEEN ? AND ?
                AND amount IS NOT NULL
                AND amount > 0
                AND order_id IS NOT NULL
            ''', (start_date, end_date)) as cursor:
                main_revenue_row = await cursor.fetchone()
                main_revenue_sum = float(main_revenue_row[0]) if main_revenue_row and main_revenue_row[0] is not None else 0.0
            
            # Если нет данных в событиях, берем из заказов
            if main_revenue_sum == 0:
                async with db.execute('''
                    SELECT 
                        COALESCE(SUM(total_amount), 0) as total_revenue
                    FROM orders 
                    WHERE status IN ({status_placeholders})
                    AND DATE(created_at) BETWEEN ? AND ?
                    AND total_amount IS NOT NULL AND total_amount > 0
                ''', (*PAID_ORDER_STATUSES, start_date, end_date)) as cursor:
                    row = await cursor.fetchone()
                    main_revenue_sum = float(row[0]) if row and row[0] is not None else 0.0
            
            # Дополнительные покупки из событий
            # Считаем уникальные order_id, исключаем нулевые суммы
            async with db.execute('''
                SELECT 
                    COUNT(DISTINCT order_id) as upsell_count,
                    SUM(amount) as upsell_revenue
                FROM event_metrics 
                WHERE event_type = 'upsell_purchased'
                AND DATE(timestamp) BETWEEN ? AND ?
                AND amount IS NOT NULL 
                AND amount > 0
                AND order_id IS NOT NULL
            ''', (start_date, end_date)) as cursor:
                upsells = await cursor.fetchone()
            
            # Если нет данных в событиях, берем из заказов с статусом upsell_paid
            if not upsells or upsells[0] == 0:
                async with db.execute('''
                    SELECT 
                        COUNT(*) as upsell_count,
                        COALESCE(SUM(total_amount), 0) as upsell_revenue
                    FROM orders 
                    WHERE status = 'upsell_paid'
                    AND DATE(created_at) BETWEEN ? AND ?
                    AND total_amount IS NOT NULL AND total_amount > 0
                ''', (start_date, end_date)) as cursor:
                    upsells = await cursor.fetchone()
            
            # Средний чек считаем по количеству покупок (по статусам)
            avg_value = (main_revenue_sum / purchases_count_by_status) if purchases_count_by_status > 0 else 0
            
            return {
                'main_purchases': {
                    'count': purchases_count_by_status,
                    'revenue': main_revenue_sum,
                    'avg_value': avg_value
                },
                'upsells': {
                    'count': upsells[0] if upsells else 0,
                    'revenue': upsells[1] if upsells else 0
                }
            }
    except Exception as e:
        print(f"❌ Ошибка получения метрик выручки: {e}")
        return {'main_purchases': {'count': 0, 'revenue': 0, 'avg_value': 0}, 'upsells': {'count': 0, 'revenue': 0}}

async def get_detailed_revenue_metrics(start_date: str, end_date: str) -> Dict:
    """Получает детализированные метрики выручки по типам продуктов"""
    try:
        import json
        async with aiosqlite.connect(DB_PATH) as db:
            # Сначала получаем суммы из event_metrics для каждого заказа
            # Берем ПЕРВОЕ событие purchase_completed (основную покупку), а не сумму
            async with db.execute('''
                SELECT 
                    order_id,
                    MIN(amount) as initial_purchase_amount,
                    MAX(amount) as max_amount
                FROM event_metrics
                WHERE event_type = 'purchase_completed'
                AND DATE(timestamp) BETWEEN ? AND ?
                AND amount IS NOT NULL
                AND amount > 0
                AND order_id IS NOT NULL
                GROUP BY order_id
            ''', (start_date, end_date)) as cursor:
                events_data = {row[0]: {'initial': row[1], 'max': row[2]} for row in await cursor.fetchall()}
            
            # Проверяем, у каких заказов есть доплаты
            async with db.execute('''
                SELECT DISTINCT order_id
                FROM event_metrics
                WHERE event_type = 'upsell_purchased'
                AND order_id IS NOT NULL
            ''') as cursor:
                upsell_orders = {row[0] for row in await cursor.fetchall()}
            
            # Получаем все заказы с order_data для анализа типов продуктов
            async with db.execute('''
                SELECT 
                    id,
                    order_data,
                    COALESCE(total_amount, 0) as total_amount,
                    status
                FROM orders 
                WHERE order_data IS NOT NULL AND order_data != ""
                AND DATE(created_at) BETWEEN ? AND ?
                AND status NOT IN ('created', 'cancelled', 'refunded')
            ''', (start_date, end_date)) as cursor:
                rows = await cursor.fetchall()
                
            # Инициализируем результат
            result = {
                'Книга (общее)': {'count': 0, 'revenue': 0, 'avg_value': 0},
                'Книга печатная': {'count': 0, 'revenue': 0, 'avg_value': 0},
                'Книга электронная': {'count': 0, 'revenue': 0, 'avg_value': 0},
                'Песня (общее)': {'count': 0, 'revenue': 0, 'avg_value': 0},
                'Песня': {'count': 0, 'revenue': 0, 'avg_value': 0}
            }
            
            # Обрабатываем каждый заказ
            for row in rows:
                order_id, order_data_str, total_amount, status = row
                
                if not order_data_str:
                    continue
                    
                try:
                    order_data = json.loads(order_data_str)
                    product = order_data.get('product', '')
                    book_format = order_data.get('book_format', '')
                    format_field = order_data.get('format', '')
                    
                    # Определяем, является ли заказ оплаченным
                    is_paid = status in PAID_ORDER_STATUSES
                    
                    # Получаем данные из событий
                    event_info = events_data.get(order_id, {})
                    initial_amount = event_info.get('initial', 0)
                    
                    # Используем сумму из event_metrics, если total_amount = 0 или None
                    # Для заказов с доплатой используем начальную сумму (без доплаты)
                    if order_id in upsell_orders:
                        actual_amount = initial_amount
                    else:
                        actual_amount = initial_amount if total_amount == 0 else total_amount
                    
                    # ОТЛАДКА: Проверяем заказ #10
                    if order_id == 10:
                        print(f"🔍 ОТЛАДКА ДЕТАЛЬНЫХ МЕТРИК: Заказ #10 - статус={status}, product={product}, total_amount={total_amount}, actual_amount={actual_amount}, is_paid={is_paid}")
                    
                    # Определяем тип продукта
                    if product == 'Книга':
                        # Учитываем только оплаченные книги в общем количестве
                        if is_paid:
                            result['Книга (общее)']['count'] += 1
                            if actual_amount > 0:
                                result['Книга (общее)']['revenue'] += actual_amount
                        
                        # ОТЛАДКА: Выводим данные о формате книги
                        if is_paid and actual_amount > 0:
                            print(f"🔍 ОТЛАДКА КНИГИ: Заказ #{order_id} - book_format='{book_format}', format='{format_field}', actual_amount={actual_amount}, is_upsell={order_id in upsell_orders}")
                        
                        # Определяем тип книги
                        # Для заказов с доплатой определяем по начальной сумме
                        if order_id in upsell_orders:
                            # Если начальная сумма < 3000, то была электронная книга
                            is_electronic = initial_amount < 3000
                        else:
                            # Для обычных заказов проверяем формат в order_data
                            is_electronic = (
                                book_format == 'Электронная книга' or 
                                format_field == '📄 Электронная книга' or
                                'Электронная' in str(book_format) or
                                'Электронная' in str(format_field)
                            )
                        
                        # ОТЛАДКА: Выводим результат определения типа
                        if is_paid and actual_amount > 0:
                            print(f"🔍 ОТЛАДКА КНИГИ: Заказ #{order_id} - is_electronic={is_electronic}, initial_amount={initial_amount}")
                        
                        # Разделяем на печатные и электронные только для оплаченных заказов
                        if is_paid:
                            if is_electronic:
                                result['Книга электронная']['count'] += 1
                                if actual_amount > 0:
                                    result['Книга электронная']['revenue'] += actual_amount
                            else:
                                # По умолчанию считаем печатной книгой
                                result['Книга печатная']['count'] += 1
                                if actual_amount > 0:
                                    result['Книга печатная']['revenue'] += actual_amount
                    elif product == 'Песня':
                        # Общее количество песен (все статусы, кроме создан/отменён/refund)
                        result['Песня (общее)']['count'] += 1
                        # Оплаченные песни
                        if is_paid:
                            result['Песня']['count'] += 1
                            if actual_amount > 0:
                                result['Песня']['revenue'] += actual_amount
                        
                except json.JSONDecodeError:
                    print(f"❌ Ошибка парсинга order_data для заказа {order_id}")
                    continue
            
            # Рассчитываем средние значения
            for product_type in result:
                if result[product_type]['count'] > 0:
                    result[product_type]['avg_value'] = result[product_type]['revenue'] / result[product_type]['count']
            
            return result
    except Exception as e:
        print(f"❌ Ошибка получения детализированных метрик выручки: {e}")
        return {
            'Книга (общее)': {'count': 0, 'revenue': 0, 'avg_value': 0},
            'Книга печатная': {'count': 0, 'revenue': 0, 'avg_value': 0},
            'Книга электронная': {'count': 0, 'revenue': 0, 'avg_value': 0},
            'Песня (общее)': {'count': 0, 'revenue': 0, 'avg_value': 0},
            'Песня': {'count': 0, 'revenue': 0, 'avg_value': 0}
        }

async def get_orders_count_with_permissions(manager_email: str, status: Optional[str] = None) -> int:
    """Получает общее количество заказов с учетом прав доступа менеджера"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, является ли менеджер главным админом
        is_admin = await is_super_admin(manager_email)
        
        if is_admin:
            # Главный админ видит все заказы
            if status:
                query = '''
                    SELECT COUNT(*) as count
                    FROM orders o 
                    WHERE o.status = ?
                '''
                args = (status,)
            else:
                query = '''
                    SELECT COUNT(*) as count
                    FROM orders o 
                '''
                args = ()
        else:
            # Обычный менеджер видит только свои заказы
            manager = await get_manager_by_email(manager_email)
            if not manager:
                return 0
            
            if status:
                query = '''
                    SELECT COUNT(*) as count
                    FROM orders o 
                    WHERE o.assigned_manager_id = ? AND o.status = ?
                '''
                args = (manager["id"], status)
            else:
                query = '''
                    SELECT COUNT(*) as count
                    FROM orders o 
                    WHERE o.assigned_manager_id = ?
                '''
                args = (manager["id"],)
        
        async with db.execute(query, args) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

# --- Функции для работы с уведомлениями ---

async def create_or_update_order_notification(order_id: int, manager_id: int = None):
    """Создает или обновляет уведомление для заказа при получении сообщения от пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        await configure_db_connection(db)
        
        # Если manager_id не указан, получаем его из заказа
        if not manager_id:
            async with db.execute('SELECT assigned_manager_id FROM orders WHERE id = ?', (order_id,)) as cursor:
                row = await cursor.fetchone()
                if row and row[0]:
                    manager_id = row[0]
        
        # Проверяем, есть ли уже уведомление для этого заказа
        async with db.execute('SELECT id, is_read FROM order_notifications WHERE order_id = ?', (order_id,)) as cursor:
            existing = await cursor.fetchone()
        
        if existing:
            # Обновляем существующее уведомление - сбрасываем флаг прочитанности
            await db.execute('''
                UPDATE order_notifications 
                SET is_read = 0, last_user_message_at = datetime('now'), updated_at = datetime('now')
                WHERE order_id = ?
            ''', (order_id,))
        else:
            # Создаем новое уведомление
            await db.execute('''
                INSERT INTO order_notifications 
                (order_id, manager_id, is_read, last_user_message_at, created_at, updated_at)
                VALUES (?, ?, 0, datetime('now'), datetime('now'), datetime('now'))
            ''', (order_id, manager_id))
        await db.commit()

async def mark_notification_as_read(order_id: int, manager_id: int = None):
    """Отмечает уведомление как прочитанное"""
    async with aiosqlite.connect(DB_PATH) as db:
        await configure_db_connection(db)
        
        # Просто обновляем уведомление для заказа (независимо от менеджера)
        await db.execute('''
            UPDATE order_notifications 
            SET is_read = 1, updated_at = datetime('now')
            WHERE order_id = ?
        ''', (order_id,))
        
        await db.commit()

async def get_order_notifications(manager_id: int = None) -> List[Dict]:
    """Получает уведомления для менеджера или все уведомления (для супер-админа)"""
    async with aiosqlite.connect(DB_PATH) as db:
        await configure_db_connection(db)
        
        if manager_id:
            # Получаем уведомления только для конкретного менеджера
            async with db.execute('''
                SELECT notif.*, o.id as order_id, o.status, o.created_at as order_created_at,
                       o.assigned_manager_id, m.email as manager_email, m.full_name as manager_name
                FROM order_notifications notif
                JOIN orders o ON notif.order_id = o.id
                LEFT JOIN managers m ON notif.manager_id = m.id
                WHERE notif.manager_id = ? AND notif.is_read = 0
                ORDER BY notif.last_user_message_at DESC
            ''', (manager_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]
        else:
            # Получаем все непрочитанные уведомления (для супер-админа)
            async with db.execute('''
                SELECT notif.*, o.id as order_id, o.status, o.created_at as order_created_at,
                       o.assigned_manager_id, m.email as manager_email, m.full_name as manager_name
                FROM order_notifications notif
                JOIN orders o ON notif.order_id = o.id
                LEFT JOIN managers m ON notif.manager_id = m.id
                WHERE notif.is_read = 0
                ORDER BY notif.last_user_message_at DESC
            ''') as cursor:
                rows = await cursor.fetchall()
                return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def get_notification_by_order_id(order_id: int) -> Dict:
    """Получает уведомление по ID заказа"""
    async with aiosqlite.connect(DB_PATH) as db:
        await configure_db_connection(db)
        
        async with db.execute('''
            SELECT * FROM order_notifications WHERE order_id = ?
        ''', (order_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(zip([column[0] for column in cursor.description], row))
            return None

async def create_notifications_for_all_orders():
    """Создает уведомления для всех заказов"""
    async with aiosqlite.connect(DB_PATH) as db:
        await configure_db_connection(db)
        
        # Находим все заказы
        async with db.execute('''
            SELECT id, assigned_manager_id 
            FROM orders
        ''') as cursor:
            all_orders = await cursor.fetchall()
        
        created_count = 0
        for order_id, manager_id in all_orders:
            # Проверяем, есть ли уже уведомление
            async with db.execute('SELECT id FROM order_notifications WHERE order_id = ?', (order_id,)) as cursor:
                existing = await cursor.fetchone()
            
            if not existing:
                # Создаем уведомление (по умолчанию прочитанное)
                await db.execute('''
                    INSERT INTO order_notifications 
                    (order_id, manager_id, is_read, last_user_message_at, created_at, updated_at)
                    VALUES (?, ?, 1, datetime('now'), datetime('now'), datetime('now'))
                ''', (order_id, manager_id))
                created_count += 1
        
        await db.commit()
        return created_count

async def get_order_notifications_v2(manager_id: int = None) -> List[Dict]:
    """Получает уведомления для менеджера или все уведомления (для супер-админа)"""
    async with aiosqlite.connect(DB_PATH) as db:
        await configure_db_connection(db)
        
        if manager_id:
            # Получаем уведомления только для конкретного менеджера
            async with db.execute('''
                SELECT notif.*, o.id as order_id, o.status, o.created_at as order_created_at,
                       o.assigned_manager_id, m.email as manager_email, m.full_name as manager_name
                FROM order_notifications notif
                JOIN orders o ON notif.order_id = o.id
                LEFT JOIN managers m ON notif.manager_id = m.id
                WHERE notif.manager_id = ? AND notif.is_read = 0
                ORDER BY notif.last_user_message_at DESC
            ''', (manager_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]
        else:
            # Получаем все непрочитанные уведомления (для супер-админа)
            async with db.execute('''
                SELECT notif.*, o.id as order_id, o.status, o.created_at as order_created_at,
                       o.assigned_manager_id, m.email as manager_email, m.full_name as manager_name
                FROM order_notifications notif
                JOIN orders o ON notif.order_id = o.id
                LEFT JOIN managers m ON notif.manager_id = m.id
                WHERE notif.is_read = 0
                ORDER BY notif.last_user_message_at DESC
            ''') as cursor:
                rows = await cursor.fetchall()
                return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def get_notification_by_order_id(order_id: int) -> Dict:
    """Получает уведомление по ID заказа"""
    async with aiosqlite.connect(DB_PATH) as db:
        await configure_db_connection(db)
        
        async with db.execute('''
            SELECT * FROM order_notifications WHERE order_id = ?
        ''', (order_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(zip([column[0] for column in cursor.description], row))
            return None
async def create_notifications_for_all_orders():
    """Создает уведомления для всех заказов"""
    async with aiosqlite.connect(DB_PATH) as db:
        await configure_db_connection(db)
        
        # Находим все заказы
        async with db.execute('''
            SELECT id, assigned_manager_id 
            FROM orders
        ''') as cursor:
            all_orders = await cursor.fetchall()
        
        created_count = 0
        for order_id, manager_id in all_orders:
            # Проверяем, есть ли уже уведомление
            async with db.execute('SELECT id FROM order_notifications WHERE order_id = ?', (order_id,)) as cursor:
                existing = await cursor.fetchone()
            
            if not existing:
                # Создаем уведомление (по умолчанию прочитанное)
                await db.execute('''
                    INSERT INTO order_notifications 
                    (order_id, manager_id, is_read, last_user_message_at, created_at, updated_at)
                    VALUES (?, ?, 1, datetime('now'), datetime('now'), datetime('now'))
                ''', (order_id, manager_id))
                created_count += 1
        
        await db.commit()
        return created_count