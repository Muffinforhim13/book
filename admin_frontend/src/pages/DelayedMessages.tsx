import React, { useEffect, useState } from "react";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";

interface DelayedMessageFile {
  id: number;
  file_path: string;
  file_type: string;
  file_name: string;
  file_size: number;
  created_at: string;
}

interface DelayedMessage {
  id: number;
  order_id: number | null;
  user_id: number | null;
  manager_id: number | null;
  manager_email?: string;
  manager_name?: string;
  name?: string;
  message_type: string;
  content: string;
  delay_minutes: number;
  status: string;
  created_at: string;
  scheduled_at: string;
  sent_at?: string;
  files?: DelayedMessageFile[];
  is_automatic?: boolean;
  order_step?: string;  // Новое поле для шага заказа
  story_batch?: number;
  story_pages?: string;
  selected_stories?: string;
  is_active?: boolean;  // Новое поле для активации/деактивации шаблона
  usage_count?: number; // Количество использований шаблона
  last_used?: string;   // Последнее использование
}

export const DelayedMessagesPage: React.FC = () => {
  const [messages, setMessages] = useState<DelayedMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [selectedType, setSelectedType] = useState<string>("all");
  const [selectedStep, setSelectedStep] = useState<string>("all");
  const [orderFilter, setOrderFilter] = useState<string>("");
  const [orders, setOrders] = useState<{id: number, user_id: number, order_data: string}[]>([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [ordersError, setOrdersError] = useState("");

  // Состояния для создания нового отложенного сообщения
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newMessage, setNewMessage] = useState({
    order_id: "",
    message_type: "payment_reminder_24h",
    content: "",
    delay_minutes: 60,
    order_step: "" // Новое поле для выбора шага заказа
  });
  const [creating, setCreating] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  // Состояния для добавления файлов
  const [selectedMessageId, setSelectedMessageId] = useState<number | null>(null);
  const [showFileUpload, setShowFileUpload] = useState(false);
  const [uploadingFiles, setUploadingFiles] = useState(false);

  // Состояния для редактирования сообщения
  const [editingMessage, setEditingMessage] = useState<DelayedMessage | null>(null);
  const [showEditForm, setShowEditForm] = useState(false);
  const [editForm, setEditForm] = useState({
    name: "",
    content: "",
    delay_minutes: 60,
    message_type: "",
    order_step: ""
  });
  const [editing, setEditing] = useState(false);
  const [editSelectedFiles, setEditSelectedFiles] = useState<File[]>([]);

  // Состояние для переключения между разделами
  const [activeTab, setActiveTab] = useState<'general' | 'personal'>('general');
  const [userPermissions, setUserPermissions] = useState<{is_super_admin: boolean} | null>(null);
  
  // Состояние для активации/деактивации шаблонов
  const [togglingActive, setTogglingActive] = useState<number | null>(null);

  useEffect(() => {
    fetchDelayedMessages();
    fetchUserPermissions();
  }, []);

  // Загружаем заказы после получения прав доступа
  useEffect(() => {
    if (userPermissions !== null) {
      fetchOrders();
    }
  }, [userPermissions]);

  // Сброс фильтров при переключении вкладок
  useEffect(() => {
    setSelectedStatus("all");
    setSelectedType("all");
    setSelectedStep("all");
    setOrderFilter("");
    
    // Сброс формы при переключении вкладок
    if (showCreateForm) {
      setNewMessage({
        order_id: "",
        message_type: activeTab === 'general' ? "payment_reminder_24h" : "demo_example",
        content: "",
        delay_minutes: 60,
        order_step: ""
      });
      setSelectedFiles([]);
    }
  }, [activeTab, showCreateForm]);

  const fetchDelayedMessages = async () => {
    try {
      const token = localStorage.getItem("token");
      // Загружаем отложенные сообщения (включая шаблоны)
      const response = await fetch("/admin/delayed-messages", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        console.log("Получены данные:", data); // Отладка
        setMessages(data);
      } else {
        setError("Ошибка загрузки отложенных сообщений");
      }
    } catch (err) {
      setError("Ошибка загрузки отложенных сообщений");
    } finally {
      setLoading(false);
    }
  };

  const fetchOrders = async () => {
    setOrdersLoading(true);
    setOrdersError("");
    try {
      const token = localStorage.getItem("token");
      
      // Определяем endpoint в зависимости от прав доступа
      const endpoint = userPermissions?.is_super_admin 
        ? "/admin/orders"  // Администратор видит все заказы
        : "/admin/profile/orders";  // Менеджер видит только свои заказы
      
      const response = await fetch(endpoint, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        // Фильтруем только активные заказы (не завершенные)
        const activeOrders = data.filter((order: any) => 
          order.status !== "completed" && 
          order.status !== "cancelled" && 
          order.status !== "failed"
        );
        setOrders(activeOrders);
      } else {
        const errorText = `Ошибка загрузки заказов: ${response.status} ${response.statusText}`;
        console.error(errorText);
        setOrdersError(errorText);
      }
    } catch (err) {
      const errorText = `Ошибка загрузки заказов: ${err}`;
      console.error(errorText);
      setOrdersError(errorText);
    } finally {
      setOrdersLoading(false);
    }
  };

  const fetchUserPermissions = async () => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch("/admin/profile/permissions", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setUserPermissions(data);
      }
    } catch (err) {
      console.error("Ошибка получения прав доступа:", err);
    }
  };

  const getOrderInfo = (orderId: number | null) => {
    if (!orderId) return null;
    const order = orders.find(o => o.id === orderId);
    if (order) {
      try {
        const orderData = JSON.parse(order.order_data);
        return {
          user_id: order.user_id,
          product: orderData.product || "Не указан",
          relation: orderData.relation || "Не указано",
          username: orderData.username || orderData.user_name || "Не указан"
        };
      } catch (parseError) {
        console.error(`Ошибка парсинга данных заказа ${orderId}:`, parseError);
        return { 
          user_id: order.user_id, 
          product: "Ошибка парсинга", 
          relation: "Ошибка парсинга",
          username: "Не указан"
        };
      }
    }
    return null;
  };

  const getMessageTypeLabel = (type: string) => {
    switch (type) {
      case "demo_example": return "Демо-пример";
      case "payment_reminder": return "Напоминание об оплате";
      case "final_reminder": return "Финальное напоминание";
      case "auto_order_created": return "Автоматическое сообщение о заказе";
      case "story_proposal": return "Предложение сюжетов";
      case "story_selection": return "Выбор сюжетов";
      case "payment_reminder_24h": return "Напоминание об оплате 1";
      case "payment_reminder_48h": return "Напоминание об оплате 2";
      case "song_feedback": return "Обратная связь по песне";
      case "song_warming_example": return "Прогревочное (пример)";
      case "song_warming_motivation": return "Прогревочное (мотивация)";
      case "story_placeholder": return "Заглушка сюжетов";
      // Новые типы для заполнения песни
      case "song_filling_reminder_20m": return "Песня ждёт";
      case "song_filling_reminder_30m": return "Песня ждет";
      case "song_filling_reminder_1h": return "Уникальная история";
      case "song_filling_reminder_2h": return "Попробуй бесплатно";
      case "song_filling_reminder_4h": return "Время летит";
      case "song_filling_reminder_8h": return "Персональная песня";
      // Новые типы для ожидания демо книги
      case "waiting_demo_book_20m": return "В самое сердце";
      case "waiting_demo_book_1h": return "История Раюши";
      case "waiting_demo_book_1_5h": return "Трогательные моменты";
      // Новые типы для ожидания демо песни
      case "waiting_demo_song_20m": return "Команда чувств";
      case "waiting_demo_song_1h": return "Трогательная история недели";
      case "waiting_demo_song_1_5h": return "Что удивляет больше всего";
      // Новые типы для получения демо книги
      case "demo_received_book_20m": return "Это навсегда";
      case "demo_received_book_1h": return "Пока мы не говорим главного";
      case "demo_received_book_1_5h": return "Смотри, что они творят";
      // Новые типы для получения демо песни
      case "demo_received_song_15m": return "Твоя мелодия готова";
      case "demo_received_song_1h": return "Слова, которые не успеваем";
      case "demo_received_song_3h": return "Когда звучит песня о тебе";
      // Новые типы для выбора сюжетов
      case "story_selection_1h": return "Твоя история ждет воплощения";
      // Новые типы для ответов на вопросы
      case "answering_questions_1h": return "Осталось совсем чуть-чуть";
      // Новые типы для ожидания основной книги
      case "waiting_main_book_1h": return "Бережно собираем вашу историю";
      // Новые типы для ожидания полной песни
      case "waiting_full_song_1h": return "Бережно создаем вашу мелодию";
      // Новые типы для заполнения книги
      case "book_filling_reminder_20m": return "Книга ждет";
      case "book_filling_reminder_1h": return "История превращается в сказку";
      case "book_filling_reminder_4h": return "Осталось чуть-чуть";
      case "book_filling_reminder_8h": return "До мурашек";
      case "book_filling_reminder_90m": return "Трогает больше всего (книги)";
      case "song_filling_reminder_90m": return "Удивляет больше всего (песни)";
      // Дополнительные напоминания для песен
      case "song_collecting_facts_1h_alt": return "Осталось совсем чуть-чуть";
      case "song_collecting_facts_3h": return "Финишная прямая";
      case "song_collecting_facts_6h": return "До музыки рукой подать";
      // Напоминания об оплате - книги
      case "book_payment_reminder_20m": return "Это навсегда (книги)";
      case "book_payment_reminder_1h": return "Пока мы не говорим главного (книги)";
      case "book_payment_reminder_3h": return "Смотри, что они творят (книги)";
      // Напоминания об оплате - песни
      case "song_payment_reminder_15m": return "Твоя мелодия готова";
      case "song_payment_reminder_1h": return "Слова, которые не успеваем";
      case "song_payment_reminder_3h": return "Когда звучит песня о тебе";
      // Выбор сюжетов
      case "story_selection_1h": return "Твоя история ждет воплощения";
      case "story_selection_3h": return "Какие моменты дороже всего?";
      case "story_selection_6h": return "Один шаг до слез счастья";
      // Создание книги
      case "book_creation_1h": return "Бережно собираем вашу историю";
      case "book_creation_5h": return "Как подаришь книгу?";
      case "book_creation_10h": return "Финальные штрихи";
      // Создание песни
      case "song_creation_1h": return "Бережно создаем вашу мелодию";
      case "song_creation_5h": return "Как подаришь песню?";
      case "song_creation_10h": return "Финальные ноты";
      default: return type;
    }
  };

  const getMessageTypeDescription = (type: string) => {
    switch (type) {
      case "demo_example": return "Демо-пример";
      case "payment_reminder": return "Напоминание об оплате";
      case "final_reminder": return "Финальное напоминание";
      case "story_proposal": return "Предложение сюжетов";
      case "story_selection": return "Выбор сюжетов";
      case "payment_reminder_24h": return "Через 24 часа";
      case "payment_reminder_48h": return "Через 48 часов";
      case "song_feedback": return "Обратная связь";
      case "song_warming_example": return "Пример песни";
      case "song_warming_motivation": return "Мотивация";
      case "story_placeholder": return "Заглушка";
      // Новые типы для заполнения песни
      case "song_filling_reminder_20m": return "Напоминание о незавершенной анкете";
      case "song_filling_reminder_30m": return "Напоминание о незавершенной анкете";
      case "song_filling_reminder_1h": return "Мотивационное сообщение";
      case "song_filling_reminder_2h": return "Предложение бесплатного демо";
      case "song_filling_reminder_4h": return "Мотивация к действию";
      case "song_filling_reminder_8h": return "Эмоциональное видео";
      // Новые типы для ожидания демо книги
      case "waiting_demo_book_20m": return "Эмоциональная мотивация";
      case "waiting_demo_book_1h": return "История с бабушкой";
      case "waiting_demo_book_1_5h": return "О важности воспоминаний";
      // Новые типы для ожидания демо песни
      case "waiting_demo_song_20m": return "Мотивация с видео реакции";
      case "waiting_demo_song_1h": return "История любви со школьной скамьи";
      case "waiting_demo_song_1_5h": return "О важности благодарности";
      // Новые типы для получения демо книги
      case "demo_received_book_20m": return "Подарок на всю жизнь";
      case "demo_received_book_1h": return "О важности не откладывать";
      case "demo_received_book_1_5h": return "Видео реакций на книги";
      // Новые типы для получения демо песни
      case "demo_received_song_15m": return "Потенциал демо-версии";
      case "demo_received_song_1h": return "Несказанные слова";
      case "demo_received_song_3h": return "Реакции на песни";
      // Новые типы для выбора сюжетов
      case "story_selection_1h": return "Ожидание воплощения";
      // Новые типы для ответов на вопросы
      case "answering_questions_1h": return "Мотивация композиторов";
      // Новые типы для ожидания основной книги
      case "waiting_main_book_1h": return "Бережное создание";
      // Новые типы для ожидания полной песни
      case "waiting_full_song_1h": return "Создание мелодии";
      // Новые типы для заполнения книги
      case "book_filling_reminder_20m": return "Напоминание о незавершенной анкете книги";
      case "book_filling_reminder_1h": return "Мотивация с акцентом на бесплатность";
      case "book_filling_reminder_4h": return "Поддержка при загрузке фото";
      case "book_filling_reminder_8h": return "Эмоциональное видео с реакциями";
      case "book_filling_reminder_90m": return "Что трогает больше всего";
      case "song_filling_reminder_90m": return "Что удивляет больше всего";
      // Дополнительные напоминания для песен
      case "song_collecting_facts_1h_alt": return "Мотивация композиторов";
      case "song_collecting_facts_3h": return "Финишная прямая";
      case "song_collecting_facts_6h": return "Готовность к созданию";
      // Напоминания об оплате - книги
      case "book_payment_reminder_20m": return "Подарок на всю жизнь";
      case "book_payment_reminder_1h": return "Важность слов";
      case "book_payment_reminder_3h": return "Реакции на книги";
      // Напоминания об оплате - песни
      case "song_payment_reminder_15m": return "Потенциал демо";
      case "song_payment_reminder_1h": return "Несказанные слова";
      case "song_payment_reminder_3h": return "Реакции на песни";
      // Выбор сюжетов
      case "story_selection_1h": return "Ожидание воплощения";
      case "story_selection_3h": return "Дорогие моменты";
      case "story_selection_6h": return "Радость близко";
      // Создание книги
      case "book_creation_1h": return "Бережное создание";
      case "book_creation_5h": return "Планирование подарка";
      case "book_creation_10h": return "Завершающий этап";
      // Создание песни
      case "song_creation_1h": return "Создание мелодии";
      case "song_creation_5h": return "Планирование сюрприза";
      case "song_creation_10h": return "Финальные ноты";
      default: return "Пользовательское сообщение";
    }
  };

  const getStatusLabel = (status: string, message: DelayedMessage) => {
    switch (status) {
      case "pending": return "Ожидает отправки";
      case "sent": return "✅ Отправлено";
      case "failed": return "Ошибка отправки";
      case "active": return "Активно";
      default: return status;
    }
  };

  const getStatusColor = (status: string, message: DelayedMessage) => {
    switch (status) {
      case "pending": return "bg-yellow-100 text-yellow-800";
      case "sent": return "bg-green-100 text-green-800";
      case "failed": return "bg-red-100 text-red-800";
      case "active": return "bg-blue-100 text-blue-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  const getOrderStepLabel = (orderStep: string) => {
    switch (orderStep) {
      case "product_selected": return "Заполнение данных для демо версий (Песня)";
      case "book_collecting_facts": return "Заполнение данных для пробной книги";
      case "waiting_demo_book": return "Ожидание демо-контента книга";
      case "waiting_demo_song": return "Ожидание демо-версии песни";
      case "demo_received_book": return "Получен демо-контент Книга";
      case "demo_received_song": return "Получен демо-версия песня";
      case "story_selection": return "Выбор сюжетов";
      case "answering_questions": return "Ответы на вопросы";
      case "waiting_main_book": return "Ожидание основной книги";
      case "waiting_full_song": return "Ожидание полная песня";
      // Старые этапы для совместимости
      case "waiting_for_payment": return "Ожидание оплаты";
      case "collecting_facts": return "Заполнение анкеты";
      case "song_collecting_facts": return "Заполнение анкеты песни";
      case "created": return "Создание заказа";
      case "waiting_manager": return "Ожидание менеджера";
      case "waiting_payment": return "Ожидание оплаты";
      case "completed": return "Завершен";
      default: return orderStep;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDelayTime = (minutes: number) => {
    if (minutes === 0) return 'Сразу';
    if (minutes < 60) return `${minutes} мин`;
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    if (remainingMinutes === 0) return `${hours} ч`;
    return `${hours} ч ${remainingMinutes} мин`;
  };

  // Функция для определения шага заказа
  const getOrderStep = (orderId: number | null): string => {
    if (!orderId) return "Не привязан к заказу";
    
    const order = orders.find(o => o.id === orderId);
    if (!order) return "Заказ не найден";
    
    try {
      const orderData = JSON.parse(order.order_data);
      const status = orderData.status || "pending";
      const product = orderData.product || "Книга";
      
      // Определяем шаг на основе статуса и типа продукта
      if (product === "Песня") {
        switch (status) {
          case "created": return "Глава 1 - Создание заказа";
          case "waiting_manager": return "Глава 2 - Демо-версия";
          case "waiting_payment": return "Глава 3 - Оплата";
          case "waiting_draft": return "Глава 4 - Предфинальная версия";
          case "editing": return "Глава 5 - Правки";
          case "prefinal_sent": return "Глава 6 - Финальная версия";
          case "completed": return "Глава 7 - Завершение";
          default: return "Неизвестный этап";
        }
      } else {
        switch (status) {
          case "created": return "Глава 1 - Создание заказа";
          case "character_created": return "Глава 2-3 - Создание персонажа";
          case "waiting_manager": return "Глава 4 - Демо-контент";
          case "waiting_payment": return "Глава 4 - Демо-контент";
          case "waiting_story_choice": return "Глава 5 - Выбор сюжетов";
          case "waiting_draft": return "Глава 6 - Черновик";
          case "waiting_cover_choice": return "Глава 7 - Выбор обложки";
          case "waiting_final": return "Глава 8 - Финальная версия";
          case "completed": return "Глава 8 - Завершение";
          default: return "Неизвестный этап";
        }
      }
    } catch (error) {
      return "Ошибка парсинга данных";
    }
  };

  const isGeneralMessage = (message: DelayedMessage) => {
    // Если флаг is_automatic установлен, используем его
    if (message.is_automatic !== undefined) {
      return message.is_automatic;
    }
    
    // Иначе определяем по типу сообщения и отсутствию order_id
    const generalMessageTypes = [
      'payment_reminder_24h', 
      'payment_reminder_48h',
      // Типы для заполнения анкеты песни
      'song_filling_reminder_20m',
      'song_filling_reminder_30m',
      'song_filling_reminder_1h', 
      'song_filling_reminder_2h',
      'song_filling_reminder_4h',
      'song_filling_reminder_8h',
      // Типы для заполнения анкеты книги
      'book_filling_reminder_20m',
      'book_filling_reminder_1h',
      'book_filling_reminder_4h', 
      'book_filling_reminder_8h',
      'book_filling_reminder_90m',
      // Типы для ожидания демо книги
      'waiting_demo_book_20m',
      'waiting_demo_book_1h',
      'waiting_demo_book_1_5h',
      // Типы для ожидания демо песни
      'waiting_demo_song_20m',
      'waiting_demo_song_1h',
      'waiting_demo_song_1_5h',
      // Типы для получения демо книги
      'demo_received_book_20m',
      'demo_received_book_1h',
      'demo_received_book_1_5h',
      // Типы для получения демо песни
      'demo_received_song_15m',
      'demo_received_song_1h',
      'demo_received_song_3h',
      // Типы для выбора сюжетов
      'story_selection_1h',
      // Типы для ответов на вопросы
      'answering_questions_1h',
      // Типы для ожидания основной книги
      'waiting_main_book_1h',
      // Типы для ожидания полной песни
      'waiting_full_song_1h'
    ];
    return generalMessageTypes.includes(message.message_type) && !message.order_id;
  };

  const filteredMessages = messages.filter(message => {
    // Фильтр по этапу заказа
    if (selectedStep !== "all") {
      // Для шаблонов (is_automatic = true) используем order_step
      if (isGeneralMessage(message)) {
        return message.order_step === selectedStep;
      }
      // Для обычных сообщений используем getOrderStep
      else if (message.order_id) {
        const orderStep = getOrderStep(message.order_id);
        return orderStep.includes(selectedStep);
      }
      return false;
    }
    
    return true;
  });


  // Фильтрация сообщений по активной вкладке
  const filteredMessagesByTab = filteredMessages.filter(message => {
    if (activeTab === 'general') {
      // Показываем все шаблоны (order_id IS NULL)
      return !message.order_id;
    } else {
      // Личные сообщения - с order_id
      return message.order_id;
    }
  });

  const handleCreateMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!newMessage.content) {
      setError("Заполните содержание сообщения");
      return;
    }

    if (!newMessage.order_step) {
      setError("Выберите шаг заказа");
      return;
    }

    setCreating(true);
    try {
      const token = localStorage.getItem("token");
      
      // Создаем отложенное сообщение (шаблон)
      const messageData = {
        order_id: null, // Шаблон не привязан к конкретному заказу
        message_type: newMessage.message_type,
        content: newMessage.content,
        delay_minutes: newMessage.delay_minutes,
        order_step: newMessage.order_step,
        is_automatic: true
      };
      
      const response = await fetch("/admin/delayed-messages", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(messageData),
      });

      if (response.ok) {
        // Загружаем файлы, если выбраны
        const created = await response.json();
        if (selectedFiles.length > 0 && created?.id) {
          try {
            const formData = new FormData();
            selectedFiles.forEach((file) => formData.append("files", file));
            const filesResp = await fetch(`/admin/message-templates/${created.id}/files`, {
              method: "POST",
              headers: { Authorization: `Bearer ${token}` },
              body: formData,
            });
            if (!filesResp.ok) {
              const err = await filesResp.json().catch(() => ({}));
              setError(err.detail || "Ошибка загрузки файлов для шаблона");
            }
          } catch {
            setError("Ошибка загрузки файлов для шаблона");
          }
        }

        setShowCreateForm(false);
        setNewMessage({
          order_id: "",
          message_type: "payment_reminder_24h",
          content: "",
          delay_minutes: 60,
          order_step: ""
        });
        setSelectedFiles([]);
        fetchDelayedMessages();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || "Ошибка создания шаблона сообщения");
      }
    } catch (err) {
      setError("Ошибка создания шаблона сообщения");
    } finally {
      setCreating(false);
    }
  };

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedFiles.length === 0) {
      setError("Выберите файлы для загрузки");
      return;
    }

    if (selectedFiles.length > 15) {
      setError("Максимальное количество файлов: 15");
      return;
    }

    setUploadingFiles(true);
    try {
      const token = localStorage.getItem("token");
      const formData = new FormData();
      
      selectedFiles.forEach(file => {
        formData.append('files', file);
      });

      const response = await fetch(`/admin/message-templates/${selectedMessageId}/files`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (response.ok) {
        setShowFileUpload(false);
        setSelectedFiles([]);
        setSelectedMessageId(null);
        fetchDelayedMessages();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || "Ошибка загрузки файлов");
      }
    } catch (err) {
      setError("Ошибка загрузки файлов");
    } finally {
      setUploadingFiles(false);
    }
  };

  const handleDeleteMessage = async (messageId: number) => {
    if (!window.confirm("Вы уверены, что хотите удалить это отложенное сообщение?")) {
      return;
    }

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/delayed-messages/${messageId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        fetchDelayedMessages();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || "Ошибка удаления отложенного сообщения");
      }
    } catch (err) {
      setError("Ошибка удаления отложенного сообщения");
    }
  };

  const handleToggleActive = async (messageId: number, currentStatus: boolean) => {
    setTogglingActive(messageId);
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/delayed-messages/${messageId}/toggle-active`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ is_active: !currentStatus }),
      });

      if (response.ok) {
        // Обновляем статус в локальном состоянии
        setMessages(messages.map(msg => 
          msg.id === messageId 
            ? { ...msg, is_active: !currentStatus }
            : msg
        ));
      } else {
        const errorData = await response.json();
        setError(errorData.detail || "Ошибка изменения статуса шаблона");
      }
    } catch (error) {
      setError("Ошибка изменения статуса шаблона");
    } finally {
      setTogglingActive(null);
    }
  };

  const handleEditMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingMessage) return;

    setEditing(true);
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/delayed-messages/${editingMessage.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: editForm.name,
          content: editForm.content,
          delay_minutes: editForm.delay_minutes,
          message_type: editForm.message_type,
          order_step: editForm.order_step
        }),
      });

      if (response.ok) {
        // Прикрепляем новые файлы если выбраны
        if (editSelectedFiles.length > 0) {
          try {
            const formData = new FormData();
            editSelectedFiles.forEach((file) => formData.append("files", file));
            const filesResp = await fetch(`/admin/message-templates/${editingMessage.id}/files`, {
              method: "POST",
              headers: { Authorization: `Bearer ${token}` },
              body: formData,
            });
            if (!filesResp.ok) {
              const err = await filesResp.json().catch(() => ({}));
              setError(err.detail || "Ошибка загрузки файлов при редактировании");
            }
          } catch {
            setError("Ошибка загрузки файлов при редактировании");
          }
        }
        setShowEditForm(false);
        setEditingMessage(null);
        setEditForm({ name: "", content: "", delay_minutes: 60, message_type: "", order_step: "" });
        setEditSelectedFiles([]);
        fetchDelayedMessages();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || "Ошибка обновления сообщения");
      }
    } catch (err) {
      setError("Ошибка обновления сообщения");
    } finally {
      setEditing(false);
    }
  };

  const startEditing = (message: DelayedMessage) => {
    setEditingMessage(message);
    setEditForm({
      name: message.name || getMessageTypeLabel(message.message_type),
      content: message.content,
      delay_minutes: message.delay_minutes,
      message_type: message.message_type,
      order_step: message.order_step || ""
    });
    setEditSelectedFiles([]);
    setShowEditForm(true);
  };

  const handleDeleteFile = async (messageId: number, fileId: number | string, fileName: string) => {
    try {
      const token = localStorage.getItem("token");
      
      // Если fileId - это ID файла, используем API с ID
      // Если это индекс, то используем имя файла как идентификатор
      const endpoint = typeof fileId === 'number' && fileId > 0 
        ? `/admin/message-templates/${messageId}/files/${fileId}`
        : `/admin/message-templates/${messageId}/files?file_name=${encodeURIComponent(fileName)}`;
      
      const response = await fetch(endpoint, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        // Обновляем список сообщений чтобы отобразить изменения
        fetchDelayedMessages();
        // Обновляем editingMessage чтобы убрать удаленный файл из интерфейса
        if (editingMessage) {
          const updatedFiles = editingMessage.files?.filter((file) => 
            typeof fileId === 'number' && fileId > 0 
              ? file.id !== fileId 
              : file.file_name !== fileName
          ) || [];
          setEditingMessage({
            ...editingMessage,
            files: updatedFiles
          });
        }
      } else {
        const errorData = await response.json();
        setError(errorData.detail || "Ошибка удаления файла");
      }
    } catch (err) {
      setError("Ошибка удаления файла");
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    
    // Проверяем количество файлов
    if (files.length > 15) {
      setError("Максимальное количество файлов: 15");
      return;
    }
    
    // Проверяем типы файлов - расширенный список
    const allowedTypes = [
      // Изображения
      'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/tiff', 'image/svg+xml',
      // Аудио
      'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg', 'audio/mp4', 'audio/m4a', 'audio/wma', 'audio/aac', 
      'audio/flac', 'audio/opus', 'audio/amr', 'audio/midi', 'audio/mid', 'audio/xmf', 'audio/rtttl', 
      'audio/smf', 'audio/imy', 'audio/rtx', 'audio/ota', 'audio/jad', 'audio/jar',
      // Видео
      'video/mp4', 'video/avi', 'video/mov', 'video/quicktime', 'video/webm', 'video/x-matroska', 'video/mkv', 
      'video/flv', 'video/wmv', 'video/m4v', 'video/3gp', 'video/ogv',
      // Документы
      'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'text/plain', 'text/csv', 'application/rtf', 'application/zip', 'application/x-rar-compressed',
      'application/x-7z-compressed', 'application/x-tar', 'application/gzip'
    ];
    const invalidFiles = files.filter(file => !allowedTypes.includes(file.type));
    
    if (invalidFiles.length > 0) {
      setError(`Неподдерживаемые типы файлов: ${invalidFiles.map(f => f.name).join(', ')}`);
      return;
    }
    
    setSelectedFiles(files);
    setError(""); // Очищаем предыдущие ошибки
  };

  // Расширенный список поддерживаемых форматов файлов
  const allowedImageTypes = [
    'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/tiff', 'image/svg+xml'
  ];
  
  const allowedVideoTypes = [
    'video/mp4', 'video/mov', 'video/avi', 'video/mkv', 'video/flv', 'video/wmv', 
    'video/m4v', 'video/3gp', 'video/ogv', 'video/webm', 'video/quicktime'
  ];
  
  const allowedAudioTypes = [
    'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4', 'audio/m4a', 'audio/wma', 
    'audio/aac', 'audio/flac', 'audio/opus', 'audio/amr', 'audio/midi', 'audio/mid',
    'audio/xmf', 'audio/rtttl', 'audio/smf', 'audio/imy', 'audio/rtx', 'audio/ota',
    'audio/jad', 'audio/jar'
  ];
  
  const allowedDocumentTypes = [
    'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain', 'text/html', 'text/css', 'text/javascript', 'application/json',
    'application/xml', 'text/xml', 'text/csv', 'application/rtf',
    'application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed',
    'application/x-tar', 'application/gzip'
  ];
  
  const allAllowedTypes = [...allowedImageTypes, ...allowedVideoTypes, ...allowedAudioTypes, ...allowedDocumentTypes];


  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-center">Загрузка отложенных сообщений...</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <div className="mb-6">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Шаблоны сообщений</h1>
            <p className="text-sm text-gray-600 mt-1">
              Автоматические сообщения для пользователей на определенных шагах заказа
            </p>
          </div>
          {userPermissions?.is_super_admin && (
            <Button onClick={() => setShowCreateForm(true)}>
              Создать шаблон
            </Button>
          )}
        </div>

        {/* Инструкция по шаблонам сообщений */}
        <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 mb-4">
          <h3 className="text-lg font-semibold text-blue-300 mb-3">📋 Как работают шаблоны сообщений</h3>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium text-blue-300 mb-2">🎯 Принцип работы:</h4>
              <ul className="text-sm text-blue-200 space-y-2">
                <li><strong>Автоматическая отправка:</strong> Система проверяет всех пользователей на определенном шаге заказа</li>
                <li><strong>По таймеру:</strong> Сообщения отправляются через указанное время после попадания на шаг</li>
                <li><strong>Без дублирования:</strong> Каждому пользователю сообщение отправляется только один раз</li>
                <li><strong>Умная фильтрация:</strong> Не отправляются пользователям с оплаченными заказами</li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-medium text-blue-300 mb-2">⚙️ Настройка шаблонов:</h4>
              <ul className="text-sm text-blue-200 space-y-2">
                <li><strong>Этап:</strong> На каком этапе отправлять сообщение</li>
                <li><strong>Задержка:</strong> Через сколько времени после попадания на шаг</li>
                <li><strong>Тип сообщения:</strong> Напоминания, демо-примеры, предложения сюжетов</li>
                <li><strong>Содержание:</strong> Текст сообщения для пользователей</li>
              </ul>
            </div>
          </div>
        </div>

        {!userPermissions?.is_super_admin && (
          <div className="bg-yellow-900 border border-yellow-500 text-white px-4 py-3 rounded mb-4">
            <strong>⚠️ Ограничение:</strong> Вы можете только просматривать отложенные сообщения. Для редактирования сообщений требуются права главного администратора.
          </div>
        )}

        {/* Вкладки для переключения между разделами */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('general')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'general'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Общие сообщения
            </button>
            {/* Личные сообщения скрыты, но код оставлен */}
            {false && (
              <button
                onClick={() => setActiveTab('personal')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'personal'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Личные сообщения
              </button>
            )}
          </nav>
        </div>

        {/* Фильтры */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-3">
          <div className="md:col-span-4 flex justify-between items-center">
            <p className="text-sm text-gray-600">
              Показано {filteredMessagesByTab.length} из {filteredMessages.length} шаблонов сообщений
            </p>
            {selectedStep !== "all" && (
              <Button
                type="button"
                onClick={() => {
                  setSelectedStep("all");
                }}
                className="text-sm bg-gray-500 hover:bg-gray-600 text-white"
              >
                Сбросить фильтры
              </Button>
            )}
          </div>
          <div className="flex flex-wrap gap-3 mb-4">
        <select
          className="filter-input border rounded bg-gray-800 text-white"
          value={selectedStep}
          onChange={(e) => setSelectedStep(e.target.value)}
        >
          <option value="all">Все этапы</option>
          <option value="product_selected">Заполнение данных для демо версий (Песня)</option>
          <option value="book_collecting_facts">Заполнение данных для пробной книги</option>
          <option value="waiting_demo_book">Ожидание демо-контента книга</option>
          <option value="waiting_demo_song">Ожидание демо-версии песни</option>
          <option value="demo_received_book">Получен демо-контент Книга</option>
          <option value="demo_received_song">Получен демо-версия песня</option>
          <option value="story_selection">Выбор сюжетов</option>
          <option value="answering_questions">Ответы на вопросы</option>
          <option value="waiting_main_book">Ожидание основной книги</option>
          <option value="waiting_full_song">Ожидание полная песня</option>
        </select>
      </div>
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}
      </div>

      {/* Форма создания нового шаблона */}
      {showCreateForm && (
        <Card className="p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">Создать шаблон сообщения</h2>
          <form onSubmit={handleCreateMessage} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2 text-gray-900">Тип сообщения:</label>
              <select
                value={newMessage.message_type}
                onChange={(e) => setNewMessage({...newMessage, message_type: e.target.value})}
                className="border border-gray-300 rounded px-3 py-2 w-full"
              >
                <option value="payment_reminder_24h">Напоминание об оплате 1</option>
                <option value="payment_reminder_48h">Напоминание об оплате 2</option>
                <option value="song_filling_reminder_30m">Песня ждет</option>
                <option value="song_filling_reminder_1h">Уникальная история</option>
                <option value="song_filling_reminder_2h">Попробуй бесплатно</option>
                <option value="song_filling_reminder_4h">Время летит</option>
                <option value="song_filling_reminder_8h">Персональная песня</option>
                <option value="book_filling_reminder_20m">Книга ждет</option>
                <option value="book_filling_reminder_1h">История превращается в сказку</option>
                <option value="book_filling_reminder_4h">Осталось чуть-чуть</option>
                <option value="book_filling_reminder_8h">До мурашек</option>
                <option value="book_filling_reminder_90m">Трогает больше всего (книги)</option>
                <option value="song_filling_reminder_90m">Удивляет больше всего (песни)</option>
                <option value="song_collecting_facts_1h_alt">Осталось совсем чуть-чуть</option>
                <option value="song_collecting_facts_3h">Финишная прямая</option>
                <option value="song_collecting_facts_6h">До музыки рукой подать</option>
                <option value="book_payment_reminder_20m">Это навсегда (книги)</option>
                <option value="book_payment_reminder_1h">Пока мы не говорим главного (книги)</option>
                <option value="book_payment_reminder_3h">Смотри, что они творят (книги)</option>
                <option value="song_payment_reminder_15m">Твоя мелодия готова</option>
                <option value="song_payment_reminder_1h">Слова, которые не успеваем</option>
                <option value="song_payment_reminder_3h">Когда звучит песня о тебе</option>
                <option value="story_selection_1h">Твоя история ждет воплощения</option>
                <option value="story_selection_3h">Какие моменты дороже всего?</option>
                <option value="story_selection_6h">Один шаг до слез счастья</option>
                <option value="book_creation_1h">Бережно собираем вашу историю</option>
                <option value="book_creation_5h">Как подаришь книгу?</option>
                <option value="book_creation_10h">Финальные штрихи</option>
                <option value="song_creation_1h">Бережно создаем вашу мелодию</option>
                <option value="song_creation_5h">Как подаришь песню?</option>
                <option value="song_creation_10h">Финальные ноты</option>
                <option value="demo_example">Демо-пример</option>
                <option value="story_proposal">Предложение сюжетов</option>
                <option value="story_selection">Выбор сюжетов</option>
                <option value="song_feedback">Обратная связь по песне</option>
              </select>
              {newMessage.message_type && (
                <p className="text-sm text-gray-600 mt-1 italic">
                  {getMessageTypeDescription(newMessage.message_type)}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium mb-2 text-gray-900">Этап:</label>
              <select
                value={newMessage.order_step}
                onChange={(e) => setNewMessage({...newMessage, order_step: e.target.value})}
                className="border border-gray-300 rounded px-3 py-2 w-full"
                required
              >
                <option value="">Выберите шаг</option>
                <option value="song_collecting_facts">Заполнение анкеты песни</option>
                <option value="book_collecting_facts">Заполнение анкеты книги</option>
                <option value="waiting_for_payment">Ожидание оплаты</option>
                <option value="waiting_for_email">Ожидание email</option>
                <option value="waiting_for_privacy_consent">Ожидание согласия на обработку данных</option>
                <option value="waiting_for_hero_photos">Ожидание фото главного героя</option>
                <option value="waiting_for_other_heroes">Ожидание фото других героев</option>
                <option value="waiting_for_story_selection">Ожидание выбора сюжета</option>
                <option value="waiting_for_style_selection">Ожидание выбора стиля</option>
                <option value="waiting_for_voice_selection">Ожидание выбора голоса</option>
                <option value="waiting_for_draft">Ожидание черновика</option>
                <option value="waiting_for_final">Ожидание финальной версии</option>
              </select>
              <p className="text-sm text-gray-600 mt-1 italic">
                Сообщение будет отправлено всем пользователям на этом этапе
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2 text-gray-900">Содержание:</label>
              <textarea
                value={newMessage.content}
                onChange={(e) => setNewMessage({...newMessage, content: e.target.value})}
                className="border border-gray-300 rounded px-3 py-2 w-full h-32"
                placeholder="Введите текст сообщения..."
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2 text-gray-900">
                Задержка отправки:
              </label>
              <div className="flex gap-2 items-center">
                <input
                  type="number"
                  min="0"
                  value={Math.floor(newMessage.delay_minutes / 60)}
                  onChange={(e) => {
                    const hours = Number(e.target.value) || 0;
                    const minutes = newMessage.delay_minutes % 60;
                    setNewMessage({...newMessage, delay_minutes: hours * 60 + minutes});
                  }}
                  className="border border-gray-300 rounded px-3 py-2 w-1/3"
                  placeholder="0"
                />
                <span className="text-gray-500">ч</span>
                <input
                  type="number"
                  min="0"
                  max="59"
                  value={newMessage.delay_minutes % 60}
                  onChange={(e) => {
                    const hours = Math.floor(newMessage.delay_minutes / 60);
                    const minutes = Number(e.target.value) || 0;
                    setNewMessage({...newMessage, delay_minutes: hours * 60 + minutes});
                  }}
                  className="border border-gray-300 rounded px-3 py-2 w-1/3"
                  placeholder="0"
                />
                <span className="text-gray-500">мин</span>
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Итого: {formatDelayTime(newMessage.delay_minutes)}
              </div>
            </div>

            {/* Загрузка файлов при создании */}
            <div>
              <label className="block text-sm font-medium mb-2 text-gray-900">Файлы (необязательно):</label>
              <input
                type="file"
                multiple
                accept={allAllowedTypes.join(',')}
                onChange={handleFileSelect}
                className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
              {selectedFiles.length > 0 && (
                <div className="mt-2 text-xs text-gray-600">
                  Выбрано файлов: {selectedFiles.length}
                </div>
              )}
            </div>

            <div className="flex space-x-2 mt-4">
              <Button type="submit" disabled={creating}>
                {creating ? "Создание..." : "Создать шаблон"}
              </Button>
              <Button
                type="button"
                className="bg-gray-500 hover:bg-gray-600 text-white"
                onClick={() => {
                  setShowCreateForm(false);
                  setNewMessage({
                    order_id: "",
                    message_type: "payment_reminder_24h",
                    content: "",
                    delay_minutes: 60,
                    order_step: ""
                  });
                  setError("");
                  setSelectedFiles([]);
                }}
              >
                Отмена
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* Форма загрузки файлов */}
      {showFileUpload && (
        <Card className="p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">Добавить файлы к сообщению</h2>
          <form onSubmit={handleFileUpload} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2 text-gray-900">
                Выберите файлы (максимум 15, поддерживаются все типы файлов):
              </label>
              <input
                type="file"
                multiple
                accept={allAllowedTypes.join(',')}
                onChange={(e) => setSelectedFiles(Array.from(e.target.files || []))}
                className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
              <p className="text-sm text-gray-600 mt-1">
                Выбрано файлов: {selectedFiles.length}
              </p>
            </div>

            {selectedFiles.length > 0 && (
              <div>
                <label className="block text-sm font-medium mb-2 text-gray-900">Выбранные файлы:</label>
                <div className="max-h-40 overflow-y-auto border border-gray-300 rounded p-2">
                  {selectedFiles.map((file, index) => (
                    <div key={index} className="text-sm text-gray-700 py-1">
                      {file.name} ({formatFileSize(file.size)})
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex space-x-2">
              <Button type="submit" disabled={uploadingFiles}>
                {uploadingFiles ? "Загрузка..." : "Загрузить файлы"}
              </Button>
              <Button
                type="button"
                className="bg-gray-500 hover:bg-gray-600 text-white"
                onClick={() => {
                  setShowFileUpload(false);
                  setSelectedFiles([]);
                  setSelectedMessageId(null);
                }}
              >
                Отмена
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* Модальное окно редактирования сообщения */}
      {showEditForm && editingMessage && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setShowEditForm(false);
              setEditingMessage(null);
              setEditForm({ name: "", content: "", delay_minutes: 60, message_type: "", order_step: "" });
              setEditSelectedFiles([]);
            }
          }}
        >
          <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto mx-4">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Редактировать сообщение</h2>
              <button
                type="button"
                onClick={() => {
                  setShowEditForm(false);
                  setEditingMessage(null);
                  setEditForm({ name: "", content: "", delay_minutes: 60, message_type: "", order_step: "" });
                  setEditSelectedFiles([]);
                }}
                className="text-gray-400 hover:text-gray-600 text-xl font-bold"
              >
                ×
              </button>
            </div>
          <form onSubmit={handleEditMessage} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2 text-gray-900">
                Название:
              </label>
              <input
                type="text"
                value={editForm.name}
                onChange={(e) => setEditForm({...editForm, name: e.target.value})}
                className="border border-gray-300 rounded px-3 py-2 w-full"
                placeholder="Введите название сообщения..."
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2 text-gray-900">
                Этап:
              </label>
              <select
                value={editForm.order_step}
                onChange={(e) => setEditForm({...editForm, order_step: e.target.value})}
                className="border border-gray-300 rounded px-3 py-2 w-full"
                required
              >
                <option value="">Выберите этап</option>
                <option value="product_selected">Заполнение данных для демо версий (Песня)</option>
                <option value="book_collecting_facts">Заполнение данных для пробной книги</option>
                <option value="waiting_demo_book">Ожидание демо-контента книга</option>
                <option value="waiting_demo_song">Ожидание демо-версии песни</option>
                <option value="demo_received_book">Получен демо-контент Книга</option>
                <option value="demo_received_song">Получен демо-версия песня</option>
                    <option value="story_selection">Выбор сюжетов</option>
                <option value="answering_questions">Ответы на вопросы</option>
                <option value="waiting_main_book">Ожидание основной книги</option>
                <option value="waiting_full_song">Ожидание полная песня</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2 text-gray-900">
                Содержание:
              </label>
              <textarea
                value={editForm.content}
                onChange={(e) => setEditForm({...editForm, content: e.target.value})}
                className="border border-gray-300 rounded px-3 py-2 w-full h-32"
                placeholder="Введите текст сообщения..."
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2 text-gray-900">
                Задержка:
              </label>
              <div className="flex gap-2 items-center">
                <Input
                  type="number"
                  min="0"
                  value={Math.floor(editForm.delay_minutes / 60)}
                  onChange={(e) => {
                    const hours = Number(e.target.value) || 0;
                    const minutes = editForm.delay_minutes % 60;
                    setEditForm({...editForm, delay_minutes: hours * 60 + minutes});
                  }}
                  className="w-1/3"
                  placeholder="0"
                />
                <span className="text-gray-500">ч</span>
                <Input
                  type="number"
                  min="0"
                  max="59"
                  value={editForm.delay_minutes % 60}
                  onChange={(e) => {
                    const hours = Math.floor(editForm.delay_minutes / 60);
                    const minutes = Number(e.target.value) || 0;
                    setEditForm({...editForm, delay_minutes: hours * 60 + minutes});
                  }}
                  className="w-1/3"
                  placeholder="0"
                />
                <span className="text-gray-500">мин</span>
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Итого: {formatDelayTime(editForm.delay_minutes)}
              </div>
            </div>

            {/* Существующие файлы */}
            {editingMessage && editingMessage.files && editingMessage.files.length > 0 && (
              <div>
                <label className="block text-sm font-medium mb-2 text-gray-900">Прикрепленные файлы:</label>
                <div className="space-y-2">
                  {editingMessage.files.map((file, index) => (
                    <div key={index} className="flex items-center justify-between bg-gray-50 p-2 rounded">
                      <div className="text-sm text-gray-700">
                        <span className="font-medium">{file.file_name}</span>
                        <span className="text-gray-500 ml-2">({formatFileSize(file.file_size)})</span>
                      </div>
                      <Button
                        type="button"
                        onClick={() => handleDeleteFile(editingMessage.id, file.id || index, file.file_name)}
                        className="text-xs bg-red-500 hover:bg-red-600 text-white px-2 py-1"
                      >
                        Удалить
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Выбор файлов при редактировании */}
            <div>
              <label className="block text-sm font-medium mb-2 text-gray-900">Добавить файлы (необязательно):</label>
              <input
                type="file"
                multiple
                accept={allAllowedTypes.join(',')}
                onChange={(e) => setEditSelectedFiles(Array.from(e.target.files || []))}
                className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
              {editSelectedFiles.length > 0 && (
                <div className="mt-2 text-xs text-gray-600">
                  Выбрано файлов: {editSelectedFiles.length}
                </div>
              )}
            </div>

            <div className="flex space-x-2 mt-4">
              <Button type="submit" disabled={editing}>
                {editing ? "Сохранение..." : "Сохранить изменения"}
              </Button>
              <Button
                type="button"
                className="bg-gray-500 hover:bg-gray-600 text-white"
                onClick={() => {
                  setShowEditForm(false);
                  setEditingMessage(null);
                  setEditForm({ name: "", content: "", delay_minutes: 60, message_type: "", order_step: "" });
                  setEditSelectedFiles([]);
                }}
              >
                Отмена
              </Button>
            </div>
          </form>
          </div>
        </div>
      )}

      {/* Список отложенных сообщений */}
      <div className="space-y-4">
        {filteredMessagesByTab.map((message) => {
          const orderInfo = getOrderInfo(message.order_id);
          const isActive = message.is_active !== false; // По умолчанию активен, если не указано иное
          
          return (
            <Card key={message.id} className={`p-4 ${!isActive ? 'opacity-60 bg-gray-50' : ''}`}>
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-2">
                    <span className="text-sm font-medium text-gray-900">
                      {message.name || getMessageTypeLabel(message.message_type)}
                    </span>
                    <span className={`px-2 py-1 rounded text-xs ${
                      isActive 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {isActive ? '🟢 Активен' : '⚫ Неактивен'}
                    </span>
                    {message.usage_count && (
                      <span className="px-2 py-1 rounded text-xs bg-blue-100 text-blue-800">
                        📊 {message.usage_count} использований
                      </span>
                    )}
                    {message.last_used && (
                      <span className="px-2 py-1 rounded text-xs bg-purple-100 text-purple-800">
                        🕒 {new Date(message.last_used).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                  
                  <div className="text-sm space-y-1 text-gray-800">
                    <div><strong className="text-gray-900">Тип:</strong> {getMessageTypeLabel(message.message_type)}</div>
                    <div className="text-xs text-gray-600 italic">
                      {getMessageTypeDescription(message.message_type)}
                    </div>
                    {isGeneralMessage(message) && (
                      <div className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs inline-block">
                        🤖 Автоматическое
                      </div>
                    )}
                    {isGeneralMessage(message) && message.order_step && (
                      <div><strong className="text-gray-900">Этап:</strong> {getOrderStepLabel(message.order_step)}</div>
                    )}
                    {message.story_batch && (
                      <div><strong className="text-gray-900">Партия сюжетов:</strong> {message.story_batch}</div>
                    )}
                    {message.story_pages && (
                      <div><strong className="text-gray-900">Страницы:</strong> {message.story_pages}</div>
                    )}
                    {message.selected_stories && (
                      <div><strong className="text-gray-900">Выбрано сюжетов:</strong> {message.selected_stories}</div>
                    )}
                    <div><strong className="text-gray-900">Задержка:</strong> {formatDelayTime(message.delay_minutes)}</div>
                    <div><strong className="text-gray-900">Создано:</strong> {new Date(message.created_at).toLocaleString()}</div>
                    {message.scheduled_at ? (
                      <div><strong className="text-gray-900">Запланировано:</strong> {new Date(message.scheduled_at).toLocaleString()}</div>
                    ) : (
                      <div><strong className="text-gray-900">Запланировано:</strong> <span className="text-blue-600">Не привязано к времени</span></div>
                    )}
                    {message.sent_at && (
                      <div><strong className="text-gray-900">Отправлено:</strong> {new Date(message.sent_at).toLocaleString()}</div>
                    )}
                    {message.order_id && orderInfo && !isGeneralMessage(message) && (
                      <>
                        <div><strong className="text-gray-900">Продукт:</strong> {orderInfo.product}</div>
                        <div><strong className="text-gray-900">Отношение:</strong> {orderInfo.relation}</div>
                        <div><strong className="text-gray-900">Пользователь:</strong> {orderInfo.user_id}</div>
                        <div><strong className="text-gray-900">Текущий шаг:</strong> <span className="text-blue-600">{getOrderStep(message.order_id)}</span></div>
                      </>
                    )}
                    {!message.order_id && !isGeneralMessage(message) && (
                      <div><strong className="text-gray-900">Заказ:</strong> <span className="text-red-500">Не указан</span></div>
                    )}
                    {message.order_id && !isGeneralMessage(message) && (
                      <div><strong className="text-gray-900">Текущий шаг:</strong> <span className="text-blue-600">{getOrderStep(message.order_id)}</span></div>
                    )}
                    {message.files && message.files.length > 0 && (
                      <div>
                        <strong className="text-gray-900">Файлы:</strong> {message.files.length} шт.
                        <div className="mt-1 space-y-1">
                          {message.files.map((file, index) => (
                            <div key={index} className="text-xs text-gray-600 ml-2">
                              {file.file_name} ({formatFileSize(file.file_size)}) - {file.file_type}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  
                  <div className="mt-3">
                    <div className="text-sm font-medium mb-1 text-gray-900">Содержание:</div>
                    <div className="bg-gray-50 p-3 rounded text-sm text-gray-800">
                      {message.content}
                    </div>
                  </div>
                </div>

                <div className="ml-4 space-y-2">
                  {userPermissions?.is_super_admin && (
                    <Button
                      onClick={() => handleToggleActive(message.id, isActive)}
                      className={`text-sm ${
                        isActive 
                          ? 'bg-orange-500 hover:bg-orange-600' 
                          : 'bg-green-500 hover:bg-green-600'
                      } text-white`}
                      disabled={togglingActive === message.id}
                    >
                      {togglingActive === message.id 
                        ? '...' 
                        : isActive 
                          ? 'Деактивировать' 
                          : 'Активировать'
                      }
                    </Button>
                  )}
                  {userPermissions?.is_super_admin && (
                    <Button
                      onClick={() => startEditing(message)}
                      className="text-sm bg-blue-500 hover:bg-blue-600 text-white"
                    >
                      Редактировать
                    </Button>
                  )}
                  {userPermissions?.is_super_admin && (
                    <Button
                      onClick={() => handleDeleteMessage(message.id)}
                      className="text-sm bg-red-500 hover:bg-red-600 text-white"
                    >
                      Удалить
                    </Button>
                  )}
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {filteredMessagesByTab.length === 0 && (
        <div className="text-center text-gray-700 mt-8">
          Нет шаблонов сообщений. Создайте первый шаблон для автоматической отправки сообщений пользователям.
        </div>
      )}
    </div>
  );
}; 

export default DelayedMessagesPage;