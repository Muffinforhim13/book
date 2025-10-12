import asyncio

import json

import logging

import os

import re

from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F

from aiogram.filters import Command, StateFilter

from aiogram.fsm.context import FSMContext

from aiogram.fsm.state import State, StatesGroup

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from aiogram.types import InputMediaPhoto, InputMediaAudio, InputMediaVideo, InputMediaDocument, FSInputFile

from aiogram.fsm.storage.memory import MemoryStorage

from db import init_db, save_user_profile, get_user_book, create_order, get_pending_outbox_tasks, update_outbox_task_status, increment_outbox_retry_count, update_order_status, add_outbox_task, get_order, get_user_active_order, update_order_data, save_selected_pages, save_main_hero_photo, save_hero_photo, save_joint_photo, save_uploaded_file, update_order_email, get_voice_styles, add_upload, update_order_field, track_event



# Функция для трекинга отвалов

async def track_abandonment(user_id: int, step_name: str, product_type: str = None, order_id: int = None):

    """Трекинг отвала пользователя на определенном шаге"""

    await track_event(

        user_id=user_id,

        event_type='step_abandoned',

        event_data={

            'step': step_name,

            'abandoned_at': datetime.now().isoformat()

        },

        step_name=step_name,

        product_type=product_type,

        order_id=order_id

    )



# Функция для трекинга отвалов при неактивности

async def track_inactivity_abandonment(user_id: int, last_step: str, product_type: str = None, order_id: int = None):

    """Трекинг отвала пользователя из-за неактивности"""

    await track_event(

        user_id=user_id,

        event_type='step_abandoned',

        event_data={

            'step': last_step,

            'abandoned_at': datetime.now().isoformat(),

            'reason': 'inactivity'

        },

        step_name=last_step,

        product_type=product_type,

        order_id=order_id

    )

from aiogram.utils.markdown import hcode

import aiohttp

import dotenv



# Универсальная функция для отправки файлов разных типов

async def send_file_by_type(bot: Bot, user_id: int, file_path: str, file_type: str, caption: str = None, reply_markup=None):

    """Отправляет файл пользователю в зависимости от его типа"""

    try:

        if not os.path.exists(file_path):

            logging.error(f"❌ Файл не существует: {file_path}")

            return False

        
        # Проверяем размер файла
        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / (1024 * 1024)
        
        # Лимиты Telegram Bot API
        max_sizes = {
            'photo': 10 * 1024 * 1024,  # 10 МБ
            'video': 50 * 1024 * 1024,  # 50 МБ
            'audio': 50 * 1024 * 1024,  # 50 МБ
            'document': 50 * 1024 * 1024,  # 50 МБ
            'gif': 50 * 1024 * 1024,  # 50 МБ
        }
        
        max_size = max_sizes.get(file_type, 50 * 1024 * 1024)  # По умолчанию 50 МБ
        
        if file_size > max_size:
            logging.error(f"❌ Файл {file_path} слишком большой: {file_size_mb:.1f} МБ (лимит для {file_type}: {max_size / (1024*1024):.0f} МБ)")
            
            # Отправляем сообщение пользователю о том, что файл слишком большой
            error_message = f"⚠️ Файл слишком большой для отправки ({file_size_mb:.1f} МБ). Максимальный размер для {file_type}: {max_size / (1024*1024):.0f} МБ"
            await bot.send_message(user_id, error_message)
            return False

        input_file = FSInputFile(file_path)
        
        logging.info(f"📤 Отправляю {file_type} файл {file_path} ({file_size_mb:.1f} МБ) пользователю {user_id}")

        

        if file_type == 'photo':

            await bot.send_photo(user_id, input_file, caption=caption, reply_markup=reply_markup)

            logging.info(f"📸 Фото отправлено пользователю {user_id}")

        elif file_type == 'audio':

            await bot.send_audio(user_id, input_file, caption=caption, reply_markup=reply_markup)

            logging.info(f"🎵 Аудио отправлено пользователю {user_id}")

        elif file_type == 'video':

            await bot.send_video(user_id, input_file, caption=caption, reply_markup=reply_markup)

            logging.info(f"🎬 Видео отправлено пользователю {user_id}")

        elif file_type == 'gif':

            await bot.send_animation(user_id, input_file, caption=caption, reply_markup=reply_markup)

            logging.info(f"🎭 GIF анимация отправлена пользователю {user_id}")

        elif file_type in ['document', 'archive']:

            await bot.send_document(user_id, input_file, caption=caption, reply_markup=reply_markup)

            logging.info(f"📄 Документ отправлен пользователю {user_id}")

        else:

            # По умолчанию отправляем как документ

            await bot.send_document(user_id, input_file, caption=caption, reply_markup=reply_markup)

            logging.info(f"📄 Файл (тип: {file_type}) отправлен как документ пользователю {user_id}")

        

        return True

    except Exception as e:

        error_msg = str(e)
        if "Request Entity Too Large" in error_msg or "413" in error_msg:
            logging.error(f"❌ Файл {file_path} слишком большой для Telegram Bot API")
            # Отправляем сообщение пользователю
            try:
                await bot.send_message(user_id, f"⚠️ Файл слишком большой для отправки. Пожалуйста, используйте файл меньшего размера.")
            except:
                pass  # Если не можем отправить сообщение, просто логируем
        else:
            logging.error(f"❌ Ошибка отправки файла {file_path} пользователю {user_id}: {e}")
        
        return False


# Функция для создания медиагруппы из файлов разных типов

async def create_mixed_media_group(files: list, content: str = None):

    """Создает медиагруппу из файлов разных типов"""

    media_group = []

    

    for i, file_info in enumerate(files):

        file_path = file_info['file_path']

        file_type = file_info['file_type']

        

        if not os.path.exists(file_path):

            logging.error(f"❌ Файл не существует: {file_path}")

            continue

        
        # Проверяем размер файла
        try:
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)
            
            # Лимиты Telegram Bot API
            max_sizes = {
                'photo': 10 * 1024 * 1024,  # 10 МБ
                'video': 50 * 1024 * 1024,  # 50 МБ
                'audio': 50 * 1024 * 1024,  # 50 МБ
                'document': 50 * 1024 * 1024,  # 50 МБ
                'gif': 50 * 1024 * 1024,  # 50 МБ
            }
            
            max_size = max_sizes.get(file_type, 50 * 1024 * 1024)  # По умолчанию 50 МБ
            
            if file_size > max_size:
                logging.error(f"❌ Файл {file_path} слишком большой для медиагруппы: {file_size_mb:.1f} МБ (лимит для {file_type}: {max_size / (1024*1024):.0f} МБ)")
                continue  # Пропускаем этот файл
                
            logging.info(f"📤 Добавляю {file_type} файл {file_path} ({file_size_mb:.1f} МБ) в медиагруппу")
            
        except Exception as size_error:
            logging.error(f"❌ Ошибка проверки размера файла {file_path}: {size_error}")
            continue

        input_file = FSInputFile(file_path)

        caption = content if i == 0 else None  # Подпись только к первому файлу

        

        if file_type == 'photo':

            media_group.append(InputMediaPhoto(media=input_file, caption=caption))

        elif file_type == 'audio':

            media_group.append(InputMediaAudio(media=input_file, caption=caption))

        elif file_type == 'video':

            media_group.append(InputMediaVideo(media=input_file, caption=caption))

        elif file_type == 'gif':

            # GIF отправляем как анимацию в медиагруппе

            media_group.append(InputMediaVideo(media=input_file, caption=caption))

        else:

            # Документы и архивы отправляем как документы

            media_group.append(InputMediaDocument(media=input_file, caption=caption))

    

    return media_group

from yookassa_integration import (

    init_payments_table, create_payment, get_payment_status, 

    get_product_price, get_product_price_async, format_payment_description, process_payment_webhook,

    update_payment_status, get_payment_by_payment_id, get_upgrade_price_difference

)

from db import aiosqlite, DB_PATH



dotenv.load_dotenv()



# Замените на ваш токен, полученный у BotFather

API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'ВАШ_ТОКЕН_БОТА')

# ID администраторов (через запятую)
ADMIN_IDS = [int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]



# Отладочная информация

print(f"🔑 Используемый токен: {API_TOKEN}")

print(f"📏 Длина токена: {len(API_TOKEN) if API_TOKEN else 0}")



logging.basicConfig(level=logging.INFO)



WELCOME_TEXT = (

    "Добро пожаловать в сервис «Книга о тех кто дорог»!\n\n"

    "Этот бот поможет вам создать уникальную книгу воспоминаний о близких людях. "

    "Следуйте инструкциям, чтобы начать создание вашей книги."

)



# Инициализация бота и диспетчера

bot = Bot(token=API_TOKEN)

storage = MemoryStorage()

dp = Dispatcher(storage=storage)







async def safe_edit_message(message, text: str, **kwargs):

    """

    Безопасно редактирует сообщение. Если редактирование не удается (например, 

    сообщение не содержит текста или это аудио/фото), отправляет новое сообщение.

    """

    try:

        # Проверяем, есть ли у сообщения текст для редактирования

        if hasattr(message, 'text') and message.text:

            await message.edit_text(text, **kwargs)

        else:

            # Если сообщение не содержит текста (аудио, фото и т.д.), отправляем новое

            await message.answer(text, **kwargs)

    except Exception as e:

        # Если не удалось отредактировать, отправляем новое сообщение

        await message.answer(text, **kwargs)



class ProductStates(StatesGroup):

    choosing_product = State()

    product_selected = State()



class RelationStates(StatesGroup):

    choosing_relation = State()

    relation_selected = State()



class CharacterStates(StatesGroup):

    intro_text = State()

    main_photos = State()

    add_more_heroes = State()

    hero_name = State()

    hero_intro = State()

    hero_photos = State()

    done = State()

    gift_reason = State()



class CoverStates(StatesGroup):

    choosing_style = State()

    waiting_for_covers = State()

    choosing_cover = State()

    cover_selected = State()  # Обложка выбрана

    done = State()



class UserDataStates(StatesGroup):

    waiting_first_name = State()

    waiting_last_name = State()

    waiting_phone = State()

    waiting_email = State()

    waiting_personal_data_consent = State()







class GenderStates(StatesGroup):

    choosing_gender = State()

    gender_selected = State()



class PhotoStates(StatesGroup):

    main_face_1 = State()

    main_face_2 = State()

    main_full = State()

    hero_face_1 = State()

    hero_face_2 = State()

    hero_full = State()

    joint_photo = State()



class StoryQuestionsStates(StatesGroup):

    q1 = State()

    q2 = State()

    q3 = State()



# Новые состояния для ожидания контента от менеджера

class ManagerContentStates(StatesGroup):

    waiting_demo_content = State()  # Ожидание демо-контента

    waiting_story_options = State()  # Ожидание вариантов сюжетов

    waiting_draft = State()  # Ожидание черновика

    waiting_final = State()  # Ожидание финальной версии



# Состояния для Главы 11 - Кастомизация сюжетов (УДАЛЕНЫ - используется только фото-реализация)

# Теперь используется ManagerContentStates.waiting_story_options для ожидания фото-страниц



class AdditionsStates(StatesGroup):

    choosing_addition = State()  # Выбор дополнения

    uploading_photos = State()  # Загрузка своих фотографий

    choosing_inserts = State()  # Выбор вкладышей

    waiting_insert_text = State()  # Ожидание текста для вкладыша

    done = State()  # Завершено



class EditBookStates(StatesGroup):

    waiting_for_draft = State()  # Ожидание черновика от менеджера

    reviewing_draft = State()  # Просмотр черновика

    adding_comments = State()  # Добавление комментариев

    done = State()  # Завершено



class DeliveryStates(StatesGroup):

    waiting_for_delivery_choice = State()  # Ожидание выбора способа доставки

    waiting_for_address = State()  # Ожидание ввода адреса

    waiting_for_recipient = State()  # Ожидание имени получателя

    waiting_for_phone = State()  # Ожидание телефона

    done = State()  # Завершено



# Новые состояния для глав 12-18

class BookFinalStates(StatesGroup):

    # Упрощенный выбор страниц

    choosing_pages = State()  # Выбор страниц (все страницы + вкладыши одним блоком)

    choosing_first_last_design = State()  # Выбор оформления первой и последней страницы книги

    entering_first_page_text = State()  # Ввод текста для первой страницы

    entering_last_page_text = State()  # Ввод текста для последней страницы

    uploading_first_last_photos = State()  # Загрузка фотографий для первой и последней страницы книги

    uploading_custom_photos = State()  # Загрузка своих фотографий

    waiting_for_cover_options = State()  # Ожидание вариантов обложек от менеджера

    

    # Новые состояния для пошаговой загрузки первой и последней страницы

    uploading_first_page_photo = State()  # Загрузка фото для первой страницы

    entering_first_page_text_after_photo = State()  # Ввод текста для первой страницы после фото

    uploading_last_page_photo = State()  # Загрузка фото для последней страницы

    entering_last_page_text_after_photo = State()  # Ввод текста для последней страницы после фото

    

    # Глава 14 - Редактирование книги

    waiting_for_book_draft = State()  # Ожидание черновика от менеджера

    reviewing_book_draft = State()  # Просмотр черновика

    adding_draft_comments = State()  # Добавление комментариев к черновику

    

    # Глава 15 - Передача книги

    waiting_for_final_book = State()  # Ожидание финальной версии

    choosing_delivery_method = State()  # Выбор способа доставки

    entering_delivery_address = State()  # Ввод адреса доставки

    

    # Глава 17 - Апсейл (если выбрана электронная книга)

    upsell_options = State()  # Показ апсейл опций

    processing_upsell_payment = State()  # Обработка доплаты

    

    # Глава 18 - Обратная связь и завершение

    collecting_feedback = State()  # Сбор обратной связи

    offering_song_creation = State()  # Предложение создания песни

    order_completed = State()  # Заказ завершен



# --- Сценарий для Песни ---



# Состояния для сценария песни

class SongGenderStates(StatesGroup):

    choosing_gender = State()

    gender_selected = State()



class SongRelationStates(StatesGroup):

    choosing_relation = State()

    waiting_recipient_name = State()

    waiting_gift_reason = State()



class SongStyleStates(StatesGroup):

    choosing_style = State()



class SongVoiceStates(StatesGroup):

    choosing_voice = State()



class SongQuizStates(StatesGroup):

    quiz_q2 = State()

    quiz_q3 = State()



class SongFactsStates(StatesGroup):

    collecting_facts = State()



class SongDraftStates(StatesGroup):

    waiting_for_demo = State()  # Ожидание демо-аудио от менеджера

    demo_received = State()     # Демо получено, ожидание оплаты

    waiting_for_draft = State()

    draft_received = State()



class SongWaitingStates(StatesGroup):

    waiting_and_warming = State()



class SongFinalStates(StatesGroup):

    waiting_for_final = State()

    final_received = State()

    collecting_feedback = State()

    collecting_final_feedback = State()



class SongDemoStates(StatesGroup):

    demo_ready = State()

    demo_received = State()



# --- Вспомогательные функции для обновления заказа и статуса ---

async def update_order_progress(state: FSMContext, status: str = None):

    data = await state.get_data()

    order_id = data.get('order_id')

    if not order_id:

        return

    # Основной герой

    main_hero_photos = []

    if data.get('main_face_1'):

        main_hero_photos.append(data['main_face_1'])

    if data.get('main_face_2'):

        main_hero_photos.append(data['main_face_2'])

    if data.get('main_full'):

        main_hero_photos.append(data['main_full'])

    # Главный герой - это отправитель (first_name)
    main_hero_name = data.get('first_name') or "-"

    

    # Формируем имя отправителя из first_name и last_name

    first_name = data.get('first_name', '')

    last_name = data.get('last_name', '')

    sender_name = ""

    if first_name and first_name != 'None':

        sender_name = first_name

    if last_name and last_name != 'None':

        if sender_name:

            sender_name += f" {last_name}"

        else:

            sender_name = last_name

    

    # Ответы

    answers = []

    if data.get('story_q1'):

        answers.append(data['story_q1'])

        print(f"🔍 ОТЛАДКА: Добавлен ответ q1: {data['story_q1']}")

    if data.get('story_q2'):

        answers.append(data['story_q2'])

        print(f"🔍 ОТЛАДКА: Добавлен ответ q2: {data['story_q2']}")

    if data.get('story_q3'):

        answers.append(data['story_q3'])

        print(f"🔍 ОТЛАДКА: Добавлен ответ q3: {data['story_q3']}")

    

    print(f"🔍 ОТЛАДКА: Все ответы: {answers}")

    # Другие герои (сохраняем name, intro, face_1, face_2, full)

    other_heroes = []

    for hero in data.get('other_heroes', []):

        other_heroes.append({

            'name': hero.get('name'),

            'intro': hero.get('intro'),

            'face_1': hero.get('face_1'),

            'face_2': hero.get('face_2'),

            'full': hero.get('full')

        })

    # Совместное фото

    joint_photo = data.get('joint_photo')

    # Отладка: проверяем данные перед формированием order_data
    current_hero_name = data.get('current_hero_name')  # Имя получателя (второй персонаж)
    recipient_name_fallback = data.get('recipient_name') 
    first_name_fallback = data.get('first_name')  # Имя отправителя (главный персонаж)
    
    # Получатель - приоритет: recipient_name (сохраненное имя), затем current_hero_name, затем fallback
    final_recipient_name = recipient_name_fallback or current_hero_name or "Получатель"
    
    # ВАЖНО: Сохраняем recipient_name обратно в состояние, чтобы оно не терялось
    if final_recipient_name and final_recipient_name != "Получатель":
        await state.update_data(recipient_name=final_recipient_name)
        logging.info(f"💾 СОХРАНЕНО recipient_name в состояние: '{final_recipient_name}'")
    
    logging.info(f"🔍 ОТЛАДКА update_order_progress: current_hero_name='{current_hero_name}', recipient_name='{recipient_name_fallback}', first_name='{first_name_fallback}', final_recipient='{final_recipient_name}', main_hero='{main_hero_name}'")

    order_data = {

        'user_id': data.get('user_id'),

        'username': data.get('username'),

        'first_name': data.get('first_name'),

        'last_name': data.get('last_name'),

        'phone': data.get('phone'),

        'product': data.get('product'),

        'gender': data.get('gender'),

        'relation': data.get('relation'),

        'recipient_name': final_recipient_name,

        'sender_name': sender_name,  # Автоматически сформированное имя отправителя

        'main_hero_intro': data.get('main_hero_intro'),

        'gift_reason': data.get('gift_reason'),

        'style': data.get('style'),

        'main_hero_name': main_hero_name,

        'hero_name': main_hero_name,  # Для совместимости с админкой

        'main_hero_photos': main_hero_photos,

        'other_heroes': other_heroes,

        'joint_photo': joint_photo,

        'answers': answers,

        'book_format': data.get('book_format'),  # Добавляем формат книги

        'format': data.get('format')  # Добавляем формат (для совместимости)

    }

    

    print(f"🔍 ОТЛАДКА КНИГИ: Сохраняем данные для заказа {order_id}:")

    print(f"📊 Данные книги: {order_data}")

    

    # Используем thread-safe функцию update_order_data вместо прямого обращения к БД

    await update_order_data(order_id, order_data)

    

    print(f"✅ Данные книги сохранены для заказа {order_id}")

    

    # Сохраняем фотографии в базу данных

    from db import save_main_hero_photo, save_hero_photo, save_joint_photo

    

    try:

        # Сохраняем фотографии главного героя

        if data.get('main_face_1'):

            await save_main_hero_photo(order_id, data['main_face_1'])

        if data.get('main_face_2'):

            await save_main_hero_photo(order_id, data['main_face_2'])

        if data.get('main_full'):

            await save_main_hero_photo(order_id, data['main_full'])

    except Exception as e:

        logging.error(f"❌ Ошибка сохранения фотографий главного героя: {e}")

        # Продолжаем выполнение, даже если сохранение фотографий не удалось

    

    try:

        # Сохраняем фотографии других героев

        for hero in data.get('other_heroes', []):

            hero_name = hero.get('name', 'hero')

            if hero.get('face_1'):

                await save_hero_photo(order_id, hero['face_1'], 'face_1', hero_name)

            if hero.get('face_2'):

                await save_hero_photo(order_id, hero['face_2'], 'face_2', hero_name)

            if hero.get('full'):

                await save_hero_photo(order_id, hero['full'], 'full', hero_name)

        

        # Сохраняем совместное фото

        if data.get('joint_photo'):

            await save_joint_photo(order_id, data['joint_photo'])

    except Exception as e:

        logging.error(f"❌ Ошибка сохранения фотографий других героев: {e}")

        # Продолжаем выполнение, даже если сохранение фотографий не удалось

    

    print(f"📸 Фотографии сохранены в базу данных для заказа {order_id}")

    

    # Проверяем что данные действительно сохранились

    from db import get_order_data_debug

    saved_data = await get_order_data_debug(order_id)

    print(f"🔍 Проверка сохранения для заказа {order_id}: {saved_data}")

    

    if status:

        await update_order_status(order_id, status)



async def remove_cover_buttons_for_user(user_id: int, selected_template_id: int = None):

    """Убирает кнопки с других обложек после выбора одной"""

    try:

        # Получаем message_id обложек из state пользователя

        from aiogram.fsm.context import FSMContext

        from aiogram.fsm.storage.base import StorageKey

        

        # Создаем FSMContext для пользователя

        storage_key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)

        user_state = FSMContext(storage=dp.storage, key=storage_key)

        

        data = await user_state.get_data()

        cover_message_ids = data.get('cover_message_ids', [])

        

        logging.info(f"🔍 Убираем кнопки с {len(cover_message_ids)} обложек для пользователя {user_id}")

        

        # Убираем кнопки с других обложек

        for message_id in cover_message_ids:

            try:

                # Убираем кнопки с сообщения обложки

                await bot.edit_message_reply_markup(

                    chat_id=user_id,

                    message_id=message_id,

                    reply_markup=None

                )

                logging.info(f"✅ Убраны кнопки с обложки message_id={message_id}")

            except Exception as e:

                logging.error(f"Ошибка при убирании кнопок с обложки message_id={message_id}: {e}")

        

        # Очищаем список message_id обложек

        await user_state.update_data(cover_message_ids=[])

        logging.info(f"✅ Кнопки убраны со всех обложек для пользователя {user_id}")

                

    except Exception as e:

        logging.error(f"Ошибка в remove_cover_buttons_for_user: {e}")



async def log_state(message, state):

    current_state = await state.get_state()

    

    # ОТЛАДКА: Проверяем данные в state

    data = await state.get_data()

    state_user_id = data.get('user_id')

    logging.info(f"🔍 ОТЛАДКА log_state: message.from_user.id={message.from_user.id}, state user_id={state_user_id}")

    if state_user_id != message.from_user.id:

        logging.error(f"❌ ОТЛАДКА log_state: НЕСООТВЕТСТВИЕ! message.from_user.id={message.from_user.id}, state user_id={state_user_id}")

    

    logging.info(f"User {message.from_user.id} state: {current_state}")

    if hasattr(message, 'photo') and message.photo:

        logging.info(f"User {message.from_user.id} sent a photo. File ID: {message.photo[-1].file_id}")

    elif hasattr(message, 'text'):

        logging.info(f"User {message.from_user.id} sent: {message.text}")

    elif hasattr(message, 'data'):

        logging.info(f"User {message.from_user.id} callback data: {message.data}")

    else:

        logging.info(f"User {message.from_user.id} sent unknown type: {type(message)}")



async def request_phone_number(message, state):

    """Функция для запроса номера телефона"""

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="Я готов отправить номер", callback_data="send_phone")],

        [InlineKeyboardButton(text="Не хочу отправлять номер", callback_data="decline_phone")]

    ])

    await message.answer("Пожалуйста, отправьте ваш номер телефона, нажав кнопку ниже, а затем отправьте контакт вручную.", reply_markup=keyboard)

    await state.set_state(UserDataStates.waiting_phone)

    await log_state(message, state)



def parse_utm_parameters(message: types.Message) -> dict:

    """Парсит UTM-параметры из startapp ссылки"""

    utm_params = {

        'utm_source': None,

        'utm_medium': None,

        'utm_campaign': None,
        
        'utm_content': None

    }

    

    if message.text and len(message.text.split()) > 1:

        # Извлекаем параметры из команды /start

        params = message.text.split()[1:]

        

        # Объединяем все параметры в одну строку для парсинга

        full_params = ' '.join(params)

        logging.info(f"🔍 ОТЛАДКА UTM: Полные параметры: '{full_params}'")

        

        # Парсим UTM-параметры

        if 'utm_source=' in full_params:

            try:

                # Сначала пробуем разделить по --, потом по &
                utm_source = full_params.split('utm_source=')[1].split('--')[0].split('&')[0]

                utm_params['utm_source'] = utm_source
                logging.info(f"🔍 ОТЛАДКА UTM: utm_source = '{utm_source}'")

            except:

                pass

                

        if 'utm_medium=' in full_params:

            try:

                # Сначала пробуем разделить по --, потом по &
                utm_medium = full_params.split('utm_medium=')[1].split('--')[0].split('&')[0]

                utm_params['utm_medium'] = utm_medium
                logging.info(f"🔍 ОТЛАДКА UTM: utm_medium = '{utm_medium}'")

            except:

                pass

                

        if 'utm_campaign=' in full_params:

            try:

                # Сначала пробуем разделить по --, потом по &
                utm_campaign = full_params.split('utm_campaign=')[1].split('--')[0].split('&')[0]

                utm_params['utm_campaign'] = utm_campaign
                logging.info(f"🔍 ОТЛАДКА UTM: utm_campaign = '{utm_campaign}'")

            except:

                pass

                
        if 'utm_content=' in full_params:

            try:

                # Сначала пробуем разделить по --, потом по &
                utm_content = full_params.split('utm_content=')[1].split('--')[0].split('&')[0]

                utm_params['utm_content'] = utm_content
                logging.info(f"🔍 ОТЛАДКА UTM: utm_content = '{utm_content}'")

            except:

                pass

    

    return utm_params



def detect_source_from_message(message: types.Message) -> str:

    """Определяет источник пользователя на основе параметров сообщения"""

    # Проверяем, есть ли параметры в тексте команды

    if message.text and len(message.text.split()) > 1:

        # Извлекаем параметры из команды /start

        params = message.text.split()[1:]

        

        # Обрабатываем UTM-параметры

        for param in params:

            param_lower = param.lower()

            

            # Проверяем различные варианты источников

            if any(keyword in param_lower for keyword in ['landing', 'лендинг', 'site', 'сайт']):

                return 'Лендинг'

            elif any(keyword in param_lower for keyword in ['ads', 'реклама', 'ad', 'yandex', 'google', 'vk', 'facebook', 'instagram']):

                return 'Реклама'

            elif any(keyword in param_lower for keyword in ['channel', 'канал', 'telegram', 'tg']):

                return 'Telegram-канал'

            elif any(keyword in param_lower for keyword in ['organic', 'органика', 'search', 'поиск']):

                return 'Органика'

            

            # Проверяем UTM-параметры

            if 'utm_source=' in param_lower:

                source_value = param_lower.split('utm_source=')[1].split('&')[0]

                if 'landing' in source_value or 'лендинг' in source_value:

                    return 'Лендинг'

                elif 'ads' in source_value or 'реклама' in source_value:

                    return 'Реклама'

                elif 'channel' in source_value or 'канал' in source_value:

                    return 'Telegram-канал'

                elif 'organic' in source_value or 'органика' in source_value:

                    return 'Органика'

    

    # Проверяем, пришел ли пользователь из канала (если есть информация о форварде)

    if message.forward_from_chat:

        return 'Telegram-канал'

    

    # По умолчанию считаем органическим трафиком

    return 'Органика'



@dp.message(Command("start"))

async def send_welcome(message: types.Message, state: FSMContext):
    
    logging.info(f"🚀 ОТЛАДКА: Получена команда /start от пользователя {message.from_user.id}")
    logging.info(f"🚀 ОТЛАДКА: Текст сообщения: '{message.text}'")
    logging.info(f"🚀 ОТЛАДКА: Полное сообщение: {message}")
    
    user = message.from_user

    user_data = {

        "user_id": user.id,

        "username": user.username,

        "first_name": user.first_name,

        "last_name": user.last_name

    }

    logging.info(f"Пользователь: {user_data}")



    # Определяем источник пользователя и UTM-параметры

    source = detect_source_from_message(message)

    utm_params = parse_utm_parameters(message)

    logging.info(f"🔍 Определен источник для пользователя {user.id}: {source}")

    logging.info(f"🔍 UTM-параметры для пользователя {user.id}: {utm_params}")



    # Трекинг: вход в бота

    await track_event(

        user_id=user.id,

        event_type='bot_entry',

        event_data={

            'username': user.username,

            'first_name': user.first_name,

            'last_name': user.last_name,

            'source': source,

            'utm_source': utm_params['utm_source'],

            'utm_medium': utm_params['utm_medium'],

            'utm_campaign': utm_params['utm_campaign']

        },

        source=source,

        utm_source=utm_params['utm_source'],

        utm_medium=utm_params['utm_medium'],

        utm_campaign=utm_params['utm_campaign']

    )



    # Очищаем состояние пользователя

    await state.clear()

    logging.info(f"🧹 Очищено состояние пользователя {user.id}")



    # Сохраняем базовые данные пользователя

    await state.update_data(

        user_id=user.id, 

        username=user.username,  # Username подтягиваем из Telegram

        # first_name и last_name НЕ подтягиваем автоматически - пользователь должен ввести вручную

        consent_given=True,  # Автоматически даем согласие

        source=source,  # Сохраняем источник

        utm_source=utm_params['utm_source'],

        utm_medium=utm_params['utm_medium'],

        utm_campaign=utm_params['utm_campaign']

    )

    

    # ОТЛАДКА: Проверяем что сохранилось в state

    debug_data = await state.get_data()

    logging.info(f"🔍 ОТЛАДКА /start: Сохранили в state user_id={debug_data.get('user_id')}, username={debug_data.get('username')}")

    logging.info(f"🔍 ОТЛАДКА /start: message.from_user.id={user.id}, message.from_user.username={user.username}")

    

    # Сохраняем профиль пользователя в базу данных

    user_data = {

        "user_id": user.id,

        "username": user.username,  # Username подтягиваем из Telegram

        # first_name и last_name НЕ подтягиваем автоматически

        "first_name": None,

        "last_name": None

    }

    await save_user_profile(user_data, None)

    

    # Сразу показываем приветственное сообщение

    await show_welcome_message(message, state)





# Функция для получения данных заказа из базы данных

async def get_order_summary_data(order_id: int, state: FSMContext = None) -> dict:

    """Получает данные заказа из базы данных для формирования сводки"""

    from db import get_order_data_debug

    order_data = await get_order_data_debug(order_id)

    order_data['order_id'] = order_id  # Добавляем ID заказа

    

    # Если передан state, дополняем данными из state (они могут быть более актуальными)

    if state:

        state_data = await state.get_data()

        # Объединяем данные, приоритет у state

        order_data.update(state_data)

        

        # Добавляем тексты страниц из state, если они есть

        if 'first_page_text' in state_data:

            order_data['first_page_text'] = state_data['first_page_text']

        if 'last_page_text' in state_data:

            order_data['last_page_text'] = state_data['last_page_text']

    

    return order_data



# Функция для формирования сводки данных заказа

async def format_order_summary(data: dict, product_type: str) -> str:

    """Формирует сводку данных заказа для отображения перед оплатой"""

    # Отладочная информация

    print(f"🔍 ОТЛАДКА СВОДКИ ЗАКАЗА: Получены данные: {data}")

    print(f"🔍 ОТЛАДКА СВОДКИ ЗАКАЗА: Тип продукта: {product_type}")

    

    summary = f"📋 <b>Сводка заказа ({product_type}):</b>\n\n"

    

    if product_type == "Книга":

        # Данные для книги

        summary += f"👤 <b>Пол отправителя:</b> {data.get('gender', 'Не указан')}\n"

        summary += f"📝 <b>Имя получателя:</b> {data.get('recipient_name', 'Не указано')}\n"

        summary += f"🎯 <b>Повод:</b> {data.get('gift_reason', 'Не указан')}\n"

        # Преобразуем отношение для корректного отображения в сводке
        relation = data.get('relation', 'Не указано')
        gender = data.get('gender', '')
        
        # Применяем маппинг отношения с учетом пола
        if relation != 'Не указано':
            # Используем ту же логику, что и в get_questions_for_relation
            def get_mapped_relation_for_summary(relation, gender):
                if relation == "Подруге":
                    return "Подруга - подруге"
                elif relation == "Девушке":
                    if gender == "мальчик" or gender == "парень":
                        return "Парень - девушке"
                    else:
                        return "Девушка - парню"
                elif relation == "Парню":
                    if gender == "мальчик" or gender == "парень":
                        return "Парень - девушке"
                    else:
                        return "Девушка - парню"
                elif relation == "Маме":
                    if gender == "мальчик" or gender == "парень":
                        return "Сын – маме"
                    else:
                        return "Дочка- маме"
                elif relation == "Папе":
                    if gender == "мальчик" or gender == "парень":
                        return "Сын – папе"
                    else:
                        return "Дочка- папе"
                elif relation == "Бабушке":
                    # Учитываем пол пользователя
                    if gender == "мальчик" or gender == "парень":
                        return "Внук - бабушке"
                    else:
                        return "Внучка - бабушке"
                elif relation == "Дедушке":
                    # Учитываем пол пользователя
                    if gender == "мальчик" or gender == "парень":
                        return "Внук - дедушке"
                    else:
                        return "Внучка - дедушке"
                elif relation == "Сестре":
                    if gender == "мальчик" or gender == "парень":
                        return "Брат – сестре"
                    else:
                        return "Сестра - сестре"
                elif relation == "Брату":
                    if gender == "девушка":
                        return "Сестра - брату"
                    else:
                        return "Брат - брату"
                elif relation == "Сыну":
                    return "Мама - сыну"
                elif relation == "Дочке" or relation == "Дочери":
                    return "Мама - дочке"
                elif relation == "Мужу":
                    return "Жена - мужу"
                elif relation == "Жене":
                    return "Муж - жене"
                else:
                    return relation
            
            relation = get_mapped_relation_for_summary(relation, gender)

        summary += f"💝 <b>Отношение:</b> {relation}\n"

        summary += f"🎨 <b>Стиль:</b> {data.get('style', 'Не указан')}\n"

        summary += f"📖 <b>Формат:</b> {data.get('format', 'Не указан')}\n"

        summary += f"👤 <b>От кого:</b> {data.get('sender_name', 'Не указано')}\n"

        

        # Дополнительные данные

        if data.get('additional_info'):

            summary += f"📝 <b>Дополнительно:</b> {data.get('additional_info', 'Не указано')}\n"

        

    elif product_type == "Песня":

        # Специальный текст для песни

        summary = "Спасибо, что хочешь продолжить🙏🏻\n"

        summary += "Мы выбрали для тебя самый тёплый формат.\n\n"

        summary += "✨ Авторская песня по вашей истории длительностью 3 минуты с трогательными поздравительными словами от тебя за 2900 рублей.\n\n"

        summary += "Это не просто музыка, а подарок, в котором оживают твои воспоминания, детали вашей истории и чувства.\n"

        summary += "Он передаст то, что невозможно купить - искреннюю любовь❤️\n"

        summary += "Такая песня тронет до мурашек и станет воспоминанием, которое останется навсегда.\n\n"

        summary += "Мы бережно соберём самые важные моменты и превратим их в тёплый текст.\n"

        summary += "Далее мы добавим уникальную аранжировку, чтобы песня звучала именно про вас 🎶\n"

        summary += "И отправим тебе версию на утверждение, чтобы каждое слово попало \"В самое сердце\"❤️"

        

        return summary

    

    # Общие данные

    summary += f"🆔 <b>Номер заказа:</b> #{data.get('order_id', 'Не указан')}\n"

    

    # Показываем имя+фамилию (не используем username автоматически)

    first_name = data.get('first_name')

    last_name = data.get('last_name')

    

    # Убираем None значения и лишние пробелы

    name_parts = []

    if first_name and first_name != 'None':

        name_parts.append(first_name)

    if last_name and last_name != 'None':

        name_parts.append(last_name)

    

    if name_parts:

        full_name = ' '.join(name_parts)

        summary += f"👤 <b>Пользователь:</b> {full_name}\n"

    else:

        summary += f"👤 <b>Пользователь:</b> Не указан\n"

    

    return summary





async def check_and_request_user_name(message, state, next_action="welcome"):

    """Проверяет, есть ли имя пользователя, и запрашивает его при необходимости"""

    data = await state.get_data()

    first_name = data.get('first_name')

    

    # Если нет имени - запрашиваем только имя

    if not first_name:

        await message.answer("Поделись, как тебя зовут 💌 Нам важно знать, чтобы обращаться к тебе лично")

        await state.set_state(UserDataStates.waiting_first_name)

        # Сохраняем информацию о том, что делать после ввода имени

        await state.update_data(after_name_input=next_action)

        return False  # Имя еще не введено

    else:

        return True  # Имя уже есть



async def start_book_creation_flow(callback_or_message, state):

    """Начинает процесс создания книги"""

    # Создаем заказ и начинаем процесс

    data = await state.get_data()

    

    # ИСПРАВЛЕНИЕ: Получаем user_id из callback или message

    if hasattr(callback_or_message, 'message'):

        # Это callback

        user_id = callback_or_message.from_user.id

        message = callback_or_message.message

    else:

        # Это message

        user_id = callback_or_message.from_user.id

        message = callback_or_message

    

    product = "Книга"

    

    # ОТЛАДКА: Проверяем данные

    logging.info(f"🔍 ОТЛАДКА start_book_creation_flow: user_id={user_id}, state user_id={data.get('user_id')}")

    logging.info(f"🔍 ОТЛАДКА start_book_creation_flow: message.chat.id={message.chat.id}")

    

    await state.update_data(product=product)

    

    # Получаем username из последнего заказа пользователя

    from db import get_last_order_username

    last_username = await get_last_order_username(user_id)

    

    order_data = {

        "product": product,

        "user_id": user_id,

        "username": last_username or data.get('username') or message.from_user.username,

        "first_name": data.get('first_name'),

        "last_name": data.get('last_name'),
        
        # Добавляем UTM параметры
        "source": data.get('source'),
        "utm_source": data.get('utm_source'),
        "utm_medium": data.get('utm_medium'),
        "utm_campaign": data.get('utm_campaign')

    }

    order_id = await create_order(user_id, order_data)

    await state.update_data(order_id=order_id)

    await update_order_status(order_id, "product_selected")
    
    # Создаем таймер для отложенных сообщений
    from db import create_or_update_user_timer
    await create_or_update_user_timer(user_id, order_id, "product_selected", product)
    logging.info(f"✅ Создан таймер отложенных сообщений для {product}, пользователь {user_id}, заказ {order_id}")

    

    # Переносим ранние сообщения пользователя в историю заказа

    from db import transfer_early_messages_to_order

    await transfer_early_messages_to_order(user_id, order_id)

    

    # Трекинг: создание заказа

    source = data.get('source', 'Органика')

    await track_event(

        user_id=user_id,

        event_type='order_created',

        event_data={

            'product': 'Книга',

            'username': last_username or data.get('username') or message.from_user.username

        },

        product_type='Книга',

        order_id=order_id,

        source=source

    )

    

    # Используем хардкод для сообщения о выборе пола

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="Женский 👩🏼", callback_data="gender_female")],

        [InlineKeyboardButton(text="Мужской 🧑🏼", callback_data="gender_male")],

    ])

    await message.answer(

        "Замечательный выбор ✨\nМы позаботимся о том, чтобы твоя книга получилась душевной и бережно сохранила все важные воспоминания.\n\nОтветь на несколько вопросов и мы начнём собирать твою историю 📖\n\n👤 Выбери свой пол:",

        reply_markup=keyboard

    )

    await state.set_state(GenderStates.choosing_gender)



async def start_song_creation_flow(callback_or_message, state):

    """Начинает процесс создания песни"""

    # Создаем заказ и начинаем процесс

    data = await state.get_data()

    

    # ИСПРАВЛЕНИЕ: Получаем user_id из callback или message

    if hasattr(callback_or_message, 'message'):

        # Это callback

        user_id = callback_or_message.from_user.id

        message = callback_or_message.message

    else:

        # Это message

        user_id = callback_or_message.from_user.id

        message = callback_or_message

    

    product = "Песня"

    

    await state.update_data(product=product)

    

    # Получаем username из последнего заказа пользователя

    from db import get_last_order_username

    last_username = await get_last_order_username(user_id)

    

    order_data = {

        "product": product,

        "user_id": user_id,

        "username": last_username or data.get('username') or message.from_user.username,

        "first_name": data.get('first_name'),

        "last_name": data.get('last_name'),
        
        # Добавляем UTM параметры
        "source": data.get('source'),
        "utm_source": data.get('utm_source'),
        "utm_medium": data.get('utm_medium'),
        "utm_campaign": data.get('utm_campaign')

    }

    order_id = await create_order(user_id, order_data)

    await state.update_data(order_id=order_id)

    await update_order_status(order_id, "product_selected")
    
    # Создаем таймер для отложенных сообщений
    from db import create_or_update_user_timer
    await create_or_update_user_timer(user_id, order_id, "product_selected", product)
    logging.info(f"✅ Создан таймер отложенных сообщений для {product}, пользователь {user_id}, заказ {order_id}")

    

    # Переносим ранние сообщения пользователя в историю заказа

    from db import transfer_early_messages_to_order

    await transfer_early_messages_to_order(user_id, order_id)

    

    # Трекинг: создание заказа

    source = data.get('source', 'Органика')

    await track_event(

        user_id=user_id,

        event_type='order_created',

        event_data={

            'product': 'Песня',

            'username': last_username or data.get('username') or message.from_user.username

        },

        product_type='Песня',

        order_id=order_id,

        source=source

    )

    

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="Женский 👩🏼", callback_data="song_gender_female")],

        [InlineKeyboardButton(text="Мужской 🧑🏼", callback_data="song_gender_male")],

    ])

    await message.answer(

        "Отличный выбор подарка✨\nМы сделаем все, чтобы твой подарок получился тёплым и трогательным 🫶🏻\n\nОтветь, пожалуйста, на несколько коротких вопросов, чтобы твоя песня попала в самое сердце \n\nВыбери свой пол:",

        reply_markup=keyboard

    )

    await state.set_state(SongGenderStates.choosing_gender)



async def show_welcome_message(message, state):

    """Функция для показа приветственного сообщения"""

    try:

        # Получаем данные пользователя из state

        data = await state.get_data()

        user_id = data.get('user_id')

        

        # ОТЛАДКА: Проверяем данные в state

        logging.info(f"🔍 ОТЛАДКА show_welcome_message: state user_id={user_id}")

        logging.info(f"🔍 ОТЛАДКА show_welcome_message: message.from_user.id={message.from_user.id}")

        logging.info(f"🔍 ОТЛАДКА show_welcome_message: message.from_user.username={message.from_user.username}")

        logging.info(f"🔍 ОТЛАДКА show_welcome_message: полные данные state={data}")

        

        # Получаем приветственное сообщение из базы данных

        from bot_messages_cache import get_welcome_message, get_message_content

        WELCOME_TEXT = await get_welcome_message()

        

        # Получаем текст для кнопок из базы данных

        book_text = await get_message_content("product_book", "Пробная книга 📕")

        song_text = await get_message_content("product_song", "Пробная песня 🎶")

        

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text=book_text, callback_data="product_book")],

            [InlineKeyboardButton(text=song_text, callback_data="product_song")]

        ])

        

        logging.info(f"📤 Отправляем приветственное сообщение пользователю {message.from_user.id}")

        logging.info(f"🔍 ОТЛАДКА: message.chat.id={message.chat.id}, message.from_user.id={message.from_user.id}")

        await message.answer(WELCOME_TEXT, reply_markup=keyboard)

        

        # Трекинг: нажатие кнопки "Старт"

        data = await state.get_data()

        source = data.get('source', 'Органика')

        await track_event(

            user_id=message.from_user.id,

            event_type='start_clicked',

            event_data={

                'username': message.from_user.username,

                'first_name': message.from_user.first_name

            },

            source=source

        )

        

        # Устанавливаем состояние ожидания выбора продукта

        await state.set_state(ProductStates.choosing_product)

        

        # НЕ очищаем state, чтобы сохранить данные пользователя

        logging.info(f"✅ Приветственное сообщение отправлено пользователю {message.from_user.id}")

        await log_state(message, state)

        

    except Exception as e:

        logging.error(f"❌ Ошибка в show_welcome_message: {e}")

        import traceback

        logging.error(f"❌ Traceback: {traceback.format_exc()}")

        # В случае ошибки пытаемся отправить полное сообщение без клавиатуры

        try:

            WELCOME_TEXT = (

                "👋 Привет!\n\n"

                "Я помогу тебе создать уникальный подарок — персональную книгу или песню с твоим голосом, лицом и теплом — для любимого человека.\n\n"

                "Это будет история или мелодия, в которой ты — главный герой.\n\n"

                "Что вы хотите создать?\n\n"

                "Напишите 'Книга' или 'Песня' для продолжения."

            )

            await message.answer(WELCOME_TEXT)

            await state.set_state(ProductStates.choosing_product)

        except Exception as e2:

            logging.error(f"❌ Не удалось отправить даже упрощенное сообщение: {e2}")

            try:

                await message.answer("👋 Привет! Готов начать создание подарка?")

            except:

                logging.error(f"❌ Не удалось отправить даже простое сообщение пользователю {message.from_user.id}")

        await log_state(message, state)



# Обработка имени

@dp.message(StateFilter(UserDataStates.waiting_first_name))

async def process_first_name(message: types.Message, state: FSMContext):

    # Сохраняем сообщение пользователя

    await save_user_message_to_history(message, state, "Имя: ")

    await state.update_data(first_name=message.text)

    data = await state.get_data()

    

    # Выполняем действие после ввода имени (не запрашиваем фамилию)

    after_action = data.get('after_name_input', 'welcome')

    if after_action == 'welcome':

        await show_welcome_message(message, state)

    elif after_action == 'book':

        await start_book_creation_flow(message, state)

    elif after_action == 'song':

        await start_song_creation_flow(message, state)

    elif after_action == 'book_relation':

        # После ввода имени для книги - переходим к выбору типа связи

        gender = data.get('gender')

        if gender:

            await show_relation_choice_after_name(message, state, gender)

        else:

            await show_welcome_message(message, state)

    elif after_action == 'song_relation':

        # После ввода имени для песни - переходим к выбору получателя

        gender = data.get('song_gender')

        if gender:

            await show_song_relation_choice_after_name(message, state, gender)

        else:

            await show_welcome_message(message, state)



# Обработка фамилии (оставляем для совместимости, но не используем)

@dp.message(StateFilter(UserDataStates.waiting_last_name))

async def process_last_name(message: types.Message, state: FSMContext):

    # Сохраняем сообщение пользователя

    await save_user_message_to_history(message, state, "Фамилия: ")

    await state.update_data(last_name=message.text)

    data = await state.get_data()

    

    # Выполняем действие после ввода фамилии

    after_action = data.get('after_name_input', 'welcome')

    if after_action == 'welcome':

        await show_welcome_message(message, state)

    elif after_action == 'book':

        await start_book_creation_flow(message, state)

    elif after_action == 'song':

        await start_song_creation_flow(message, state)



# Обработка телефона через контакт

@dp.message(StateFilter(UserDataStates.waiting_phone), F.contact)

async def process_phone_contact(message: types.Message, state: FSMContext):

    phone = message.contact.phone_number

    await state.update_data(phone=phone)

    data = await state.get_data()

    # Сохраняем профиль пользователя

    await save_user_profile(data, None)

    # Удаляем клавиатуру

    await message.answer("Спасибо! Данные сохранены.", reply_markup=types.ReplyKeyboardRemove())

    # Переход к приветствию и выбору продукта

    await show_welcome_message(message, state)



# Обработка телефона при ручном вводе

@dp.message(StateFilter(UserDataStates.waiting_phone))

async def process_phone_manual(message: types.Message, state: FSMContext):

    # Сохраняем сообщение пользователя

    await save_user_message_to_history(message, state, "Телефон: ")

    # Валидация номера телефона

    phone = message.text.strip()

    

    # Проверяем, что номер содержит только цифры и возможно знак +

    if not re.match(r'^\+?[\d\s\(\)\-]+$', phone):

        await message.answer(

            "❌ <b>Неверный формат номера телефона!</b>\n\n"

            "Пожалуйста, введите номер в одном из форматов:\n"

            "• +dytc (999) 123-45-67\n"

            "• 89991234567\n"

            "• 9991234567\n\n"

            "Или используйте кнопку 'Поделиться контактом'",

            parse_mode="HTML"

        )

        return

    

    # Проверяем минимальную длину (должно быть минимум 10 цифр)

    digits_only = re.sub(r'[^\d]', '', phone)

    if len(digits_only) < 10:

        await message.answer(

            "❌ Номер телефона должен содержать от 11 цифр.\n"

            "Пожалуйста, введи корректный номер телефона 💌",

            parse_mode="HTML"

        )

        return

    

    # Проверяем максимальную длину (не более 15 цифр)

    if len(digits_only) > 15:

        await message.answer(

            "❌ <b>Номер телефона слишком длинный!</b>\n\n"

            "Номер не должен содержать более 15 цифр.\n"

            "Попробуйте еще раз:",

            parse_mode="HTML"

        )

        return

    

    await state.update_data(phone=phone)

    data = await state.get_data()

    # Сохраняем профиль пользователя

    await save_user_profile(data, None)

    # Удаляем клавиатуру

    await message.answer("Спасибо! Данные сохранены.", reply_markup=types.ReplyKeyboardRemove())

    # Переход к приветствию и выбору продукта

    await show_welcome_message(message, state)



# Обработка email

@dp.message(StateFilter(UserDataStates.waiting_email))

async def process_email(message: types.Message, state: FSMContext):

    # Сохраняем сообщение пользователя

    await save_user_message_to_history(message, state, "Email: ")

    try:

        email = message.text.strip()

        

        # Простая валидация email

        if '@' not in email or '.' not in email:

            await message.answer("❌ Пожалуйста, введите корректный email адрес.")

            return

        

        # Сохраняем email в state

        await state.update_data(email=email)

        

        # Получаем order_id для сохранения в базу

        data = await state.get_data()

        order_id = data.get('order_id')

        

        if order_id:

            await update_order_email(order_id, email)

        

        # Определяем тип продукта

        product = data.get('product', 'Книга')

        

        # Email сохранен, переходим к следующему шагу

        if product == "Песня":

            await message.answer("✅ Email сохранен! Теперь мы можем продолжить создание вашей песни.")

            

            # Для песни переходим к анкете

            await state.set_state(SongFactsStates.collecting_facts)

            await update_order_status(order_id, "collecting_facts")

            # Создаем таймер для этапа "collecting_facts"
            from db import create_or_update_user_timer, get_order
            user_id = message.from_user.id
            
            # Получаем тип продукта из заказа в базе данных
            order = await get_order(order_id)
            if order and order.get('order_data'):
                import json
                order_data = order['order_data']
                if isinstance(order_data, str):
                    order_data = json.loads(order_data)
                product_type = order_data.get('product', 'Неизвестно')
            else:
                product_type = data.get('product', 'Неизвестно')
            
            await create_or_update_user_timer(user_id, order_id, "collecting_facts", product_type)
            logging.info(f"✅ Создан таймер для этапа collecting_facts, продукт {product_type}, пользователь {user_id}, заказ {order_id}")
            
            # Создаем таймер для этапа "answering_questions" (отправляется при достижении collecting_facts)
            await create_or_update_user_timer(user_id, order_id, "answering_questions", product_type)
            logging.info(f"✅ Создан таймер для этапа answering_questions, продукт {product_type}, пользователь {user_id}, заказ {order_id}")

            # Создаем отложенные сообщения для напоминаний о заполнении анкеты
            try:
                from db import add_delayed_message
                
                # Создаем напоминания в зависимости от типа продукта
                if product_type == "Песня":
                    # Создаем напоминания о заполнении анкеты для песни
                    await add_delayed_message(
                        order_id=order_id,
                        user_id=user_id,
                        message_type="song_filling_reminder_20m",
                        content="Привет! ✨ Вижу, анкета не заполнена до конца, возможно, тебя что-то отвлекло. Так бывает - жизнь полна дел и забот. Твоя история ждет, когда ты будешь готов её рассказать. Всего пара минут, и мы сможем создать что-то по-настоящему особенное. Ведь ценные моменты жизни не повторяются дважды 💕",
                        delay_minutes=20,
                        order_step="song_collecting_facts"
                    )
                    
                    await add_delayed_message(
                        order_id=order_id,
                        user_id=user_id,
                        message_type="song_filling_reminder_1h",
                        content="Твоя история уникальна",
                        delay_minutes=60,
                        order_step="song_collecting_facts"
                    )
                    
                    await add_delayed_message(
                        order_id=order_id,
                        user_id=user_id,
                        message_type="song_filling_reminder_2h",
                        content="Каждая история любви уникальна 💕 Твоя история с этим особенным человеком больше ни у кого не повторится. Эти воспоминания, моменты, чувства - они бесценны.",
                        delay_minutes=120,
                        order_step="song_collecting_facts"
                    )
                    
                    await add_delayed_message(
                        order_id=order_id,
                        user_id=user_id,
                        message_type="song_filling_reminder_4h",
                        content="Время летит, а воспоминания остаются навсегда. Не упусти возможность создать что-то особенное для того, кто дорог твоему сердцу.",
                        delay_minutes=240,
                        order_step="song_collecting_facts"
                    )
                    
                    await add_delayed_message(
                        order_id=order_id,
                        user_id=user_id,
                        message_type="song_filling_reminder_8h",
                        content="Персональная песня - это не просто подарок, это частичка твоей души, подаренная тому, кого ты любишь.",
                        delay_minutes=480,
                        order_step="song_collecting_facts"
                    )
                elif product_type == "Книга":
                    # Создаем напоминания о заполнении анкеты для книги
                    await add_delayed_message(
                        order_id=order_id,
                        user_id=user_id,
                        message_type="book_filling_reminder_20m",
                        content="Привет! ✨ Вижу, анкета не заполнена до конца, возможно, тебя что-то отвлекло. Так бывает - жизнь полна дел и забот. Твоя история ждет, когда ты будешь готов её рассказать. Всего пара минут, и мы сможем создать что-то по-настоящему особенное. Ведь ценные моменты жизни не повторяются дважды 💕",
                        delay_minutes=20,
                        order_step="book_collecting_facts"
                    )
                    
                    await add_delayed_message(
                        order_id=order_id,
                        user_id=user_id,
                        message_type="book_filling_reminder_1h",
                        content="Твоя история уникальна",
                        delay_minutes=60,
                        order_step="book_collecting_facts"
                    )
                    
                    await add_delayed_message(
                        order_id=order_id,
                        user_id=user_id,
                        message_type="book_filling_reminder_2h",
                        content="Каждая история любви уникальна 💕 Твоя история с этим особенным человеком больше ни у кого не повторится. Эти воспоминания, моменты, чувства - они бесценны.",
                        delay_minutes=120,
                        order_step="book_collecting_facts"
                    )
                    
                    await add_delayed_message(
                        order_id=order_id,
                        user_id=user_id,
                        message_type="book_filling_reminder_4h",
                        content="Время летит, а воспоминания остаются навсегда. Не упусти возможность создать что-то особенное для того, кто дорог твоему сердцу.",
                        delay_minutes=240,
                        order_step="book_collecting_facts"
                    )
                    
                    await add_delayed_message(
                        order_id=order_id,
                        user_id=user_id,
                        message_type="book_filling_reminder_8h",
                        content="Персональная книга - это не просто подарок, это частичка твоей души, подаренная тому, кого ты любишь.",
                        delay_minutes=480,
                        order_step="book_collecting_facts"
                    )
                
                logging.info(f"✅ Созданы отложенные сообщения для заказа {order_id}")
                
            except Exception as e:
                logging.error(f"❌ Ошибка создания отложенных сообщений: {e}")

            # Отправляем уведомление менеджеру
            await add_outbox_task(
                order_id=order_id,
                user_id=message.from_user.id,
                type_="manager_notification",
                content=f"Заказ #{order_id}: Пользователь предоставил email. Готов к сбору фактов для песни."
            )

            # Глава 2.8. Анкета для песни — задаём вопросы
            relation = data.get("song_relation", "получателя")
            song_gender = data.get("song_gender", "")

            song_questions = await get_song_questions_for_relation(relation, song_gender)

            # ОТЛАДКА: проверяем что получили
            logging.info(f"🔍 ОТЛАДКА: relation='{relation}', song_gender='{song_gender}'")
            logging.info(f"🔍 ОТЛАДКА: song_questions={song_questions}")

            # Получаем имена для замены
            sender_name = data.get("first_name", "") or data.get("username", "пользователь")
            recipient_name = data.get("song_recipient_name", "получатель")
            
            # Проверяем, что вопросы получены
            if not song_questions:
                logging.error(f"❌ ОШИБКА: song_questions пустой для relation='{relation}', song_gender='{song_gender}'")
                await message.answer("❌ Произошла ошибка при получении вопросов. Попробуйте еще раз.")
                return
            
            # Формируем текст точно как в админ-панели
            intro_text = ""
            
            for question in song_questions:
                # Заменяем имена в тексте
                question_with_names = question.replace("(имя)", sender_name)
                question_with_names = question_with_names.replace("(имя)", recipient_name)
                
                # Добавляем строку как есть (включая пустые строки для абзацев)
                intro_text += f"{question_with_names}\n"
            
            await message.answer(intro_text, parse_mode="HTML")

        else:

            await message.answer("✅ Email сохранен! Теперь мы можем продолжить создание вашей книги.")

            

            # Обновляем статус заказа на следующий этап

            await update_order_status(order_id, "waiting_story_options")
            
            # Создаем таймер для этапа "waiting_story_options"
            from db import create_or_update_user_timer
            product_type = data.get('product', 'Неизвестно')
            user_id = message.from_user.id
            await create_or_update_user_timer(user_id, order_id, "waiting_story_options", product_type)
            logging.info(f"✅ Создан таймер для этапа waiting_story_options, продукт {product_type}, пользователь {user_id}, заказ {order_id}")

            

            # Переходим к ожиданию вариантов сюжетов от менеджера

            await state.set_state(ManagerContentStates.waiting_story_options)

            

            # Отправляем уведомление менеджеру

            await add_outbox_task(

                order_id=order_id,

                user_id=message.from_user.id,

                type_="manager_notification",

                content=f"Заказ #{order_id}: Пользователь предоставил email. Готов к выбору сюжетов."

            )

            

            await message.answer(

                "✨ Уже через несколько минут мы направим тебе подобранные сюжеты, но пока без твоих героев.\n\n"

                "Тебе нужно будет выбрать 24 сюжета, которые вызывают у тебя тёплые эмоции и в которых ты видишь свою историю. Мы уверены, что именно они сделают книгу по-настоящему личной 💖\n\n"

                "Первая и последняя страницы будут с трогательным текстом — мы заметили, что это добавляет особую теплоту.\n\n"

                "После того как ты выберешь сюжеты, наши иллюстраторы добавят твоих героев, которых мы создали ранее. А когда всё будет готово, мы отправим тебе страницы на утверждение. На этом этапе ты сможешь внести изменения в текст и изображения, чтобы всё было именно так, как хочется тебе 🫶🏻"

            )
            
            # Создаем таймер для этапа story_selection (Глава 5: Выбор сюжетов)
            from db import create_or_update_user_timer
            await create_or_update_user_timer(message.from_user.id, order_id, "story_selection", "Книга")
            logging.info(f"✅ Создан таймер для этапа story_selection (Глава 5), пользователь {message.from_user.id}, заказ {order_id}")

        

    except Exception as e:

        logging.error(f"❌ Ошибка в process_email: {e}")

        await message.answer("Произошла ошибка при обработке email. Попробуйте еще раз.")



# Обработка согласия на обработку персональных данных

@dp.callback_query(F.data.in_(["personal_data_consent_yes", "personal_data_consent_no"]))

async def personal_data_consent_handler(callback: types.CallbackQuery, state: FSMContext):

    try:

        data = await state.get_data()

        order_id = data.get('order_id')

        product = data.get('product', 'Книга')

        

        if callback.data == "personal_data_consent_yes":

            # Сохраняем согласие

            await state.update_data(personal_data_consent=True, personal_data_consent_date=datetime.now().isoformat())

            

            # Обновляем данные заказа

            if order_id:

                order_data = data.get('order_data', {})

                order_data.update({

                    'personal_data_consent': True,

                    'personal_data_consent_date': datetime.now().isoformat()

                })

                await update_order_data(order_id, order_data)

            

            await callback.message.edit_text(

                "✅ Спасибо! Ваше согласие получено.\n\n"

                "Оставь, пожалуйста, свой email адрес. 📩 ✨ Это нужно для того, чтобы гарантированно отправить вам все материалы — на случай, если с Телеграмом что-то случится, мы всегда сможем с вами связаться 🩷"

            )

            

            # Определяем следующий шаг в зависимости от продукта

            if product == "Книга":

                # Для книги переходим к запросу email

                await state.set_state(UserDataStates.waiting_email)

            else:

                # Для песни переходим к запросу email

                await state.set_state(UserDataStates.waiting_email)

        

        else:

            # Пользователь не согласился

            await state.update_data(personal_data_consent=False, personal_data_consent_date=datetime.now().isoformat())

            

            # Обновляем данные заказа

            if order_id:

                order_data = data.get('order_data', {})

                order_data.update({

                    'personal_data_consent': False,

                    'personal_data_consent_date': datetime.now().isoformat()

                })

                await update_order_data(order_id, order_data)

            

            await callback.message.edit_text(

                "📋 Понимаем твои опасения — доверие очень важно ❤️\n"

                "Мы храним данные так же бережно, как создаем подарки. ✨ За все годы работы ни одна личная информация не была передана третьим лицам — мы дорожим каждой семьей, которая нам доверяет и репутацией компании 💕\n"

                "Может, все же попробуем создать что-то особенное вместе? Мы гарантируем, что твой подарок тронет до мурашек📖",

                reply_markup=InlineKeyboardMarkup(inline_keyboard=[

                    [InlineKeyboardButton(text="Согласиться и продолжить", callback_data="personal_data_consent_yes")],

                    [InlineKeyboardButton(text="Отменить заказ", callback_data="restart_bot")]

                ])

            )

            

            # Не сбрасываем состояние полностью, а переходим в состояние ожидания

            await state.set_state(UserDataStates.waiting_personal_data_consent)

        

        await callback.answer()

        

    except Exception as e:

        logging.error(f"❌ Ошибка в personal_data_consent_handler: {e}")

        await callback.answer("Произошла ошибка. Попробуйте еще раз.")





# Обработчики для кнопок после отказа от согласия на персональные данные

@dp.callback_query(F.data == "restart_bot")

async def restart_bot_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    # Очищаем состояние и начинаем заново

    await state.clear()

    

    # Показываем приветственное сообщение

    await show_welcome_message(callback.message, state)







@dp.callback_query(F.data == "ask_support")

async def ask_support_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    await callback.message.edit_text(

        "💬 Свяжитесь с нашим менеджером\n\n"

        "Мы понимаем ваши опасения и готовы найти индивидуальное решение!\n\n"

        "📞 Как связаться:\n"

        "• Напишите нам: @BookAI_Support\n"

        "• Email: support@bookai.ru\n"

        "• Телефон: +7 (800) 555-35-35\n\n"

        "🎯 Что обсудим:\n"

        "• Ваши пожелания по конфиденциальности\n"

        "• Альтернативные варианты создания книги\n"

        "• Индивидуальные условия\n\n"

        "Мы обязательно найдем подходящее решение! 🙏"

    )





# После выбора продукта — создаём заказ и сохраняем order_id в state

@dp.callback_query(F.data.in_(["product_book", "product_song"]))

async def product_chosen_callback(callback: types.CallbackQuery, state: FSMContext):

    try:

        # ОТЛАДКА: Проверяем от кого пришел callback

        logging.info(f"🔍 ОТЛАДКА product_chosen_callback: callback.from_user.id={callback.from_user.id}, callback.message.chat.id={callback.message.chat.id}")

        

        await callback.answer()

        data = await state.get_data()

        print(f"🔍 ОТЛАДКА: product_chosen_callback - пользователь {callback.from_user.id} выбрал продукт: {callback.data}")

        print(f"🔍 ОТЛАДКА: Текущий order_id в state: {data.get('order_id')}")

        

        # Трекинг: выбор продукта

        product_type = "Книга" if callback.data == "product_book" else "Песня"

        source = data.get('source', 'Органика')

        await track_event(

            user_id=callback.from_user.id,

            event_type='product_selected',

            event_data={

                'product': product_type,

                'username': callback.from_user.username

            },

            product_type=product_type,

            source=source

        )

        

        if callback.data == "product_book":

            # Используем новую функцию с проверкой имени

            # ИСПРАВЛЕНИЕ: Передаем callback вместо callback.message, чтобы получить правильный user_id

            await start_book_creation_flow(callback, state)

        else:

            # Используем новую функцию с проверкой имени

            # ИСПРАВЛЕНИЕ: Передаем callback вместо callback.message, чтобы получить правильный user_id

            await start_song_creation_flow(callback, state)

        

        await log_state(callback.message, state)

        

    except Exception as e:

        logging.error(f"❌ Ошибка в product_chosen_callback: {e}")

        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

        # Попробуем отправить сообщение об ошибке

        try:

            await callback.message.answer("Произошла ошибка при создании заказа. Попробуйте еще раз или обратитесь в поддержку.")

        except:

            pass



# Обработка выбора пола

@dp.callback_query(F.data.in_(["gender_female", "gender_male"]))

async def gender_chosen_callback(callback: types.CallbackQuery, state: FSMContext):

    try:

        await callback.answer()

        gender = "девушка" if callback.data == "gender_female" else "парень"

        await state.update_data(gender=gender)

        await update_order_progress(state, status="character_created")

        

        # Проверяем, есть ли имя пользователя, и запрашиваем его при необходимости

        data = await state.get_data()

        if not data.get('first_name'):

            await callback.message.edit_text("Поделись, как тебя зовут 💌 Нам важно знать, чтобы обращаться к тебе лично")

            await state.set_state(UserDataStates.waiting_first_name)

            await state.update_data(after_name_input="book_relation")

            await log_state(callback.message, state)

            return

        

        # Если имя есть - переходим к выбору типа связи

        await show_relation_choice(callback.message, state, gender)

        

    except Exception as e:

        logging.error(f"❌ Ошибка в gender_chosen_callback: {e}")

        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

        try:

            await callback.message.answer("Произошла ошибка при сохранении данных. Попробуйте еще раз или обратитесь в поддержку.")

        except:

            pass



async def show_relation_choice(message, state, gender):

    """Показывает выбор типа связи для книги (для callback)"""

    # Кастомизация выбора типа связи

    if gender == "девушка":

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="Мужу", callback_data="rel_to_husband")],

            [InlineKeyboardButton(text="Парню", callback_data="rel_to_boyfriend")],

            [InlineKeyboardButton(text="Маме", callback_data="rel_to_mom")],

            [InlineKeyboardButton(text="Папе", callback_data="rel_to_dad")],

            [InlineKeyboardButton(text="Подруге", callback_data="rel_to_girlfriend")],

            [InlineKeyboardButton(text="Бабушке", callback_data="rel_to_grandma")],

            [InlineKeyboardButton(text="Дедушке", callback_data="rel_to_grandpa")],

            [InlineKeyboardButton(text="Сестре", callback_data="rel_to_sister")],

            [InlineKeyboardButton(text="Брату", callback_data="rel_to_brother")],

            [InlineKeyboardButton(text="Сыну", callback_data="rel_to_son")],

            [InlineKeyboardButton(text="Дочери", callback_data="rel_to_daughter")],

        ])

    else:

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="Жене", callback_data="rel_to_wife")],

            [InlineKeyboardButton(text="Девушке", callback_data="rel_to_girlfriend")],

            [InlineKeyboardButton(text="Маме", callback_data="rel_to_mom")],

            [InlineKeyboardButton(text="Папе", callback_data="rel_to_dad")],

            [InlineKeyboardButton(text="Бабушке", callback_data="rel_to_grandma")],

            [InlineKeyboardButton(text="Дедушке", callback_data="rel_to_grandpa")],

            [InlineKeyboardButton(text="Сестре", callback_data="rel_to_sister")],

            [InlineKeyboardButton(text="Брату", callback_data="rel_to_brother")],

            [InlineKeyboardButton(text="Сыну", callback_data="rel_to_son")],

            [InlineKeyboardButton(text="Дочери", callback_data="rel_to_daughter")],

        ])

    

    await message.edit_text(

        "Каждую книгу мы создаём с любовью и заботой о том, кто будет её читать 💌\nВыбери для кого мы собираем твою книгу воспоминаний:",

        reply_markup=keyboard

    )
    
    # Создаем таймер для этапа book_collecting_facts (Глава 1: Создание заказа книги)
    data = await state.get_data()
    order_id = data.get('order_id')
    if order_id:
        from db import create_or_update_user_timer
        await create_or_update_user_timer(message.from_user.id, order_id, "book_collecting_facts", "Книга")
        logging.info(f"✅ Создан таймер для этапа book_collecting_facts (Глава 1), пользователь {message.from_user.id}, заказ {order_id}")

    await state.set_state(RelationStates.choosing_relation)

    await log_state(message, state)



async def show_relation_choice_after_name(message, state, gender):

    """Показывает выбор типа связи для книги (после ввода имени)"""

    # Кастомизация выбора типа связи

    if gender == "девушка":

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="Мужу", callback_data="rel_to_husband")],

            [InlineKeyboardButton(text="Парню", callback_data="rel_to_boyfriend")],

            [InlineKeyboardButton(text="Маме", callback_data="rel_to_mom")],

            [InlineKeyboardButton(text="Папе", callback_data="rel_to_dad")],

            [InlineKeyboardButton(text="Подруге", callback_data="rel_to_girlfriend")],

            [InlineKeyboardButton(text="Бабушке", callback_data="rel_to_grandma")],

            [InlineKeyboardButton(text="Дедушке", callback_data="rel_to_grandpa")],

            [InlineKeyboardButton(text="Сестре", callback_data="rel_to_sister")],

            [InlineKeyboardButton(text="Брату", callback_data="rel_to_brother")],

            [InlineKeyboardButton(text="Сыну", callback_data="rel_to_son")],

            [InlineKeyboardButton(text="Дочери", callback_data="rel_to_daughter")],

        ])

    else:

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="Жене", callback_data="rel_to_wife")],

            [InlineKeyboardButton(text="Девушке", callback_data="rel_to_girlfriend")],

            [InlineKeyboardButton(text="Маме", callback_data="rel_to_mom")],

            [InlineKeyboardButton(text="Папе", callback_data="rel_to_dad")],

            [InlineKeyboardButton(text="Бабушке", callback_data="rel_to_grandma")],

            [InlineKeyboardButton(text="Дедушке", callback_data="rel_to_grandpa")],

            [InlineKeyboardButton(text="Сестре", callback_data="rel_to_sister")],

            [InlineKeyboardButton(text="Брату", callback_data="rel_to_brother")],

            [InlineKeyboardButton(text="Сыну", callback_data="rel_to_son")],

            [InlineKeyboardButton(text="Дочери", callback_data="rel_to_daughter")],

        ])

    

    await message.answer(

        "Каждую книгу мы создаём с любовью и заботой о том, кто будет её читать 💌\nВыбери для кого мы собираем твою книгу воспоминаний:",

        reply_markup=keyboard

    )
    
    # Создаем таймер для этапа book_collecting_facts (Глава 1: Создание заказа книги)
    data = await state.get_data()
    order_id = data.get('order_id')
    if order_id:
        from db import create_or_update_user_timer
        await create_or_update_user_timer(message.from_user.id, order_id, "book_collecting_facts", "Книга")
        logging.info(f"✅ Создан таймер для этапа book_collecting_facts (Глава 1), пользователь {message.from_user.id}, заказ {order_id}")

    await state.set_state(RelationStates.choosing_relation)

    await log_state(message, state)



# Обработка выбора типа связи (кастомные варианты)

@dp.callback_query(F.data.in_([

    "rel_to_man", "rel_to_mom", "rel_to_dad", "rel_to_girlfriend", "rel_to_grandma",

    "rel_to_woman", "rel_to_grandpa", "rel_to_sister", "rel_to_brother", "rel_to_son", "rel_to_daughter",

    "rel_to_boyfriend", "rel_to_husband", "rel_to_wife"

]))

async def relation_chosen_custom_callback(callback: types.CallbackQuery, state: FSMContext):

    # Получаем пол пользователя для правильного маппинга
    data = await state.get_data()
    gender = data.get('gender', '')

    relations = {

        "rel_to_man": "Любимому",

        "rel_to_mom": "Маме",

        "rel_to_dad": "Папе",

        "rel_to_girlfriend": "Девушке" if gender == "парень" else "Подруге",  # Учитываем пол пользователя

        "rel_to_grandma": "Бабушке",

        "rel_to_woman": "Любимой",

        "rel_to_grandpa": "Дедушке",

        "rel_to_sister": "Сестре",

        "rel_to_brother": "Брату",

        "rel_to_son": "Сыну",

        "rel_to_daughter": "Дочери",

        "rel_to_boyfriend": "Парню",

        "rel_to_husband": "Мужу",

        "rel_to_wife": "Жене"

    }

    relation = relations.get(callback.data, "Неизвестно")

    # Применяем маппинг с учетом пола для правильного сохранения
    def get_mapped_relation_for_save(relation, gender):
        if relation == "Дедушке":
            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Внук - дедушке"
            else:
                return "Внучка - дедушке"
        elif relation == "Бабушке":
            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Внук - бабушке"
            else:
                return "Внучка - бабушке"
        elif relation == "Маме":
            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Сын – маме"
            else:
                return "Дочка- маме"
        elif relation == "Папе":
            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Сын – папе"
            else:
                return "Дочка- папе"
        elif relation == "Сыну":
            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Папа - сыну"
            else:
                return "Мама - сыну"
        elif relation == "Дочке" or relation == "Дочери":
            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Папа - дочке"
            else:
                return "Мама - дочке"
        elif relation == "Брату":
            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Брат - брату"
            else:
                return "Сестра - брату"
        elif relation == "Сестре":
            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Брат – сестре"
            else:
                return "Сестра - сестре"
        elif relation == "Парню":
            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Парень - девушке"
            else:
                return "Девушка - парню"
        elif relation == "Девушке":
            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Парень - девушке"
            else:
                return "Девушка - парню"
        elif relation == "Мужу":
            return "Жена - мужу"
        elif relation == "Жене":
            return "Муж - жене"
        else:
            return relation

    # Применяем маппинг с учетом пола
    mapped_relation = get_mapped_relation_for_save(relation, gender)
    
    await state.update_data(relation=mapped_relation)

    

    # Сохраняем данные в базу

    await update_order_progress(state)

    

    # Сразу переходим к созданию персонажа (пользователя)

    from bot_messages_cache import get_book_intro

    intro_message = await get_book_intro()

    await callback.message.edit_text(intro_message)

    await state.set_state(CharacterStates.intro_text)

    await callback.answer()

    await log_state(callback.message, state)



# Обработка имени получателя

@dp.message(StateFilter(RelationStates.relation_selected))

async def recipient_name_input(message: types.Message, state: FSMContext):

    await state.update_data(recipient_name=message.text)

    # Сохраняем промежуточные данные в БД

    await update_order_progress(state)

    # Получаем сообщение из базы данных

    from bot_messages_cache import get_book_intro

    intro_message = await get_book_intro()

    await message.answer(intro_message)

    await state.set_state(CharacterStates.intro_text)

    await log_state(message, state)



# Изменяем обработчик CharacterStates.intro_text

@dp.message(StateFilter(CharacterStates.intro_text), F.text)

async def save_intro_text(message: types.Message, state: FSMContext):

    # Сохраняем сообщение в историю заказа
    data = await state.get_data()
    order_id = data.get('order_id')
    if order_id:
        from db import add_message_history, create_or_update_order_notification
        await add_message_history(order_id, "user", message.text)
        await create_or_update_order_notification(order_id)
        logging.info(f"✅ СОХРАНЕНО: Сообщение пользователя {message.from_user.id} в историю заказа {order_id}: {message.text[:50]}...")

    await state.update_data(main_hero_intro=message.text)

    # Сохраняем промежуточные данные в БД

    await update_order_progress(state)

    await message.answer("Напиши по какому поводу мы создаём книгу 📔\nИли это просто подарок без повода?")

    await state.set_state(CharacterStates.gift_reason)

    await log_state(message, state)



@dp.message(StateFilter(CharacterStates.intro_text), F.photo)

async def not_text_intro_text(message: types.Message, state: FSMContext):

    await message.answer(

        "❌ <b>Пожалуйста, отправьте текстовое описание</b>\n\n"

        "Нам нужен текст с описанием персонажа: возраст, цвет глаз, особенные детали. "

        "Фотографии мы попросим позже 📝",

        parse_mode="HTML"

    )

    

    await log_state(message, state)



# Исправленный обработчик для этапа выбора события (повода для подарка): ждём только текст

@dp.message(StateFilter(CharacterStates.gift_reason), F.text)

async def save_gift_reason(message: types.Message, state: FSMContext):

    # Сохраняем сообщение пользователя в историю заказа

    await save_user_message_to_history(message, state, "Повод для подарка: ")

    

    await state.update_data(gift_reason=message.text)

    # Сохраняем промежуточные данные в БД

    await update_order_progress(state)

    await message.answer("Отлично, теперь нам нужно твое фото, важно, чтобы на нём хорошо было видно лицо.\nТак иллюстрация получится максимально похожей 💯")

    await state.set_state(PhotoStates.main_face_1)

    await log_state(message, state)



# Если пользователь отправил фото вместо текста на этапе выбора события

@dp.message(StateFilter(CharacterStates.gift_reason), F.photo)

async def photo_instead_of_gift_reason(message: types.Message, state: FSMContext):

    await message.answer("Пожалуйста, сначала напиши по какому поводу мы создаём песню🎶\nИли это просто подарок без повода? А потом отправь фото.")

    await log_state(message, state)



# Первое фото основного героя (лицом)

@dp.message(StateFilter(PhotoStates.main_face_1), F.photo)

async def main_face_1_photo(message: types.Message, state: FSMContext):

    file_id = message.photo[-1].file_id

    data = await state.get_data()

    order_id = data.get('order_id')

    filename = f"order_{order_id}_main_face_1.jpg"

    await download_and_save_photo(message.bot, file_id, "uploads", filename)

    await state.update_data(main_face_1=filename)

    

    # Формируем имя отправителя

    first_name = data.get('first_name', '')

    sender_name = first_name if first_name and first_name != 'None' else 'Друг'

    

    await message.answer(f"Благодарим 🙏🏻\n{sender_name}, отправь ещё одно фото лица, можно с другого ракурса — это сделает иллюстрацию ещё точнее 🎯")

    await state.set_state(PhotoStates.main_face_2)

    await log_state(message, state)



@dp.message(StateFilter(PhotoStates.main_face_1), F.document)

async def main_face_1_document(message: types.Message, state: FSMContext):

    # Проверяем, что это изображение

    if not message.document.mime_type or not message.document.mime_type.startswith('image/'):

        await message.answer(

            "Ой, кажется, вместо фото загрузился другой файл ❌\n"

            "Сейчас нам нужно именно изображение.\n"

            "Пришли, пожалуйста, фотографию 📷",

            parse_mode="HTML"

        )

        return

    

    file_id = message.document.file_id

    data = await state.get_data()

    order_id = data.get('order_id')

    # Сохраняем оригинальное расширение файла

    file_ext = os.path.splitext(message.document.file_name)[1] if message.document.file_name else '.jpg'

    filename = f"order_{order_id}_main_face_1{file_ext}"

    await download_and_save_photo(message.bot, file_id, "uploads", filename)

    await state.update_data(main_face_1=filename)

    

    # Формируем имя отправителя

    first_name = data.get('first_name', '')

    sender_name = first_name if first_name and first_name != 'None' else 'Друг'

    

    await message.answer(f"Благодарим 🙏🏻\n{sender_name}, отправь ещё одно фото лица, можно с другого ракурса — это сделает иллюстрацию ещё точнее 🎯")

    await state.set_state(PhotoStates.main_face_2)

    await log_state(message, state)



@dp.message(StateFilter(PhotoStates.main_face_1), F.text)

async def not_photo_main_face_1(message: types.Message, state: FSMContext):

    # Сохраняем сообщение в историю заказа
    await save_user_message_to_history(message, state, "Текст вместо фото: ")

    await message.answer(

        "Ой, кажется, вместо фото загрузился другой файл ❌\n"

        "Сейчас нам нужно именно изображение.\n"

        "Пришли, пожалуйста, фотографию 📷",

        parse_mode="HTML"

    )

    

    await log_state(message, state)



# Второе фото основного героя (лицом)

@dp.message(StateFilter(PhotoStates.main_face_2), F.photo)

async def main_face_2_photo(message: types.Message, state: FSMContext):

    file_id = message.photo[-1].file_id

    order_id = (await state.get_data()).get('order_id')

    filename = f"order_{order_id}_main_face_2.jpg"

    await download_and_save_photo(message.bot, file_id, "uploads", filename)

    await state.update_data(main_face_2=filename)

    

    await message.answer("Замечательно, мы получили фотографию, теперь нам нужно твое фото в полный рост.")

    await state.set_state(PhotoStates.main_full)

    await log_state(message, state)



@dp.message(StateFilter(PhotoStates.main_face_2), F.document)

async def main_face_2_document(message: types.Message, state: FSMContext):

    # Проверяем, что это изображение

    if not message.document.mime_type or not message.document.mime_type.startswith('image/'):

        await message.answer(

            "Ой, кажется, вместо фото загрузился другой файл ❌\n"

            "Сейчас нам нужно именно изображение.\n"

            "Пришли, пожалуйста, фотографию 📷",

            parse_mode="HTML"

        )

        return

    

    file_id = message.document.file_id

    order_id = (await state.get_data()).get('order_id')

    # Сохраняем оригинальное расширение файла

    file_ext = os.path.splitext(message.document.file_name)[1] if message.document.file_name else '.jpg'

    filename = f"order_{order_id}_main_face_2{file_ext}"

    await download_and_save_photo(message.bot, file_id, "uploads", filename)

    await state.update_data(main_face_2=filename)

    

    await message.answer("Замечательно, мы получили фотографию, теперь нам нужно твое фото в полный рост.")

    await state.set_state(PhotoStates.main_full)

    await log_state(message, state)



@dp.message(StateFilter(PhotoStates.main_face_2), F.text)

async def not_photo_main_face_2(message: types.Message, state: FSMContext):

    # Сохраняем сообщение в историю заказа
    await save_user_message_to_history(message, state, "Текст вместо фото: ")

    await message.answer(

        "Ой, кажется, вместо фото загрузился другой файл ❌\n"

        "Сейчас нам нужно именно изображение.\n"

        "Пришли, пожалуйста, фотографию 📷",

        parse_mode="HTML"

    )

    

    await log_state(message, state)



# Фото основного героя в полный рост

@dp.message(StateFilter(PhotoStates.main_full), F.photo)

async def main_full_photo(message: types.Message, state: FSMContext):

    try:

        logging.info(f"📸 Получено третье фото основного героя от пользователя {message.from_user.id}")

        

        file_id = message.photo[-1].file_id

        order_id = (await state.get_data()).get('order_id')

        filename = f"order_{order_id}_main_full.jpg"

        

        logging.info(f"💾 Сохраняем фото: {filename}")

        await download_and_save_photo(message.bot, file_id, "uploads", filename)

        await state.update_data(main_full=filename)

        

        logging.info(f"📊 Обновляем прогресс заказа {order_id}")

        await update_order_progress(state, status="character_created")

        

        # Автоматически переходим к добавлению второго героя

        logging.info(f"🔄 Автоматически переходим к добавлению второго героя для пользователя {message.from_user.id}")

        await message.answer("Переходим к следующему шагу:\n"

                            "Мы собрали информацию о тебе.\n"

                            "Теперь давай заполним данные о том самом особенном человеке, для которого мы создаём книгу ❤️")

        await message.answer("Напиши имя того, кому будет посвящена твоя книга 💌\n"

                            "Оно станет главным на её страницах и прозвучит особенно тепло.")

        await state.set_state(CharacterStates.hero_name)

        

        logging.info(f"✅ Успешно обработано третье фото для заказа {order_id}")

        await log_state(message, state)

        

    except Exception as e:

        logging.error(f"❌ Ошибка в main_full_photo: {e}")

        await message.answer("Произошла ошибка при обработке фото. Попробуйте еще раз или обратитесь в поддержку.")

        await log_state(message, state)



@dp.message(StateFilter(PhotoStates.main_full), F.document)

async def main_full_document(message: types.Message, state: FSMContext):

    try:

        # Проверяем, что это изображение

        if not message.document.mime_type or not message.document.mime_type.startswith('image/'):

            await message.answer(

                "Ой, кажется, вместо фото загрузился другой файл ❌\n"

                "Сейчас нам нужно именно изображение.\n"

                "Пришли, пожалуйста, фотографию 📷",

                parse_mode="HTML"

            )

            return

        

        logging.info(f"📸 Получено третье фото основного героя (как файл) от пользователя {message.from_user.id}")

        

        file_id = message.document.file_id

        order_id = (await state.get_data()).get('order_id')

        # Сохраняем оригинальное расширение файла

        file_ext = os.path.splitext(message.document.file_name)[1] if message.document.file_name else '.jpg'

        filename = f"order_{order_id}_main_full{file_ext}"

        

        logging.info(f"💾 Сохраняем фото в оригинальном качестве: {filename}")

        await download_and_save_photo(message.bot, file_id, "uploads", filename)

        await state.update_data(main_full=filename)

        

        logging.info(f"📊 Обновляем прогресс заказа {order_id}")

        await update_order_progress(state, status="character_created")

        

        # Автоматически переходим к добавлению второго героя

        logging.info(f"🔄 Автоматически переходим к добавлению второго героя для пользователя {message.from_user.id}")

        await message.answer("Переходим к следующему шагу:\n"

                            "Мы собрали информацию о тебе.\n"

                            "Теперь давай заполним данные о том самом особенном человеке, для которого мы создаём книгу ❤️")

        await message.answer("Напиши имя того, кому будет посвящена твоя книга 💌\n"

                            "Оно станет главным на её страницах и прозвучит особенно тепло.")

        await state.set_state(CharacterStates.hero_name)

        

        logging.info(f"✅ Успешно обработано третье фото для заказа {order_id}")

        await log_state(message, state)

        

    except Exception as e:

        logging.error(f"❌ Ошибка в main_full_document: {e}")

        await message.answer("Произошла ошибка при обработке фото. Попробуйте еще раз или обратитесь в поддержку.")

        await log_state(message, state)



@dp.message(StateFilter(PhotoStates.main_full), F.text)

async def not_photo_main_full(message: types.Message, state: FSMContext):

    # Сохраняем сообщение в историю заказа
    await save_user_message_to_history(message, state, "Текст вместо фото: ")

    await message.answer(

        "Ой, кажется, вместо фото загрузился другой файл ❌\n"

        "Сейчас нам нужно именно изображение.\n"

        "Пришли, пожалуйста, фотографию 📷",

        parse_mode="HTML"

    )

    

    await log_state(message, state)



# Универсальный обработчик фотографий для отладки

@dp.message(F.photo)

async def universal_photo_handler(message: types.Message, state: FSMContext):

    """Универсальный обработчик фотографий для отладки"""

    try:

        current_state = await state.get_state()

        logging.info(f"📸 Универсальный обработчик: получено фото от пользователя {message.from_user.id}, состояние: {current_state}")

        

        # Если мы в состоянии ожидания третьего фото основного героя, обрабатываем его

        if current_state == "PhotoStates:main_full":

            logging.info(f"🔄 Перенаправляем фото в main_full_photo для пользователя {message.from_user.id}")

            await main_full_photo(message, state)

        # Если мы в состоянии ожидания фото второго героя, передаем специальным обработчикам

        elif current_state == "PhotoStates:hero_face_1":

            logging.info(f"🔄 Перенаправляем фото в hero_face_1_photo для пользователя {message.from_user.id}")

            await hero_face_1_photo(message, state)

        elif current_state == "PhotoStates:hero_face_2":

            logging.info(f"🔄 Перенаправляем фото в hero_face_2_photo для пользователя {message.from_user.id}")

            await hero_face_2_photo(message, state)

        elif current_state == "PhotoStates:hero_full":

            logging.info(f"🔄 Перенаправляем фото в hero_full_photo для пользователя {message.from_user.id}")

            await hero_full_photo(message, state)

        elif current_state == "PhotoStates:main_face_1":

            logging.info(f"🔄 Перенаправляем фото в main_face_1_photo для пользователя {message.from_user.id}")

            await main_face_1_photo(message, state)

        elif current_state == "PhotoStates:main_face_2":

            logging.info(f"🔄 Перенаправляем фото в main_face_2_photo для пользователя {message.from_user.id}")

            await main_face_2_photo(message, state)

        elif current_state == "PhotoStates:joint_photo":

            logging.info(f"🔄 Перенаправляем фото в joint_photo_handler для пользователя {message.from_user.id}")

            await joint_photo_handler(message, state)

        elif current_state == "AdditionsStates:uploading_photos":

            logging.info(f"🔄 Перенаправляем фото в upload_custom_photo для пользователя {message.from_user.id}")

            await upload_custom_photo(message, state)

        elif current_state == "BookFinalStates:uploading_custom_photos":

            # Проверяем, является ли это медиа-группой

            if message.media_group_id:

                logging.info(f"🔄 Перенаправляем медиа-группу в handle_media_group_custom_photos для пользователя {message.from_user.id}")

                await handle_media_group_custom_photos(message, state)

            else:

                logging.info(f"🔄 Перенаправляем фото в upload_custom_photo_book_final для пользователя {message.from_user.id}")

                await upload_custom_photo_book_final(message, state)

        elif current_state == "BookFinalStates:uploading_first_last_photos":

            logging.info(f"🔄 Перенаправляем фото в handle_first_last_photo_upload для пользователя {message.from_user.id}")

            await handle_first_last_photo_upload(message, state)

        elif current_state == "BookFinalStates:uploading_first_page_photo":

            logging.info(f"🔄 Перенаправляем фото в handle_first_page_photo_upload для пользователя {message.from_user.id}")

            await handle_first_page_photo_upload(message, state)

        elif current_state == "BookFinalStates:uploading_last_page_photo":

            logging.info(f"🔄 Перенаправляем фото в handle_last_page_photo_upload для пользователя {message.from_user.id}")

            await handle_last_page_photo_upload(message, state)

        elif current_state == "SongRelationStates:waiting_recipient_name":

            logging.info(f"📸 Фото получено в состоянии ожидания имени получателя, игнорируем")

            await message.answer("Напиши имя того кому будет посвящена твоя песня 🎵\nОно станет главным, и песня прозвучит особенно тепло ❤️\nТекстом, а не фотографией.")

        elif current_state == "SongRelationStates:waiting_gift_reason":

            logging.info(f"📸 Фото получено в состоянии ожидания повода подарка, игнорируем")

            await message.answer("Пожалуйста, напиши по какому поводу мы создаём песню🎶\nИли это просто подарок без повода? Текстом, а не фотографией.")

        else:

            logging.info(f"📸 Фото получено в состоянии {current_state}, но нет специального обработчика")

            await message.answer("Фото получено, но сейчас не ожидается загрузка фотографий.")

            

    except Exception as e:

        logging.error(f"❌ Ошибка в universal_photo_handler: {e}")

        await message.answer("Произошла ошибка при обработке фото. Попробуйте еще раз.")



# Новый герой: имя

@dp.callback_query(F.data == "add_hero")

async def add_hero(callback: types.CallbackQuery, state: FSMContext):

    await callback.message.edit_text("Напиши имя того кому будет посвящена твоя книга 💌\n"

                                   "Оно станет главным на её страницах и прозвучит особенно тепло")

    await state.set_state(CharacterStates.hero_name)

    await callback.answer()

    await log_state(callback.message, state)



# Пропустить добавление героя и продолжить

@dp.callback_query(F.data == "skip_add_hero")

async def skip_add_hero(callback: types.CallbackQuery, state: FSMContext):

    try:

        logging.info(f"🔘 Кнопка 'Пропустить и продолжить' нажата пользователем {callback.from_user.id}")

        await callback.answer()

        

        # Получаем стили из базы данных

        from db import get_book_styles

        styles = await get_book_styles()

        

        if styles:

            # Отправляем заголовок

            header_text = "🎨 <b>Выберите стиль вашей книги:</b>\n\n"

            await callback.message.edit_text(header_text, parse_mode="HTML")

            

            # Отправляем каждый стиль отдельным сообщением с фото

            for i, style in enumerate(styles):

                photo_path = f"styles/{style['filename']}"

                caption = f"<b>{i+1}. {style['name']}</b>\n{style['description']}"

                

                if os.path.exists(photo_path):

                    await callback.message.answer_photo(

                        types.FSInputFile(photo_path),

                        caption=caption,

                        parse_mode="HTML"

                    )

                else:

                    # Если фото нет, отправляем только текст

                    await callback.message.answer(caption, parse_mode="HTML")

            

            # Отправляем кнопки выбора в последнем сообщении

            keyboard = InlineKeyboardMarkup(inline_keyboard=[

                [InlineKeyboardButton(

                    text=style['name'] if '—' in style['name'] else f"{style['name']} {'🏡 — будет позже' if 'Ghibli' in style['name'] else '👩‍❤️‍👨 — будет позже' if 'Love' in style['name'] else ''}",

                    callback_data="style_pixar" if 'Pixar' in style['name'] else "style_ghibli_placeholder" if 'Ghibli' in style['name'] else "style_loveis_placeholder" if 'Love' in style['name'] else f"style_{style['id']}"

                )]

                for style in styles

            ])

            

            await callback.message.answer(

                "Выберите стиль:",

                reply_markup=keyboard

            )

        else:

            # Fallback на старые стили, если в базе нет

            keyboard = InlineKeyboardMarkup(inline_keyboard=[

                [InlineKeyboardButton(text="Pixar 🌈", callback_data="style_pixar")],

                [InlineKeyboardButton(text="Ghibli 🏡", callback_data="style_ghibli_placeholder")],

                [InlineKeyboardButton(text="Love is 👩‍❤️‍👨", callback_data="style_loveis_placeholder")],

            ])

            

            await callback.message.edit_text(

                "Отлично! Теперь выберите стиль вашей книги:",

                reply_markup=keyboard

            )

        

        await state.set_state(CoverStates.choosing_style)

        

        logging.info(f"✅ Успешно перешли к выбору стиля для пользователя {callback.from_user.id}")

        await log_state(callback.message, state)

        

    except Exception as e:

        logging.error(f"❌ Ошибка в skip_add_hero: {e}")

        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

        await log_state(callback.message, state)



# Новый герой: фото лицом 1

@dp.message(StateFilter(CharacterStates.hero_name))

async def save_hero_name(message: types.Message, state: FSMContext):

    await state.update_data(current_hero_name=message.text, current_hero_photos=[])
    
    # Отладка: проверяем, что имя героя сохранилось
    data = await state.get_data()
    logging.info(f"🔍 ОТЛАДКА save_hero_name: current_hero_name={data.get('current_hero_name')}, first_name={data.get('first_name')}")

    # Сохраняем промежуточные данные в БД
    await update_order_progress(state)

    await message.answer(f"Нам важно узнать чуть больше о том, кому будет посвящена книга ❤️\n"

                        f"Чтобы персонаж был максимально похож, расскажи: сколько ему лет, какого цвета у него глаза и есть ли особенные детали, которые важно указать 🩷\n"

                        f"Эти детали помогут художнику передать его уникальность на страницах книги 💞")

    await state.set_state(CharacterStates.hero_intro)

    await log_state(message, state)



@dp.message(StateFilter(CharacterStates.hero_intro), F.text)

async def save_hero_intro(message: types.Message, state: FSMContext):

    # Сохраняем сообщение в историю заказа
    data = await state.get_data()
    order_id = data.get('order_id')
    if order_id:
        from db import add_message_history, create_or_update_order_notification
        await add_message_history(order_id, "user", message.text)
        await create_or_update_order_notification(order_id)
        logging.info(f"✅ СОХРАНЕНО: Сообщение пользователя {message.from_user.id} в историю заказа {order_id}: {message.text[:50]}...")

    await state.update_data(current_hero_intro=message.text)

    hero_name = (await state.get_data()).get('current_hero_name')

    await message.answer(f"Нам нужно его фото, чтобы на нём хорошо было видно лицо  📷\n"

                        f"Благодаря этому книга получится по-настоящему личной и трогательной 🥹")

    await state.set_state(PhotoStates.hero_face_1)

    await log_state(message, state)



@dp.message(StateFilter(CharacterStates.hero_intro), F.photo)

async def not_text_hero_intro(message: types.Message, state: FSMContext):

    await message.answer(

        "❌ <b>Пожалуйста, отправьте текстовое описание</b>\n\n"

        "Нам нужен текст с описанием персонажа: возраст, цвет глаз, особенные детали. "

        "Фотографии мы попросим позже 📝",

        parse_mode="HTML"

    )

    

    await log_state(message, state)



@dp.message(StateFilter(PhotoStates.hero_face_1), F.photo)

async def hero_face_1_photo(message: types.Message, state: FSMContext):

    try:

        logging.info(f"📸 Специальный обработчик hero_face_1_photo сработал для пользователя {message.from_user.id}")

        

        file_id = message.photo[-1].file_id

        order_id = (await state.get_data()).get('order_id')

        hero_name = (await state.get_data()).get('current_hero_name', 'hero')

        filename = f"order_{order_id}_{hero_name}_face_1.jpg"

        

        logging.info(f"💾 Сохраняем фото второго героя: {filename}")

        await download_and_save_photo(message.bot, file_id, "uploads", filename)

        await state.update_data(hero_face_1=filename)

        

        # Сохраняем в базу данных

        from db import save_hero_photo

        await save_hero_photo(order_id, filename, "face_1", hero_name)

        

        logging.info(f"✅ Фото второго героя сохранено, переходим к следующему")

        logging.info(f"🔍 ОТЛАДКА: Переходим к состоянию PhotoStates.hero_face_2")

        await message.answer("Спасибо! 🙏\n"

                            "Отправь, пожалуйста, ещё одно фото второго персонажа, на котором хорошо видно лицо, но с другого ракурса 🙂\n"

                            "Так мы сможем уловить все детали и сделать иллюстрацию максимально похожей 🪞")

        await state.set_state(PhotoStates.hero_face_2)

        logging.info(f"🔍 ОТЛАДКА: Состояние установлено, вызываем log_state")

        await log_state(message, state)

        logging.info(f"🔍 ОТЛАДКА: Обработчик hero_face_1_photo завершен")

        

    except Exception as e:

        logging.error(f"❌ Ошибка в hero_face_1_photo: {e}")

        import traceback

        traceback.print_exc()

        await message.answer("Произошла ошибка при обработке фото. Попробуйте еще раз.")

        await log_state(message, state)



@dp.message(StateFilter(PhotoStates.hero_face_1), F.document)

async def hero_face_1_document(message: types.Message, state: FSMContext):

    try:

        # Проверяем, что это изображение

        if not message.document.mime_type or not message.document.mime_type.startswith('image/'):

            await message.answer(

                "Ой, кажется, вместо фото загрузился другой файл ❌\n"

                "Сейчас нам нужно именно изображение.\n"

                "Пришли, пожалуйста, фотографию 📷",

                parse_mode="HTML"

            )

            return

        

        logging.info(f"📸 Специальный обработчик hero_face_1_document сработал для пользователя {message.from_user.id}")

        

        file_id = message.document.file_id

        order_id = (await state.get_data()).get('order_id')

        hero_name = (await state.get_data()).get('current_hero_name', 'hero')

        # Сохраняем оригинальное расширение файла

        file_ext = os.path.splitext(message.document.file_name)[1] if message.document.file_name else '.jpg'

        filename = f"order_{order_id}_{hero_name}_face_1{file_ext}"

        

        logging.info(f"💾 Сохраняем фото второго героя: {filename}")

        await download_and_save_photo(message.bot, file_id, "uploads", filename)

        await state.update_data(hero_face_1=filename)

        

        # Сохраняем в базу данных

        from db import save_hero_photo

        await save_hero_photo(order_id, filename, "face_1", hero_name)

        

        logging.info(f"✅ Фото второго героя сохранено, переходим к следующему")

        logging.info(f"🔍 ОТЛАДКА: Переходим к состоянию PhotoStates.hero_face_2")

        await message.answer("Спасибо! 🙏\n"

                            "Отправь, пожалуйста, ещё одно фото второго персонажа, на котором хорошо видно лицо, но с другого ракурса 🙂\n"

                            "Так мы сможем уловить все детали и сделать иллюстрацию максимально похожей 🪞")

        await state.set_state(PhotoStates.hero_face_2)

        logging.info(f"🔍 ОТЛАДКА: Состояние установлено, вызываем log_state")

        await log_state(message, state)

        logging.info(f"🔍 ОТЛАДКА: Обработчик hero_face_1_photo завершен")

        

    except Exception as e:

        logging.error(f"❌ Ошибка в hero_face_1_photo: {e}")

        import traceback

        traceback.print_exc()

        await message.answer("Произошла ошибка при обработке фото. Попробуйте еще раз.")

        await log_state(message, state)



@dp.message(StateFilter(PhotoStates.hero_face_1), F.text)

async def not_photo_hero_face_1(message: types.Message, state: FSMContext):

    # Сохраняем сообщение в историю заказа
    await save_user_message_to_history(message, state, "Текст вместо фото: ")

    await message.answer(

        "Ой, кажется, вместо фото загрузился другой файл ❌\n"

        "Сейчас нам нужно именно изображение.\n"

        "Пришли, пожалуйста, фотографию 📷",

        parse_mode="HTML"

    )

    

    await log_state(message, state)



# Обработчик для всех остальных типов сообщений в состоянии hero_face_1 (перемещен ниже)

@dp.message(StateFilter(PhotoStates.hero_face_1))

async def any_message_hero_face_1(message: types.Message, state: FSMContext):

    # Определяем тип контента

    content_type = "неизвестный тип"

    if message.video:

        content_type = "видео"

    elif message.animation:

        content_type = "GIF/анимация"

    elif message.sticker:

        content_type = "стикер"

    elif message.voice:

        content_type = "голосовое сообщение"

    elif message.video_note:

        content_type = "кружок"

    elif message.document:

        content_type = "документ"

    elif message.audio:

        content_type = "аудио"

    elif message.text:

        content_type = "текст"

    

    logging.warning(f"⚠️ Неподдерживаемый контент: {content_type} от пользователя {message.from_user.id} в состоянии hero_face_1")

    

    # Отправляем понятное сообщение пользователю

    await message.answer(

        "Ой, кажется, вместо фото загрузился другой файл ❌\n"

        "Сейчас нам нужно именно изображение.\n"

        "Пришли, пожалуйста, фотографию 📷",

        parse_mode="HTML"

    )

    

    await log_state(message, state)



# Фото героя (лицом 2)

@dp.message(StateFilter(PhotoStates.hero_face_2), F.photo)

async def hero_face_2_photo(message: types.Message, state: FSMContext):

    try:

        logging.info(f"📸 Обработчик hero_face_2_photo сработал для пользователя {message.from_user.id}")

        

        file_id = message.photo[-1].file_id

        order_id = (await state.get_data()).get('order_id')

        hero_name = (await state.get_data()).get('current_hero_name', 'hero')

        filename = f"order_{order_id}_{hero_name}_face_2.jpg"

        

        logging.info(f"💾 Сохраняем второе фото героя: {filename}")

        await download_and_save_photo(message.bot, file_id, "uploads", filename)

        await state.update_data(hero_face_2=filename)

        

        # Сохраняем в базу данных

        from db import save_hero_photo

        await save_hero_photo(order_id, filename, "face_2", hero_name)

        

        logging.info(f"✅ Второе фото героя сохранено, переходим к фото в полный рост")

        await message.answer(f"Отлично!\n"

                            f"Теперь нам нужно фото в полный рост 🌿\n"

                            f"Это поможет нам правильно изобразить второго героя в иллюстрациях.")

        await state.set_state(PhotoStates.hero_full)

        await log_state(message, state)

        

    except Exception as e:

        logging.error(f"❌ Ошибка в hero_face_2_photo: {e}")

        import traceback

        traceback.print_exc()

        await message.answer("Произошла ошибка при обработке фото. Попробуйте еще раз.")

        await log_state(message, state)



@dp.message(StateFilter(PhotoStates.hero_face_2), F.document)

async def hero_face_2_document(message: types.Message, state: FSMContext):

    try:

        # Проверяем, что это изображение

        if not message.document.mime_type or not message.document.mime_type.startswith('image/'):

            await message.answer(

                "Ой, кажется, вместо фото загрузился другой файл ❌\n"

                "Сейчас нам нужно именно изображение.\n"

                "Пришли, пожалуйста, фотографию 📷",

                parse_mode="HTML"

            )

            return

        

        logging.info(f"📸 Обработчик hero_face_2_document сработал для пользователя {message.from_user.id}")

        

        file_id = message.document.file_id

        order_id = (await state.get_data()).get('order_id')

        hero_name = (await state.get_data()).get('current_hero_name', 'hero')

        # Сохраняем оригинальное расширение файла

        file_ext = os.path.splitext(message.document.file_name)[1] if message.document.file_name else '.jpg'

        filename = f"order_{order_id}_{hero_name}_face_2{file_ext}"

        

        logging.info(f"💾 Сохраняем второе фото героя в оригинальном качестве: {filename}")

        await download_and_save_photo(message.bot, file_id, "uploads", filename)

        await state.update_data(hero_face_2=filename)

        

        # Сохраняем в базу данных

        from db import save_hero_photo

        await save_hero_photo(order_id, filename, "face_2", hero_name)

        

        logging.info(f"✅ Второе фото героя сохранено, переходим к фото в полный рост")

        await message.answer(f"Отлично!\n"

                            f"Теперь нам нужно фото в полный рост 🌿\n"

                            f"Это поможет нам правильно изобразить второго героя в иллюстрациях.")

        await state.set_state(PhotoStates.hero_full)

        await log_state(message, state)

        

    except Exception as e:

        logging.error(f"❌ Ошибка в hero_face_2_document: {e}")

        import traceback

        traceback.print_exc()

        await message.answer("Произошла ошибка при обработке фото. Попробуйте еще раз.")

        await log_state(message, state)





@dp.message(StateFilter(PhotoStates.hero_face_2), F.text)

async def not_photo_hero_face_2(message: types.Message, state: FSMContext):

    # Сохраняем сообщение в историю заказа
    await save_user_message_to_history(message, state, "Текст вместо фото: ")

    await message.answer(

        "Ой, кажется, вместо фото загрузился другой файл ❌\n"

        "Сейчас нам нужно именно изображение.\n"

        "Пришли, пожалуйста, фотографию 📷",

        parse_mode="HTML"

    )

    

    await log_state(message, state)



# Обработчик для всех остальных типов сообщений в состоянии hero_face_2

@dp.message(StateFilter(PhotoStates.hero_face_2))

async def any_message_hero_face_2(message: types.Message, state: FSMContext):

    # Определяем тип контента

    content_type = "неизвестный тип"

    if message.video:

        content_type = "видео"

    elif message.animation:

        content_type = "GIF/анимация"

    elif message.sticker:

        content_type = "стикер"

    elif message.voice:

        content_type = "голосовое сообщение"

    elif message.video_note:

        content_type = "кружок"

    elif message.document:

        content_type = "документ"

    elif message.audio:

        content_type = "аудио"

    elif message.text:

        content_type = "текст"

    

    logging.warning(f"⚠️ Неподдерживаемый контент: {content_type} от пользователя {message.from_user.id} в состоянии hero_face_2")

    

    # Отправляем понятное сообщение пользователю

    await message.answer(

        "Ой, кажется, вместо фото загрузился другой файл ❌\n"

        "Сейчас нам нужно именно изображение.\n"

        "Пришли, пожалуйста, фотографию 📷",

        parse_mode="HTML"

    )

    

    await log_state(message, state)



# Фото героя в полный рост

@dp.message(StateFilter(PhotoStates.hero_full), F.photo)

async def hero_full_photo(message: types.Message, state: FSMContext):

    try:

        logging.info(f"📸 Обработчик hero_full_photo сработал для пользователя {message.from_user.id}")

        

        file_id = message.photo[-1].file_id

        order_id = (await state.get_data()).get('order_id')

        hero_name = (await state.get_data()).get('current_hero_name', 'hero')

        filename = f"order_{order_id}_{hero_name}_full.jpg"

        

        logging.info(f"💾 Сохраняем фото героя в полный рост: {filename}")

        await download_and_save_photo(message.bot, file_id, "uploads", filename)

        

        # Сохраняем в базу данных

        from db import save_hero_photo

        await save_hero_photo(order_id, filename, "full", hero_name)

        

        data = await state.get_data()

        hero = {

            'name': data.get('current_hero_name'),

            'intro': data.get('current_hero_intro'),

            'face_1': data.get('hero_face_1'),

            'face_2': data.get('hero_face_2'),

            'full': filename

        }

        all_heroes = data.get('other_heroes', [])

        all_heroes.append(hero)

        # Сохраняем имя текущего героя как получателя перед обнулением
        current_hero_name = data.get('current_hero_name')
        await state.update_data(
            other_heroes=all_heroes, 
            recipient_name=current_hero_name,  # Сохраняем имя как получателя
            current_hero_name=None, 
            current_hero_intro=None, 
            hero_face_1=None, 
            hero_face_2=None
        )

        

        logging.info(f"✅ Фото героя в полный рост сохранено, переходим к совместному фото")

        # Переходим к совместному фото

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="У нас нет совместного фото", callback_data="skip_joint_photo")]

        ])

        await message.answer("Какие вы красивые!\n"

                            "Если у вас есть совместно фото, которое ты готов нам отправить, пришли его нам", reply_markup=keyboard)

        await state.set_state(PhotoStates.joint_photo)

        await log_state(message, state)

        

    except Exception as e:

        logging.error(f"❌ Ошибка в hero_full_photo: {e}")

        import traceback

        traceback.print_exc()

        await message.answer("Произошла ошибка при обработке фото. Попробуйте еще раз.")

        await log_state(message, state)



@dp.message(StateFilter(PhotoStates.hero_full), F.document)

async def hero_full_document(message: types.Message, state: FSMContext):

    try:

        # Проверяем, что это изображение

        if not message.document.mime_type or not message.document.mime_type.startswith('image/'):

            await message.answer(

                "Ой, кажется, вместо фото загрузился другой файл ❌\n"

                "Сейчас нам нужно именно изображение.\n"

                "Пришли, пожалуйста, фотографию 📷",

                parse_mode="HTML"

            )

            return

        

        logging.info(f"📸 Обработчик hero_full_document сработал для пользователя {message.from_user.id}")

        

        file_id = message.document.file_id

        order_id = (await state.get_data()).get('order_id')

        hero_name = (await state.get_data()).get('current_hero_name', 'hero')

        # Сохраняем оригинальное расширение файла

        file_ext = os.path.splitext(message.document.file_name)[1] if message.document.file_name else '.jpg'

        filename = f"order_{order_id}_{hero_name}_full{file_ext}"

        

        logging.info(f"💾 Сохраняем фото героя в полный рост в оригинальном качестве: {filename}")

        await download_and_save_photo(message.bot, file_id, "uploads", filename)

        

        # Сохраняем в базу данных

        from db import save_hero_photo

        await save_hero_photo(order_id, filename, "full", hero_name)

        

        data = await state.get_data()

        hero = {

            'name': data.get('current_hero_name'),

            'intro': data.get('current_hero_intro'),

            'face_1': data.get('hero_face_1'),

            'face_2': data.get('hero_face_2'),

            'full': filename

        }

        all_heroes = data.get('other_heroes', [])

        all_heroes.append(hero)

        # Сохраняем имя текущего героя как получателя перед обнулением
        current_hero_name = data.get('current_hero_name')
        await state.update_data(
            other_heroes=all_heroes, 
            recipient_name=current_hero_name,  # Сохраняем имя как получателя
            current_hero_name=None, 
            current_hero_intro=None, 
            hero_face_1=None, 
            hero_face_2=None
        )

        

        logging.info(f"✅ Фото героя в полный рост сохранено, переходим к совместному фото")

        # Переходим к совместному фото

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="У нас нет совместного фото", callback_data="skip_joint_photo")]

        ])

        await message.answer("Какие вы красивые!\n"

                            "Если у вас есть совместно фото, которое ты готов нам отправить, пришли его нам", reply_markup=keyboard)

        await state.set_state(PhotoStates.joint_photo)

        await log_state(message, state)

        

    except Exception as e:

        logging.error(f"❌ Ошибка в hero_full_document: {e}")

        import traceback

        traceback.print_exc()

        await message.answer("Произошла ошибка при обработке фото. Попробуйте еще раз.")

        await log_state(message, state)



@dp.message(StateFilter(PhotoStates.hero_full), F.text)

async def not_photo_hero_full(message: types.Message, state: FSMContext):

    # Сохраняем сообщение в историю заказа
    await save_user_message_to_history(message, state, "Текст вместо фото: ")

    await message.answer(

        "Ой, кажется, вместо фото загрузился другой файл ❌\n"

        "Сейчас нам нужно именно изображение.\n"

        "Пришли, пожалуйста, фотографию 📷",

        parse_mode="HTML"

    )

    

    await log_state(message, state)



# Эта функция больше не нужна, так как мы убрали кнопку "Далее"

# @dp.callback_query(F.data == "no_more_heroes")

# async def finish_characters(callback: types.CallbackQuery, state: FSMContext):

#     data = await state.get_data()

#     if data.get('other_heroes'):

#         await callback.message.edit_text("Пожалуйста, отправьте совместное фото всех героев:")

#         await state.set_state(PhotoStates.joint_photo)

#     else:

#         # Если других героев нет — сразу к следующему этапу

#         await finish_photos(callback, state)

#     await callback.answer()

#     await log_state(callback.message, state)



# Совместное фото

@dp.message(StateFilter(PhotoStates.joint_photo), F.photo)

async def joint_photo_handler(message: types.Message, state: FSMContext):

    file_id = message.photo[-1].file_id

    order_id = (await state.get_data()).get('order_id')

    filename = f"order_{order_id}_joint_photo.jpg"

    await download_and_save_photo(message.bot, file_id, "uploads", filename)

    await state.update_data(joint_photo=filename)

    

    # Сохраняем в базу данных

    from db import save_joint_photo

    await save_joint_photo(order_id, filename)

    

    await finish_photos(message, state)

    await log_state(message, state)



@dp.message(StateFilter(PhotoStates.joint_photo), F.document)

async def joint_photo_document(message: types.Message, state: FSMContext):

    # Проверяем, что это изображение

    if not message.document.mime_type or not message.document.mime_type.startswith('image/'):

        await message.answer(

            "Ой, кажется, вместо фото загрузился другой файл ❌\n"

            "Сейчас нам нужно именно изображение.\n"

            "Пришли, пожалуйста, фотографию 📷",

            parse_mode="HTML"

        )

        return

    

    file_id = message.document.file_id

    order_id = (await state.get_data()).get('order_id')

    # Сохраняем оригинальное расширение файла

    file_ext = os.path.splitext(message.document.file_name)[1] if message.document.file_name else '.jpg'

    filename = f"order_{order_id}_joint_photo{file_ext}"

    await download_and_save_photo(message.bot, file_id, "uploads", filename)

    await state.update_data(joint_photo=filename)

    

    # Сохраняем в базу данных

    from db import save_joint_photo

    await save_joint_photo(order_id, filename)

    

    await finish_photos(message, state)

    await log_state(message, state)



@dp.message(StateFilter(PhotoStates.joint_photo), F.text)

async def not_photo_joint(message: types.Message, state: FSMContext):

    # Сохраняем сообщение в историю заказа
    await save_user_message_to_history(message, state, "Текст вместо фото: ")

    await message.answer(

        "Ой, кажется, вместо фото загрузился другой файл ❌\n"

        "Сейчас нам нужно именно изображение.\n"

        "Пришли, пожалуйста, фотографию 📷",

        parse_mode="HTML"

    )

    

    await log_state(message, state)



# Пропустить совместное фото и продолжить

@dp.callback_query(F.data == "skip_joint_photo")

async def skip_joint_photo(callback: types.CallbackQuery, state: FSMContext):

    try:

        logging.info(f"🔘 Кнопка 'Пропустить и продолжить' для совместного фото нажата пользователем {callback.from_user.id}")

        await callback.answer()

        

        # Переходим к следующему этапу - выбор стиля

        await finish_photos(callback, state)

        

        logging.info(f"✅ Успешно пропустили совместное фото для пользователя {callback.from_user.id}")

        

    except Exception as e:

        logging.error(f"❌ Ошибка в skip_joint_photo: {e}")

        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

        await log_state(callback.message, state)



# Функция завершения этапа фото и перехода к следующему этапу

async def finish_photos(message_or_callback, state: FSMContext):

    await update_order_progress(state, status="photos_uploaded")

    

    # Получаем стили из базы данных

    from db import get_book_styles

    styles = await get_book_styles()

    

    if styles:

        # Отправляем заголовок

        header_text = "Замечательно📓\n" + \
                     "Теперь выбери стиль оформления, а мы создадим пробные сюжеты, которые покажут, как будет выглядеть ваша история ✨\n\n"

        if hasattr(message_or_callback, 'message'):

            await message_or_callback.message.edit_text(header_text, parse_mode="HTML")

            await message_or_callback.answer()

        else:

            await message_or_callback.answer(header_text, parse_mode="HTML")

        

        # Отправляем каждый стиль отдельным сообщением с фото

        for i, style in enumerate(styles):

            photo_path = f"styles/{style['filename']}"

            caption = f"<b>{i+1}. {style['name']}</b>\n{style['description']}"

            

            if os.path.exists(photo_path):

                if hasattr(message_or_callback, 'message'):

                    await message_or_callback.message.answer_photo(

                        types.FSInputFile(photo_path),

                        caption=caption,

                        parse_mode="HTML"

                    )

                else:

                    await message_or_callback.answer_photo(

                        types.FSInputFile(photo_path),

                        caption=caption,

                        parse_mode="HTML"

                    )

            else:

                # Если фото нет, отправляем только текст

                if hasattr(message_or_callback, 'message'):

                    await message_or_callback.message.answer(caption, parse_mode="HTML")

                else:

                    await message_or_callback.answer(caption, parse_mode="HTML")

        

        # Отправляем кнопки выбора в последнем сообщении

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(

                text=style['name'] if '—' in style['name'] else f"{style['name']} {'🏡 — будет позже' if 'Ghibli' in style['name'] else '👩‍❤️‍👨 — будет позже' if 'Love' in style['name'] else ''}",

                callback_data="style_pixar" if 'Pixar' in style['name'] else "style_ghibli_placeholder" if 'Ghibli' in style['name'] else "style_loveis_placeholder" if 'Love' in style['name'] else f"style_{style['id']}"

            )]

            for style in styles

        ])

        

        if hasattr(message_or_callback, 'message'):

            await message_or_callback.message.answer(

                "Выберите стиль:",

                reply_markup=keyboard

            )

        else:

            await message_or_callback.answer(

                "Выберите стиль:",

                reply_markup=keyboard

            )

    else:

        # Fallback на старые стили, если в базе нет

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="Pixar 🌈", callback_data="style_pixar")],

            [InlineKeyboardButton(text="Ghibli 🏡", callback_data="style_ghibli_placeholder")],

            [InlineKeyboardButton(text="Love is 👩‍❤️‍👨", callback_data="style_loveis_placeholder")],

        ])

        

        if hasattr(message_or_callback, 'message'):

            await message_or_callback.message.edit_text(

                "Замечательно📓\n"

                "Теперь выбери стиль оформления, а мы создадим пробные сюжеты, которые покажут, как будет выглядеть ваша история ✨",

                reply_markup=keyboard

            )

            await message_or_callback.answer()

        else:

            await message_or_callback.answer("Замечательно📓\n"

                                            "Теперь выбери стиль оформления, а мы создадим пробные сюжеты, которые покажут, как будет выглядеть ваша история ✨", reply_markup=keyboard)

    

    await state.set_state(CoverStates.choosing_style)

    await log_state(message_or_callback, state)



@dp.callback_query(F.data == "show_book")

async def show_book(callback: types.CallbackQuery, state: FSMContext):

    user_id = callback.from_user.id

    

    try:

        book_data = await get_user_book(user_id)

        if book_data and book_data['generated_book']:

            # Разбиваем книгу на части, если она слишком длинная

            book_text = book_data['generated_book']

            if len(book_text) > 4000:

                # Отправляем первые 4000 символов

                await callback.message.edit_text(

                    f"{book_text[:4000]}...\n\n[Книга продолжается]",

                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[

                        [InlineKeyboardButton(text="📖 Показать продолжение", callback_data="show_book_continue")],

                        [InlineKeyboardButton(text="🔄 Создать новую", callback_data="start_create_book")]

                    ])

                )

            else:

                await callback.message.edit_text(

                    book_text,

                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[

                        [InlineKeyboardButton(text="🔄 Создать новую", callback_data="start_create_book")]

                    ])

                )

        else:

            await callback.message.edit_text(

                "Книга не найдена. Создайте новую книгу.",

                reply_markup=InlineKeyboardMarkup(inline_keyboard=[

                    [InlineKeyboardButton(text="🔄 Создать новую", callback_data="start_create_book")]

                ])

            )

    except Exception as e:

        logging.error(f"Ошибка при показе книги: {e}")

        await callback.message.edit_text(

            "Произошла ошибка при загрузке книги. Попробуйте позже.",

            reply_markup=InlineKeyboardMarkup(inline_keyboard=[

                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="start_create_book")]

            ])

        )

    await callback.answer()

    await log_state(callback.message, state)



# После выбора стиля — задаём вопросы

# Обработчик для заглушек стилей

@dp.callback_query(F.data == "style_ghibli_placeholder")

async def ghibli_placeholder(callback: types.CallbackQuery):

    await callback.answer("Стиль Ghibli пока недоступен, но скоро будет! 🏡", show_alert=True)



@dp.callback_query(F.data == "style_loveis_placeholder")

async def loveis_placeholder(callback: types.CallbackQuery):

    await callback.answer("Стиль Love is пока недоступен, но скоро будет! 👩‍❤️‍👨", show_alert=True)



@dp.callback_query(F.data == "style_pixar")

async def pixar_style(callback: types.CallbackQuery, state: FSMContext):

    """Обработчик для стиля Pixar"""

    await callback.answer()

    

    # Сохраняем стиль

    await state.update_data(style="Pixar", style_id="pixar")

    

    # Получаем данные для персонализации

    data = await state.get_data()

    relation = data.get("relation")

    recipient_name = data.get("recipient_name")

    

    if recipient_name:

        who = recipient_name

    elif relation:

        who = relation.lower()

    else:

        who = "мамой"

    

    # Определяем вопросы в зависимости от типа связи

    gender = data.get("gender")

    questions = get_questions_for_relation(relation, gender)

    await state.update_data(story_questions=questions)

    

    # Показываем первый вопрос

    first_question = questions["q1"]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text=option, callback_data=f"q1_{i}")] 

        for i, option in enumerate(first_question["options"])

    ] + [[InlineKeyboardButton(text="Другое", callback_data="q1_other")]])

    

    question_text = first_question["text"].format(who=who)

    await callback.message.edit_text(question_text, reply_markup=keyboard)

    await state.set_state(StoryQuestionsStates.q1)

    await log_state(callback.message, state)



@dp.callback_query(F.data.startswith("style_"))

async def style_chosen(callback: types.CallbackQuery, state: FSMContext):

    style_id = callback.data.replace("style_", "")

    

    # Получаем информацию о стиле из базы данных

    from db import get_book_styles

    styles = await get_book_styles()

    

    # Ищем стиль по ID или по названию (для обратной совместимости)

    selected_style = None

    for style in styles:

        if str(style['id']) == style_id or style['name'].lower() == style_id.lower():

            selected_style = style

            break

    

    if selected_style:

        # Сохраняем ID стиля и его название

        await state.update_data(style=selected_style['name'], style_id=selected_style['id'])

        style = selected_style['name']  # Используем название для дальнейшей логики

    else:

        # Fallback для старых стилей

        await state.update_data(style=style_id)

        style = style_id

    data = await state.get_data()

    # Определяем получателя для персонализации вопроса

    relation = data.get("relation")

    recipient_name = data.get("recipient_name")
    
    # ОТЛАДКА: проверяем, есть ли recipient_name на этом этапе
    logging.info(f"🔍 ОТЛАДКА style_chosen: recipient_name='{recipient_name}', relation='{relation}'")

    if recipient_name:

        who = recipient_name

    elif relation:

        who = relation.lower()

    else:

        who = "мамой"
        
    # ВАЖНО: Убеждаемся, что recipient_name сохранен в состоянии
    if recipient_name:
        await state.update_data(recipient_name=recipient_name)
        logging.info(f"💾 ПЕРЕПОДТВЕРЖДЕНО recipient_name в состоянии: '{recipient_name}'")

    

    # Определяем вопросы в зависимости от типа связи

    gender = data.get("gender")

    print(f"🔍 ОТЛАДКА: relation = '{relation}', gender = '{gender}'")

    questions = get_questions_for_relation(relation, gender)

    print(f"🔍 ОТЛАДКА: questions = {questions}")

    await state.update_data(story_questions=questions)

    

    # Показываем первый вопрос

    first_question = questions["q1"]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text=option, callback_data=f"q1_{i}")] 

        for i, option in enumerate(first_question["options"])

    ] + [[InlineKeyboardButton(text="Другое", callback_data="q1_other")]])

    

    question_text = first_question["text"].format(who=who)

    await callback.message.edit_text(question_text, reply_markup=keyboard)

    await state.set_state(StoryQuestionsStates.q1)

    await callback.answer()

    await log_state(callback.message, state)


# Обработчик сообщений в состоянии выбора стиля книги
@dp.message(StateFilter(CoverStates.choosing_style), F.text)
async def handle_text_in_style_selection(message: types.Message, state: FSMContext):
    """Обрабатывает текстовые сообщения при выборе стиля книги"""
    
    print(f"🔍 ОТЛАДКА: Получено текстовое сообщение в состоянии choosing_style: '{message.text}' от пользователя {message.from_user.id}")
    
    # Сохраняем сообщение пользователя в историю заказа
    await save_user_message_to_history(message, state, "Сообщение при выборе стиля: ")
    
    # Проверяем текущее состояние FSM - если пользователь уже перешел к следующему этапу
    current_state = await state.get_state()
    
    if current_state and current_state != "CoverStates:choosing_style":
        await message.answer("❌ Выбор стиля уже завершен! Вы перешли к следующему этапу.")
        return
    
    # Пользователь отвечает администратору - сообщение уже сохранено в историю заказа
    # Не отправляем подтверждение пользователю
    
    await log_state(message, state)


def get_questions_for_relation(relation, gender=None):

    """Возвращает вопросы в зависимости от типа связи"""

    print(f"🔍 ОТЛАДКА get_questions_for_relation: получен relation = '{relation}', gender = '{gender}'")

    

    # Маппинг коротких названий на полные с учетом пола

    def get_mapped_relation(relation, gender):
        print(f"🔍 ОТЛАДКА get_mapped_relation: relation = '{relation}', gender = '{gender}'")

        if relation == "Дедушке":
            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Внук - дедушке"
            else:
                return "Внучка - дедушке"

        elif relation == "Бабушке":
            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Внук - бабушке"
            else:
                return "Внучка - бабушке"

        elif relation == "Маме":

            # Учитываем пол пользователя

            if gender == "мальчик" or gender == "парень":

                return "Сын – маме"

            else:
                return "Дочка- маме"

        elif relation == "Папе":

            # Учитываем пол пользователя

            if gender == "мальчик" or gender == "парень":

                return "Сын – папе"

            else:

                return "Дочка- папе"

        elif relation == "Сыну":

            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Папа - сыну"
            else:
                return "Мама - сыну"

        elif relation == "Дочке" or relation == "Дочери":

            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Папа - дочке"
            else:
                return "Мама - дочке"

        elif relation == "Брату":

            # Учитываем пол пользователя

            if gender == "мальчик" or gender == "парень":

                return "Брат – брату"

            else:

                return "Сестра - брату"

        elif relation == "Сестре":

            # Учитываем пол пользователя

            if gender == "мальчик" or gender == "парень":

                return "Брат – сестре"

            else:
                return "Сестра - сестре"

        elif relation == "Парню":

            # Учитываем пол пользователя

            if gender == "мальчик" or gender == "парень":
                result = "Парень - девушке"
                print(f"🔍 ОТЛАДКА get_mapped_relation: Парню + парень = '{result}'")
                return result

            else:
                result = "Девушка - парню"
                print(f"🔍 ОТЛАДКА get_mapped_relation: Парню + девушка = '{result}'")
                return result

        elif relation == "Девушке":

            # Учитываем пол пользователя

            if gender == "мальчик" or gender == "парень":
                result = "Парень - девушке"
                print(f"🔍 ОТЛАДКА get_mapped_relation: Девушке + парень = '{result}'")
                return result

            else:
                result = "Девушка - парню"
                print(f"🔍 ОТЛАДКА get_mapped_relation: Девушке + девушка = '{result}'")
                return result

        elif relation == "Мужу":

            # Жена выбирает "Мужу" → "Жена - мужу"

            return "Жена - мужу"

        elif relation == "Жене":

            # Муж выбирает "Жене" → "Муж - жене"

            return "Муж - жене"

        elif relation == "Подруге":

            return "Подруга - подруге"

        else:
            result = relation  # Возвращаем как есть, если это уже полное название
            print(f"🔍 ОТЛАДКА get_mapped_relation: возвращаем '{result}'")
            return result

    

    # Применяем маппинг с учетом пола

    old_relation = relation

    relation = get_mapped_relation(relation, gender)

    if old_relation != relation:

        print(f"🔍 ОТЛАДКА: преобразовали '{old_relation}' в полное название: '{relation}' (gender: '{gender}')")

    else:

        print(f"🔍 ОТЛАДКА: relation '{relation}' остался без изменений")

    

    questions = {

        "Девушка - парню": {

            "q1": {

                "text": "Как вы любите проводить выходные дома?",

                "options": ["Смотрим дома фильм", "Готовим вместе ужин", "Валяемся в кровати в обнимку"]

            },

            "q2": {

                "text": "Что вы делаете вместе как команда?",

                "options": ["Играем в настолки с друзьями", "Готовим дом к празднику", "Ходим за покупками"]

            },

            "q3": {

                "text": "Как вы любите проводить выходные вне дома?",

                "options": ["Совместные тренировки", "Вечерние прогулки", "Поход в кинотеатр"]

            }

        },

        "Парень - девушке": {

            "q1": {

                "text": "Как вы любите проводить выходные дома?",

                "options": ["Смотрим дома фильм", "Готовим вместе ужин", "Валяемся в кровати в обнимку"]

            },

            "q2": {

                "text": "Что вы делаете вместе как команда?",

                "options": ["Готовим дом к празднику", "Ходим за покупками", "Играем в настолки с друзьями"]

            },

            "q3": {

                "text": "Как вы любите проводить выходные вне дома?",

                "options": ["Совместные тренировки", "Вечерние прогулки", "Поход в кинотеатр"]

            }

        },

        "Жена - мужу": {

            "q1": {

                "text": "Какой самый яркий день в ваших отношениях?",

                "options": ["Наш первый поцелуй", "Предложение руки и сердца", "Когда мы узнали о беременности"]

            },

            "q2": {

                "text": "Что ты ценишь в муже больше всего?",

                "options": ["Он всегда поддерживает меня", "Он заботится обо мне, когда я болею", "Он балует меня подарками"]

            },

            "q3": {

                "text": "Какой знак внимания от мужа у вас самый любимый?",

                "options": ["Он готовит ужин специально для меня", "Он проявляет свои чувства", "Он нежно целует меня в лоб"]

            }

        },

        "Муж - жене": {

            "q1": {

                "text": "Какой самый яркий день в ваших отношениях?",

                "options": ["Наш первый поцелуй", "Наше первое свидание", "Рождение ребенка"]

            },

            "q2": {

                "text": "Что ты ценишь в жене больше всего?",

                "options": ["Она всегда поддерживает меня", "Она заботится обо мне, когда я болею", "Она готовит для нас романтические ужины"]

            },

            "q3": {

                "text": "Как вы любите проводить время с женой вдвоем?",

                "options": ["Путешествовать, изучать новые места", "Гулять в парке", "Лежать вдвоем в обнимку и смотреть кино"]

            }

        },

        "Дочка- маме": {

            "q1": {

                "text": "Какое у тебя самое нежное или яркое воспоминание о маме?",

                "options": ["Мамина еда - самая вкусная в мире", "Мама устраивала мне лучшие сюрпризы", "Мама всегда поддерживала меня"]

            },

            "q2": {

                "text": "Чем вы любили заниматься вместе с мамой в детстве?",

                "options": ["Наряжать ёлку", "Готовить вместе", "Смотреть вместе любимый сериал"]

            },

            "q3": {

                "text": "Чему важному вас научила мама?",

                "options": ["Получать удовольствие от творчества", "Содержать дом в чистоте", "Любить себя"]

            }

        },

        "Мама - дочке": {

            "q1": {

                "text": "Какое у тебя самое нежное или яркое воспоминание о дочери?",

                "options": ["Когда я впервые взяла ее на руки", "Когда она впервые сказала \"мама\"", "Когда она подарила мне внука/внучку"]

            },

            "q2": {

                "text": "Что вы больше всего любите делать вместе с дочерью?",

                "options": ["Готовить вкусный ужин", "Наряжать ёлку", "Смотреть кино вечером"]

            },

            "q3": {

                "text": "Когда вы испытали невероятные эмоции рядом с дочерью?",

                "options": ["Когда она выступала на сцене", "Когда увидела её невестой", "Когда она рассказала мне свой секрет"]

            }

        },

        "Папа - дочке": {

            "q1": {

                "text": "Какое у тебя самое нежное или яркое воспоминание о дочери?",

                "options": ["Когда я впервые взял ее на руки", "Когда она впервые сказала \"папа\"", "Когда она подарила мне внука/внучку"]

            },

            "q2": {

                "text": "Что вы больше всего любите делать вместе с дочерью?",

                "options": ["Гулять вместе по парку", "Кататься на велосипеде", "Смотреть любимые мультфильмы"]

            },

            "q3": {

                "text": "Когда вы испытали невероятные эмоции рядом с дочерью?",

                "options": ["Когда она выступала на сцене", "Когда увидел её невестой", "Когда она рассказала мне свой секрет"]

            }

        },

        "Мама - сыну": {

            "q1": {

                "text": "Какое у тебя самое нежное или яркое воспоминание о сыне?",

                "options": ["Первый день, когда я взяла его на руки", "Когда он впервые сказал \"мама\"", "Когда я отвела его в 1 класс"]

            },

            "q2": {

                "text": "Чем вы любили заниматься вместе с сыном?",

                "options": ["Готовить вместе вкусный ужин", "Слушать его забавные истории", "Смотреть вместе кино или телевизор"]

            },

            "q3": {

                "text": "Когда ты испытала невероятные эмоции рядом с сыном?",

                "options": ["Когда он закончил школу или институт", "Когда он победил на соревнованиях", "Когда увидела его женихом на свадьбе"]

            }

        },

        "Папа - сыну": {

            "q1": {

                "text": "Какое у тебя самое нежное или яркое воспоминание о сыне?",

                "options": ["Первый день, когда я взял его на руки", "Когда он впервые сказал \"папа\"", "Когда я отвел его в 1 класс"]

            },

            "q2": {

                "text": "Чем вы любили заниматься вместе с сыном?",

                "options": ["Играть вместе в футбол", "Мастерить что-то дома", "Смотреть матчи по ТВ"]

            },

            "q3": {

                "text": "Когда ты испытал невероятные эмоции рядом с сыном?",

                "options": ["Когда он закончил школу или институт", "Когда он победил на соревнованиях", "Когда увидел его женихом на свадьбе"]

            }

        },

        "Сестра - сестре": {

            "q1": {

                "text": "Какое у тебя самое нежное или яркое воспоминание о сестре?",

                "options": ["Когда ее принесли домой из роддома", "Когда она защитила меня", "Когда она поддерживала меня в трудности"]

            },

            "q2": {

                "text": "Что вы больше всего любите делать вместе с сестрой?",

                "options": ["Сплетничать", "Готовить вместе", "Смотреть мульфильфы или телевизор"]

            },

            "q3": {

                "text": "Чему тебя научила сестра?",

                "options": ["Читать или делать уроки", "Научила делиться", "Наносить макияж или ухаживать за собой"]

            }

        },

        "Сестра - брату": {

            "q1": {

                "text": "Какое у тебя самое нежное или яркое воспоминание о брате?",

                "options": ["Когда он сделал первый шаг", "Когда он защитил меня", "Когда мы с ним обиделись на родителей"]

            },

            "q2": {

                "text": "Что вы больше всего любите делать вместе с братом?",

                "options": ["Играть вдвоем", "Готовить сюрприз родителям", "Смотреть кино или телевизор"]

            },

            "q3": {

                "text": "Чему тебя научил брат?",

                "options": ["Читать или делать уроки", "Что я могу всегда на него положиться", "Кататься на велосипеде"]

            }

        },

        "Подруга - подруге": {

            "q1": {

                "text": "Что для тебя самое важное в твоей подруге?",

                "options": ["Что мы вместе гуляем", "Что она всегда меня поддерживает", "Что мы можем посекретничать"]

            },

            "q2": {

                "text": "Что вы больше всего любите делать вместе с подругой?",

                "options": ["Сплетничать", "Ходить на тусовки", "Переписываться"]

            },

            "q3": {

                "text": "Чему тебя научила твоя подруга?",

                "options": ["Верить в женскую дружбу", "Доверять свои секреты", "Верить в себя"]

            }

        },

        "Внучка - бабушке": {

            "q1": {

                "text": "Какое у тебя самое нежное или яркое воспоминание о бабушке?",

                "options": ["Что ее еда - самая вкусная в мире", "Как она читала сказки перед сном", "Как бабушка меня обнимает"]

            },

            "q2": {

                "text": "Что вы любите делать с бабушкой вместе?",

                "options": ["Слушать истории ее молодости", "Гулять в парке", "Проводить время на даче или в саду"]

            },

            "q3": {

                "text": "Чему важному тебя научила бабушка?",

                "options": ["Рисовать", "Вязать", "Печь пирожки"]

            }

        },

        "Дочка- папе": {

            "q1": {

                "text": "Какое у тебя самое нежное или яркое воспоминание о папе?",

                "options": ["Как папа катал меня на своей шее", "Как папа ходил на все мои выступления", "Папины сказки на ночь"]

            },

            "q2": {

                "text": "Что вы любите делать с папой вместе?",

                "options": ["Украшать елку и готовиться к празднику", "Строить шалаш из одеял дома", "Ходить на рыбалку"]

            },

            "q3": {

                "text": "Чему важному тебя научил папа?",

                "options": ["Кататься на велосипеде", "Чувствовать себя нежной и хрупкой", "Водить машину"]

            }

        },

        "Внучка - дедушке": {

            "q1": {

                "text": "Какое у тебя самое нежное или яркое воспоминание о дедушке?",

                "options": ["Как он катал меня на шее", "Как мы играли с ним", "Истории его жизни"]

            },

            "q2": {

                "text": "Что вы любите делать с дедушкой вместе?",

                "options": ["Ходить на рыбалку", "Помогать на даче или в саду", "Разгадывать кроссворд"]

            },

            "q3": {

                "text": "Чему важному дедушка тебя научил?",

                "options": ["Кататься на велосипеде", "Водить машину", "Играть в шахматы"]

            }

        },

        "Сын – маме": {

            "q1": {

                "text": "Какое у тебя самое нежное или яркое воспоминание о маме?",

                "options": ["Мама готовила мои любимые блюда", "Мама лечила и заботилась, когда я болел", "Мама всегда верила в меня"]

            },

            "q2": {

                "text": "Что вы любите делать вместе с мамой?",

                "options": ["Смотреть фильмы и сериалы", "Вместе проводить время на природе", "Готовить дом к Новому году"]

            },

            "q3": {

                "text": "Чему важному тебя научила мама?",

                "options": ["Ставить цели и достигать их", "Быть надежным мужчиной", "Заботиться о других"]

            }

        },

        "Сын – папе": {

            "q1": {

                "text": "Какое у тебя самое яркое воспоминание о папе?",

                "options": ["Как папа отвел в первый класс", "Как папа играл со мной в детстве", "Папа поддерживал меня на соревнованиях"]

            },

            "q2": {

                "text": "Что вы любите делать вместе с папой?",

                "options": ["Играть в спортивные игры", "Смотреть боевик", "Мастерить что-то дома"]

            },

            "q3": {

                "text": "Чему важному тебя научил папа?",

                "options": ["Водить машину", "Уметь защищать себя", "Ловить рыбу"]

            }

        },

        "Брат – брату": {

            "q1": {

                "text": "Какое у тебя самое яркое воспоминание о брате?",

                "options": ["Как мы играли вместе в детстве", "Как брат защищал меня", "Как мы соревновались друг с другом"]

            },

            "q2": {

                "text": "Что вы любите делать вместе с братом?",

                "options": ["Играть в компьютерные игры", "Ходить на тренировки", "Смотреть футбол"]

            },

            "q3": {

                "text": "Чему тебя научил брат?",

                "options": ["Кататься на велосипеде", "Быть смелым", "Поддерживать в трудные моменты"]

            }

        },

        "Брат – сестре": {

            "q1": {

                "text": "Какое у тебя самое нежное или яркое воспоминание о сестре?",

                "options": ["Как она сделала первый шаг", "Мы вместе готовили сюрприз для родных", "Как мы ссорились и быстро мирились"]

            },

            "q2": {

                "text": "Что вы любите делать вместе с сестрой?",

                "options": ["Смотреть кино или сериалы", "Подшучивать над родителями", "Играть вместе"]

            },

            "q3": {

                "text": "Чему тебя научила сестра?",

                "options": ["Читать или делать уроки", "Делиться сладостями", "Стильно одеваться"]

            }

        },

        "Внук - бабушке": {

            "q1": {

                "text": "Какое у тебя самое нежное или яркое воспоминание о бабушке?",

                "options": ["Что ее еда - самая вкусная в мире", "Как она читала сказки перед сном", "Как бабушка меня обнимает"]

            },

            "q2": {

                "text": "Что вы любите делать с бабушкой вместе?",

                "options": ["Слушать истории ее молодости", "Гулять в парке", "Проводить время на даче или в саду"]

            },

            "q3": {

                "text": "Чему важному тебя научила бабушка?",

                "options": ["Рисовать", "Вязать", "Печь пирожки"]

            }

        },

        "Внук - дедушке": {

            "q1": {

                "text": "Какое у тебя самое нежное или яркое воспоминание о дедушке?",

                "options": ["Как он катал меня на шее", "Как мы играли с ним", "Истории его жизни"]

            },

            "q2": {

                "text": "Что вы любите делать с дедушкой вместе?",

                "options": ["Ходить на рыбалку", "Помогать на даче или в саду", "Разгадывать кроссворд"]

            },

            "q3": {

                "text": "Чему важному дедушка тебя научил?",

                "options": ["Рыбачить", "Работать с инструментами", "Играть в шахматы"]

            }

        }

    }

    

    # Получаем правильное название связи с учетом пола
    mapped_relation = get_mapped_relation(relation, gender)

    # Возвращаем вопросы для "Девушка - парню" по умолчанию, если тип связи не найден
    result = questions.get(mapped_relation, questions["Девушка - парню"])

    print(f"🔍 ОТЛАДКА get_questions_for_relation: возвращаем {result}")

    if mapped_relation not in questions:

        print(f"❌ ОТЛАДКА: mapped_relation '{mapped_relation}' НЕ НАЙДЕН в questions! Доступные ключи: {list(questions.keys())}")

    return result



async def get_song_questions_for_relation(relation, gender):

    """Возвращает вопросы анкеты для песни в зависимости от типа связи и пола"""

    

    # Сначала пытаемся получить тексты из БД song_quiz
    try:
        from db import get_song_quiz_item
        gender_key = 'female' if gender in ('девушка', 'женщина') else 'male'
        relation_map = {
            'Любимому': 'husband',
            'Любимой': 'wife',
            'Парню': 'boyfriend',
            'Девушке': 'girlfriend',
            'Маме': 'mom',
            'Папе': 'dad',
            'Бабушке': 'grandma',
            'Дедушке': 'grandpa',
            'Подруге': 'friend',
            'Сестре': 'sister',
            'Брату': 'brother',
            'Сыну': 'son',
            'Дочери': 'daughter'
        }
        rel_key = relation_map.get(relation)
        if rel_key:
            item = await get_song_quiz_item(rel_key, gender_key)
            if item:
                import json
                questions = []
                questions.append(item.get('intro', ''))
                questions.append('')
                if item.get('phrases_hint'):
                    questions.append(item['phrases_hint'])
                    questions.append('')
                try:
                    q_list = json.loads(item.get('questions_json', '[]'))
                    questions.extend(q_list)
                except Exception:
                    pass
                questions.append('')
                if item.get('outro'):
                    questions.append(item['outro'])
                if questions:
                    return questions
    except Exception:
        pass

    # Вопросы для пар (муж → жена)

    husband_to_wife = [

        "Дорогой (имя), сегодня мы вместе с тобой создаем песню для твоей любимой жены (имя), давай сделаем этот подарок запоминающимся и трогательным. Ответь пожалуйста на вопросы, которые помогут нам сделать песню до-мурашек.",

        "",

        "Словосочетания: \"Ты самая лучшая, Самая красивая и нежная\", наша команда напишет в любом случае, а от тебя нам нужны конкретные детали:",

        "",

        "Как вы познакомились и сколько лет вы вместе?",

        "Опиши ваше первое свидание? Что вы делали, что чувствовали?",

        "Как ласково вы называете друг друга?",

        "Какие самые трогательные моменты объединяют вас? (предложение, день свадьбы, путешествия, крупные совместные покупки)",

        "Есть ли у вас дети? Напиши их имена. Кто первый родился, кто второй (какие важные проявление жены в жизни детей)?",

        "Чем увлечена твоя жена? (дети, хобби, работа, спорт, творчество, музыка и т.д.)",

        "Что она делает для тебя, благодаря чему ты чувствуешь себя любимым и счастливым?",

        "Какое совместное занятие с женой приносит вам обоим особую радость?",

        "",

        "Отвечая на эти вопросы поищи теплые общие воспоминания, которые вызовут трепет, радость и мурашки у твоей супруги, которые смогут тронуть ее сердце. Ты можешь написать нам в свободной форме, не опираясь на список вопросов. Для создания трогательной и душевной песни, мы ждем от тебя 5-8 уникальных фактов про ваши отношения и о твоей супруге.",

        "Счастливых вам воспоминаний и мы ждем вашу историю."

    ]

    

    # Вопросы для пар (жена → муж)

    wife_to_husband = [

        "Дорогая (имя), сегодня мы вместе с тобой создаем песню для твоего любимого мужа (имя), давай сделаем этот подарок запоминающимся и трогательным. Ответь пожалуйста на вопросы, которые помогут нам сделать песню до-мурашек.",

        "",

        "Словосочетания: \"Ты самый лучший, самый надежный, заботливый и нежный\", наша команда напишет в любом случае, а от тебя нам нужны конкретные детали:",

        "",

        "Как вы познакомились и сколько лет вы вместе?",

        "Опишите ваше первое свидание? Что вы делали, что чувствовали?",

        "Как ласково вы называете друг друга?",

        "Какие самые трогательные моменты связывают вас? (предложение руки и сердца, день свадьбы, путешествия)",

        "Есть ли у вас дети? Напиши их имена. И кто первый родился, кто второй (какие важные проявление мужа в жизни детей)",

        "Чем увлечен твой муж? (работа, спорт, хобби, творчество, музыка и т.д.)",

        "Что он делает для тебя, благодаря чему ты чувствуешь себя любимой, счастливой и за что ты благодарна ему?",

        "Какое совместное занятие с мужем приносит вам обоим особую радость?",

        "",

        "Отвечая на эти вопросы поищи теплые общие воспоминания, которые вызовут трепет, радость и мурашки у твоего супруга, которые смогут тронуть его сердце. Ты можешь написать нам в свободной форме, не опираясь на список вопросов. Для создания трогательной и душевной песни, мы ждем от тебя 5-8 уникальных фактов про ваши отношения и о твоем супруге.",

        "Счастливых вам воспоминаний и мы ждем вашу историю."

    ]

    

    # Вопросы для пар (девушка → парень)

    girlfriend_to_boyfriend = [

        "Дорогая (имя), сегодня мы вместе с тобой создаем песню для твоего любимого (имя), давай сделаем этот подарок запоминающимся и трогательным. Ответь пожалуйста на вопросы, которые помогут нам сделать песню до-мурашек.",

        "",

        "Словосочетания: \"Ты самый лучший, самый надежный, заботливый и нежный\", наша команда напишет в любом случае, а от тебя нам нужны конкретные детали:",

        "",

        "Как вы познакомились и сколько вы вместе?",

        "2 Опишите ваше первое свидание? Что вы делали, что чувствовали?",

        "Как ласково вы называете друг друга?",

        "Какие самые трогательные моменты связывают вас? (свидания, предложение руки и сердца, путешествия)",

        "Какой самый яркий поступок твоего любимого навсегда остался в памяти?",

        "Чем увлечен твой любимый? (работа, спорт, хобби, творчество, музыка и т.д.)",

        "Что он делает для тебя, благодаря чему ты чувствуешь себя любимой, счастливой и за что ты благодарна ему?",

        "Какое совместное занятие с любимым приносит вам обоим особую радость?",

        "",

        "Отвечая на эти вопросы поищи теплые общие воспоминания, которые вызовут трепет, радость и мурашки у твоего любимого человека, которые смогут тронуть его сердце. Ты можешь написать нам в свободной форме, не опираясь на список вопросов. Для создания трогательной и душевной песни, мы ждем от тебя 5-8 уникальных фактов про ваши отношения и о твоем любимом человеке.",

        "Счастливых вам воспоминаний и мы ждем вашу историю."

    ]

    

    # Вопросы для пар (парень → девушка)

    boyfriend_to_girlfriend = [

        "Дорогой(имя), сегодня мы вместе с тобой создаем песню для твоей любимой (имя), давай сделаем этот подарок запоминающимся и трогательным. Ответь пожалуйста на вопросы, которые помогут нам сделать песню до-мурашек.",

        "",

        "Словосочетания: \"Ты самая лучшая, Самая красивая и нежная\", наша команда напишет в любом случае, а от тебя нам нужны конкретные детали:",

        "",

        "Как вы познакомились и сколько вы вместе?",

        "Опиши ваше первое свидание? Что вы делали, что чувствовали?",

        "Как ласково вы называете друг друга?",

        "Какие самые трогательные моменты связывают вас? (свидания, предложение руки и сердца, путешествия)",

        "Какой самый яркий поступок твоей любимой навсегда остался в памяти?",

        "Чем увлечена твоя любимая? (работа, спорт, хобби, творчество, музыка, танцы и т.д.)",

        "Что она делает для тебя, благодаря чему ты чувствуешь себя любимым, счастливым и за что ты благодарен ей?",

        "Какое совместное занятие с любимой приносит вам обоим особую радость?",

        "",

        "Отвечая на эти вопросы поищи теплые общие воспоминания, которые вызовут трепет, радость и мурашки у твоей любимой, которые смогут тронуть ее сердце. Ты можешь написать нам в свободной форме, не опираясь на список вопросов. Для создания трогательной и душевной песни, мы ждем от тебя 5-8 уникальных фактов про ваши отношения и о твоей любимой девушке.",

        "Счастливых вам воспоминаний и мы ждем вашу историю."

    ]

    

    # Вопросы для детей к маме

    child_to_mom = [

        "Дорогая (имя), сегодня мы вместе с тобой создаем песню для твоей любимой мамы, давай сделаем этот подарок запоминающимся и трогательным. Ответь пожалуйста на вопросы, которые помогут нам сделать песню до-мурашек.",

        "",

        "Словосочетания: \"Ты самая лучшая, добрая, красивая и нежная\", наша команда напишет в любом случае, а от тебя нам нужны конкретные детали:",

        "",

        "Какой момент с мамой из твоего детства ты особенно ценишь и всегда будешь помнить?",

        "Какое мамино блюдо или лакомство было твои самым любимым в детстве?",

        "Какие слова или советы мамы запомнились? Как мама поддерживала или утешала тебя в трудные моменты?",

        "Есть ли у вас с мамой милые слова друг для друга?",

        "Вы с мамой живете в одном городе или между вами расстояния? (города указать)?",

        "Какой самый незабываемый сюрприз, праздник или подарок мама для тебя делала?",

        "Если у тебя братишки, сестренки о которых бы ты хотела сказать в песне, напиши их имена и последовательность?",

        "Вспомни трогательные проявления твоей мамы как жены, сестры, бабушки, подруги (что ты можешь подчеркнуть) ее отношение к другим членам семьи? Любовь к питомцам?",

        " Чему мама тебя научила, какие важные навыки она тебе передала? (готовить, петь, рисовать, мечтать)",

        "",

        "Отвечая на эти вопросы поищи теплые общие воспоминания, которые вызовут трепет, радость и мурашки у твоей мамы, которые смогут тронуть ее сердце. Ты можешь написать нам в свободной форме, не опираясь на список вопросов. Для создания трогательной и душевной песни, мы ждем от тебя 5-8 уникальных фактов про ваши отношения и о твоей маме.",

        "Счастливых вам воспоминаний и мы ждем вашу историю."

    ]

    

    # Вопросы для сына к маме

    son_to_mom = [

        "Дорогой(имя), сегодня мы вместе с тобой создаем песню для твоей любимой мамы, давай сделаем этот подарок запоминающимся и трогательным. Ответь пожалуйста на вопросы, которые помогут нам сделать песню до-мурашек.",

        "",

        "Словосочетания: \"Ты самая лучшая, Самая красивая и нежная\", наша команда напишет в любом случае, а от тебя нам нужны конкретные детали:",

        "",

        "Какой момент с мамой из твоего детства ты особенно ценишь и всегда будешь помнить?",

        "Какое мамино блюдо или лакомство было твое самым любимым в детстве?",

        "Какие слова или советы мамы запомнились? Как мама поддерживала или утешала тебя в трудные моменты?",

        "Есть ли у вас с мамой милые слова друг для друга?",

        "Вы с мамой живете в одном городе или между вами расстояния? (города указать)?",

        "Какой самый незабываемый сюрприз, праздник или подарок мама для тебя делала?",

        "Если у тебя братишки, сестренки о которых бы ты хотел сказать в песне, напиши их имена и последовательность?",

        "Вспомни трогательные проявления твоей мамы как жены, сестры, бабушки, подруги (что ты можете подчеркнуть) ее отношение к другим членам семьи? Любовь к питомцам?",

        " Чему мама тебя научила, какие важные навыки она тебе передала? (готовить, петь, рисовать, мечтать)",

        "",

        "Отвечая на эти вопросы поищи теплые общие воспоминания, которые вызовут трепет, радость и мурашки у твоей любимой мамы, которые смогут тронуть ее сердце. Ты можешь написать нам в свободной форме, не опираясь на список вопросов. Для создания трогательной и душевной песни, мы ждем от тебя 5-8 уникальных фактов про ваши отношения и о твоей любимой мамуле.",

        "Счастливых вам воспоминаний и мы ждем вашу историю."

    ]

    

    # Вопросы для детей к папе

    child_to_dad = [

        "Дорогая (имя), сегодня мы вместе с тобой создаем песню для твоего любимого папы, давай сделаем этот подарок запоминающимся и трогательным. Ответь пожалуйста на вопросы, которые помогут нам сделать песню до-мурашек.",

        "",

        "Словосочетания: \"Ты самый лучший папа, добрый, сильный и надежный\", наша команда напишет в любом случае, а от тебя нам нужны конкретные детали:",

        "",

        "Какой момент с папой из твоего детства ты особенно ценишь и всегда будешь помнить?",

        "Какие у папы хобби, интересы, увлечения, фирменное блюдо?",

        "Какие слова или советы папы запомнились? Как папа защищал и поддерживал тебя в трудные моменты?",

        "Есть ли у вас с папой милые слова друг для друга?",

        "Вы с папой живете в одном городе или между вами расстояния? (города указать)?",

        "Какой самый незабываемый сюрприз, праздник или подарок папа для тебя делал?",

        "Если у тебя братишки, сестренки о которых бы ты хотела сказать в песне, напиши их имена и последовательность?",

        "Вспомни трогательные проявления твоего папы как мужа, сына, дедушки, друга (что ты можешь подчеркнуть) его отношение к другим членам семьи? Любовь к питомцам?",

        " Чему папа тебя научил, какие важные навыки он тебе передал? (стрелять, кататься на велосипеде, на коньках, лыжах)?",

        "",

        "Отвечая на эти вопросы поищи теплые общие воспоминания, которые вызовут трепет, радость и мурашки у твоего папы, которые смогут тронуть его сердце. Ты можешь написать нам в свободной форме, не опираясь на список вопросов. Для создания трогательной и душевной песни, мы ждем от тебя 5-8 уникальных фактов про ваши отношения и о твоем папе.",

        "Счастливых вам воспоминаний и мы ждем вашу историю."

    ]

    

    # Вопросы для сына к папе

    son_to_dad = [

        "Дорогой(имя), сегодня мы вместе с тобой создаем песню для твоего любимого папы, давай сделаем этот подарок запоминающимся и трогательным. Ответь пожалуйста на вопросы, которые помогут нам сделать песню до-мурашек.",

        "",

        "Словосочетания: \"Ты самая храбрый, сильный и надежный\", наша команда напишет в любом случае, а от тебя нам нужны конкретные детали:",

        "",

        "Какой момент с папой из твоего детства ты особенно ценишь и всегда будешь помнить?",

        "Какие у папы хобби, интересы, увлечения, фирменное блюдо?",

        "Какие слова или советы папы запомнились? Как папа защищал и поддерживал тебя в трудные моменты?",

        "Есть ли у вас с папой милые слова друг для друга?",

        "Вы с папой живете в одном городе или между вами расстояния? (города указать)?",

        "Какой самый незабываемый сюрприз, праздник или подарок папа для тебя делал?",

        "Если у тебя братишки, сестренки о которых бы ты хотел сказать в песне, напиши их имена и последовательность?",

        "Вспомни трогательные проявления твоего папы как мужа, сына, дедушки, друга (что ты можешь подчеркнуть) его отношение к другим членам семьи? Любовь к питомцам?",

        " Чему папа тебя научил, какие важные навыки он тебе передал? (стрелять, кататься на велосипеде, на коньках, лыжах)?",

        "",

        "Отвечая на эти вопросы поищи теплые общие воспоминания, которые вызовут трепет, радость и мурашки у твоего любимого папы, которые смогут тронуть его сердце. Ты можешь написать нам в свободной форме, не опираясь на список вопросов. Для создания трогательной и душевной песни, мы ждем от тебя 5-8 уникальных фактов про ваши отношения и о твоем любимом папе.",

        "Счастливых вам воспоминаний и мы ждем вашу историю."

    ]

    

    # Вопросы для внуков к бабушке

    grandchild_to_grandma = [

        "Дорогая (имя), сегодня мы вместе с тобой создаем песню для твоей любимой бабушки, давай сделаем этот подарок запоминающимся и трогательным. Ответь пожалуйста на вопросы, которые помогут нам сделать песню до-мурашек.",

        "",

        "Словосочетания: \"Ты самая лучшая, добрая, теплая и нежная\", наша команда напишет в любом случае, а от тебя нам нужны конкретные детали:",

        "",

        "Какой момент с бабушкой из твоего детства ты особенно ценишь и всегда будешь помнить?",

        "Какое бабушкино блюдо или лакомство было твоим самым любимым в детстве?",

        "Какие слова или советы бабушки запомнились? Как бабушка поддерживала или утешала тебя в трудные моменты?",

        "Есть ли у вас с бабушкой милые слова друг для друга?",

        "Вспомните весёлый случай или шалость из детства, когда вы с бабушкой вместе смеялись. Что тогда произошло?",

        "Какой самый незабываемый сюрприз, праздник или подарок бабушка для тебя делала?",

        "Чему бабушка тебя научила, какие важные навыки она тебе передала? (готовить, петь, печь?)",

        "Вспомни трогательные проявления твоей бабушки как мамы, бабушки, подруги (что ты можешь подчеркнуть) ее отношение к другим членам семьи? Любовь к питомцам?",

        "",

        "Отвечая на эти вопросы поищи теплые общие воспоминания, которые вызовут трепет, радость и мурашки у твоей бабушки, которые смогут тронуть ее сердце. Ты можешь написать нам в свободной форме, не опираясь на список вопросов. Для создания трогательной и душевной песни, мы ждем от тебя 5-8 уникальных фактов про ваши отношения и о твоей бабушке.",

        "Счастливых вам воспоминаний и мы ждем вашу историю."

    ]

    

    # Вопросы для внука к бабушке

    grandson_to_grandma = [

        "Дорогой (имя), сегодня мы вместе с тобой создаем песню для твоей любимой бабушки, давай сделаем этот подарок запоминающимся и трогательным. Ответь пожалуйста на вопросы, которые помогут нам сделать песню до-мурашек.",

        "",

        "Словосочетания: \"Ты самая лучшая, добрая, теплая и нежная\", наша команда напишет в любом случае, а от тебя нам нужны конкретные детали:",

        "",

        "Какой момент с бабушкой из твоего детства ты особенно ценишь и всегда будешь помнить?",

        "Какое бабушкино блюдо или лакомство было твоим самым любимым в детстве?",

        "Какие слова или советы бабушки запомнились? Как бабушка поддерживала или утешала тебя в трудные моменты?",

        "Есть ли у вас с бабушкой милые слова друг для друга?",

        "Вспомни весёлый случай или шалость из детства, когда вы с бабушкой вместе смеялись. Что тогда произошло?",

        "Какой самый незабываемый сюрприз, праздник или подарок бабушка для тебя делала?",

        "Чему бабушка тебя научила, какие важные навыки она тебе передала? (готовить, петь, печь)?",

        "Вспомни трогательные проявления твоей бабушки как мамы, бабушки, подруги (что ты можете подчеркнуть) ее отношение к другим членам семьи? Любовь к питомцам?",

        "",

        "Отвечая на эти вопросы поищи теплые общие воспоминания, которые вызовут трепет, радость и мурашки у твоей бабушки, которые смогут тронуть ее сердце. Ты можешь написать нам в свободной форме, не опираясь на список вопросов. Для создания трогательной и душевной песни, мы ждем от тебя 5-8 уникальных фактов про ваши отношения и о твоей бабушке.",

        "Счастливых вам воспоминаний и мы ждем вашу историю."

    ]

    

    # Вопросы для внуков к дедушке

    grandchild_to_grandpa = [

        "Дорогая (имя), сегодня мы вместе с тобой создаем песню для твоего любимого дедушки, давай сделаем этот подарок запоминающимся и трогательным. Ответь пожалуйста на вопросы, которые помогут нам сделать песню до-мурашек.",

        "",

        "Словосочетания: \"Ты самый лучший, добрый, смелый и надежный\", наша команда напишет в любом случае, а от тебя нам нужны конкретные детали:",

        "",

        "Какой момент из детства с дедушкой остался самым дорогим воспоминанием?",

        "Какое занятие или времяпрепровождение с дедушкой было самым любимым?",

        "Какие дедушкины слова, советы или истории поддержки запомнились навсегда?",

        "Были ли у вас с дедушкой свои особенные, только ваши ласковые слова или прозвища?",

        "Какой весёлый случай или шалость с дедушкой всегда вызывает улыбку при воспоминании?",

        "Какой сюрприз, праздник или подарок от дедушки стал самым запоминающимся?",

        "Чему дедушка тебя научил, какие важные навыки он тебе передал? (мастерить, играть, читать, рассказывать истории или чему-то ещё?)",

        "В чём проявлялась дедушкина забота о семье и близких? Как он выражал свою любовь?",

        "",

        "Отвечая на эти вопросы поищи теплые общие воспоминания, которые вызовут трепет, радость и мурашки у твоего дедушки, которые смогут тронуть его сердце. Ты можешь написать нам в свободной форме, не опираясь на список вопросов. Для создания трогательной и душевной песни, мы ждем от тебя 5-8 уникальных фактов про ваши отношения и о твоем дедушке.",

        "Счастливых вам воспоминаний и мы ждем вашу историю."

    ]

    

    # Вопросы для внука к дедушке

    grandson_to_grandpa = [

        "Дорогой (имя), сегодня мы вместе с тобой создаем песню для твоего любимого дедушки, давай сделаем этот подарок запоминающимся и трогательным. Ответь пожалуйста на вопросы, которые помогут нам сделать песню до-мурашек.",

        "",

        "Словосочетания: \"Ты самый лучший, добрый, смелый и надежный\", наша команда напишет в любом случае, а от тебя нам нужны конкретные детали:",

        "",

        "Какой момент из детства с дедушкой остался самым дорогим воспоминанием?",

        "Какое занятие или времяпрепровождение с дедушкой было самым любимым?",

        "Какие дедушкины слова, советы или истории поддержки запомнились навсегда?",

        "Были ли у вас с дедушкой свои особенные, только ваши ласковые слова или прозвища?",

        "Какой весёлый случай или шалость с дедушкой всегда вызывает улыбку при воспоминании?",

        "Какой сюрприз, праздник или подарок от дедушки стал самым запоминающимся?",

        "Чему дедушка тебя научил, какие важные навыки он тебе передал? (мастерить, играть, читать, рассказывать истории или чему-то ещё?)",

        "В чём проявлялась дедушкина забота о семье и близких? Как он выражал свою любовь?",

        "",

        "Отвечая на эти вопросы поищи теплые общие воспоминания, которые вызовут трепет, радость и мурашки у твоего дедушки, которые смогут тронуть его сердце. Ты можешь написать нам в свободной форме, не опираясь на список вопросов. Для создания трогательной и душевной песни, мы ждем от тебя 5-8 уникальных фактов про ваши отношения и о твоем дедушке.",

        "Счастливых вам воспоминаний и мы ждем вашу историю."

    ]

    

    # Вопросы для подруг

    friend_to_friend = [

        "Дорогая (имя), сегодня мы вместе с тобой создаем песню для твоей любимой подруги (имя) давай сделаем этот подарок запоминающимся и трогательным. Ответь пожалуйста на вопросы, которые помогут нам сделать песню до-мурашек.",

        "",

        "Словосочетания: \"Ты самая лучшая, добрая, красивая, нежная, верная\", наша команда напишет в любом случае, а от тебя нам нужны конкретные детали:",

        "",

        "Где вы познакомились и в каком возрасте? Сколько лет дружите?",

        "Какой поступок или событие, по твоему мнению, особенно трогательно и важно в воспоминаниях для вас обеих?",

        "Какие слова и действия подруги подчеркнули для тебя ее поддержку и верность?",

        "Есть ли у тебя с подругой милые слова друг для друга?",

        "Вспомни весёлый случай, когда вы с подругой вместе смеялись. Что тогда произошло?",

        "Какой самый незабываемый сюрприз, праздник или подарок подруга для тебя делала?",

        "Есть ли у вас совместные путешествия, поездки или любимое времяпрепровождение?",

        "Вспомните трогательные проявления твоей подруги как жены, сестры, подруги (что ты можешь подчеркнуть) ее отношение к другим членам семьи? Любовь к питомцам?",

        " Чему она тебя научила или чему научили тебя эти отношения?",

        "",

        "Отвечая на эти вопросы поищи теплые общие воспоминания, которые вызовут трепет, радость и мурашки у твоей подруги, которые смогут тронуть ее сердце. Ты можешь написать нам в свободной форме, не опираясь на список вопросов. Для создания трогательной и душевной песни, мы ждем от тебя 5-8 уникальных фактов про ваши отношения и о твоей подруге.",

        "Счастливых вам воспоминаний и мы ждем вашу историю."

    ]

    

    # Вопросы для сестры

    sister_to_sister = [

        "Дорогая (имя), сегодня мы вместе с тобой создаем песню для твоей любимой сестры (имя), давай сделаем этот подарок запоминающимся и трогательным. Ответь пожалуйста на вопросы, которые помогут нам сделать песню до-мурашек.",

        "",

        "Словосочетания: \"Ты самая лучшая, добрая, красивая, нежная\", наша команда напишет в любом случае, а от тебя нам нужны конкретные детали:",

        "",

        "Сколько тебе лет и сколько лет твоей сестре?",

        "Какой поступок или событие, по твоему мнению, особенно трогательно и важно в воспоминаниях для вас обеих?",

        "Какие слова и действия сестры подчеркнули для тебя ее поддержку и опору?",

        "Есть ли у вас с сестрой милые слова друг для друга?",

        "Вспомни весёлый случай, когда вы с сестрой вместе смеялись. Что тогда произошло?",

        "Какой самый незабываемый сюрприз, праздник или подарок сестра для тебя делала?",

        "Есть ли у вас совместные путешествия, поездки или любимое времяпрепровождение?",

        "Вспомни трогательные проявления твоей сестры как дочери, жены, сестры, подруги (что ты можешь подчеркнуть) ее отношение к другим членам семьи? Любовь к питомцам?",

        "Чему она тебя научила или чему ты ее научила, что вы может быть вместе любили делать?",

        "",

        "Отвечая на эти вопросы поищи теплые общие воспоминания, которые вызовут трепет, радость и мурашки у твоей сестренки, которые смогут тронуть ее сердце. Ты можешь написать нам в свободной форме, не опираясь на список вопросов. Для создания трогательной и душевной песни, мы ждем от тебя 5-8 уникальных фактов про ваши отношения и о твоей сестре.",

        "Счастливых вам воспоминаний и мы ждем вашу историю."

    ]

    

    # Вопросы для сестры к брату

    sister_to_brother = [

        "Дорогая (имя), сегодня мы вместе с тобой создаем песню для твоего любимого брата (имя) , давай сделаем этот подарок запоминающимся и трогательным. Ответь пожалуйста на вопросы, которые помогут нам сделать песню до-мурашек.",

        "",

        "Словосочетания: \"Ты самый лучший, добрый, надежный, сильный\", наша команда напишет в любом случае, а от тебя нам нужны конкретные детали:",

        "",

        "Сколько тебе лет и сколько лет твоему брату?",

        "Какой поступок или событие, по твоему мнению, особенно трогательно и важно в воспоминаниях для вас обеих?",

        "Какие слова и действия брата подчеркнули для тебя его поддержку и опору?",

        "Есть ли у вас с братом милые слова друг для друга?",

        "Вспомни весёлый случай, когда вы с братом вместе смеялись. Что тогда произошло?",

        "Какой самый незабываемый сюрприз, праздник или подарок брат для тебя делал?",

        "Если ли у вас совместные путешествия, поездки, любимое времяпрепровождение, общие детские игры или игрушки?",

        "Вспомни трогательные проявления твоего брата как сына, мужа, отца, друга (что ты можете подчеркнуть) его отношение к другим членам семьи? Любовь к питомцам?",

        "Чему он тебя научил или чему ты его научила, что вы может быть вместе любили делать?",

        "10. Были ли забавные ссоры у вас, из-за чего вы ссорились? (игрушки, питомцы, друзья, подарки)",

        "",

        "Отвечая на эти вопросы поищи теплые общие воспоминания, которые вызовут трепет, радость и мурашки у твоего брата, которые смогут тронуть его сердце. Ты можешь написать нам в свободной форме, не опираясь на список вопросов. Для создания трогательной и душевной песни, мы ждем от тебя 5-8 уникальных фактов про ваши отношения и о твоем брате.",

        "Счастливых вам воспоминаний и мы ждем вашу историю."

    ]

    

    # Вопросы для брата к сестре

    brother_to_sister = [

        "Дорогой (имя), сегодня мы вместе с тобой создаем песню для твоей любимой сестры (имя), давай сделаем этот подарок запоминающимся и трогательным. Ответь пожалуйста на вопросы, которые помогут нам сделать песню до-мурашек.",

        "",

        "Словосочетания: \"Ты самая лучшая, добрая, красивая, нежная\", наша команда напишет в любом случае, а от тебя нам нужны конкретные детали:",

        "",

        "Сколько вам лет и сколько лет вашей сестре? В каких городах живете?",

        "Какое событие, которое вы уверены трогательно в воспоминаниях для вас обоих?",

        "Какие слова и действия сестры подчеркнули для вас ее поддержку и опору?",

        "Есть ли у вас с сестрой милые слова друг для друга?",

        "Вспомните весёлый случай, когда вы с сестрой вместе смеялись. Что тогда произошло?",

        "Какой самый незабываемый сюрприз, праздник или подарок сестра для вас делала?",

        "Есть ли у вас совместные путешествия, поездки или любимое времяпрепровождение?",

        "Вспомните трогательные проявления вашей сестры как дочери, жены, сестры, подруги (что вы можете подчеркнуть) ее отношения к другим членам семьи? Любовь к питомцам?",

        "Чему она вас научила или чему вы ее научили, что вы может быть вместе любили делать?",

        "",

        "Отвечая на эти вопросы поищи теплые общие воспоминания, которые вызовут трепет, радость и мурашки у твоей сестренки, которые смогут тронуть ее сердце. Ты можешь написать нам в свободной форме, не опираясь на список вопросов. Для создания трогательной и душевной песни, мы ждем от тебя 5-8 уникальных фактов про ваши отношения и о твоей сестре.",

        "Счастливых вам воспоминаний и мы ждем вашу историю."

    ]

    

    # Вопросы для брата

    brother_to_brother = [

        "Что ты особенно ценишь в отношениях с братом?",

        "Какое воспоминание с братом тебе особенно дорого?",

        "Были ли у вас с ним «секретные» занятия или традиции?",

        "Чему научил тебя брат?",

        "Что он делал, когда тебе было трудно?",

        "Как он выражает свою заботу?",

        "Какие у него увлечения и интересы, о которых ты рассказываешь с гордостью?",

        "Чем вы любите заниматься вместе?"

    ]

    

    # Вопросы для сына

    parent_to_son = [

        "Дорогая (имя), сегодня мы вместе с тобой создаем песню для твоего любимого сына, давай сделаем этот подарок запоминающимся и трогательным. Ответь пожалуйста на вопросы, которые помогут нам сделать песню до-мурашек.",

        "",

        "Словосочетания: \"Ты самый лучший, добрый, надежный и смелый\", наша команда напишет в любом случае, а от тебя нам нужны конкретные детали:",

        "",

        "Какой момент с сыном вы считаете самым трогательным из детства /юности?",

        "Какими его достижениями ты гордилась в детстве или сейчас?",

        "Какой самый трепетный подарок вы получали от него на праздники?",

        "Есть ли у вас с сыном милые слова друг для друга?",

        "Вспомни, где ты его чему-то учила и вы делали это вместе? (готовить, кататься на коньках, учиться)?",

        "Какой самый важный и сложный момент вы вместе прошли, прожили, были опорой друг для друга?",

        "Какие хобби у твоего сына, чем он увлечен, в чем ты его поддерживаешь?",

        "Трогательные проявления твоего сына, как брата, мужа, отца, друга (что ты можешь подчеркнуть) его отношение к другим членам семьи? Любовь к питомцам?",

        "Ты живешь с сыном в одном городе или расстояние между вами? (города указать)",

        "",

        "Отвечая на эти вопросы поищи теплые общие воспоминания, которые вызовут трепет, радость и мурашки у твоего сына, которые смогут тронуть его сердце. Ты можешь написать нам в свободной форме, не опираясь на список вопросов. Для создания трогательной и душевной песни, мы ждем от тебя 5-8 уникальных фактов про ваши отношения и о твоем сыне.",

        "Счастливых вам воспоминаний и мы ждем вашу историю."

    ]

    

    # Вопросы для дочери

    parent_to_daughter = [

        "Дорогая (имя), сегодня мы вместе с тобой создаем песню для твоей любимой дочки, давай сделаем этот подарок запоминающимся и трогательным. Ответь пожалуйста на вопросы, которые помогут нам сделать песню до-мурашек.",

        "",

        "Словосочетания: \"Ты самая лучшая, добрая, красивая и нежная\", наша команда напишет в любом случае, а от тебя нам нужны конкретные детали:",

        "",

        "Какой момент с дочкой ты считаешь самым трогательным из детства /юности?",

        "Какими ее достижениями ты гордилась в детстве или сейчас?",

        "Какой самый трепетный подарок ты получала от нее на праздники?",

        "Есть ли у вас с дочкой милые слова друг для друга?",

        "Вспомни, где ты ее чему-то учила и вы делали это вместе? (готовить, стирать, рисовать, шить)?",

        "Какой самый важный и сложный момент вы вместе прошли, прожили, были опорой друг для друга?",

        "Какие хобби у твоей дочери, чем она увлечена, в чем ты ее поддерживаешь?",

        "Трогательные проявления твоей дочери, как сестры, жены, мамы, подруги (что ты можешь подчеркнуть) ее отношение к другим членам семьи? Любовь к питомцам?",

        "Ты живешь с дочкой в одном городе или расстояние между вами? (города указать)",

        "",

        "Отвечая на эти вопросы поищи теплые общие воспоминания, которые вызовут трепет, радость и мурашки у твоей дочери, которые смогут тронуть ее сердце. Ты можешь написать нам в свободной форме, не опираясь на список вопросов. Для создания трогательной и душевной песни, мы ждем от тебя 5-8 уникальных фактов про ваши отношения и о твоей доченьке.",

        "Счастливых вам воспоминаний и мы ждем вашу историю."

    ]

    

    # Вопросы для отца к сыну

    father_to_son = [

        "Дорогой (имя), сегодня мы вместе с тобой создаем песню для твоего любимого сына, давай сделаем этот подарок запоминающимся и трогательным. Ответь пожалуйста на вопросы, которые помогут нам сделать песню до-мурашек.",

        "",

        "Словосочетания: \"Ты самый лучший, добрый, надежный и смелый\", наша команда напишет в любом случае, а от тебя нам нужны конкретные детали:",

        "",

        "Какой момент с сыном ты считаешь самым трогательным из детства /юности?",

        "Какими его достижениями ты гордился в детстве или сейчас?",

        "Какой самый трепетный подарок ты получал от него на праздники?",

        "Есть ли у вас с сыном милые слова друг для друга?",

        "Вспомни, где ты его чему-то учил и вы делали это вместе? (готовить, кататься на коньках, учиться)?",

        "Какой самый важный и сложный момент вы вместе прошли, прожили, были опорой друг для друга?",

        "Какие хобби у твоего сына, чем он увлечен, в чем ты его поддерживаешь?",

        "Трогательные проявления твоего сына, как брата, мужа, отца, друга (что ты можешь подчеркнуть) его отношение к другим членам семьи? Любовь к питомцам?",

        "Ты живешь с сыном в одном городе или расстояние между вами? (города указать)",

        "",

        "Отвечая на эти вопросы поищи теплые общие воспоминания, которые вызовут трепет, радость и мурашки у твоего сына, которые смогут тронуть его сердце. Ты можешь написать нам в свободной форме, не опираясь на список вопросов. Для создания трогательной и душевной песни, мы ждем от тебя 5-8 уникальных фактов про ваши отношения и о твоем сыне.",

        "Счастливых вам воспоминаний и мы ждем вашу историю."

    ]

    

    # Вопросы для отца к дочери

    father_to_daughter = [

        "Дорогой (имя), сегодня мы вместе с тобой создаем песню для твоей любимой дочки, давай сделаем этот подарок запоминающимся и трогательным. Ответь пожалуйста на вопросы, которые помогут нам сделать песню до-мурашек.",

        "",

        "Словосочетания: \"Ты самая лучшая, добрая, красивая и нежная\", наша команда напишет в любом случае, а от тебя нам нужны конкретные детали:",

        "",

        "Какой момент с дочкой ты считаешь самым трогательным из детства /юности?",

        "Какими ее достижениями ты гордился в детстве или сейчас?",

        "Какой самый трепетный подарок ты получал от нее на праздники?",

        "Есть ли у вас с дочкой милые слова друг для друга?",

        "Вспомни, где ты ее чему-то учил и вы делали это вместе? (готовить, стирать, рисовать, шить)?",

        "Какой самый важный и сложный момент вы вместе прошли, прожили, были опорой друг для друга?",

        "Какие хобби у твоей дочери, чем она увлечена, в чем ты ее поддерживаешь?",

        "Трогательные проявления твоей дочери, как сестры, жены, мамы, подруги (что ты можешь подчеркнуть) ее отношение к другим членам семьи? Любовь к питомцам?",

        "Ты живешь с дочкой в одном городе или расстояние между вами? (города указать)",

        "",

        "Отвечая на эти вопросы поищи теплые общие воспоминания, которые вызовут трепет, радость и мурашки у твоей дочери, которые смогут тронуть ее сердце. Ты можешь написать нам в свободной форме, не опираясь на список вопросов. Для создания трогательной и душевной песни, мы ждем от тебя 5-8 уникальных фактов про ваши отношения и о твоей доченьке.",

        "Счастливых вам воспоминаний и мы ждем вашу историю."

    ]

    

    # Определяем вопросы в зависимости от типа связи и пола

    if relation == "Любимому" and gender == "девушка":

        return wife_to_husband

    elif relation == "Любимой" and gender == "парень":

        return husband_to_wife

    elif relation == "Маме":

        # Проверяем пол создателя песни

        if gender == "парень" or gender == "мальчик":

            return son_to_mom

        else:

            return child_to_mom

    elif relation == "Папе":

        # Проверяем пол создателя песни

        if gender == "парень" or gender == "мальчик":

            return son_to_dad

        else:

            return child_to_dad

    elif relation == "Бабушке":

        # Проверяем пол создателя песни

        if gender == "парень" or gender == "мальчик":

            return grandson_to_grandma

        else:

            return grandchild_to_grandma

    elif relation == "Дедушке":

        # Проверяем пол создателя песни

        if gender == "парень" or gender == "мальчик":

            return grandson_to_grandpa

        else:

            return grandchild_to_grandpa

    elif relation == "Подруге":

        return friend_to_friend

    elif relation == "Сестре":

        # Проверяем пол создателя песни

        if gender == "парень" or gender == "мальчик":

            return brother_to_sister

        else:

            return sister_to_sister

    elif relation == "Брату":

        # Проверяем, кто создает песню для брата

        if gender == "девушка":

            return sister_to_brother

        else:

            return brother_to_brother

    elif relation == "Сыну":

        # Проверяем пол создателя песни

        if gender == "парень" or gender == "мальчик":

            return father_to_son

        else:

            return parent_to_son

    elif relation == "Дочери":

        # Проверяем пол создателя песни

        if gender == "парень" or gender == "мальчик":

            return father_to_daughter

        else:

            return parent_to_daughter

    elif relation == "Парню":

        return girlfriend_to_boyfriend

    elif relation == "Девушке":

        return boyfriend_to_girlfriend

    else:

        # По умолчанию возвращаем вопросы для пар

        if gender == "девушка":

            return wife_to_husband

        else:

            return husband_to_wife



# Обработчики для кнопок "Другое" (должны быть выше startswith обработчиков)

@dp.callback_query(F.data == "q1_other")

async def story_q1_other(callback: types.CallbackQuery, state: FSMContext):

    await callback.message.edit_text("Пожалуйста, напишите ваш ответ:")

    await state.set_state(StoryQuestionsStates.q1)

    await callback.answer()

    await log_state(callback.message, state)



@dp.callback_query(F.data == "q2_other")

async def story_q2_other(callback: types.CallbackQuery, state: FSMContext):

    await callback.message.edit_text("Пожалуйста, напишите ваш ответ:")

    await state.set_state(StoryQuestionsStates.q2)

    await callback.answer()

    await log_state(callback.message, state)



@dp.callback_query(F.data == "q3_other")

async def story_q3_other(callback: types.CallbackQuery, state: FSMContext):

    await callback.message.edit_text("Пожалуйста, напишите ваш ответ:")

    await state.set_state(StoryQuestionsStates.q3)

    await callback.answer()

    await log_state(callback.message, state)



@dp.callback_query(F.data.startswith("q1_"))

async def story_q1(callback: types.CallbackQuery, state: FSMContext):

    answer_index = callback.data.replace("q1_", "")
    
    # Получаем вопросы из состояния чтобы найти текст ответа
    data = await state.get_data()
    questions = data.get("story_questions", {})
    q1_question = questions.get("q1", {"options": []})
    
    # Находим текст ответа по индексу
    try:
        answer_text = q1_question["options"][int(answer_index)]
    except (IndexError, ValueError):
        answer_text = answer_index  # Fallback к старому поведению
    
    await state.update_data(story_q1=answer_text)

    

    # Сохраняем промежуточные данные в БД

    await update_order_progress(state)

    

    print(f"🔍 ОТЛАДКА: Сохранен ответ q1: {answer_text} (индекс: {answer_index})")

    

    # Получаем вопросы из состояния

    data = await state.get_data()

    questions = data.get("story_questions", {})

    q2_question = questions.get("q2", {"text": "Тёплое воспоминание:", "options": ["Школа", "Когда болела", "Поддержка"]})

    

    # Вопрос 2

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text=option, callback_data=f"q2_{i}")] 

        for i, option in enumerate(q2_question["options"])

    ] + [[InlineKeyboardButton(text="Другое", callback_data="q2_other")]])

    

    await callback.message.edit_text(q2_question["text"], reply_markup=keyboard)

    # Очищаем пользовательские ответы при переходе к новому вопросу

    await state.update_data(story_q1_user_answer=None)

    await state.set_state(StoryQuestionsStates.q2)

    await callback.answer()

    await log_state(callback.message, state)



@dp.callback_query(F.data.startswith("q2_"))

async def story_q2(callback: types.CallbackQuery, state: FSMContext):

    answer_index = callback.data.replace("q2_", "")
    
    # Получаем вопросы из состояния чтобы найти текст ответа
    data = await state.get_data()
    questions = data.get("story_questions", {})
    q2_question = questions.get("q2", {"options": []})
    
    # Находим текст ответа по индексу
    try:
        answer_text = q2_question["options"][int(answer_index)]
    except (IndexError, ValueError):
        answer_text = answer_index  # Fallback к старому поведению
    
    await state.update_data(story_q2=answer_text)

    

    # Сохраняем промежуточные данные в БД

    await update_order_progress(state)

    

    print(f"🔍 ОТЛАДКА: Сохранен ответ q2: {answer_text} (индекс: {answer_index})")

    

    # Получаем вопросы из состояния

    data = await state.get_data()

    questions = data.get("story_questions", {})

    q3_question = questions.get("q3", {"text": "Чему мама научила:", "options": ["Коньки", "Велосипед", "Рисовать", "Готовить"]})

    

    # Вопрос 3

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text=option, callback_data=f"q3_{i}")] 

        for i, option in enumerate(q3_question["options"])

    ] + [[InlineKeyboardButton(text="Другое", callback_data="q3_other")]])

    

    await callback.message.edit_text(q3_question["text"], reply_markup=keyboard)

    # Очищаем пользовательские ответы при переходе к новому вопросу

    await state.update_data(story_q2_user_answer=None)

    await state.set_state(StoryQuestionsStates.q3)

    await callback.answer()

    await log_state(callback.message, state)



# Обработчики для текстовых ответов на вопросы анкеты

@dp.message(StateFilter(StoryQuestionsStates.q1))

async def story_q1_text(message: types.Message, state: FSMContext):

    await state.update_data(story_q1=message.text, story_q1_user_answer=message.text)

    # Сохраняем промежуточные данные в БД

    await update_order_progress(state)

    

    # Отправляем уведомление менеджеру о пользовательском ответе

    data = await state.get_data()

    order_id = data.get('order_id')

    if order_id:

        await add_outbox_task(

            order_id=order_id,

            user_id=message.from_user.id,

            type_="manager_notification",

            content=f"📝 Заказ #{order_id}: Ответ на вопрос 1 (свой вариант): {message.text}"

        )

    

    # Получаем вопросы из состояния

    data = await state.get_data()

    questions = data.get("story_questions", {})

    q2_question = questions.get("q2", {"text": "Тёплое воспоминание:", "options": ["Школа", "Когда болела", "Поддержка"]})

    

    # Вопрос 2

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text=option, callback_data=f"q2_{i}")] 

        for i, option in enumerate(q2_question["options"])

    ] + [[InlineKeyboardButton(text="Другое", callback_data="q2_other")]])

    

    await message.answer(q2_question["text"], reply_markup=keyboard)

    # Очищаем пользовательские ответы при переходе к новому вопросу

    await state.update_data(story_q1_user_answer=None)

    await state.set_state(StoryQuestionsStates.q2)

    await log_state(message, state)



@dp.message(StateFilter(StoryQuestionsStates.q2))

async def story_q2_text(message: types.Message, state: FSMContext):

    await state.update_data(story_q2=message.text, story_q2_user_answer=message.text)

    # Сохраняем промежуточные данные в БД

    await update_order_progress(state)

    

    # Отправляем уведомление менеджеру о пользовательском ответе

    data = await state.get_data()

    order_id = data.get('order_id')

    if order_id:

        await add_outbox_task(

            order_id=order_id,

            user_id=message.from_user.id,

            type_="manager_notification",

            content=f"📝 Заказ #{order_id}: Ответ на вопрос 2 (свой вариант): {message.text}"

        )

    

    # Получаем вопросы из состояния

    data = await state.get_data()

    questions = data.get("story_questions", {})

    q3_question = questions.get("q3", {"text": "Чему мама научила:", "options": ["Коньки", "Велосипед", "Рисовать", "Готовить"]})

    

    # Вопрос 3

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text=option, callback_data=f"q3_{i}")] 

        for i, option in enumerate(q3_question["options"])

    ] + [[InlineKeyboardButton(text="Другое", callback_data="q3_other")]])

    

    await message.answer(q3_question["text"], reply_markup=keyboard)

    # Очищаем пользовательские ответы при переходе к новому вопросу

    await state.update_data(story_q2_user_answer=None)

    await state.set_state(StoryQuestionsStates.q3)

    await log_state(message, state)



@dp.message(StateFilter(StoryQuestionsStates.q3))

async def story_q3_text(message: types.Message, state: FSMContext):

    await state.update_data(story_q3=message.text)

    await update_order_progress(state, status="questions_completed")

    

    # Отправляем уведомление менеджеру о пользовательском ответе

    data = await state.get_data()

    order_id = data.get('order_id')

    if order_id:

        await add_outbox_task(

            order_id=order_id,

            user_id=message.from_user.id,

            type_="manager_notification",

            content=f"📝 Заказ #{order_id}: Ответ на вопрос 3 (свой вариант): {message.text}"

        )

    

    # Отправляем сообщение пользователю о том, что заказ в работе
    await message.answer(
        f"Заказ №{order_id:04d} в работе 🦋\n"
        f"Иллюстратор бережно создает сюжеты, а авторы наполняют её самыми трогательными словами. Совсем скоро пробные страницы будут готовы ☑️"
    )
    
    # Создаем таймер для этапа waiting_demo_book (Глава 2: Ожидание демо-контента книги)
    from db import create_or_update_user_timer
    await create_or_update_user_timer(message.from_user.id, order_id, "waiting_demo_book", "Книга")
    logging.info(f"✅ Создан таймер для этапа waiting_demo_book (Глава 2), пользователь {message.from_user.id}, заказ {order_id}")

    # Переходим к упрощенному выбору страниц
    await state.set_state(BookFinalStates.choosing_pages)

    

    # Отправляем уведомление менеджеру через outbox

    await add_outbox_task(

        order_id=order_id,

        user_id=message.from_user.id,

        type_="manager_notification",

        content=f"Заказ #{order_id} готов к загрузке страниц (упрощенный флоу). Пользователь завершил вопросы."

    )

    

    # УБРАНО: отложенное сообщение с заглушкой - оно не нужно
    # Теперь пользователь будет ждать демо-контент от менеджера без промежуточных сообщений

    

    await log_state(message, state)



# Для генерации уникального номера заказа (можно заменить на реальную логику из БД)

def get_order_number(user_id):

    return f"{int(user_id)%10000:04d}"



@dp.callback_query(F.data.startswith("q3_"))

async def story_q3(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    answer_index = callback.data.replace("q3_", "")
    
    # Получаем вопросы из состояния чтобы найти текст ответа
    data = await state.get_data()
    questions = data.get("story_questions", {})
    q3_question = questions.get("q3", {"options": []})
    
    # Находим текст ответа по индексу
    try:
        answer_text = q3_question["options"][int(answer_index)]
    except (IndexError, ValueError):
        answer_text = answer_index  # Fallback к старому поведению
    
    await state.update_data(story_q3=answer_text)

    await update_order_progress(state, status="questions_completed")

    

    print(f"🔍 ОТЛАДКА: Сохранен ответ q3: {answer_text} (индекс: {answer_index})")

    

    # Сообщение с реальным номером заказа

    data = await state.get_data()

    order_id = data.get('order_id')

    await callback.message.edit_text(

        f"Заказ №{order_id:04d} в работе 🦋\n"

        f"Иллюстратор бережно создает сюжеты, а авторы наполняют её самыми трогательными словами. Совсем скоро пробные страницы будут готовы ☑️"

    )
    
    # Создаем таймер для этапа waiting_demo_book (Глава 2: Ожидание демо-контента книги)
    from db import create_or_update_user_timer
    await create_or_update_user_timer(callback.from_user.id, order_id, "waiting_demo_book", "Книга")
    logging.info(f"✅ Создан таймер для этапа waiting_demo_book (Глава 2), пользователь {callback.from_user.id}, заказ {order_id}")

    

    # Переходим к упрощенному выбору страниц

    await state.set_state(BookFinalStates.choosing_pages)

    

    # Отправляем уведомление менеджеру через outbox

    await add_outbox_task(

        order_id=order_id,

        user_id=callback.from_user.id,

        type_="manager_notification",

        content=f"Заказ #{order_id} готов к загрузке страниц (упрощенный флоу). Пользователь завершил вопросы."

    )

    

    # УБРАНО: отложенное сообщение с заглушкой согласно Главе 11

    

    await log_state(callback.message, state)



# Обработка кнопки "Продолжить создание" после демонстрации

@dp.callback_query(F.data == "continue_after_demo")

async def after_demo_continue(callback: types.CallbackQuery, state: FSMContext):

    try:

        logging.info(f"🔘 Кнопка 'Продолжить создание' нажата пользователем {callback.from_user.id}")

        

        # Получаем данные пользователя

        data = await state.get_data()

        order_id = data.get('order_id')

        

        # Трекинг: пользователь нажал "Узнать цену" после демо книги
        await track_event(
            user_id=callback.from_user.id,
            event_type='demo_learn_price_clicked',
            event_data={
                'order_id': order_id,
                'clicked_at': datetime.now().isoformat()
            },
            step_name='demo_learn_price_clicked',
            product_type='Книга',
            order_id=order_id
        )

        logging.info(f"📋 Данные пользователя: order_id={order_id}, data={data}")

        logging.info(f"📋 Тип продукта в state: {data.get('product', 'НЕ УКАЗАН')}")

        

        # Определяем тип продукта

        product = data.get('product', 'Книга')  # Берем из state, если есть

        try:

            if order_id:

                order = await get_order(order_id)

                logging.info(f"🔍 Получен заказ: {order}")

                if order and order.get('order_data'):

                    order_data = json.loads(order.get('order_data', '{}'))

                    product_from_db = order_data.get('product', '')

                    if product_from_db:  # Если в БД есть тип продукта, используем его

                        product = product_from_db

                        logging.info(f"📦 Определен тип продукта из БД: {product}")

                    else:

                        logging.info(f"📦 Используем тип продукта из state: {product}")

                    logging.info(f"📦 Данные заказа: {order_data}")

                else:

                    logging.warning(f"⚠️ Нет order_data в заказе {order_id}")

            else:

                logging.warning(f"⚠️ Нет order_id в состоянии")

        except Exception as e:

            logging.error(f"❌ Ошибка определения типа продукта: {e}")

            import traceback

            logging.error(f"❌ Traceback: {traceback.format_exc()}")

        

        logging.info(f"🎯 Финальный тип продукта: {product}")

        

        if product == "Песня":

            logging.info(f"🎵 Обрабатываем заказ песни для пользователя {callback.from_user.id}")
            
            # Создаем таймер для этапа demo_received_song после получения демо
            if order_id:
                try:
                    from db import deactivate_user_timers, create_or_update_user_timer
                    await deactivate_user_timers(callback.from_user.id, order_id)
                    await create_or_update_user_timer(callback.from_user.id, order_id, "demo_received_song", "Песня")
                    logging.info(f"✅ Создан таймер для этапа demo_received_song после получения демо, пользователь {callback.from_user.id}, заказ {order_id}")
                except Exception as e:
                    logging.error(f"❌ Ошибка создания таймера для demo_received_song: {e}")

            # Для песни - переход к оплате

            try:

                song_price = await get_product_price_async("Песня", "💌 Персональная песня")

                logging.info(f"💰 Получена цена для песни: {song_price}")

            except Exception as e:

                logging.error(f"❌ Ошибка получения цены песни: {e}")

                song_price = 2990  # Резервная цена

            

            # Создаем платеж в ЮKassa для песни

            description = format_payment_description("Песня", "💌 Персональная песня", order_id)

            payment_data = await create_payment(order_id, song_price, description, "Песня")

            

            # Сохраняем данные платежа в state

            await state.update_data(

                payment_id=payment_data['payment_id'],

                payment_url=payment_data['confirmation_url'],

                format="🎵 Песня",

                price=song_price

            )

            

            keyboard = InlineKeyboardMarkup(inline_keyboard=[

                [InlineKeyboardButton(text="Заказать песню", url=payment_data['confirmation_url'])],

                [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="check_payment")],


            ])

            

            # Формируем сводку заказа для песни из базы данных

            order_data = await get_order_summary_data(order_id, state)

            order_summary = ""

            

            await callback.message.answer(

                f"Спасибо, что хочешь продолжить🙏🏻\n"

                f"Мы выбрали для тебя самый тёплый формат.\n\n"

                f"✨ Авторская песня по вашей истории длительностью 3 минуты с трогательными поздравительными словами от тебя за 2900 рублей.\n\n"

                f"Это не просто музыка, а подарок, в котором оживают твои воспоминания, детали вашей истории и чувства.\n"

                f"Он передаст то, что невозможно купить - искреннюю любовь❤️\n"

                f"Такая песня тронет до мурашек и станет воспоминанием, которое останется навсегда.\n\n"

                f"Мы бережно соберём самые важные моменты и превратим их в тёплый текст.\n"

                f"Далее мы добавим уникальную аранжировку, чтобы песня звучала именно про вас 🎶\n"

                f"И отправим тебе версию на утверждение, чтобы каждое слово попало \"В самое сердце\"❤️",

                reply_markup=keyboard,

                parse_mode="HTML"

            )

            await callback.answer()

            logging.info(f"✅ Оплата песни отправлена пользователю {callback.from_user.id}")

            

        else:

            logging.info(f"📖 Обрабатываем заказ книги для пользователя {callback.from_user.id}")

            

            # Проверяем, был ли уже выбран формат при оплате

            existing_format = None

            existing_price = None

            try:

                if order_id:

                    order = await get_order(order_id)

                    if order and order.get('order_data'):

                        order_data = json.loads(order.get('order_data', '{}'))

                        existing_format = order_data.get('format')

                        existing_price = order_data.get('price')

                        logging.info(f"🔍 Найден существующий формат в заказе: {existing_format}, цена: {existing_price}")

            except Exception as e:

                logging.error(f"❌ Ошибка проверки существующего формата: {e}")

            

            # Если формат уже выбран, переходим сразу к созданию книги

            if existing_format and existing_price:

                logging.info(f"✅ Формат уже выбран: {existing_format}, переходим к созданию книги")

                await state.update_data(format=existing_format, price=existing_price)

                

                # Переходим к созданию книги

                await state.set_state(BookCreationStates.waiting_for_hero_intro)

                await callback.message.answer(

                    "✨ Авторская книга по вашей уникальной истории — с иллюстрациями ваших героев и трогательными словами, собранными специально для тебя 💝\n\n"

                    "Она состоит из 26 страниц, вы можете выбрать ее в нескольких форматах:\n\n"

                    f"Печатная книга в твердом переплете — {combo_price} рублей;\n"

                    f"Электронная версия — {ebook_price} рублей;\n"

                    "Доставка оплачивается отдельно в зависимости от региона проживания.\n\n"

                    "Это не просто книга, а подарок, в котором оживают воспоминания.\n"

                    "Осталось только выбрать сюжеты и обложку.\n\n"

                    "Давайте начнем! Расскажи, кто главный герой твоей истории? 👤",

                    parse_mode="HTML"

                )

                await callback.answer()

                await log_state(callback.message, state)

                return

            

            # Если формат не выбран, показываем выбор формата

            try:

                ebook_price = await get_product_price_async("Книга", "📄 Электронная книга")

                combo_price = await get_product_price_async("Книга", "📦 Печатная версия")

                logging.info(f"💰 Получены цены: ebook={ebook_price}, combo={combo_price}")

            except Exception as e:

                logging.error(f"❌ Ошибка получения цен: {e}")

                # Если не удалось получить цены из БД, используем резервные

                ebook_price = 1990

                combo_price = 7639

            

            # Этап выбора формата

            keyboard = InlineKeyboardMarkup(inline_keyboard=[

                [InlineKeyboardButton(text=f"Печатная версия — {combo_price} рублей", callback_data="format_combo")],

                [InlineKeyboardButton(text=f"Электронная версия — {ebook_price} рублей", callback_data="format_ebook")],

            ])

            logging.info(f"🎯 Отправляем выбор формата пользователю {callback.from_user.id}")

            

            # Отправляем новое сообщение вместо редактирования (так как предыдущее сообщение содержит изображение)

            await callback.message.answer(

                "✨ Авторская книга по вашей уникальной истории — с иллюстрациями ваших героев и трогательными словами, собранными специально для тебя 💝\n\n"

                "Она состоит из 26 страниц, вы можете выбрать ее в нескольких форматах:\n\n"

                f"Печатная книга в твердом переплете — {combo_price} рублей;\n"

                f"Электронная версия — {ebook_price} рублей;\n"

                "Доставка оплачивается отдельно в зависимости от региона проживания.\n\n"

                "Это не просто книга, а подарок, в котором оживают воспоминания.\n"

                "Осталось только выбрать сюжеты и обложку.\n"

                "Наша команда бережно соберёт самые важные моменты и превратит их в трогательные иллюстрации и текст, чтобы каждая страница тронула ваши сердца ❤️\n\n"

                "Мы отправим тебе первую версию книги на утверждение.",

                reply_markup=keyboard

            )

            await callback.answer()

            logging.info(f"✅ Выбор формата отправлен пользователю {callback.from_user.id}")

        

        await log_state(callback.message, state)

    except Exception as e:

        logging.error(f"❌ Ошибка в after_demo_continue: {e}")

        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

        try:

            await callback.message.answer("Произошла ошибка при переходе к оплате. Попробуйте еще раз или обратитесь в поддержку.")

        except:

            pass



@dp.callback_query(F.data.in_(["format_ebook", "format_combo"]))

async def format_chosen(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    format_choice = callback.data

    data = await state.get_data()

    order_id = data.get('order_id')

    

    # Получаем актуальные цены из базы данных

    try:

        if format_choice == "format_ebook":

            price = await get_product_price_async("Книга", "📄 Электронная книга")

            format_name = "📄 Электронная книга"

        else:

            price = await get_product_price_async("Книга", "📦 Печатная версия")

            format_name = "📦 Печатная версия"

    except:

        # Если не удалось получить цены из БД, используем резервные

        if format_choice == "format_ebook":

            price = 1990

            format_name = "📄 Электронная книга"

        else:

            price = 7639

            format_name = "📦 Печатная версия"

    

    await state.update_data(format=format_name, price=price)

    

    # Сохраняем данные формата в базу данных

    from db import update_order_data

    await update_order_data(order_id, {'format': format_name, 'price': price})

    

    try:

        # Создаем платеж в ЮKassa

        description = format_payment_description("Книга", format_name, order_id)

        payment_data = await create_payment(order_id, price, description, "Книга")

        

        # Сохраняем данные платежа в state

        await state.update_data(

            payment_id=payment_data['payment_id'],

            payment_url=payment_data['confirmation_url']

        )

        

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="Заказать книгу", url=payment_data['confirmation_url'])],

            [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="check_payment")],


        ])

        

        # Формируем сводку заказа из базы данных

        order_data = await get_order_summary_data(order_id, state)

        order_summary = ""

        

        # Исправляем цену для электронной книги

        display_price = price

        if format_name == "📄 Электронная книга":

            try:
                display_price = await get_product_price_async("Книга", "📄 Электронная книга")
            except:
                display_price = 1990

        

        await safe_edit_message(

            callback.message,

            f"{order_summary}\n"

            f"💳 <b>Оплата:</b>\n"

            f"Вы выбрали: <b>{format_name}</b>\n"

            f"Стоимость: <b>{display_price} ₽</b>\n\n"

            f"Для завершения заказа нажмите кнопку оплаты ниже:",

            reply_markup=keyboard,

            parse_mode="HTML"

        )

        

        # Обновляем статус заказа

        await update_order_status(order_id, "waiting_payment")

        

        # Создаем отложенные напоминания об оплате через 24 и 48 часов

        from db import create_payment_reminder_messages

        await create_payment_reminder_messages(order_id, callback.from_user.id)

        

    except Exception as e:

        logging.error(f"Ошибка создания платежа: {e}")

        await safe_edit_message(

            callback.message,

            "Произошла ошибка при создании платежа. Попробуйте позже или обратитесь в поддержку."

        )

    

    await log_state(callback.message, state)



# --- Автоматическая проверка платежей ---

async def auto_check_payments():
    """
    Автоматически проверяет статус платежей каждые 10 секунд
    """
    while True:
        try:
            # Получаем все платежи со статусом 'pending' старше 30 секунд
            # Исключаем тестовые платежи и платежи с ошибками
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute('''
                    SELECT p.*, o.user_id, o.order_data 
                    FROM payments p
                    JOIN orders o ON p.order_id = o.id
                    WHERE p.status = 'pending' 
                    AND p.payment_id NOT LIKE 'test_payment_%'
                    AND p.status NOT IN ('invalid', 'expired', 'error')
                    AND datetime(p.created_at) < datetime('now', '-2 seconds')
                    AND datetime(p.created_at) > datetime('now', '-2 hours')
                ''') as cursor:
                    rows = await cursor.fetchall()
                    
                    for row in rows:
                        payment_id = row[2]  # payment_id
                        order_id = row[1]    # order_id
                        user_id = row[8]     # user_id
                        
                        logging.info(f"🔍 AUTO-CHECK: Проверяем платеж {payment_id} для заказа {order_id}, пользователь {user_id}")
                        
                        # Проверяем статус платежа в ЮKassa
                        try:
                            payment_status = await get_payment_status(payment_id)
                            
                            if payment_status and payment_status.get('status') == 'succeeded':
                                logging.info(f"🔄 AUTO-CHECK: Найден успешный платеж {payment_id} для заказа {order_id}")
                                logging.info(f"🚀 АВТОМАТИЧЕСКАЯ ОБРАБОТКА: Платеж {payment_id} будет обработан автоматически!")
                                
                                # Получаем описание платежа для определения типа
                                payment_data = await get_payment_by_payment_id(payment_id)
                                description = payment_data.get('description', '') if payment_data else ''
                                
                                # logging.info(f"🔄 AUTO-CHECK: Описание платежа: '{description}'")
                                
                                # Обрабатываем успешный платеж
                                webhook_data = {
                                    'event': 'payment.succeeded',
                                    'object': {
                                        'id': payment_id,
                                        'status': 'succeeded',
                                        'amount': {'value': payment_status.get('amount', 0)},
                                        'description': description
                                    }
                                }
                                
                                await process_payment_webhook(webhook_data)
                                
                                # Обновляем статус платежа в БД
                                await update_payment_status(payment_id, 'succeeded')
                                
                                # Принудительно обрабатываем outbox задачи для этого пользователя
                                try:
                                    from db import get_pending_outbox_tasks, update_outbox_task_status
                                    user_tasks = await get_pending_outbox_tasks()
                                    if user_tasks:
                                        for task in user_tasks:
                                            if task.get('user_id') == user_id and task.get('order_id') == order_id:
                                                logging.info(f"🔄 AUTO-CHECK: Принудительно обрабатываем задачу {task.get('id')} для заказа {order_id}")
                                                # Здесь можно добавить принудительную обработку задачи
                                except Exception as force_error:
                                    logging.error(f"❌ AUTO-CHECK: Ошибка принудительной обработки outbox: {force_error}")
                                
                                # Удален код прямой отправки сообщений - используется система outbox
                                logging.info(f"✅ AUTO-CHECK: Платеж {payment_id} обработан, сообщения отправятся через outbox")
                            elif payment_status and payment_status.get('status') == 'canceled':
                                # Платеж отменен - обновляем статус
                                logging.info(f"🔄 AUTO-CHECK: Платеж {payment_id} отменен")
                                await update_payment_status(payment_id, 'canceled')
                        except Exception as payment_error:
                            # Если платеж не найден или есть ошибка доступа - помечаем как недействительный
                            if 'not_found' in str(payment_error) or 'access denied' in str(payment_error) or 'Incorrect payment_id' in str(payment_error):
                                logging.warning(f"🔄 AUTO-CHECK: Платеж {payment_id} не найден или недоступен, помечаем как недействительный")
                                await update_payment_status(payment_id, 'invalid')
                                
                                # Также помечаем заказ как имеющий проблему с платежом
                                try:
                                    from db import update_order_status
                                    await update_order_status(order_id, "payment_error")
                                except:
                                    pass
                            else:
                                logging.error(f"🔄 AUTO-CHECK: Ошибка проверки платежа {payment_id}: {payment_error}")
                            
        except Exception as e:
            logging.error(f"❌ Ошибка автоматической проверки платежей: {e}")
        
        # Очищаем старые недействительные платежи (старше 24 часов)
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                # Помечаем старые недействительные платежи как истекшие
                await db.execute('''
                    UPDATE payments 
                    SET status = 'expired' 
                    WHERE status = 'invalid' 
                    AND datetime(created_at) < datetime('now', '-24 hours')
                ''')
                
                # Удален код помечания платежей 3069* как недействительные - теперь они обрабатываются автоматически
                
                await db.commit()
        except Exception as cleanup_error:
            logging.error(f"❌ Ошибка очистки недействительных платежей: {cleanup_error}")
        
        # Ждем 2 секунды перед следующей проверкой для максимально быстрой обработки
        await asyncio.sleep(2)

# --- Напоминания об оплате (эмуляция через команду /remind) ---

@dp.message(StateFilter(lambda c: c.text == "/remind"))

async def remind_payment(message: types.Message, state: FSMContext):

    # В реальном проекте — запускать через планировщик/cron

    await message.answer(

        "Возможно, цена вас смутила? Мы можем предложить другие варианты — напишите нам."

    )

    await asyncio.sleep(1)  # 1 секунда для тестирования

    await message.answer(

        "Готовы сделать книгу проще, но не менее искренней. Дайте знать, если вам это интересно."

    )

    await log_state(message, state)



# Глава 11. Кастомизация сюжетов - УДАЛЕНА (оставлена только фото-реализация)

# Теперь используется только загрузка фото-страниц через админку



# Функция для показа упрощенного выбора страниц

async def show_simplified_page_selection(message, state):

    """Показывает упрощенный выбор страниц (все страницы + вкладыши одним блоком)"""

    data = await state.get_data()

    order_id = data.get('order_id')

    

    selection_text = (

        f"📖 <b>Выбор страниц для вашей книги</b>\n\n"

        f"Перед вами все сгенерированные страницы и вкладыши.\n"

        f"Выберите минимум <b>24 страницы</b> для вашей книги.\n\n"

        f"После выбора страниц вы сможете настроить оформление первой и последней страницы."

    )

    

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="📖 Начать выбор страниц", callback_data="start_page_selection")],

    ])

    

    await message.answer(selection_text, reply_markup=keyboard, parse_mode="HTML")

    await state.set_state(BookFinalStates.choosing_pages)



# Функции для работы с партиями сюжетов - УДАЛЕНЫ (оставлена только фото-реализация)



# Обработчик для начала выбора страниц

@dp.callback_query(F.data == "start_page_selection")

async def start_page_selection_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    # Показываем упрощенный выбор страниц

    await show_simplified_page_selection(callback.message, state)

    

    await log_state(callback.message, state)



# Обработчик для текстовых сообщений в состоянии выбора страниц

@dp.message(StateFilter(BookFinalStates.choosing_pages), F.text)

async def handle_text_in_story_options(message: types.Message, state: FSMContext):

    """Обрабатывает текстовые сообщения при выборе страниц"""

    print(f"🔍 ОТЛАДКА: Получено текстовое сообщение в состоянии choosing_pages: '{message.text}' от пользователя {message.from_user.id}")

    

    # Сохраняем сообщение пользователя в историю заказа

    await save_user_message_to_history(message, state, "Сообщение при выборе страниц: ")

    

    # Проверяем текущее состояние FSM - если пользователь уже перешел к следующему этапу

    current_state = await state.get_state()

    if current_state and current_state != "BookFinalStates:choosing_pages":

        await message.answer("❌ Выбор страниц уже завершен! Вы перешли к следующему этапу.")

        return

    

    text = message.text.strip().lower()

    

    if text == "далее":

        # Пользователь хочет перейти к выбору оформления обложки

        data = await state.get_data()

        order_id = data.get('order_id')

        selected_pages = data.get(f"selected_pages_{order_id}", [])

        

        if len(selected_pages) == 24:

            # Сохраняем выбранные страницы в базу данных

            order_id = data.get('order_id')

            if order_id:

                await save_selected_pages(order_id, selected_pages)

                print(f"🔍 ОТЛАДКА: Сохранены выбранные страницы для заказа {order_id}: {selected_pages}")

            

            # Переходим к выбору оформления первой и последней страницы книги

            await show_first_last_page_selection(message, state)

        elif len(selected_pages) < 24:

            await message.answer("❌ Сначала выберите ровно 24 страницы, затем напишите 'Далее'.")

        else:

            await message.answer("❌ Выбрано слишком много страниц. Выберите ровно 24 страницы.")

    else:

        # Пользователь отвечает администратору - сохраняем сообщение в историю заказа

        data = await state.get_data()

        order_id = data.get('order_id')

        

        if order_id:

            # Сообщение уже сохранено через save_user_message_to_history выше

            # Создаем или обновляем уведомление для менеджера

            from db import create_or_update_order_notification

            await create_or_update_order_notification(order_id)

            print(f"🔍 ОТЛАДКА: Сообщение уже сохранено через save_user_message_to_history")

            print(f"🔔 ОТЛАДКА: Создано уведомление для заказа {order_id}")

            

            # Не отвечаем пользователю - это диалог с администратором

            # Сообщение будет отображаться в карточке заказа

        else:

            # Если нет order_id, показываем подсказку

            await message.answer("ℹ️ Напишите 'Далее' когда выберете ровно 24 страницы и будете готовы продолжить.")

    

    await log_state(message, state)


# Обработчик сообщений в состоянии ожидания вариантов сюжетов
@dp.message(StateFilter(ManagerContentStates.waiting_story_options), F.text)
async def handle_text_while_waiting_stories(message: types.Message, state: FSMContext):
    """Обрабатывает текстовые сообщения в состоянии ожидания вариантов сюжетов"""
    
    print(f"🔍 ОТЛАДКА: Получено текстовое сообщение в состоянии ManagerContentStates.waiting_story_options: '{message.text}' от пользователя {message.from_user.id}")
    
    # Сохраняем сообщение пользователя в историю заказа
    await save_user_message_to_history(message, state, "Сообщение в ожидании сюжетов: ")
    
    # Проверяем текущее состояние FSM - если пользователь уже перешел к следующему этапу
    current_state = await state.get_state()
    
    if current_state and current_state != "ManagerContentStates:waiting_story_options":
        await message.answer("❌ Ожидание сюжетов завершено! Вы перешли к следующему этапу.")
        return
    
    # Пользователь отвечает администратору - сообщение уже сохранено в историю заказа
    # Не отправляем подтверждение пользователю
    
    await log_state(message, state)


# Функция для выбора оформления первой и последней страницы

async def show_first_last_page_selection(message, state):

    """Показывает выбор оформления первой и последней страницы книги"""

    design_text = (

        "Давай решим какими будут первая и последняя страницы твоей книги:\n\n"

        "📝 <b>Только текст</b> - классическое оформление с текстом.\n"

        "📸 <b>Текст + фото</b> - ты сможешь добавить фотографии к тексту."

    )

    

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="📝 Только текст", callback_data="first_last_text_only")],

        [InlineKeyboardButton(text="📸 Текст + фото", callback_data="first_last_text_photo")],

    ])

    

    await message.answer(design_text, reply_markup=keyboard, parse_mode="HTML")

    await state.set_state(BookFinalStates.choosing_first_last_design)


# Обработчик сообщений в состоянии выбора оформления первой и последней страницы
@dp.message(StateFilter(BookFinalStates.choosing_first_last_design), F.text)
async def handle_text_while_choosing_first_last_design(message: types.Message, state: FSMContext):
    """Обрабатывает текстовые сообщения при выборе оформления первой и последней страницы"""
    
    print(f"🔍 ОТЛАДКА: Получено текстовое сообщение в состоянии BookFinalStates.choosing_first_last_design: '{message.text}' от пользователя {message.from_user.id}")
    
    # Сохраняем сообщение пользователя в историю заказа
    await save_user_message_to_history(message, state, "Сообщение при выборе оформления первой и последней страницы: ")
    
    # Проверяем текущее состояние FSM - если пользователь уже перешел к следующему этапу
    current_state = await state.get_state()
    
    if current_state and current_state != "BookFinalStates:choosing_first_last_design":
        await message.answer("❌ Выбор оформления уже завершен! Вы перешли к следующему этапу.")
        return
    
    # Пользователь отвечает администратору - сообщение уже сохранено в историю заказа
    # Не отправляем подтверждение пользователю
    
    await log_state(message, state)


# Обработчики для выбора оформления первой и последней страницы

@dp.callback_query(F.data.in_(["first_last_text_only", "first_last_text_photo"]))

async def handle_first_last_page_choice(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    if callback.data == "first_last_text_only":

        # Пользователь выбрал только текст для первой и последней страницы

        await state.update_data(first_last_design="text_only")

        

        # Сохраняем выбор в базу данных

        data = await state.get_data()

        order_id = data.get('order_id')

        await update_order_field(order_id, 'first_last_design', 'text_only')

        await callback.message.edit_text(

            "📝 <b>Отлично!</b> Первая и последняя страницы книги будут оформлены только текстом.\n\n"

            "Теперь напишите <b>текст для первой страницы книги</b>.\n"

            "Это может быть трогательное посвящение, начало вашей истории или просто теплые слова от сердца 💕",

            parse_mode="HTML"

        )

        # Переходим к вводу текста для первой страницы

        await state.set_state(BookFinalStates.entering_first_page_text)

        

    elif callback.data == "first_last_text_photo":

        # Пользователь выбрал текст + фото для первой и последней страницы

        await state.update_data(first_last_design="text_photo")

        

        # Сохраняем выбор в базу данных

        data = await state.get_data()

        order_id = data.get('order_id')

        await update_order_field(order_id, 'first_last_design', 'text_photo')

        

        # Переходим к пошаговой загрузке - сначала фото для первой страницы

        await state.set_state(BookFinalStates.uploading_first_page_photo)

        await callback.message.edit_text(

            "📸 <b>Отлично!</b> Теперь мы будем создавать первую и последнюю страницы пошагово.\n\n"

            "📷 <b>Шаг 1:</b> Отправьте фотографию для <b>первой страницы</b> книги:",

            parse_mode="HTML"

        )

    

    await log_state(callback.message, state)



# === НОВЫЕ ОБРАБОТЧИКИ ДЛЯ ПОШАГОВОЙ ЗАГРУЗКИ ===



# Обработчик для загрузки фото первой страницы

@dp.message(StateFilter(BookFinalStates.uploading_first_page_photo), F.photo)

async def handle_first_page_photo_upload(message: types.Message, state: FSMContext):

    """Обрабатывает загрузку фотографии для первой страницы книги"""

    print(f"🔍 ОТЛАДКА: Получена фотография для первой страницы от пользователя {message.from_user.id}")

    

    data = await state.get_data()

    order_id = data.get('order_id')

    

    # Сохраняем фотографию

    file_id = message.photo[-1].file_id

    filename = f"first_page_photo_{order_id}.jpg"

    

    print(f"🔍 ОТЛАДКА: Сохраняем фото первой страницы как {filename}")

    

    await download_and_save_photo(message.bot, file_id, "uploads", filename)

    

    # Сохраняем информацию о файле в базу данных

    await add_upload(order_id, filename, "first_page_photo")

    

    # Сохраняем в state

    await state.update_data(first_page_photo=filename)

    

    # Переходим к вводу текста для первой страницы

    await state.set_state(BookFinalStates.entering_first_page_text_after_photo)

    await message.answer(

        "✅ <b>Фотография для первой страницы сохранена!</b>\n\n"

        "📝 <b>Шаг 2:</b> Теперь напиши текст для <b>первой страницы</b> книги. "

        "Это может быть трогательное посвящение, начало вашей истории или просто теплые слова от сердца 💕",

        parse_mode="HTML"

    )

    

    await log_state(message, state)



# Обработчик для текста в состоянии загрузки фото первой страницы

@dp.message(StateFilter(BookFinalStates.uploading_first_page_photo), F.text)

async def handle_first_page_photo_text(message: types.Message, state: FSMContext):

    """Обрабатывает текстовые сообщения в состоянии загрузки фото первой страницы"""

    # Сохраняем сообщение в историю заказа
    await save_user_message_to_history(message, state, "Текст вместо фото первой страницы: ")

    await message.answer(

        "⚠️ <b>Ожидается фотография!</b>\n\n"

        "Пожалуйста, отправьте фотографию для первой страницы книги.",

        parse_mode="HTML"

    )



# Обработчик для ввода текста первой страницы после фото

@dp.message(StateFilter(BookFinalStates.entering_first_page_text_after_photo), F.text)

async def handle_first_page_text_after_photo(message: types.Message, state: FSMContext):

    """Обрабатывает ввод текста для первой страницы после загрузки фото"""

    print(f"🔍 ОТЛАДКА: Получен текст для первой страницы: '{message.text}'")

    

    # Сохраняем сообщение пользователя в историю заказа

    await save_user_message_to_history(message, state, "Текст первой страницы: ")

    

    data = await state.get_data()

    order_id = data.get('order_id')

    

    # Сохраняем текст первой страницы

    await state.update_data(first_page_text=message.text)

    await update_order_field(order_id, 'first_page_text', message.text)

    

    # Переходим к загрузке фото для последней страницы

    await state.set_state(BookFinalStates.uploading_last_page_photo)

    await message.answer(

        "✅ <b>Текст для первой страницы сохранен!</b>\n\n"

        "📷 <b>Шаг 3:</b> Теперь отправьте фотографию для <b>последней страницы</b> книги:",

        parse_mode="HTML"

    )

    

    await log_state(message, state)



# Обработчик для фото в состоянии ввода текста первой страницы

@dp.message(StateFilter(BookFinalStates.entering_first_page_text_after_photo), F.photo)

async def handle_first_page_text_photo(message: types.Message, state: FSMContext):

    """Обрабатывает фото в состоянии ввода текста первой страницы"""

    await message.answer(

        "⚠️ <b>Ожидается текст!</b>\n\n"

        "Пожалуйста, напишите текст для первой страницы книги.",

        parse_mode="HTML"

    )



# Обработчик для загрузки фото последней страницы

@dp.message(StateFilter(BookFinalStates.uploading_last_page_photo), F.photo)

async def handle_last_page_photo_upload(message: types.Message, state: FSMContext):

    """Обрабатывает загрузку фотографии для последней страницы книги"""

    print(f"🔍 ОТЛАДКА: Получена фотография для последней страницы от пользователя {message.from_user.id}")

    

    data = await state.get_data()

    order_id = data.get('order_id')

    

    # Сохраняем фотографию

    file_id = message.photo[-1].file_id

    filename = f"last_page_photo_{order_id}.jpg"

    

    print(f"🔍 ОТЛАДКА: Сохраняем фото последней страницы как {filename}")

    

    await download_and_save_photo(message.bot, file_id, "uploads", filename)

    

    # Сохраняем информацию о файле в базу данных

    await add_upload(order_id, filename, "last_page_photo")

    

    # Сохраняем в state

    await state.update_data(last_page_photo=filename)

    

    # Переходим к вводу текста для последней страницы

    await state.set_state(BookFinalStates.entering_last_page_text_after_photo)

    await message.answer(

        "✅ <b>Фотография для последней страницы сохранена!</b>\n\n"

        "📝 <b>Шаг 4:</b> Теперь напиши текст для <b>последней страницы</b> книги. "

        "Это могут быть пожелания на будущее, благодарность или просто слова, которые останутся в сердце навсегда 💕",

        parse_mode="HTML"

    )

    

    await log_state(message, state)



# Обработчик для текста в состоянии загрузки фото последней страницы

@dp.message(StateFilter(BookFinalStates.uploading_last_page_photo), F.text)

async def handle_last_page_photo_text(message: types.Message, state: FSMContext):

    """Обрабатывает текстовые сообщения в состоянии загрузки фото последней страницы"""

    # Сохраняем сообщение в историю заказа
    await save_user_message_to_history(message, state, "Текст вместо фото последней страницы: ")

    await message.answer(

        "⚠️ <b>Ожидается фотография!</b>\n\n"

        "Пожалуйста, отправьте фотографию для последней страницы книги.",

        parse_mode="HTML"

    )



# Обработчик для ввода текста последней страницы после фото

@dp.message(StateFilter(BookFinalStates.entering_last_page_text_after_photo), F.text)

async def handle_last_page_text_after_photo(message: types.Message, state: FSMContext):

    """Обрабатывает ввод текста для последней страницы после загрузки фото"""

    print(f"🔍 ОТЛАДКА: Получен текст для последней страницы: '{message.text}'")

    

    # Сохраняем сообщение пользователя в историю заказа

    await save_user_message_to_history(message, state, "Текст последней страницы: ")

    

    data = await state.get_data()

    order_id = data.get('order_id')

    

    # Сохраняем текст последней страницы

    await state.update_data(last_page_text=message.text)

    await update_order_field(order_id, 'last_page_text', message.text)

    

    # Завершаем процесс и переходим к выбору обложек

    await message.answer(

        "✅ <b>Текст для последней страницы сохранен!</b>\n\n"

        "🎉 <b>Отлично!</b> Первая и последняя страницы готовы! Теперь переходим к выбору обложки.",

        parse_mode="HTML"

    )

    # Переходим к выбору обложек

    await show_cover_library(message, state)

    

    await log_state(message, state)



# Обработчик для фото в состоянии ввода текста последней страницы

@dp.message(StateFilter(BookFinalStates.entering_last_page_text_after_photo), F.photo)

async def handle_last_page_text_photo(message: types.Message, state: FSMContext):

    """Обрабатывает фото в состоянии ввода текста последней страницы"""

    await message.answer(

        "⚠️ <b>Ожидается текст!</b>\n\n"

        "Пожалуйста, напишите текст для последней страницы книги.",

        parse_mode="HTML"

    )



# === СТАРЫЕ ОБРАБОТЧИКИ (для совместимости) ===



# Обработчик для загрузки фотографий первой и последней страницы

@dp.message(StateFilter(BookFinalStates.uploading_first_last_photos), F.photo)

async def handle_first_last_photo_upload(message: types.Message, state: FSMContext):

    """Обрабатывает загрузку фотографий для первой и последней страницы книги"""

    print(f"🔍 ОТЛАДКА: Получена фотография для первой/последней страницы от пользователя {message.from_user.id}")

    

    data = await state.get_data()

    order_id = data.get('order_id')

    first_last_photos = data.get('first_last_photos', [])

    

    print(f"🔍 ОТЛАДКА: order_id={order_id}, текущих фото={len(first_last_photos)}")

    

    # Сохраняем фотографию

    file_id = message.photo[-1].file_id

    filename = f"first_last_photo_{len(first_last_photos) + 1}_{order_id}.jpg"

    

    print(f"🔍 ОТЛАДКА: Сохраняем фото как {filename}")

    

    await download_and_save_photo(message.bot, file_id, "uploads", filename)

    

    # Сохраняем информацию о файле в базу данных

    photo_type = "first_page_photo" if len(first_last_photos) == 0 else "last_page_photo"

    await add_upload(order_id, filename, photo_type)

    

    # Добавляем в список

    first_last_photos.append(filename)

    await state.update_data(first_last_photos=first_last_photos)

    

    print(f"🔍 ОТЛАДКА: Фото добавлено, всего фото={len(first_last_photos)}")

    

    if len(first_last_photos) == 1:

        await message.answer("✅ <b>Фотография для первой страницы книги</b> сохранена!\n\nТеперь отправьте <b>вторую фотографию для последней страницы книги</b>.", parse_mode="HTML")

    elif len(first_last_photos) == 2:

        # Автоматически переходим к следующему шагу

        await finish_page_selection(message, state)

    

    await log_state(message, state)



@dp.message(StateFilter(BookFinalStates.uploading_first_last_photos), F.text)

async def handle_first_last_photos_text(message: types.Message, state: FSMContext):

    """Обрабатывает текстовые сообщения при загрузке фотографий для первой и последней страницы"""

    print(f"🔍 ОТЛАДКА: Получено текстовое сообщение в состоянии uploading_first_last_photos: '{message.text}'")

    

    # Сохраняем сообщение пользователя в историю заказа

    await save_user_message_to_history(message, state, "Сообщение при загрузке фото: ")

    

    # Игнорируем текстовые сообщения, так как автоматически переходим после получения фото

    await message.answer("ℹ️ Отправьте фотографии для первой и последней страницы книги.")

    

    await log_state(message, state)



# Обработчик для ввода текста первой страницы

@dp.message(StateFilter(BookFinalStates.entering_first_page_text))

async def handle_first_page_text(message: types.Message, state: FSMContext):

    """Обрабатывает ввод текста для первой страницы книги"""

    print(f"🔍 ОТЛАДКА: Получен текст для первой страницы: '{message.text}'")

    

    # Сохраняем сообщение пользователя в историю заказа

    await save_user_message_to_history(message, state, "Текст первой страницы: ")

    

    data = await state.get_data()

    order_id = data.get('order_id')

    

    # Сохраняем текст первой страницы

    await state.update_data(first_page_text=message.text)

    await update_order_field(order_id, 'first_page_text', message.text)

    

    await message.answer(

        "✅ <b>Текст для первой страницы сохранен!</b>\n\n"

        "Теперь напишите <b>текст для последней страницы книги</b> (например, заключение, пожелание или эпилог):",

        parse_mode="HTML"

    )

    

    # Переходим к вводу текста для последней страницы

    await state.set_state(BookFinalStates.entering_last_page_text)

    

    await log_state(message, state)



# Обработчик для ввода текста последней страницы

@dp.message(StateFilter(BookFinalStates.entering_last_page_text))

async def handle_last_page_text(message: types.Message, state: FSMContext):

    """Обрабатывает ввод текста для последней страницы книги"""

    print(f"🔍 ОТЛАДКА: Получен текст для последней страницы: '{message.text}'")

    

    # Сохраняем сообщение пользователя в историю заказа

    await save_user_message_to_history(message, state, "Текст последней страницы: ")

    

    data = await state.get_data()

    order_id = data.get('order_id')

    

    # Сохраняем текст последней страницы

    await state.update_data(last_page_text=message.text)

    await update_order_field(order_id, 'last_page_text', message.text)

    

    # Переходим к завершению выбора страниц (без отправки дополнительного сообщения)

    await finish_page_selection(message, state)

    

    await log_state(message, state)



# Функция завершения выбора страниц

async def finish_page_selection(message, state):

    """Завершает процесс выбора страниц и переходит к следующему этапу"""

    data = await state.get_data()

    order_id = data.get('order_id')

    

    # Отмечаем, что выбор страниц завершен для этого заказа

    await state.update_data({f"page_selection_finished_{order_id}": True})

    

    await message.answer(

        "🎉 <b>Отлично! Выбор страниц завершен!</b>\n\n"

        "✅ Основные страницы: выбраны\n"

        "✅ Первая и последняя страница: оформлены\n\n"

        "🎨 <b>Теперь перейдем к выбору обложки для вашей книги!</b>",

        parse_mode="HTML"

    )

    

    # Обновляем статус заказа

    await update_order_status(order_id, "pages_selected")
    
    # Создаем таймер для этапа "pages_selected"
    from db import create_or_update_user_timer
    user_id = message.from_user.id
    await create_or_update_user_timer(user_id, order_id, "pages_selected", "Книга")
    logging.info(f"✅ Создан таймер для этапа pages_selected, пользователь {user_id}, заказ {order_id}")

    

    # Переходим к выбору обложки

    await show_cover_library(message, state)

    

    await log_state(message, state)



# Обработчик для любых сообщений в состоянии загрузки фотографий первой и последней страницы

@dp.message(StateFilter(BookFinalStates.uploading_first_last_photos))

async def handle_any_message_in_first_last_photos(message: types.Message, state: FSMContext):

    """Обрабатывает любые сообщения при загрузке фотографий первой и последней страницы"""

    print(f"🔍 ОТЛАДКА: Получено сообщение в состоянии uploading_first_last_photos: тип={message.content_type}, текст='{message.text if message.text else 'НЕТ ТЕКСТА'}'")

    

    if message.content_type == "photo":

        print(f"🔍 ОТЛАДКА: Это фото, обрабатываем...")

        # Фото будет обработано основным обработчиком

    elif message.content_type == "text":

        print(f"🔍 ОТЛАДКА: Это текст, обрабатываем...")

        # Текст будет обработан основным обработчиком

    else:

        await message.answer("ℹ️ Пожалуйста, отправьте фотографии или напишите 'Готово' для завершения.")

    

    await log_state(message, state)



# Обработчик для любых сообщений в состоянии выбора страниц

@dp.message(StateFilter(BookFinalStates.choosing_pages))

async def handle_any_message_in_story_options(message: types.Message, state: FSMContext):

    """Обрабатывает любые сообщения при выборе страниц"""

    print(f"🔍 ОТЛАДКА: Получено сообщение в состоянии choosing_pages: тип={message.content_type}, текст='{message.text}' от пользователя {message.from_user.id}")

    

    # Проверяем текущее состояние FSM - если пользователь уже перешел к следующему этапу

    current_state = await state.get_state()

    if current_state and current_state != "BookFinalStates:choosing_pages":

        await message.answer("❌ Выбор страниц уже завершен! Вы перешли к следующему этапу.")

        return

    

    if not message.text:

        # Если это не текстовое сообщение (фото, документ и т.д.), сохраняем в историю заказа

        data = await state.get_data()

        order_id = data.get('order_id')

        

        if order_id:

            # Сохраняем информацию о не текстовом сообщении в историю заказа

            from db import add_message_history

            content_type = message.content_type or "unknown"

            await add_message_history(order_id, "user", f"[{content_type.upper()}] Сообщение от пользователя")

            

            # Создаем или обновляем уведомление для менеджера

            from db import create_or_update_order_notification

            await create_or_update_order_notification(order_id)

            print(f"🔍 ОТЛАДКА: Сохранено не текстовое сообщение пользователя в историю заказа {order_id}: {content_type}")

            print(f"🔔 ОТЛАДКА: Создано уведомление для заказа {order_id}")

            

            # Не отвечаем пользователю - это диалог с администратором

        else:

            # Если нет order_id, показываем подсказку

            await message.answer("ℹ️ Пожалуйста, напишите 'Далее' когда выберете ровно 24 страницы и будете готовы продолжить.")

    await log_state(message, state)



# Обработчики для получения контента от менеджера

@dp.message(StateFilter(ManagerContentStates.waiting_demo_content))

async def receive_demo_content(message: types.Message, state: FSMContext):

    # Менеджер отправляет демо-контент (ручная отправка)

    data = await state.get_data()

    order_id = data.get('order_id')

    

    # Сохраняем демо-контент

    await state.update_data(demo_content=message.text)

    await update_order_status(order_id, "demo_sent")
    
    # Получаем тип продукта из заказа
    from db import get_order
    order = await get_order(order_id)
    if not order:
        logging.error(f"❌ Заказ {order_id} не найден")
        return
    
    user_id = order.get('user_id')
    if not user_id:
        logging.error(f"❌ user_id не найден в заказе {order_id}")
        return
    
    # Определяем тип продукта
    order_data = order.get('order_data')
    if isinstance(order_data, str):
        import json
        order_data = json.loads(order_data)
    product_type = order_data.get('product', 'Книга')
    
    # Таймер создается автоматически в update_order_status при изменении статуса на demo_sent

    

    # Показываем демо-контент пользователю с кнопкой

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="Узнать цену", callback_data="continue_after_demo")]

    ])

    

    await message.answer("Пробные страницы вашей книги готовы ☑️\n"

                        "Мы старались, чтобы они были тёплыми и живыми.\n\n"

                        "Но впереди ещё больше — иллюстратор вдохновился вашей историей и собрал десятки сюжетов для полной версии книги.")

    await message.answer(message.text)

    await message.answer("Как вам такие варианты? Готовы продолжить?", reply_markup=keyboard)

    

    # Трекинг: демо книги отправлено пользователю
    await track_event(
        user_id=user_id,
        event_type='demo_abandoned_book',
        event_data={
            'order_id': order_id,
            'product': product_type,
            'demo_sent_at': datetime.now().isoformat()
        },
        step_name='demo_sent_book',
        product_type=product_type,
        order_id=order_id
    )

    # Переходим к ожиданию вариантов сюжетов

    await state.set_state(ManagerContentStates.waiting_story_options)

    await log_state(message, state)



# Глава 11. Обработчики для получения сюжетов от менеджера - УДАЛЕНЫ (оставлена только фото-реализация)



# Вспомогательные функции для работы с фото-страницами (оставлены только нужные)



# Обработчик для получения сюжетов от менеджера - УДАЛЕН (оставлена только фото-реализация)



@dp.message(StateFilter(ManagerContentStates.waiting_draft))

async def receive_book_draft(message: types.Message, state: FSMContext):

    # Проверяем, что это сообщение от менеджера, а не от пользователя

    # Если это сообщение от пользователя, игнорируем его

    data = await state.get_data()

    order_id = data.get('order_id')

    

    if order_id:

        order = await get_order(order_id)

        if order and order.get('user_id') == message.from_user.id:

            # Это сообщение от пользователя, а не от менеджера

            # Сохраняем сообщение в историю заказа, но не перекидываем пользователя

            try:

                from db import add_message_history

                await add_message_history(order_id, "user", message.text)

                logging.info(f"💬 Сообщение пользователя {message.from_user.id} сохранено в историю заказа {order_id}: {message.text[:50]}...")

            except Exception as e:

                logging.error(f"❌ Ошибка сохранения сообщения в историю: {e}")

            

            logging.info(f"📖 Игнорируем сообщение от пользователя {message.from_user.id} в состоянии ManagerContentStates.waiting_draft")

            return

    

    # Менеджер отправляет черновик книги

    await state.update_data(book_draft=message.text)

    await update_order_status((await state.get_data()).get('order_id'), "draft_sent")

    

    # Показываем черновик пользователю и предлагаем кнопки редактирования

    await message.answer("Вот они — страницы твоей книги 📖\n"

                        "Мы вложили в них много тепла и переживаем не меньше тебя. Надеемся, они тронут твоё сердце 💕\n\n"

                        "Если тебе всё нравится — жми \"Всё супер\".\n"

                        "Если хочешь внести правки — нажми \"Внести правки\".")

    await message.answer(message.text)  # Показываем черновик

    

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="Всё супер", callback_data="edit_done")],

        [InlineKeyboardButton(text="Внести правки", callback_data="edit_change")]

    ])

    await message.answer(

        "Если вас все устраивает, нажмите 'Готово'. "

        "Если хотите что-то изменить, нажмите 'Изменить' и напишите ваши комментарии.",

        reply_markup=keyboard

    )

    await state.set_state(EditBookStates.reviewing_draft)

    await log_state(message, state)



# Глава 15. Передача книги - улучшенная версия

@dp.message(StateFilter(ManagerContentStates.waiting_final))

async def receive_final_book(message: types.Message, state: FSMContext):

    # Менеджер отправляет финальную версию книги

    data = await state.get_data()

    order_id = data.get('order_id')

    format_name = data.get('format', 'Книга')

    

    logging.info(f"📚 Менеджер отправляет финальную версию книги для заказа {order_id}")

    await update_order_status(order_id, "ready")

    logging.info(f"📚 Статус заказа {order_id} изменен на 'ready'")

    

    # Отправляем файлы книги (PDF, фото или видео)

    if message.document:

        # Если это PDF файл

        await message.answer_document(

            message.document.file_id, 

            caption="📄 Электронная версия книги (PDF)"

        )

    elif message.photo:

        # Если это галерея изображений

        await message.answer_photo(

            message.photo[-1].file_id, 

            caption="📖 Финальная версия книги"

        )

    elif message.video:

        # Если это видео

        logging.info(f"🎬 Отправляем видео финальной версии книги для заказа {order_id}")

        await message.answer_video(

            message.video.file_id, 

            caption="🎬 Финальная версия книги"

        )

        logging.info(f"✅ Видео отправлено, продолжаем выполнение функции")

    else:

        # Если это текст с описанием

        await message.answer(message.text)

    

    # Отправляем текст и кнопки после медиа

    await message.answer(

        "Вот они — страницы твоей книги 📖\n"

        "Мы вложили в них много тепла и переживаем не меньше тебя. Надеемся, они тронут твоё сердце 💕\n\n"

        "Если тебе всё нравится — жми \"Всё супер\".\n"

        "Если хочешь внести правки — нажми \"Внести правки\"."

    )

    

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="Всё супер", callback_data="edit_done")],

        [InlineKeyboardButton(text="Внести правки", callback_data="edit_change")]

    ])

    

    await message.answer(

        "Если вас все устраивает, нажмите 'Готово'. "

        "Если хотите что-то изменить, нажмите 'Изменить' и напишите ваши комментарии.",

        reply_markup=keyboard

    )

    

    # Переходим в состояние ожидания ответа пользователя

    await state.set_state(EditBookStates.reviewing_draft)

    

    logging.info(f"📚 Функция receive_final_book завершена для заказа {order_id}")

    await log_state(message, state)



# Глава 13. Выбор обложки - улучшенная версия

@dp.callback_query(F.data == "additions_next")

async def additions_next_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    data = await state.get_data()

    inserts = data.get("inserts", [])

    custom_photos = data.get("custom_photos", [])

    insert_texts = data.get("insert_texts", {})

    

    # Сохраняем данные в базу данных

    order_id = data.get('order_id')

    if order_id:

        order_data = {

            "inserts": inserts,

            "insert_texts": insert_texts,

            "custom_photos": custom_photos,

            "additions_completed": True,

            "additions_completed_date": datetime.now().isoformat()

        }

        await update_order_data(order_id, order_data)

    

    additions_text = []

    if inserts:

        additions_text.append(f"Вкладыши: {', '.join(inserts)}")

    if custom_photos:

        additions_text.append(f"Свои фотографии: {len(custom_photos)} шт.")

    

    additions_summary = '; '.join(additions_text) if additions_text else 'Без дополнений'

    

    await callback.message.edit_text(

        f"✅ Отлично! {additions_summary}\n\n"

        f"🎨 <b>Теперь выберите обложку для вашей книги</b>\n\n"

        f"Мы подготовили несколько вариантов обложек в разных стилях. "

        f"Выберите ту, которая больше всего подходит к вашему подарку.",

        parse_mode="HTML"

    )

    

    # Отправляем уведомление менеджеру о готовности к выбору обложки

    order_id = data.get('order_id')

    await add_outbox_task(

        order_id=order_id,

        user_id=callback.from_user.id,

        type_="manager_notification",

        content=f"Заказ #{order_id}: Пользователь готов к выбору обложки. Дополнения: {additions_summary}"

    )

    

    # Переходим в состояние ожидания обложек от менеджера

    await state.set_state(BookFinalStates.waiting_for_cover_options)

    await log_state(callback.message, state)



# Функция для показа библиотеки обложек

async def show_cover_library(message, state):

    """Показывает библиотеку обложек пользователю"""

    try:

        # Получаем обложки из базы данных

        from db import get_cover_templates

        cover_templates = await get_cover_templates()

        

        if not cover_templates:

            # Если нет обложек в библиотеке, показываем сообщение

            await message.answer(

                "🎨 <b>Библиотека обложек</b>\n\n"

                "К сожалению, в данный момент библиотека обложек пуста. "

                "Менеджер скоро добавит варианты обложек для вас.",

                parse_mode="HTML"

            )

            # Переходим в состояние ожидания обложек от менеджера

            await state.set_state(BookFinalStates.waiting_for_cover_options)

            return

        

        # Показываем обложки пользователю

        await message.answer(

            "📚 Теперь выбери обложку для своей книги.\n"
            "Мы создали несколько вариантов в разных цветах, чтобы обложка гармонично дополнила твой подарок 😍",

            parse_mode="HTML"

        )

        

        # Отправляем каждую обложку с кнопкой выбора

        cover_message_ids = []

        for i, template in enumerate(cover_templates, 1):

            # Создаем кнопку для выбора обложки

            keyboard = InlineKeyboardMarkup(inline_keyboard=[

                [InlineKeyboardButton(text="Выбрать эту обложку", callback_data=f"choose_cover_template_{template['id']}")]

            ])

            

            # Отправляем обложку с описанием и кнопкой

            caption = f"📖 <b>{template['name']}</b>\n\n"

            if template.get('category'):

                caption += f"Категория: {template['category']}\n"

            caption += f"Обложка #{i} из {len(cover_templates)}"

            

            # Отправляем фото обложки

            photo_path = f"covers/{template['filename']}"

            try:

                sent_message = await message.answer_photo(

                    photo=types.FSInputFile(photo_path),

                    caption=caption,

                    reply_markup=keyboard,

                    parse_mode="HTML"

                )

                # Сохраняем message_id обложки

                cover_message_ids.append(sent_message.message_id)

            except Exception as e:

                print(f"❌ Ошибка отправки обложки {template['filename']}: {e}")

                # Если не удалось отправить фото, отправляем текстовое описание

                sent_message = await message.answer(

                    f"📖 <b>{template['name']}</b>\n"

                    f"Категория: {template.get('category', 'Не указана')}\n"

                    f"Обложка #{i} из {len(cover_templates)}",

                    reply_markup=keyboard,

                    parse_mode="HTML"

                )

                # Сохраняем message_id обложки

                cover_message_ids.append(sent_message.message_id)

        

        # Сохраняем message_id обложек в state

        await state.update_data(cover_message_ids=cover_message_ids)

        

        # Переходим в состояние выбора обложки

        await state.set_state(CoverStates.choosing_cover)

        

    except Exception as e:

        print(f"❌ Ошибка показа библиотеки обложек: {e}")

        await message.answer("Произошла ошибка при загрузке библиотеки обложек. Попробуйте позже.")

        # Переходим в состояние ожидания обложек от менеджера

        await state.set_state(BookFinalStates.waiting_for_cover_options)



# Обработчик для получения обложек от менеджера

@dp.message(StateFilter(BookFinalStates.waiting_for_cover_options))

async def receive_covers_from_manager(message: types.Message, state: FSMContext):

    data = await state.get_data()

    order_id = data.get('order_id')

    

    # Обрабатываем галерею изображений с обложками

    if message.media_group_id:

        # Если это часть медиа-группы, сохраняем информацию

        media_group = data.get('cover_media_group', {})

        media_group[message.media_group_id] = media_group.get(message.media_group_id, [])

        

        if message.photo:

            media_group[message.media_group_id].append({

                'type': 'photo',

                'file_id': message.photo[-1].file_id,

                'caption': message.caption or f"Обложка {len(media_group[message.media_group_id]) + 1}"

            })

        elif message.document:

            media_group[message.media_group_id].append({

                'type': 'document',

                'file_id': message.document.file_id,

                'caption': message.caption or f"Обложка {len(media_group[message.media_group_id]) + 1}"

            })

        

        await state.update_data(cover_media_group=media_group)

        

        # Если это первое изображение в группе, отправляем сообщение пользователю

        if len(media_group[message.media_group_id]) == 1:

            await message.answer("🎨 <b>Варианты обложек для вашей книги:</b>", parse_mode="HTML")

    

    elif message.photo or message.document:

        # Одиночное изображение

        if message.photo:

            file_id = message.photo[-1].file_id

            caption = message.caption or "Вариант обложки"

        else:

            file_id = message.document.file_id

            caption = message.caption or "Вариант обложки"

        

        # Сохраняем информацию об обложке

        covers = data.get('cover_options', [])

        covers.append({

            'file_id': file_id,

            'caption': caption,

            'type': 'photo' if message.photo else 'document'

        })

        await state.update_data(cover_options=covers)

        

        # Отправляем пользователю с кнопкой выбора

        if len(covers) == 1:

            await message.answer("🎨 <b>Варианты обложек для вашей книги:</b>", parse_mode="HTML")

        

        # Создаем кнопку для выбора этой обложки

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="Выбрать эту обложку", callback_data=f"choose_cover_{len(covers)}")]

        ])

        

        if message.photo:

            sent_message = await message.answer_photo(file_id, caption=caption, reply_markup=keyboard)

        else:

            sent_message = await message.answer_document(file_id, caption=caption, reply_markup=keyboard)

        

        # Сохраняем message_id обложки в state

        data = await state.get_data()

        cover_message_ids = data.get('cover_message_ids', [])

        cover_message_ids.append(sent_message.message_id)

        await state.update_data(cover_message_ids=cover_message_ids)

    

    elif message.text:

        # Текстовое описание обложек (для совместимости)

        await state.update_data(cover_options_text=message.text)

        await update_order_status(order_id, "covers_sent")

        

        await message.answer("🎨 <b>Варианты обложек для вашей книги:</b>", parse_mode="HTML")

        await message.answer(message.text)

    

    # Если это последняя обложка, переходим к выбору

    covers = data.get('cover_options', [])

    if len(covers) >= 1:

        await state.set_state(CoverStates.choosing_cover)

    

    await log_state(message, state)


# Обработчик текстовых сообщений в состоянии ожидания вариантов обложек
@dp.message(StateFilter(BookFinalStates.waiting_for_cover_options), F.text)
async def handle_text_while_waiting_covers(message: types.Message, state: FSMContext):
    """Обрабатывает текстовые сообщения в состоянии ожидания вариантов обложек"""
    
    print(f"🔍 ОТЛАДКА: Получено текстовое сообщение в состоянии BookFinalStates.waiting_for_cover_options: '{message.text}' от пользователя {message.from_user.id}")
    
    # Сохраняем сообщение пользователя в историю заказа
    await save_user_message_to_history(message, state, "Сообщение в ожидании обложек: ")
    
    # Проверяем текущее состояние FSM - если пользователь уже перешел к следующему этапу
    current_state = await state.get_state()
    
    if current_state and current_state != "BookFinalStates:waiting_for_cover_options":
        await message.answer("❌ Ожидание обложек завершено! Вы перешли к следующему этапу.")
        return
    
    # Пользователь отвечает администратору - сообщение уже сохранено в историю заказа
    # Не отправляем подтверждение пользователю
    
    await log_state(message, state)


@dp.callback_query(F.data.startswith("choose_cover_"))

async def choose_cover_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    # Проверяем, не выбрана ли уже обложка

    data = await state.get_data()

    if data.get('selected_cover'):

        await callback.answer("❌ Обложка уже выбрана! Вы не можете выбрать другую.", show_alert=True)

        return

    

    if callback.data.startswith("choose_cover_template_"):

        # Выбор обложки из библиотеки

        template_id = int(callback.data.replace("choose_cover_template_", ""))

        

        # Получаем информацию об обложке из базы данных

        from db import get_cover_template_by_id

        template = await get_cover_template_by_id(template_id)

        

        if template:

            selected_cover = {

                'template_id': template_id,

                'name': template['name'],

                'category': template.get('category', ''),

                'filename': template['filename'],

                'type': 'template'

            }

            

            await state.update_data(selected_cover=selected_cover)

            

            # Сохраняем в базу данных

            data = await state.get_data()

            order_id = data.get('order_id')

            if order_id:

                from db import update_order_data

                await update_order_data(order_id, {'selected_cover': selected_cover})

                

                # Обновляем статус заказа

                await update_order_status(order_id, "cover_selected")
                
                # Сразу переходим к ожиданию черновика
                await update_order_status(order_id, "waiting_draft")

            

            # Убираем кнопки после выбора обложки

            await callback.message.edit_caption(

                caption=f"✅ <b>Обложка выбрана!</b>\n\n"

                       f"📖 <b>{template['name']}</b>\n"

                       f"Категория: {template.get('category', 'Не указана')}",

                parse_mode="HTML",

                reply_markup=None  # Убираем кнопки

            )

            

            # Убираем кнопки с других обложек вместо показа предупреждения

            await remove_cover_buttons_for_user(callback.from_user.id, selected_template_id=template_id)

            

            # Переходим к этапу редактирования книги

            await callback.message.answer(

                "Вся информация собрана, и наша команда уже творит волшебство, бережно воплощая вашу историю в жизнь ✨\n"

                "Скоро вернемся с результатом и очень ждем вашей реакции — надеемся, что книга тронет тебя до мурашек! 💎💕"

            )

            # Создаем таймер для этапа waiting_main_book (Глава 6: Ожидание основной книги)
            from db import create_or_update_user_timer
            await create_or_update_user_timer(callback.from_user.id, order_id, "waiting_main_book", "Книга")
            logging.info(f"✅ Создан таймер для этапа waiting_main_book (Глава 6), пользователь {callback.from_user.id}, заказ {order_id}")

            

            # Отправляем уведомление менеджеру

            await add_outbox_task(

                order_id=order_id,

                user_id=callback.from_user.id,

                type_="manager_notification",

                content=f"Заказ #{order_id}: Пользователь выбрал обложку '{template['name']}' из библиотеки. Готов к созданию черновика."

            )

            

            await state.set_state(EditBookStates.waiting_for_draft)

        else:

            await callback.answer("❌ Обложка не найдена. Попробуйте выбрать другую.")

    



    

    else:

        # Старый формат для совместимости

        cover_id = callback.data.replace("choose_cover_", "")

        data = await state.get_data()

        covers = data.get('cover_options', [])

        

        # Сохраняем выбранную обложку в профиль

        selected_cover = None

        cover_num = int(cover_id)

        

        # Проверяем, что выбран корректный номер обложки (1-5)

        if 1 <= cover_num <= 5:

            # Если есть загруженные обложки и номер не превышает их количество

            if covers and cover_num <= len(covers):

                selected_cover = covers[cover_num - 1]

            else:

                # Если конкретной обложки нет, сохраняем информацию о выбранном номере

                selected_cover = {

                    'cover_number': cover_num,

                    'type': 'selected_number',

                    'caption': f'Обложка {cover_num}'

                }

            

            await state.update_data(selected_cover=selected_cover)

            

            # Сохраняем в базу данных

            order_id = data.get('order_id')

            if order_id:

                from db import update_order_data

                await update_order_data(order_id, {'selected_cover': selected_cover})

        

        # Убираем кнопки после выбора обложки

        await callback.message.edit_text(

            f"✅ Обложка выбрана: {cover_id}",

            reply_markup=None  # Убираем кнопки

        )

        

        # Убираем кнопки с других обложек вместо показа предупреждения

        await remove_cover_buttons_for_user(callback.from_user.id)

        

        # Переходим к этапу редактирования книги

        await callback.message.answer(

            "Вся информация собрана, и наша команда уже творит волшебство, бережно воплощая вашу историю в жизнь ✨\n"

            "Скоро вернемся с результатом и очень ждем вашей реакции — надеемся, что книга тронет тебя до мурашек! 💎💕"

        )

        # Создаем таймер для этапа waiting_main_book (Глава 6: Ожидание основной книги)
        from db import create_or_update_user_timer
        await create_or_update_user_timer(callback.from_user.id, order_id, "waiting_main_book", "Книга")
        logging.info(f"✅ Создан таймер для этапа waiting_main_book (Глава 6), пользователь {callback.from_user.id}, заказ {order_id}")

        

        # Отправляем уведомление менеджеру

        await add_outbox_task(

            order_id=order_id,

            user_id=callback.from_user.id,

            type_="manager_notification",

            content=f"Заказ #{order_id}: Пользователь выбрал обложку {cover_id}. Готов к созданию черновика."

        )

        

        await state.set_state(EditBookStates.waiting_for_draft)

    

    await log_state(callback.message, state)


# Обработчик сообщений в состоянии выбора обложки
@dp.message(StateFilter(CoverStates.choosing_cover), F.text)
async def handle_text_while_choosing_cover(message: types.Message, state: FSMContext):
    """Обрабатывает текстовые сообщения при выборе обложки"""
    
    print(f"🔍 ОТЛАДКА: Получено текстовое сообщение в состоянии CoverStates.choosing_cover: '{message.text}' от пользователя {message.from_user.id}")
    
    # Сохраняем сообщение пользователя в историю заказа
    await save_user_message_to_history(message, state, "Сообщение при выборе обложки: ")
    
    # Проверяем текущее состояние FSM - если пользователь уже перешел к следующему этапу
    current_state = await state.get_state()
    
    if current_state and current_state != "CoverStates:choosing_cover":
        await message.answer("❌ Выбор обложки уже завершен! Вы перешли к следующему этапу.")
        return
    
    # Пользователь отвечает администратору - сообщение уже сохранено в историю заказа
    # Не отправляем подтверждение пользователю
    
    await log_state(message, state)


# Обработчик для выбора обложки из библиотеки

@dp.callback_query(F.data.startswith("select_cover_"))

async def select_cover_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    # Проверяем, не выбрана ли уже обложка

    data = await state.get_data()

    if data.get('selected_cover'):

        await callback.answer("❌ Обложка уже выбрана! Вы не можете выбрать другую.", show_alert=True)

        return

    

    # Извлекаем ID обложки из callback_data

    cover_id = int(callback.data.replace("select_cover_", ""))

    

    # Получаем информацию об обложке из базы данных

    from db import get_cover_template_by_id

    template = await get_cover_template_by_id(cover_id)

    

    if template:

        selected_cover = {

            'template_id': cover_id,

            'name': template['name'],

            'category': template.get('category', ''),

            'filename': template['filename'],

            'type': 'template'

        }

        

        await state.update_data(selected_cover=selected_cover)

        

        # Сохраняем в базу данных

        data = await state.get_data()

        order_id = data.get('order_id')

        if order_id:

            from db import update_order_data

            await update_order_data(order_id, {'selected_cover': selected_cover})

        

        # Обновляем статус заказа

        await update_order_status(order_id, "cover_selected")
        
        # Сразу переходим к ожиданию черновика
        await update_order_status(order_id, "waiting_draft")

        

        # Убираем кнопки после выбора обложки

        await callback.message.edit_text(

            f"✅ <b>Обложка выбрана!</b>\n\n"

            f"📖 <b>{template['name']}</b>\n"

            f"Категория: {template.get('category', 'Не указана')}",

            parse_mode="HTML",

            reply_markup=None  # Убираем кнопки

        )

        

        # Убираем кнопки с других обложек вместо показа предупреждения

        await remove_cover_buttons_for_user(callback.from_user.id, selected_template_id=template_id)

        

        # Переходим к этапу создания черновика

        await callback.message.answer(

            "Вся информация собрана, и наша команда уже творит волшебство, бережно воплощая вашу историю в жизнь ✨\n"

            "Скоро вернемся с результатом и очень ждем вашей реакции — надеемся, что книга тронет тебя до мурашек! 💎💕"

        )

        # Создаем таймер для этапа waiting_main_book (Глава 6: Ожидание основной книги)
        from db import create_or_update_user_timer
        await create_or_update_user_timer(callback.from_user.id, order_id, "waiting_main_book", "Книга")
        logging.info(f"✅ Создан таймер для этапа waiting_main_book (Глава 6), пользователь {callback.from_user.id}, заказ {order_id}")

        

        # Отправляем уведомление менеджеру

        await add_outbox_task(

            order_id=order_id,

            user_id=callback.from_user.id,

            type_="manager_notification",

            content=f"Заказ #{order_id}: Пользователь выбрал обложку '{template['name']}' из библиотеки. Готов к созданию черновика."

        )

        

        await state.set_state(EditBookStates.waiting_for_draft)

        await log_state(callback.message, state)

    else:

        await callback.answer("❌ Обложка не найдена. Попробуйте выбрать другую.")



# Обработчик для кнопки "Выбрать" при просмотре обложек

@dp.callback_query(F.data == "cover_next_step")

async def cover_next_step_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer("Переходим к следующему шагу...")

    

    # Просто переходим к следующему шагу без выбора обложки

    data = await state.get_data()

    order_id = data.get('order_id')

    

    # Переходим к этапу редактирования книги

    await callback.message.answer(

        "Вся информация собрана, и наша команда уже творит волшебство, бережно воплощая вашу историю в жизнь ✨\n"

        "Скоро вернемся с результатом и очень ждем вашей реакции — надеемся, что книга тронет тебя до мурашек! 💎💕"

    )

    # Создаем таймер для этапа waiting_main_book (Глава 6: Ожидание основной книги)
    from db import create_or_update_user_timer
    await create_or_update_user_timer(callback.from_user.id, order_id, "waiting_main_book", "Книга")
    logging.info(f"✅ Создан таймер для этапа waiting_main_book (Глава 6), пользователь {callback.from_user.id}, заказ {order_id}")

    

    # Отправляем уведомление менеджеру

    await add_outbox_task(

        order_id=order_id,

        user_id=callback.from_user.id,

        type_="manager_notification",

        content=f"Заказ #{order_id}: Пользователь просмотрел обложки и перешел к следующему шагу. Готов к созданию черновика."

    )

    

    await state.set_state(EditBookStates.waiting_for_draft)

    await log_state(callback.message, state)



# Обработчики для загрузки своей обложки удалены - обложки отправляются автоматически



# Глава 14. Редактирование книги - улучшенная версия

@dp.callback_query(F.data.in_(["edit_done", "edit_change"]))

async def edit_book_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    if callback.data == "edit_done":

        # Получаем номер заказа

        data = await state.get_data()

        order_id = data.get('order_id')

        order_number = get_order_number(callback.from_user.id)

        

        await callback.message.edit_text(

            f"⏳ <b>Ваш заказ под номером №{order_number} дорабатывается.</b>\n\n"

            "Команда сценаристов вносит последние штрихи, это займет 2-3 дня.\n\n"

            "Мы уведомим вас, когда финальная версия книги будет готова!",

            parse_mode="HTML"

        )

        await state.set_state(EditBookStates.done)

        

        # Отправляем уведомление менеджеру для ручной сборки книги

        await add_outbox_task(

            order_id=order_id,

            user_id=callback.from_user.id,

            type_="manager_notification",

            content=f"Заказ #{order_id}: Пользователь подтвердил черновик книги. Требуется ручная сборка финальной версии."

        )

        

        # Переходим в состояние ожидания финальной версии

        await state.set_state(ManagerContentStates.waiting_final)

        

    elif callback.data == "edit_change":

        await callback.message.edit_text(

            "🔄 <b>Напишите ваши комментарии для внесения изменений:</b>\n\n"

            "Вы можете указать:\n"

            "• <b>По тексту:</b> изменить слова, фразы, добавить или убрать текст\n"

            "• <b>По картинкам:</b> заменить изображения, изменить их расположение\n"

            "• <b>По порядку страниц:</b> поменять местами страницы\n"

            "• <b>Другие пожелания:</b> любые изменения, которые вы хотите внести\n\n"

            "Опишите подробно, что именно нужно изменить:",

            parse_mode="HTML"

        )

        await state.set_state(EditBookStates.adding_comments)

    

    await log_state(callback.message, state)



# Глава 14. Обработка комментариев к редактированию - улучшенная версия

@dp.message(StateFilter(EditBookStates.adding_comments))

async def save_edit_comments(message: types.Message, state: FSMContext):

    # Сохраняем сообщение пользователя в историю заказа

    await save_user_message_to_history(message, state, "Комментарий к черновику книги: ")

    

    # Сохраняем комментарии пользователя

    data = await state.get_data()

    comments = data.get("edit_comments", [])

    comments.append(message.text)

    await state.update_data(edit_comments=comments)

    

    await message.answer(

        "Спасибо за комментарии!🙏🏻\n"

        "Мы учтём все изменения и отправим обновлённую версию книги в ближайшее время.",

        parse_mode="HTML"

    )

    

    # Отправляем комментарии менеджеру

    order_id = data.get('order_id')

    await add_outbox_task(

        order_id=order_id,

        user_id=message.from_user.id,

        type_="manager_notification",

        content=f"Заказ #{order_id}: Комментарии пользователя для редактирования: {message.text}"

    )

    

    # Обновляем статус заказа

    await update_order_status(order_id, "editing")

    

    # Переходим в состояние ожидания обновленного черновика

    await state.set_state(EditBookStates.waiting_for_draft)

    await log_state(message, state)



# Глава 15. Система доставки - улучшенная версия



# Обработчики выбора способа доставки

@dp.callback_query(F.data == "book_delivery_digital")

async def book_delivery_digital_callback(callback: types.CallbackQuery, state: FSMContext):

    data = await state.get_data()

    order_id = data.get('order_id')

    

    # Сохраняем выбор электронной версии

    await state.update_data(book_format="Электронная книга")

    

    await callback.message.edit_text(

        "📄 <b>Электронная версия выбрана!</b>\n\n"

        "Ваша книга будет отправлена в формате PDF. "

        "Вы получите ссылку для скачивания в ближайшее время.",

        parse_mode="HTML"

    )

    

    # Обновляем статус заказа

    await update_order_status(order_id, "delivered")

    

    # Сопроводительное сообщение

    await callback.message.answer(

        "🎉 <b>Ваша книга готова! Спасибо, что выбрали нас ❤️</b>\n\n"

        "Мы подготовили для вас электронную версию (PDF). "

        "Ссылка для скачивания будет отправлена в ближайшее время!",

        parse_mode="HTML"

    )

    

    # Предложение печатной версии

    await callback.message.answer(

        "📦 Теперь мы подготовим печатную книгу для доставки!",

        parse_mode="HTML"

    )

    

    await callback.message.answer(

        "Хотите получить также печатную версию вашей книги?",

        parse_mode="HTML"

    )

    

    # Кнопки для выбора

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="📦 Получить печатную версию", callback_data="upsell_print")],

        [InlineKeyboardButton(text="📄 Продолжить с электронной", callback_data="continue_electronic")]

    ])

    

    await callback.message.answer(

        "Выберите вариант:",

        reply_markup=keyboard

    )

    

    # Отправляем уведомление менеджеру

    await add_outbox_task(

        order_id=order_id,

        user_id=callback.from_user.id,

        type_="manager_notification",

        content=f"Заказ #{order_id}: Пользователь выбрал электронную версию книги"

    )

    

    await callback.answer()

    await log_state(callback.message, state)



@dp.callback_query(F.data == "book_delivery_print")

async def book_delivery_print_callback(callback: types.CallbackQuery, state: FSMContext):

    data = await state.get_data()

    order_id = data.get('order_id')

    

    # Сохраняем выбор печатной версии

    await state.update_data(book_format="Печатная книга")

    

    await callback.message.edit_text(

        "📦 <b>Печатная версия выбрана!</b>\n\n"

        "Для доставки печатной книги нам нужны ваши данные. "

        "Пожалуйста, введите адрес доставки, например, 455000, Республика Татарстан, г. Казань, ул. Ленина, д. 52, кв. 43",

        parse_mode="HTML"

    )

    

    await state.set_state(DeliveryStates.waiting_for_address)

    

    await callback.answer()

    await log_state(callback.message, state)



@dp.message(StateFilter(DeliveryStates.waiting_for_address))

async def save_address(message: types.Message, state: FSMContext):

    # Сохраняем адрес

    await state.update_data(delivery_address=message.text)

    await message.answer(

        "✅ <b>Адрес сохранен!</b>\n\n"

        "Теперь введи имя получателя (ФИО), например, Иванов Иван Иванович",

        parse_mode="HTML"

    )

    await state.set_state(DeliveryStates.waiting_for_recipient)

    await log_state(message, state)



@dp.message(StateFilter(DeliveryStates.waiting_for_recipient))

async def save_recipient(message: types.Message, state: FSMContext):

    # Сохраняем имя получателя

    await state.update_data(delivery_recipient=message.text)

    await message.answer(

        "✅ <b>Имя получателя сохранено!</b>\n\n"

        "Теперь введи телефон для связи (для курьера), например: +7 900 000 00 00",

        parse_mode="HTML"

    )

    await state.set_state(DeliveryStates.waiting_for_phone)

    await log_state(message, state)



@dp.message(StateFilter(DeliveryStates.waiting_for_phone))

async def save_phone(message: types.Message, state: FSMContext):

    # Валидация номера телефона

    phone = message.text.strip()

    

    # Удаляем все пробелы, скобки, дефисы и другие символы

    phone_clean = re.sub(r'[^\d+]', '', phone)

    

    # Проверяем, что номер содержит только цифры и возможно знак +

    if not re.match(r'^\+?[\d\s\(\)\-]+$', phone):

        await message.answer(

            "❌ <b>Неверный формат номера телефона!</b>\n\n"

            "Пожалуйста, введите номер в одном из форматов:\n"

            "• +7 (999) 123-45-67\n"

            "• 89991234567\n"

            "• 9991234567\n\n"

            "Попробуйте еще раз:",

            parse_mode="HTML"

        )

        return

    

    # Проверяем минимальную длину (должно быть минимум 10 цифр)

    digits_only = re.sub(r'[^\d]', '', phone)

    if len(digits_only) < 10:

        await message.answer(

            "❌ Номер телефона должен содержать от 11 цифр.\n"

            "Пожалуйста, введи корректный номер телефона 💌",

            parse_mode="HTML"

        )

        return

    

    # Проверяем максимальную длину (не более 15 цифр)

    if len(digits_only) > 15:

        await message.answer(

            "❌ <b>Номер телефона слишком длинный!</b>\n\n"

            "Номер не должен содержать более 15 цифр.\n"

            "Попробуйте еще раз:",

            parse_mode="HTML"

        )

        return

    

    # Сохраняем телефон и завершаем

    data = await state.get_data()

    order_id = data.get('order_id')

    address = data.get('delivery_address')

    recipient = data.get('delivery_recipient')

    

    # Сохраняем в базу данных

    try:

        from db import save_delivery_address

        await save_delivery_address(order_id, message.from_user.id, address, recipient, phone)

    except Exception as e:

        logging.error(f"Ошибка сохранения адреса доставки: {e}")

    

    await message.answer(

        f"✅ <b>Данные доставки сохранены!</b>\n\n"

        f"📦 <b>Адрес:</b> {address}\n"

        f"👤🏼 <b>Получатель:</b> {recipient}\n"

        f"📞 <b>Телефон:</b> {phone}\n\n"

        f"Теперь мы отправляем книгу в печать 📖, и она будет доставлена тебе в течение 1–2 недель ✨",

        parse_mode="HTML"

    )

    

    # Сопроводительное сообщение согласно Главе 15

    # Убрано по запросу пользователя

    

    # Предлагаем дополнительные опции согласно Главе 18

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="Хочу попробовать создать песню! 💕", callback_data="create_song")],

        [InlineKeyboardButton(text="Спасибо, вернусь к вам позже! 💎", callback_data="finish_order")]

    ])

    await message.answer(

        "💌 Спасибо, что доверил нам создание книги!\n"

        "Хочешь сделать подарок ещё более особенным? Мы можем создать для тебя пробную персональную песню — ваши воспоминания превратятся в музыку, которая тронет сердце вашего близкого ✨",

        reply_markup=keyboard,

        parse_mode="HTML"

    )

    

    await state.set_state(DeliveryStates.done)

    

    # Отправляем уведомление менеджеру

    await add_outbox_task(

        order_id=order_id,

        user_id=message.from_user.id,

        type_="manager_notification",

        content=f"Заказ #{order_id}: Сохранен адрес доставки - {address}, получатель: {recipient}, тел: {phone}"

    )

    

    await log_state(message, state)


# Обработчик сообщений в состоянии завершения доставки
@dp.message(StateFilter(DeliveryStates.done), F.text)
async def handle_text_after_delivery_done(message: types.Message, state: FSMContext):
    """Обрабатывает текстовые сообщения после завершения оформления доставки"""
    
    print(f"🔍 ОТЛАДКА: Получено текстовое сообщение в состоянии DeliveryStates.done: '{message.text}' от пользователя {message.from_user.id}")
    
    # Сохраняем сообщение пользователя в историю заказа
    await save_user_message_to_history(message, state, "Сообщение после завершения доставки: ")
    
    # Проверяем текущее состояние FSM - если пользователь уже перешел к следующему этапу
    current_state = await state.get_state()
    
    if current_state and current_state != "DeliveryStates:done":
        await message.answer("❌ Оформление доставки уже завершено! Вы перешли к следующему этапу.")
        return
    
    # Пользователь отвечает администратору - сообщение уже сохранено в историю заказа
    # Не отправляем подтверждение пользователю
    
    await log_state(message, state)


# Апсейл для электронной книги

async def upsell_stage(message, state):

    data = await state.get_data()

    format_name = data.get("format", "📄 Электронная книга")

    logging.info(f"🎯 upsell_stage: format_name = {format_name}")

    

    # Проверяем, какой формат выбрал пользователь изначально

    if format_name == "📄 Электронная книга":

        # Если пользователь выбрал электронную версию - принудительно переходим к подготовке печатной версии

        await message.answer(

            "📦 <b>Теперь мы подготовим печатную книгу для доставки!</b>\n\n"

            "Для доставки печатной версии нам нужны ваши данные. "

            "Пожалуйста, введите <b>адрес доставки</b>:",

            parse_mode="HTML"

        )

        

        # Переходим к сбору адреса доставки

        await state.set_state(DeliveryStates.waiting_for_address)

    else:

        # Если пользователь изначально выбрал печатную версию - не предлагаем апсейл печатной версии

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="💌 Создать песню", callback_data="create_song")],

            [InlineKeyboardButton(text="✅ Завершить", callback_data="finish_order")]

        ])

        

        await message.answer(

            "🎉 <b>Спасибо, что доверили нам создание вашего подарка!</b>\n\n"

            "А хотите создать ещё и песню?",

            reply_markup=keyboard,

            parse_mode="HTML"

        )

    

    await log_state(message, state)



@dp.callback_query(F.data.in_(["upsell_link", "upsell_print", "continue_electronic"]))

async def upsell_option_callback(callback: types.CallbackQuery, state: FSMContext):

    data = await state.get_data()

    order_id = data.get('order_id')

    

    if callback.data == "continue_electronic":

        # Пользователь выбрал продолжить с электронной версией

        await callback.message.edit_text(

            "📄 <b>Отлично! Вы выбрали электронную версию.</b>\n\n"

            "Ваша книга будет отправлена в формате PDF. "

            "Ссылка для скачивания будет отправлена в ближайшее время!",

            parse_mode="HTML"

        )

        

        # Статус заказа уже обновлен на "ready" в book_draft_ok_callback

        logging.info(f"📚 Пользователь подтвердил выбор электронной версии для заказа {order_id}")

        

        # Отправляем финальные кнопки

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="💌 Создать песню", callback_data="create_song")],

            [InlineKeyboardButton(text="✅ Завершить", callback_data="finish_order")],

            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_upsell_choice")]

        ])

        

        await callback.message.answer(

            "🎉 <b>Спасибо, что доверили нам создание вашего подарка!</b>\n\n"

            "А хотите создать ещё и песню?",

            reply_markup=keyboard,

            parse_mode="HTML"

        )

        

    else:

        # Обработка upsell_link и upsell_print

        try:

            if callback.data == "upsell_link":

                # Оплата за отправку ссылкой

                price = 500  # Цена за отправку ссылкой

                description = f"Отправка ссылкой - заказ #{order_id}" if order_id else "Отправка ссылкой"

                

                payment_data = await create_payment(order_id, price, description, "Дополнительная услуга", is_upsell=True)

                

                keyboard = InlineKeyboardMarkup(inline_keyboard=[

                    [InlineKeyboardButton(text="💳 Оплатить", url=payment_data['confirmation_url'])],

                    [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="check_upsell_payment")],


                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_upsell_choice")]

                ])

                

                # Формируем сводку заказа из базы данных

                order_data = await get_order_summary_data(order_id, state)

                order_summary = ""

                

                await callback.message.edit_text(

                    f"{order_summary}\n"

                    f"💳 <b>Дополнительная оплата:</b>\n"

                    f"Стоимость отправки ссылкой: <b>{price} ₽</b>\n\n"

                    f"Для получения ссылки нажмите кнопку оплаты ниже:\n\n",

                    reply_markup=keyboard,

                    parse_mode="HTML"

                )

                

            elif callback.data == "upsell_print":

                # Оплата за печатную версию - доплата (разница между печатной и электронной версией)

                price = await get_upgrade_price_difference("Книга", "📄 Электронная книга", "📦 Печатная версия")

                # Получаем актуальные цены для отображения
                try:
                    ebook_price = await get_product_price_async("Книга", "📄 Электронная книга")
                    combo_price = await get_product_price_async("Книга", "📦 Печатная версия")
                except:
                    ebook_price = 1990
                    combo_price = 7639

                description = f"Доплата за печатную версию книги - заказ #{order_id}" if order_id else "Доплата за печатную версию книги"

                

                payment_data = await create_payment(order_id, price, description, "Дополнительная услуга", is_upsell=True)

                

                keyboard = InlineKeyboardMarkup(inline_keyboard=[

                    [InlineKeyboardButton(text="💳 Оплатить", url=payment_data['confirmation_url'])],

                    [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="check_upsell_payment")],


                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_upsell_choice")]

                ])

                

                await callback.message.edit_text(

                    f"💳 Дополнительная оплата:\n"

                    f"Электронная версия: {ebook_price} ₽ (уже оплачена)\n"

                    f"Печатная версия: {combo_price} ₽\n"

                    f"Доплата: {price} ₽\n\n"

                    f"После оплаты доплаты мы подготовим и отправим вам печатную версию книги:\n\n",

                    reply_markup=keyboard,

                    parse_mode="HTML"

                )

            

            # Сохраняем данные платежа в state

            await state.update_data(

                upsell_payment_id=payment_data['payment_id'],

                upsell_payment_url=payment_data['confirmation_url'],

                upsell_type="link" if callback.data == "upsell_link" else "print"

            )

            

        except Exception as e:

            logging.error(f"Ошибка создания upsell платежа: {e}")

            await callback.message.edit_text(

                "Произошла ошибка при создании платежа. Попробуйте позже или обратитесь в поддержку."

            )

    

    await callback.answer()

    await log_state(callback.message, state)



# Обработчик кнопки "Назад" для возврата к выбору формата

@dp.callback_query(F.data == "back_to_upsell_choice")

async def back_to_upsell_choice_callback(callback: types.CallbackQuery, state: FSMContext):

    data = await state.get_data()

    order_id = data.get('order_id')

    

    # Возвращаемся к исходному выбору формата

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="📦 Получить печатную версию", callback_data="upsell_print")],

        [InlineKeyboardButton(text="📄 Продолжить с электронной", callback_data="continue_electronic")]

    ])

    

    await callback.message.edit_text(

        "🎉 <b>Ваша книга готова! Спасибо, что выбрали нас ❤️</b>\n\n"

        "Мы подготовили для вас электронную версию (PDF). "

        "Ссылка для скачивания будет отправлена в ближайшее время!\n\n"

        "Выберите вариант:",

        reply_markup=keyboard,

        parse_mode="HTML"

    )

    

    await callback.answer()

    await log_state(callback.message, state)



# Глава 17. Апсейл и Глава 18. Обратная связь - улучшенная версия

@dp.callback_query(F.data == "create_song")

async def create_song_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    # Получаем username из последнего заказа пользователя

    user_id = callback.from_user.id

    from db import get_last_order_username

    last_username = await get_last_order_username(user_id)

    

    # Получаем данные пользователя из предыдущего заказа книги

    from db import get_user_active_order

    previous_order = await get_user_active_order(user_id, "Книга")

    

    # Извлекаем данные пользователя из предыдущего заказа

    # first_name и last_name НЕ подтягиваем автоматически из Telegram

    user_first_name = None

    user_last_name = None

    

    if previous_order and previous_order.get('order_data'):

        try:

            import json

            order_data = json.loads(previous_order.get('order_data', '{}')) if previous_order and isinstance(previous_order.get('order_data'), str) else (previous_order.get('order_data', {}) if previous_order else {})

            user_first_name = order_data.get('first_name', user_first_name)

            user_last_name = order_data.get('last_name', user_last_name)

        except:

            pass

    

    # Очищаем состояние для создания песни

    await state.clear()

    

    # Устанавливаем базовые данные пользователя

    await state.update_data(

        user_id=user_id,

        username=last_username or callback.from_user.username,

        first_name=user_first_name,

        last_name=user_last_name

    )

    

    # Используем новую функцию с проверкой имени

    await start_song_creation_flow(callback, state)

    await log_state(callback.message, state)



@dp.callback_query(F.data == "finish_order")

async def finish_order_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    data = await state.get_data()

    order_id = data.get('order_id')

    

    # Завершаем заказ независимо от формата

    await callback.message.edit_text(

        "Спасибо, что выбрал именно нас для создания своего сокровенного подарка💝\n\n"

        "Когда захочешь снова подарить эмоции и тронуть сердце близкого человека — возвращайся 🫶🏻\n\n"

        "Мы будем здесь для тебя,\n"

        "Команда \"В самое сердце\" 💖",

        parse_mode="HTML"

    )

    

    # Обновляем статус заказа на "завершен"

    await update_order_status(order_id, "completed")

    

    # Отправляем уведомление менеджеру о завершении заказа

    await add_outbox_task(

        order_id=order_id,

        user_id=callback.from_user.id,

        type_="manager_notification",

        content=f"Заказ #{order_id}: Пользователь завершил заказ. Книга доставлена успешно."

    )

    

    # Очищаем состояние

    await state.clear()

    

    await log_state(callback.message, state)



# Обработчик проверки статуса платежа

@dp.callback_query(F.data == "check_payment")

async def check_payment_status(callback: types.CallbackQuery, state: FSMContext):

    try:

        data = await state.get_data()

        payment_id = data.get('payment_id')

        order_id = data.get('order_id')

        product = data.get('product', 'Книга')

        

        if not payment_id:

            await callback.answer("Ошибка: данные платежа не найдены", show_alert=True)

            return

        

        # Проверяем, есть ли order_id

        if order_id is None:

            # Проверяем, есть ли уже активный заказ для этого пользователя

            user_id = callback.from_user.id

            existing_order = await get_user_active_order(user_id, product)

            

            if existing_order:

                # Используем существующий заказ

                order_id = existing_order.get('id') if existing_order else None

                await state.update_data(order_id=order_id)

            else:

                # Создаем новый заказ только если нет существующего

                # Получаем данные пользователя из state

                user_data = await state.get_data()

                order_data = {

                    "product": product,

                    "user_id": user_id,  # Используем правильный user_id из callback

                    "username": user_data.get('username'),

                    "first_name": user_data.get('first_name'),

                    "last_name": user_data.get('last_name')

                }

                order_id = await create_order(user_id, order_data)

                await state.update_data(order_id=order_id)

        

        # Проверяем статус платежа

        payment_data = await get_payment_status(payment_id)
        
        if not payment_data:
            await callback.answer("❌ Не удалось получить статус платежа. Попробуйте позже.", show_alert=True)
            return
            
        status = payment_data.get('status')

        if status == 'succeeded':
            # Отменяем прогревочные сообщения при успешной оплате

            try:

                from db import cleanup_trigger_messages_by_type

                await cleanup_trigger_messages_by_type(order_id, ['song_warming_example', 'song_warming_motivation'])

                logging.info(f"✅ Отменены прогревочные сообщения для заказа {order_id}")

            except Exception as e:

                logging.error(f"❌ Ошибка отмены прогревочных сообщений: {e}")

            

            # Обновляем статус заказа
            await update_order_status(order_id, "paid")
            logging.info(f"✅ check_payment_status: Статус заказа {order_id} обновлен на 'paid'")

            

            # Получаем данные заказа для трекинга
            try:
                import json
                from yookassa_integration import get_payment_by_order_id
                payment = await get_payment_by_order_id(order_id)
                total_amount = float(payment.get('amount', 0)) if payment else 0
                
                # Получаем тип продукта из заказа
                order = await get_order(order_id)
                if order:
                    order_data = json.loads(order.get('order_data', '{}'))
                    product_type = order_data.get('product', product)  # fallback на переменную product
                else:
                    product_type = product
                    
            except Exception as e:
                print(f"❌ Ошибка получения данных платежа/заказа: {e}")
                total_amount = 0
                product_type = product

            # Трекинг: завершение покупки
            await track_event(
                user_id=callback.from_user.id,
                event_type='purchase_completed',
                event_data={
                    'order_id': order_id,
                    'product': product_type,
                    'amount': total_amount
                },
                product_type=product_type,
                order_id=order_id,
                amount=total_amount
            )

            

            # ПРИНУДИТЕЛЬНО отправляем сообщение с согласием (не ждем webhook)
            logging.info(f"💡 check_payment_status: Оплата прошла успешно для заказа {order_id}, отправляем согласие")
            
            # Отправляем сообщение с согласием на обработку данных
            try:
                from db import add_outbox_task
                
                # Получаем тип продукта
                order = await get_order(order_id)
                product_type = 'подарок'
                if order and order.get('order_data'):
                    import json
                    try:
                        parsed_data = json.loads(order.get('order_data', '{}'))
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
                    user_id=callback.from_user.id,
                    type_="text_with_buttons",
                    content=consent_message,
                    button_text="✅ Согласен|❌ Не согласен",
                    button_callback="personal_data_consent_yes|personal_data_consent_no"
                )
                logging.info(f"✅ CHECK_PAYMENT: Добавлено уведомление о согласии для заказа {order_id}")
                
                # Автоматическая проверка должна обработать платеж
                logging.info(f"✅ CHECK_PAYMENT: Платеж успешен, автоматическая проверка обработает заказ {order_id}")
                
                # Обновляем статус заказа
                await update_order_status(order_id, "paid")
                
                # Создаем таймер для этапа "paid"
                from db import create_or_update_user_timer
                product_type = order_data.get('product', 'Неизвестно')
                await create_or_update_user_timer(callback.from_user.id, order_id, "paid", product_type)
                logging.info(f"✅ Создан таймер для этапа paid, продукт {product_type}, пользователь {callback.from_user.id}, заказ {order_id}")
                
            except Exception as e:
                logging.error(f"❌ Ошибка отправки согласия: {e}")
            
            await callback.answer("Оплата прошла успешно ✅")

            

        elif status == 'pending':

            await callback.answer("⏳ Платеж в обработке. Попробуйте проверить через несколько минут.", show_alert=True)

            

        elif status == 'canceled':

            await callback.answer("❌ Платеж отменен. Попробуйте создать новый платеж.", show_alert=True)

            

        else:

            await callback.answer(f"Статус платежа: {status}", show_alert=True)

            

    except Exception as e:

        logging.error(f"Ошибка проверки платежа: {e}")

        await callback.answer("Произошла ошибка при проверке платежа", show_alert=True)

    

    await callback.answer()

    await log_state(callback.message, state)



# Обработчик проверки статуса upsell платежа

@dp.callback_query(F.data == "check_upsell_payment")

async def check_upsell_payment_status(callback: types.CallbackQuery, state: FSMContext):

    try:

        data = await state.get_data()

        payment_id = data.get('upsell_payment_id')

        

        if not payment_id:

            await callback.answer("Платеж не найден", show_alert=True)

            return

        

        # Получаем статус платежа из ЮKassa

        payment_status = await get_payment_status(payment_id)

        

        if not payment_status:

            await callback.answer("Не удалось получить статус платежа", show_alert=True)

            return

        

        status = payment_status['status']

        

        if status == 'succeeded':

            # Платеж успешен - получаем тип доплаты
            upsell_type = data.get('upsell_type', 'print')
            order_id = data.get('order_id')

            # Обновляем статус заказа
            if order_id:
                await update_order_status(order_id, "upsell_paid")
                
                # Трекинг: дополнительная покупка
                await track_event(
                    user_id=callback.from_user.id,
                    event_type='upsell_purchased',
                    event_data={
                        'order_id': order_id,
                        'upsell_type': upsell_type
                    },
                    order_id=order_id
                )

            if upsell_type == "print":

                # Для печатной версии - переходим к сбору данных для доставки

                await callback.message.edit_text(

                    "✅ <b>Доплата за печатную версию прошла успешно!</b>\n\n"

                    "Теперь нам нужны ваши данные для доставки печатной книги.\n\n"

                    "Пожалуйста, введите адрес доставки, например: 455000, Республика Татарстан, г. Казань, ул. Ленина, д. 52, кв. 43",

                    parse_mode="HTML"

                )

                

                await state.set_state(DeliveryStates.waiting_for_address)

                

            else:

                # Для других типов upsell

                await callback.message.edit_text(

                    "✅ <b>Дополнительная оплата прошла успешно!</b>\n\n"

                "Ваша услуга будет предоставлена в ближайшее время."

            )

                

                # Отправляем финальные кнопки

                keyboard = InlineKeyboardMarkup(inline_keyboard=[

                    [InlineKeyboardButton(text="💌 Создать песню", callback_data="create_song")],

                    [InlineKeyboardButton(text="✅ Завершить", callback_data="finish_order")]

                ])

                

                await callback.message.answer(

                    "🎉 <b>Спасибо, что доверили нам создание вашего подарка!</b>\n\n"

                    "А хотите создать ещё и песню?",

                    reply_markup=keyboard,

                    parse_mode="HTML"

                )

            

        elif status == 'pending':

            await callback.answer("⏳ Платеж в обработке. Попробуйте проверить через несколько минут.", show_alert=True)

            

        elif status == 'canceled':

            await callback.answer("❌ Платеж отменен. Попробуйте создать новый платеж.", show_alert=True)

            

        else:

            await callback.answer(f"Статус платежа: {status}", show_alert=True)

            

    except Exception as e:

        logging.error(f"Ошибка проверки upsell платежа: {e}")

        await callback.answer("Произошла ошибка при проверке платежа", show_alert=True)

    

    await callback.answer()

    await log_state(callback.message, state)












# --- Обработчики кнопок анкеты песни ---

@dp.callback_query(F.data == "continue_with_5_facts")

async def continue_with_5_facts_callback(callback: types.CallbackQuery, state: FSMContext):

    """Обработчик кнопки 'Продолжить с 5 фактами'"""

    try:

        data = await state.get_data()

        facts = data.get("song_facts", [])

        

        # Удаляем дубликаты

        unique_facts = []

        for fact in facts:

            fact_clean = fact.strip().lower()

            if fact_clean not in [f.strip().lower() for f in unique_facts]:

                unique_facts.append(fact)

        

        # Проверяем, есть ли уже активный заказ для этого пользователя

        user_id = callback.from_user.id

        existing_order = await get_user_active_order(user_id, "Песня")

        

        if existing_order:

            # Используем существующий заказ и обновляем его данные

            order_id = existing_order.get('id') if existing_order else None

            await state.update_data(order_id=order_id)

            

            # Обновляем данные заказа в базе (формат для админки)

            order_data = {

                "product": "Песня",

                "hero_name": data.get('song_recipient_name', ''),  # Для админки

                "style": data.get('song_style', ''),  # Для админки

                "answers": unique_facts,  # Для админки (список фактов)

                "song_gender": data.get('song_gender'),

                "song_relation": data.get('song_relation'),

                "song_recipient_name": data.get('song_recipient_name'),

                "song_gift_reason": data.get('song_gift_reason'),

                "song_style": data.get('song_style'),

                "song_quiz_special": data.get('song_quiz_special'),

                "song_quiz_memory": data.get('song_quiz_memory'),

                "song_facts": unique_facts,

                "username": data.get('username'),

                "first_name": data.get('first_name'),

                "last_name": data.get('last_name')

            }

            

            # Обновляем order_data в существующем заказе

            await update_order_data(order_id, order_data)

        else:

            # Создаем новый заказ только если нет существующего (формат для админки)

            order_data = {

                "product": "Песня",

                "user_id": data.get('user_id'),

                "username": data.get('username'),

                "first_name": data.get('first_name'),

                "last_name": data.get('last_name'),

                "hero_name": data.get('song_recipient_name', ''),  # Для админки

                "style": data.get('song_style', ''),  # Для админки

                "answers": unique_facts,  # Для админки (список фактов)

                "song_gender": data.get('song_gender'),

                "song_relation": data.get('song_relation'),

                "song_recipient_name": data.get('song_recipient_name'),

                "song_gift_reason": data.get('song_gift_reason'),

                "song_style": data.get('song_style'),

                "song_quiz_special": data.get('song_quiz_special'),

                "song_quiz_memory": data.get('song_quiz_memory'),

                "song_facts": unique_facts

            }

            

            order_id = await create_order(user_id, order_data)

            await state.update_data(order_id=order_id)

        

        # Для песни переводим в ожидание предфинальной версии

        await update_order_status(order_id, "waiting_draft")

        

        # --- Ожидание предфинальной версии песни ---

        await callback.message.edit_text(

            f"🎙 Ваша песня под номером №{order_id:04d} уже в работе 💌\n"

            f"Мы бережно собрали ваши воспоминания и теперь начинаем превращать их в музыку. Совсем скоро она оживёт 🎶"

        )
        
        # Создаем таймер для этапа waiting_full_song (Глава 4: Ожидание полной песни)
        from db import create_or_update_user_timer
        await create_or_update_user_timer(callback.from_user.id, order_id, "waiting_full_song", "Песня")
        logging.info(f"✅ Создан таймер для этапа waiting_full_song (Глава 4), пользователь {callback.from_user.id}, заказ {order_id}")

        

        # --- Ожидание и прогрев — планируем 1–2 сообщения ---

        try:

            from db import add_delayed_message

            # 1) Пример использования песни

            await add_delayed_message(

                order_id=order_id,

                user_id=user_id,

                message_type="song_warming_example",

                content="💡 Один из наших клиентов включил песню во время ужина с женой. Было трогательно до слёз!",

                delay_minutes=1440  # через 24 часа

            )

            # 2) Мотивационное сообщение

            await add_delayed_message(

                order_id=order_id,

                user_id=user_id,

                message_type="song_warming_motivation",

                content="✨ Песня — это больше, чем подарок. Это признание. И мы почти закончили!",

                delay_minutes=2880  # через 48 часов

            )

        except Exception as e:

            logging.error(f"Не удалось запланировать прогревочные сообщения: {e}")

        

        # Переходим в состояние ожидания предфинальной версии песни

        await state.set_state(SongDraftStates.waiting_for_draft)

        

        await callback.answer()

        await log_state(callback.message, state)

        

    except Exception as e:

        logging.error(f"❌ Ошибка в continue_with_5_facts_callback: {e}")

        await callback.answer("Произошла ошибка. Попробуйте еще раз.")



@dp.callback_query(F.data == "add_more_facts")

async def add_more_facts_callback(callback: types.CallbackQuery, state: FSMContext):

    """Обработчик кнопки 'Добавить ещё воспоминания'"""

    try:

        await callback.message.edit_text(

            "💡 Отлично! Добавьте ещё 1-3 факта для более персонализированной песни.\n\n"

            "Вы можете отвечать по одному факту в сообщении или написать несколько фактов одним сообщением."

        )

        

        # Остаемся в том же состоянии для сбора дополнительных фактов

        await callback.answer()

        await log_state(callback.message, state)

        

    except Exception as e:

        logging.error(f"❌ Ошибка в add_more_facts_callback: {e}")

        await callback.answer("Произошла ошибка. Попробуйте еще раз.")



# Обработчик выбора индивидуальных страниц

@dp.callback_query(F.data.startswith("choose_page_"))

async def choose_individual_page(callback: types.CallbackQuery, state: FSMContext):

    try:

        page_num = int(callback.data.replace("choose_page_", ""))

        print(f"🔍 ОТЛАДКА: choose_individual_page: callback.data={callback.data}, page_num={page_num}")

        

        # Получаем текущие выбранные страницы для конкретного заказа

        data = await state.get_data()

        order_id = data.get('order_id')

        selected_pages = data.get(f"selected_pages_{order_id}", [])

        

        # Проверяем, завершен ли уже выбор страниц для этого заказа

        selection_finished = data.get(f"page_selection_finished_{order_id}", False)

        

        # Проверяем текущее состояние FSM - если пользователь уже перешел к следующему этапу

        current_state = await state.get_state()

        if current_state and current_state != "BookFinalStates:choosing_pages":

            await callback.answer("❌ Выбор страниц уже завершен! Вы перешли к следующему этапу.")

            return

        

        if page_num in selected_pages:

            # Проверяем, можно ли отменять выбор

            if selection_finished:

                await callback.answer("✅ Вы уже всё выбрали! Выбор страниц завершен.")

                return

            # Убираем страницу из выбранных

            selected_pages.remove(page_num)

            await callback.answer(f"❌ Выбрано страниц: {len(selected_pages)}/24")

        else:

            # Проверяем ограничение в 24 страницы

            if len(selected_pages) >= 24:

                await callback.answer("❌ Вы уже выбрали 24 сюжета! Можете перевыбрать, убрав некоторые из выбранных.")

                return

            # Добавляем страницу к выбранным

            selected_pages.append(page_num)

            await callback.answer(f"✅ Выбрано страниц: {len(selected_pages)}/24")

        

        # Сохраняем обновленный список для конкретного заказа

        await state.update_data({f"selected_pages_{order_id}": selected_pages})

        

        # Обновляем сообщение с прогрессом

        progress_text = f"Выберите страницы (ровно 24)\n\n"

        

        # Проверяем, достигнут ли минимум (24 страницы)

        minimum_reached = len(selected_pages) >= 24

        minimum_already_processed = data.get(f"minimum_processed_{order_id}", False)

        

        if minimum_reached and not minimum_already_processed:

            # Сохраняем выбранные страницы в базу данных

            if order_id:

                await save_selected_pages(order_id, selected_pages)

                print(f"🔍 ОТЛАДКА: Сохранены выбранные страницы для заказа {order_id}: {selected_pages}")

            

            # Отмечаем, что минимум был обработан для этого заказа

            await state.update_data({f"minimum_processed_{order_id}": True})

            

            # Показываем кнопку "Убрать из выбранных" для последней выбранной страницы

            current_caption = callback.message.caption or ""

            description_part = extract_page_description(current_caption)

            

            new_caption = f"✅ {description_part}\n\n{progress_text}"

            

            keyboard_buttons = []

            keyboard_buttons.append([InlineKeyboardButton(text="Убрать из выбранных", callback_data=f"choose_page_{page_num}")])

            new_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

            

            await callback.message.edit_caption(

                caption=new_caption,

                reply_markup=new_keyboard

            )

            

            # Отправляем сообщение с кнопкой "Продолжить" только один раз

            continue_message_sent = data.get(f"continue_message_sent_{order_id}", False)

            if not continue_message_sent:

                # Отправляем сообщение с кнопкой "Продолжить"

                continue_keyboard = InlineKeyboardMarkup(inline_keyboard=[

                    [InlineKeyboardButton(text="Продолжить создание книги", callback_data="continue_book_creation")]

                ])

                

                await callback.message.answer(

                    "🎉 <b>Отлично! Выбор сделан!</b>\n\n"

                    "✅ Выбор завершен\n"

                    "📚 Ваша книга будет содержать 24 уникальные страницы\n\n"

                    "Нажмите кнопку ниже, чтобы продолжить создание книги:",

                    reply_markup=continue_keyboard,

                    parse_mode="HTML"

                )

                

                # Отмечаем, что сообщение с кнопкой "Продолжить" было отправлено

                await state.update_data({f"continue_message_sent_{order_id}": True})

                print(f"🔍 ОТЛАДКА: Отправлено сообщение с кнопкой 'Продолжить' для заказа {order_id}")

            

            print(f"🔍 ОТЛАДКА: Достигнут минимум 24 страницы для заказа {order_id}, но автоматический переход отключен")

            return  # Выходим, чтобы не обновлять текущее сообщение еще раз

        elif len(selected_pages) < 24:

            # Сохраняем выбранные страницы в базу данных даже если минимум не достигнут

            if order_id:

                await save_selected_pages(order_id, selected_pages)

                print(f"🔍 ОТЛАДКА: Сохранены выбранные страницы для заказа {order_id}: {selected_pages} (минимум не достигнут)")

            

            # Если количество стало меньше 24, сбрасываем флаги обработки

            if len(selected_pages) < 24:

                if minimum_already_processed:

                    await state.update_data({f"minimum_processed_{order_id}": False})

                    print(f"🔍 ОТЛАДКА: Сброшен флаг обработки для заказа {order_id} (количество < 24)")

                

                # НЕ сбрасываем флаг отправки сообщения с кнопкой "Продолжить"

                # Сообщение должно отправляться только один раз, даже если пользователь меняет страницы

        

        # Обновляем сообщение - извлекаем описание страницы более надежно

        current_caption = callback.message.caption or ""

        description_part = extract_page_description(current_caption)

        

        # Меняем иконку в зависимости от того, выбрана страница или нет

        if page_num in selected_pages:

            new_caption = f"✅ {description_part}\n\n{progress_text}"

        else:

            new_caption = f"📖 {description_part}\n\n{progress_text}"

        

        # Обновляем кнопки в зависимости от состояния

        keyboard_buttons = []

        

        if selection_finished:

            # Выбор завершен - скрываем все кнопки выбора

            if page_num in selected_pages:

                # Показываем только статус для выбранных страниц

                keyboard_buttons.append([InlineKeyboardButton(text="✅ Выбрано (вы уже всё выбрали)", callback_data="selection_finished")])

            # Для невыбранных страниц не показываем кнопки вообще

        else:

            # Выбор еще не завершен - показываем обычные кнопки

            if page_num in selected_pages:

                # Показываем кнопку "Убрать из выбранных"

                keyboard_buttons.append([InlineKeyboardButton(text="Убрать из выбранных", callback_data=f"choose_page_{page_num}")])

            else:

                # Показываем кнопку "Выбрать"

                keyboard_buttons.append([InlineKeyboardButton(text="Выбрать", callback_data=f"choose_page_{page_num}")])

        

        new_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        

        await callback.message.edit_caption(

            caption=new_caption,

            reply_markup=new_keyboard

        )

        

        # Больше не отправляем отдельное сообщение о минимуме - сразу переходим к следующему шагу

        

    except Exception as e:

        logging.error(f"❌ Ошибка в choose_individual_page: {e}")

        await callback.answer("Произошла ошибка. Попробуйте еще раз.")





    

    await callback.answer()

    await log_state(callback.message, state)



# Обработчик для кнопки "Выбор завершен"

@dp.callback_query(F.data == "selection_finished")

async def selection_finished_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer("✅ Вы уже всё выбрали! Выбор страниц завершен.")



# Обработчик удаления страниц

@dp.callback_query(F.data.startswith("remove_page_"))

async def remove_individual_page(callback: types.CallbackQuery, state: FSMContext):

    try:

        page_num = int(callback.data.replace("remove_page_", ""))

        print(f"🔍 ОТЛАДКА: remove_individual_page: callback.data={callback.data}, page_num={page_num}")

        

        # Получаем текущие выбранные страницы для конкретного заказа

        data = await state.get_data()

        order_id = data.get('order_id')

        selected_pages = data.get(f"selected_pages_{order_id}", [])

        

        # Проверяем, завершен ли уже выбор страниц для этого заказа

        selection_finished = data.get(f"page_selection_finished_{order_id}", False)

        

        if selection_finished:

            await callback.answer("✅ Вы уже всё выбрали! Выбор страниц завершен.")

            return

        

        # Убираем страницу из выбранных (если она была выбрана)

        if page_num in selected_pages:

            selected_pages.remove(page_num)

            await callback.answer(f"❌ Выбрано страниц: {len(selected_pages)}/24")

        else:

            await callback.answer("ℹ️ Страница не была выбрана")

        

        # Сохраняем обновленный список для конкретного заказа

        await state.update_data({f"selected_pages_{order_id}": selected_pages})

        

        # Если количество стало 0 (полная отмена всех выборов), сбрасываем флаг уведомления

        if len(selected_pages) == 0:

            minimum_already_notified = data.get(f"minimum_notified_{order_id}", False)

            if minimum_already_notified:

                await state.update_data({f"minimum_notified_{order_id}": False})

                print(f"🔍 ОТЛАДКА: Сброшен флаг уведомления для заказа {order_id} (полная отмена)")

        

        # УДАЛЯЕМ СООБЩЕНИЕ С ФОТОГРАФИЕЙ ИЗ ЧАТА

        try:

            await callback.message.delete()

            print(f"✅ Сообщение с фотографией страницы {page_num} удалено из чата")

            

        except Exception as delete_error:

            logging.error(f"❌ Ошибка удаления сообщения: {delete_error}")

            # Если не удалось удалить сообщение, показываем уведомление

            await callback.answer("❌ Не удалось удалить сообщение из чата")

        

    except Exception as e:

        logging.error(f"❌ Ошибка в remove_individual_page: {e}")

        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

    

    await log_state(callback.message, state)



# Функция для удаления кнопок с других сообщений обложек

async def remove_cover_buttons_from_other_messages(user_id: int, selected_template_id: int):

    """Удаляет кнопки выбора с других сообщений обложек после выбора одной"""

    try:

        from db import get_cover_templates

        cover_templates = await get_cover_templates()

        

        # Получаем бота из контекста

        from aiogram import Bot

        bot = Bot.get_current()

        

        # Проходим по всем обложкам, кроме выбранной

        for template in cover_templates:

            if template['id'] != selected_template_id:

                try:

                    # Пытаемся найти и обновить сообщение с этой обложкой

                    # Это сложно сделать без сохранения message_id, поэтому просто пропускаем

                    pass

                except Exception as e:

                    print(f"❌ Ошибка обновления сообщения с обложкой {template['id']}: {e}")

    except Exception as e:

        print(f"❌ Ошибка в remove_cover_buttons_from_other_messages: {e}")



# Функция для отправки примеров голосов

async def send_voice_examples(message: types.Message, user_gender: str):

    """Отправляет примеры голосов перед выбором стиля"""

    try:

        logging.info(f"🎵 send_voice_examples вызвана с полом: '{user_gender}'")

        # Проверяем, что пол определен
        if not user_gender or user_gender == '':
            logging.warning(f"⚠️ Пол не определен, используем 'парень' по умолчанию")
            user_gender = 'парень'

        # Получаем доступные голоса из базы данных

        from db import get_voice_styles

        voices = await get_voice_styles()

        

        if not voices:

            await message.answer("К сожалению, примеры голосов временно недоступны.")

            return

        

        # Выбираем голоса на основе пола клиента

        matching_voices = []

        logging.info(f"🎵 Поиск голосов для пола: '{user_gender}', доступно голосов: {len(voices)}")

        for voice in voices:

            voice_gender = voice.get('gender', 'male').lower()

            logging.info(f"🎵 Проверяем голос: {voice.get('name', 'Без названия')}, пол: '{voice_gender}'")

            if user_gender == "девушка" and voice_gender in ['female', 'женский']:

                matching_voices.append(voice)

                logging.info(f"✅ Найден подходящий женский голос: {voice.get('name', 'Без названия')}")

            elif user_gender == "парень" and voice_gender in ['male', 'мужской']:

                matching_voices.append(voice)

                logging.info(f"✅ Найден подходящий мужской голос: {voice.get('name', 'Без названия')}")

        

        # Если нет подходящих голосов, берем первый доступный

        if not matching_voices:

            logging.warning(f"⚠️ Не найдено подходящих голосов для пола '{user_gender}', используем первый доступный")

            matching_voices = [voices[0]]

            logging.info(f"🎵 Используем голос: {voices[0].get('name', 'Без названия')}, пол: '{voices[0].get('gender', 'male')}'")

        

        # Отправляем 3 примера голосов с разными эмоциональными окрасками

        await message.answer("Каждая история звучит по-своему, а как звучит твоя?\nПослушай примеры, и выбери свой.")

        

        # Отправляем до 3 примеров голосов для разных стилей песен

        for i, voice in enumerate(matching_voices[:3]):

            audio_path = f"voices/{voice['filename']}"

            

            # Определяем стиль песни для этого примера голоса

            song_styles = ["Нежная и романтичная песня ❤️‍🔥", "Весёлый и жизнерадостный трек🎉", "Глубокая и лиричная мелодия 💓"]

            style_name = song_styles[i] if i < len(song_styles) else "Глубокая и лиричная мелодия 💓"

            

            if os.path.exists(audio_path):

                await message.answer_audio(

                    types.FSInputFile(audio_path),

                    caption=f"Пример {style_name.lower()}",

                    title=f"Пример {style_name.lower()}",

                    performer="BookAI Bot"

                )

            else:

                logging.warning(f"⚠️ Файл голоса не найден: {audio_path}")

                await message.answer(f"Пример {style_name.lower()} (файл недоступен)")

        

        logging.info(f"🎵 Отправлены примеры голосов для пользователя {message.from_user.id}")

        

    except Exception as e:

        logging.error(f"❌ Ошибка отправки примеров голосов: {e}")

        await message.answer("К сожалению, не удалось отправить примеры голосов.")



# Fallback функция для обработки состояния waiting_recipient_name

async def handle_song_recipient_name_fallback(message: types.Message, state: FSMContext):

    """Fallback обработка для состояния waiting_recipient_name"""

    try:

        logging.info(f"🎵 Fallback обработчик song_recipient_name вызван для пользователя {message.from_user.id}")

        logging.info(f"🎵 Получен текст: '{message.text}'")

        await state.update_data(song_recipient_name=message.text)

        

        # Сохраняем сообщение пользователя в историю для админки

        await save_user_message_to_history(message, state, "Имя получателя песни: ")

        

        # Обновляем заказ с именем получателя

        data = await state.get_data()

        order_id = data.get('order_id')

        if order_id:

            # Формируем имя отправителя из first_name и last_name

            first_name = data.get('first_name', '')

            last_name = data.get('last_name', '')

            sender_name = ""

            if first_name and first_name != 'None':

                sender_name = first_name

            if last_name and last_name != 'None':

                if sender_name:

                    sender_name += f" {last_name}"

                else:

                    sender_name = last_name

            

            order_data = {

                "product": "Песня",

                "user_gender": data.get('song_gender', ''),

                "song_relation": data.get('song_relation', ''),

                "song_recipient_name": message.text,

                "hero_name": message.text,  # Для админки

                "song_gender": data.get('song_gender', ''),

                "username": data.get('username'),

                "first_name": data.get('first_name'),

                "last_name": data.get('last_name'),

                "sender_name": sender_name  # Добавляем имя отправителя

            }

            await update_order_data(order_id, order_data)

            await update_order_status(order_id, "recipient_name_entered")

        

        # Проверяем тип продукта - отправляем сообщение только для песни
        product = data.get('product', '')
        if product != "Песня":
            logging.info(f"🔍 Пропускаем сообщение о поводе песни для продукта: {product}")
            return

        logging.info(f"🎵 Отправляем сообщение о поводе подарка пользователю {message.from_user.id}")

        try:

            await message.answer("Напиши по какому поводу мы создаём песню 🎶\nИли это просто подарок без повода?")

            logging.info(f"🎵 Сообщение о поводе подарка отправлено успешно")

        except Exception as send_error:

            logging.error(f"❌ Ошибка отправки сообщения о поводе: {send_error}")

            raise send_error

        

        await state.set_state(SongRelationStates.waiting_gift_reason)

        await log_state(message, state)

        logging.info(f"🎵 Состояние изменено на waiting_gift_reason для пользователя {message.from_user.id}")

        

    except Exception as e:

        logging.error(f"❌ Ошибка в handle_song_recipient_name_fallback: {e}")

        import traceback

        logging.error(f"❌ Traceback: {traceback.format_exc()}")

        await message.answer("Произошла ошибка. Попробуйте еще раз.")



# Fallback функция для обработки состояния waiting_gift_reason

async def handle_song_gift_reason_fallback(message: types.Message, state: FSMContext):

    """Fallback обработка для состояния waiting_gift_reason"""

    try:

        logging.info(f"🎵 Fallback обработчик song_gift_reason вызван для пользователя {message.from_user.id}")

        logging.info(f"🎵 Получен текст: '{message.text}'")

        await state.update_data(song_gift_reason=message.text)

        

        # Сохраняем сообщение пользователя в историю для админки

        await save_user_message_to_history(message, state, "Повод подарка: ")

        

        # Обновляем заказ с поводом подарка

        data = await state.get_data()

        order_id = data.get('order_id')

        if order_id:

            # Формируем имя отправителя из first_name и last_name

            first_name = data.get('first_name', '')

            last_name = data.get('last_name', '')

            sender_name = ""

            if first_name and first_name != 'None':

                sender_name = first_name

            if last_name and last_name != 'None':

                if sender_name:

                    sender_name += f" {last_name}"

                else:

                    sender_name = last_name

            

            order_data = {

                "product": "Песня",

                "user_gender": data.get('song_gender', ''),

                "song_relation": data.get('song_relation', ''),

                "song_recipient_name": data.get('song_recipient_name', ''),

                "hero_name": data.get('song_recipient_name', ''),

                "song_gift_reason": message.text,

                "song_gender": data.get('song_gender', ''),

                "username": data.get('username'),

                "first_name": data.get('first_name'),

                "last_name": data.get('last_name'),

                "sender_name": sender_name

            }

            await update_order_data(order_id, order_data)

            await update_order_status(order_id, "gift_reason_entered")

        

        # Автоматический выбор голоса на основе пола клиента

        await update_order_status(order_id, "voice_selection")

        

        # Получаем пол клиента

        user_gender = data.get('song_gender', '')

        

        # Получаем доступные голоса из базы данных

        from db import get_voice_styles

        voices = await get_voice_styles()

        

        if voices:

            # Выбираем голос автоматически на основе пола клиента

            selected_voice = None

            if user_gender == 'female':

                # Для женщин выбираем мужской голос

                for voice in voices:

                    if voice.get('gender') == 'male':

                        selected_voice = voice

                        break

            else:

                # Для мужчин выбираем женский голос

                for voice in voices:

                    if voice.get('gender') == 'female':

                        selected_voice = voice

                        break

            

            # Если не нашли подходящий голос, берем первый доступный

            if not selected_voice and voices:

                selected_voice = voices[0]

            

            if selected_voice:

                # Формируем имя отправителя

                first_name = data.get('first_name', '')

                last_name = data.get('last_name', '')

                sender_name = ""

                if first_name and first_name != 'None':

                    sender_name = first_name

                if last_name and last_name != 'None':

                    if sender_name:

                        sender_name += f" {last_name}"

                    else:

                        sender_name = last_name

                

                # Обновляем данные заказа с выбранным голосом

                order_data = {

                    "product": "Песня",

                    "user_gender": user_gender,

                    "song_relation": data.get('song_relation', ''),

                    "song_recipient_name": data.get('song_recipient_name', ''),

                    "hero_name": data.get('song_recipient_name', ''),

                    "song_gift_reason": message.text,

                    "song_gender": user_gender,

                    "song_voice": selected_voice['name'],

                    "song_voice_gender": selected_voice.get('gender', 'male'),

                    "username": data.get('username'),

                    "first_name": data.get('first_name'),

                    "last_name": data.get('last_name'),

                    "sender_name": sender_name

                }

                await update_order_data(order_id, order_data)

                

                # Проверяем, не выбран ли уже стиль песни
                song_style = data.get('song_style')
                logging.info(f"🔍 ОТЛАДКА: song_style = '{song_style}', user_id = {message.from_user.id}")
                if not song_style:
                    # НЕ отправляем примеры голосов здесь - пусть отправляет основная функция song_gift_reason
                    logging.info(f"🎵 Fallback: примеры голосов отправит основная функция song_gift_reason")
                else:
                    # Стиль уже выбран, просто игнорируем сообщение
                    logging.info(f"🎵 Стиль уже выбран, игнорируем сообщение от пользователя {message.from_user.id}")

            else:

                await message.answer("К сожалению, голоса временно недоступны. Попробуйте позже.")

        else:

            await message.answer("К сожалению, голоса временно недоступны. Попробуйте позже.")

        

    except Exception as e:

        logging.error(f"❌ Ошибка в handle_song_gift_reason_fallback: {e}")

        import traceback

        logging.error(f"❌ Traceback: {traceback.format_exc()}")

        await message.answer("Произошла ошибка. Попробуйте еще раз.")



# Fallback функция для обработки состояния collecting_facts

async def handle_song_facts_fallback(message: types.Message, state: FSMContext):

    """Fallback обработка для состояния collecting_facts"""

    try:

        logging.info(f"🎵 Fallback обработчик song_facts вызван для пользователя {message.from_user.id}")

        logging.info(f"🎵 Получен текст: '{message.text}'")

        

        # Сохраняем сообщение пользователя в историю для админки

        await save_user_message_to_history(message, state, "Факт о получателе: ")

        

        # Получаем текущие факты из состояния

        data = await state.get_data()

        current_facts = data.get('song_facts', [])

        

        # Добавляем новый факт

        current_facts.append(message.text)

        await state.update_data(song_facts=current_facts)

        

        # Обновляем заказ с фактами

        order_id = data.get('order_id')

        if order_id:

            import json

            order_data = {

                "song_facts": json.dumps(current_facts, ensure_ascii=False)

            }

            await update_order_data(order_id, order_data)

        

        # Проверяем количество фактов

        if len(current_facts) >= 5:

            # Достаточно фактов, переходим к следующему этапу

            await message.answer("Отлично! Мы собрали достаточно информации для создания трогательной песни 🎵\n\nТеперь мы приступим к созданию демо-версии. Скоро вернемся с первыми нотами!")

            

            # Переходим в состояние ожидания демо

            await state.set_state(SongDraftStates.waiting_for_demo)

            await update_order_status(order_id, "demo_content")
            
            # Создаем таймер для ожидания демо
            from db import create_or_update_user_timer
            await create_or_update_user_timer(message.from_user.id, order_id, "waiting_demo_song", "Песня")
            logging.info(f"✅ Создан таймер для этапа waiting_demo_song, пользователь {message.from_user.id}, заказ {order_id}")

            logging.info(f"🎵 Переходим к ожиданию демо для пользователя {message.from_user.id}")

        else:

            # Нужно еще фактов

            remaining = 5 - len(current_facts)

            await message.answer(f"Спасибо! У нас уже {len(current_facts)} фактов. Нужно еще {remaining} фактов для создания идеальной песни 🎶\n\nПоделись еще чем-то особенным о получателе!")

        

    except Exception as e:

        logging.error(f"❌ Ошибка в handle_song_facts_fallback: {e}")

        import traceback

        logging.error(f"❌ Traceback: {traceback.format_exc()}")

        await message.answer("Произошла ошибка. Попробуйте еще раз.")



# --- Глава 2.8. Анкета для песни ---

@dp.message(StateFilter(SongFactsStates.collecting_facts))

async def song_facts_collect(message: types.Message, state: FSMContext):

    logging.info(f"🎵 song_facts_collect вызван для пользователя {message.from_user.id}, текст: '{message.text}'")

    # Сохраняем сообщение пользователя в историю заказа
    data = await state.get_data()
    order_id = data.get('order_id')
    if order_id:
        from db import add_message_history, create_or_update_order_notification
        await add_message_history(order_id, "user", message.text)
        await create_or_update_order_notification(order_id)
        logging.info(f"✅ СОХРАНЕНО: Сообщение пользователя {message.from_user.id} в историю заказа {order_id}: {message.text[:50]}...")

    facts = (await state.get_data()).get("song_facts", [])

    

    # Анализируем сообщение на предмет нескольких фактов

    text = message.text.strip()

    

    # Проверяем, содержит ли сообщение несколько фактов

    # Ищем признаки структурированного ответа (номера, маркеры, переносы строк)

    if any(char in text for char in ['\n', '•', '-', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.']) or re.search(r'\d+[a-z]?[\.\)]', text):

        # Разбиваем на отдельные факты

        lines = text.split('\n')

        new_facts = []

        

        for line in lines:

            line = line.strip()

            # Пропускаем пустые строки

            if not line:

                continue

            # Проверяем, содержит ли строка номер в начале

            if re.match(r'^\d+[a-z]?[\.\)]', line):

                # Если да, сохраняем как есть

                new_facts.append(line)

            else:

                # Убираем номера и маркеры в начале строки (включая формат "1)a", "2)b", "1.", "1)" и т.д.)

                line = re.sub(r'^\d+[a-z]?[\.\)]?\s*', '', line)

                line = line.lstrip('0123456789.•- ')

                if line and len(line) > 0:  # Минимальная длина факта (принимаем любую длину)

                    new_facts.append(line)

        

        # Отладочная информация

        print(f"🔍 ОТЛАДКА: Обработка фактов: найдено {len(new_facts)} фактов")

        print(f"🔍 ОТЛАДКА: Факты: {new_facts}")

        

        # Если нашли несколько фактов, добавляем их все (проверяя дубликаты)

        if len(new_facts) > 1:

            # Проверяем дубликаты перед добавлением

            existing_facts = [f.strip().lower() for f in facts]

            unique_new_facts = []

            for fact in new_facts:

                if fact.strip().lower() not in existing_facts:

                    unique_new_facts.append(fact)

            

            if unique_new_facts:

                facts.extend(unique_new_facts)

                await state.update_data(song_facts=facts)

                await message.answer(f"Отлично! Добавлено {len(unique_new_facts)} новых фактов.")

            else:

                await message.answer("Эти факты уже были добавлены ранее.")

        elif len(new_facts) == 1:

            # Если найден только один факт, добавляем его (проверяя дубликаты)

            existing_facts = [f.strip().lower() for f in facts]

            if new_facts[0].strip().lower() not in existing_facts:

                facts.append(new_facts[0])

                await state.update_data(song_facts=facts)

                await message.answer("Воспоминание добавлено ✅")

            else:

                await message.answer("Это воспоминание было добавлено ранее")

            

            # Показываем прогресс после добавления фактов списком

            unique_facts_temp = []

            for fact in facts:

                fact_clean = fact.strip().lower()

                # Проверяем дубликаты для всех фактов

                if fact_clean not in [f.strip().lower() for f in unique_facts_temp]:

                    unique_facts_temp.append(fact)

            

            if len(unique_facts_temp) >= 5 and len(unique_facts_temp) < 8:

                # Создаем клавиатуру с кнопками выбора

                keyboard = InlineKeyboardMarkup(inline_keyboard=[

                    [InlineKeyboardButton(text="✅ Продолжить", callback_data="continue_with_5_facts")],

                    [InlineKeyboardButton(text="➕ Добавить ещё воспоминания", callback_data="add_more_facts")]

                ])

                

                await message.answer(

                    f"🎉 Отлично! Вы собрали {len(unique_facts_temp)} воспоминаний.\n\n"

                    "Вы можете продолжить с текущим количеством воспоминаний или добавить ещё 1-3 воспоминания для более персонализированной песни.",

                    reply_markup=keyboard

                )

                return

            elif len(unique_facts_temp) >= 8:

                # Достигнут максимум фактов - предлагаем продолжить

                keyboard = InlineKeyboardMarkup(inline_keyboard=[

                    [InlineKeyboardButton(text="✅ Продолжить", callback_data="continue_with_5_facts")]

                ])

                

                await message.answer(

                    f"🎉 Отлично! Вы собрали максимальное количество воспоминаний ({len(unique_facts_temp)}).\n\n"

                    "Теперь мы можем создать максимально персонализированную песню!",

                    reply_markup=keyboard

                )

                return

            else:

                # Показываем прогресс если еще не достигли 5 фактов

                remaining = 5 - len(unique_facts_temp)

                

                # Показываем прогресс

                progress_text = f"📊 <b>Прогресс:</b> {len(unique_facts_temp)}/5 воспоминаний собрано\n\n"

                

                if len(unique_facts_temp) > 0:

                    progress_text += "<b>Собранные воспоминания:</b>\n"

                    for i, fact in enumerate(unique_facts_temp, 1):

                        # Обрезаем длинные факты для отображения

                        display_fact = fact[:50] + "..." if len(fact) > 50 else fact

                        progress_text += f"{i}. {display_fact}\n"

                    progress_text += "\n"

                

                if remaining == 1:

                    progress_text += f"Добавь ещё {remaining} воспоминание о вашем близком или вашей истории 🧩\n"

                    progress_text += "Эти детали помогут нам сделать песню максимально личной и трогательной."

                elif remaining < 5:

                    progress_text += f"Добавь ещё {remaining} воспоминания о вашем близком или вашей истории 🧩\n"

                    progress_text += "Эти детали помогут нам сделать песню максимально личной и трогательной."

                else:

                    progress_text += f"Добавь ещё {remaining} воспоминаний о вашем близком или вашей истории 🧩\n"

                    progress_text += "Эти детали помогут нам сделать песню максимально личной и трогательной."

                

                await message.answer(progress_text, parse_mode="HTML")

                await log_state(message, state)

                return

        else:

            # Если разбивка не дала результатов, но есть паттерн с номерами, попробуем разбить по регулярному выражению

            if re.search(r'\d+[a-z]?[\.\)]', text) and '\n' not in text:

                # Разбиваем по паттерну "число+буква+точка/скобка"

                matches = re.findall(r'\d+[a-z]?[\.\)]\s*([^0-9]*)', text)

                if len(matches) > 1:

                    new_facts = [match.strip() for match in matches if match.strip() and len(match.strip()) > 0]

                    if len(new_facts) > 1:

                        facts.extend(new_facts)

                        await state.update_data(song_facts=facts)

                        await message.answer(f"Отлично! Добавлено {len(new_facts)} фактов.")

                        

                        # Показываем прогресс после добавления фактов списком

                        unique_facts_temp = []

                        for fact in facts:

                            fact_clean = fact.strip().lower()

                            # Проверяем дубликаты для всех фактов

                            if fact_clean not in [f.strip().lower() for f in unique_facts_temp]:

                                unique_facts_temp.append(fact)

                        

                        if len(unique_facts_temp) >= 5:

                            await message.answer("Спасибо! Ваши ответы отправлены в поддержку для создания финальной версии песни.")

                            

                            # Проверяем, есть ли уже активный заказ для этого пользователя

                            data = await state.get_data()

                            user_id = message.from_user.id

                            existing_order = await get_user_active_order(user_id, "Песня")

                            

                            if existing_order:

                                # Используем существующий заказ и обновляем его данные

                                order_id = existing_order.get('id') if existing_order else None

                                await state.update_data(order_id=order_id)

                                

                                # Обновляем данные заказа в базе (формат для админки)

                                order_data = {

                                    "product": "Песня",

                                    "hero_name": data.get('song_recipient_name', ''),  # Для админки

                                    "style": data.get('song_style', ''),  # Для админки

                                    "answers": unique_facts_temp,  # Для админки (список фактов)

                                    "song_gender": data.get('song_gender'),

                                    "song_relation": data.get('song_relation'),

                                    "song_recipient_name": data.get('song_recipient_name'),

                                    "song_gift_reason": data.get('song_gift_reason'),

                                    "song_style": data.get('song_style'),

                                    "song_quiz_special": data.get('song_quiz_special'),

                                    "song_quiz_memory": data.get('song_quiz_memory'),

                                    "song_facts": unique_facts_temp

                                }

                                

                                # Обновляем order_data в существующем заказе

                                await update_order_data(order_id, order_data)

                            else:

                                # Создаем новый заказ только если нет существующего (формат для админки)

                                order_data = {

                                    "product": "Песня",

                                    "user_id": data.get('user_id'),

                                    "username": data.get('username'),

                                    "first_name": data.get('first_name'),

                                    "last_name": data.get('last_name'),

                                    "hero_name": data.get('song_recipient_name', ''),  # Для админки

                                    "style": data.get('song_style', ''),  # Для админки

                                    "answers": unique_facts_temp,  # Для админки (список фактов)

                                    "song_gender": data.get('song_gender'),

                                    "song_relation": data.get('song_relation'),

                                    "song_recipient_name": data.get('song_recipient_name'),

                                    "song_gift_reason": data.get('song_gift_reason'),

                                    "song_style": data.get('song_style'),

                                    "song_quiz_special": data.get('song_quiz_special'),

                                    "song_quiz_memory": data.get('song_quiz_memory'),

                                    "song_facts": unique_facts_temp

                                }

                                

                                order_id = await create_order(user_id, order_data)

                                await state.update_data(order_id=order_id)

                            

                            # Для песни сразу переводим в ожидание черновика

                            await update_order_status(order_id, "waiting_draft")

                            

                            # --- Глава 2.5. Ожидание демо-аудио ---

                            await message.answer(f"🎙 Ваша песня под номером №{order_id:04d} уже в работе 💌\n"

                            f"Мы бережно собрали ваши воспоминания и теперь начинаем превращать их в музыку. Совсем скоро она оживёт 🎶")
                            
                            # Создаем таймер для этапа waiting_full_song (Глава 4: Ожидание полной песни)
                            from db import create_or_update_user_timer
                            await create_or_update_user_timer(message.from_user.id, order_id, "waiting_full_song", "Песня")
                            logging.info(f"✅ Создан таймер для этапа waiting_full_song (Глава 4), пользователь {message.from_user.id}, заказ {order_id}")

                            

                            # --- Глава 2.9. Ожидание и прогрев — планируем 1–2 сообщения ---

                            try:

                                from db import add_delayed_message

                                # 1) Пример использования песни

                                await add_delayed_message(

                                    order_id=order_id,

                                    user_id=user_id,

                                    message_type="song_warming_example",

                                    content="💡 Один из наших клиентов включил песню во время ужина с женой. Было трогательно до слёз!",

                                    delay_minutes=1440  # через 24 часа

                                )

                                # 2) Мотивационное сообщение

                                await add_delayed_message(

                                    order_id=order_id,

                                    user_id=user_id,

                                    message_type="song_warming_motivation",

                                    content="✨ Песня — это больше, чем подарок. Это признание. И мы почти закончили!",

                                    delay_minutes=2880  # через 48 часов

                                )

                            except Exception as e:

                                logging.error(f"Не удалось запланировать прогревочные сообщения: {e}")

                            

                            # Переходим в состояние ожидания демо-аудио

                            await state.set_state(SongDraftStates.waiting_for_demo)

                            await log_state(message, state)

                            return

                        else:

                            # Показываем прогресс если еще не достигли 5 фактов

                            remaining = 5 - len(unique_facts_temp)

                            

                            # Показываем прогресс

                            progress_text = f"📊 <b>Прогресс:</b> {len(unique_facts_temp)}/5 воспоминаний собрано\n\n"

                            

                            if len(unique_facts_temp) > 0:

                                progress_text += "<b>Собранные воспоминания:</b>\n"

                                for i, fact in enumerate(unique_facts_temp, 1):

                                    # Обрезаем длинные факты для отображения

                                    display_fact = fact[:50] + "..." if len(fact) > 50 else fact

                                    progress_text += f"{i}. {display_fact}\n"

                                progress_text += "\n"

                            

                            if remaining == 1:

                                progress_text += f"Добавь ещё {remaining} воспоминание о вашем близком или вашей истории 🧩\n"

                                progress_text += "Эти детали помогут нам сделать песню максимально личной и трогательной."

                            elif remaining < 5:

                                progress_text += f"Добавь ещё {remaining} воспоминания о вашем близком или вашей истории 🧩\n"

                                progress_text += "Эти детали помогут нам сделать песню максимально личной и трогательной."

                            else:

                                progress_text += f"Добавь ещё {remaining} воспоминаний о вашем близком или вашей истории 🧩\n"

                                progress_text += "Эти детали помогут нам сделать песню максимально личной и трогательной."

                            

                            await message.answer(progress_text, parse_mode="HTML")

                            await log_state(message, state)

                            return

                    else:

                        # Проверяем дубликаты перед добавлением

                        existing_facts = [f.strip().lower() for f in facts]

                        if text.strip().lower() not in existing_facts:

                            facts.append(text)

                            await state.update_data(song_facts=facts)

                            await message.answer("Воспоминание добавлено ✅")

                        else:

                            await message.answer("Это воспоминание было добавлено ранее")

                else:

                    # Проверяем дубликаты перед добавлением

                    existing_facts = [f.strip().lower() for f in facts]

                    if text.strip().lower() not in existing_facts:

                        facts.append(text)

                        await state.update_data(song_facts=facts)

                        await message.answer("Воспоминание добавлено ✅")

                    else:

                        await message.answer("Это воспоминание было добавлено ранее")

            else:

                # Если разбивка не дала результатов, добавляем как один факт (проверяя дубликаты)

                existing_facts = [f.strip().lower() for f in facts]

                if text.strip().lower() not in existing_facts:

                    facts.append(text)

                    await state.update_data(song_facts=facts)

                    await message.answer("Воспоминание добавлено ✅")

                else:

                    await message.answer("Это воспоминание было добавлено ранее")

    else:

        # Проверяем, не содержит ли сообщение паттерн с буквами без переносов строк

        if re.search(r'\d+[a-z]?[\.\)]', text):

            # Извлекаем содержимое после каждого паттерна "число+буква+точка/скобка"

            matches = re.findall(r'\d+[a-z]?[\.\)]\s*([^0-9]*)', text)

            new_facts = []

            for i, match in enumerate(matches):

                match = match.strip()

                if match and len(match) > 0:  # Для коротких ответов типа "a", "b", "c" принимаем любую длину

                    # Сохраняем контекст, добавляя номер к факту

                    new_facts.append(f"{i+1}){match}")

            

            if len(new_facts) > 1:

                # Проверяем, не являются ли все факты просто числами

                all_numbers = all(re.match(r'^\d+$', fact.strip()) for fact in new_facts)

                if all_numbers:

                    # Если все факты - числа, добавляем их как есть

                    facts.extend([fact.strip() for fact in new_facts])

                else:

                    # Если есть не только числа, добавляем с номерами

                    facts.extend(new_facts)

                await state.update_data(song_facts=facts)

                await message.answer(f"Отлично! Добавлено {len(new_facts)} фактов.")

                

                # Показываем прогресс после добавления фактов списком

                unique_facts_temp = []

                for fact in facts:

                    if re.match(r'^\d+[a-z]?[\.\)]', fact):

                        unique_facts_temp.append(fact)

                    else:

                        fact_clean = fact.strip().lower()

                        if fact_clean not in [f.strip().lower() for f in unique_facts_temp]:

                            unique_facts_temp.append(fact)

                

                if len(unique_facts_temp) >= 5 and len(unique_facts_temp) < 8:

                    # Создаем клавиатуру с кнопками выбора

                    keyboard = InlineKeyboardMarkup(inline_keyboard=[

                        [InlineKeyboardButton(text="✅ Продолжить", callback_data="continue_with_5_facts")],

                        [InlineKeyboardButton(text="➕ Добавить ещё воспоминания", callback_data="add_more_facts")]

                    ])

                    

                    await message.answer(

                        f"🎉 Отлично! Вы собрали {len(unique_facts_temp)} воспоминаний.\n\n"

                        "Вы можете продолжить с текущим количеством воспоминаний или добавить ещё 1-3 воспоминания для более персонализированной песни.",

                        reply_markup=keyboard

                    )

                    return

                elif len(unique_facts_temp) >= 8:

                    # Достигнут максимум фактов - предлагаем продолжить

                    keyboard = InlineKeyboardMarkup(inline_keyboard=[

                        [InlineKeyboardButton(text="✅ Продолжить", callback_data="continue_with_5_facts")]

                    ])

                    

                    await message.answer(

                        f"🎉 Отлично! Вы собрали максимальное количество воспоминаний ({len(unique_facts_temp)}).\n\n"

                        "Теперь мы можем создать максимально персонализированную песню!",

                        reply_markup=keyboard

                    )

                    return

                else:

                    # Показываем прогресс если еще не достигли 5 фактов

                    remaining = 5 - len(unique_facts_temp)

                    

                    # Показываем прогресс

                    progress_text = f"📊 <b>Прогресс:</b> {len(unique_facts_temp)}/5 воспоминаний собрано\n\n"

                    

                    if len(unique_facts_temp) > 0:

                        progress_text += "<b>Собранные воспоминания:</b>\n"

                        for i, fact in enumerate(unique_facts_temp, 1):

                            # Обрезаем длинные факты для отображения

                            display_fact = fact[:50] + "..." if len(fact) > 50 else fact

                            progress_text += f"{i}. {display_fact}\n"

                        progress_text += "\n"

                    

                    if remaining == 1:

                        progress_text += f"Добавь ещё {remaining} воспоминание о вашем близком или вашей истории 🧩\n"

                        progress_text += "Эти детали помогут нам сделать песню максимально личной и трогательной."

                    elif remaining < 5:

                        progress_text += f"Добавь ещё {remaining} воспоминания о вашем близком или вашей истории 🧩\n"

                        progress_text += "Эти детали помогут нам сделать песню максимально личной и трогательной."

                    else:

                        progress_text += f"Добавь ещё {remaining} воспоминаний о вашем близком или вашей истории 🧩\n"

                        progress_text += "Эти детали помогут нам сделать песню максимально личной и трогательной."

                    

                    await message.answer(progress_text, parse_mode="HTML")

                    await log_state(message, state)

                    return

            else:

                # Проверяем дубликаты перед добавлением

                existing_facts = [f.strip().lower() for f in facts]

                if text.strip().lower() not in existing_facts:

                    facts.append(text)

                    await state.update_data(song_facts=facts)

                    await message.answer("Воспоминание добавлено ✅")

                else:

                    await message.answer("Это воспоминание было добавлено ранее")

        # Проверяем, не является ли это длинным сообщением с несколькими предложениями

        elif len(text.split('.')) > 2 and len(text) > 100:

            # Возможно, это несколько фактов в одном предложении

            # Разбиваем по запятым или другим разделителям

            parts = text.split(',')

            if len(parts) > 2:

                new_facts = []

                for part in parts:

                    part = part.strip()

                    if part and len(part) > 0:  # Минимальная длина для факта (принимаем любую длину)

                        new_facts.append(part)

                

                if len(new_facts) > 1:

                    # Проверяем дубликаты перед добавлением

                    existing_facts = [f.strip().lower() for f in facts]

                    unique_new_facts = []

                    for fact in new_facts:

                        if fact.strip().lower() not in existing_facts:

                            unique_new_facts.append(fact)

                    

                    if unique_new_facts:

                        facts.extend(unique_new_facts)

                        await state.update_data(song_facts=facts)

                        await message.answer(f"Отлично! Добавлено {len(unique_new_facts)} новых фактов.")

                    else:

                        await message.answer("Эти факты уже были добавлены ранее.")

                else:

                    # Проверяем дубликаты перед добавлением

                    existing_facts = [f.strip().lower() for f in facts]

                    if text.strip().lower() not in existing_facts:

                        facts.append(text)

                        await state.update_data(song_facts=facts)

                        await message.answer("Воспоминание добавлено ✅")

                    else:

                        await message.answer("Это воспоминание было добавлено ранее")

            else:

                # Проверяем дубликаты перед добавлением

                existing_facts = [f.strip().lower() for f in facts]

                if text.strip().lower() not in existing_facts:

                    facts.append(text)

                    await state.update_data(song_facts=facts)

                    await message.answer("Воспоминание добавлено ✅")

                else:

                    await message.answer("Это воспоминание было добавлено ранее")

        else:

            # Обычное сообщение - добавляем как один факт (проверяя дубликаты)

            existing_facts = [f.strip().lower() for f in facts]

            if text.strip().lower() not in existing_facts:

                facts.append(text)

                await state.update_data(song_facts=facts)

                await message.answer("Воспоминание добавлено ✅")

            else:

                await message.answer("Это воспоминание было добавлено ранее")

    

    # Удаляем дублирующиеся факты

    unique_facts = []

    for fact in facts:

        fact_clean = fact.strip().lower()

        # Проверяем дубликаты для всех фактов

        if fact_clean not in [f.strip().lower() for f in unique_facts]:

            unique_facts.append(fact)

    

    await state.update_data(song_facts=unique_facts)

    

    if len(unique_facts) >= 5 and len(unique_facts) < 8:

        # Создаем клавиатуру с кнопками выбора

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="✅ Продолжить", callback_data="continue_with_5_facts")],

            [InlineKeyboardButton(text="➕ Добавить ещё воспоминания", callback_data="add_more_facts")]

        ])

        

        await message.answer(

            f"🎉 Отлично! Вы собрали {len(unique_facts)} воспоминаний.\n\n"

            "Вы можете продолжить с текущим количеством воспоминаний или добавить ещё 1-3 воспоминания для более персонализированной песни.",

            reply_markup=keyboard

        )

        return

    elif len(unique_facts) >= 8:

        # Достигнут максимум фактов - предлагаем продолжить

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="✅ Продолжить с 8 фактами", callback_data="continue_with_5_facts")]

        ])

        

        await message.answer(

            f"🎉 Отлично! Вы собрали максимальное количество воспоминаний ({len(unique_facts)}).\n\n"

            "Теперь мы можем создать максимально персонализированную песню!",

            reply_markup=keyboard

        )

        return

    else:

        remaining = 5 - len(unique_facts)

        

        # Показываем прогресс

        progress_text = f"📊 <b>Прогресс:</b> {len(unique_facts)}/5 воспоминаний собрано\n\n"

        

        if len(unique_facts) > 0:

            progress_text += "<b>Собранные воспоминания:</b>\n"

            for i, fact in enumerate(unique_facts, 1):

                # Обрезаем длинные факты для отображения

                display_fact = fact[:50] + "..." if len(fact) > 50 else fact

                progress_text += f"{i}. {display_fact}\n"

            progress_text += "\n"

        

        if remaining == 1:

            progress_text += f"Добавь ещё {remaining} воспоминание о вашем близком или вашей истории 🧩\n"

            progress_text += "Эти детали помогут нам сделать песню максимально личной и трогательной."

        elif remaining < 5:

            progress_text += f"Добавь ещё {remaining} воспоминания о вашем близком или вашей истории 🧩\n"

            progress_text += "Эти детали помогут нам сделать песню максимально личной и трогательной."

        else:

            progress_text += f"Добавь ещё {remaining} воспоминаний о вашем близком или вашей истории 🧩\n"

            progress_text += "Эти детали помогут нам сделать песню максимально личной и трогательной."

        

        await message.answer(progress_text, parse_mode="HTML")

        await log_state(message, state)



# --- Обработка комментариев к песне ---

@dp.message(StateFilter(SongFinalStates.collecting_feedback))

async def save_song_feedback(message: types.Message, state: FSMContext):

    # Сохраняем комментарии пользователя

    data = await state.get_data()

    feedback = data.get("song_feedback", [])

    feedback.append(message.text)

    await state.update_data(song_feedback=feedback)

    

    await message.answer(

        "✅ Благодарим за подробные комментарии!\n"

        "Наша команда уже работает над правками, чтобы песня зазвучала именно так, как вы мечтали ✨ Обновленная версия будет готова в ближайшее время — обязательно вам сообщим! 💞"

    )

    

    # Отправляем комментарии менеджеру и записываем в историю

    order_id = data.get('order_id')

    await add_outbox_task(

        order_id=order_id,

        user_id=message.from_user.id,

        type_="manager_notification",

        content=f"Заказ #{order_id}: Комментарии пользователя для редактирования песни: {message.text}"

    )

    try:

        from db import add_message_history

        await add_message_history(order_id, sender="user", message=f"Комментарий к черновику: {message.text}")

    except Exception:

        pass

    

    # Обновляем статус заказа

    await update_order_status(order_id, "editing")

    

    # Переходим в состояние ожидания обновленного черновика

    await state.set_state(SongDraftStates.waiting_for_draft)

    await log_state(message, state)



# Обработчик для состояния ожидания демо удален - используется receive_song_demo



# УБРАНО: универсальный обработчик перемещен в конец файла



# Универсальная функция для сохранения сообщений пользователя в историю заказа

async def save_user_message_to_history(message: types.Message, state: FSMContext, context: str = ""):

    """Сохраняет сообщение пользователя в историю заказа"""

    try:

        data = await state.get_data()

        order_id = data.get('order_id')

        

        if order_id and message.text:

            from db import add_message_history, create_or_update_order_notification

            message_text = f"{context}{message.text}" if context else message.text

            await add_message_history(order_id, "user", message_text)

            

            # Создаем или обновляем уведомление для менеджера

            await create_or_update_order_notification(order_id)

            logging.info(f"✅ СОХРАНЕНО: Сообщение пользователя {message.from_user.id} в историю заказа {order_id}: {message_text[:50]}...")

            print(f"🔍 ОТЛАДКА: Сохранено сообщение пользователя в историю заказа {order_id}: {message_text}")

            print(f"🔔 ОТЛАДКА: Создано уведомление для заказа {order_id}")

        elif message.text:

            # Если заказа еще нет, сохраняем сообщение для последующего переноса

            from db import save_early_user_message

            message_text = f"{context}{message.text}" if context else message.text

            await save_early_user_message(message.from_user.id, message_text)

            logging.info(f"📝 СОХРАНЕНО: Раннее сообщение пользователя {message.from_user.id}: {message_text[:50]}...")

            print(f"🔍 ОТЛАДКА: Сохранено раннее сообщение пользователя {message.from_user.id}: {message_text}")

    except Exception as e:

        logging.error(f"❌ Ошибка сохранения сообщения в историю: {e}")

        print(f"❌ Ошибка сохранения сообщения в историю: {e}")



# Универсальная функция для извлечения описания страницы из заголовка

def extract_page_description(caption: str) -> str:

    """Извлекает описание страницы из заголовка сообщения"""

    if not caption:

        return "Страница"

    

    # Пытаемся найти номер страницы в заголовке (например, "Страница 2")

    page_match = re.search(r'Страница\s+(\d+)', caption)

    if page_match:

        page_number = page_match.group(1)

        return f"Страница {page_number}"

    

    # Если не нашли номер, ищем любую строку после иконки до первого \n\n

    lines = caption.split('\n\n')

    if len(lines) > 0:

        first_line = lines[0]

        # Убираем иконки из начала строки

        clean_line = re.sub(r'^[📖📸✅❌]+\s*', '', first_line).strip()

        if clean_line:

            return clean_line

    

    return "Страница"



# Функция для обновления всех сообщений с фотографиями страниц после завершения выбора

async def update_all_page_messages(chat_id: int, state: FSMContext):

    """Обновляет все сообщения с фотографиями страниц после завершения выбора"""

    try:

        data = await state.get_data()

        order_id = data.get('order_id')

        selected_pages = data.get(f"selected_pages_{order_id}", [])

        

        # Получаем все сообщения с фотографиями страниц из базы данных

        # Здесь можно добавить логику для получения всех сообщений с фотографиями страниц

        # и обновления их кнопок

        

        print(f"🔍 ОТЛАДКА: Обновление сообщений с фотографиями страниц для чата {chat_id}")

        print(f"🔍 ОТЛАДКА: Заказ {order_id}, выбранные страницы: {selected_pages}")

        

        # В будущем здесь можно добавить логику для получения всех сообщений с фотографиями страниц

        # из базы данных и обновления их кнопок, чтобы показать, что выбор завершен

        

        # Пока что просто логируем - в реальной реализации нужно будет

        # получить все сообщения с фотографиями страниц и обновить их кнопки

        

    except Exception as e:

        logging.error(f"❌ Ошибка в update_all_page_messages: {e}")



# Обработчик завершения выбора страниц

@dp.callback_query(F.data == "finish_page_selection")

async def finish_page_selection_callback(callback: types.CallbackQuery, state: FSMContext):

    try:

        # Проверяем текущее состояние FSM - если пользователь уже перешел к следующему этапу

        current_state = await state.get_state()

        if current_state and current_state != "BookFinalStates:choosing_pages":

            await callback.answer("❌ Выбор страниц уже завершен! Вы перешли к следующему этапу.")

            return

        

        data = await state.get_data()

        order_id = data.get('order_id')

        selected_pages = data.get(f"selected_pages_{order_id}", [])

        selected_count = len(selected_pages)

        

        # Проверяем, что выбрано ровно 24 страницы

        if selected_count != 24:

            await callback.answer("❌ Сначала выберите ровно 24 страницы, затем завершите выбор.")

            return

        

        await callback.answer()

        

        # Показываем итоговое сообщение

        await callback.message.edit_caption(

            caption=f"🎉 <b>Выбор страниц завершен!</b>\n\n"

                   f"✅ Выбрано страниц: {selected_count}/24\n"

                   f"📚 Ваша книга будет содержать {selected_count} уникальных страниц\n\n"

                   f"Ваш выбор отправлен команде сценаристов для создания уникальной книги!",

            parse_mode="HTML"

        )

        

        # Отмечаем, что выбор страниц завершен для этого заказа

        await state.update_data({f"page_selection_finished_{order_id}": True})

        

        # Обновляем все сообщения с фотографиями страниц

        await update_all_page_messages(callback.message.chat.id, state)

        

        # Переход к выбору оформления первой и последней страницы книги

        await show_first_last_page_selection(callback.message, state)

        

    except Exception as e:

        logging.error(f"❌ Ошибка в finish_page_selection_callback: {e}")

        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

    

    await log_state(callback.message, state)



# Обработчик кнопки "Продолжить создание книги"

@dp.callback_query(F.data == "continue_book_creation")

async def continue_book_creation_callback(callback: types.CallbackQuery, state: FSMContext):

    try:

        # Проверяем текущее состояние FSM - если пользователь уже перешел к следующему этапу

        current_state = await state.get_state()

        if current_state and current_state != "BookFinalStates:choosing_pages":

            await callback.answer("❌ Выбор страниц уже завершен! Вы перешли к следующему этапу.")

            return

        

        data = await state.get_data()

        order_id = data.get('order_id')

        selected_pages = data.get(f"selected_pages_{order_id}", [])

        selected_count = len(selected_pages)

        

        # Проверяем, что выбрано ровно 24 страницы

        if selected_count != 24:

            await callback.answer("❌ Сначала выберите ровно 24 страницы, затем продолжите создание книги.")

            return

        

        await callback.answer("🎉 Переходим к созданию книги!")

        

        # Показываем итоговое сообщение

        await callback.message.edit_text(

            f"🎉 <b>Выбор страниц завершен!</b>\n\n"

            f"✅ Выбрано страниц: {selected_count}/24\n"

            f"📚 Ваша книга будет содержать {selected_count} уникальных страниц\n\n"

            f"Ваш выбор отправлен команде сценаристов для создания уникальной книги!",

            parse_mode="HTML"

        )

        

        # Сохраняем выбранные страницы в базу данных

        if order_id:

            await save_selected_pages(order_id, selected_pages)

            print(f"🔍 ОТЛАДКА: Сохранены выбранные страницы для заказа {order_id}: {selected_pages}")

        

        # Отмечаем, что выбор страниц завершен для этого заказа

        await state.update_data({f"page_selection_finished_{order_id}": True})

        

        # Обновляем все сообщения с фотографиями страниц

        await update_all_page_messages(callback.message.chat.id, state)

        

        # Переход к выбору оформления первой и последней страницы книги

        await show_first_last_page_selection(callback.message, state)

        

    except Exception as e:

        logging.error(f"❌ Ошибка в continue_book_creation_callback: {e}")

        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

    

    await log_state(callback.message, state)





# --- Глава 2.1. Выбор пола пользователя (Песня) ---

@dp.callback_query(F.data.in_(["song_gender_female", "song_gender_male"]))

async def song_gender_chosen(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    gender = "девушка" if callback.data == "song_gender_female" else "парень"

    await state.update_data(song_gender=gender)

    

    # Проверяем, есть ли имя пользователя, и запрашиваем его при необходимости

    data = await state.get_data()

    if not data.get('first_name'):

        await callback.message.edit_text("Поделись, как тебя зовут 💌 Нам важно знать, чтобы обращаться к тебе лично")

        await state.set_state(UserDataStates.waiting_first_name)

        await state.update_data(after_name_input="song_relation")

        await log_state(callback.message, state)

        return

    

    # Если имя есть - переходим к выбору получателя

    await show_song_relation_choice(callback.message, state, gender)



async def show_song_relation_choice(message, state, gender):

    """Показывает выбор получателя для песни (для callback)"""

    # Обновляем заказ с данными пола

    data = await state.get_data()

    order_id = data.get('order_id')

    if order_id:

        # Формируем имя отправителя из first_name

        first_name = data.get('first_name', '')

        sender_name = first_name if first_name and first_name != 'None' else ""

        

        order_data = {

            "product": "Песня",

            "user_gender": gender,

            "song_gender": gender,

            "username": data.get('username'),

            "first_name": data.get('first_name'),

            "last_name": data.get('last_name'),

            "sender_name": sender_name  # Добавляем имя отправителя

        }

        await update_order_data(order_id, order_data)

        await update_order_status(order_id, "gender_selected")

    

    # Переход к выбору получателя

    if gender == "парень":

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="Любимой", callback_data="song_rel_to_man")],

            [InlineKeyboardButton(text="Маме", callback_data="song_rel_to_mom")],

            [InlineKeyboardButton(text="Папе", callback_data="song_rel_to_dad")],

            [InlineKeyboardButton(text="Дочери", callback_data="song_rel_to_daughter")],

            [InlineKeyboardButton(text="Девушке", callback_data="song_rel_to_girlfriend")],

            [InlineKeyboardButton(text="Бабушке", callback_data="song_rel_to_grandma")],

            [InlineKeyboardButton(text="Дедушке", callback_data="song_rel_to_grandpa")],

            [InlineKeyboardButton(text="Сестре", callback_data="song_rel_to_sister")],

            [InlineKeyboardButton(text="Брату", callback_data="song_rel_to_brother")],

            [InlineKeyboardButton(text="Сыну", callback_data="song_rel_to_son")],

        ])

    else:

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="Любимому", callback_data="song_rel_to_man")],

            [InlineKeyboardButton(text="Маме", callback_data="song_rel_to_mom")],

            [InlineKeyboardButton(text="Папе", callback_data="song_rel_to_dad")],

            [InlineKeyboardButton(text="Дочери", callback_data="song_rel_to_daughter")],

            [InlineKeyboardButton(text="Подруге", callback_data="song_rel_to_girlfriend")],

            [InlineKeyboardButton(text="Бабушке", callback_data="song_rel_to_grandma")],

            [InlineKeyboardButton(text="Дедушке", callback_data="song_rel_to_grandpa")],

            [InlineKeyboardButton(text="Сестре", callback_data="song_rel_to_sister")],

            [InlineKeyboardButton(text="Брату", callback_data="song_rel_to_brother")],

            [InlineKeyboardButton(text="Сыну", callback_data="song_rel_to_son")],

        ])

    await message.edit_text("Каждую песню мы делаем с заботой о том, кто её получит 💖\nПодскажи, пожалуйста, для кого мы создаём твою песню:", reply_markup=keyboard)

    await state.set_state(SongRelationStates.choosing_relation)

    await log_state(message, state)



async def show_song_relation_choice_after_name(message, state, gender):

    """Показывает выбор получателя для песни (после ввода имени)"""

    # Обновляем заказ с данными пола

    data = await state.get_data()

    order_id = data.get('order_id')

    if order_id:

        # Формируем имя отправителя из first_name

        first_name = data.get('first_name', '')

        sender_name = first_name if first_name and first_name != 'None' else ""

        

        order_data = {

            "product": "Песня",

            "user_gender": gender,

            "song_gender": gender,

            "username": data.get('username'),

            "first_name": data.get('first_name'),

            "last_name": data.get('last_name'),

            "sender_name": sender_name  # Добавляем имя отправителя

        }

        await update_order_data(order_id, order_data)

        await update_order_status(order_id, "gender_selected")

    

    # Переход к выбору получателя

    if gender == "парень":

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="Любимой", callback_data="song_rel_to_man")],

            [InlineKeyboardButton(text="Маме", callback_data="song_rel_to_mom")],

            [InlineKeyboardButton(text="Папе", callback_data="song_rel_to_dad")],

            [InlineKeyboardButton(text="Дочери", callback_data="song_rel_to_daughter")],

            [InlineKeyboardButton(text="Девушке", callback_data="song_rel_to_girlfriend")],

            [InlineKeyboardButton(text="Бабушке", callback_data="song_rel_to_grandma")],

            [InlineKeyboardButton(text="Дедушке", callback_data="song_rel_to_grandpa")],

            [InlineKeyboardButton(text="Сестре", callback_data="song_rel_to_sister")],

            [InlineKeyboardButton(text="Брату", callback_data="song_rel_to_brother")],

            [InlineKeyboardButton(text="Сыну", callback_data="song_rel_to_son")],

        ])

    else:

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="Любимому", callback_data="song_rel_to_man")],

            [InlineKeyboardButton(text="Маме", callback_data="song_rel_to_mom")],

            [InlineKeyboardButton(text="Папе", callback_data="song_rel_to_dad")],

            [InlineKeyboardButton(text="Дочери", callback_data="song_rel_to_daughter")],

            [InlineKeyboardButton(text="Подруге", callback_data="song_rel_to_girlfriend")],

            [InlineKeyboardButton(text="Бабушке", callback_data="song_rel_to_grandma")],

            [InlineKeyboardButton(text="Дедушке", callback_data="song_rel_to_grandpa")],

            [InlineKeyboardButton(text="Сестре", callback_data="song_rel_to_sister")],

            [InlineKeyboardButton(text="Брату", callback_data="song_rel_to_brother")],

            [InlineKeyboardButton(text="Сыну", callback_data="song_rel_to_son")],

        ])

    await message.answer("Каждую песню мы делаем с заботой о том, кто её получит 💖\nПодскажи, пожалуйста, для кого мы создаём твою песню:", reply_markup=keyboard)

    await state.set_state(SongRelationStates.choosing_relation)

    await log_state(message, state)



# --- Глава 2.2. Выбор получателя и повода (Песня) ---

@dp.callback_query(F.data.startswith("song_rel_to_"))

async def song_relation_chosen(callback: types.CallbackQuery, state: FSMContext):

    # Получаем пол пользователя для правильного маппинга
    data = await state.get_data()
    gender = data.get('song_gender', '')

    relations = {

        "song_rel_to_man": "Любимому",

        "song_rel_to_mom": "Маме",

        "song_rel_to_dad": "Папе",

        "song_rel_to_girlfriend": "Девушке" if gender == "парень" else "Подруге",  # Учитываем пол пользователя

        "song_rel_to_grandma": "Бабушке",

        "song_rel_to_grandpa": "Дедушке",

        "song_rel_to_sister": "Сестре",

        "song_rel_to_brother": "Брату",

        "song_rel_to_son": "Сыну",

        "song_rel_to_daughter": "Дочери",

        "song_rel_to_woman": "Любимой",

        "song_rel_to_boyfriend": "Парню",

    }

    relation = relations.get(callback.data, "Неизвестно")

    # Применяем маппинг с учетом пола для правильного сохранения
    def get_mapped_relation_for_song_save(relation, gender):
        if relation == "Дедушке":
            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Внук - дедушке"
            else:
                return "Внучка - дедушке"
        elif relation == "Бабушке":
            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Внук - бабушке"
            else:
                return "Внучка - бабушке"
        elif relation == "Маме":
            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Сын – маме"
            else:
                return "Дочка- маме"
        elif relation == "Папе":
            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Сын – папе"
            else:
                return "Дочка- папе"
        elif relation == "Сыну":
            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Папа - сыну"
            else:
                return "Мама - сыну"
        elif relation == "Дочке" or relation == "Дочери":
            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Папа - дочке"
            else:
                return "Мама - дочке"
        elif relation == "Брату":
            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Брат - брату"
            else:
                return "Сестра - брату"
        elif relation == "Сестре":
            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Брат – сестре"
            else:
                return "Сестра - сестре"
        elif relation == "Парню":
            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Парень - девушке"
            else:
                return "Девушка - парню"
        elif relation == "Девушке":
            # Учитываем пол пользователя
            if gender == "мальчик" or gender == "парень":
                return "Парень - девушке"
            else:
                return "Девушка - парню"
        elif relation == "Мужу":
            return "Жена - мужу"
        elif relation == "Жене":
            return "Муж - жене"
        else:
            return relation

    # Применяем маппинг с учетом пола
    mapped_relation = get_mapped_relation_for_song_save(relation, gender)
    
    await state.update_data(song_relation=mapped_relation)

    

    # Обновляем заказ с данными получателя

    data = await state.get_data()

    order_id = data.get('order_id')

    if order_id:

        # Формируем имя отправителя из first_name и last_name

        first_name = data.get('first_name', '')

        last_name = data.get('last_name', '')

        sender_name = ""

        if first_name and first_name != 'None':

            sender_name = first_name

        if last_name and last_name != 'None':

            if sender_name:

                sender_name += f" {last_name}"

            else:

                sender_name = last_name

        

        order_data = {

            "product": "Песня",

            "user_gender": data.get('song_gender', ''),

            "song_relation": relation,

            "song_gender": data.get('song_gender', ''),

            "username": data.get('username'),

            "first_name": data.get('first_name'),

            "last_name": data.get('last_name'),

            "sender_name": sender_name  # Добавляем имя отправителя

        }

        await update_order_data(order_id, order_data)

        await update_order_status(order_id, "recipient_selected")

    

    # Запрашиваем имя получателя

    await callback.message.edit_text("Напиши имя того кому будет посвящена твоя песня 🎵\nОно станет главным, и песня прозвучит особенно тепло ❤️")

    await state.set_state(SongRelationStates.waiting_recipient_name)

    logging.info(f"🎵 Установлено состояние waiting_recipient_name для пользователя {callback.from_user.id}")

    await callback.answer()

    await log_state(callback.message, state)



@dp.message(StateFilter(SongRelationStates.waiting_recipient_name))

async def song_recipient_name(message: types.Message, state: FSMContext):

    try:

        logging.info(f"🎵 Обработчик song_recipient_name вызван для пользователя {message.from_user.id}")

        logging.info(f"🎵 Получен текст: '{message.text}'")

        current_state = await state.get_state()

        logging.info(f"🎵 Текущее состояние: {current_state}")

        await state.update_data(song_recipient_name=message.text)

        

        # Сохраняем сообщение пользователя в историю для админки

        await save_user_message_to_history(message, state, "Имя получателя песни: ")

        

        # Обновляем заказ с именем получателя

        data = await state.get_data()

        order_id = data.get('order_id')

        if order_id:

            # Формируем имя отправителя из first_name и last_name

            first_name = data.get('first_name', '')

            last_name = data.get('last_name', '')

            sender_name = ""

            if first_name and first_name != 'None':

                sender_name = first_name

            if last_name and last_name != 'None':

                if sender_name:

                    sender_name += f" {last_name}"

                else:

                    sender_name = last_name

            

            order_data = {

                "product": "Песня",

                "user_gender": data.get('song_gender', ''),

                "song_relation": data.get('song_relation', ''),

                "song_recipient_name": message.text,

                "hero_name": message.text,  # Для админки

                "song_gender": data.get('song_gender', ''),

                "username": data.get('username'),

                "first_name": data.get('first_name'),

                "last_name": data.get('last_name'),

                "sender_name": sender_name  # Добавляем имя отправителя

            }

            await update_order_data(order_id, order_data)

            await update_order_status(order_id, "recipient_name_entered")

        

        # Проверяем тип продукта - отправляем сообщение только для песни
        product = data.get('product', '')
        if product != "Песня":
            logging.info(f"🔍 Пропускаем сообщение о поводе песни для продукта: {product}")
            return

        logging.info(f"🎵 Отправляем сообщение о поводе подарка пользователю {message.from_user.id}")

        try:

            await message.answer("Напиши по какому поводу мы создаём песню 🎶\nИли это просто подарок без повода?")

            logging.info(f"🎵 Сообщение о поводе подарка отправлено успешно")

        except Exception as send_error:

            logging.error(f"❌ Ошибка отправки сообщения о поводе: {send_error}")

            raise send_error

        

        await state.set_state(SongRelationStates.waiting_gift_reason)

        await log_state(message, state)

        logging.info(f"🎵 Состояние изменено на waiting_gift_reason для пользователя {message.from_user.id}")

        

    except Exception as e:

        logging.error(f"❌ Ошибка в song_recipient_name: {e}")

        import traceback

        logging.error(f"❌ Traceback: {traceback.format_exc()}")

        await message.answer("Произошла ошибка. Попробуйте еще раз.")



@dp.message(StateFilter(SongRelationStates.waiting_gift_reason))

async def song_gift_reason(message: types.Message, state: FSMContext):

    print("ФУНКЦИЯ ВЫЗВАНА!")

    # Проверяем текущее состояние - если пользователь уже выбирает стиль, игнорируем
    current_state = await state.get_state()
    if current_state == SongStyleStates.choosing_style:
        logging.info(f"⚠️ Пользователь уже в состоянии выбора стиля, игнорируем сообщение")
        return
    
    # Проверяем, не отправляется ли уже сообщение со стилями
    data = await state.get_data()
    style_message_sending = data.get('style_message_sending', False)
    if style_message_sending:
        logging.info(f"⚠️ Сообщение со стилями уже отправляется, пропускаем дублирование")
        return

    # Устанавливаем флаг сразу, чтобы предотвратить дублирование при быстром вводе
    await state.update_data(style_message_sending=True)
    
    try:
        await state.update_data(song_gift_reason=message.text)

        # Сохраняем сообщение пользователя в историю для админки
        await save_user_message_to_history(message, state, "Повод подарка: ")

        # Обновляем заказ с поводом подарка
        data = await state.get_data()
        order_id = data.get('order_id')

        if order_id:
            # Формируем имя отправителя из first_name и last_name
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')

            sender_name = ""

            if first_name and first_name != 'None':
                sender_name = first_name

            if last_name and last_name != 'None':
                if sender_name:
                    sender_name += f" {last_name}"
                else:
                    sender_name = last_name

            

            order_data = {
                "product": "Песня",
                "user_gender": data.get('song_gender', ''),
                "song_relation": data.get('song_relation', ''),
                "song_recipient_name": data.get('song_recipient_name', ''),
                "hero_name": data.get('song_recipient_name', ''),  # Для админки
                "song_gift_reason": message.text,

                "song_gender": data.get('song_gender', ''),
                "username": data.get('username'),
                "first_name": data.get('first_name'),
                "last_name": data.get('last_name'),
                "sender_name": sender_name  # Добавляем имя отправителя
            }

            await update_order_data(order_id, order_data)
            await update_order_status(order_id, "gift_reason_entered")

            # Автоматический выбор голоса на основе пола клиента
            await update_order_status(order_id, "voice_selection")

            # Получаем пол клиента
            user_gender = data.get('song_gender', '')

            # Получаем доступные голоса из базы данных
            voices = await get_voice_styles()

            if voices:
                # Фильтруем голоса по полу клиента
                matching_voices = []

                for voice in voices:
                    voice_gender = voice.get('gender', 'male').lower()

                    if user_gender == "девушка" and voice_gender in ['female', 'женский']:
                        matching_voices.append(voice)
                    elif user_gender == "парень" and voice_gender in ['male', 'мужской']:
                        matching_voices.append(voice)

                # Если нет подходящих голосов, берем первый доступный
                if not matching_voices:
                    matching_voices = [voices[0]]

                # Проверяем, не отправлялись ли уже примеры голосов
                song_style = data.get('song_style')
                if not song_style:
                    # Отправляем 3 примера голосов с разными эмоциональными окрасками
                    # Используем общую функцию для отправки примеров голосов
                    await send_voice_examples(message, data.get('song_gender', 'парень'))
                else:
                    logging.info(f"🎵 Стиль уже выбран, пропускаем отправку примеров голосов для пользователя {message.from_user.id}")

                # Автоматически выбираем первый подходящий голос
                selected_voice = matching_voices[0]

                # Сохраняем выбранный голос в состояние
                await state.update_data(
                    song_voice=selected_voice['name'], 
                    song_voice_gender=selected_voice.get('gender', 'male')
                )

                # Обновляем данные заказа с выбранным голосом
                order_data.update({
                    "song_voice": selected_voice['name'],
                    "song_voice_gender": selected_voice.get('gender', 'male')
                })

                await update_order_data(order_id, order_data)

            # Переходим к выбору стиля песни
            # Проверяем, не отправлялось ли уже сообщение со стилями
            from db import get_order
            order_info = await get_order(order_id)
            song_style_message_sent = order_info.get('song_style_message_sent', 0) if order_info else 0
            
            # Дополнительная проверка в состоянии FSM
            current_state = await state.get_state()
            if current_state == SongStyleStates.choosing_style:
                logging.info(f"⚠️ Пользователь уже в состоянии выбора стиля, пропускаем отправку сообщения")
                return
            
            if not song_style_message_sent:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Нежная и романтичная песня ❤️‍🔥", callback_data="song_style_gentle")],
                    [InlineKeyboardButton(text="Весёлый и жизнерадостный трек🎉", callback_data="song_style_bright")],
                    [InlineKeyboardButton(text="Глубокая и лиричная мелодия 💓", callback_data="song_style_artist")],
                ])

                await message.answer("Выбери стиль песни: 🤗", reply_markup=keyboard)

                # Сначала меняем состояние, чтобы предотвратить повторные вызовы
                await state.set_state(SongStyleStates.choosing_style)

                # Затем отмечаем, что сообщение со стилями было отправлено
                await update_order_data(order_id, {'song_style_message_sent': 1})
                
                logging.info(f"✅ Сообщение со стилями песен отправлено для заказа {order_id}")
            else:
                # Если сообщение уже отправлялось, просто меняем состояние
                await state.set_state(SongStyleStates.choosing_style)

    
    except Exception as e:
        logging.error(f"❌ Ошибка в song_gift_reason: {e}")
    finally:
        # Сбрасываем флаг в конце функции (даже если произошла ошибка)
        await state.update_data(style_message_sending=False)

    await log_state(message, state)



# --- Глава 2.3. Выбор стиля песни ---

@dp.callback_query(F.data.startswith("song_style_"))

async def song_style_chosen(callback: types.CallbackQuery, state: FSMContext):

    styles = {

        "song_style_gentle": "Нежная и романтичная песня ❤️‍🔥",

        "song_style_bright": "Весёлый и жизнерадостный трек🎉",

        "song_style_artist": "Глубокая и лиричная мелодия 💓",

    }

    style = styles.get(callback.data, "Глубокая и лиричная мелодия 💓")

    await state.update_data(song_style=style)

    

    # Обновляем заказ с данными стиля

    data = await state.get_data()

    order_id = data.get('order_id')

    user_id = callback.from_user.id

    

    if order_id:

        # Формируем имя отправителя из first_name и last_name

        first_name = data.get('first_name', '')

        last_name = data.get('last_name', '')

        sender_name = ""

        if first_name and first_name != 'None':

            sender_name = first_name

        if last_name and last_name != 'None':

            if sender_name:

                sender_name += f" {last_name}"

            else:

                sender_name = last_name

        

        # У нас уже есть order_id в состоянии - обновляем этот заказ

        order_data = {

            "product": "Песня",

            "user_gender": data.get('song_gender', ''),

            "song_relation": data.get('song_relation', ''),

            "song_recipient_name": data.get('song_recipient_name', ''),

            "hero_name": data.get('song_recipient_name', ''),  # Для админки

            "song_style": style,

            "style": style,  # Для админки

            "song_gift_reason": data.get('song_gift_reason', ''),

            "song_gender": data.get('song_gender', ''),

            "relation": data.get('song_relation', ''),  # Дополнительно для админки

            "gift_reason": data.get('song_gift_reason', ''),  # Дополнительно для админки

            "song_voice": data.get('song_voice', ''),  # Добавляем выбранный голос

            "song_voice_gender": data.get('song_voice_gender', ''),  # Добавляем пол голоса

            "username": data.get('username'),

            "first_name": data.get('first_name'),

            "last_name": data.get('last_name'),

            "sender_name": sender_name  # Добавляем имя отправителя

        }

        print(f"🔍 ОТЛАДКА: Сохраняем данные для заказа {order_id}:")

        print(f"📊 Данные: {order_data}")

        await update_order_data(order_id, order_data)

        print(f"✅ Данные сохранены для заказа {order_id}")

        

        # Проверяем что данные действительно сохранились

        from db import get_order_data_debug

        saved_data = await get_order_data_debug(order_id)

        print(f"🔍 ПРОВЕРКА: Данные в БД после сохранения: {saved_data}")

        

        # Проверяем ключевые поля

        required_fields = ['hero_name', 'style', 'relation', 'gift_reason']

        missing_fields = [field for field in required_fields if not saved_data.get(field)]

        if missing_fields:

            print(f"⚠️ ВНИМАНИЕ: Отсутствуют поля в БД: {missing_fields}")

        else:

            print(f"✅ Все ключевые поля присутствуют в БД")

    else:

        # Формируем имя отправителя из first_name и last_name

        first_name = data.get('first_name', '')

        last_name = data.get('last_name', '')

        sender_name = ""

        if first_name and first_name != 'None':

            sender_name = first_name

        if last_name and last_name != 'None':

            if sender_name:

                sender_name += f" {last_name}"

            else:

                sender_name = last_name

        

        # Создаем новый заказ только если нет существующего (включая данные для админки)

        order_data = {

            "product": "Песня",

            "user_id": data.get('user_id'),

            "username": data.get('username'),

            "first_name": data.get('first_name'),

            "last_name": data.get('last_name'),

            "sender_name": sender_name,  # Добавляем имя отправителя

            "song_gender": data.get('song_gender'),

            "song_relation": data.get('song_relation'),

            "song_recipient_name": data.get('song_recipient_name'),

            "song_gift_reason": data.get('song_gift_reason'),

            "song_style": style,

            "song_voice": data.get('song_voice', ''),  # Добавляем выбранный голос

            "song_voice_gender": data.get('song_voice_gender', ''),  # Добавляем пол голоса

            "hero_name": data.get('song_recipient_name', ''),  # Для админки

            "style": style,  # Для админки

            "relation": data.get('song_relation', ''),  # Дополнительно для админки

            "gift_reason": data.get('song_gift_reason', '')  # Дополнительно для админки

        }

        

        print(f"🔍 ОТЛАДКА: Создаем новый заказ для пользователя {user_id}:")

        print(f"📊 Данные нового заказа: {order_data}")

        order_id = await create_order(user_id, order_data)

        await state.update_data(order_id=order_id)

        print(f"✅ Новый заказ создан с ID {order_id}")

    

    # --- Переход к демо-контенту ---

    await update_order_status(order_id, "demo_content")

    

    # Получаем информацию о выбранном голосе

    selected_voice = data.get('song_voice', 'Не указан')

    

    await callback.message.edit_text(f"✅ Выбран стиль: {style}")

    

    await callback.message.answer(

        f"Спасибо за доверие!☺️\n\n"

        f"Мы уже начали собирать демо-версию, скоро мы вернемся и ты услышишь первые ноты 🎶"

    )

    

    # Переходим в состояние ожидания демо

    await state.set_state(SongDraftStates.waiting_for_demo)

    # Создаем таймер для этапа waiting_demo_song (Глава 2: Демо-песня)
    from db import create_or_update_user_timer
    await create_or_update_user_timer(callback.from_user.id, order_id, "waiting_demo_song", "Песня")
    logging.info(f"✅ Создан таймер для этапа waiting_demo_song (Глава 2), пользователь {callback.from_user.id}, заказ {order_id}")

    await callback.answer()

    await log_state(callback.message, state)


# Обработчик сообщений в состоянии выбора стиля песни
@dp.message(StateFilter(SongStyleStates.choosing_style), F.text)
async def handle_text_in_song_style_selection(message: types.Message, state: FSMContext):
    """Обрабатывает текстовые сообщения при выборе стиля песни"""
    
    print(f"🔍 ОТЛАДКА: Получено текстовое сообщение в состоянии SongStyleStates.choosing_style: '{message.text}' от пользователя {message.from_user.id}")
    
    # Сохраняем сообщение пользователя в историю заказа
    await save_user_message_to_history(message, state, "Сообщение при выборе стиля песни: ")
    
    # Проверяем текущее состояние FSM - если пользователь уже перешел к следующему этапу
    current_state = await state.get_state()
    
    if current_state and current_state != "SongStyleStates:choosing_style":
        await message.answer("❌ Выбор стиля уже завершен! Вы перешли к следующему этапу.")
        return
    
    # Пользователь отвечает администратору - сообщение уже сохранено в историю заказа
    # Не отправляем подтверждение пользователю
    
    await log_state(message, state)


# Обработчик выбора голоса для песни (оставлен для совместимости, но больше не используется)

@dp.callback_query(F.data.startswith("song_voice_"))

async def song_voice_chosen(callback: types.CallbackQuery, state: FSMContext):

    # Голос теперь выбирается автоматически на основе пола клиента

    await callback.answer("🎤 Голос уже выбран автоматически на основе вашего пола!")



# УБРАНО: обработчик перемещен перед универсальным обработчиком



@dp.message(StateFilter(SongQuizStates.quiz_q2))

async def song_quiz_q2(message: types.Message, state: FSMContext):

    await state.update_data(song_quiz_special=message.text)

    await message.answer("Какой момент из вашей жизни с этим человеком вы вспоминаете чаще всего?")

    await state.set_state(SongQuizStates.quiz_q3)

    await log_state(message, state)



@dp.message(StateFilter(SongQuizStates.quiz_q3))

async def song_quiz_q3(message: types.Message, state: FSMContext):

    await state.update_data(song_quiz_memory=message.text)

    

    # Переходим к сбору дополнительных фактов

    data = await state.get_data()

    relation = data.get("song_relation", "получателя")

    # Получаем пол создателя песни для правильного выбора вопросов
    song_gender = data.get("song_gender", "парень")
    
    # Получаем имена для замены
    sender_name = data.get("first_name", "") or data.get("username", "пользователь")
    recipient_name = data.get("song_recipient_name", "получатель")
    
    # Получаем динамические вопросы в зависимости от типа связи
    song_questions = await get_song_questions_for_relation(relation, song_gender)
    
    # Формируем текст точно как в админ-панели
    intro_text = ""
    
    for question in song_questions:
        # Заменяем имена в тексте
        question_with_names = question.replace("(имя)", sender_name)
        question_with_names = question_with_names.replace("(имя)", recipient_name)
        
        # Добавляем строку как есть (включая пустые строки для абзацев)
        intro_text += f"{question_with_names}\n"
    
    await message.answer(intro_text, parse_mode="HTML")

    await state.set_state(SongFactsStates.collecting_facts)

    await log_state(message, state)



# --- Глава 2.5. Демо-версия песни ---

@dp.message(StateFilter(SongDraftStates.waiting_for_demo))

async def receive_song_demo(message: types.Message, state: FSMContext):

    # Проверяем, что это сообщение от менеджера, а не от пользователя

    if message.from_user.id not in ADMIN_IDS:

        # Это сообщение от пользователя - сохраняем в историю заказа

        data = await state.get_data()

        order_id = data.get('order_id')

        

        if order_id:

            try:

                from db import add_message_history

                await add_message_history(order_id, "user", message.text or f"[{message.content_type.upper()}] Сообщение от пользователя")

                

                # Создаем или обновляем уведомление для менеджера

                from db import create_or_update_order_notification

                await create_or_update_order_notification(order_id)

                print(f"🔍 ОТЛАДКА: Сохранено сообщение пользователя в состоянии waiting_for_demo для заказа {order_id}: {message.text}")

                print(f"🔔 ОТЛАДКА: Создано уведомление для заказа {order_id}")

            except Exception as e:

                logging.error(f"❌ Ошибка сохранения сообщения в историю: {e}")

        

        logging.info(f"🎵 Игнорируем сообщение от пользователя {message.from_user.id} в состоянии waiting_for_demo")

        return

    

    # Менеджер отправляет демо-версию песни

    data = await state.get_data()

    order_id = data.get('order_id')

    

    logging.info(f"🎵 Менеджер отправляет демо песни для заказа {order_id}")

    

    # Сохраняем демо-аудио

    await state.update_data(song_demo=message.text)

    await update_order_status(order_id, "demo_sent")
    
    # Импортируем все необходимые функции
    from db import get_order, get_active_timers_for_order, deactivate_user_timers, create_or_update_user_timer, get_message_templates
    
    # Получаем user_id из заказа
    order = await get_order(order_id)
    if not order:
        logging.error(f"❌ Заказ {order_id} не найден")
        return
    
    user_id = order.get('user_id')
    if not user_id:
        logging.error(f"❌ user_id не найден в заказе {order_id}")
        return
    
    # Проверяем текущие активные таймеры ДО деактивации
    active_timers_before = await get_active_timers_for_order(order_id)
    logging.info(f"🔍 Активные таймеры ДО деактивации: {active_timers_before}")
    
    # Таймер создается автоматически в update_order_status при изменении статуса на demo_sent
    
    # Проверяем, есть ли шаблоны для demo_received_song
    templates = await get_message_templates()
    demo_templates = [t for t in templates if t.get('order_step') == 'demo_received_song']
    logging.info(f"🔍 Найдено {len(demo_templates)} шаблонов для demo_received_song: {[t.get('message_type') for t in demo_templates]}")
    
    # Проверяем, есть ли активные шаблоны для waiting_demo_song (которые могут мешать)
    waiting_templates = [t for t in templates if t.get('order_step') == 'waiting_demo_song']
    logging.info(f"🔍 Найдено {len(waiting_templates)} шаблонов для waiting_demo_song: {[t.get('message_type') for t in waiting_templates]}")

    

    # Показываем демо-версию пользователю

    await message.answer(

        "Спасибо за ожидание ✨\n"

        "Демо-версия твоей песни готова 💌\n"

        "Мы собрали её первые ноты с теплом и уже знаем, как превратить их в полную мелодию, которая тронет до мурашек.\n\n"

        "Чтобы создать по-настоящему авторскую историю с твоими деталями, моментами и чувствами, нам нужно чуть больше информации 🧩\n\n"

        "Твоя история достойна того, чтобы зазвучать полностью и стать запоминающимся подарком для тебя и получателя ❤️‍🔥"

    )
    
    # Создаем таймер для этапа demo_received_song после отправки сообщения
    from db import create_or_update_user_timer, deactivate_user_timers
    await deactivate_user_timers(user_id, order_id)
    await create_or_update_user_timer(user_id, order_id, "demo_received_song", "Песня")
    logging.info(f"✅ Создан таймер для этапа demo_received_song после отправки сообщения, пользователь {user_id}, заказ {order_id}")

    

    # Кнопка для продолжения

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="Узнать цену", callback_data="continue_after_song_demo")]

    ])

    

    logging.info(f"🔘 Создаю кнопку 'Узнать цену' с callback_data='continue_after_song_demo'")

    logging.info(f"🔘 Структура клавиатуры: {keyboard.inline_keyboard}")

    

    await message.answer("Жми \"Узнать цену\", и я расскажу, как мы можем дописать песню.", reply_markup=keyboard)

    

    # Переходим в состояние ожидания оплаты

    await state.set_state(SongDraftStates.demo_received)

    await log_state(message, state)



# --- Обработка кнопки "Узнать цену" после демо ---

@dp.callback_query(F.data == "continue_after_song_demo")

async def after_song_demo_continue(callback: types.CallbackQuery, state: FSMContext):

    logging.info(f"🔘 Кнопка 'Узнать цену' нажата! User ID: {callback.from_user.id}")

    logging.info(f"🔘 Callback data: {callback.data}")

    logging.info(f"🔘 Current state: {await state.get_state()}")

    

    try:

        data = await state.get_data()

        order_id = data.get('order_id')

        

        # Глава 2.6. Оплата заказа песни

        # Получаем цену для песни

        price = await get_product_price_async("Песня", "💌 Персональная песня")

        

        # Создаем платеж

        description = f"Песня - заказ #{order_id}" if order_id else "Песня"

        payment_data = await create_payment(order_id, price, description, "Песня")

        

        # Сохраняем данные платежа

        await state.update_data(

            payment_id=payment_data['payment_id'],

            payment_url=payment_data['confirmation_url'],

            product="Песня"

        )

        

        # Формируем сводку заказа

        order_summary = ""

        

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="Заказать песню", url=payment_data['confirmation_url'])],

            [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="check_payment")],


        ])

        

        await safe_edit_message(

            callback.message,

            f"{order_summary}\n"

            f"💳 <b>Оплата:</b>\n"

            f"Стоимость: <b>{price} ₽</b>\n\n"

            f"Для завершения заказа нажмите кнопку оплаты ниже:",

            reply_markup=keyboard,

            parse_mode="HTML"

        )

        

        # Обновляем статус заказа

        await update_order_status(order_id, "waiting_payment")

        

        # Создаем отложенные напоминания об оплате через 24 и 48 часов

        from db import create_payment_reminder_messages

        await create_payment_reminder_messages(order_id, callback.from_user.id)

        

        await callback.answer()

        await log_state(callback.message, state)

        

    except Exception as e:

        logging.error(f"❌ Ошибка в after_song_demo_continue: {e}")

        await callback.answer("Произошла ошибка. Попробуйте еще раз.")



@dp.callback_query(F.data == "listen_song")

async def listen_song_callback(callback: types.CallbackQuery, state: FSMContext):

    logging.info(f"🔘 Кнопка 'listen_song' нажата! User ID: {callback.from_user.id}")

    logging.info(f"🔘 Callback data: {callback.data}")

    logging.info(f"🔘 Current state: {await state.get_state()}")

    

    try:

        data = await state.get_data()

        order_id = data.get('order_id')

        

        # Глава 2.6. Оплата заказа песни

        # Получаем цену для песни

        price = await get_product_price_async("Песня", "💌 Персональная песня")

        

        # Создаем платеж

        description = f"Песня - заказ #{order_id}" if order_id else "Песня"

        payment_data = await create_payment(order_id, price, description, "Песня")

        

        # Сохраняем данные платежа

        await state.update_data(

            payment_id=payment_data['payment_id'],

            payment_url=payment_data['confirmation_url'],

            product="Песня"

        )

        

        # Формируем сводку заказа

        order_summary = ""

        

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="Заказать песню", url=payment_data['confirmation_url'])],

            [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="check_payment")],


        ])

        

        await safe_edit_message(

            callback.message,

            f"{order_summary}\n"

            f"💳 <b>Оплата:</b>\n"

            f"Стоимость: <b>{price} ₽</b>\n\n"

            f"Для завершения заказа нажмите кнопку оплаты ниже:",

            reply_markup=keyboard,

            parse_mode="HTML"

        )

        

        # Обновляем статус заказа

        await update_order_status(order_id, "waiting_payment")

        

        # Создаем отложенные напоминания об оплате через 24 и 48 часов

        from db import create_payment_reminder_messages

        await create_payment_reminder_messages(order_id, callback.from_user.id)

        

        await callback.answer()

        await log_state(callback.message, state)

        

    except Exception as e:

        logging.error(f"❌ Ошибка в listen_song_callback: {e}")

        await callback.answer("Произошла ошибка. Попробуйте еще раз.")



# --- Обработка сообщений пользователя после демо ---

@dp.message(StateFilter(SongDraftStates.demo_received))

async def handle_user_message_after_demo(message: types.Message, state: FSMContext):

    """Обрабатывает сообщения пользователя после получения демо"""

    # Сохраняем сообщение пользователя в историю заказа

    data = await state.get_data()

    order_id = data.get('order_id')

    

    if order_id:

        try:

            from db import add_message_history

            await add_message_history(order_id, "user", message.text or f"[{message.content_type.upper()}] Сообщение от пользователя")

            

            # Создаем или обновляем уведомление для менеджера

            from db import create_or_update_order_notification

            await create_or_update_order_notification(order_id)

            print(f"🔍 ОТЛАДКА: Сохранено сообщение пользователя в состоянии demo_received для заказа {order_id}: {message.text}")

            print(f"🔔 ОТЛАДКА: Создано уведомление для заказа {order_id}")

        except Exception as e:

            logging.error(f"❌ Ошибка сохранения сообщения в историю: {e}")

    

    logging.info(f"🎵 Сообщение от пользователя {message.from_user.id} в состоянии demo_received сохранено в историю")



# --- Глава 2.6. Пробная версия песни (после оплаты) ---

@dp.message(StateFilter(SongDraftStates.waiting_for_draft))

async def receive_song_draft(message: types.Message, state: FSMContext):

    # Проверяем, что это сообщение от менеджера, а не от пользователя

    # Если это сообщение от пользователя, игнорируем его

    data = await state.get_data()

    order_id = data.get('order_id')

    

    if order_id:

        order = await get_order(order_id)

        if order and order.get('user_id') == message.from_user.id:

            # Это сообщение от пользователя, а не от менеджера

            # Сохраняем сообщение в историю заказа, но не перекидываем пользователя

            try:

                from db import add_message_history

                await add_message_history(order_id, "user", message.text)

                logging.info(f"💬 Сообщение пользователя {message.from_user.id} сохранено в историю заказа {order_id}: {message.text[:50]}...")

            except Exception as e:

                logging.error(f"❌ Ошибка сохранения сообщения в историю: {e}")

            

            logging.info(f"🎵 Игнорируем сообщение от пользователя {message.from_user.id} в состоянии waiting_for_draft")

            return

    

    # Менеджер отправляет черновик песни (Глава 2.10. Предфинальная версия песни)

    logging.info(f"🎵 Получен черновик песни от менеджера для пользователя {message.from_user.id}")

    

    logging.info(f"📋 Данные заказа: order_id={order_id}")

    

    await state.update_data(song_draft=message.text)

    await update_order_status(order_id, "draft_sent")

    

    # Показываем черновик пользователю

    await message.answer("🎉 Вот она - финальная версия твоей песни ❤️\n\n"

                        "Мы вложили в эту песню много любви и переживаем не меньше тебя. Надеемся, она тронет до мурашек 🥹")

    

    # Кнопки для подтверждения или редактирования

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="Все нравится, отличная песня", callback_data="song_draft_ok")],

        [InlineKeyboardButton(text="Обратная связь", callback_data="song_draft_edit")]

    ])

    

    logging.info("🔘 Отправляю кнопки для черновика песни")

    

    await message.answer("🎉 Вот она - финальная версия твоей песни ❤️\n\n"

                        "Мы вложили в эту песню много любви и переживаем не меньше тебя. Надеемся, она тронет до мурашек 🥹", reply_markup=keyboard)

    await state.set_state(SongDraftStates.draft_received)

    await log_state(message, state)



# --- Обработка подтверждения черновика песни ---

@dp.callback_query(F.data == "song_draft_ok")

async def song_draft_ok_callback(callback: types.CallbackQuery, state: FSMContext):

    data = await state.get_data()

    order_id = data.get('order_id')

    

    # Пользователь одобрил черновик - этот же трек становится финальной версией

    try:

        from db import add_message_history

        await add_message_history(order_id, sender="user", message="Пользователь нажал 'Всё супер' - черновик одобрен")

    except Exception:

        pass

    

    await callback.message.answer("🎉 Отлично! Твоя песня готова!\n\nЭтот трек становится финальной версией твоей песни. Надеемся, она вызовет сильные эмоции! 💖")

    

    # Обновляем статус заказа на "ready" - песня готова

    await update_order_status(order_id, "ready")

    

    # Отправляем прогревочные сообщения для книги сразу

    await callback.message.answer("Спасибо, что доверили нам создание такого важного подарка 💝")

    

    # Отправляем предложение с кнопками

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="Создать пробную книгу", callback_data="create_book_after_song")],

        [InlineKeyboardButton(text="Вернусь к вам чуть позже ❤️", callback_data="finish_song_order")]

    ])

    

    await callback.message.answer(

        "Давай соберём ещё больше воспоминаний в книге со словами, моментами и фотографиями.\n\n"

        "🗝 Уникальность этой книги заключается в том, что мы оживим то, что не успело попасть на фото: особенные ситуации в вашей жизни, важные слова, сказанные шёпотом, и чувства, которые мы бережем.\n\n"

        "Это сокровенный подарок, где оживут самые дорогие мгновения ✨\n"

        "Хочешь попробовать бесплатно?",

        reply_markup=keyboard

    )

    

    # Обновляем состояние пользователя

    await state.set_state(SongFinalStates.final_received)

    

    await callback.answer()

    await log_state(callback.message, state)


# Обработчик сообщений в состоянии final_received (после одобрения черновика песни)
@dp.message(StateFilter(SongFinalStates.final_received), F.text)
async def handle_text_after_song_approval(message: types.Message, state: FSMContext):
    """Обрабатывает текстовые сообщения после одобрения черновика песни"""
    
    print(f"🔍 ОТЛАДКА: Получено текстовое сообщение в состоянии SongFinalStates.final_received: '{message.text}' от пользователя {message.from_user.id}")
    
    # Сохраняем сообщение пользователя в историю заказа
    await save_user_message_to_history(message, state, "Сообщение после одобрения песни: ")
    
    # Проверяем текущее состояние FSM - если пользователь уже перешел к следующему этапу
    current_state = await state.get_state()
    
    if current_state and current_state != "SongFinalStates:final_received":
        await message.answer("❌ Песня уже завершена! Вы перешли к следующему этапу.")
        return
    
    # Пользователь отвечает администратору - сообщение уже сохранено в историю заказа
    # Не отправляем подтверждение пользователю
    
    await log_state(message, state)


# --- Обработчики для кнопок после завершения песни ---

@dp.callback_query(F.data == "create_book_after_song")

async def create_book_after_song_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    # НЕ очищаем состояние полностью - сохраняем данные пользователя!
    # Сохраняем критически важные данные перед частичной очисткой
    data = await state.get_data()
    preserved_data = {
        'user_id': data.get('user_id'),
        'username': data.get('username'), 
        'first_name': data.get('first_name'),
        'last_name': data.get('last_name'),
        'recipient_name': data.get('song_recipient_name'),  # ВАЖНО: сохраняем имя получателя из песни
    }
    
    # Очищаем только песенные данные, сохраняя пользовательские
    await state.clear()
    await state.update_data(**preserved_data)
    logging.info(f"💾 СОХРАНЕНЫ данные при переходе к книге: {preserved_data}")

    # Создаем новый заказ для книги

    user_id = callback.from_user.id

    

    # Получаем данные пользователя из предыдущего заказа песни

    from db import get_user_active_order, get_last_order_username

    previous_order = await get_user_active_order(user_id, "Песня")

    last_username = await get_last_order_username(user_id)

    

    # Извлекаем данные пользователя из предыдущего заказа

    # first_name и last_name НЕ подтягиваем автоматически из Telegram

    user_first_name = None

    user_last_name = None

    

    if previous_order and previous_order.get('order_data'):

        try:

            import json

            order_data = json.loads(previous_order.get('order_data', '{}')) if previous_order and isinstance(previous_order.get('order_data'), str) else (previous_order.get('order_data', {}) if previous_order else {})

            user_first_name = order_data.get('first_name', user_first_name)

            user_last_name = order_data.get('last_name', user_last_name)

        except:

            pass

    

    # Данные уже установлены выше при сохранении, но обновляем если нужно
    current_data = await state.get_data()
    if not current_data.get('first_name'):
        await state.update_data(
            first_name=user_first_name,
            last_name=user_last_name
        )
        logging.info(f"💾 ОБНОВЛЕНЫ имена пользователя: first_name='{user_first_name}', last_name='{user_last_name}'")

    

    # Используем новую функцию с проверкой имени

    await start_book_creation_flow(callback, state)

    

    await log_state(callback.message, state)



@dp.callback_query(F.data == "finish_song_order")

async def finish_song_order_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    # Завершаем работу с пользователем

    await callback.message.edit_text(

        "Спасибо, что выбрал именно нас для создания своего сокровенного подарка💝\n\n"

        "Когда захочешь снова подарить эмоции и тронуть сердце близкого человека — возвращайся 🫶🏻\n\n"

        "Мы будем здесь для тебя,\n"

        "Команда \"В самое сердце\" 💖"

    )

    

    # Очищаем состояние

    await state.clear()

    

    await log_state(callback.message, state)



# --- Обработка запроса на редактирование черновика песни ---

@dp.callback_query(F.data == "song_draft_edit")

async def song_draft_edit_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.message.answer("Поделись, пожалуйста, что именно хочешь изменить в песне? ✨\n"

                                 "Укажи конкретно: в каком куплете, какое слово или строчку нужно заменить — так мы сможем внести правки максимально точно 💕")

    # Сохраняем в историю сообщений для админки, что пользователь перешел к правкам

    try:

        data = await state.get_data()

        order_id = data.get('order_id')

        from db import add_message_history

        await add_message_history(order_id, sender="user", message="Пользователь нажал 'Обратная связь' и отправит комментарии")

    except Exception:

        pass

    await state.set_state(SongFinalStates.collecting_feedback)

    await callback.answer()

    await log_state(callback.message, state)



# --- Обработка подтверждения черновика книги ---

@dp.callback_query(F.data == "book_draft_ok")

async def book_draft_ok_callback(callback: types.CallbackQuery, state: FSMContext):

    logging.info(f"🎯 Обработчик book_draft_ok вызван! User ID: {callback.from_user.id}")

    

    data = await state.get_data()

    order_id = data.get('order_id')

    format_choice = data.get('format', '')

    logging.info(f"📋 Order ID: {order_id}, Format: {format_choice}")

    

    # Пользователь одобрил черновик - переходим к Главе 15 (доставка)

    try:

        from db import add_message_history

        await add_message_history(order_id, sender="user", message="Пользователь нажал 'Всё супер' - черновик одобрен")

        logging.info(f"✅ История сообщений обновлена")

    except Exception as e:

        logging.error(f"❌ Ошибка обновления истории: {e}")

    

    # Обновляем статус заказа на "ready" - книга готова к доставке

    logging.info(f"📋 Обновляю статус заказа {order_id} на 'ready'")

    await update_order_status(order_id, "ready")

    

    # Проверяем изначальный выбор формата

    if format_choice == "📦 Печатная версия":

        # Если изначально выбрана печатная версия - сразу переходим к сбору данных для доставки

        logging.info(f"📦 Пользователь изначально выбрал печатную версию, переходим к сбору данных для доставки")

        

        await callback.message.answer(

            "📦 <b>Печатная версия выбрана!</b>\n\n"

            "Для доставки печатной книги нам нужны ваши данные. "

            "Пожалуйста, введите адрес доставки, например, 455000, Республика Татарстан, г. Казань, ул. Ленина, д. 52, кв. 43",

            parse_mode="HTML"

        )

        

        await state.set_state(DeliveryStates.waiting_for_address)

        

    else:

        # Если изначально выбрана электронная версия - используем новую логику

        logging.info(f"📤 Отправляю сообщение о готовности книги...")

        

        # Обновляем статус заказа на "waiting_final" для электронной версии

        await update_order_status(order_id, "waiting_final")

        logging.info(f"📚 Статус заказа {order_id} изменен на 'waiting_final' для электронной версии")

        

        await callback.message.answer(

            "🎉 <b>Ваша книга готова! Спасибо, что выбрали нас ❤️</b>\n\n"

            "Мы подготовили для вас электронную версию (PDF). "

            "Ссылка для скачивания будет отправлена в ближайшее время!",

            parse_mode="HTML"

        )

        

        # Предложение печатной версии с кнопками

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="📦 Получить печатную версию", callback_data="upsell_print")],

            [InlineKeyboardButton(text="📄 Продолжить с электронной", callback_data="continue_electronic")]

        ])

        

        await callback.message.answer(

            "Хотите получить также печатную версию вашей книги?",

            reply_markup=keyboard,

            parse_mode="HTML"

        )

    

    logging.info(f"✅ Обработчик book_draft_ok завершен успешно")

    await callback.answer()

    await log_state(callback.message, state)



# --- Обработка запроса на редактирование черновика книги ---

@dp.callback_query(F.data == "book_draft_edit")

async def book_draft_edit_callback(callback: types.CallbackQuery, state: FSMContext):

    logging.info(f"🎯 Обработчик book_draft_edit вызван! User ID: {callback.from_user.id}")

    

    await callback.message.answer("Опиши подробно, что именно нужно изменить в книге. \nПример: укажи страницу, и что нам необходимо изменить.")

    

    # Сохраняем в историю сообщений для админки, что пользователь перешел к правкам

    try:

        data = await state.get_data()

        order_id = data.get('order_id')

        from db import add_message_history

        await add_message_history(order_id, sender="user", message="Пользователь нажал 'Обратная связь' и отправит комментарии")

        logging.info(f"✅ История сообщений обновлена для заказа {order_id}")

    except Exception as e:

        logging.error(f"❌ Ошибка обновления истории: {e}")

    

    logging.info(f"🔄 Устанавливаю состояние EditBookStates.adding_comments")

    await state.set_state(EditBookStates.adding_comments)

    await callback.answer()

    await log_state(callback.message, state)



# --- Тестовые обработчики оплаты ---





# --- Глава 2.7. Создание платежа для песни ---

@dp.callback_query(F.data == "song_pay_2990")

async def song_pay_link(callback: types.CallbackQuery, state: FSMContext):

    logging.info(f"🔘 Кнопка '🎙 Песня — 2990₽' нажата! User ID: {callback.from_user.id}")

    

    try:

        # Получаем данные заказа

        data = await state.get_data()

        order_id = data.get('order_id')

        product = data.get('product', 'Песня')

        

        logging.info(f"📋 Данные заказа: order_id={order_id}, product={product}")

        

        if not order_id:

            await callback.message.answer("Ошибка: заказ не найден. Попробуйте создать заказ заново.")

            await callback.answer()

            return

        

        # Получаем актуальную цену песни из базы данных

        try:

            price = await get_product_price_async("Песня", "💌 Персональная песня")

            format_name = "💌 Персональная песня"

        except:

            # Если не удалось получить цены из БД, используем резервные

            price = 2990

            format_name = "💌 Персональная песня"

        

        logging.info(f"💰 Цена песни: {price} ₽")

        

        await state.update_data(format=format_name, price=price)

        

        # Сохраняем данные формата в базу данных

        from db import update_order_data

        await update_order_data(order_id, {'format': format_name, 'price': price})

        

        try:

            # Создаем платеж в ЮKassa

            description = format_payment_description("Песня", format_name, order_id)

            payment_data = await create_payment(order_id, price, description, "Песня")

            

            logging.info(f"💳 Платеж создан: {payment_data['payment_id']}")

            

            # Сохраняем данные платежа в state

            await state.update_data(

                payment_id=payment_data['payment_id'],

                payment_url=payment_data['confirmation_url']

            )

            

            keyboard = InlineKeyboardMarkup(inline_keyboard=[

                [InlineKeyboardButton(text="Заказать песню", url=payment_data['confirmation_url'])],

                [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="check_payment")],


            ])

            

            # Формируем сводку заказа

            data = await state.get_data()

            order_summary = ""

            

            await safe_edit_message(

                callback.message,

                f"{order_summary}\n"

                f"💳 <b>Оплата:</b>\n"

                f"Вы выбрали: <b>{format_name}</b>\n"

                f"Стоимость: <b>{price} ₽</b>\n\n"

                f"Для завершения заказа нажмите кнопку оплаты ниже:",

                reply_markup=keyboard,

                parse_mode="HTML"

            )

            

            # Обновляем статус заказа

            await update_order_status(order_id, "waiting_payment")

            

            # Создаем отложенные напоминания об оплате через 24 и 48 часов

            from db import create_payment_reminder_messages

            await create_payment_reminder_messages(order_id, callback.from_user.id)

            

        except Exception as e:

            logging.error(f"❌ Ошибка создания платежа: {e}")

            


            keyboard = InlineKeyboardMarkup(inline_keyboard=[


            ])

            

            # Формируем сводку заказа

            data = await state.get_data()

            order_summary = ""

            

            await safe_edit_message(

                callback.message,

                f"{order_summary}\n"

                f"💳 <b>Оплата:</b>\n"

                f"Вы выбрали: <b>{format_name}</b>\n"

                f"Стоимость: <b>{price} ₽</b>\n\n",

                reply_markup=keyboard,

                parse_mode="HTML"

            )

        

        await callback.answer()

        await log_state(callback.message, state)

        

    except Exception as e:

        logging.error(f"💥 Критическая ошибка в song_pay_link: {e}")

        await callback.message.answer(

            "Произошла критическая ошибка. Попробуйте позже или обратитесь в поддержку."

        )

        await callback.answer()



# --- Глава 2.7.1. Обработчик для кнопки "Песня — 2990P" из админки ---

@dp.callback_query(F.data == "song_final_payment")

async def song_final_payment_handler(callback: types.CallbackQuery, state: FSMContext):

    logging.info(f"🔘 Кнопка '🎙 Песня — 2990₽' (song_final_payment) нажата! User ID: {callback.from_user.id}")

    logging.info(f"🔘 Callback data: {callback.data}")

    logging.info(f"🔘 Current state: {await state.get_state()}")

    

    try:

        # Получаем данные заказа

        data = await state.get_data()

        order_id = data.get('order_id')

        product = data.get('product', 'Песня')

        

        logging.info(f"📋 Данные заказа: order_id={order_id}, product={product}")

        

        if not order_id:

            await callback.message.answer("Ошибка: заказ не найден. Попробуйте создать заказ заново.")

            await callback.answer()

            return

        

        # Получаем актуальную цену песни из базы данных

        try:

            price = await get_product_price_async("Песня", "💌 Персональная песня")

            format_name = "💌 Персональная песня"

        except:

            # Если не удалось получить цены из БД, используем резервные

            price = 2990

            format_name = "💌 Персональная песня"

        

        logging.info(f"💰 Цена песни: {price} ₽")

        

        await state.update_data(format=format_name, price=price)

        

        # Сохраняем данные формата в базу данных

        from db import update_order_data

        await update_order_data(order_id, {'format': format_name, 'price': price})

        

        try:

            # Создаем платеж в ЮKassa

            description = format_payment_description("Песня", format_name, order_id)

            payment_data = await create_payment(order_id, price, description, "Песня")

            

            logging.info(f"💳 Платеж создан: {payment_data['payment_id']}")

            

            # Сохраняем данные платежа в state

            await state.update_data(

                payment_id=payment_data['payment_id'],

                payment_url=payment_data['confirmation_url']

            )

            

            keyboard = InlineKeyboardMarkup(inline_keyboard=[

                [InlineKeyboardButton(text="Заказать песню", url=payment_data['confirmation_url'])],

                [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="check_payment")],


            ])

            

            # Формируем сводку заказа

            data = await state.get_data()

            order_summary = ""

            

            await safe_edit_message(

                callback.message,

                f"{order_summary}\n"

                f"💳 <b>Оплата:</b>\n"

                f"Вы выбрали: <b>{format_name}</b>\n"

                f"Стоимость: <b>{price} ₽</b>\n\n"

                f"Для завершения заказа нажмите кнопку оплаты ниже:",

                reply_markup=keyboard,

                parse_mode="HTML"

            )

            

            # Обновляем статус заказа

            await update_order_status(order_id, "waiting_payment")

            

            # Создаем отложенные напоминания об оплате через 24 и 48 часов

            from db import create_payment_reminder_messages

            await create_payment_reminder_messages(order_id, callback.from_user.id)

            

        except Exception as e:

            logging.error(f"❌ Ошибка создания платежа: {e}")

            


            keyboard = InlineKeyboardMarkup(inline_keyboard=[


            ])

            

            # Формируем сводку заказа

            data = await state.get_data()

            order_summary = ""

            

            await safe_edit_message(

                callback.message,

                f"{order_summary}\n"

                f"💳 <b>Оплата:</b>\n"

                f"Вы выбрали: <b>{format_name}</b>\n"

                f"Стоимость: <b>{price} ₽</b>\n\n",

                reply_markup=keyboard,

                parse_mode="HTML"

            )

        

        await callback.answer()

        await log_state(callback.message, state)

        

    except Exception as e:

        logging.error(f"💥 Критическая ошибка в song_final_payment_handler: {e}")

        await callback.message.answer(

            "Произошла критическая ошибка. Попробуйте позже или обратитесь в поддержку."

        )

        await callback.answer()





# --- Глава 2.9. Ожидание и прогрев ---

@dp.message(StateFilter(SongWaitingStates.waiting_and_warming))

async def song_waiting_and_warming(message: types.Message, state: FSMContext):

    # Пользователь может отправлять сообщения во время ожидания

    # Это состояние для прогрева и удержания интереса

    # Сохраняем сообщение пользователя в историю заказа
    data = await state.get_data()
    order_id = data.get('order_id')
    if order_id:
        from db import add_message_history, create_or_update_order_notification
        await add_message_history(order_id, "user", message.text)
        await create_or_update_order_notification(order_id)
        logging.info(f"✅ СОХРАНЕНО: Сообщение пользователя {message.from_user.id} в историю заказа {order_id}: {message.text[:50]}...")

    # Можно добавить логику для ответов на сообщения пользователя

    await message.answer("Спасибо за ваше сообщение! Мы продолжаем работу над вашей песней.")

    await log_state(message, state)



# --- Команда для менеджера для отправки черновика песни (Глава 2.5) ---

@dp.message(Command("send_draft"))

async def send_song_draft(message: types.Message, state: FSMContext):

    # Проверяем, что это менеджер (можно добавить проверку роли)

    # В реальном проекте здесь должна быть проверка прав доступа

    

    # Получаем ID пользователя из команды (формат: /send_draft USER_ID)

    try:

        user_id = int(message.text.split()[1])

        # В реальном проекте здесь нужно:

        # 1. Получить состояние пользователя из БД

        # 2. Установить состояние SongDraftStates.waiting_for_draft

        # 3. Отправить черновик пользователю

        await message.answer(f"Черновик будет отправлен пользователю {user_id}. В реальном проекте здесь будет интеграция с БД.")

    except (IndexError, ValueError):

        await message.answer("Использование: /send_draft USER_ID")

    

    await log_state(message, state)



# --- Глава 2.7. Работа с отказом от оплаты (эмуляция через команду /remind_song) ---

@dp.message(StateFilter(lambda c: c.text == "/remind_song"))

async def remind_song_payment(message: types.Message, state: FSMContext):

    await message.answer("Возможно, цена вас смутила? Мы можем предложить другие варианты — напишите нам.")

    await asyncio.sleep(5)

    await message.answer("Готовы сделать песню проще, но не менее искренней. Дайте знать, если вам это интересно.")

    await log_state(message, state)



# --- Глава 2.10. Предфинальная версия песни ---

@dp.message(StateFilter(SongFinalStates.waiting_for_final))

async def receive_song_final(message: types.Message, state: FSMContext):

    # Менеджер отправляет предфинальную версию песни

    await state.update_data(song_final=message.text)

    await update_order_status((await state.get_data()).get('order_id'), "final_sent")

    

    # Показываем предфинальную версию пользователю

    await message.answer("🎉 Вот она - финальная версия твоей песни ❤️\n\n"

                        "Мы вложили в эту песню много любви и переживаем не меньше тебя. Надеемся, она тронет до мурашек 🥹")

    await message.answer(message.text)  # Показываем версию

    

    # Кнопки такие же, как для обычного черновика

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="Все нравится, отличная песня", callback_data="song_draft_ok")],

        [InlineKeyboardButton(text="Обратная связь", callback_data="song_draft_edit")]

    ])

    await message.answer("🎉 Вот она - финальная версия твоей песни ❤️\n\n"

                        "Мы вложили в эту песню много любви и переживаем не меньше тебя. Надеемся, она тронет до мурашек 🥹", reply_markup=keyboard)

    await state.set_state(SongDraftStates.draft_received)

    await log_state(message, state)



@dp.callback_query(F.data.in_(["song_final_ok", "song_final_edit"]))

async def song_final_feedback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    if callback.data == "song_final_ok":

        # Переходим к доставке финальной версии

        await callback.message.answer("✅ Отлично! Твоя песня готова к финализации.")

        await state.set_state(SongFinalStates.waiting_for_final)

        

        # Отправляем уведомление менеджеру

        data = await state.get_data()

        order_id = data.get('order_id')

        await add_outbox_task(

            order_id=order_id,

            user_id=callback.from_user.id,

            type_="manager_notification",

            content=f"Заказ #{order_id}: Пользователь подтвердил предфинальную версию песни. Готов к финализации."

        )

        

    elif callback.data == "song_final_edit":

        await callback.message.answer(

            "Поделись, пожалуйста, что именно хочешь изменить в песне? ✨\n"

            "Укажи конкретно: в каком куплете, какое слово или строчку нужно заменить — так мы сможем внести правки максимально точно 💕"

        )

        await state.set_state(SongFinalStates.collecting_feedback)

    

    await log_state(callback.message, state)





# --- Глава 2.12. Доставка финальной песни ---

@dp.message(StateFilter(SongFinalStates.waiting_for_final))

async def deliver_final_song(message: types.Message, state: FSMContext):

    # Менеджер отправляет финальную версию песни

    data = await state.get_data()

    order_id = data.get('order_id')

    

    await update_order_status(order_id, "ready")

    

    # Глава 2.12. Доставка финальной песни

    await message.answer("🎵 Ваша песня готова! Как вам? Надеемся, она вызовет сильные эмоции 💖")

    

    # Отправляем прогревочные сообщения для книги сразу

    await message.answer("📖 Спасибо, что доверили нам создание вашего подарка. А хотите создать ещё и книгу?")

    

    # Отправляем предложение с кнопками

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="📖 Создать книгу", callback_data="create_book_after_song")],

        [InlineKeyboardButton(text="✅ Завершить", callback_data="finish_song_order")]

    ])

    

    await message.answer("📚 Книга станет прекрасным дополнением к вашей песне!", reply_markup=keyboard)

    

    # Песня считается готовой и завершенной

    await state.set_state(SongFinalStates.final_received)

    await log_state(message, state)



# --- Глава 2.13. Обратная связь и завершение ---

@dp.callback_query(F.data == "song_liked")

async def song_liked_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    # Записываем в историю

    try:

        data = await state.get_data()

        order_id = data.get('order_id')

        from db import add_message_history

        await add_message_history(order_id, sender="user", message="Пользователь: понравилась финальная песня")

    except Exception:

        pass

    

    # Согласно требованию п.7: после нажатия "Всё понравилось" выдаем только "Отлично..." без повторных кнопок

    await callback.message.answer(

        "🎉 Отлично! Спасибо, что доверили нам создание вашего подарка!"

    )

    await log_state(callback.message, state)



@dp.callback_query(F.data == "song_needs_edit")

async def song_needs_edit_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    # Записываем в историю

    try:

        data = await state.get_data()

        order_id = data.get('order_id')

        from db import add_message_history

        await add_message_history(order_id, sender="user", message="Пользователь: требуются правки финальной песни")

    except Exception:

        pass

    

    await callback.message.answer("Что бы вы хотели изменить? Мы готовы внести правки.")

    await state.set_state(SongFinalStates.collecting_final_feedback)

    await log_state(callback.message, state)



# Обработчик сбора финальных правок

@dp.message(StateFilter(SongFinalStates.collecting_final_feedback))

async def collect_final_feedback(message: types.Message, state: FSMContext):

    data = await state.get_data()

    order_id = data.get('order_id')

    

    # Записываем комментарии в историю и отправляем менеджеру

    try:

        from db import add_message_history

        await add_message_history(order_id, sender="user", message=f"Правки к финальной песне: {message.text}")

    except Exception:

        pass

    

    # Отправляем комментарии менеджеру

    await add_outbox_task(

        order_id=order_id,

        user_id=message.from_user.id,

        type_="manager_notification",

        content=f"Заказ #{order_id}: Правки к финальной песне: {message.text}"

    )

    

    await message.answer("Спасибо за комментарии! Мы внесем правки и отправим обновленную версию.")

    

    # Возвращаемся к ожиданию финальной версии

    await state.set_state(SongFinalStates.waiting_for_final)

    await update_order_status(order_id, "editing")

    await log_state(message, state)



# Старый обработчик для совместимости

@dp.callback_query(F.data == "song_final_ok")

async def song_feedback_and_completion(callback: types.CallbackQuery, state: FSMContext):

    # Перенаправляем на новый обработчик

    await song_liked_callback(callback, state)



# УДАЛЕН ДУБЛИРУЮЩИЙ ОБРАБОТЧИК - используется только create_book_after_song_callback выше

    

    # Используем новую функцию с проверкой имени

    await start_book_creation_flow(callback, state)

    await log_state(callback.message, state)



@dp.callback_query(F.data == "finish_song_order")

async def finish_song_order(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    data = await state.get_data()

    order_id = data.get('order_id')

    

    await callback.message.answer(

        "Спасибо, что выбрал именно нас для создания своего сокровенного подарка💝\n\n"

        "Когда захочешь снова подарить эмоции и тронуть сердце близкого человека — возвращайся 🫶🏻\n\n"

        "Мы будем здесь для тебя,\n"

        "Команда \"В самое сердце\" 💖",

        parse_mode="HTML"

    )

    

    # Отправляем уведомление менеджеру о завершении заказа

    await add_outbox_task(

        order_id=order_id,

        user_id=callback.from_user.id,

        type_="manager_notification",

        content=f"Заказ #{order_id}: Пользователь завершил заказ песни. Песня доставлена успешно."

    )

    

    # Очищаем состояние

    await state.clear()

    await log_state(callback.message, state)



@dp.callback_query(F.data == "send_phone")

async def on_send_phone(callback: types.CallbackQuery, state: FSMContext):

    await callback.message.answer(

        "Пожалуйста, отправьте свой номер телефона через 📎 → Контакт в этом чате."

    )

    await callback.answer()

    await log_state(callback.message, state)







@dp.callback_query(F.data == "decline_phone")

async def on_decline_phone(callback: types.CallbackQuery, state: FSMContext):

    # Сохраняем, что номер не предоставлен

    await state.update_data(phone=None)

    # Переходим к следующему этапу — приветствие и выбор продукта

    await show_welcome_message(callback.message, state)

    await callback.answer()

    await log_state(callback.message, state)



@dp.callback_query(F.data == "start_create_book")

async def choose_product(callback: types.CallbackQuery, state: FSMContext):

    try:

        await callback.answer()

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="💌 Персональная песня", callback_data="product_song")],

            [InlineKeyboardButton(text="📖 Книга", callback_data="product_book")]

        ])

        await callback.message.answer("Что вы хотите создать?", reply_markup=keyboard)

        await state.set_state(ProductStates.choosing_product)

        await log_state(callback.message, state)

    except Exception as e:

        logging.error(f"❌ Ошибка в choose_product: {e}")

        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

        try:

            await callback.message.answer("Произошла ошибка. Попробуйте еще раз или обратитесь в поддержку.")

        except:

            pass



# Функции для обработки выбора продукта

async def process_book_choice(message: types.Message, state: FSMContext):

    """Обрабатывает выбор книги"""

    try:

        data = await state.get_data()

        product = "Книга"

        await state.update_data(product=product)

        user_id = message.from_user.id

        order_id = data.get('order_id')

        

        if not order_id:

            # Получаем актуальные данные пользователя

            user_data = await state.get_data()

            

            # Получаем username из последнего заказа пользователя

            from db import get_last_order_username

            last_username = await get_last_order_username(user_id)

            

            order_data = {

                "product": product,

                "user_id": user_id,

                "username": last_username or user_data.get('username') or message.from_user.username,

                "first_name": user_data.get('first_name') or message.from_user.first_name,

                "last_name": user_data.get('last_name') or message.from_user.last_name

            }

            order_id = await create_order(user_id, order_data)

            await state.update_data(order_id=order_id)

            await update_order_status(order_id, "product_selected")
            
            # Создаем таймер для отложенных сообщений
            from db import create_or_update_user_timer
            await create_or_update_user_timer(user_id, order_id, "product_selected", product)
            logging.info(f"✅ Создан таймер отложенных сообщений для {product}, пользователь {user_id}, заказ {order_id}")

        

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="Женский 👩🏼", callback_data="gender_female")],

            [InlineKeyboardButton(text="Мужской 🧑🏼", callback_data="gender_male")],

        ])

        await message.answer("Замечательный выбор ✨\nМы позаботимся о том, чтобы твоя книга получилась душевной и бережно сохранила все важные воспоминания.\n\nОтветь на несколько вопросов и мы начнём собирать твою историю 📖\n\n👤 Выбери свой пол:", reply_markup=keyboard)

        await state.set_state(GenderStates.choosing_gender)

        await log_state(message, state)

        

    except Exception as e:

        logging.error(f"❌ Ошибка в process_book_choice: {e}")

        await message.answer("Произошла ошибка при создании заказа. Попробуйте еще раз.")



async def process_song_choice(message: types.Message, state: FSMContext):

    """Обрабатывает выбор песни"""

    try:

        data = await state.get_data()

        product = "Песня"

        await state.update_data(product=product)

        user_id = message.from_user.id

        order_id = data.get('order_id')

        

        if not order_id:

            # Получаем актуальные данные пользователя

            user_data = await state.get_data()

            

            # Получаем username из последнего заказа пользователя

            from db import get_last_order_username

            last_username = await get_last_order_username(user_id)

            

            order_data = {

                "product": product,

                "user_id": user_id,

                "username": last_username or user_data.get('username') or message.from_user.username,

                "first_name": user_data.get('first_name') or message.from_user.first_name,

                "last_name": user_data.get('last_name') or message.from_user.last_name

            }

            order_id = await create_order(user_id, order_data)

            await state.update_data(order_id=order_id)

            await update_order_status(order_id, "product_selected")

        

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="Женский 👩🏼", callback_data="song_gender_female")],

            [InlineKeyboardButton(text="Мужской 🧑🏼", callback_data="song_gender_male")],

        ])

        await message.answer("Отличный выбор подарка✨\nМы сделаем все, чтобы твой подарок получился тёплым и трогательным 🫶🏻\n\nОтветь, пожалуйста, на несколько коротких вопросов, чтобы твоя песня попала в самое сердце \n\nВыбери свой пол:", reply_markup=keyboard)

        await state.set_state(SongGenderStates.choosing_gender)

        await log_state(message, state)

        

    except Exception as e:

        logging.error(f"❌ Ошибка в process_song_choice: {e}")

        await message.answer("Произошла ошибка при создании заказа. Попробуйте еще раз.")



# Обработчик текстовых сообщений в состоянии выбора продукта

@dp.message(StateFilter(ProductStates.choosing_product))

async def handle_product_choice_text(message: types.Message, state: FSMContext):

    """Обрабатывает текстовые сообщения при выборе продукта"""

    text = message.text.lower().strip()

    

    if text in ["книга", "book", "📖"]:

        # Пользователь выбрал книгу

        await process_book_choice(message, state)

    elif text in ["песня", "song", "❤️", "💌"]:

        # Пользователь выбрал песню

        await process_song_choice(message, state)

    elif text in ["создать подарок", "подарок", "начать", "старт"]:

        # Показываем выбор продукта

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="❤️ Песня", callback_data="product_song")],

            [InlineKeyboardButton(text="📖 Книга", callback_data="product_book")]

        ])

        await message.answer("Что вы хотите создать?", reply_markup=keyboard)

        await log_state(message, state)

    else:

        # Если пользователь написал что-то другое, напоминаем о кнопках

        await message.answer(

            "Пожалуйста, выберите 'Книга' или 'Песня', или нажмите соответствующую кнопку."

        )

        await log_state(message, state)



async def process_outbox_tasks(bot: Bot):
    logging.info("🚀 ПРОЦЕСС OUTBOX ЗАПУЩЕН - начинаем обработку задач")

    while True:

        try:
            from db import get_order
            logging.info("🔄 ПРОВЕРЯЕМ OUTBOX ЗАДАЧИ...")
            tasks = await get_pending_outbox_tasks()
            logging.info(f"🔍 РЕЗУЛЬТАТ ЗАПРОСА: найдено {len(tasks) if tasks else 0} pending задач в outbox")

            if tasks:

                logging.info(f"🔍 Найдено {len(tasks)} pending задач в outbox")

            

            for task in tasks:
                # Проверяем, что task не является None
                if not task or not isinstance(task, dict):
                    logging.error(f"❌ Некорректная задача: {task}")
                    continue
                
                try:
                    logging.info(f"🔧 НАЧИНАЕМ ОБРАБОТКУ ЗАДАЧИ: {task}")
                    logging.info(f"🔧 ПРОВЕРЯЕМ TASK: type={type(task)}, is_dict={isinstance(task, dict)}")
                    
                    if not task or not isinstance(task, dict):
                        logging.error(f"❌ TASK НЕ СЛОВАРЬ: {task}")
                        continue
                        
                    user_id = task.get('user_id')
                    type_ = task.get('type')
                    content = task.get('content')
                    task_id = task.get('id')
                    
                    if not all([user_id, type_, task_id]):
                        logging.error(f"❌ Неполные данные в задаче: user_id={user_id}, type={type_}, task_id={task_id}")
                        continue
                    order_id = task.get('order_id')
                    logging.info(f"🔧 ИЗВЛЕЧЕНЫ ДАННЫЕ ЗАДАЧИ {task_id}: user_id={user_id}, type={type_}, order_id={order_id}")
                except KeyError as e:
                    logging.error(f"❌ Отсутствует обязательное поле в задаче {task}: {e}")
                    continue
                except Exception as e:
                    logging.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА при извлечении данных задачи {task}: {e}")
                    import traceback
                    logging.error(f"❌ TRACEBACK: {traceback.format_exc()}")
                    continue

                

                # Безопасное логирование с проверкой на None
                safe_content = str(content)[:100] if content else 'None'
                safe_comment = (task.get('comment') or '')[:50]
                logging.info(f"📤 Обрабатываем задачу {task_id}: type={type_}, user_id={user_id}, content={safe_content}..., file_type={task.get('file_type')}, comment={safe_comment}...")

                

                # Проверяем валидность user_id

                if not user_id or user_id <= 0 or user_id in [12345, 0, -1]:

                    logging.error(f"❌ Некорректный user_id {user_id} в задаче {task_id}. Пропускаем задачу.")

                    await update_outbox_task_status(task_id, 'failed')

                    continue

                

                # Проверяем статус заказа для предотвращения дублирования финальных версий

                if order_id:

                    try:

                        order_data = await get_order(order_id)

                        if order_data:

                            order_status = order_data.get('status')

                            if order_status == 'ready':

                                logging.info(f"📚 Заказ {order_id} имеет статус 'ready' - пропускаем задачу {task_id} для предотвращения дублирования")

                                await update_outbox_task_status(task_id, 'sent')

                                continue

                            elif order_status == 'completed':

                                logging.info(f"✅ Заказ {order_id} завершен - пропускаем задачу {task_id}")

                                await update_outbox_task_status(task_id, 'sent')

                                continue

                    except Exception as e:

                        logging.error(f"❌ Ошибка проверки статуса заказа {order_id}: {e}")

                

                if type_ == 'text' or type_ == 'text_message':

                    try:

                        logging.info(f"📝 Отправляем текстовое сообщение пользователю {user_id}: {content[:50]}...")

                        

                        # Обычное текстовое сообщение

                        await bot.send_message(user_id, content, parse_mode="HTML")

                        await update_outbox_task_status(task_id, 'sent')

                        logging.info(f"✅ Сообщение отправлено успешно")

                    except Exception as e:

                        logging.error(f"Ошибка отправки текстового сообщения {task_id}: {e}")

                        await update_outbox_task_status(task_id, 'failed')

                elif type_ == 'stories':

                    try:

                        logging.info(f"📖 Отправляем сюжеты пользователю {user_id}: {content[:50]}...")

                        

                        # Создаем виртуальное сообщение для обработки сюжетов

                        from aiogram.types import Message

                        from aiogram.fsm.context import FSMContext

                        

                        # Создаем виртуальное сообщение от менеджера

                        virtual_message = Message(

                            message_id=0,

                            date=datetime.now(),

                            chat=types.Chat(id=user_id, type="private"),

                            from_user=types.User(id=0, is_bot=False, first_name="Manager"),

                            text=content

                        )

                        

                        # Получаем состояние пользователя

                        from aiogram.fsm.storage.base import StorageKey

                        storage_key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)

                        

                        # Создаем контекст состояния

                        from aiogram.fsm.context import FSMContext

                        state = FSMContext(storage=storage, key=storage_key)

                        

                        # Проверяем текущее состояние пользователя

                        current_state = await state.get_state()

                        

                        if current_state == "ManagerContentStates:waiting_story_options":

                            # Пользователь ожидает страницы для выбора - переводим в состояние выбора страниц

                            await state.set_state(BookFinalStates.choosing_pages)

                            

                            # Инициализируем данные заказа

                            order_id = task.get('order_id')

                            if order_id:

                                await state.update_data(order_id=order_id)

                            

                            # Отправляем как обычное сообщение, так как страницы будут отправлены через page_selection

                            await bot.send_message(user_id, content)

                            logging.info(f"✅ Переведен в состояние выбора страниц и отправлено сообщение пользователю {user_id}")

                        elif current_state == "StoryCustomizationStates:waiting_for_stories":

                            # Пользователь ожидает сюжеты - обрабатываем их (старый код)

                            await receive_stories_from_manager(virtual_message, state)

                            logging.info(f"✅ Сюжеты обработаны и отправлены пользователю {user_id}")

                        else:

                            # Пользователь не в состоянии ожидания сюжетов - отправляем как обычное сообщение

                            await bot.send_message(user_id, content)

                            logging.info(f"✅ Сюжеты отправлены как обычное сообщение пользователю {user_id}")

                            logging.info(f"🔍 Текущее состояние пользователя: {current_state}")

                        

                        await update_outbox_task_status(task_id, 'sent')

                        logging.info(f"✅ Сюжеты отправлены успешно")

                    except Exception as e:

                        logging.error(f"Ошибка отправки сюжетов {task_id}: {e}")

                        await update_outbox_task_status(task_id, 'failed')

                elif type_ == 'file':

                    try:

                        file_type = (task.get('file_type') or '').lower()

                        comment = task.get('comment') or ''
                        
                        # Проверяем, является ли это общим сообщением
                        is_general_message = task.get('is_general_message', 0) == 1

                        logging.info(f"📤 Полученный тип файла в file: '{file_type}'")
                        logging.info(f"📤 Общее сообщение: {is_general_message}")

                        # Если это общее сообщение, отправляем файл без кнопок
                        if is_general_message:
                            logging.info(f"📤 ОБЩЕЕ СООБЩЕНИЕ: Отправляем файл для задачи {task_id}")
                            logging.info(f"📤 Файл: {content}, Тип: {file_type}, Комментарий: {comment}")
                            
                            # Проверяем существование файла
                            if not os.path.exists(content):
                                logging.error(f"❌ Файл не существует: {content}")
                                await update_outbox_task_status(task_id, 'failed')
                                continue
                            
                            try:
                                # Логируем размер файла перед отправкой
                                file_size_mb = os.path.getsize(content) / (1024 * 1024)
                                logging.info(f"📤 Размер файла перед отправкой: {file_size_mb:.2f} МБ")
                                
                                # Для общих сообщений отправляем файлы как нативные типы, но без кнопок
                                input_file = FSInputFile(content)
                                
                                if file_type in ['image', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
                                    # Изображение - отправляем как фото
                                    logging.info(f"📤 Отправляем как ФОТО: {file_type}")
                                    await bot.send_photo(
                                        user_id, 
                                        input_file, 
                                        caption=comment if comment else None
                                    )
                                elif file_type in ['video', 'mp4', 'avi', 'mov', 'mkv', 'webm']:
                                    # Видео - отправляем как видео
                                    logging.info(f"📤 Отправляем как ВИДЕО: {file_type}")
                                    await bot.send_video(
                                        user_id, 
                                        input_file, 
                                        caption=comment if comment else None
                                    )
                                elif file_type in ['audio', 'mp3', 'wav', 'ogg', 'm4a', 'aac']:
                                    # Аудио - отправляем как аудио
                                    logging.info(f"📤 Отправляем как АУДИО: {file_type}")
                                    await bot.send_audio(
                                        user_id, 
                                        input_file, 
                                        caption=comment if comment else None
                                    )
                                else:
                                    # Остальные файлы (PDF, документы) - как документы
                                    logging.info(f"📤 Отправляем как ДОКУМЕНТ: {file_type}")
                                    await bot.send_document(
                                        user_id, 
                                        input_file, 
                                        caption=comment if comment else None
                                    )
                                
                                # Помечаем задачу как отправленную
                                await update_outbox_task_status(task_id, 'sent')
                                logging.info(f"✅ Общее сообщение с файлом отправлено успешно")
                                continue
                                
                            except Exception as send_error:
                                error_msg = str(send_error)
                                logging.error(f"❌ Ошибка отправки общего сообщения {task_id}: {error_msg}")
                                await update_outbox_task_status(task_id, 'failed')
                                continue

                        # Проверяем, является ли это черновиком или финальной версией песни

                        order_id = task.get('order_id')
                        logging.info(f"📋 Получен order_id: {order_id} для задачи {task_id}")
                        
                        if not order_id:
                            logging.error(f"❌ Отсутствует order_id в задаче {task_id}")
                            await update_outbox_task_status(task_id, 'failed')
                            continue
                        
                        # НЕ отправляем файл сразу! Сначала определим тип и добавим кнопки

                        is_song_draft = False

                        is_song_final = False

                        is_book_draft = False

                        is_book_demo = False

                        is_song_demo = False

                        

                        logging.info(f"🔍 ОТЛАДКА: Обрабатываем файл для заказа {order_id or 'неизвестно'}")

                        logging.info(f"📄 Тип файла: {file_type}, Комментарий: {comment}")

                        # Получаем данные заказа
                        from db import get_order
                        order = await get_order(order_id)

                        if order and order.get('order_data'):

                            import json

                            try:

                                order_data = json.loads(order.get('order_data', '{}')) if order and order.get('order_data') else {}

                                product = order_data.get('product', '')

                                order_status = order.get('status', '')

                                

                                logging.info(f"📊 Продукт: {product}, Статус заказа: {order_status}")
                                
                                logging.info(f"📋 ДЕТАЛЬНАЯ ОТЛАДКА для задачи {task_id}:")
                                logging.info(f"📋 - Задача ID: {task_id}")
                                logging.info(f"📋 - Заказ ID: {order_id}")
                                logging.info(f"📋 - Продукт: '{product}'")
                                logging.info(f"📋 - Статус заказа: '{order_status}'")
                                logging.info(f"📋 - Тип файла: '{file_type}'")
                                logging.info(f"📋 - Комментарий: '{comment}'")

                                

                                if product == 'Песня':

                                    logging.info(f"🎵 Проверяем статус для песни: {order_status}, file_type: {file_type}")

                                    # Если это демо-контент для песни (аудио или видео)
                                    if file_type in ['demo_audio', 'demo_video'] or order_status in ['waiting_manager', 'demo_content', 'questions_completed']:
                                        
                                        is_song_demo = True
                                        
                                        logging.info(f"🎵 Обнаружен демо-контент песни для заказа {order_id}")
                                        
                                        # Обновляем статус заказа
                                        await update_order_status(order_id, "demo_sent")

                                    # Если это черновик/предфинальная версия песни

                                    elif file_type == 'mp3' and order_status in ['paid', 'waiting_draft', 'editing', 'draft_sent', 'prefinal_sent']:

                                        is_song_draft = True

                                        logging.info(f"🎵 Обнаружен черновик/предфинальная версия песни для заказа {order_id}")

                                    # Если это финальная версия песни

                                    elif file_type == 'mp3' and order_status in ['waiting_final', 'ready']:

                                        is_song_final = True

                                        logging.info(f"🎼 Обнаружена финальная версия песни для заказа {order_id}")

                                    else:

                                        logging.info(f"❌ НЕ черновик/финал песни: product={product}, file_type={file_type}, status={order_status}")

                                        logging.info(f"🔍 Доступные статусы для песни: paid, waiting_draft, editing, draft_sent, prefinal_sent, waiting_final")

                                elif product == 'Книга':

                                    # Определяем тип контента для книги

                                    logging.info(f"📖 Обработка файла для книги: file_type={file_type}, status={order_status}")

                                    

                                    # Проверяем по статусу заказа

                                    if order_status in ['questions_completed', 'waiting_manager', 'demo_sent', 'demo_content']:

                                        is_book_demo = True

                                        logging.info(f"📖 Обнаружен демо-контент книги по статусу для заказа {order_id}")

                                        logging.info(f"📖 Статус заказа: {order_status}")

                                        # Обновляем статус заказа

                                        await update_order_status(order_id, "demo_sent")

                                    elif order_status in ['waiting_draft', 'draft_sent', 'editing']:

                                        is_book_draft = True

                                        logging.info(f"📖 Обнаружен черновик книги по статусу для заказа {order_id}")

                                        logging.info(f"📖 Продукт: {product}, Статус: {order_status}")

                                    elif order_status == 'ready':

                                        is_book_final = True

                                        logging.info(f"📚 Обнаружена финальная версия книги по статусу для заказа {order_id}")

                                        logging.info(f"📚 Продукт: {product}, Статус: {order_status}")

                                        logging.info(f"📚 Финальная версия книги - пропускаем повторную отправку")

                                    # Проверяем по тексту комментария

                                    elif 'демо-контент' in comment.lower() or 'примеры оформления' in comment.lower():

                                        is_book_demo = True

                                        logging.info(f"📖 Обнаружен демо-контент книги по комментарию для заказа {order_id}")

                                        # Обновляем статус заказа

                                        await update_order_status(order_id, "demo_sent")

                                    elif 'черновик' in comment.lower() or 'внимательно просмотрите' in comment.lower():

                                        is_book_draft = True

                                        logging.info(f"📖 Обнаружен черновик книги по комментарию для заказа {order_id}")

                                    else:

                                        logging.info(f"📖 Обычная отправка файла для книги: file_type={file_type}, status={order_status}")

                                else:

                                    # Для других продуктов - обычная отправка файлов

                                    logging.info(f"📖 Обычная отправка файла для {product}: file_type={file_type}, status={order_status}")

                            except Exception as e:

                                logging.error(f"Ошибка проверки типа заказа: {e}")

                        else:

                            logging.warning(f"⚠️ Заказ {order_id} не найден или нет данных")

                        
                        # ПРИНУДИТЕЛЬНАЯ ЛОГИКА ОПРЕДЕЛЕНИЯ ДЕМО-КОНТЕНТА
                        # Проверяем по статусу заказа (ПРИОРИТЕТ #1)
                        if order:
                            try:
                                order_data = json.loads(order.get('order_data', '{}')) if order.get('order_data') else {}
                                product = order_data.get('product', '')
                                order_status = order.get('status', '')
                                
                                # Если статус указывает на демо - это ТОЧНО демо
                                if order_status in ['waiting_manager', 'demo_content', 'questions_completed']:
                                    if product == 'Книга':
                                        is_book_demo = True
                                        logging.info(f"🔧 ПРИНУДИТЕЛЬНО: статус {order_status} -> is_book_demo=True")
                                    elif product == 'Песня':
                                        is_song_demo = True
                                        logging.info(f"🔧 ПРИНУДИТЕЛЬНО: статус {order_status} -> is_song_demo=True")
                                        
                            except Exception as e:
                                logging.error(f"❌ Ошибка определения демо по статусу: {e}")
                        
                        # Если в комментарии есть ключевые слова демо - это демо (ПРИОРИТЕТ #2)
                        demo_keywords = ['демо', 'demo', 'пробные страницы', 'примеры оформления', 'образцы']
                        if any(keyword in comment.lower() for keyword in demo_keywords):
                            if order:
                                try:
                                    order_data = json.loads(order.get('order_data', '{}')) if order.get('order_data') else {}
                                    product = order_data.get('product', '')
                                    if product == 'Книга':
                                        is_book_demo = True
                                        logging.info(f"🔧 ПРИНУДИТЕЛЬНО: ключевые слова -> is_book_demo=True")
                                    elif product == 'Песня':
                                        is_song_demo = True
                                        logging.info(f"🔧 ПРИНУДИТЕЛЬНО: ключевые слова -> is_song_demo=True")
                                except Exception as e:
                                    logging.error(f"❌ Ошибка определения демо по ключевым словам: {e}")
                        
                        # ПОСЛЕДНЯЯ ПОПЫТКА: если ничего не определилось, но есть файл - делаем демо
                        if not any([is_song_draft, is_song_final, is_book_draft, is_book_demo, is_song_demo]):
                            if order:
                                try:
                                    order_data = json.loads(order.get('order_data', '{}')) if order.get('order_data') else {}
                                    product = order_data.get('product', '')
                                    # Если есть файл и продукт, но тип не определился - делаем демо
                                    if product == 'Книга' and file_type in ['jpg', 'jpeg', 'png', 'pdf']:
                                        is_book_demo = True
                                        logging.info(f"🔧 РЕЗЕРВНАЯ ЛОГИКА: файл {file_type} для книги -> is_book_demo=True")
                                    elif product == 'Песня' and file_type in ['mp3', 'wav', 'demo_audio', 'demo_video']:
                                        is_song_demo = True
                                        logging.info(f"🔧 РЕЗЕРВНАЯ ЛОГИКА: файл {file_type} для песни -> is_song_demo=True")
                                except Exception as e:
                                    logging.error(f"❌ Ошибка резервной логики: {e}")
                        
                        # Логируем финальные результаты определения типов
                        logging.info(f"📋 РЕЗУЛЬТАТЫ ОПРЕДЕЛЕНИЯ ТИПОВ для задачи {task_id}:")
                        logging.info(f"📋 - is_song_draft: {is_song_draft}")
                        logging.info(f"📋 - is_song_final: {is_song_final}")
                        logging.info(f"📋 - is_book_draft: {is_book_draft}")
                        logging.info(f"📋 - is_book_demo: {is_book_demo}")
                        logging.info(f"📋 - is_song_demo: {is_song_demo}")

                        # Проверяем существование и размер файла перед отправкой
                        if not os.path.exists(content):
                            logging.error(f"❌ Файл не существует: {content}")
                            if safe_task_id != 'неизвестно':
                                await update_outbox_task_status(safe_task_id, 'failed')
                            continue
                        
                        # Логируем размер файла, но не блокируем отправку
                        try:
                            file_size_mb = os.path.getsize(content) / (1024 * 1024)
                            logging.info(f"📄 Отправляем файл {content} размером {file_size_mb:.1f}MB")
                        except Exception as e:
                            logging.error(f"❌ Ошибка получения размера файла {content}: {e}")

                        # Обычная обработка файлов

                        if file_type == 'pdf':

                            input_file = FSInputFile(content)
                            
                            logging.info(f"🔍 ОТЛАДКА PDF: is_book_draft={is_book_draft}, comment='{comment}', order_id={order_id}")

                            

                            # Проверяем, является ли это черновиком книги

                            if is_book_draft:

                                # Для черновика книги добавляем кнопки

                                keyboard = InlineKeyboardMarkup(inline_keyboard=[

                                    [InlineKeyboardButton(text="Все супер", callback_data="book_draft_ok")],

                                    [InlineKeyboardButton(text="Внести правки", callback_data="book_draft_edit")]

                                ])

                                

                                # Добавляем дополнительный текст для черновика книги

                                additional_text = "\n\nВот они — страницы твоей книги 📖\n"

                                additional_text += "Мы вложили в них много тепла и переживаем не меньше тебя. Надеемся, они тронут твоё сердце 💕\n\n"

                                additional_text += "Если тебе всё нравится — жми \"Всё супер\".\n"

                                additional_text += "Если хочешь внести правки — нажми \"Внести правки\"."

                                full_caption = comment + additional_text

                                

                                try:
                                    await bot.send_document(user_id, input_file, caption=full_caption, reply_markup=keyboard)

                                    # Обновляем статус заказа ТОЛЬКО если это действительно черновик
                                    if any(keyword in comment.lower() for keyword in ['черновик', 'внимательно просмотрите', 'готов', 'готово']):
                                        await update_order_status(order_id, "draft_sent")
                                        logging.info(f"📋 Статус заказа {order_id} изменен на draft_sent")
                                    else:
                                        logging.info(f"📋 Файл отправлен без изменения статуса (не черновик)")
                                    
                                    # Помечаем задачу как отправленную
                                    await update_outbox_task_status(task_id, 'sent')
                                    logging.info(f"✅ Черновик книги отправлен с кнопками успешно")
                                    
                                except Exception as send_error:
                                    error_msg = str(send_error)
                                    logging.error(f"❌ Ошибка отправки черновика {task_id}: {error_msg}")
                                    
                                    # Увеличиваем счетчик попыток
                                    await increment_outbox_retry_count(task_id)
                                    current_retry_count = task.get('retry_count', 0) + 1
                                    max_retries = task.get('max_retries', 5)
                                    
                                    # Проверяем тип ошибки для принятия решения о повторе
                                    if any(err in error_msg.lower() for err in ['timeout', 'too many requests', 'network', 'connection', 'read timeout']):
                                        # Временные ошибки - проверяем лимит попыток
                                        if current_retry_count >= max_retries:
                                            logging.error(f"❌ Превышен лимит попыток ({max_retries}) для задачи {task_id}")
                                            await update_outbox_task_status(task_id, 'failed')
                                        else:
                                            logging.info(f"🔄 Временная ошибка для задачи {task_id}, попытка {current_retry_count}/{max_retries}")
                                            await update_outbox_task_status(task_id, 'pending')
                                    elif "file size" in error_msg.lower() or "too large" in error_msg.lower():
                                        # Ошибки размера файла - логируем но не блокируем
                                        logging.warning(f"⚠️ Возможна проблема с размером файла для задачи {task_id}")
                                        await update_outbox_task_status(task_id, 'failed')
                                    elif "forbidden" in error_msg.lower() or "blocked" in error_msg.lower():
                                        # Пользователь заблокировал бота
                                        logging.error(f"❌ Пользователь {user_id} заблокировал бота")
                                        await update_outbox_task_status(task_id, 'failed')
                                    else:
                                        # Неизвестные ошибки - проверяем лимит попыток
                                        if current_retry_count >= max_retries:
                                            logging.error(f"❌ Превышен лимит попыток ({max_retries}) для неизвестной ошибки задачи {task_id}")
                                            await update_outbox_task_status(task_id, 'failed')
                                        else:
                                            logging.info(f"🔄 Неизвестная ошибка для задачи {task_id}, попытка {current_retry_count}/{max_retries}")
                                            await update_outbox_task_status(task_id, 'pending')
                                    
                                    continue

                            else:

                                # Обычная отправка PDF без кнопок
                                logging.info(f"📄 Отправляем обычный PDF (не черновик) пользователю {user_id}")

                                try:
                                    await bot.send_document(user_id, input_file, caption=comment)
                                    logging.info(f"✅ PDF отправлен успешно пользователю {user_id}")
                                    
                                    # Помечаем задачу как отправленную
                                    await update_outbox_task_status(task_id, 'sent')
                                    
                                except Exception as pdf_error:
                                    logging.error(f"❌ Ошибка отправки обычного PDF {task_id}: {pdf_error}")
                                    await update_outbox_task_status(task_id, 'failed')

                        elif file_type == 'mp3':

                            input_file = FSInputFile(content)

                            

                            # Если это финальная версия песни (Глава 2.12)

                            if is_song_final:

                                # Глава 2.12. Доставка финальной песни

                                # НЕ отправляем аудиофайл повторно - он уже был отправлен менеджером

                                logging.info(f"🎼 Финальная версия песни уже отправлена менеджером, пропускаем повторную отправку")

                            

                                await bot.send_message(user_id, "🎵 Ваша песня готова! Как вам? Надеемся, она вызовет сильные эмоции 💖")

                                

                                # Отправляем прогревочные сообщения для книги сразу

                                await bot.send_message(user_id, "Спасибо, что доверили нам создание такого важного подарка 💝")

                                

                                # Отправляем предложение с кнопками

                                keyboard = InlineKeyboardMarkup(inline_keyboard=[

                                    [InlineKeyboardButton(text="Создать пробную книгу", callback_data="create_book_after_song")],

                                    [InlineKeyboardButton(text="Вернусь к вам чуть позже ❤️", callback_data="finish_song_order")]

                                ])

                                

                                await bot.send_message(

                                    user_id,

                                    "Давай соберём ещё больше воспоминаний в книге со словами, моментами и фотографиями.\n\n"

                                    "🗝 Уникальность этой книги заключается в том, что мы оживим то, что не успело попасть на фото: особенные ситуации в вашей жизни, важные слова, сказанные шёпотом, и чувства, которые мы бережем.\n\n"

                                    "Это сокровенный подарок, где оживут самые дорогие мгновения ✨\n"

                                    "Хочешь попробовать бесплатно?",

                                    reply_markup=keyboard

                                )

                            

                                # Обновляем состояние пользователя в хранилище

                                try:

                                    from aiogram.fsm.storage.base import StorageKey

                                    storage_key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)

                                    await storage.set_state(key=storage_key, state=SongFinalStates.final_received)

                                    

                                    # Также сохраняем order_id в данных состояния

                                    await storage.set_data(key=storage_key, data={"order_id": order_id})

                                    

                                    logging.info(f"🔄 Состояние пользователя {user_id} изменено на SongFinalStates.final_received")

                                except Exception as e:

                                    logging.error(f"Ошибка обновления состояния: {e}")

                                

                                # Обновляем статус заказа

                                await update_order_status(order_id, "ready")

                                logging.info(f"📋 Статус заказа {order_id} изменен на ready")

                                

                                # Удаляем задачу из outbox после успешной отправки

                                await update_outbox_task_status(task_id, 'sent')

                                logging.info(f"✅ Финальная версия песни отправлена успешно, задача {task_id} удалена из outbox")

                                logging.info(f"🔍 Задача {task_id} помечена как 'sent' в базе данных")

                            

                            # Если это черновик/предфинальная версия песни, добавляем кнопки

                            elif is_song_draft:

                                logging.info(f"🔘 Статус заказа: {order_status}")

                                

                                message_text = "🎉 Вот она - финальная версия твоей песни ❤️\n\n"

                                message_text += "Мы вложили в эту песню много любви и переживаем не меньше тебя. Надеемся, она тронет до мурашек 🥹"

                                button_text = "Все нравится, отличная песня"

                                logging.info(f"🔘 Создаю кнопки для черновика/предфинальной версии: {button_text}")

                                

                                keyboard = InlineKeyboardMarkup(inline_keyboard=[

                                    [InlineKeyboardButton(text=button_text, callback_data="song_draft_ok")],

                                    [InlineKeyboardButton(text="Обратная связь", callback_data="song_draft_edit")]

                                ])

                                await bot.send_audio(user_id, input_file, caption=message_text, reply_markup=keyboard)

                                

                                # Обновляем состояние пользователя в хранилище

                                try:

                                    from aiogram.fsm.storage.base import StorageKey

                                    storage_key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)

                                    await storage.set_state(key=storage_key, state=SongDraftStates.draft_received)

                                    

                                    # Также сохраняем order_id в данных состояния

                                    await storage.set_data(key=storage_key, data={"order_id": order_id})

                                    

                                    logging.info(f"🔄 Состояние пользователя {user_id} изменено на SongDraftStates.draft_received")

                                except Exception as e:

                                    logging.error(f"Ошибка обновления состояния: {e}")

                                

                                logging.info(f"✅ Черновик песни отправлен с кнопками успешно")

                                

                                # Удаляем задачу из outbox после отправки аудиофайла

                                await update_outbox_task_status(task_id, 'sent')

                                logging.info(f"✅ Черновик песни отправлен, задача {task_id} удалена из outbox")

                            else:

                                await bot.send_audio(user_id, input_file)

                                

                                # Обновляем статус заказа ТОЛЬКО если это действительно черновик

                                # Проверяем, что комментарий содержит ключевые слова черновика

                                if any(keyword in comment.lower() for keyword in ['черновик', 'пробная версия', 'предфинальная', 'готов', 'готово']):

                                    await update_order_status(order_id, "draft_sent")

                                    logging.info(f"📋 Статус заказа {order_id} изменен на draft_sent")

                                else:

                                    logging.info(f"📋 MP3 файл отправлен без изменения статуса (не черновик)")

                                

                                # Удаляем задачу из outbox после отправки аудиофайла

                                await update_outbox_task_status(task_id, 'sent')

                                logging.info(f"✅ MP3 файл отправлен, задача {task_id} удалена из outbox")

                        elif file_type in ['jpg', 'jpeg', 'png', 'image']:

                            try:

                                input_file = FSInputFile(content)

                                

                                # Проверяем, является ли это черновиком книги

                                if is_book_draft:

                                    # Для черновика книги добавляем кнопки

                                    keyboard = InlineKeyboardMarkup(inline_keyboard=[

                                        [InlineKeyboardButton(text="Все супер", callback_data="book_draft_ok")],

                                        [InlineKeyboardButton(text="Внести правки", callback_data="book_draft_edit")]

                                    ])

                                    

                                    # Добавляем дополнительный текст для черновика книги

                                    additional_text = "\n\nВот они — страницы твоей книги 📖\n"

                                    additional_text += "Мы вложили в них много тепла и переживаем не меньше тебя. Надеемся, они тронут твоё сердце 💕\n\n"

                                    additional_text += "Если тебе всё нравится — жми \"Всё супер\".\n"

                                    additional_text += "Если хочешь внести правки — нажми \"Внести правки\"."

                                    full_caption = comment + additional_text

                                    

                                    await bot.send_photo(user_id, input_file, caption=full_caption, reply_markup=keyboard)

                                    

                                    # Обновляем статус заказа ТОЛЬКО если это действительно черновик

                                    # Проверяем, что комментарий содержит ключевые слова черновика

                                    if any(keyword in comment.lower() for keyword in ['черновик', 'внимательно просмотрите', 'готов', 'готово']):

                                        await update_order_status(order_id, "draft_sent")

                                        logging.info(f"📋 Статус заказа {order_id} изменен на draft_sent")

                                    else:

                                        logging.info(f"📋 Изображение отправлено без изменения статуса (не черновик)")

                                    

                                    # Помечаем задачу как отправленную

                                    await update_outbox_task_status(task_id, 'sent')

                                    logging.info(f"✅ Черновик книги отправлен с кнопками успешно")

                                else:

                                    # Обычная отправка фото без кнопок

                                    await bot.send_photo(user_id, input_file, caption=comment)

                                    # Помечаем задачу как отправленную

                                    await update_outbox_task_status(task_id, 'sent')

                            except Exception as e:

                                logging.error(f"Ошибка отправки изображения {task_id}: {e}")

                                await update_outbox_task_status(task_id, 'failed')

                        elif file_type in ['gif', 'mov', 'mp4', 'avi', 'mkv', 'webm'] or file_type == 'video':

                            try:

                                input_file = FSInputFile(content)

                                logging.info(f"🎬 Отправляю видео файл: file_type='{file_type}', user_id={user_id}")

                                

                                # Отправляем анимацию/видео

                                if file_type == 'gif':

                                    # GIF отправляем как анимацию

                                    await bot.send_animation(user_id, input_file, caption=comment)

                                    logging.info(f"🎬 GIF анимация отправлена пользователю {user_id}")

                                else:

                                    # Видео файлы отправляем как видео

                                    # Проверяем, является ли это черновиком книги
                                    if is_book_draft:
                                        # Для черновика книги добавляем кнопки
                                        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                            [InlineKeyboardButton(text="Все супер", callback_data="book_draft_ok")],
                                            [InlineKeyboardButton(text="Внести правки", callback_data="book_draft_edit")]
                                        ])
                                        
                                        # Добавляем дополнительный текст для черновика книги
                                        additional_text = "\n\nВот они — страницы твоей книги 📖\n"
                                        additional_text += "Мы вложили в них много тепла и переживаем не меньше тебя. Надеемся, они тронут твоё сердце 💕\n\n"
                                        additional_text += "Если тебе всё нравится — жми \"Всё супер\".\n"
                                        additional_text += "Если хочешь внести правки — нажми \"Внести правки\"."
                                        
                                        full_caption = comment + additional_text
                                        
                                        await bot.send_video(user_id, input_file, caption=full_caption, reply_markup=keyboard)
                                        
                                        # Обновляем статус заказа ТОЛЬКО если это действительно черновик
                                        if any(keyword in comment.lower() for keyword in ['черновик', 'внимательно просмотрите', 'готов', 'готово']):
                                            await update_order_status(order_id, "draft_sent")
                                            logging.info(f"📋 Статус заказа {order_id} изменен на draft_sent")
                                        
                                        logging.info(f"✅ Черновик книги (видео) отправлен с кнопками успешно")
                                    else:
                                        # Обычная отправка видео
                                        await bot.send_video(user_id, input_file, caption=comment)
                                    logging.info(f"🎬 Видео файл ({file_type}) отправлен пользователю {user_id}")

                                await update_outbox_task_status(task_id, 'sent')

                            except Exception as e:

                                logging.error(f"Ошибка отправки видео {task_id}: {e}")

                                await update_outbox_task_status(task_id, 'failed')

                        else:

                            try:

                                input_file = FSInputFile(content)

                                logging.info(f"📄 Отправляю как документ: file_type='{file_type}', user_id={user_id}")

                                await bot.send_document(user_id, input_file, caption=comment)

                                await update_outbox_task_status(task_id, 'sent')

                            except Exception as e:

                                logging.error(f"Ошибка отправки документа {task_id}: {e}")

                        await update_outbox_task_status(task_id, 'failed')

                    except Exception as e:
                        logging.error(f"Ошибка отправки файла {task_id}: {e}")
                        await update_outbox_task_status(task_id, 'failed')

                elif type_ == 'multiple_images_with_text_and_button':

                    try:

                        # Отправляем несколько файлов с текстом и кнопкой одним сообщением

                        file_type = (task.get('file_type') or '').lower()

                        text = task.get('comment') or ''

                        button_text = task.get('button_text') or 'Продолжить'

                        button_callback = task.get('button_callback') or 'continue_creation'

                        # Получаем order_id из задачи
                        order_id = task.get('order_id')
                        
                        if not order_id:
                            logging.error(f"❌ Отсутствует order_id в задаче multiple_images_with_text_and_button {task_id}")
                            await update_outbox_task_status(task_id, 'failed')
                            continue

                        logging.info(f"🔘 Обрабатываю outbox задание типа 'multiple_images_with_text_and_button'")

                        logging.info(f"🔘 Task data: {task}")

                        

                        # Парсим список файлов из JSON

                        import json

                        try:

                            file_paths = json.loads(content)

                            if not isinstance(file_paths, list):

                                file_paths = [content]  # Fallback для одного файла

                        except (json.JSONDecodeError, TypeError):

                            file_paths = [content]  # Fallback для одного файла

                        

                        logging.info(f"🔘 Отправляю {len(file_paths)} файлов одним сообщением")

                        

                        # Создаем медиагруппу

                        media_group = []

                        for i, file_path in enumerate(file_paths):

                            if os.path.exists(file_path):

                                input_file = FSInputFile(file_path)

                                # Добавляем текст только к первому файлу

                                caption = text if i == 0 else None

                                

                                # Определяем тип файла по расширению

                                file_extension = os.path.splitext(file_path)[1].lower()

                                if file_extension in ['.mp3', '.wav', '.ogg', '.m4a', '.aac']:

                                    # Аудиофайл

                                    media_group.append(InputMediaAudio(media=input_file, caption=caption))

                                    logging.info(f"🔘 Добавляю аудиофайл: {file_path}")

                                elif file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:

                                    # Изображение

                                    media_group.append(InputMediaPhoto(media=input_file, caption=caption))

                                    logging.info(f"🔘 Добавляю изображение: {file_path}")

                                elif file_extension in ['.mp4', '.avi', '.mov', '.mkv']:

                                    # Видеофайл

                                    media_group.append(InputMediaVideo(media=input_file, caption=caption))

                                    logging.info(f"🔘 Добавляю видеофайл: {file_path}")

                                else:

                                    # Документ

                                    media_group.append(InputMediaDocument(media=input_file, caption=caption))

                                    logging.info(f"🔘 Добавляю документ: {file_path}")

                            else:

                                logging.error(f"❌ Файл не найден: {file_path}")

                        

                        if media_group:

                            # Создаем клавиатуру с кнопкой

                            keyboard = InlineKeyboardMarkup(inline_keyboard=[

                                [InlineKeyboardButton(text=button_text, callback_data=button_callback)]

                            ])

                            

                            # Отправляем медиагруппу

                            await bot.send_media_group(user_id, media_group)

                            

                            # Отправляем кнопку отдельным сообщением

                            # Проверяем тип продукта для правильного текста

                            from db import get_order

                            order_data = await get_order(order_id)

                            product_type = ''

                            if order_data and order_data.get('order_data'):

                                import json

                                parsed_order_data = json.loads(order_data.get('order_data', '{}'))

                                product_type = parsed_order_data.get('product', '')

                            

                            logging.info(f"🔍 Отложенное сообщение: order_id={order_id}, product_type='{product_type}', order_data={order_data}")

                            

                            if product_type == 'Песня':

                                message_text = "Жми \"Узнать цену\", и я расскажу, как мы можем дописать песню."

                                logging.info(f"🎵 Используем текст для песни")

                            elif product_type == 'Книга':

                                message_text = "Жми \"Узнать цену\" и расскажем, как мы можем создать вашу книгу так, чтобы она стала тем самым особенным подарком🎁"

                                logging.info(f"📖 Используем текст для книги")

                            else:

                                # Если тип продукта не определен, используем текст для книги по умолчанию

                                message_text = "Жми \"Узнать цену\" и расскажем, как мы можем создать вашу книгу так, чтобы она стала тем самым особенным подарком🎁"

                                logging.info(f"📖 Используем текст для книги по умолчанию, product_type='{product_type}'")

                            

                            await bot.send_message(user_id, message_text, reply_markup=keyboard)

                            await update_outbox_task_status(task_id, 'sent')
                            
                            # Создаем таймер для этапа demo_received_book (Глава 3: Получение демо-контента книги)
                            if product_type == 'Книга':
                                try:
                                    from db import create_or_update_user_timer
                                    await create_or_update_user_timer(user_id, order_id, "demo_received_book", "Книга")
                                    logging.info(f"✅ Создан таймер для этапа demo_received_book (Глава 3), пользователь {user_id}, заказ {order_id}")
                                except Exception as timer_error:
                                    logging.error(f"❌ Ошибка создания таймера для demo_received_book: {timer_error}")
                            
                            # Создаем таймер для этапа demo_received_song (Глава 3: Получение демо-контента песни)
                            elif product_type == 'Песня':
                                try:
                                    from db import create_or_update_user_timer
                                    await create_or_update_user_timer(user_id, order_id, "demo_received_song", "Песня")
                                    logging.info(f"✅ Создан таймер для этапа demo_received_song (Глава 3), пользователь {user_id}, заказ {order_id}")
                                except Exception as timer_error:
                                    logging.error(f"❌ Ошибка создания таймера для demo_received_song: {timer_error}")

                        else:

                            await update_outbox_task_status(task_id, 'failed')

                    except Exception as e:

                        logging.error(f"Ошибка отправки multiple_images_with_text_and_button {task_id}: {e}")

                        await update_outbox_task_status(task_id, 'failed')

                elif type_ == 'image_with_text_and_button':

                    try:

                        # Отправляем файл с текстом и кнопкой

                        file_type = (task.get('file_type') or '').lower()

                        text = task.get('comment') or ''

                        button_text = task.get('button_text') or 'Продолжить'

                        button_callback = task.get('button_callback') or 'continue_creation'

                        # Получаем order_id из задачи
                        order_id = task.get('order_id')
                        
                        if not order_id:
                            logging.error(f"❌ Отсутствует order_id в задаче image_with_text_and_button {task_id}")
                            await update_outbox_task_status(task_id, 'failed')
                            continue

                        logging.info(f"🔘 Обрабатываю outbox задание типа 'image_with_text_and_button'")

                        logging.info(f"🔘 Task data: {task}")

                        logging.info(f"🔘 Создаю кнопку: text='{button_text}', callback='{button_callback}'")

                        logging.info(f"🔘 Полученный текст: '{text}'")

                        

                        # Проверяем тип заказа и статус

                        order = await get_order(order_id)

                        is_song_demo = False

                        is_book_demo = False

                        is_book_draft = False

                        is_song_draft = False

                        is_book_final = False

                        

                        if order and order.get('order_data'):

                            import json

                            try:

                                order_data = json.loads(order.get('order_data', '{}')) if order and order.get('order_data') else {}

                                product = order_data.get('product', '')

                                order_status = order.get('status', '')

                                

                                # Проверяем, является ли это демо-файлом для песни
                                logging.info(f"🔍 ПРОВЕРКА ПЕСНИ: product='{product}', order_status='{order_status}'")

                                if product == 'Песня' and order_status in ['waiting_manager', 'demo_content']:
                                    logging.info(f"✅ НАЙДЕНА ПЕСНЯ! Создаем is_song_demo=True для заказа {order_id}")
                                    is_song_demo = True

                                    # Обновляем статус заказа
                                    logging.info(f"🔄 Обновляем статус заказа {order_id} с '{order_status}' на 'demo_sent'")
                                    await update_order_status(order_id, "demo_sent")
                                    logging.info(f"✅ Статус заказа {order_id} обновлен на 'demo_sent'")

                                

                                # Проверяем тип контента по тексту сообщения (приоритет)

                                logging.info(f"🔍 Проверяем тип контента: product={product}, order_status={order_status}")

                                if product == 'Книга':

                                    if 'демо-контент' in text.lower() or 'примеры оформления' in text.lower() or any(keyword in text.lower() for keyword in ['демо', 'demo', 'пробные страницы', 'образцы']):

                                        is_book_demo = True

                                        logging.info(f"📖 Обнаружен демо-контент книги по тексту для заказа {order_id}")

                                        # Обновляем статус заказа

                                        await update_order_status(order_id, "demo_sent")

                                    elif 'черновик' in text.lower() or 'внимательно просмотрите' in text.lower():

                                        is_book_draft = True

                                        logging.info(f"📖 Обнаружен черновик книги по тексту для заказа {order_id}")

                                        logging.info(f"📖 Продукт: {product}, Статус: {order_status}")

                                    # Если по тексту не определили, проверяем по callback_data (ПРИОРИТЕТ)

                                    elif button_callback == "continue_after_demo":

                                        is_book_demo = True

                                        logging.info(f"📖 Обнаружен демо-контент книги по callback_data для заказа {order_id}")

                                        # Обновляем статус заказа

                                        await update_order_status(order_id, "demo_sent")

                                    elif button_callback in ["book_draft_ok", "book_draft_edit"]:

                                        is_book_draft = True

                                        logging.info(f"📖 Обнаружен черновик книги по callback_data для заказа {order_id}")

                                        logging.info(f"📖 Продукт: {product}, Статус: {order_status}")

                                    # Если по callback_data не определили, проверяем по статусу

                                    elif order_status in ['questions_completed', 'waiting_manager', 'demo_sent', 'demo_content']:

                                        is_book_demo = True

                                        logging.info(f"📖 Обнаружен демо-контент книги по статусу для заказа {order_id}")

                                        logging.info(f"📖 Статус заказа: {order_status}")

                                        # Обновляем статус заказа

                                        await update_order_status(order_id, "demo_sent")

                                    elif order_status in ['waiting_draft', 'draft_sent', 'editing']:

                                        is_book_draft = True

                                        logging.info(f"📖 Обнаружен черновик книги по статусу для заказа {order_id}")

                                        logging.info(f"📖 Продукт: {product}, Статус: {order_status}")

                                    elif order_status == 'ready':

                                        is_book_final = True

                                        logging.info(f"📚 Обнаружена финальная версия книги по статусу для заказа {order_id}")

                                        logging.info(f"📚 Продукт: {product}, Статус: {order_status}")

                                        logging.info(f"📚 Финальная версия книги - пропускаем повторную отправку")

                                    else:

                                        logging.info(f"🔍 Проверка типа контента: продукт={product}, статус={order_status}, callback={button_callback}, текст={text[:50]}...")

                                elif product == 'Песня':

                                    # Проверяем демо песни по callback_data

                                    if button_callback == "continue_after_demo":

                                        is_song_demo = True

                                        logging.info(f"🎵 Обнаружено демо песни по callback_data для заказа {order_id}")

                                        # Обновляем статус заказа

                                        await update_order_status(order_id, "demo_sent")

                                    # Проверяем черновик песни по callback_data

                                    elif button_callback == "song_draft_ok":

                                        is_song_draft = True

                                        logging.info(f"🎵 Обнаружен черновик песни по callback_data для заказа {order_id}")

                                    # Проверяем по статусу

                                    elif order_status in ['waiting_draft', 'editing', 'draft_sent', 'prefinal_sent']:

                                        is_song_draft = True

                                        logging.info(f"🎵 Обнаружен черновик песни по статусу для заказа {order_id}")

                                    # Проверяем демо по статусу

                                    elif order_status in ['paid', 'demo_sent']:

                                        is_song_demo = True

                                        logging.info(f"🎵 Обнаружено демо песни по статусу для заказа {order_id}")

                                    else:

                                        logging.info(f"🔍 Проверка типа контента для песни: статус={order_status}, callback={button_callback}")

                            except (json.JSONDecodeError, KeyError):
                                logging.error(f"❌ Ошибка парсинга JSON в image_with_text_and_button")
                        
                        # ПРИНУДИТЕЛЬНАЯ ЛОГИКА: если ничего не определилось - делаем демо
                        if not any([is_song_demo, is_book_demo, is_book_draft, is_song_draft, is_book_final]):
                            if order:
                                try:
                                    order_data = json.loads(order.get('order_data', '{}')) if order.get('order_data') else {}
                                    product = order_data.get('product', '')
                                    logging.info(f"🔧 ПРИНУДИТЕЛЬНАЯ ЛОГИКА: продукт={product}, ничего не определилось")
                                    if product == 'Книга':
                                        is_book_demo = True
                                        logging.info(f"🔧 ПРИНУДИТЕЛЬНО: is_book_demo=True (резерв)")
                                    elif product == 'Песня':
                                        is_song_demo = True
                                        logging.info(f"🔧 ПРИНУДИТЕЛЬНО: is_song_demo=True (резерв)")
                                except Exception as e:
                                    logging.error(f"❌ Ошибка принудительной логики: {e}")
                            else:
                                # Если заказ не найден, но есть файл - делаем книга демо по умолчанию
                                logging.info(f"🔧 ЗАКАЗ НЕ НАЙДЕН - делаем book_demo по умолчанию для task_id {task_id}")
                                is_book_demo = True
                        
                        

                        # ЛОГИРУЕМ ОКОНЧАТЕЛЬНЫЙ ВЫБОР ТИПА
                        logging.info(f"📋 ФИНАЛЬНЫЙ ТИП для task_id {task_id}:")
                        logging.info(f"📋 - is_song_demo: {is_song_demo}")
                        logging.info(f"📋 - is_book_demo: {is_book_demo}")
                        logging.info(f"📋 - is_book_draft: {is_book_draft}")
                        logging.info(f"📋 - is_song_draft: {is_song_draft}")
                        logging.info(f"📋 - is_book_final: {is_book_final}")
                        
                        # Отправляем файл в зависимости от типа
                        input_file = FSInputFile(content)

                        

                        # Логируем тип файла для диагностики

                        logging.info(f"📤 ДЕМО-КОНТЕНТ: file_type='{file_type}', is_book_demo={is_book_demo}")

                        

                        # Создаем клавиатуру в зависимости от типа заказа

                        logging.info(f"🔍 ФИНАЛЬНАЯ ПРОВЕРКА: is_book_demo={is_book_demo}, is_book_draft={is_book_draft}, is_song_draft={is_song_draft}, is_book_final={is_book_final}")

                        if is_book_final:

                            # Для финальной версии книги - НЕ отправляем файл повторно, удаляем задачу из outbox

                            logging.info(f"📚 Финальная версия книги уже отправлена менеджером, пропускаем повторную отправку")

                            logging.info(f"📚 Задача {task_id} удалена из outbox без отправки файла")

                            await update_outbox_task_status(task_id, 'sent')

                            continue

                        elif is_book_demo:

                            # Для демо-контента книги - кнопка перехода к оплате

                            keyboard = InlineKeyboardMarkup(inline_keyboard=[

                                [InlineKeyboardButton(text="Узнать цену", callback_data="continue_after_demo")]

                            ])

                            # ПРИНУДИТЕЛЬНО заменяем текст на правильный для демо-контента

                            full_text = "Пробные страницы вашей книги готовы ☑️\n" + \
                                       "Мы старались, чтобы они были тёплыми и живыми.\n\n" + \
                                       "Но впереди ещё больше — иллюстратор вдохновился вашей историей и собрал десятки сюжетов для полной версии книги."

                            logging.info(f"🔧 ПРИНУДИТЕЛЬНО заменен текст на демо-контент для заказа {task.get('order_id', 'неизвестно')}")

                            logging.info(f"🔧 Исходный текст был: {comment}")

                        elif is_song_demo:

                            # Для демо-аудио песни - кнопка перехода к оплате

                            keyboard = InlineKeyboardMarkup(inline_keyboard=[

                                [InlineKeyboardButton(text="Узнать цену", callback_data="continue_after_demo")]

                            ])

                            # ПРИНУДИТЕЛЬНО заменяем текст на правильный для демо-аудио песни

                            full_text = "Спасибо за ожидание ✨\nДемо-версия твоей песни готова 💌\nМы собрали её первые ноты с теплом и уже знаем, как превратить их в полную мелодию, которая тронет до мурашек.\n\nЧтобы создать по-настоящему авторскую историю с твоими деталями, моментами и чувствами, нам нужно чуть больше информации 🧩\n\nТвоя история достойна того, чтобы зазвучать полностью и стать запоминающимся подарком для тебя и получателя ❤️‍🔥"

                            logging.info(f"🔧 ПРИНУДИТЕЛЬНО заменен текст на демо-аудио песни для заказа {order_id or 'неизвестно'}")

                            logging.info(f"🔧 Исходный текст был: {comment}")

                        elif is_book_draft:

                            # Для черновика книги - две кнопки (как в правильных путях)

                            logging.info(f"🔘 Создаю кнопки для черновика книги: 'book_draft_edit' и 'book_draft_ok'")

                            keyboard = InlineKeyboardMarkup(inline_keyboard=[

                            [InlineKeyboardButton(text="Все супер", callback_data="book_draft_ok")],

                            [InlineKeyboardButton(text="Внести правки", callback_data="book_draft_edit")]

                            ])

                            

                            # Добавляем дополнительный текст для черновика книги (как в правильных путях)

                            additional_text = "\n\nВот они — страницы твоей книги 📖\n"

                            additional_text += "Мы вложили в них много тепла и переживаем не меньше тебя. Надеемся, они тронут твоё сердце 💕\n\n"

                            additional_text += "Если тебе всё нравится — жми \"Всё супер\".\n"

                            additional_text += "Если хочешь внести правки — нажми \"Внести правки\"."

                            full_text = text + additional_text

                            logging.info(f"📝 Текст для черновика книги: {full_text[:100]}...")

                            

                            # Обновляем статус заказа ТОЛЬКО если это действительно черновик

                            # Проверяем, что текст содержит ключевые слова черновика

                            if any(keyword in text.lower() for keyword in ['черновик', 'внимательно просмотрите', 'готов', 'готово']):

                                await update_order_status(order_id, "draft_sent")

                                logging.info(f"📋 Статус заказа {order_id} изменен на draft_sent")

                            else:

                                logging.info(f"📋 Текстовое сообщение отправлено без изменения статуса (не черновик)")

                            logging.info(f"✅ Черновик книги отправлен с кнопками успешно")

                        elif is_song_draft:

                            # Для черновика песни - две кнопки

                            logging.info(f"🔘 Создаю кнопки для черновика песни: 'song_draft_edit' и 'song_draft_ok'")

                            keyboard = InlineKeyboardMarkup(inline_keyboard=[

                            [InlineKeyboardButton(text="Все нравится, отличная песня", callback_data="song_draft_ok")],

                            [InlineKeyboardButton(text="Обратная связь", callback_data="song_draft_edit")]

                            ])

                            

                            # Добавляем дополнительный текст для черновика песни

                            additional_text = "\n\n🎉 Вот она - финальная версия твоей песни ❤️\n\n"

                            additional_text += "Мы вложили в эту песню много любви и переживаем не меньше тебя. Надеемся, она тронет до мурашек 🥹"

                            full_text = text + additional_text

                            logging.info(f"📝 Текст для черновика песни: {full_text[:100]}...")

                        else:

                            # Для остальных случаев - одна кнопка

                            logging.info(f"🔘 Создаю обычную кнопку: text='{button_text}', callback='{button_callback}'")

                            

                            # ПРОСТАЯ ПРОВЕРКА: если callback = "continue_after_demo", то это демо-контент

                            if button_callback == "continue_after_demo":

                                # Проверяем тип продукта для правильного текста

                                try:

                                    order = await get_order(order_id)

                                    if order and order.get('order_data'):

                                        order_data = json.loads(order.get('order_data', '{}')) if order and order.get('order_data') else {}

                                        product = order_data.get('product', '')

                                        if product == 'Песня':

                                            full_text = "Спасибо за ожидание ✨\nДемо-версия твоей песни готова 💌\nМы собрали её первые ноты с теплом и уже знаем, как превратить их в полную мелодию, которая тронет до мурашек.\n\nЧтобы создать по-настоящему авторскую историю с твоими деталями, моментами и чувствами, нам нужно чуть больше информации 🧩\n\nТвоя история достойна того, чтобы зазвучать полностью и стать запоминающимся подарком для тебя и получателя ❤️‍🔥"

                                            logging.info(f"🔧 Исправлен текст для демо-аудио песни")

                                        else:

                                            full_text = "Пробные страницы вашей книги готовы ☑️\n" + \
                                                       "Мы старались, чтобы они были тёплыми и живыми.\n\n" + \
                                                       "Но впереди ещё больше — иллюстратор вдохновился вашей историей и собрал десятки сюжетов для полной версии книги."

                                            logging.info(f"🔧 Исправлен текст для демо-контента книги")

                                    else:

                                        full_text = "Пробные страницы вашей книги готовы ☑️\n" + \
                                                   "Мы старались, чтобы они были тёплыми и живыми.\n\n" + \
                                                   "Но впереди ещё больше — иллюстратор вдохновился вашей историей и собрал десятки сюжетов для полной версии книги."

                                        logging.info(f"🔧 Исправлен текст для демо-контента (по умолчанию)")

                                except Exception as e:

                                    logging.error(f"❌ Ошибка при определении типа продукта: {e}")

                                    full_text = "Пробные страницы вашей книги готовы ☑️\n" + \
                                               "Мы старались, чтобы они были тёплыми и живыми.\n\n" + \
                                               "Но впереди ещё больше — иллюстратор вдохновился вашей историей и собрал десятки сюжетов для полной версии книги."

                                    logging.info(f"🔧 Исправлен текст для демо-контента (по умолчанию)")

                            else:

                                full_text = text

                            

                            # Проверяем тип продукта для правильного текста кнопки

                            try:

                                order = await get_order(order_id)

                                if order and order.get('order_data'):

                                    order_data = json.loads(order.get('order_data', '{}')) if order and order.get('order_data') else {}

                                    product = order_data.get('product', '')

                                    if product == 'Песня' and button_callback == "continue_after_demo":

                                        button_text = "Узнать цену"

                                        logging.info(f"🔧 Исправлен текст кнопки для песни")

                                    elif product == 'Книга' and button_callback == "continue_after_demo":

                                        button_text = "Узнать цену"

                                        logging.info(f"🔧 Исправлен текст кнопки для книги")

                            except Exception as e:

                                logging.error(f"❌ Ошибка при определении типа продукта для кнопки: {e}")

                            

                            keyboard = InlineKeyboardMarkup(inline_keyboard=[

                                [InlineKeyboardButton(text=button_text, callback_data=button_callback)]

                            ])

                        

                        if file_type in ['jpg', 'jpeg', 'png', 'image']:

                            # Проверяем существование файла

                            if not os.path.exists(content):

                                logging.error(f"❌ Файл не существует: {content}")

                                await update_outbox_task_status(task_id, 'failed')

                                continue

                            

                            # Размер файла логируем, но не блокируем отправку

                            try:

                                file_size = os.path.getsize(content) / (1024 * 1024)  # в МБ

                                logging.info(f"🔍 Размер файла {content}: {file_size:.2f} МБ")

                            except Exception as size_error:

                                logging.error(f"❌ Ошибка проверки размера файла {content}: {size_error}")

                            

                            await bot.send_photo(user_id, input_file, caption=full_text, reply_markup=keyboard)

                        elif file_type == 'mp3':

                            await bot.send_audio(user_id, input_file, caption=full_text, reply_markup=keyboard)

                        elif file_type == 'pdf':

                            # Проверяем существование файла

                            if not os.path.exists(content):

                                logging.error(f"❌ Файл не существует: {content}")

                                await update_outbox_task_status(task_id, 'failed')

                                continue

                            

                            # Логируем размер PDF файла, но не блокируем отправку
                            try:
                                file_size = os.path.getsize(content) / (1024 * 1024)  # в МБ
                                logging.info(f"🔍 Размер PDF файла {content}: {file_size:.2f} МБ")
                            except Exception as size_error:
                                logging.error(f"❌ Ошибка проверки размера PDF файла {content}: {size_error}")

                            # Отправляем PDF документ с обработкой ошибок
                            try:
                                await bot.send_document(user_id, input_file, caption=full_text, reply_markup=keyboard)
                                logging.info(f"✅ PDF документ отправлен успешно пользователю {user_id}")
                            except Exception as pdf_error:
                                error_msg = str(pdf_error)
                                logging.error(f"❌ Ошибка отправки PDF документа: {pdf_error}")
                                await update_outbox_task_status(task_id, 'failed')
                                continue

                        elif file_type == 'gif':

                            # GIF отправляем как анимацию

                            await bot.send_animation(user_id, input_file, caption=full_text, reply_markup=keyboard)

                            logging.info(f"🎬 GIF анимация с кнопкой отправлена пользователю {user_id}")

                        elif file_type in ['mov', 'mp4', 'avi', 'mkv', 'webm'] or file_type == 'video':

                            # Видео файлы отправляем как видео

                            logging.info(f"🎬 Отправляю видео файл: file_type='{file_type}', user_id={user_id}")

                            await bot.send_video(user_id, input_file, caption=full_text, reply_markup=keyboard)

                            logging.info(f"🎬 Видео файл ({file_type}) с кнопкой отправлен пользователю {user_id}")

                        else:

                            # Для других типов файлов отправляем как документ

                            logging.info(f"📄 Отправляю как документ: file_type='{file_type}', user_id={user_id}")

                            await bot.send_document(user_id, input_file, caption=full_text, reply_markup=keyboard)

                        

                        await update_outbox_task_status(task_id, 'sent')

                        if is_song_demo:

                            logging.info(f"✅ Демо-файл песни отправлен успешно")
                            
                            # Создаем таймер для этапа demo_received_song (Глава 3: Получение демо-версии)
                            from db import create_or_update_user_timer
                            await create_or_update_user_timer(user_id, order_id, "demo_received_song", "Песня")
                            logging.info(f"✅ Создан таймер для этапа demo_received_song (Глава 3), пользователь {user_id}, заказ {order_id}")
                            
                            # Отложенные сообщения для этапа demo_received_song управляются через новую систему шаблонов в админке

                        elif is_book_demo:

                            logging.info(f"✅ Демо-контент книги отправлен с кнопкой перехода к оплате")

                        elif is_book_draft:

                            logging.info(f"✅ Черновик книги отправлен с кнопками успешно")

                            logging.info(f"🔘 Кнопки созданы: book_draft_edit, book_draft_ok")

                        else:

                            logging.info(f"✅ Файл с кнопкой отправлен успешно")

                            logging.info(f"🔘 Кнопка создана: {button_callback}")

                    except Exception as e:

                        logging.error(f"Ошибка отправки image_with_text_and_button {task_id}: {e}")

                        await update_outbox_task_status(task_id, 'failed')

                elif type_ == 'covers_selection':

                    try:

                        # Отправляем каждую обложку отдельно с кнопкой перехода к следующему шагу

                        logging.info(f"🎨 Обрабатываю outbox задание типа 'covers_selection'")

                        

                        # Получаем все обложки

                        from db import get_cover_templates

                        cover_templates = await get_cover_templates()

                        logging.info(f"🔍 ОТЛАДКА: Получено {len(cover_templates) if cover_templates else 0} обложек")

                        

                        if not cover_templates:

                            logging.warning(f"⚠️ Нет обложек в базе данных")

                            await bot.send_message(user_id, "❌ К сожалению, обложки временно недоступны")

                        await update_outbox_task_status(task_id, 'failed')

                        continue

                        

                        # Отправляем каждую обложку отдельно с кнопкой

                        for i, template in enumerate(cover_templates[:5]):  # Максимум 5 обложек

                            try:

                                covers_dir = "covers"
                                
                                # Создаем папку covers, если её нет
                                os.makedirs(covers_dir, exist_ok=True)

                                file_path = os.path.join(covers_dir, template['filename'])

                                

                                if os.path.exists(file_path):

                                    logging.info(f"✅ Файл обложки найден: {file_path}")

                                                                        # Создаем кнопку для выбора обложки

                                    keyboard = InlineKeyboardMarkup(inline_keyboard=[

                                        [InlineKeyboardButton(text="Выбрать эту обложку", callback_data=f"choose_cover_template_{template['id']}")]

                                    ])

                                    

                                    # Отправляем обложку с описанием и кнопкой

                                    caption = f"📖 <b>{template['name']}</b>\n\n"

                                    if template.get('category'):

                                        caption += f"Категория: {template['category']}\n"

                                    caption += f"Обложка #{i+1} из {len(cover_templates[:5])}"

                                    

                                    await bot.send_photo(

                                        user_id,

                                        photo=FSInputFile(file_path),

                                        caption=caption,

                                        reply_markup=keyboard,

                                        parse_mode="HTML"

                                    )
                                    
                                    logging.info(f"✅ Обложка {template['name']} отправлена пользователю {user_id}")

                                else:

                                    logging.warning(f"⚠️ Файл обложки не найден: {file_path}")

                            except Exception as e:

                                logging.error(f"❌ Ошибка загрузки обложки {template['name']}: {e}")

                        

                        await update_outbox_task_status(task_id, 'sent')

                        logging.info(f"✅ Отправлено {len(cover_templates[:5])} обложек по отдельности")

                    except Exception as e:

                        logging.error(f"Ошибка отправки covers_selection {task_id}: {e}")

                        await update_outbox_task_status(task_id, 'failed')

                elif type_ == 'page_selection':

                    try:

                        # Отправляем страницу с кнопкой выбора

                        logging.info(f"📖 Обрабатываю outbox задание типа 'page_selection'")

                        

                        file_type = (task.get('file_type') or '').lower()

                        comment = task.get('comment') or ''

                        button_text = task.get('button_text') or '✅ Выбрать'

                        button_callback = task.get('button_callback') or 'choose_page'

                        

                        # Устанавливаем правильное состояние пользователя для выбора страниц

                        try:

                            from aiogram.fsm.context import FSMContext

                            from aiogram.fsm.storage.memory import MemoryStorage

                            

                            # Получаем контекст состояния для пользователя

                            storage = dp.storage

                            state_key = f"{user_id}:{user_id}"

                            

                            # Создаем FSMContext для пользователя

                            from aiogram.fsm.storage.base import StorageKey

                            storage_key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)

                            user_state = FSMContext(storage=storage, key=storage_key)

                            

                            # Устанавливаем состояние выбора страниц

                            await user_state.set_state(BookFinalStates.choosing_pages)

                            

                            # Инициализируем данные заказа если их нет

                            current_data = await user_state.get_data()

                            order_id = task.get('order_id')

                            if order_id and 'order_id' not in current_data:

                                await user_state.update_data(order_id=order_id)

                            

                            # ОЧИЩАЕМ данные о выбранных страницах при восстановлении состояния

                            # чтобы пользователь мог заново выбрать страницы

                            if 'selected_pages' in current_data:

                                await user_state.update_data(selected_pages=[])

                                logging.info(f"🧹 Очищены выбранные страницы для пользователя {user_id}")

                            

                            # Очищаем флаги состояния

                            await user_state.update_data(

                                minimum_processed=False,

                                continue_message_sent=False

                            )

                            

                            logging.info(f"✅ Установлено состояние choosing_pages для пользователя {user_id}")

                        except Exception as state_error:

                            logging.error(f"❌ Ошибка установки состояния: {state_error}")

                        

                        # Создаем клавиатуру

                        keyboard = InlineKeyboardMarkup(inline_keyboard=[

                            [InlineKeyboardButton(text=button_text, callback_data=button_callback)]

                        ])

                        

                        # Отправляем страницу

                        if file_type in ['jpg', 'jpeg', 'png', 'image']:

                            # Проверяем существование файла

                            if not os.path.exists(content):

                                logging.error(f"❌ Файл не существует: {content}")

                                await update_outbox_task_status(task_id, 'failed')

                                continue

                            

                            # Проверяем текущее состояние FSM - если пользователь уже перешел к следующему этапу

                            try:

                                current_state = await user_state.get_state()

                                if current_state and current_state != "BookFinalStates:choosing_pages":

                                    logging.info(f"⚠️ Пользователь {user_id} уже перешел к следующему этапу, пропускаем отправку страницы")

                                    await update_outbox_task_status(task_id, 'sent')

                                    continue

                            except Exception as state_check_error:

                                logging.error(f"❌ Ошибка проверки состояния: {state_check_error}")

                            

                            input_file = FSInputFile(content)

                            caption = f"📖 {comment}\n\nЕсли этот сюжет про вас, то выбери его:"

                            

                            await bot.send_photo(user_id, input_file, caption=caption, reply_markup=keyboard)

                            logging.info(f"✅ Страница отправлена с кнопкой выбора")

                        else:

                            logging.error(f"❌ Неподдерживаемый тип файла для page_selection: {file_type}")

                        await update_outbox_task_status(task_id, 'failed')

                        continue

                        

                        await update_outbox_task_status(task_id, 'sent')

                    except Exception as e:

                        logging.error(f"Ошибка отправки page_selection {task_id}: {e}")

                        await update_outbox_task_status(task_id, 'failed')

                elif type_ == 'text_with_buttons':
                    
                    try:
                        # Отправляем текстовое сообщение с кнопками
                        logging.info(f"📝 OUTBOX: Обрабатываю text_with_buttons для user_id={user_id}, task_id={task_id}, content='{text[:50]}...'")
                        
                        text = content
                        button_text = task.get('button_text', '')
                        button_callback = task.get('button_callback', '')
                        
                        # Парсим кнопки (разделенные |)
                        button_texts = button_text.split('|') if button_text else []
                        button_callbacks = button_callback.split('|') if button_callback else []
                        
                        if button_texts and button_callbacks and len(button_texts) == len(button_callbacks):
                            # Создаем клавиатуру
                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text=btn_text.strip(), callback_data=btn_callback.strip())]
                                for btn_text, btn_callback in zip(button_texts, button_callbacks)
                            ])
                            
                            await bot.send_message(user_id, text, parse_mode="HTML", reply_markup=keyboard)
                        else:
                            # Если кнопки не настроены правильно, отправляем без них
                            await bot.send_message(user_id, text, parse_mode="HTML")
                        
                        await update_outbox_task_status(task_id, 'sent')
                        logging.info(f"✅ Текстовое сообщение с кнопками отправлено успешно")
                        
                    except Exception as e:
                        logging.error(f"Ошибка отправки text_with_buttons {task_id}: {e}")
                        await update_outbox_task_status(task_id, 'failed')

                elif type_ == 'text':

                    try:

                        # Отправляем текстовое сообщение

                        logging.info(f"📝 Обрабатываю outbox задание типа 'text'")

                        

                        # Если это инструкции для выбора страниц, устанавливаем состояние

                        comment = task.get('comment') or ''

                        if 'выбор страниц' in comment.lower() or 'выберите страницы' in content.lower():

                            try:

                                from aiogram.fsm.context import FSMContext

                                

                                # Создаем FSMContext для пользователя

                                from aiogram.fsm.storage.base import StorageKey

                                storage_key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)

                                user_state = FSMContext(storage=dp.storage, key=storage_key)

                                

                                # Устанавливаем состояние выбора страниц

                                await user_state.set_state(BookFinalStates.choosing_pages)

                                

                                # Инициализируем данные заказа

                                order_id = task.get('order_id')

                                if order_id:

                                    await user_state.update_data(order_id=order_id)

                                

                                logging.info(f"✅ Установлено состояние choosing_pages для инструкций пользователю {user_id}")

                            except Exception as state_error:

                                logging.error(f"❌ Ошибка установки состояния для инструкций: {state_error}")

                        

                        await bot.send_message(user_id, content, parse_mode="HTML")

                        logging.info(f"✅ Текстовое сообщение отправлено")

                        

                        await update_outbox_task_status(task_id, 'sent')

                    except Exception as e:

                        logging.error(f"Ошибка отправки text {task_id}: {e}")

                        await update_outbox_task_status(task_id, 'failed')

                elif type_ == 'manager_notification':

                    # Уведомления для менеджера - пропускаем

                    await update_outbox_task_status(task_id, 'sent')

                elif type_ == 'set_state':

                    try:

                        logging.info(f"🔄 Устанавливаем состояние для пользователя {user_id}: {content}")

                        # Получаем состояние пользователя
                        from aiogram.fsm.storage.base import StorageKey
                        storage_key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
                        
                        # Создаем контекст состояния
                        from aiogram.fsm.context import FSMContext
                        state = FSMContext(storage=storage, key=storage_key)
                        
                        # Устанавливаем состояние
                        if content == "DeliveryStates.waiting_for_address":
                            from aiogram.fsm.state import StatesGroup, State
                            class DeliveryStates(StatesGroup):
                                waiting_for_address = State()
                            await state.set_state(DeliveryStates.waiting_for_address)
                        else:
                            # Для других состояний можно добавить обработку
                            logging.warning(f"⚠️ Неизвестное состояние для установки: {content}")
                        
                        await update_outbox_task_status(task_id, 'sent')
                        logging.info(f"✅ Состояние установлено успешно")

                    except Exception as e:
                        logging.error(f"❌ Ошибка установки состояния {task_id}: {e}")
                        await update_outbox_task_status(task_id, 'failed')

                else:

                    await update_outbox_task_status(task_id, 'failed')

        except Exception as e:

            error_msg = str(e)
            
            # Безопасное получение task_id и user_id
            safe_task_id = locals().get('task_id', 'неизвестно')
            safe_user_id = locals().get('user_id', 'неизвестно')

            logging.error(f"Ошибка отправки задания {safe_task_id}: {error_msg}")
            
            # Добавляем полный traceback для диагностики
            import traceback
            logging.error(f"🔍 ПОЛНЫЙ TRACEBACK ОШИБКИ: {traceback.format_exc()}")

            

            # Определяем тип ошибки для лучшей диагностики

            if "Forbidden" in error_msg or "bot was blocked" in error_msg.lower():

                logging.error(f"Пользователь {safe_user_id} заблокировал бота")

                # Для заблокированных пользователей помечаем задачу как failed и не повторяем
                if safe_task_id != 'неизвестно':
                    await update_outbox_task_status(safe_task_id, 'failed')

                # Добавляем комментарий о том, что пользователь заблокировал бота

                # Добавляем уведомление менеджеру только если есть данные задачи
                if 'task' in locals() and task:
                    await add_outbox_task(
                        order_id=task.get('order_id'),
                        user_id=0,  # Системное сообщение
                        type_="manager_notification",
                        content=f"⚠️ ВНИМАНИЕ: Пользователь {safe_user_id} заблокировал бота. Демо-контент не доставлен. Необходимо связаться с пользователем другим способом."
                    )

            elif "chat not found" in error_msg.lower():

                logging.error(f"Чат с пользователем {safe_user_id} не найден (возможно, пользователь не взаимодействовал с ботом)")

                if safe_task_id != 'неизвестно':
                    await update_outbox_task_status(safe_task_id, 'failed')

            elif "user not found" in error_msg.lower():

                logging.error(f"Пользователь {safe_user_id} не найден в Telegram")

                if safe_task_id != 'неизвестно':
                    await update_outbox_task_status(safe_task_id, 'failed')

            else:

                # Для других ошибок оставляем задачу в pending для повторной попытки

                logging.error(f"Неизвестная ошибка для пользователя {safe_user_id}: {error_msg}")

                if safe_task_id != 'неизвестно':
                    await update_outbox_task_status(safe_task_id, 'pending')

        except Exception as e:
            logging.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА В PROCESS_OUTBOX_TASKS: {e}")
            import traceback
            logging.error(f"❌ ПОЛНЫЙ TRACEBACK: {traceback.format_exc()}")

        await asyncio.sleep(2)  # Уменьшаем интервал для более быстрой обработки задач



async def compress_image(image_path: str, max_size_mb: float = 5.0, quality: int = 85):

    """

    Сжимает изображение до указанного размера

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

                logging.info(f"📸 Файл {image_path} уже подходящего размера ({file_size:.2f} МБ)")

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

                logging.info(f"📸 Изображение сжато: {file_size:.2f} МБ → {compressed_size:.2f} МБ")

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

                    logging.info(f"📸 Изображение сжато с качеством {quality}: {file_size:.2f} МБ → {compressed_size:.2f} МБ")

                else:

                    logging.warning(f"⚠️ Не удалось сжать изображение {image_path} до {max_size_mb} МБ")

                    

    except ImportError:

        logging.warning("⚠️ PIL не установлен, сжатие изображений недоступно")

    except Exception as e:

        logging.error(f"❌ Ошибка сжатия изображения {image_path}: {e}")



async def download_and_save_photo(bot: Bot, file_id: str, save_dir: str, filename: str) -> str:

    file = await bot.get_file(file_id)

    file_path = file.file_path

    dest_path = os.path.join(save_dir, filename)

    await bot.download_file(file_path, dest_path)

    

    # Сжимаем фотографию, если это изображение

    try:

        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')):

            await compress_image(dest_path)

            logging.info(f"✅ Фотография сжата: {filename}")

    except Exception as e:

        logging.error(f"❌ Ошибка сжатия фотографии {filename}: {e}")

    

    return filename



# Функция для автоматических напоминаний об оплате

async def send_payment_reminders(bot: Bot):

    """Отправляет напоминания об оплате через 24 часа"""

    while True:

        try:

            # Получаем заказы, которые ожидают оплаты более 1 минуты (для тестирования)

            from db import aiosqlite, DB_PATH

            import datetime

            

            async with aiosqlite.connect(DB_PATH) as db:

                # Заказы со статусом "waiting_payment" старше 1 минуты (для тестирования)

                one_minute_ago = datetime.now() - timedelta(minutes=1)

                cursor = await db.execute('''

                    SELECT id, user_id, order_data FROM orders 

                    WHERE status = 'waiting_payment' 

                    AND updated_at < ?

                ''', (one_minute_ago,))

                orders = await cursor.fetchall()

                

                for order_id, user_id, order_data in orders:

                    try:

                        # Первое напоминание

                        await bot.send_message(

                            user_id,

                            "Возможно, цена вас смутила? Мы можем предложить другие варианты — напишите нам."

                        )

                        

                        # Обновляем статус заказа

                        await db.execute(

                            'UPDATE orders SET status = ? WHERE id = ?',

                            ('reminder_sent', order_id)

                        )

                        await db.commit()

                        

                        # Второе напоминание через 1 минуту (для тестирования)

                        await asyncio.sleep(60)  # 1 минута для тестирования

                        await bot.send_message(

                            user_id,

                            "Готовы сделать книгу проще, но не менее искренней. Дайте знать, если вам это интересно."

                        )

                        

                        # Обновляем статус заказа

                        await db.execute(

                            'UPDATE orders SET status = ? WHERE id = ?',

                            ('final_reminder_sent', order_id)

                        )

                        await db.commit()

                        

                    except Exception as e:

                        logging.error(f"Ошибка отправки напоминания для заказа {order_id}: {e}")

                        

        except Exception as e:

            logging.error(f"Ошибка в системе напоминаний: {e}")

        

        # Проверяем каждые 30 секунд (для тестирования)

        await asyncio.sleep(30)  # 30 секунд для тестирования



@dp.callback_query(F.data == "continue_creation")

async def continue_creation_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    # Получаем актуальные цены из базы данных

    try:

        ebook_price = await get_product_price_async("Книга", "📄 Электронная книга")

        combo_price = await get_product_price_async("Книга", "📦 Печатная версия")

    except:

        # Если не удалось получить цены из БД, используем резервные

        ebook_price = 1990

        combo_price = 7639

    

    # Переходим к выбору формата и оплаты

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text=f"Печатная версия — {combo_price} рублей", callback_data="format_combo")]

    ])

    

    await safe_edit_message(

        callback.message,

        "Отлично! Теперь выберите формат вашей книги:",

        reply_markup=keyboard

    )

    

    await log_state(callback.message, state)



async def process_message_templates(bot: Bot):

    """Обрабатывает шаблоны сообщений (новая система)"""

    logging.info("🔄 Запущена фоновая задача process_message_templates")

    

    while True:

        try:

            from db import get_message_templates, get_users_on_step, is_message_sent_to_user, log_message_sent, get_order

            # Получаем все активные шаблоны

            templates = await get_message_templates()

            

            if not templates:
                continue

                logging.info(f"🔍 Найдено {len(templates)} активных шаблонов сообщений")

            

            for template in templates:

                order_step = template['order_step']

                delay_minutes = template['delay_minutes']

                template_id = template['id']

                message_type = template['message_type']

                content = template['content']

                

                logging.info(f"🔍 Обрабатываю шаблон {template_id} для шага '{order_step}' с задержкой {delay_minutes} мин, тип: {message_type}")

                

                # Получаем всех пользователей на этом шаге с нужной задержкой

                users = await get_users_on_step(order_step, delay_minutes)

                if users:
                    logging.info(f"🔍 Найдено {len(users)} пользователей для шаблона {template_id} ({message_type})")
                    # Логируем детали первых нескольких пользователей для отладки
                    for i, user in enumerate(users[:3]):
                        order_id = user['order_id']
                        order = await get_order(order_id)
                        if order:
                            order_status = order.get('status')
                            order_data = order.get('order_data', {})
                            if isinstance(order_data, str):
                                import json
                                order_data = json.loads(order_data)
                            product = order_data.get('product', '')
                            logging.info(f"🔍 Пользователь {i+1}: order_id={order_id}, status={order_status}, product={product}")
                else:
                    logging.info(f"ℹ️ Нет пользователей для шаблона {template_id} ({message_type}) на шаге {order_step}")
                    continue
                
                # Фильтруем только пользователей, которые действительно находятся на этапе заполнения анкеты
                from datetime import datetime, timedelta
                cutoff_time = datetime.now() - timedelta(hours=24)
                
                eligible_users = []
                for user_data in users:
                    order_id = user_data['order_id']
                    order = await get_order(order_id)
                    if order and order.get('created_at'):
                        order_created = datetime.fromisoformat(order['created_at'].replace('Z', '+00:00'))
                        # Проверяем, что заказ создан не более 24 часов назад
                        if order_created > cutoff_time:
                            # Проверяем, что пользователь действительно находится на этапе заполнения анкеты
                            order_status = order.get('status')
                            if order_status == 'collecting_facts':
                                # Проверяем тип продукта
                                order_data = order.get('order_data', {})
                                if isinstance(order_data, str):
                                    import json
                                    order_data = json.loads(order_data)
                                product = order_data.get('product', '')
                                
                                # Проверяем соответствие типа продукта и шага
                                if order_step == "song_collecting_facts" and product == "Песня":
                                    # Проверяем, что прошло достаточно времени с момента перехода в collecting_facts
                                    order_updated = datetime.fromisoformat(order.get('updated_at', order['created_at']).replace('Z', '+00:00'))
                                    time_since_update = datetime.now() - order_updated
                                    required_delay = timedelta(minutes=delay_minutes)
                                    
                                    if time_since_update >= required_delay:
                                        eligible_users.append(user_data)
                                elif order_step == "book_collecting_facts" and product == "Книга":
                                    # Проверяем, что прошло достаточно времени с момента перехода в collecting_facts
                                    order_updated = datetime.fromisoformat(order.get('updated_at', order['created_at']).replace('Z', '+00:00'))
                                    time_since_update = datetime.now() - order_updated
                                    required_delay = timedelta(minutes=delay_minutes)
                                    
                                    if time_since_update >= required_delay:
                                        eligible_users.append(user_data)
                
                if not eligible_users:
                    logging.info(f"ℹ️ Нет подходящих пользователей для шаблона {template_id} ({message_type})")
                    continue
                    
                logging.info(f"🔍 Обрабатываем {len(eligible_users)} подходящих пользователей из {len(users)} для шаблона {template_id} ({message_type})")
                users = eligible_users

                sent_count = 0
                skipped_count = 0

                for user_data in users:

                    user_id = user_data['user_id']

                    order_id = user_data['order_id']

                    

                    # Проверяем, не было ли уже отправлено это сообщение

                    if await is_message_sent_to_user(template_id, user_id, order_id):

                        skipped_count += 1
                        continue
                    
                    # order уже получен и проверен выше
                    
                    # Пропускаем пользователей, которые заблокировали бота (проверяем по последней активности)
                    # Это поможет избежать ошибок "chat not found"
                    try:
                        # Пробуем получить информацию о чате
                        chat = await bot.get_chat(user_id)
                        if not chat:
                            skipped_count += 1
                            continue
                    except Exception:
                        # Если не можем получить чат, пропускаем пользователя
                        skipped_count += 1
                        continue

                    

                    # order уже получен и проверен выше
                    order_status = order.get('status')

                    

                    # Если заказ уже оплачен, не отправляем напоминания об оплате

                    if message_type in ['payment_reminder', 'final_reminder', 'payment_reminder_24h', 'payment_reminder_48h'] and order_status in ['paid', 'upsell_paid', 'ready', 'delivered', 'completed']:

                        skipped_count += 1
                        continue

                    

                    try:

                        # Отправляем сообщение пользователю

                        await bot.send_message(user_id, content)

                        # logging.info(f"✅ Отправлено сообщение из шаблона {template_id} пользователю {user_id}")

                        sent_count += 1

                        # Записываем факт отправки

                        await log_message_sent(template_id, user_id, order_id)

                        

                    except Exception as e:
                        error_msg = str(e)
                        
                        # Пропускаем ошибки "chat not found" (пользователь заблокировал бота)
                        if "chat not found" in error_msg.lower():
                            skipped_count += 1
                            # Все равно записываем как отправленное, чтобы не повторять
                            await log_message_sent(template_id, user_id, order_id)
                        else:
                            logging.error(f"❌ Ошибка отправки сообщения из шаблона {template_id} пользователю {user_id}: {e}")
                            skipped_count += 1

                # Выводим итоговую статистику для шаблона
                if users:
                    logging.info(f"📊 Шаблон {template_id} ({message_type}): отправлено {sent_count}, пропущено {skipped_count} из {len(users)} пользователей")
            
            
            # Обрабатываем старые отложенные сообщения (для совместимости)
            # await process_old_delayed_messages_fixed(bot)  # Отключаем старую систему

            

        except Exception as e:

            logging.error(f"❌ Ошибка в process_message_templates: {e}")

        

        # Ждем 10 секунд перед следующей проверкой

        await asyncio.sleep(10)



async def process_timer_based_messages(bot: Bot):
    """
    Новая система обработки отложенных сообщений на основе индивидуальных таймеров
    """
    logging.info("🔄 Запущена новая система обработки сообщений по таймерам")

    while True:
        try:
            from db import get_users_ready_for_messages, is_timer_message_sent, log_timer_message_sent, get_order
            
            # Получаем пользователей, готовых для получения сообщений по таймерам
            ready_users = await get_users_ready_for_messages()
            
            if ready_users:
                logging.info(f"🔍 Найдено {len(ready_users)} готовых к отправке сообщений")
            
            for user_data in ready_users:
                timer_id = user_data['timer_id']
                user_id = user_data['user_id']
                order_id = user_data['order_id']
                template_id = user_data['template_id']
                message_type = user_data['message_type']
                content = user_data['content']
                delay_minutes = user_data['delay_minutes']
                template_name = user_data['template_name']
                
                logging.info(f"🔍 Проверяю отправку '{template_name}' (задержка {delay_minutes}м) пользователю {user_id}")
                logging.info(f"📝 Содержимое сообщения из таблицы 'message_templates' (ID: {template_id}): {content[:100]}...")
                
                # Проверяем, не было ли уже отправлено это сообщение для данного таймера
                if await is_timer_message_sent(timer_id, template_id, delay_minutes):
                    logging.info(f"ℹ️ Сообщение уже отправлено для таймера {timer_id}, шаблон {template_id}")
                    continue
                
                # Получаем данные заказа для дополнительных проверок
                order = await get_order(order_id)
                if not order:
                    logging.warning(f"Заказ {order_id} не найден для пользователя {user_id}")
                    continue
                
                # Проверяем, что заказ все еще в подходящем статусе
                order_status = order.get('status')
                logging.info(f"🔍 Статус заказа {order_id}: {order_status}, этап: {user_data['order_step']}")
                # Блокируем только полностью завершенные заказы, НЕ оплаченные!
                if order_status in ['completed', 'cancelled', 'failed', 'delivered']:
                    logging.info(f"❌ Заказ {order_id} в финальном статусе {order_status}, пропускаем сообщение")
                    continue
                
                try:
                    # Получаем файлы для этого шаблона сообщения
                    from db import get_message_template_files
                    files = await get_message_template_files(template_id)
                    
                    logging.info(f"📁 Файлы для шаблона '{template_name}' (ID: {template_id}): найдено {len(files)} файлов")
                    if files:
                        for i, file_info in enumerate(files):
                            logging.info(f"  📎 Файл {i+1}: {file_info.get('file_name', 'unknown')} ({file_info.get('file_type', 'unknown')})")
                    
                    if files:
                        # Создаем медиагруппу из всех файлов
                        media_group = await create_mixed_media_group(files, content)
                        
                        if media_group:
                            # Отправляем медиагруппу
                            await bot.send_media_group(user_id, media_group)
                            logging.info(f"✅ Отправлена медиагруппа с {len(files)} файлами '{template_name}' пользователю {user_id} (заказ {order_id})")
                        else:
                            # Если не удалось создать медиагруппу, отправляем файлы по отдельности
                            for file_info in files:
                                await send_file_by_type(
                                    bot, user_id, 
                                    file_info['file_path'], 
                                    file_info['file_type'],
                                    content if files.index(file_info) == 0 else None
                                )
                            logging.info(f"✅ Отправлены файлы по отдельности '{template_name}' пользователю {user_id} (заказ {order_id})")
                    else:
                        # Если нет файлов, отправляем только текст
                        await bot.send_message(user_id, content, parse_mode="HTML")
                        logging.info(f"✅ Отправлено сообщение '{template_name}' пользователю {user_id} (заказ {order_id})")
                    
                    # Записываем факт отправки в новую систему
                    await log_timer_message_sent(timer_id, template_id, user_id, order_id, message_type, delay_minutes)
                    
                    # Также записываем в старую систему для совместимости
                    from db import log_message_sent
                    await log_message_sent(template_id, user_id, order_id)
                    
                except Exception as e:
                    logging.error(f"❌ Ошибка отправки сообщения '{template_name}' пользователю {user_id}: {e}")
            
        except Exception as e:
            logging.error(f"❌ Ошибка в process_timer_based_messages: {e}")
        
        await asyncio.sleep(30)  # Проверяем каждые 30 секунд

async def complete_all_delayed_messages():
    """Завершает все отложенные сообщения для прошлых заказов"""
    try:
        from db import get_pending_delayed_messages, update_delayed_message_status
        
        messages = await get_pending_delayed_messages()
        
        if messages:
            logging.info(f"🔍 Найдено {len(messages)} отложенных сообщений для завершения")
            
            for message in messages:
                message_id = message['id']
                message_type = message['message_type']
                user_id = message['user_id']
                order_id = message['order_id']
                
                # Помечаем как отправленные (завершенные)
                await update_delayed_message_status(message_id, 'sent')
                logging.info(f"✅ Завершено отложенное сообщение {message_id} типа '{message_type}' для пользователя {user_id}")
            
            logging.info(f"✅ Завершено {len(messages)} отложенных сообщений")
        else:
            logging.info("🔍 Отложенных сообщений для завершения не найдено")
            
    except Exception as e:
        logging.error(f"❌ Ошибка при завершении отложенных сообщений: {e}")

async def process_old_delayed_messages_fixed(bot: Bot):
    """Обрабатывает старые отложенные сообщения (исправленная версия)"""
    
    try:
        from db import get_pending_delayed_messages, update_delayed_message_status, get_delayed_message_files, get_order, log_general_message_sent, is_general_message_sent_to_user
        
        messages = await get_pending_delayed_messages()
        
        if messages:
            logging.info(f"🔍 Найдено {len(messages)} старых отложенных сообщений для отправки")
        
        for message in messages:
            user_id = message['user_id']
            order_id = message['order_id']
            message_type = message['message_type']
            content = message['content']
            message_id = message['id']
            
            # logging.info(f"🔍 Обрабатываю отложенное сообщение {message_id} типа '{message_type}' для пользователя {user_id}")
            
            try:
                # Проверяем статус заказа перед отправкой сообщения
                order = await get_order(order_id)
                if not order:
                    logging.warning(f"Заказ {order_id} не найден, пропускаем сообщение {message_id}")
                    await update_delayed_message_status(message_id, 'failed')
                    continue

                order_status = order.get('status') if order else None
                
                # Если заказ уже оплачен, не отправляем напоминания об оплате
                if message_type in ['payment_reminder', 'final_reminder', 'payment_reminder_24h', 'payment_reminder_48h'] and order_status in ['paid', 'upsell_paid', 'ready', 'delivered', 'completed']:
                    logging.info(f"Заказ {order_id} уже оплачен (статус: {order_status}), пропускаем {message_type}")
                    await update_delayed_message_status(message_id, 'cancelled')
                    continue
                
                # Проверяем, не было ли уже отправлено это сообщение пользователю
                if await is_general_message_sent_to_user(message_id, user_id, order_id):
                    # logging.info(f"ℹ️ Сообщение {message_id} уже отправлено пользователю {user_id} (заказ {order_id})")
                    await update_delayed_message_status(message_id, 'sent')
                    continue
                
                # Дополнительная проверка: если сообщение уже в статусе 'sent', пропускаем
                if message.get('status') == 'sent':
                    # logging.info(f"ℹ️ Сообщение {message_id} уже в статусе 'sent', пропускаем")
                    continue
                
                # Получаем файлы для этого сообщения
                files = await get_delayed_message_files(message_id)
                
                if message_type == 'demo_example':
                    # Отправляем пример книги с кнопкой "Продолжить создание книги"
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    
                    # Создаем клавиатуру с кнопкой
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Узнать цену", callback_data="continue_after_demo")]
                    ])
                    
                    if files:
                        # Создаем медиагруппу из всех файлов
                        media_group = await create_mixed_media_group(files, content)
                        
                        if media_group:
                            # Отправляем медиагруппу
                            await bot.send_media_group(user_id, media_group)
                            # Отправляем кнопку отдельным сообщением после медиагруппы
                            await bot.send_message(user_id, "Готовы продолжить?", reply_markup=keyboard)
                        else:
                            # Если не удалось создать медиагруппу, отправляем файлы по отдельности
                            for file_info in files:
                                await send_file_by_type(
                                    bot, user_id, 
                                    file_info['file_path'], 
                                    file_info['file_type'],
                                    content if files.index(file_info) == 0 else None
                                )
                            # Отправляем кнопку отдельным сообщением
                            await bot.send_message(user_id, "Готовы продолжить?", reply_markup=keyboard)
                    else:
                        # Если нет файлов, отправляем только текст с кнопкой
                        await bot.send_message(user_id, content, reply_markup=keyboard)
                    
                    await update_delayed_message_status(message_id, 'sent')
                    # Записываем в лог отправку
                    await log_general_message_sent(message_id, user_id, order_id)
                    
                elif message_type.startswith('song_filling_reminder_'):
                    # Напоминания о заполнении анкеты для песни
                    logging.info(f"🎵 Отправляю напоминание о заполнении анкеты песни: {message_type}")
                    await bot.send_message(user_id, content, parse_mode="HTML")
                    await update_delayed_message_status(message_id, 'sent')
                    await log_general_message_sent(message_id, user_id, order_id)
                    
                elif message_type.startswith('song_warming_'):
                    # Прогревающие сообщения для песни
                    logging.info(f"🎵 Отправляю прогревающее сообщение для песни: {message_type}")
                    await bot.send_message(user_id, content, parse_mode="HTML")
                    await update_delayed_message_status(message_id, 'sent')
                    await log_general_message_sent(message_id, user_id, order_id)
                    
                elif message_type.startswith('waiting_demo_song_'):
                    # Напоминания об ожидании демо песни - ОТКЛЮЧЕНО (используется новая система таймеров)
                    logging.info(f"🎵 Пропускаю напоминание об ожидании демо песни (новая система таймеров): {message_type}")
                    await update_delayed_message_status(message_id, 'cancelled')
                    continue
                    
                elif message_type.startswith('demo_received_song_'):
                    # Напоминания после получения демо песни - ОТКЛЮЧЕНО (используется новая система таймеров)
                    logging.info(f"🎵 Пропускаю напоминание после получения демо песни (новая система таймеров): {message_type}")
                    await update_delayed_message_status(message_id, 'cancelled')
                    continue
                    
                elif message_type == 'waiting_full_song_1h':
                    # Напоминание об ожидании полной песни
                    logging.info(f"🎵 Отправляю напоминание об ожидании полной песни: {message_type}")
                    await bot.send_message(user_id, content, parse_mode="HTML")
                    await update_delayed_message_status(message_id, 'sent')
                    await log_general_message_sent(message_id, user_id, order_id)
                    
                else:
                    # Остальные типы сообщений
                    await bot.send_message(user_id, content, parse_mode="HTML")
                    await update_delayed_message_status(message_id, 'sent')
                    await log_general_message_sent(message_id, user_id, order_id)
                    
            except Exception as e:
                pass  # logging.error(f"❌ Ошибка отправки отложенного сообщения {message_id}: {e}")

    except Exception as e:

        logging.error(f"❌ Ошибка в process_old_delayed_messages_fixed: {e}")

async def process_old_delayed_messages(bot: Bot):
    """Старая версия (отключена)"""
    # Временно отключено для исправления отступов
    while True:
        await asyncio.sleep(10)
        continue

    

    # ОРИГИНАЛЬНЫЙ КОД С ОШИБКАМИ ОТСТУПОВ (ЗАКОММЕНТИРОВАН)

    """

    while True:

        try:

            from db import get_pending_delayed_messages, update_delayed_message_status, get_delayed_message_files, get_order, log_general_message_sent, is_general_message_sent_to_user

            

            messages = await get_pending_delayed_messages()

            

            if messages:

                logging.info(f"🔍 Найдено {len(messages)} старых отложенных сообщений для отправки")

            

            for message in messages:

                    user_id = message['user_id']

                    order_id = message['order_id']

                    message_type = message['message_type']

                    content = message['content']

                    message_id = message['id']

                    

                    # logging.info(f"🔍 Обрабатываю отложенное сообщение {message_id} типа '{message_type}' для пользователя {user_id}")

                    

                    try:

                        # Проверяем статус заказа перед отправкой сообщения

                        order = await get_order(order_id)

                        if not order:

                            logging.warning(f"Заказ {order_id} не найден, пропускаем сообщение {message_id}")

                            await update_delayed_message_status(message_id, 'failed')

                            continue

                        

                        order_status = order.get('status') if order else None

                        

                        # Если заказ уже оплачен, не отправляем напоминания об оплате

                        if message_type in ['payment_reminder', 'final_reminder', 'payment_reminder_24h', 'payment_reminder_48h'] and order_status in ['paid', 'upsell_paid', 'ready', 'delivered', 'completed']:

                            logging.info(f"Заказ {order_id} уже оплачен (статус: {order_status}), пропускаем {message_type}")

                            await update_delayed_message_status(message_id, 'cancelled')

                            continue

                        

                        # Проверяем, не было ли уже отправлено это сообщение пользователю

                        if await is_general_message_sent_to_user(message_id, user_id, order_id):

                            # logging.info(f"ℹ️ Сообщение {message_id} уже отправлено пользователю {user_id} (заказ {order_id})")

                            await update_delayed_message_status(message_id, 'sent')

                            continue

                        

                        # Дополнительная проверка: если сообщение уже в статусе 'sent', пропускаем

                        if message.get('status') == 'sent':

                            # logging.info(f"ℹ️ Сообщение {message_id} уже в статусе 'sent', пропускаем")

                            continue

                        

                        # Получаем файлы для этого сообщения

                        files = await get_delayed_message_files(message_id)

                        

                        if message_type == 'demo_example':

                            # Отправляем пример книги с кнопкой "Продолжить создание книги"

                            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

                            

                            # Создаем клавиатуру с кнопкой

                            keyboard = InlineKeyboardMarkup(inline_keyboard=[

                                [InlineKeyboardButton(text="Узнать цену", callback_data="continue_after_demo")]

                            ])

                            

                            if files:

                                # Создаем медиагруппу из всех файлов

                                media_group = await create_mixed_media_group(files, content)

                                

                                if media_group:

                                    # Отправляем медиагруппу

                                    await bot.send_media_group(user_id, media_group)

                                    # Отправляем кнопку отдельным сообщением после медиагруппы

                                    await bot.send_message(user_id, "Готовы продолжить?", reply_markup=keyboard)

                                else:

                                    # Если не удалось создать медиагруппу, отправляем файлы по отдельности

                                    for file_info in files:

                                        await send_file_by_type(

                                            bot, user_id, 

                                            file_info['file_path'], 

                                            file_info['file_type'],

                                            content if files.index(file_info) == 0 else None

                                        )

                                    # Отправляем кнопку отдельным сообщением

                                    await bot.send_message(user_id, "Готовы продолжить?", reply_markup=keyboard)

                            else:

                                # Если нет файлов, отправляем только текст с кнопкой

                                await bot.send_message(user_id, content, reply_markup=keyboard)

                            

                            await update_delayed_message_status(message_id, 'sent')

                            # Записываем в лог отправку

                            await log_general_message_sent(message_id, user_id, order_id)

                            # Увеличиваем счетчик использований шаблона

                            from db import increment_template_usage

                            await increment_template_usage(message_id)

                        

                    elif message_type == 'page_selection':

                        # Отправляем страницы для выбора (каждую отдельно с кнопкой)

                        logging.info(f"📖 Обрабатываю отложенное сообщение типа 'page_selection'")

                        

                        # Устанавливаем правильное состояние пользователя для выбора страниц

                        try:

                            from aiogram.fsm.context import FSMContext

                            from aiogram.fsm.storage.base import StorageKey

                            

                            # Создаем FSMContext для пользователя

                            storage_key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)

                            user_state = FSMContext(storage=dp.storage, key=storage_key)

                            

                            # Устанавливаем состояние выбора страниц

                            await user_state.set_state(BookFinalStates.choosing_pages)

                            

                            # Инициализируем данные заказа

                            if order_id:

                                await user_state.update_data(order_id=order_id)

                            

                            logging.info(f"✅ Установлено состояние choosing_pages для пользователя {user_id}")

                        except Exception as state_error:

                            logging.error(f"❌ Ошибка установки состояния: {state_error}")

                        

                        # Отправляем инструкции

                        await bot.send_message(user_id, content, parse_mode="HTML")

                        

                        # Отправляем дополнительное сообщение с инструкциями по выбору страниц

                        selection_instructions = (

                            "📖 <b>Выбор страниц для вашей книги</b>\n\n"

                            "Здесь представлены сгенерированные страницы и готовые вкладыши.\n"

                            "Выберите ровно 24 страницы из предложенных.\n"

                            "После выбора напишите 'Далее' для продолжения."

                        )

                        await bot.send_message(user_id, selection_instructions, parse_mode="HTML")

                        

                        # Отправляем каждый файл отдельно с кнопкой выбора

                        if files:

                            photos = [f for f in files if f['file_type'] == 'photo']

                            for i, photo in enumerate(photos, 1):

                                try:

                                    keyboard = InlineKeyboardMarkup(inline_keyboard=[

                                        [InlineKeyboardButton(text="Выбрать", callback_data=f"choose_page_{i}")]

                                    ])

                                    

                                    caption = f"📖 Страница {i}\n\nЕсли этот сюжет про вас, то выбери его:"

                                    

                                    await bot.send_photo(

                                        user_id,

                                        FSInputFile(photo['file_path']),

                                        caption=caption,

                                        reply_markup=keyboard

                                    )

                                    logging.info(f"✅ Страница {i} отправлена с кнопкой выбора")

                                except Exception as photo_error:

                                    logging.error(f"❌ Ошибка отправки страницы {i}: {photo_error}")

                        

                        await update_delayed_message_status(message_id, 'sent')

                        # Записываем в лог отправку

                        await log_general_message_sent(message_id, user_id, order_id)

                        # Увеличиваем счетчик использований шаблона

                        from db import increment_template_usage

                        await increment_template_usage(message_id)

                        

                    elif message_type == 'payment_reminder':

                        # Первое напоминание об оплате

                        if files:

                            # Создаем медиагруппу из всех файлов

                            media_group = await create_mixed_media_group(files, content)

                            

                            if media_group:

                                # Отправляем медиагруппу

                                await bot.send_media_group(user_id, media_group)

                            else:

                                # Если не удалось создать медиагруппу, отправляем файлы по отдельности

                                for file_info in files:

                                    await send_file_by_type(

                                        bot, user_id, 

                                        file_info['file_path'], 

                                        file_info['file_type'],

                                        content if files.index(file_info) == 0 else None

                                )

                        else:

                            await bot.send_message(user_id, content)

                        

                        await update_delayed_message_status(message_id, 'sent')

                        # Записываем в лог отправку

                        await log_general_message_sent(message_id, user_id, order_id)

                        # Увеличиваем счетчик использований шаблона

                        from db import increment_template_usage

                        await increment_template_usage(message_id)

                        

                    elif message_type == 'final_reminder':

                        # Финальное напоминание об оплате

                        if files:

                            # Создаем медиагруппу из всех файлов

                            media_group = await create_mixed_media_group(files, content)

                            

                            if media_group:

                                # Отправляем медиагруппу

                                await bot.send_media_group(user_id, media_group)

                            else:

                                # Если не удалось создать медиагруппу, отправляем файлы по отдельности

                                for file_info in files:

                                    await send_file_by_type(

                                        bot, user_id, 

                                        file_info['file_path'], 

                                        file_info['file_type'],

                                        content if files.index(file_info) == 0 else None

                                )

                        else:

                            await bot.send_message(user_id, content)

                        

                        await update_delayed_message_status(message_id, 'sent')

                        # Записываем в лог отправку

                        await log_general_message_sent(message_id, user_id, order_id)

                        # Увеличиваем счетчик использований шаблона

                        from db import increment_template_usage

                        await increment_template_usage(message_id)

                        

                    else:

                        # Универсальная обработка для всех остальных типов сообщений

                        logging.info(f"🔍 Отправляю сообщение типа '{message_type}' пользователю {user_id}")

                        

                        if files:

                            # Создаем медиагруппу из всех файлов

                            media_group = await create_mixed_media_group(files, content)

                            

                            if media_group:

                                # Отправляем медиагруппу

                                await bot.send_media_group(user_id, media_group)

                            else:

                                # Если не удалось создать медиагруппу, отправляем файлы по отдельности

                                for file_info in files:

                                    await send_file_by_type(

                                        bot, user_id, 

                                        file_info['file_path'], 

                                        file_info['file_type'],

                                        content if files.index(file_info) == 0 else None

                                    )

                        else:

                            # Отправляем только текстовое сообщение

                            if message_type in ['payment_reminder_24h', 'payment_reminder_48h']:

                        await bot.send_message(user_id, content)

                            elif message_type in ['song_progress_update', 'book_progress_update', 'story_placeholder']:

                                await bot.send_message(user_id, content, parse_mode="HTML")

                    elif message_type == 'book_offer_after_song':

                                # Создаем клавиатуру для предложения книги

                        keyboard = InlineKeyboardMarkup(inline_keyboard=[

                            [InlineKeyboardButton(text="📖 Создать книгу", callback_data="create_book_after_song")],

                            [InlineKeyboardButton(text="✅ Завершить", callback_data="finish_song_order")]

                        ])

                        await bot.send_message(user_id, content, reply_markup=keyboard)

                            else:

                                await bot.send_message(user_id, content)

                        

                        await update_delayed_message_status(message_id, 'sent')

                        # Записываем в лог отправку

                        await log_general_message_sent(message_id, user_id, order_id)

                        # Увеличиваем счетчик использований шаблона

                        from db import increment_template_usage

                        await increment_template_usage(message_id)

                        # Увеличиваем счетчик использований шаблона

                        from db import increment_template_usage

                        await increment_template_usage(message_id)

                        logging.info(f"✅ Сообщение типа '{message_type}' отправлено пользователю {user_id}")

                        

                        

                    except Exception as e:

                        logging.error(f"Ошибка отправки отложенного сообщения {message_id}: {e}")

                        await update_delayed_message_status(message_id, 'failed')

                        

        except Exception as e:

            logging.error(f"Ошибка обработки отложенных сообщений: {e}")

        

        await asyncio.sleep(10)  # Проверяем каждые 10 секунд для тестирования

    """



@dp.callback_query(F.data.in_(["insert_card", "insert_letter", "insert_audio", "insert_drawing", "insert_poem", "insert_certificate", "skip_inserts"]))

async def choose_insert_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    if callback.data == "skip_inserts":

        await callback.message.edit_text("Вкладыши пропущены. Переходим к следующему этапу.")

        await state.set_state(AdditionsStates.done)

        await additions_next_callback(callback, state)

        return

    

    # Сохраняем выбранный вкладыш

    data = await state.get_data()

    inserts = data.get("inserts", [])

    insert_name = {

        "insert_card": "Поздравительная открытка",

        "insert_letter": "Персональное письмо", 

        "insert_audio": "Аудио-пожелание",

        "insert_drawing": "Рисунок ребенка",

        "insert_poem": "Стихотворение",

        "insert_certificate": "Подарочный сертификат"

    }[callback.data]

    

    inserts.append(insert_name)

    await state.update_data(inserts=inserts)

    

    # Сохраняем информацию о текущем вкладыше для запроса текста

    await state.update_data(current_insert=callback.data)

    

    # Запрашиваем текст для вкладыша

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="✍️ Написать свой текст", callback_data="write_insert_text")],

        [InlineKeyboardButton(text="🎭 Оставить на усмотрение сценаристов", callback_data="auto_insert_text")],

        [InlineKeyboardButton(text="🔄 Выбрать другой вкладыш", callback_data="change_insert")]

    ])

    

    await callback.message.edit_text(

        f"📝 <b>Текст для вкладыша: {insert_name}</b>\n\n"

        f"Теперь нужно добавить текст для этого вкладыша.\n\n"

        f"Вы можете:\n"

        f"• Написать свой персональный текст\n"

        f"• Оставить написание на усмотрение наших сценаристов\n"

        f"• Выбрать другой вкладыш",

        reply_markup=keyboard,

        parse_mode="HTML"

    )

    await state.set_state(AdditionsStates.waiting_insert_text)

    await log_state(callback.message, state)



# Обработчики для выбора текста вкладыша

@dp.callback_query(F.data == "write_insert_text")

async def write_insert_text_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    data = await state.get_data()

    current_insert = data.get("current_insert")

    insert_name = {

        "insert_card": "Поздравительная открытка",

        "insert_letter": "Персональное письмо", 

        "insert_audio": "Аудио-пожелание",

        "insert_drawing": "Рисунок ребенка",

        "insert_poem": "Стихотворение",

        "insert_certificate": "Подарочный сертификат"

    }[current_insert]

    

    await callback.message.edit_text(

        f"✍️ <b>Напишите текст для {insert_name}</b>\n\n"

        f"Отправьте ваш персональный текст для этого вкладыша.\n\n"

        f"💡 <b>Рекомендации:</b>\n"

        f"• Пишите от сердца\n"

        f"• Упомяните особые моменты\n"

        f"• Добавьте теплые пожелания\n"

        f"• Будьте искренними\n\n"

        f"Отправьте текст одним сообщением.",

        parse_mode="HTML"

    )

    await state.set_state(AdditionsStates.waiting_insert_text)

    await log_state(callback.message, state)



@dp.callback_query(F.data == "auto_insert_text")

async def auto_insert_text_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    data = await state.get_data()

    current_insert = data.get("current_insert")

    insert_name = {

        "insert_card": "Поздравительная открытка",

        "insert_letter": "Персональное письмо", 

        "insert_audio": "Аудио-пожелание",

        "insert_drawing": "Рисунок ребенка",

        "insert_poem": "Стихотворение",

        "insert_certificate": "Подарочный сертификат"

    }[current_insert]

    

    # Сохраняем информацию о том, что текст будет написан сценаристами

    insert_texts = data.get("insert_texts", {})

    insert_texts[current_insert] = "На усмотрение сценаристов"

    await state.update_data(insert_texts=insert_texts)

    

    await callback.message.edit_text(

        f"✅ <b>Вкладыш добавлен: {insert_name}</b>\n\n"

        f"Текст будет написан нашими профессиональными сценаристами на основе информации о вашей книге.",

        parse_mode="HTML"

    )

    

    # Показываем кнопки для продолжения

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="➕ Добавить еще вкладыш", callback_data="add_insert")],

        [InlineKeyboardButton(text="📸 Добавить свои фото", callback_data="add_custom_photos")],

        [InlineKeyboardButton(text="➡️ Продолжить", callback_data="additions_next")]

    ])

    await callback.message.answer("Хотите добавить еще вкладыши или свои фотографии?", reply_markup=keyboard)

    await state.set_state(AdditionsStates.choosing_inserts)

    await log_state(callback.message, state)



@dp.callback_query(F.data == "change_insert")

async def change_insert_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    # Удаляем последний добавленный вкладыш

    data = await state.get_data()

    inserts = data.get("inserts", [])

    if inserts:

        inserts.pop()

        await state.update_data(inserts=inserts)

    

    # Показываем выбор вкладышей снова

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="💝 Поздравительная открытка", callback_data="insert_card")],

        [InlineKeyboardButton(text="📝 Персональное письмо", callback_data="insert_letter")],

        [InlineKeyboardButton(text="🎵 Аудио-пожелание", callback_data="insert_audio")],

        [InlineKeyboardButton(text="🎨 Рисунок ребенка", callback_data="insert_drawing")],

        [InlineKeyboardButton(text="💌 Стихотворение", callback_data="insert_poem")],

        [InlineKeyboardButton(text="🎁 Подарочный сертификат", callback_data="insert_certificate")],

        [InlineKeyboardButton(text="Пропустить", callback_data="skip_inserts")]

    ])

    await callback.message.edit_text(

        "Выберите вкладыши для вашей книги:\n\n"

        "💝 <b>Поздравительная открытка</b> - красивая открытка с вашими пожеланиями\n"

        "📝 <b>Персональное письмо</b> - письмо от сердца с вашими чувствами\n"

        "🎵 <b>Аудио-пожелание</b> - запись вашего голоса с пожеланиями\n"

        "🎨 <b>Рисунок ребенка</b> - детский рисунок как дополнение к книге\n"

        "💌 <b>Стихотворение</b> - стихотворение, написанное специально для получателя\n"

        "🎁 <b>Подарочный сертификат</b> - сертификат на создание следующей книги",

        reply_markup=keyboard,

        parse_mode="HTML"

    )

    await state.set_state(AdditionsStates.choosing_inserts)

    await log_state(callback.message, state)



# Обработчик для получения текста вкладыша от пользователя

@dp.message(StateFilter(AdditionsStates.waiting_insert_text), F.text)

async def receive_insert_text(message: types.Message, state: FSMContext):

    # Сохраняем сообщение пользователя в историю заказа

    await save_user_message_to_history(message, state, "Текст вкладыша: ")

    

    data = await state.get_data()

    current_insert = data.get("current_insert")

    insert_name = {

        "insert_card": "Поздравительная открытка",

        "insert_letter": "Персональное письмо", 

        "insert_audio": "Аудио-пожелание",

        "insert_drawing": "Рисунок ребенка",

        "insert_poem": "Стихотворение",

        "insert_certificate": "Подарочный сертификат"

    }[current_insert]

    

    # Сохраняем текст вкладыша

    insert_texts = data.get("insert_texts", {})

    insert_texts[current_insert] = message.text

    await state.update_data(insert_texts=insert_texts)

    

    await message.answer(

        f"✅ <b>Текст сохранен для {insert_name}</b>\n\n"

        f"Ваш текст будет использован в вкладыше.",

        parse_mode="HTML"

    )

    

    # Показываем кнопки для продолжения

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="➕ Добавить еще вкладыш", callback_data="add_insert")],

        [InlineKeyboardButton(text="📸 Добавить свои фото", callback_data="add_custom_photos")],

        [InlineKeyboardButton(text="➡️ Продолжить", callback_data="additions_next")]

    ])

    await message.answer("Хотите добавить еще вкладыши или свои фотографии?", reply_markup=keyboard)

    await state.set_state(AdditionsStates.choosing_inserts)

    await log_state(message, state)



# Обработчик кнопки "Добавить свои фото"

@dp.callback_query(F.data == "add_custom_photos")

async def add_custom_photos_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    await callback.message.edit_text(

        "📸 <b>Добавление своих фотографий</b>\n\n"

        "Отправьте фотографии, которые вы хотите добавить в книгу. "

        "Это могут быть семейные фото, фото ребенка, памятные моменты и т.д.\n\n"

        "Отправляйте фото по одному. Когда закончите, напишите <b>'Готово'</b>.",

        parse_mode="HTML"

    )

    

    # Переходим в состояние загрузки фотографий

    await state.set_state(AdditionsStates.uploading_photos)

    await log_state(callback.message, state)



# Обработчик кнопки "Добавить еще вкладыш"

@dp.callback_query(F.data == "add_insert")

async def add_more_insert_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

    

    # Показываем выбор вкладышей с подробными описаниями

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="💝 Поздравительная открытка", callback_data="insert_card")],

        [InlineKeyboardButton(text="📝 Персональное письмо", callback_data="insert_letter")],

        [InlineKeyboardButton(text="🎵 Аудио-пожелание", callback_data="insert_audio")],

        [InlineKeyboardButton(text="🎨 Рисунок ребенка", callback_data="insert_drawing")],

        [InlineKeyboardButton(text="💌 Стихотворение", callback_data="insert_poem")],

        [InlineKeyboardButton(text="🎁 Подарочный сертификат", callback_data="insert_certificate")],

        [InlineKeyboardButton(text="Пропустить", callback_data="skip_inserts")]

    ])

    await callback.message.edit_text(

        "Выберите дополнительные вкладыши для вашей книги:\n\n"

        "💝 <b>Поздравительная открытка</b> - красивая открытка с вашими пожеланиями\n"

        "📝 <b>Персональное письмо</b> - письмо от сердца с вашими чувствами\n"

        "🎵 <b>Аудио-пожелание</b> - запись вашего голоса с пожеланиями\n"

        "🎨 <b>Рисунок ребенка</b> - детский рисунок как дополнение к книге\n"

        "💌 <b>Стихотворение</b> - стихотворение, написанное специально для получателя\n"

        "🎁 <b>Подарочный сертификат</b> - сертификат на создание следующей книги",

        reply_markup=keyboard,

        parse_mode="HTML"

    )

    await state.set_state(BookFinalStates.choosing_inserts)

    await log_state(callback.message, state)



# Глава 12. Обработка загрузки пользовательских фотографий - улучшенная версия

@dp.message(StateFilter(AdditionsStates.uploading_photos), F.photo)

async def upload_custom_photo(message: types.Message, state: FSMContext):

    file_id = message.photo[-1].file_id

    

    # Сохраняем фото

    data = await state.get_data()

    custom_photos = data.get("custom_photos", [])

    custom_photos.append(file_id)

    await state.update_data(custom_photos=custom_photos)

    

    await message.answer(

        f"✅ <b>Фото добавлено!</b>\n\n"

        f"Всего загружено: <b>{len(custom_photos)}</b> фотографий\n\n"

        f"Отправьте еще фото или напишите <b>'Готово'</b> для завершения.",

        parse_mode="HTML"

    )

    await log_state(message, state)



@dp.message(StateFilter(AdditionsStates.uploading_photos), F.text)

async def finish_photo_upload(message: types.Message, state: FSMContext):

    # Сохраняем сообщение пользователя в историю заказа

    await save_user_message_to_history(message, state, "Сообщение при загрузке фото: ")

    

    if message.text.lower() == "готово":

        data = await state.get_data()

        custom_photos = data.get("custom_photos", [])

        

        await message.answer(

            f"✅ <b>Отлично! Загружено {len(custom_photos)} фотографий.</b>\n\n"

            f"Все ваши фотографии будут добавлены в книгу и красиво оформлены.",

            parse_mode="HTML"

        )

        

        # Показываем кнопку для продолжения

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="➡️ Продолжить", callback_data="additions_next")]

        ])

        await message.answer("Переходим к следующему этапу", reply_markup=keyboard)

        await state.set_state(AdditionsStates.done)

    else:

        # Проверяем, не является ли это ответом на отложенное сообщение

        if "цена" in message.text.lower() or "смутила" in message.text.lower():

            # Это ответ на отложенное сообщение о цене

            await message.answer(

                "Спасибо за ваш ответ! Наш менеджер свяжется с вами в ближайшее время для обсуждения вариантов."

            )

        else:

            await message.answer(

                "Отправьте еще фото или напишите <b>'Готово'</b> для завершения.",

                parse_mode="HTML"

            )

    

    await log_state(message, state)



# Обработчики для загрузки своих фотографий в главе 12

@dp.message(StateFilter(BookFinalStates.uploading_custom_photos), F.photo)

async def upload_custom_photo_book_final(message: types.Message, state: FSMContext):

    """Обрабатывает загрузку своих фотографий в главе 12"""

    try:

        # Получаем данные

        data = await state.get_data()

        order_id = data.get('order_id')

        

        if not order_id:

            await message.answer("❌ Ошибка: заказ не найден")

            return

        

        # Сохраняем фото в папку

        photo = message.photo[-1]

        file_id = photo.file_id

        

        # Создаем папку для пользовательских фотографий

        custom_photos_dir = f"uploads/order_{order_id}_custom_photos"

        os.makedirs(custom_photos_dir, exist_ok=True)

        

        # Скачиваем и сохраняем фото

        file_info = await bot.get_file(file_id)

        file_path = file_info.file_path

        

        # Генерируем уникальное имя файла

        import time

        import secrets

        file_extension = os.path.splitext(file_path)[1] if file_path else '.jpg'

        unique_filename = f"custom_photo_{int(time.time())}_{secrets.token_hex(4)}{file_extension}"

        local_path = os.path.join(custom_photos_dir, unique_filename)

        

        # Скачиваем файл

        await bot.download_file(file_path, local_path)

        

        # Сохраняем информацию о файле в базу данных

        await save_uploaded_file(order_id, unique_filename, "custom_photo", local_path)

        

        # Обновляем данные в state

        custom_photos = data.get("custom_photos", [])

        custom_photos.append(unique_filename)

        await state.update_data(custom_photos=custom_photos)

        

        # Обновляем order_data в базе

        order_data = data.get('order_data', {})

        order_data['custom_photos'] = custom_photos

        await update_order_data(order_id, order_data)

        

        await message.answer(

            f"✅ <b>Фото добавлено!</b>\n\n"

            f"Всего загружено: <b>{len(custom_photos)}</b> фотографий\n\n"

            f"Отправьте еще фото или напишите <b>'Готово'</b> для завершения.",

            parse_mode="HTML"

        )

        

    except Exception as e:

        logging.error(f"❌ Ошибка в upload_custom_photo_book_final: {e}")

        await message.answer("❌ Произошла ошибка при загрузке фото. Попробуйте еще раз.")

    

    await log_state(message, state)



@dp.message(StateFilter(BookFinalStates.uploading_custom_photos), F.text)

async def finish_photo_upload_book_final(message: types.Message, state: FSMContext):

    """Завершает загрузку своих фотографий в главе 12"""

    try:

        # Сохраняем сообщение пользователя в историю заказа

        await save_user_message_to_history(message, state, "Сообщение при загрузке фото: ")

        

        if message.text.lower() == "готово":

            data = await state.get_data()

            custom_photos = data.get("custom_photos", [])

            

            await message.answer(

                f"✅ <b>Отлично! Загружено {len(custom_photos)} фотографий.</b>\n\n"

                f"Все ваши фотографии будут добавлены в книгу и красиво оформлены.",

                parse_mode="HTML"

            )

            

            # Предлагаем добавить вкладыши или продолжить

            keyboard = InlineKeyboardMarkup(inline_keyboard=[

                [InlineKeyboardButton(text="📄 Добавить вкладыши", callback_data="add_inserts")],

                [InlineKeyboardButton(text="➡️ Продолжить без вкладышей", callback_data="skip_inserts")]

            ])

            

            await message.answer(

                "Хотите добавить вкладыши в книгу или продолжить без них?",

                reply_markup=keyboard

            )

            

            # Переходим к выбору дополнений

            await state.set_state(AdditionsStates.choosing_addition)

        else:

            # Проверяем, не является ли это ответом на отложенное сообщение

            if "цена" in message.text.lower() or "смутила" in message.text.lower():

                # Это ответ на отложенное сообщение о цене

                await message.answer(

                    "Спасибо за ваш ответ! Наш менеджер свяжется с вами в ближайшее время для обсуждения вариантов."

                )

            else:

                await message.answer(

                    "Отправьте еще фото или напишите <b>'Готово'</b> для завершения.",

                    parse_mode="HTML"

                )

        

    except Exception as e:

        logging.error(f"❌ Ошибка в finish_photo_upload_book_final: {e}")

        await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")

    

    await log_state(message, state)



# Обработчики для BookFinalStates.uploading_custom_photos

@dp.message(StateFilter(BookFinalStates.uploading_custom_photos), F.media_group_id)

async def upload_custom_photos_media_group(message: types.Message, state: FSMContext):

    """Обрабатывает медиагруппы с несколькими фотографиями"""

    try:

        # Получаем данные заказа

        data = await state.get_data()

        order_id = data.get('order_id')

        

        if not order_id:

            await message.answer("❌ Ошибка: не найден ID заказа. Попробуйте еще раз.")

            return

        

        # Получаем медиагруппу ID

        media_group_id = message.media_group_id

        

        # Проверяем, не обрабатывали ли мы уже эту медиагруппу

        processed_groups = data.get("processed_media_groups", set())

        if media_group_id in processed_groups:

            return  # Уже обработали эту группу

        

        # Добавляем группу в обработанные

        processed_groups.add(media_group_id)

        await state.update_data(processed_media_groups=processed_groups)

        

        # Получаем все сообщения из медиагруппы

        from aiogram.fsm.context import FSMContext

        from aiogram.types import Message

        

        # Создаем папку для заказа если её нет

        order_dir = f"uploads/order_{order_id}_custom_photos"

        os.makedirs(order_dir, exist_ok=True)

        

        # Получаем количество уже загруженных фото для нумерации

        custom_photos = data.get("custom_photos", [])

        start_photo_number = len(custom_photos) + 1

        

        # Обрабатываем каждое фото в медиагруппе

        photos_in_group = []

        

        # Получаем все сообщения из медиагруппы (это будет сделано в основном обработчике)

        # Здесь мы обрабатываем только текущее сообщение

        if message.photo:

            photo = message.photo[-1]  # Берем самое большое фото

            file_id = photo.file_id

            

            # Скачиваем файл

            file_info = await bot.get_file(file_id)

            file_path = file_info.file_path

            

            # Определяем расширение файла

            file_extension = os.path.splitext(file_path)[1] or '.jpg'

            photo_number = start_photo_number

            filename = f"custom_photo_{photo_number:02d}{file_extension}"

            local_path = os.path.join(order_dir, filename)

            

            # Скачиваем файл

            await bot.download_file(file_path, local_path)

            

            # Сохраняем информацию о фото в базу данных

            upload_id = await save_uploaded_file(order_id, filename, "custom_photo")

            

            # Добавляем в список фотографий группы

            photos_in_group.append({

                'file_id': file_id,

                'filename': filename,

                'upload_id': upload_id,

                'local_path': local_path

            })

        

        # Добавляем все фотографии группы в общий список

        custom_photos.extend(photos_in_group)

        await state.update_data(custom_photos=custom_photos)

        

        # Обновляем order_data в базе

        order_data = data.get('order_data', {})

        order_data['custom_photos'] = custom_photos

        await update_order_data(order_id, order_data)

        

        # Отправляем сообщение о загрузке группы фотографий

        # Используем более точный подсчет для медиагрупп

        photos_count = len(photos_in_group)

        total_count = len(custom_photos)

        

        await message.answer(

            f"✅ <b>Загружено {photos_count} фотографий!</b>\n\n"

            f"Всего загружено: <b>{total_count}</b> фотографий\n\n"

            f"Отправьте еще фото или напишите <b>'Готово'</b> для завершения.",

            parse_mode="HTML"

        )

        

        print(f"🔍 ОТЛАДКА: Загружено {len(photos_in_group)} фотографий из медиагруппы для заказа {order_id}")

        

    except Exception as e:

        logging.error(f"❌ Ошибка загрузки медиагруппы фотографий: {e}")

        await message.answer("❌ Произошла ошибка при загрузке фотографий. Попробуйте еще раз.")

    

    await log_state(message, state)







# Глава 14. Отправка черновика книги от менеджера

@dp.message(StateFilter(EditBookStates.waiting_for_draft))

async def receive_book_draft_for_editing(message: types.Message, state: FSMContext):

    # Проверяем, что это сообщение от менеджера, а не от пользователя

    # Если это сообщение от пользователя, игнорируем его

    data = await state.get_data()

    order_id = data.get('order_id')

    

    if order_id:

        order = await get_order(order_id)

        if order and order.get('user_id') == message.from_user.id:

            # Это сообщение от пользователя, а не от менеджера

            # Сохраняем сообщение в историю заказа, но не перекидываем пользователя

            try:

                from db import add_message_history

                await add_message_history(order_id, "user", message.text)

                logging.info(f"💬 Сообщение пользователя {message.from_user.id} сохранено в историю заказа {order_id}: {message.text[:50]}...")

            except Exception as e:

                logging.error(f"❌ Ошибка сохранения сообщения в историю: {e}")

            

            logging.info(f"📖 Игнорируем сообщение от пользователя {message.from_user.id} в состоянии waiting_for_draft")

            return

    

    # Менеджер отправляет черновик книги для редактирования

    await update_order_status(order_id, "draft_sent")

    

    # Отправляем черновик пользователю

    await message.answer(

        "📖 <b>Черновик вашей книги готов!</b>\n\n"

        "Пожалуйста, внимательно просмотрите черновик и сообщите нам, если нужны изменения.",

        parse_mode="HTML"

    )

    

    # Отправляем файлы черновика

    if message.document:

        # Если это PDF файл

        await message.answer_document(

            message.document.file_id, 

            caption="📄 Черновик книги (PDF)\n\nПросмотрите и сообщите, если нужны изменения."

        )

    elif message.photo:

        # Если это галерея изображений

        await message.answer_photo(

            message.photo[-1].file_id, 

            caption="📖 Черновик книги\n\nПросмотрите и сообщите, если нужны изменения."

        )

    else:

        # Если это текст с описанием

        await message.answer(message.text)

    

    # Кнопки для ответа пользователя

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="✅ Готово", callback_data="edit_done")],

        [InlineKeyboardButton(text="🔄 Изменить", callback_data="edit_change")]

    ])

    

    await message.answer(

        "Как вам черновик?\n\n"

        "• <b>✅ Готово</b> - если все устраивает\n"

        "• <b>🔄 Изменить</b> - если нужны правки",

        reply_markup=keyboard,

        parse_mode="HTML"

    )

    

    await state.set_state(EditBookStates.reviewing_draft)

    await log_state(message, state)



# Обработчики для кнопок помощи и навигации

@dp.callback_query(lambda c: c.data in ["help", "restart", "main_menu", "start"])

async def handle_help_navigation_buttons(callback: types.CallbackQuery, state: FSMContext):

    """Обрабатывает кнопки помощи и навигации"""

    current_state = await state.get_state()

    

    if callback.data == "help":

        await callback.answer("Показываю справку")

        await callback.message.answer(

            "📖 <b>Справка по созданию книги/песни:</b>\n\n"

            "• <b>Фото</b> - отправляйте четкие фотографии\n"

            "• <b>Текст</b> - пишите подробно о герое\n"

            "• <b>Аудио</b> - для песен отправляйте голосовые сообщения\n\n"

            "Если у вас возникли трудности, напишите /start для перезапуска.",

            parse_mode="HTML"

        )

        

    elif callback.data == "restart":

        await callback.answer("Начинаем заново")

        await state.clear()

        await callback.message.answer("🔄 Начинаем создание заново!")

        # Вызываем функцию приветственного сообщения

        await show_welcome_message(callback.message, state)

        

    elif callback.data == "main_menu":

        await callback.answer("Главное меню")

        await state.clear()

        await callback.message.answer("🏠 Добро пожаловать в главное меню!")

        # Показываем выбор продукта

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="🎵 Создать песню", callback_data="create_song")],

            [InlineKeyboardButton(text="📖 Создать книгу", callback_data="create_book")]

        ])

        await callback.message.answer(

            "Выберите, что хотите создать:",

            reply_markup=keyboard

        )

        

    elif callback.data == "start":

        await callback.answer("Начинаем!")

        await state.clear()

        await show_welcome_message(callback.message, state)



# Обработчик для всех остальных необработанных callback_query

@dp.callback_query()

async def handle_unhandled_callback(callback: types.CallbackQuery):

    logging.warning(f"⚠️ Необработанный callback_query: {callback.data}")

    logging.warning(f"⚠️ User ID: {callback.from_user.id}")

    logging.warning(f"⚠️ Message ID: {callback.message.message_id}")

    logging.warning(f"⚠️ Message text: {callback.message.text}")

    logging.warning(f"⚠️ Message caption: {callback.message.caption}")

    logging.warning(f"⚠️ Available handlers: {[h.callback.__name__ for h in dp.callback_query.handlers]}")

    await callback.answer("Эта функция пока не реализована")



# Универсальный обработчик для непредвиденных типов контента (НЕ текстовых сообщений)

@dp.message()

async def handle_unexpected_content(message: types.Message, state: FSMContext):

    """

    Обрабатывает все непредвиденные типы контента (видео, кружки, стикеры и т.д.)

    НЕ обрабатывает текстовые сообщения - они должны обрабатываться специфическими обработчиками

    """

    # НЕ обрабатываем текстовые сообщения - пусть их обрабатывают специфические обработчики

    if message.text:

        logging.info(f"🔍 Универсальный обработчик: пропускаем текстовое сообщение '{message.text[:50]}...' - пусть обработает специфический обработчик")

        return

        

    current_state = await state.get_state()

    data = await state.get_data()

    

    # Проверяем, является ли это действительно неподдерживаемым контентом

    is_unsupported = False

    content_type = "неизвестный тип"

    

    if message.video:

        content_type = "видео"

        is_unsupported = True

    elif message.animation:

        content_type = "GIF/анимация"

        is_unsupported = True

    elif message.sticker:

        content_type = "стикер"

        is_unsupported = True

    elif message.voice:

        content_type = "голосовое сообщение"

        is_unsupported = True

    elif message.video_note:

        content_type = "кружок"

        is_unsupported = True

    elif message.document:

        content_type = "документ"

        is_unsupported = True

    elif message.audio:

        content_type = "аудио"

        is_unsupported = True

    

    # Если это не неподдерживаемый контент, просто игнорируем

    if not is_unsupported:

        return

    

    logging.warning(f"⚠️ Непредвиденный контент: {content_type} от пользователя {message.from_user.id} в состоянии {current_state}")

    

    # Определяем, на каком этапе находится пользователь и что от него ожидается

    expected_content = "текст"

    if current_state:

        if "photo" in current_state.lower():

            expected_content = "фотографию"

        elif "text" in current_state.lower():

            expected_content = "текст"

        elif "demo" in current_state.lower():

            expected_content = "аудио файл"

        elif "draft" in current_state.lower():

            expected_content = "файл"

    

    # Отправляем понятное сообщение пользователю

    await message.answer(

        "Ой, кажется, вместо фото загрузился другой файл ❌\n"

        "Сейчас нам нужно именно изображение.\n"

        "Пришли, пожалуйста, фотографию 📷",

        parse_mode="HTML"

    )

    

    await log_state(message, state)



# Универсальный обработчик для всех текстовых сообщений (ПЕРЕМЕЩЕН В КОНЕЦ ФАЙЛА)

@dp.message(F.text)

async def handle_all_text_messages(message: types.Message, state: FSMContext):

    """Обрабатывает все текстовые сообщения и сохраняет их в историю"""

    try:

        # Получаем текущее состояние

        current_state = await state.get_state()

        # РАСШИРЕННОЕ ЛОГИРОВАНИЕ для отладки
        logging.info(f"📥 Универсальный обработчик: получено сообщение от {message.from_user.id}, состояние: {current_state}, текст: '{message.text[:50]}...'")

        # ВРЕМЕННЫЙ ЛОГ для отладки дублирования голосов

        if "kk" in message.text.lower() or "стил" in message.text.lower():

            logging.error(f"🚨 ДУБЛИРОВАНИЕ: универсальный обработчик вызван с состоянием {current_state}, текст: '{message.text}'")

        

        # Проверяем, есть ли специфический обработчик для этого состояния
        # Если есть, не обрабатываем здесь, чтобы избежать дублирования

        if current_state in [
            "SongDraftStates.waiting_for_demo",
            "SongDraftStates.demo_received", 
            "SongDraftStates.waiting_for_draft",
            "SongFactsStates.collecting_facts",
            "SongRelationStates.waiting_recipient_name",
            "SongRelationStates.waiting_gift_reason"
        ]:
            logging.info(f"🔍 Состояние {current_state} имеет специфический обработчик, пропускаем универсальный")
            return

        logging.info(f"🔍 Универсальный обработчик: обрабатываем сообщение в состоянии {current_state}")

        

        data = await state.get_data()

        order_id = data.get('order_id')

        logging.info(f"📦 Order ID из состояния: {order_id}")

        

        # Если есть заказ, сохраняем сообщение в историю

        if order_id:

            from db import add_message_history, create_or_update_order_notification

            await add_message_history(order_id, "user", message.text)

            

            # Создаем или обновляем уведомление для менеджера

            await create_or_update_order_notification(order_id)

            logging.info(f"✅ СОХРАНЕНО: Сообщение пользователя {message.from_user.id} в историю заказа {order_id}: {message.text[:50]}...")
            logging.info(f"🔔 СОЗДАНО: Уведомление для заказа {order_id}")

            print(f"🔍 ОТЛАДКА: Сохранено сообщение пользователя в историю заказа {order_id}: {message.text}")

            print(f"🔔 ОТЛАДКА: Создано уведомление для заказа {order_id}")

        else:

            # Если заказа еще нет, сохраняем сообщение для последующего переноса

            from db import save_early_user_message

            await save_early_user_message(message.from_user.id, message.text)

            logging.info(f"📝 СОХРАНЕНО: Раннее сообщение пользователя {message.from_user.id}: {message.text[:50]}...")

            print(f"🔍 ОТЛАДКА: Сохранено раннее сообщение пользователя {message.from_user.id}: {message.text}")

    except Exception as e:

        logging.error(f"❌ Ошибка сохранения сообщения в историю: {e}")
        print(f"❌ Ошибка сохранения сообщения в историю: {e}")



async def main():

    await init_db()

    await init_payments_table()

    

    # Запуск фоновой задачи для обработки outbox
    asyncio.create_task(process_outbox_tasks(bot))  # Включаем

    # Запуск фоновой задачи для обработки шаблонов сообщений (новая система)
    # asyncio.create_task(process_message_templates(bot))  # Отключаем
    
    # Запуск новой системы обработки по таймерам
    asyncio.create_task(process_timer_based_messages(bot))  # Включаем новую систему
    
    # Запуск автоматической проверки платежей
    asyncio.create_task(auto_check_payments())  # Включаем автоматическую проверку

    

    # Добавляем логирование для отладки

    logging.info(f"📝 Зарегистрировано обработчиков: {len(dp.message.handlers) + len(dp.callback_query.handlers)}")

    logging.info(f"🔘 Обработчики callback_query: {len(dp.callback_query.handlers)}")

    

    # Запуск бота с обработкой ошибок

    try:

        logging.info("🚀 Запуск бота...")

        await dp.start_polling(bot)

    except Exception as e:

        logging.error(f"❌ Критическая ошибка запуска бота: {e}")

        raise


if __name__ == '__main__':

    asyncio.run(main())