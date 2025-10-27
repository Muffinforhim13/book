// Полный словарь статусов => отображаемые названия
export const STATUS_TRANSLATIONS: { [key: string]: string } = {
    'created': 'Создан',
    'product_selected': 'Выбран продукт',
    'gender_selected': 'Выбран пол',
    'recipient_selected': 'Выбран получатель',
    'recipient_name_entered': 'Введено имя получателя',
    'gift_reason_entered': 'Указан повод подарка',
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
    'delivered': 'Доставлен',
    'completed': 'Завершен',
    'waiting_cover_choice': 'Ожидает выбора обложки',
    'cover_selected': 'Обложка выбрана',
    'waiting_story_choice': 'Ожидает выбора сюжета',
    'waiting_story_options': 'Ожидает вариантов сюжета',
    'story_selected': 'Сюжет выбран',
    'pages_selected': 'Страницы выбраны',
    'voice_selection': 'Выбор голоса',
    'upsell_payment_created': 'Ожидание доплаты',
    'upsell_payment_pending': 'Ожидание доплаты',
    'upsell_paid': 'Доплата получена',
    'print_delivery_pending': 'Отправка печатной версии',
    'additional_payment_paid': 'Доплата за печатную версию оплачена',
    // Новые статусы для детализации создания персонажа книги
    'first_name_entered': 'Введено имя',
    'relation_selected': 'Выбран получатель',
    'character_description_entered': 'Описание персонажа',
    'main_photos_uploaded': 'Загружены фото основного героя',
    'hero_name_entered': 'Введено имя второго героя',
    'hero_description_entered': 'Описание второго персонажа',
    'hero_photos_uploaded': 'Загружены фото второго героя',
    'joint_photo_uploaded': 'Загружено совместное фото',
    // Дополнительный статус, используемый на вкладке заказов
    'covers_sent': 'Обложки отправлены'
};

// Функция для перевода статусов заказов на русский
export const translateStatus = (status: string): string => {
  return STATUS_TRANSLATIONS[status] || status;
};

// Полный список значений статусов и удобные структуры для выпадающих списков
export const ALL_STATUS_VALUES: string[] = Object.keys(STATUS_TRANSLATIONS);
export const ALL_STATUS_OPTIONS: Array<{ value: string; label: string }> = ALL_STATUS_VALUES.map((value) => ({
  value,
  label: STATUS_TRANSLATIONS[value]
}));
