import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { translateStatus } from "../utils/statusTranslations";

// CSS-классы для плавных переходов
const smoothTransitionClasses = {
  fadeIn: "opacity-0 transition-opacity duration-300 ease-in-out",
  fadeInVisible: "opacity-100 transition-opacity duration-300 ease-in-out",
  slideIn: "transform translate-y-2 opacity-0 transition-all duration-300 ease-out",
  slideInVisible: "transform translate-y-0 opacity-100 transition-all duration-300 ease-out",
  loading: "animate-pulse transition-opacity duration-200",
  success: "bg-green-600 bg-opacity-20 border-green-500 transition-all duration-300",
  error: "bg-red-600 bg-opacity-20 border-red-500 transition-all duration-300"
};

interface Order {
  id: number;
  user_id: number;
  telegram_id?: number;
  status: string;
  order_data: string;
  pdf_path?: string;
  mp3_path?: string;
  email?: string;
  username?: string;
  first_name?: string;
  last_name?: string;
  first_last_design?: string;
  first_page_text?: string;
  last_page_text?: string;
  created_at: string;
  updated_at: string;
}

// Интерфейс для шаблонов обложек
interface CoverTemplate {
  id: number;
  name: string;
  filename: string;
  category: string;
  created_at: string;
}

// Новый интерфейс для шагов рабочего процесса
// Интерфейс WorkflowStep удален по запросу пользователя

// Интерфейс для триггерных сообщений
interface TriggerMessage {
  message_type: string;
  count: number;
  message_ids: string;
  next_scheduled: string;
}

function parseOrderData(order_data: string) {
  try {
    const parsed = JSON.parse(order_data);
    return parsed;
  } catch (error) {
    console.error("Error parsing order data:", error);
    return {};
  }
}

// Компонент для отображения шагов рабочего процесса
// Компонент WorkflowSteps удален по запросу пользователя



const steps = [
  { key: "created", label: "Старт" },
  { key: "product_selected", label: "Выбор продукта" },
  { key: "character_created", label: "Создание персонажа" },
  { key: "waiting_manager", label: "Демо" },
  { key: "waiting_payment", label: "Ожидание оплаты" },
  { key: "paid", label: "Оплачено" },
  { key: "warming_messages", label: "Прогревочные сообщения" },
  { key: "waiting_final", label: "Финальная версия" },
  { key: "completed", label: "Завершено" },
];

function getActiveStep(status: string) {
  switch (status) {
    case "created": return 1; // Старт
    case "product_selected": return 2; // Выбор продукта
    case "gender_selected": return 2; // Выбран пол
    case "first_name_entered": return 2; // Введено имя
    case "relation_selected": return 2; // Выбран получатель
    case "character_description_entered": return 2; // Описание персонажа
    case "gift_reason_entered": return 2; // Введен повод
    case "main_photos_uploaded": return 2; // Загружены фото основного героя
    case "hero_name_entered": return 2; // Введено имя второго героя
    case "hero_description_entered": return 2; // Описание второго персонажа
    case "hero_photos_uploaded": return 2; // Загружены фото второго героя
    case "joint_photo_uploaded": return 2; // Загружено совместное фото
    case "style_selected": return 2; // Выбран стиль
    case "recipient_selected": return 2; // Выбран получатель (для песен)
    case "recipient_name_entered": return 3; // Введено имя получателя (для песен)
    case "character_created": return 3; // Создание персонажа
    case "photos_uploaded": return 3; // Создание персонажа
    case "collecting_facts": return 4; // Сбор фактов
    case "questions_completed": return 4; // Демо
    case "waiting_manager": return 4; // Демо
    case "demo_sent": return 4; // Демо
    case "demo_content": return 4; // Демо контент
    case "story_options_sent": return 4; // Демо
    case "waiting_payment": return 5; // Ожидание оплаты
    case "payment_pending": return 5; // Ожидание оплаты
    case "paid": return 6; // Оплачено
    case "waiting_draft": return 6; // Ожидание черновика (для песен)
    case "draft_sent": return 9; // Черновик отправлен (завершено)
    case "editing": return 7; // Внесение правок
    case "warming_messages": return 7; // Прогревочные сообщения
    case "waiting_delivery": return 8; // Ожидание доставки
    case "waiting_final": return 8; // Ожидание финальной версии
    case "final_sent": return 9; // Финальная версия отправлена (завершено)
    case "ready": return 9; // Финальная версия готова
    case "delivered": return 9; // Завершено
    case "completed": return 9; // Завершено
    default: return 1; // По умолчанию показываем "Старт"
  }
}

function getTimeSince(dateStr: string) {
  if (!dateStr) return "неизвестно";
  
  const now = new Date();
  const date = new Date(dateStr);
  
  // Проверяем, что дата валидна
  if (isNaN(date.getTime())) return "неизвестно";
  
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000); // seconds
  
  if (diff < 0) return "недавно"; // Если дата в будущем
  if (diff < 60) return `${diff} сек. назад`;
  if (diff < 3600) return `${Math.floor(diff / 60)} мин. назад`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} ч. назад`;
  if (diff < 2592000) return `${Math.floor(diff / 86400)} дн. назад`;
  return `${Math.floor(diff / 2592000)} мес. назад`;
}

// Функции для перевода ответов на русский по вопросам
function translateAnswer(answer: string, questionType?: string, relation?: string): string {
  const numAnswer = String(answer);
  
  // Если это уже текст, возвращаем как есть
  if (isNaN(Number(answer))) {
    return answer;
  }
  
  // Переводим числовые ответы в зависимости от вопроса и отношения
  switch (questionType) {
    case 'q1': // Первый вопрос
      if (relation === 'Маме' || relation === 'маме') {
        switch (numAnswer) {
          case "0": return "Гулять";
          case "1": return "Пить чай";
          case "2": return "Магазины";
          default: return answer;
        }
      } else if (relation === 'Папе' || relation === 'папе') {
        switch (numAnswer) {
          case "0": return "Играть";
          case "1": return "Кататься на машине";
          case "2": return "Строить";
          default: return answer;
        }
      } else if (relation === 'Брату' || relation === 'брату') {
        switch (numAnswer) {
          case "0": return "Игры";
          case "1": return "Кататься на великах";
          case "2": return "Смотреть фильмы";
          default: return answer;
        }
      } else if (relation === 'Любимому' || relation === 'любимому') {
        switch (numAnswer) {
          case "0": return "Смотреть фильмы";
          case "1": return "Готовить";
          case "2": return "Путешествовать";
          default: return answer;
        }
      } else if (relation === 'Подруге' || relation === 'подруге') {
        switch (numAnswer) {
          case "0": return "Болтаем";
          case "1": return "Ходим по кафе";
          case "2": return "Путешествуем";
          default: return answer;
        }
      } else if (relation === 'Бабушке' || relation === 'бабушке') {
        switch (numAnswer) {
          case "0": return "Пекли";
          case "1": return "Вязали";
          case "2": return "Читали сказки";
          default: return answer;
        }
      } else if (relation === 'Дедушке' || relation === 'дедушке') {
        switch (numAnswer) {
          case "0": return "Ремонтировать";
          case "1": return "Играть в шахматы";
          case "2": return "Гулять в парке";
          default: return answer;
        }
      } else if (relation === 'Сестре' || relation === 'сестре') {
        switch (numAnswer) {
          case "0": return "Игры";
          case "1": return "Наряжались";
          case "2": return "Болтали по вечерам";
          default: return answer;
        }
      } else if (relation === 'Сыну' || relation === 'сыну') {
        switch (numAnswer) {
          case "0": return "Играть";
          case "1": return "Читать";
          case "2": return "Строить";
          default: return answer;
        }
      } else if (relation === 'Дочери' || relation === 'дочери') {
        switch (numAnswer) {
          case "0": return "Рисовать";
          case "1": return "Наряжаться";
          case "2": return "Читать";
          default: return answer;
        }
      } else if (relation === 'Любимой' || relation === 'любимой') {
        switch (numAnswer) {
          case "0": return "Готовить";
          case "1": return "Разговаривать";
          case "2": return "Смотреть на закат";
          default: return answer;
        }
      } else {
        // По умолчанию для мамы
        switch (numAnswer) {
          case "0": return "Гулять";
          case "1": return "Пить чай";
          case "2": return "Магазины";
          default: return answer;
        }
      }
      break;
      
    case 'q2': // Второй вопрос
      if (relation === 'Маме' || relation === 'маме') {
        switch (numAnswer) {
          case "0": return "Школа";
          case "1": return "Когда болела";
          case "2": return "Поддержка";
          default: return answer;
        }
      } else if (relation === 'Папе' || relation === 'папе') {
        switch (numAnswer) {
          case "0": return "Рыбалка";
          case "1": return "Поездка";
          case "2": return "Советы";
          default: return answer;
        }
      } else if (relation === 'Брату' || relation === 'брату') {
        switch (numAnswer) {
          case "0": return "Розыгрыши";
          case "1": return "Совместные шалости";
          case "2": return "Защита";
          default: return answer;
        }
      } else if (relation === 'Любимому' || relation === 'любимому') {
        switch (numAnswer) {
          case "0": return "Первое свидание";
          case "1": return "Общее хобби";
          case "2": return "Поддержка в трудный момент";
          default: return answer;
        }
      } else if (relation === 'Подруге' || relation === 'подруге') {
        switch (numAnswer) {
          case "0": return "Смешные фотки";
          case "1": return "Курьез в поездке";
          case "2": return "Общие шутки";
          default: return answer;
        }
      } else if (relation === 'Бабушке' || relation === 'бабушке') {
        switch (numAnswer) {
          case "0": return "Каникулы у бабушки";
          case "1": return "Пироги";
          case "2": return "Утренний чай";
          default: return answer;
        }
      } else if (relation === 'Дедушке' || relation === 'дедушке') {
        switch (numAnswer) {
          case "0": return "Истории на ночь";
          case "1": return "Советы";
          case "2": return "Совместная работа";
          default: return answer;
        }
      } else if (relation === 'Сестре' || relation === 'сестре') {
        switch (numAnswer) {
          case "0": return "Тайны в детстве";
          case "1": return "Совместный отпуск";
          case "2": return "Поддержка";
          default: return answer;
        }
      } else if (relation === 'Сыну' || relation === 'сыну') {
        switch (numAnswer) {
          case "0": return "Первое «мама/папа»";
          case "1": return "Сон на руках";
          case "2": return "Первый шаг";
          default: return answer;
        }
      } else if (relation === 'Дочери' || relation === 'дочери') {
        switch (numAnswer) {
          case "0": return "Первый смех";
          case "1": return "Праздник вместе";
          case "2": return "Засыпала на руках";
          default: return answer;
        }
      } else if (relation === 'Любимой' || relation === 'любимой') {
        switch (numAnswer) {
          case "0": return "Признание";
          case "1": return "Первое объятие";
          case "2": return "Утренний кофе";
          default: return answer;
        }
      } else {
        // По умолчанию для мамы
        switch (numAnswer) {
          case "0": return "Школа";
          case "1": return "Когда болела";
          case "2": return "Поддержка";
          default: return answer;
        }
      }
      break;
      
    case 'q3': // Третий вопрос
      if (relation === 'Маме' || relation === 'маме') {
        switch (numAnswer) {
          case "0": return "Коньки";
          case "1": return "Велосипед";
          case "2": return "Рисовать";
          case "3": return "Готовить";
          default: return answer;
        }
      } else if (relation === 'Папе' || relation === 'папе') {
        switch (numAnswer) {
          case "0": return "Честность";
          case "1": return "Работать руками";
          case "2": return "Быть сильным";
          case "3": return "Не сдаваться";
          default: return answer;
        }
      } else if (relation === 'Брату' || relation === 'брату') {
        switch (numAnswer) {
          case "0": return "Не бояться";
          case "1": return "Быть сильным";
          case "2": return "Быть собой";
          case "3": return "Дружить";
          default: return answer;
        }
      } else if (relation === 'Любимому' || relation === 'любимому') {
        switch (numAnswer) {
          case "0": return "Забота";
          case "1": return "Улыбки";
          case "2": return "Уверенность";
          case "3": return "Любовь";
          default: return answer;
        }
      } else if (relation === 'Подруге' || relation === 'подруге') {
        switch (numAnswer) {
          case "0": return "Поддержка";
          case "1": return "Умение слушать";
          case "2": return "Искренность";
          case "3": return "Весёлость";
          default: return answer;
        }
      } else if (relation === 'Бабушке' || relation === 'бабушке') {
        switch (numAnswer) {
          case "0": return "Терпению";
          case "1": return "Уюту";
          case "2": return "Заботе";
          case "3": return "Домашним делам";
          default: return answer;
        }
      } else if (relation === 'Дедушке' || relation === 'дедушке') {
        switch (numAnswer) {
          case "0": return "Дисциплине";
          case "1": return "Смелости";
          case "2": return "Любить семью";
          case "3": return "Мастерить";
          default: return answer;
        }
      } else if (relation === 'Сестре' || relation === 'сестре') {
        switch (numAnswer) {
          case "0": return "Делиться";
          case "1": return "Заботиться";
          case "2": return "Быть смелой";
          case "3": return "Доверять";
          default: return answer;
        }
      } else if (relation === 'Сыну' || relation === 'сыну') {
        switch (numAnswer) {
          case "0": return "Доброте";
          case "1": return "Уверенности";
          case "2": return "Заботе";
          case "3": return "Терпению";
          default: return answer;
        }
      } else if (relation === 'Дочери' || relation === 'дочери') {
        switch (numAnswer) {
          case "0": return "Любить себя";
          case "1": return "Радоваться";
          case "2": return "Быть доброй";
          case "3": return "Мечтать";
          default: return answer;
        }
      } else if (relation === 'Любимой' || relation === 'любимой') {
        switch (numAnswer) {
          case "0": return "Смысл";
          case "1": return "Лёгкость";
          case "2": return "Вдохновение";
          case "3": return "Заботу";
          default: return answer;
        }
      } else {
        // По умолчанию для мамы
        switch (numAnswer) {
          case "0": return "Коньки";
          case "1": return "Велосипед";
          case "2": return "Рисовать";
          case "3": return "Готовить";
          default: return answer;
        }
      }
      break;
    default:
      // Попробуем определить по значению
      if (["0", "1", "2", "3"].includes(numAnswer)) {
        // Это может быть любой из вопросов, показываем как есть
        return answer;
      }
      return answer;
  }
}

// Удалена локальная функция перевода статусов — используется translateStatus из utils

export const OrderDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  // Проверка авторизации
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      navigate("/admin/login");
      return;
    }
  }, [navigate]);
  
  const [order, setOrder] = useState<Order | null>(null);
  const [initialLoading, setInitialLoading] = useState(true); // добавлено
  const [error, setError] = useState("");

  const [uploading, setUploading] = useState(false);

  const [uploadError, setUploadError] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [sendSuccess, setSendSuccess] = useState("");
  const [sendError, setSendError] = useState("");
  const [messages, setMessages] = useState<{ sender: string; message: string; sent_at: string }[]>([]);
  
  // Новые состояния для отправки изображений с текстом и кнопкой
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageFilePreview, setImageFilePreview] = useState<string>("");
  const [demoFiles, setDemoFiles] = useState<File[]>([]);
  const [imageText, setImageText] = useState("");
  const [buttonText, setButtonText] = useState("");
  const [buttonCallback, setButtonCallback] = useState("");
  const [sendingImage, setSendingImage] = useState(false);
  const [imageSuccess, setImageSuccess] = useState("");
  const [imageError, setImageError] = useState("");
  
  // Состояния для выбранного контента
  const [selectedContent, setSelectedContent] = useState<any>(null);
  const [selectedContentLoading, setSelectedContentLoading] = useState(false);
  const [selectedContentError, setSelectedContentError] = useState("");
  
  // Состояния для файлов выбранных страниц
  const [selectedPagesFiles, setSelectedPagesFiles] = useState<any[]>([]);
  const [selectedPagesFilesLoading, setSelectedPagesFilesLoading] = useState(false);
  
  // Состояния для редактирования сводки заказа
  
  
  // Состояния для файлов демо-контента
  const [demoContentFiles, setDemoContentFiles] = useState<any[]>([]);
  const [demoContentFilesLoading, setDemoContentFilesLoading] = useState(false);
  const [demoFilePreviews, setDemoFilePreviews] = useState<string[]>([]);
  const [selectedPreviewIndex, setSelectedPreviewIndex] = useState<number | null>(null);
  const [selectedPagesFilesError, setSelectedPagesFilesError] = useState("");
  
  // Состояния для отправки сообщений
  const [messageFile, setMessageFile] = useState<File | null>(null);
  
  // Состояние для адреса доставки
  const [deliveryAddress, setDeliveryAddress] = useState<any>(null);
  const [loadingAddress, setLoadingAddress] = useState(false);
  const [savingStatus] = useState(false);
  const [statusSuccess] = useState("");
  const [statusError] = useState("");
  
  // Состояние для модального окна просмотра фотографий
  const [selectedPhoto, setSelectedPhoto] = useState<string | null>(null);
  const [isPhotoModalOpen, setIsPhotoModalOpen] = useState(false);
  
  // Отладка состояния модального окна
  useEffect(() => {
    console.log(`🔍 Состояние модального окна изменилось: isPhotoModalOpen=${isPhotoModalOpen}`);
  }, [isPhotoModalOpen]);
  
  // Состояние для модального окна просмотра обложек
  const [selectedCoverImage, setSelectedCoverImage] = useState<string | null>(null);
  const [isCoverModalOpen, setIsCoverModalOpen] = useState(false);

  // Состояния для работы с шаблонами обложек
  const [coverTemplates, setCoverTemplates] = useState<CoverTemplate[]>([]);
  const [loadingCovers, setLoadingCovers] = useState(false);
  const [selectedCover, setSelectedCover] = useState<CoverTemplate | null>(null);
  const [showCoverSelection, setShowCoverSelection] = useState(false);
  const [selectedCovers, setSelectedCovers] = useState<CoverTemplate[]>([]);
  
  // Состояние для глобального таймера
  const [globalCountdown, setGlobalCountdown] = useState(0);

  // Отдельные состояния для каждого раздела загрузки файлов
  const [draftFile, setDraftFile] = useState<File | null>(null);
  const [draftType, setDraftType] = useState("");
  const [draftComment, setDraftComment] = useState("");
  
  const [coverFile, setCoverFile] = useState<File | null>(null);
  const [coverFilePreview, setCoverFilePreview] = useState<string>("");
  const [coverType, setCoverType] = useState("");
  const [coverComment, setCoverComment] = useState("");
  
  const [finalFile, setFinalFile] = useState<File | null>(null);

  // Отдельные состояния для сообщений об успехе каждого раздела
  const [draftSuccess, setDraftSuccess] = useState("");
  const [coverSuccess, setCoverSuccess] = useState("");
  const [finalSuccess, setFinalSuccess] = useState("");
  
  // Состояние для триггерных сообщений
  const [triggerMessages, setTriggerMessages] = useState<TriggerMessage[]>([]);
  const [triggerMessagesLoading, setTriggerMessagesLoading] = useState(false);
  const [triggerMessagesError, setTriggerMessagesError] = useState("");
  
  // Состояние для прогревочных сообщений
  const [warmingMessages, setWarmingMessages] = useState<TriggerMessage[]>([]);
  const [warmingMessagesLoading, setWarmingMessagesLoading] = useState(false);
  const [warmingMessagesError, setWarmingMessagesError] = useState("");
  
  // Состояние для других героев
  const [otherHeroes, setOtherHeroes] = useState<any[]>([]);
  
  // Состояние для фотографий заказа
  const [orderPhotos, setOrderPhotos] = useState<any[]>([]);
  const [photosLoading, setPhotosLoading] = useState(false);
  




  // Состояния для загрузки индивидуальных страниц
  const [pageFiles, setPageFiles] = useState<File[]>([]);
  const [pageDescriptions, setPageDescriptions] = useState<string[]>([]);
  const [pageFilePreviews, setPageFilePreviews] = useState<string[]>([]);
  const [uploadingPages, setUploadingPages] = useState(false);
  const [pagesSuccess, setPagesSuccess] = useState("");
  const [pagesError, setPagesError] = useState("");
  
  // Состояния для быстрой загрузки
  const [bulkFiles, setBulkFiles] = useState<File[]>([]);
  const [bulkFilePreviews, setBulkFilePreviews] = useState<string[]>([]);
  const [uploadingBulk, setUploadingBulk] = useState(false);
  const [bulkSuccess, setBulkSuccess] = useState("");
  const [bulkError, setBulkError] = useState("");

  // Функция для отметки уведомления как прочитанного
  const markNotificationAsRead = useCallback(async () => {
    try {
      const token = localStorage.getItem("token");
      if (!token) return;
      
      const response = await fetch(`/admin/notifications/${id}/mark-read`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        console.log(`📧 Уведомление для заказа ${id} отмечено как прочитанное`);
      } else {
        console.error(`❌ Ошибка отметки уведомления для заказа ${id}:`, response.status);
      }
    } catch (error) {
      console.error(`❌ Ошибка при отметке уведомления для заказа ${id}:`, error);
    }
  }, [id]);

  // Тихая версия для автообновления фотографий (без индикаторов загрузки)
  const fetchOrderPhotosSilent = useCallback(async () => {
    try {
      const token = localStorage.getItem("token");
      console.log(`🔄 Тихий запрос фотографий для заказа ${id}...`);
      
      const response = await fetch(`/admin/orders/${id}/photos?t=${Date.now()}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-cache'
      });
      
      if (response.ok) {
        const photos = await response.json();
        console.log(`✅ Фотографии обновлены:`, photos);
        setOrderPhotos(photos);
      }
    } catch (error) {
      console.error("Ошибка автообновления фотографий:", error);
    }
  }, [id]);

  // Функция для загрузки заказа (вынесена из useEffect)
  const fetchOrder = useCallback(async (isInitial = false) => {
    if (isInitial) setInitialLoading(true);
    setError("");
    setSendSuccess(""); // Очищаем сообщение об успехе при загрузке заказа
    setSendError(""); // Очищаем сообщение об ошибке при загрузке заказа
    // setImageSuccess(""); // НЕ очищаем сообщение об успехе загрузки изображения - оно должно оставаться видимым
    setImageError(""); // Очищаем сообщение об ошибке загрузки изображения
    try {
      const token = localStorage.getItem("token");
      if (!token) {
        navigate("/admin/login");
        return;
      }
      
      const response = await fetch(`/admin/orders/${id}?t=${Date.now()}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        cache: 'no-cache' // Принудительно отключаем кэширование
      });
      if (!response.ok) {
        if (response.status === 401) {
          // Токен недействителен
          localStorage.removeItem("token");
          navigate("/admin/login");
          return;
        } else if (response.status === 403) {
          throw new Error("Доступ к заказу запрещен. У вас нет прав для просмотра этого заказа.");
        } else if (response.status === 404) {
          throw new Error("Заказ не найден");
        } else {
          throw new Error("Ошибка загрузки заказа");
        }
      }
      const data = await response.json();
      console.log("🔍 ОТЛАДКА: Данные заказа загружены:", data);
      console.log("🔍 ОТЛАДКА: data.first_page_text:", data.first_page_text);
      console.log("🔍 ОТЛАДКА: data.last_page_text:", data.last_page_text);
      console.log("🔍 ОТЛАДКА: Обновляем состояние заказа...");
      setOrder(data);
      console.log("✅ Состояние заказа обновлено");
      
      // Устанавливаем значения по умолчанию в зависимости от типа заказа
      const orderData = parseOrderData(data.order_data);
      if (orderData.product === "Песня") {
        if (data.status === "waiting_manager" || data.status === "demo_sent" || data.status === "waiting_for_demo") {
          setImageText("🎧 Вот черновик вашей песни. Давайте настроим все детали");
          setButtonText("🎙 Песня — 2990Р");
          setButtonCallback("song_final_payment");
        } else {
          setImageText("🎵 Ваша песня готова!");
          setButtonText("Слушать готовую песню");
          setButtonCallback("listen_song");
        }
      } else {
        
        // Устанавливаем значения по умолчанию в зависимости от статуса
        if (data.status === "demo_content" || data.status === "demo_sent") {
          setImageText("Пробные страницы вашей книги готовы ☑️\nМы старались, чтобы они были тёплыми и живыми.\n\nНо впереди ещё больше — иллюстратор вдохновился вашей историей и собрал десятки сюжетов для полной версии книги.");
          setButtonText("Узнать цену");
          setButtonCallback("continue_after_demo");
        } else if (data.status === "waiting_draft" || data.status === "draft_sent") {
          setImageText("");
          setButtonText("✅ Всё супер");
          setButtonCallback("book_draft_ok");
        } else {
          // По умолчанию для черновика
          setImageText("");
          setButtonText("✅ Всё супер");
          setButtonCallback("book_draft_ok");
        }
      }
      
      // Отмечаем уведомление как прочитанное только при первоначальной загрузке
      if (isInitial) {
        await markNotificationAsRead();
      }
    } catch (err: any) {
      setError(err.message || "Ошибка загрузки");
    } finally {
      if (isInitial) setInitialLoading(false);
    }
  }, [id, navigate, markNotificationAsRead]);

  // Функция для загрузки выбранного контента
  const fetchSelectedContent = useCallback(async () => {
    if (!id) return;
    try {
      setSelectedContentLoading(true);
      setSelectedContentError("");
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/orders/${id}/selected-content`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const content = await response.json();
        console.log("🔍 ОТЛАДКА selectedContent:", content);
        console.log("🔍 ОТЛАДКА first_page_text:", content.first_page_text);
        console.log("🔍 ОТЛАДКА last_page_text:", content.last_page_text);
        setSelectedContent(content);
      } else {
        setSelectedContentError("Ошибка загрузки выбранного контента");
      }
    } catch (error) {
      console.error("Ошибка загрузки выбранного контента:", error);
      setSelectedContentError("Ошибка загрузки выбранного контента");
    } finally {
      setSelectedContentLoading(false);
    }
  }, [id]);

  // Тихая версия для автообновления (без индикаторов загрузки)
  const fetchSelectedContentSilent = useCallback(async () => {
    if (!id) return;
    try {
      console.log("🔄 Тихий запрос выбранного контента...");
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/orders/${id}/selected-content?t=${Date.now()}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-cache'
      });
      if (response.ok) {
        const content = await response.json();
        console.log("✅ Выбранный контент обновлен:", content);
        setSelectedContent(content);
      }
    } catch (error) {
      console.error("Ошибка автообновления выбранного контента:", error);
    }
  }, [id]);

  // Функция для загрузки файлов выбранных страниц
  const fetchSelectedPagesFiles = useCallback(async () => {
    if (!id) return;
    
    try {
      setSelectedPagesFilesLoading(true);
      setSelectedPagesFilesError("");
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/orders/${id}/selected-pages-files`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const files = await response.json();
        setSelectedPagesFiles(files);
      } else {
        const errorText = await response.text();
        console.error(`Ошибка загрузки файлов выбранных страниц: ${response.status} - ${errorText}`);
        setSelectedPagesFilesError(`Ошибка загрузки файлов выбранных страниц: ${response.status} - ${errorText}`);
      }
    } catch (error) {
      console.error("Ошибка загрузки файлов выбранных страниц:", error);
      setSelectedPagesFilesError("Ошибка загрузки файлов выбранных страниц");
    } finally {
      setSelectedPagesFilesLoading(false);
    }
  }, [id]);

  // Тихая версия для автообновления (без индикаторов загрузки)
  const fetchSelectedPagesFilesSilent = useCallback(async () => {
    if (!id) return;
    
    try {
      console.log("🔄 Тихий запрос файлов выбранных страниц...");
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/orders/${id}/selected-pages-files?t=${Date.now()}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-cache'
      });
      
      if (response.ok) {
        const files = await response.json();
        console.log("✅ Файлы выбранных страниц обновлены:", files);
        setSelectedPagesFiles(files);
      }
    } catch (error) {
      console.error("Ошибка автообновления файлов выбранных страниц:", error);
    }
  }, [id]);

  // Функция для загрузки файлов демо-контента
  const fetchDemoContentFiles = useCallback(async () => {
    if (!id) return;
    
    try {
      setDemoContentFilesLoading(true);
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/orders/${id}/demo-content-files`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const files = await response.json();
        setDemoContentFiles(files);
      } else {
        console.error(`Ошибка загрузки файлов демо-контента: ${response.status}`);
      }
    } catch (error) {
      console.error("Ошибка загрузки файлов демо-контента:", error);
    } finally {
      setDemoContentFilesLoading(false);
    }
  }, [id]);

  // Функция для загрузки триггерных сообщений
  const fetchTriggerMessages = useCallback(async () => {
    try {
      setTriggerMessagesLoading(true);
      setTriggerMessagesError("");
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/orders/${id}/trigger-messages`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const messages = await response.json();
        setTriggerMessages(messages);
      } else {
        setTriggerMessagesError("Ошибка загрузки триггерных сообщений");
      }
    } catch (error) {
      console.error("Ошибка загрузки триггерных сообщений:", error);
      setTriggerMessagesError("Ошибка загрузки триггерных сообщений");
    } finally {
      setTriggerMessagesLoading(false);
    }
  }, [id]);

  // Функция для загрузки прогревочных сообщений
  const fetchWarmingMessages = useCallback(async () => {
    if (!id) return;
    try {
      setWarmingMessagesLoading(true);
      setWarmingMessagesError("");
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/orders/${id}/trigger-messages`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const allMessages = await response.json();
        // Фильтруем только прогревочные сообщения
        const warmingMessages = allMessages.filter((message: any) => 
          message.message_type === "song_warming_example" || 
          message.message_type === "song_warming_motivation"
        );
        setWarmingMessages(warmingMessages);
      } else {
        setWarmingMessagesError("Ошибка загрузки прогревочных сообщений");
      }
    } catch (error) {
      console.error("Ошибка загрузки прогревочных сообщений:", error);
      setWarmingMessagesError("Ошибка загрузки прогревочных сообщений");
    } finally {
      setWarmingMessagesLoading(false);
    }
  }, [id]);

  // Функция для загрузки других героев
  const fetchOtherHeroes = useCallback(async () => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/orders/${id}/other-heroes`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const heroes = await response.json();
        setOtherHeroes(heroes);
      }
    } catch (error) {
      console.error("Ошибка загрузки других героев:", error);
    }
  }, [id]);

  // Тихая версия для автообновления триггерных сообщений (без индикаторов загрузки)
  const fetchTriggerMessagesSilent = useCallback(async () => {
    try {
      const token = localStorage.getItem("token");
      console.log(`🔄 Тихий запрос триггерных сообщений для заказа ${id}...`);
      
      const response = await fetch(`/admin/orders/${id}/trigger-messages?t=${Date.now()}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-cache'
      });
      
      if (response.ok) {
        const messages = await response.json();
        console.log(`✅ Триггерные сообщения обновлены:`, messages);
        setTriggerMessages(messages);
      }
    } catch (error) {
      console.error("Ошибка автообновления триггерных сообщений:", error);
    }
  }, [id]);

  // Тихая версия для автообновления прогревочных сообщений (без индикаторов загрузки)
  const fetchWarmingMessagesSilent = useCallback(async () => {
    if (!id) return;
    try {
      const token = localStorage.getItem("token");
      console.log(`🔄 Тихий запрос прогревочных сообщений для заказа ${id}...`);
      
      const response = await fetch(`/admin/orders/${id}/warming-messages?t=${Date.now()}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-cache'
      });
      
      if (response.ok) {
        const messages = await response.json();
        console.log(`✅ Прогревочные сообщения обновлены:`, messages);
        setWarmingMessages(messages);
      }
    } catch (error) {
      console.error("Ошибка автообновления прогревочных сообщений:", error);
    }
  }, [id]);

  // Тихая версия для автообновления других героев (без индикаторов загрузки)
  const fetchOtherHeroesSilent = useCallback(async () => {
    try {
      const token = localStorage.getItem("token");
      console.log(`🔄 Тихий запрос других героев для заказа ${id}...`);
      
      const response = await fetch(`/admin/orders/${id}/other-heroes?t=${Date.now()}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-cache'
      });
      
      if (response.ok) {
        const heroes = await response.json();
        console.log(`✅ Другие герои обновлены:`, heroes);
        setOtherHeroes(heroes);
      }
    } catch (error) {
      console.error("Ошибка автообновления других героев:", error);
    }
  }, [id]);

  // Функция для загрузки адреса доставки
  const fetchDeliveryAddress = useCallback(async () => {
    try {
      setLoadingAddress(true);
      const token = localStorage.getItem("token");
      
      const response = await fetch(`/admin/orders/${id}/delivery_address`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const address = await response.json();
        setDeliveryAddress(address);
      } else if (response.status === 404) {
        // Адрес не найден - это нормально для заказов без доставки
        setDeliveryAddress(null);
      } else {
        console.error(`❌ Ошибка получения адреса доставки: ${response.status}`);
      }
    } catch (error) {
      console.error("❌ Ошибка загрузки адреса доставки:", error);
    } finally {
      setLoadingAddress(false);
    }
  }, [id]);

  // Функция для загрузки фотографий заказа
  const fetchOrderPhotos = useCallback(async () => {
    try {
      setPhotosLoading(true);
      const token = localStorage.getItem("token");
      console.log(`🔍 Загружаем фотографии для заказа ${id}...`);
      
      const response = await fetch(`/admin/orders/${id}/photos?t=${Date.now()}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-cache' // Принудительно отключаем кэширование
      });
      
      console.log(`📡 Ответ сервера: ${response.status} ${response.statusText}`);
      
      if (response.ok) {
        const photos = await response.json();
        console.log(`✅ Получено ${photos.length} фотографий:`, photos);
        setOrderPhotos(photos);
      } else {
        console.error(`❌ Ошибка получения фотографий: ${response.status}`);
        const errorText = await response.text();
        console.error(`📝 Текст ошибки: ${errorText}`);
      }
    } catch (error) {
      console.error("❌ Ошибка загрузки фотографий заказа:", error);
    } finally {
      setPhotosLoading(false);
    }
  }, [id]);



  // Функция для закрытия модального окна
  const closePhotoModal = () => {
    setIsPhotoModalOpen(false);
    setSelectedPhoto(null);
  };

  // Обработчик клавиши Escape для модальных окон
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (isPhotoModalOpen) {
          closePhotoModal();
        } else if (isCoverModalOpen) {
          closeCoverModal();
        }
      }
    };

    if (isPhotoModalOpen || isCoverModalOpen) {
      document.addEventListener('keydown', handleEscape);
      // Блокируем прокрутку страницы
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isPhotoModalOpen, isCoverModalOpen]);

  useEffect(() => {
    fetchOrder(true); // загружаем только один раз при монтировании компонента
    
    // Автообновление каждые 5 секунд
    const interval = setInterval(async () => {
      console.log("🔄 Автообновление данных заказа...");
      try {
        await fetchOrder(false); // обновляем без изменения состояния загрузки
        console.log("✅ Данные заказа обновлены");
      } catch (error) {
        console.error("❌ Ошибка обновления данных заказа:", error);
      }
      
      try {
        await fetchSelectedContentSilent(); // тихо обновляем выбранный контент
      } catch (error) {
        console.error("❌ Ошибка обновления выбранного контента:", error);
      }
      
      try {
        await fetchSelectedPagesFilesSilent(); // тихо обновляем файлы выбранных страниц
      } catch (error) {
        console.error("❌ Ошибка обновления файлов страниц:", error);
      }
      
      try {
        await fetchOrderPhotosSilent(); // тихо обновляем фотографии
      } catch (error) {
        console.error("❌ Ошибка обновления фотографий:", error);
      }
      
      try {
        await fetchOtherHeroesSilent(); // тихо обновляем других героев
      } catch (error) {
        console.error("❌ Ошибка обновления других героев:", error);
      }
      
      try {
        await fetchTriggerMessagesSilent(); // тихо обновляем триггерные сообщения
      } catch (error) {
        console.error("❌ Ошибка обновления триггерных сообщений:", error);
      }
      
      try {
        await fetchWarmingMessagesSilent(); // тихо обновляем прогревочные сообщения
      } catch (error) {
        console.error("❌ Ошибка обновления прогревочных сообщений:", error);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [id]); // Убираем fetchOrder из зависимостей

  // Загрузка истории сообщений
  useEffect(() => {
    const fetchMessages = async () => {
      try {
        const token = localStorage.getItem("token");
        const response = await fetch(`/admin/orders/${id}/message_history`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.ok) {
          const data = await response.json();
          console.log(`📨 Загружено ${data.length} сообщений для заказа ${id}:`, data);
          setMessages(data);
        } else {
          console.error(`❌ Ошибка загрузки сообщений для заказа ${id}:`, response.status);
        }
      } catch (error) {
        console.error(`❌ Ошибка при загрузке сообщений для заказа ${id}:`, error);
      }
    };
    fetchMessages();
    
    // Автообновление истории сообщений каждые 5 секунд
    const messagesInterval = setInterval(fetchMessages, 5000);
    return () => clearInterval(messagesInterval);
  }, [id, sendSuccess]);

  // Загрузка истории статусов
  useEffect(() => {
    const fetchStatusHistory = async () => {
      try {
        const token = localStorage.getItem("token");
        const response = await fetch(`/admin/orders/${id}/status_history`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.ok) {
          const data = await response.json();
          // setStatusHistory(data); // This state was removed, so this useEffect is no longer needed
        }
      } catch {}
    };
    fetchStatusHistory();
  }, [id, statusSuccess]);

  useEffect(() => {
    fetchTriggerMessages();
    fetchWarmingMessages();
    fetchOtherHeroes();
    fetchOrderPhotos();
    fetchDeliveryAddress();
    fetchSelectedContent();
  }, [id, fetchTriggerMessages, fetchWarmingMessages, fetchOtherHeroes, fetchOrderPhotos, fetchDeliveryAddress, fetchSelectedContent]);

  const data = React.useMemo(() => parseOrderData(order?.order_data || "{}"), [order?.order_data]);
  
  
  // Мемоизируем состояния для предотвращения лишних обновлений
  const selectedPagesFilesStable = React.useMemo(() => selectedPagesFiles, [selectedPagesFiles]);
  const selectedPagesFilesLoadingStable = React.useMemo(() => selectedPagesFilesLoading, [selectedPagesFilesLoading]);
  const selectedPagesFilesErrorStable = React.useMemo(() => selectedPagesFilesError, [selectedPagesFilesError]);

  // Отдельный useEffect для загрузки файлов страниц
  useEffect(() => {
    if (order && id) {
      const orderData = JSON.parse(order.order_data || "{}");
      if (orderData.product === "Книга") {
        fetchSelectedPagesFiles();
        fetchDemoContentFiles();
      }
    }
  }, [id, order?.order_data, fetchSelectedPagesFiles, fetchDemoContentFiles]);
  // Для книг используем main_hero_name или recipient_name, для песен - hero_name
  const heroName = React.useMemo(() => data.main_hero_name || data.recipient_name || data.hero_name || "-", [data.main_hero_name, data.recipient_name, data.hero_name]);
  const heroIntro = React.useMemo(() => data.main_hero_intro || "-", [data.main_hero_intro]);
  const answers = React.useMemo(() => data.answers || [], [data.answers]);
  const style = React.useMemo(() => {
    console.log("🔍 ОТЛАДКА: data.style =", data.style);
    return data.style || "-";
  }, [data.style]);
  const voice = React.useMemo(() => data.song_voice || data.voice || "-", [data.song_voice, data.voice]);
  // Username для связи с пользователем
  const username = React.useMemo(() => {
    return order?.username || data.username || "-";
  }, [order?.username, data.username]);

  // Имя отправителя (кто создает заказ) для отображения в сводке
  const senderName = React.useMemo(() => {
    console.log("🔍 ОТЛАДКА: Данные пользователя:", {
      orderUsername: order?.username,
      orderFirstName: order?.first_name,
      orderLastName: order?.last_name,
      dataUsername: data.username,
      dataFirstName: data.first_name,
      dataLastName: data.last_name
    });
    
    console.log("🔍 ОТЛАДКА: Полный объект order:", order);
    console.log("🔍 ОТЛАДКА: Полный объект data:", data);
    
    // Приоритет: имя и фамилия из order, затем из data
    if (order?.first_name || order?.last_name) {
      console.log("🔍 ОТЛАДКА: Используем order.first_name/last_name");
      const first_name_clean = order.first_name && order.first_name !== "None" ? order.first_name : "";
      const last_name_clean = order.last_name && order.last_name !== "None" ? order.last_name : "";
      return `${first_name_clean} ${last_name_clean}`.trim();
    } else if (data.first_name || data.last_name) {
      console.log("🔍 ОТЛАДКА: Используем data.first_name/last_name");
      const first_name_clean = data.first_name && data.first_name !== "None" ? data.first_name : "";
      const last_name_clean = data.last_name && data.last_name !== "None" ? data.last_name : "";
      return `${first_name_clean} ${last_name_clean}`.trim();
    }
    console.log("🔍 ОТЛАДКА: Ничего не найдено, возвращаем '-'");
    return "-";
  }, [order?.first_name, order?.last_name, data.first_name, data.last_name]);
  const relation = React.useMemo(() => {
    const rawRelation = data.relation || data.song_relation || "-";
    if (rawRelation === "-") return rawRelation;
    
    // Преобразуем отношение для корректного отображения
    const gender = data.gender || data.song_gender || "";
    
    const getMappedRelation = (relation: string, gender: string) => {
      if (relation === "Подруге") {
        return "Подруга - подруге";
      } else if (relation === "Девушке") {
        if (gender === "мальчик" || gender === "парень") {
          return "Парень - девушке";
        } else {
          return "Девушка - парню";
        }
      } else if (relation === "Парню") {
        if (gender === "мальчик" || gender === "парень") {
          return "Парень - девушке";
        } else {
          return "Девушка - парню";
        }
      } else if (relation === "Маме") {
        if (gender === "мальчик" || gender === "парень") {
          return "Сын – маме";
        } else {
          return "Дочка- маме";
        }
      } else if (relation === "Папе") {
        if (gender === "мальчик" || gender === "парень") {
          return "Сын – папе";
        } else {
          return "Дочка- папе";
        }
      } else if (relation === "Бабушке") {
        return "Внучка - бабушке";
      } else if (relation === "Дедушке") {
        return "Внучка - дедушке";
      } else if (relation === "Сестре") {
        if (gender === "мальчик" || gender === "парень") {
          return "Брат – сестре";
        } else {
          return "Сестра - сестре";
        }
      } else if (relation === "Брату") {
        if (gender === "девушка") {
          return "Сестра - брату";
        } else {
          return "Брат - брату";
        }
      } else if (relation === "Сыну") {
        if (gender === "мальчик" || gender === "парень") {
          return "Папа - сыну";
        } else {
          return "Мама - сыну";
        }
      } else if (relation === "Дочке" || relation === "Дочери") {
        if (gender === "мальчик" || gender === "парень") {
          return "Папа - дочке";
        } else {
          return "Мама - дочке";
        }
      } else if (relation === "Мужу") {
        return "Жена - мужу";
      } else if (relation === "Жене") {
        return "Муж - жене";
      } else {
        return relation;
      }
    };
    
    return getMappedRelation(rawRelation, gender);
  }, [data.relation, data.song_relation, data.gender, data.song_gender]);
  const giftReason = React.useMemo(() => data.gift_reason || data.song_gift_reason || "-", [data.gift_reason, data.song_gift_reason]);
  const activeStep = React.useMemo(() => getActiveStep(order?.status || "created"), [order?.status]);
  // Константы для определения бездействия
  const INACTIVITY_THRESHOLD_HOURS = 24; // Час бездействия для показа предупреждения
  
  // Функция для определения бездействия клиента
  const checkClientInactivity = React.useCallback((order: any) => {
    if (!order?.updated_at) return false;
    
    // Статусы, для которых не показываем бездействие
    const completedStatuses = [
      "delivered", 
      "completed", 
      "payment_pending",
      "final_sent"
    ];
    
    if (completedStatuses.includes(order.status)) return false;
    
    // Проверяем, прошло ли более заданного времени с последнего обновления
    const now = new Date();
    const lastUpdate = new Date(order.updated_at);
    const hoursSinceUpdate = (now.getTime() - lastUpdate.getTime()) / (1000 * 60 * 60);
    
    return hoursSinceUpdate > INACTIVITY_THRESHOLD_HOURS;
  }, []);

  const isAbandoned = React.useMemo(() => checkClientInactivity(order), [order]);
  const timeSince = React.useMemo(() => getTimeSince(order?.updated_at || ""), [order?.updated_at]);
  
  // Отладочная информация для проверки бездействия (убрана для стабильности)

  // Функция для загрузки шаблонов обложек
  const fetchCoverTemplates = useCallback(async () => {
    if (order) {
      const orderData = JSON.parse(order.order_data || "{}");
      if (orderData.product === "Книга") {
        setLoadingCovers(true);
        try {
          const token = localStorage.getItem("token");
          const response = await fetch("/admin/cover-templates", {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (response.ok) {
            const templates = await response.json();
            setCoverTemplates(templates);
          }
        } catch (error) {
          console.error("Ошибка загрузки шаблонов обложек:", error);
        } finally {
          setLoadingCovers(false);
        }
      }
    }
  }, [order?.order_data]);

  // Загрузка шаблонов обложек
  useEffect(() => {
    fetchCoverTemplates();
  }, [order?.order_data, fetchCoverTemplates]);
  
  if (initialLoading) return (
    <div className={`p-8 text-white ${smoothTransitionClasses.loading}`}>
      <div className="flex items-center justify-center space-x-2">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white"></div>
        <span>Загрузка...</span>
      </div>
    </div>
  );
  if (error) return (
    <div className="p-8">
      <div className="text-red-500 mb-4">{error}</div>
      <Button onClick={() => navigate("/admin/orders")} className="bg-blue-500 hover:bg-blue-700 text-white">
        Вернуться к списку заказов
      </Button>
    </div>
  );
  if (!order) return <div className="p-8 text-white">Заказ не найден</div>;

  const statusOptions = data.product === "Песня" ? [
    { value: "created", label: "🆕 Новая заявка на песню" },
    { value: "waiting_manager", label: "👨‍💼 Ожидает демо от менеджера" },
    { value: "demo_sent", label: "📤 Демо отправлено" },
    { value: "waiting_payment", label: "💰 Ожидает оплату" },
    { value: "payment_pending", label: "💳 Оплата в процессе" },
    { value: "waiting_draft", label: "📝 Ожидает черновика песни" },
    { value: "draft_sent", label: "📤 Черновик отправлен" },
    { value: "waiting_feedback", label: "💬 Ожидает отзывов" },
    { value: "prefinal_sent", label: "🎵 Предфинальная версия отправлена" },
    { value: "waiting_final", label: "🎯 Ожидает финальной версии" },
    { value: "final_sent", label: "🎉 Финальная песня отправлена" },
    { value: "completed", label: "✅ Завершен" },
  ] : [
    { value: "created", label: "🆕 Новая заявка на книгу" },
    { value: "gender_selected", label: "👤 Выбран пол" },
    { value: "first_name_entered", label: "📝 Введено имя" },
    { value: "relation_selected", label: "👥 Выбран получатель" },
    { value: "character_description_entered", label: "📖 Описание персонажа" },
    { value: "gift_reason_entered", label: "🎁 Указан повод подарка" },
    { value: "main_photos_uploaded", label: "📸 Загружены фото основного героя" },
    { value: "hero_name_entered", label: "👤 Введено имя второго героя" },
    { value: "hero_description_entered", label: "📖 Описание второго персонажа" },
    { value: "hero_photos_uploaded", label: "📸 Загружены фото второго героя" },
    { value: "joint_photo_uploaded", label: "🤝 Загружено совместное фото" },
    { value: "style_selected", label: "🎨 Выбран стиль" },
    { value: "waiting_manager", label: "👨‍💼 Ожидает демо от менеджера" },
    { value: "demo_sent", label: "📤 Демо отправлено" },
    { value: "waiting_payment", label: "💰 Ожидает оплату" },
    { value: "payment_pending", label: "💳 Оплата в процессе" },
    { value: "waiting_story_choice", label: "📖 Ожидает выбора сюжета" },
    { value: "story_selected", label: "✅ Сюжет выбран" },
    { value: "waiting_draft", label: "📝 Ожидает черновика" },
    { value: "draft_sent", label: "📤 Черновик отправлен" },
    { value: "waiting_feedback", label: "💬 Ожидает отзывов" },
    { value: "feedback_processed", label: "✅ Правки внесены" },
    { value: "waiting_cover_choice", label: "🖼️ Ожидает выбора обложки" },
    { value: "cover_selected", label: "✅ Обложка выбрана" },
    { value: "waiting_final", label: "🎯 Ожидает финальной версии" },
    { value: "final_sent", label: "🎉 Финальная книга отправлена" },
    { value: "waiting_delivery", label: "📦 Ожидает доставки" },
    { value: "completed", label: "✅ Завершен" },
  ];



  // Функция для загрузки черновика
  const handleDraftUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    setUploading(true);
    setDraftSuccess("");
    setUploadError("");
    try {
      if (!draftFile) throw new Error("Файл не выбран");
      const token = localStorage.getItem("token");
      const formData = new FormData();
      formData.append("file", draftFile);
      formData.append("type", draftType || "Черновик");
      formData.append("comment", draftComment);
      const response = await fetch(`/admin/orders/${id}/upload_file`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });
      if (!response.ok) throw new Error("Ошибка загрузки файла");
      setDraftSuccess("✅ Черновик успешно загружен!");
      setDraftFile(null);
      setDraftType("");
      setDraftComment("");
    } catch (err: any) {
      setUploadError(err.message || "Ошибка загрузки файла");
    } finally {
      setUploading(false);
    }
  };

  // Функция для обработки изменения файла обложки
  const handleCoverFileChange = (file: File | null) => {
    setCoverFile(file);
    if (file && file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const result = e.target?.result as string;
        setCoverFilePreview(result);
      };
      reader.readAsDataURL(file);
    } else {
      setCoverFilePreview("");
    }
  };

  // Функция для обработки изменения файла черновика
  const handleImageFileChange = (file: File | null) => {
    setImageFile(file);
    if (file && file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const result = e.target?.result as string;
        setImageFilePreview(result);
      };
      reader.readAsDataURL(file);
    } else {
      setImageFilePreview("");
    }
  };

  // Функция для загрузки обложки
  const handleCoverUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    setUploading(true);
    setCoverSuccess("");
    setUploadError("");
    try {
      if (!coverFile) throw new Error("Файл не выбран");
      const token = localStorage.getItem("token");
      const formData = new FormData();
      formData.append("file", coverFile);
      formData.append("type", coverType || "Своя обложка");
      formData.append("comment", coverComment);
      const response = await fetch(`/admin/orders/${id}/upload_file`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });
      if (!response.ok) throw new Error("Ошибка загрузки файла");
      setCoverSuccess("✅ Обложка успешно загружена!");
      setCoverFile(null);
      setCoverFilePreview("");
      setCoverType("");
      setCoverComment("");
    } catch (err: any) {
      setUploadError(err.message || "Ошибка загрузки файла");
    } finally {
      setUploading(false);
    }
  };

  // Функция для загрузки финальной версии
  const handleFinalUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    setUploading(true);
    setFinalSuccess("");
    setUploadError("");
    try {
      if (!finalFile) throw new Error("Файл не выбран");
      const token = localStorage.getItem("token");
      const formData = new FormData();
      formData.append("file", finalFile);
      formData.append("type", "Финальная версия");
      formData.append("comment", "");
      const response = await fetch(`/admin/orders/${id}/upload_file`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });
      if (!response.ok) throw new Error("Ошибка загрузки файла");
      setFinalSuccess("✅ Финальная версия успешно загружена!");
      setFinalFile(null);
    } catch (err: any) {
      setUploadError(err.message || "Ошибка загрузки файла");
    } finally {
      setUploading(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    setSending(true);
    setSendSuccess("");
    setSendError("");
    try {
      if (!message.trim() && !messageFile) {
        throw new Error("Введите текст сообщения или прикрепите файл");
      }
      
      const token = localStorage.getItem("token");
      
      if (messageFile) {
        // Отправка сообщения с файлом
        const formData = new FormData();
        formData.append("file", messageFile);
        if (message.trim()) {
          formData.append("text", message);
        }
        
        const response = await fetch(`/orders/${id}/file`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        });
        if (!response.ok) throw new Error("Ошибка отправки сообщения с файлом");
      } else {
        // Отправка только текстового сообщения
        const response = await fetch(`/orders/${id}/message`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ text: message }),
        });
        if (!response.ok) throw new Error("Ошибка отправки сообщения");
      }
      
      setSendSuccess("✅ Сообщение отправлено успешно!");
      setMessage("");
      setMessageFile(null);
    } catch (err: any) {
      setSendError(err.message || "Ошибка отправки сообщения");
    } finally {
      setSending(false);
    }
  };

  // Функции для Главы 11 - Кастомизация сюжетов


  // Функции для работы с индивидуальными страницами
  const handlePageFileChange = (index: number, file: File | null) => {
    const newFiles = [...pageFiles];
    newFiles[index] = file as any;
    setPageFiles(newFiles);
    
    // Создаем превью для файла
    if (file && file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const result = e.target?.result as string;
        const newPreviews = [...pageFilePreviews];
        newPreviews[index] = result;
        setPageFilePreviews(newPreviews);
      };
      reader.readAsDataURL(file);
    } else {
      const newPreviews = [...pageFilePreviews];
      newPreviews[index] = '';
      setPageFilePreviews(newPreviews);
    }
  };

  const handlePageDescriptionChange = (index: number, description: string) => {
    const newDescriptions = [...pageDescriptions];
    newDescriptions[index] = description;
    setPageDescriptions(newDescriptions);
  };

  const addPageSlot = () => {
    setPageFiles([...pageFiles, null as any]);
    setPageDescriptions([...pageDescriptions, ""]);
    setPageFilePreviews([...pageFilePreviews, ""]);
  };

  const removePageSlot = (index: number) => {
    const newFiles = pageFiles.filter((_, i) => i !== index);
    const newDescriptions = pageDescriptions.filter((_, i) => i !== index);
    const newPreviews = pageFilePreviews.filter((_, i) => i !== index);
    setPageFiles(newFiles);
    setPageDescriptions(newDescriptions);
    setPageFilePreviews(newPreviews);
  };

  const handleUploadPages = async (e: React.FormEvent) => {
    e.preventDefault();
    setUploadingPages(true);
    setPagesSuccess("");
    setPagesError("");
    
    try {
      if (pageFiles.length === 0) {
        throw new Error("Выберите хотя бы один файл");
      }

      const formData = new FormData();
      
      pageFiles.forEach((file, index) => {
        if (file) {
          formData.append(`page_${index + 1}`, file);
          formData.append(`description_${index + 1}`, pageDescriptions[index] || `Страница ${index + 1}`);
        }
      });

      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/orders/${id}/upload-pages`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Ошибка загрузки страниц");
      }

      setPagesSuccess("✅ Страницы загружены и отправлены пользователю!");
      setPageFiles([]);
      setPageDescriptions([]);
      setPageFilePreviews([]);
    } catch (err: any) {
      setPagesError(err.message || "Ошибка загрузки страниц");
    } finally {
      setUploadingPages(false);
    }
  };

  // Функции для быстрой загрузки
  const handleBulkFileChange = (files: FileList | null) => {
    if (files) {
      const fileArray = Array.from(files);
      setBulkFiles(fileArray);
      
      // Создаем превью для каждого файла
      const previews: string[] = [];
      fileArray.forEach((file) => {
        if (file.type.startsWith('image/')) {
          const reader = new FileReader();
          reader.onload = (e) => {
            const result = e.target?.result as string;
            previews.push(result);
            setBulkFilePreviews([...previews]);
          };
          reader.readAsDataURL(file);
        } else {
          previews.push('');
        }
      });
    }
  };

  const handleBulkUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    setUploadingBulk(true);
    setBulkSuccess("");
    setBulkError("");
    
    try {
      if (bulkFiles.length === 0) {
        throw new Error("Выберите файлы для загрузки");
      }

      const formData = new FormData();
      
      console.log(`🔍 ОТЛАДКА: Начинаем обработку ${bulkFiles.length} файлов`);
      
      bulkFiles.forEach((file, index) => {
        formData.append(`page_${index + 1}`, file);
        formData.append(`description_${index + 1}`, `Страница ${index + 1}`);
        console.log(`🔍 ОТЛАДКА: Добавляем файл page_${index + 1}: ${file.name} (размер: ${file.size})`);
      });
      
      console.log(`🔍 ОТЛАДКА: FormData создан, отправляем запрос на /admin/orders/${id}/upload-pages`);

      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/orders/${id}/upload-pages`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`🔍 ОТЛАДКА: Ошибка ответа ${response.status}: ${errorText}`);
        throw new Error(`Ошибка быстрой загрузки страниц: ${response.status} - ${errorText}`);
      }

      setBulkSuccess(`✅ Быстро загружено и отправлено ${bulkFiles.length} страниц!`);
      setBulkFiles([]);
      setBulkFilePreviews([]);
      
      // Плавно обновляем данные заказа без перезагрузки страницы
      setTimeout(async () => {
        try {
          await fetchOrder(false);
        } catch (error) {
          console.log("Ошибка обновления данных заказа:", error);
        }
      }, 1000);
    } catch (err: any) {
      setBulkError(err.message || "Ошибка быстрой загрузки страниц");
    } finally {
      setUploadingBulk(false);
    }
  };



  const handleSendImageWithButton = async (e: React.FormEvent) => {
    e.preventDefault();
    setSendingImage(true);
    setImageSuccess("");
    setImageError("");
    try {
      if (!imageFile) throw new Error("Выберите файл");
      
      // Автоматически устанавливаем текст и кнопки в зависимости от типа продукта
      let autoText = "";
      let autoButtonText = "";
      let autoButtonCallback = "";
      
      if (data.product === "Песня") {
        autoText = "";
        autoButtonText = "✅ Всё супер";
        autoButtonCallback = "song_draft_ok";
      } else {
        // Для книг - это всегда черновик, используем правильные значения
        autoText = "";
        autoButtonText = "✅ Всё супер";
        autoButtonCallback = "book_draft_ok";
      }
      
      const token = localStorage.getItem("token");
      const formData = new FormData();
      formData.append("file", imageFile);
      formData.append("text", autoText);
      formData.append("button_text", autoButtonText);
      formData.append("button_callback", autoButtonCallback);
      
      const response = await fetch(`/admin/orders/${id}/send_image_with_button`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });
      if (!response.ok) throw new Error("Ошибка отправки файла");
      setImageSuccess(`✅ ${data.product === "Песня" ? "Предфинальная версия" : "Файл"} отправлен с кнопками!`);
      setImageFile(null);
      setImageFilePreview("");
    } catch (err: any) {
      setImageError(err.message || "Ошибка отправки изображения");
    } finally {
      setSendingImage(false);
    }
  };

  // Отдельная функция для отправки демо-контента
  const handleSendDemoContent = async (e: React.FormEvent) => {
    e.preventDefault();
    setSendingImage(true);
    setImageSuccess("");
    setImageError("");
    try {
      if (demoFiles.length === 0) throw new Error("Выберите файлы");
      
      // Устанавливаем демо-контент в зависимости от типа продукта
      let demoText, demoButtonText, demoButtonCallback;
      
      if (data.product === "Песня") {
        demoText = "Спасибо за ожидание ✨\nДемо-версия твоей песни готова 💌\nМы собрали её первые ноты с теплом и уже знаем, как превратить их в полную мелодию, которая тронет до мурашек.\n\nЧтобы создать по-настоящему авторскую историю с твоими деталями, моментами и чувствами, нам нужно чуть больше информации 🧩\n\nТвоя история достойна того, чтобы зазвучать полностью и стать запоминающимся подарком для тебя и получателя ❤️‍🔥";
        demoButtonText = "Узнать цену";
        demoButtonCallback = "continue_after_demo";
      } else {
        demoText = "Пробные страницы вашей книги готовы ☑️\nМы старались, чтобы они были тёплыми и живыми.\n\nНо впереди ещё больше — иллюстратор вдохновился вашей историей и собрал десятки сюжетов для полной версии книги.";
        demoButtonText = "Узнать цену";
        demoButtonCallback = "continue_after_demo";
      }
      
      const token = localStorage.getItem("token");
      
      // Отправляем все файлы одним запросом
      const formData = new FormData();
      demoFiles.forEach((file, index) => {
        formData.append("files", file);
      });
      formData.append("text", demoText);
      formData.append("button_text", demoButtonText);
      formData.append("button_callback", demoButtonCallback);
      
      console.log(`🔍 ОТЛАДКА: Отправляем демо-контент: ${demoFiles.length} файлов`);
      console.log(`🔍 ОТЛАДКА: Текст: ${demoText}`);
      console.log(`🔍 ОТЛАДКА: Кнопка: ${demoButtonText}`);
      console.log(`🔍 ОТЛАДКА: Callback: ${demoButtonCallback}`);
      
      const response = await fetch(`/admin/orders/${id}/send_multiple_images_with_button`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });
      
      console.log(`🔍 ОТЛАДКА: Ответ сервера: ${response.status} ${response.statusText}`);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`🔍 ОТЛАДКА: Ошибка ответа: ${errorText}`);
        throw new Error(`Ошибка отправки файлов: ${response.status} - ${errorText}`);
      }
      
      const result = await response.json();
      console.log(`🔍 ОТЛАДКА: Успешный ответ:`, result);
      
      setImageSuccess(`✅ Демо-контент отправлен (${demoFiles.length} файлов) с кнопкой перехода к оплате!`);
      setImageFile(null);
      setImageFilePreview("");
      setDemoFiles([]);
      setDemoFilePreviews([]);
      
      // Плавно обновляем данные заказа без перезагрузки страницы
      setTimeout(async () => {
        try {
          await fetchOrder(false);
        } catch (error) {
          console.log("Ошибка обновления данных заказа:", error);
        }
      }, 1000);
    } catch (err: any) {
      setImageError(err.message || "Ошибка отправки демо-контента");
    } finally {
      setSendingImage(false);
    }
  };

  const handleContinueToPayment = async () => {
    if (!id) return;
    
    setSending(true);
    setSendError("");
    setSendSuccess("");
    
    try {
      const response = await fetch(`/admin/orders/${id}/continue_creation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        setSendSuccess("✅ Книга успешно переведена к оплате (глава 9)!");
        // Плавно обновляем данные заказа без перезагрузки страницы
        setTimeout(async () => {
          try {
            await fetchOrder(false);
          } catch (error) {
            console.log("Ошибка обновления данных заказа:", error);
          }
        }, 1000);
      } else {
        const errorData = await response.json();
        setSendError(errorData.detail || "Ошибка при переходе к оплате");
      }
    } catch (error) {
      setSendError("Ошибка сети при переходе к оплате");
    } finally {
      setSending(false);
      // Очищаем сообщение об успехе через 5 секунд
      setTimeout(() => setSendSuccess(""), 5000);
    }
  };

  // Функция для получения защищенного изображения
  const getProtectedImageUrl = (filePath: string) => {
    const token = localStorage.getItem("token");
    if (!token) return filePath;
    return `/admin/files/${filePath}?token=${token}`;
  };

  // Функция для открытия модального окна с фотографией
  const openPhotoModal = (photoPath: string) => {
    console.log(`🔍 openPhotoModal вызвана с: ${photoPath}`);
    setSelectedPhoto(photoPath);
    setIsPhotoModalOpen(true);
    console.log(`✅ Модальное окно открыто: selectedPhoto=${photoPath}, isPhotoModalOpen=true`);
  };

  // Функция для открытия модального окна с обложкой
  const openCoverModal = (coverFilename: string) => {
    setSelectedCoverImage(coverFilename);
    setIsCoverModalOpen(true);
  };

  // Функция для закрытия модального окна обложки
  const closeCoverModal = () => {
    setIsCoverModalOpen(false);
    setSelectedCoverImage(null);
  };

  // Функция для скачивания архива выбранных страниц
  const downloadSelectedPagesArchive = async () => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/orders/${id}/download-selected-pages`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `selected_pages_order_${id}.zip`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        console.error('Ошибка при скачивании архива');
        alert('Ошибка при скачивании архива');
      }
    } catch (error) {
      console.error('Ошибка при скачивании архива:', error);
      alert('Ошибка при скачивании архива');
    }
  };

  // Функция для скачивания файла
  const downloadFile = async (filepath: string, filename: string, fileType: string = 'photo') => {
    try {
      const response = await fetch(`/${filepath}`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        console.error('Ошибка при скачивании файла');
      }
    } catch (error) {
      console.error('Ошибка при скачивании файла:', error);
    }
  };

  // Функция для скачивания фотографии (для обратной совместимости)
  const downloadPhoto = async (photoId: string, filename: string = "photo") => {
    try {
      const response = await fetch(`/photo/${photoId}`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${filename}_${photoId}.jpg`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        console.error('Ошибка при скачивании фотографии');
      }
    } catch (error) {
      console.error('Ошибка при скачивании фотографии:', error);
    }
  };

  // Функция для запуска глобального таймера
  const startGlobalTimer = () => {
    setGlobalCountdown(15);
    const interval = setInterval(() => {
      setGlobalCountdown(prev => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  // Функция для отправки обложки пользователю
  const sendCoverToUser = async (template: CoverTemplate) => {
    // Проверяем глобальный таймер
    if (globalCountdown > 0) {
      alert(`Подождите ${globalCountdown} секунд перед следующей отправкой!`);
      return;
    }
    
    // Запускаем глобальный таймер
    startGlobalTimer();
    
    try {
      const token = localStorage.getItem("token");
      if (!token) {
        alert("Ошибка: токен не найден!");
        return;
      }
      
      const formData = new FormData();
      formData.append("cover_id", template.id.toString());
      
      const response = await fetch(`/orders/${id}/send_cover`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });
      
      if (response.ok) {
        const result = await response.json();
        setCoverSuccess(`✅ Обложка "${template.name}" отправлена пользователю!`);
        // Обновляем заказ
        fetchOrder(false);
      } else {
        const errorText = await response.text();
        if (response.status === 429) {
          throw new Error("Запрос уже выполняется. Подождите немного.");
        }
        throw new Error(`Ошибка отправки обложки: ${response.status} - ${errorText}`);
      }
    } catch (error: any) {
      setUploadError(`Ошибка: ${error.message}`);
    }
  };


  
  // Функция для выбора обложки
  const handleCoverSelection = (template: CoverTemplate) => {
    setSelectedCover(template);
    setShowCoverSelection(true);
  };
  
  // Функция для добавления/удаления обложки из множественного выбора
  const toggleCoverSelection = (template: CoverTemplate) => {
    setSelectedCovers(prev => {
      const isSelected = prev.some(cover => cover.id === template.id);
      if (isSelected) {
        return prev.filter(cover => cover.id !== template.id);
      } else {
        return [...prev, template];
      }
    });
  };
  
  // Функция для отправки всех выбранных обложек
  const sendSelectedCovers = async () => {
    // Проверяем глобальный таймер
    if (globalCountdown > 0) {
      alert(`Подождите ${globalCountdown} секунд перед следующей отправкой!`);
      return;
    }
    
    if (selectedCovers.length === 0) {
      alert("Выберите хотя бы одну обложку для отправки");
      return;
    }
    
    // Запускаем глобальный таймер
    startGlobalTimer();
    
    try {
      const token = localStorage.getItem("token");
      
      // Сортируем выбранные обложки по порядку в coverTemplates
      const sortedCovers = selectedCovers.sort((a, b) => {
        const indexA = coverTemplates.findIndex(t => t.id === a.id);
        const indexB = coverTemplates.findIndex(t => t.id === b.id);
        return indexA - indexB;
      });
      
      console.log("📚 Порядок отправки обложек:", sortedCovers.map(t => `${t.name} (ID: ${t.id})`));
      
      for (const template of sortedCovers) {
        const formData = new FormData();
        formData.append("cover_id", template.id.toString());
        
        const response = await fetch(`/orders/${id}/send_cover`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        });
        
        if (!response.ok) {
          if (response.status === 429) {
            throw new Error("Запрос уже выполняется. Подождите немного.");
          }
          throw new Error(`Ошибка отправки обложки ${template.name}`);
        }
      }
      
      setCoverSuccess(`✅ Отправлено ${selectedCovers.length} обложек пользователю!`);
      setSelectedCovers([]); // Очищаем выбор
      fetchOrder(false);
    } catch (error: any) {
      setUploadError(`Ошибка: ${error.message}`);
    }
  };
  
  // Функция для отправки всех обложек сразу
  const sendAllCovers = async () => {
    // Проверяем глобальный таймер
    if (globalCountdown > 0) {
      alert(`Подождите ${globalCountdown} секунд перед следующей отправкой!`);
      return;
    }
    
    if (coverTemplates.length === 0) {
      alert("Нет доступных обложек для отправки");
      return;
    }
    
    // Запускаем глобальный таймер
    startGlobalTimer();
    
    try {
      const token = localStorage.getItem("token");
      if (!token) {
        alert("Ошибка: токен не найден!");
        return;
      }
      
      const response = await fetch(`/orders/${id}/send_all_covers`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        if (response.status === 429) {
          throw new Error("Запрос уже выполняется. Подождите немного.");
        }
        throw new Error(`Ошибка отправки обложек: ${response.status} - ${errorText}`);
      }
      
      const result = await response.json();
      setCoverSuccess(`✅ Отправлено все ${coverTemplates.length} обложек пользователю!`);
      fetchOrder(false);
    } catch (error: any) {
      setUploadError(`Ошибка: ${error.message}`);
    }
  };
  


  // Функция для подтверждения выбора обложки
  const confirmCoverSelection = async () => {
    if (!selectedCover) return;
    
    try {
      const token = localStorage.getItem("token");
      const formData = new FormData();
      formData.append("file", new File([""], selectedCover.filename, { type: "image/jpeg" }));
      formData.append("type", "Выбранная обложка");
      formData.append("comment", `Выбрана обложка: ${selectedCover.name} (${selectedCover.category})`);
      
      const response = await fetch(`/admin/orders/${id}/upload_file`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });
      
      if (response.ok) {
        setCoverSuccess("✅ Обложка успешно добавлена в заказ!");
        setShowCoverSelection(false);
        setSelectedCover(null);
        // Обновляем заказ
        fetchOrder(false);
      } else {
        throw new Error("Ошибка добавления обложки");
      }
    } catch (error: any) {
      setUploadError(`Ошибка: ${error.message}`);
    }
  };

  // Функция для удаления триггерных сообщений определенного типа
  const handleDeleteTriggerMessages = async (messageTypes: string[]) => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/orders/${id}/cleanup-trigger-messages`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message_types: messageTypes }),
      });
      
      if (response.ok) {
        const result = await response.json();
        // Обновляем список триггерных сообщений
        fetchTriggerMessages();
        fetchWarmingMessages();
        // Показываем сообщение об успехе
        alert(`Успешно удалено ${result.deleted_count} триггерных сообщений`);
      } else {
        throw new Error("Ошибка удаления триггерных сообщений");
      }
    } catch (error: any) {
      alert(`Ошибка: ${error.message}`);
    }
  };

  // Новый компонент для отображения прогресса создания заказа
const OrderProgress: React.FC<{ 
  status: string; 
  product: string; 
  isAbandoned: boolean; 
  timeSince: string; 
}> = ({ status, product, isAbandoned, timeSince }) => {
    // Определяем этапы в зависимости от типа продукта
    const getSteps = () => {
      if (product === "Песня") {
        return [
          { 
            key: "created", 
            label: "Глава 1", 
            title: "Создание заказа песни",
            description: "Пользователь создает заказ и выбирает получателя", 
            emoji: "🆕",
            managerAction: "Ожидание создания заказа"
          },
          { 
            key: "waiting_manager", 
            label: "Глава 2", 
            title: "Демо-версия песни",
            description: "Менеджер отправляет демо-версию", 
            emoji: "🎵",
            managerAction: "Отправить демо-аудио с кнопкой"
          },
          { 
            key: "waiting_payment", 
            label: "Глава 3", 
            title: "Оплата заказа",
            description: "Пользователь оплачивает заказ", 
            emoji: "💰",
            managerAction: "Ожидание оплаты"
          },
          { 
            key: "collecting_facts", 
            label: "Глава 4", 
            title: "Сбор фактов",
            description: "Пользователь заполняет анкету с фактами", 
            emoji: "📝",
            managerAction: "Ожидание заполнения анкеты"
          },
          { 
            key: "waiting_draft", 
            label: "Глава 5", 
            title: "Предфинальная версия",
            description: "Менеджер отправляет предфинальную версию", 
            emoji: "🎵",
            managerAction: "Отправить предфинальную версию"
          },
          { 
            key: "waiting_feedback", 
            label: "Глава 6", 
            title: "Правки и доработки",
            description: "Пользователь вносит правки", 
            emoji: "✏️",
            managerAction: "Обработать правки пользователя"
          },
          { 
            key: "prefinal_sent", 
            label: "Глава 7", 
            title: "Финальная версия",
            description: "Менеджер отправляет финальную версию", 
            emoji: "🎯",
            managerAction: "Отправить финальную версию"
          }
        ];
      } else {
        return [
          { 
            key: "created", 
            label: "Глава 1", 
            title: "Создание заказа книги",
            description: "Пользователь создает заказ и выбирает персонажей", 
            emoji: "🆕",
            managerAction: "Ожидание создания заказа"
          },
          { 
            key: "waiting_manager", 
            label: "Глава 2", 
            title: "Демо-контент",
            description: "Менеджер отправляет демо-версию книги", 
            emoji: "📖",
            managerAction: "Отправить демо-пример с кнопкой"
          },
          { 
            key: "waiting_payment", 
            label: "Глава 3", 
            title: "Оплата заказа",
            description: "Пользователь оплачивает заказ", 
            emoji: "💰",
            managerAction: "Ожидание оплаты"
          },
          { 
            key: "waiting_story_choice", 
            label: "Глава 4", 
            title: "Выбор сюжетов",
            description: "Пользователь выбирает сюжеты для книги", 
            emoji: "📚",
            managerAction: "Отправить варианты сюжетов"
          },

          { 
            key: "waiting_cover_choice", 
            label: "Глава 5", 
            title: "Выбор обложки",
            description: "Пользователь выбирает обложку", 
            emoji: "🖼️",
            managerAction: "Отправить варианты обложек"
          },
          { 
            key: "waiting_draft", 
            label: "Глава 6", 
            title: "Создание черновика",
            description: "Менеджер создает черновик книги", 
            emoji: "📝",
            managerAction: "Отправить черновик книги"
          },
          { 
            key: "upsell_paid", 
            label: "Глава 7", 
            title: "Доплата за печатную версию",
            description: "Пользователь доплачивает за печатную версию", 
            emoji: "💳",
            managerAction: "Ожидание доплаты"
          },
          { 
            key: "waiting_final", 
            label: "Глава 8", 
            title: "Финальная версия",
            description: "Менеджер отправляет финальную версию", 
            emoji: "🎯",
            managerAction: "Отправить финальную версию"
          },
          { 
            key: "completed", 
            label: "Глава 9", 
            title: "Завершение проекта",
            description: "Проект завершен", 
            emoji: "✅",
            managerAction: "Проект завершен"
          }
        ];
      }
    };

    const steps = getSteps();
    
         // Определяем текущий этап
     // Логика прогресса:
     // КНИГИ (9 этапов): 1-создание, 2-демо, 3-оплата, 4-сюжеты, 5-обложка, 6-черновик, 7-доплата, 8-финал, 9-завершение
     // ПЕСНИ (7 этапов): 1-создание, 2-демо, 3-оплата, 4-черновик, 5-правки, 6-финал, 7-завершение
     const getCurrentStep = () => {
       // Если доплата получена, показываем финальный этап
       if (status === "upsell_paid") {
         return product === "Песня" ? 7 : 9;
       }
       
       // Если заказ завершен, возвращаем последний шаг
       if (status === "completed" || status === "delivered" || status === "final_sent") {
         return product === "Песня" ? 7 : 9;
       }
       

       
       // Создаем разные карты этапов для разных продуктов
       if (product === "Песня") {
         const songStepMap: { [key: string]: number } = {
           // Глава 1: Создание заказа песни
           "created": 1,
           "product_selected": 1,
           "character_created": 1,
           "photos_uploaded": 1,
           "gender_selected": 1,
           "recipient_selected": 1,
           "recipient_name_entered": 1,
           "gift_reason_entered": 1,
           "voice_selection": 1,
           
           // Глава 2: Демо-версия песни
           "waiting_manager": 2,
           "demo_content": 2,
           "demo_sent": 2,
           
           // Глава 3: Оплата заказа
           "waiting_payment": 3,
           "payment_pending": 3,
           "paid": 3,
           "payment_created": 3,
           
           // Глава 4: Сбор фактов
           "collecting_facts": 4,
           "questions_completed": 4,
           
           // Глава 5: Предфинальная версия
           "waiting_draft": 5,
           "draft_sent": 5,
           
           // Глава 6: Правки и доработки
           "waiting_feedback": 6,
           "feedback_processed": 6,
           "editing": 6,
           
           // Глава 7: Финальная версия
           "prefinal_sent": 7,
           "waiting_final": 7,
           "final_sent": 7,
           "ready": 7,
           "delivered": 7,
           "upsell_paid": 7,
         };
         return songStepMap[status] || 1;
       } else {
         const bookStepMap: { [key: string]: number } = {
           // Общие этапы
           "created": 1,
           "product_selected": 1,
           "character_created": 1,
           "photos_uploaded": 1,
           "gender_selected": 1,
           "recipient_selected": 1,
           "recipient_name_entered": 1,
           "gift_reason_entered": 1,
           "voice_selection": 1,
           "collecting_facts": 2,
           "questions_completed": 2,
           "waiting_manager": 2,
           "demo_content": 2,
           "demo_sent": 2,
           "waiting_payment": 3,
           "payment_pending": 3,
           "paid": 3,
           "payment_created": 3,
           
           // Этапы для книг
           "waiting_story_options": 4,
           "waiting_story_choice": 4,
           "story_selected": 4,
           "story_options_sent": 4,
           "pages_selected": 5,
           "covers_sent": 5,
           "waiting_cover_choice": 5,
           "cover_selected": 5,
           "waiting_draft": 6,
           "draft_sent": 6,
           "editing": 6,
           "upsell_payment_created": 7,
           "upsell_payment_pending": 7,
           "upsell_paid": 9,
           "waiting_delivery": 8,
           "waiting_final": 8,
           "ready": 8,
           "print_delivery_pending": 9,
           "delivered": 9,
           "final_sent": 9,
           "completed": 9,
         };
         return bookStepMap[status] || 1;
               }
    };

    const currentStep = getCurrentStep();
    
    // Проверяем, завершен ли заказ
    const isCompleted = status === "completed" || status === "delivered" || status === "final_sent" || status === "upsell_paid";
    
    // Отладочная информация для проверки прогресса
    console.log(`🔍 Прогресс для заказа ${order?.id}:`, {
      status,
      product,
      currentStep,
      totalSteps: steps.length,
      progressPercent: Math.round((isCompleted ? 100 : (currentStep / steps.length) * 100)),
      isCompleted,
      stepDescription: status === "character_created" ? "Создан персонаж (этап 1)" :
                     status === "photos_uploaded" ? "Загружены фото (этап 1)" :
                     status === "questions_completed" ? "Завершены вопросы (этап 2)" :
                     `Статус: ${status}`
    });



    return (
      <div className="mb-4 p-4 bg-gray-800 rounded-lg border border-gray-600 shadow-sm progress-container">
        <h3 className="text-lg font-bold mb-4 text-blue-300 border-b border-gray-600 pb-2">
          📚 Прогресс создания {product === "Песня" ? "песни" : "книги"}
        </h3>
        
        {/* Горизонтальный прогресс-бар */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-300">Общий прогресс</span>
            <span className="text-sm text-gray-400">
              {isCompleted ? "Завершено" : `${currentStep} из ${steps.length} этапов`} ({Math.round((isCompleted ? 100 : (currentStep / steps.length) * 100))}%)
            </span>
          </div>
          <div className="w-full bg-gray-600 rounded-full h-3">
            <div 
              className={`h-3 rounded-full transition-all duration-500 ${
                isCompleted 
                  ? "bg-gradient-to-r from-green-500 to-green-600" 
                  : "bg-gradient-to-r from-blue-500 to-green-500"
              }`}
              style={{ width: `${isCompleted ? 100 : (currentStep / steps.length) * 100}%` }}
            />
          </div>
        </div>
        
        {/* Детальный прогресс по главам */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          {steps.map((step, index) => {
            const stepNumber = index + 1;
            const isStepCompleted = stepNumber < currentStep;
            const isCurrent = stepNumber === currentStep;
            const isPending = stepNumber > currentStep;
            
            return (
              <div key={step.key} className={`
                p-4 rounded-lg border-2 transition-all duration-200 progress-step
                ${isStepCompleted 
                  ? 'border-green-500 bg-green-900' 
                  : isCurrent 
                  ? 'border-blue-500 bg-blue-900 shadow-md' 
                  : 'border-gray-600 bg-gray-700'
                }
              `}>
                <div className="flex items-center justify-between mb-2">
                  <div className={`
                    w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold
                    ${isStepCompleted 
                      ? 'bg-green-500 text-white' 
                      : isCurrent 
                      ? 'bg-blue-500 text-white animate-pulse' 
                      : 'bg-gray-300 text-gray-600'
                    }
                  `}>
                    {isStepCompleted ? "✓" : stepNumber}
                  </div>
                  <span className="text-2xl">{step.emoji}</span>
                </div>
                
                <div className="space-y-1">
                  <div className={`
                    text-sm font-bold
                    ${isStepCompleted ? 'text-green-300' : isCurrent ? 'text-blue-300' : 'text-gray-300'}
                  `}>
                    {step.label}
                  </div>
                  <div className={`
                    text-xs font-semibold
                    ${isStepCompleted ? 'text-green-200' : isCurrent ? 'text-blue-200' : 'text-gray-400'}
                  `}>
                    {step.title}
                  </div>
                  <div className={`
                    text-xs
                    ${isStepCompleted ? 'text-green-100' : isCurrent ? 'text-blue-100' : 'text-gray-500'}
                  `}>
                    {step.description}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        
        {/* Информация о текущем этапе */}
        <div className={`mt-4 p-3 rounded-lg border ${
          isCompleted 
            ? "bg-green-900 border-green-700" 
            : "bg-blue-900 border-blue-700"
        }`}>
          <div className="flex items-center justify-between mb-3">
            <h4 className={`text-lg font-bold ${
              isCompleted ? "text-green-200" : "text-blue-200"
            }`}>
              {isCompleted ? "✅ Заказ завершен" : `🎯 Текущий этап: ${steps[currentStep - 1]?.label} - ${steps[currentStep - 1]?.title}`}
            </h4>
            <span className={`text-sm font-medium ${
              isCompleted ? "text-green-300" : "text-blue-300"
            }`}>
              {Math.round((isCompleted ? 100 : (currentStep / steps.length) * 100))}% завершено
            </span>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <div className={`text-sm font-semibold mb-1 ${
                isCompleted ? "text-green-300" : "text-blue-300"
              }`}>📋 Описание этапа:</div>
              <div className={`text-sm ${
                isCompleted ? "text-green-200" : "text-blue-200"
              }`}>
                {isCompleted ? "Заказ успешно завершен и доставлен клиенту" : steps[currentStep - 1]?.description}
              </div>
            </div>
            <div>
              <div className={`text-sm font-semibold mb-1 ${
                isCompleted ? "text-green-300" : "text-blue-300"
              }`}>👤🏼 Действие менеджера:</div>
              <div className={`text-sm ${
                isCompleted ? "text-green-200" : "text-blue-200"
              }`}>
                {isCompleted ? "Заказ завершен - никаких действий не требуется" : steps[currentStep - 1]?.managerAction}
              </div>
            </div>
          </div>
          
          {isAbandoned && (
            <div className="mt-3 p-2 bg-yellow-900 rounded border border-yellow-700">
              <div className="flex items-center text-yellow-200">
                <span className="text-sm">
                  ⚠️ Клиент неактивен: {timeSince}
                </span>
              </div>
              <div className="text-xs text-yellow-300 mt-1">
                Рекомендуется связаться с клиентом для уточнения деталей заказа
              </div>
            </div>
          )}
        </div>
      </div>
    );
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
    'text/plain', 'text/html', 'text/css', 'text/javascript', 'application/json',
    'application/xml', 'text/xml'
  ];
  
  const allAllowedTypes = [...allowedImageTypes, ...allowedVideoTypes, ...allowedAudioTypes, ...allowedDocumentTypes];

  return (
    <div className="p-4 max-w-2xl mx-auto text-white">
      <div className="flex justify-between items-center mb-4">
        <Button onClick={() => navigate(-1)}>Назад к заказам</Button>
        <div className="flex items-center gap-3">
          <Button 
            onClick={() => {
              fetchOrder(false);
              fetchTriggerMessages();
            }}
            className="bg-blue-600 hover:bg-blue-700 text-sm"
          >
            🔄 Обновить
          </Button>
          <div className="text-sm text-gray-400">Данные загружаются при открытии страницы</div>
        </div>
      </div>
      {/* Полная сводка заказа - вынесена наверх */}
      <div className="bg-gray-800 rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-bold text-center mb-4">📋 Полная информация о заказе ({data.product || "Книга"})</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Левая колонка - Основная информация */}
          <div className="space-y-3">
            <h3 className="text-lg font-semibold text-blue-300 border-b border-gray-600 pb-2">👤 Информация о пользователе</h3>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-gray-400">🆔</span>
                <span className="text-gray-300">Номер заказа:</span>
                <span className="font-semibold text-white">#{order.id.toString().padStart(4, "0")}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-400">👤</span>
                <span className="text-gray-300">Пользователь:</span>
                <span className="font-semibold text-white">{senderName !== "-" ? senderName : "Не указан"}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-400">📱</span>
                <span className="text-gray-300">Telegram ID:</span>
                <span className="font-semibold text-white">{order.telegram_id || order.user_id}</span>
              </div>
              {order.email && (
                <div className="flex items-center gap-2">
                  <span className="text-gray-400">📧</span>
                  <span className="text-gray-300">Email:</span>
                  <span className="font-semibold text-blue-300">{order.email}</span>
                </div>
              )}
              <div className="flex items-center gap-2">
                <span className="text-gray-400">📊</span>
                <span className="text-gray-300">Статус:</span>
                <span className="font-semibold text-white">{translateStatus(order.status)}</span>
              </div>
            </div>
          </div>
          
          {/* Правая колонка - Детали заказа */}
          <div className="space-y-3">
            <h3 className="text-lg font-semibold text-blue-300 border-b border-gray-600 pb-2">📝 Детали заказа</h3>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-gray-400">👤</span>
                <span className="text-gray-300">Пол отправителя:</span>
                <span className="font-semibold text-white">{data.gender || data.song_gender || "Не указан"}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-400">📝</span>
                <span className="text-gray-300">Имя получателя:</span>
                <span className="font-semibold text-white">{data.recipient_name || data.main_hero_name || data.hero_name || data.song_recipient_name || "Не указано"}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-400">🎯</span>
                <span className="text-gray-300">Повод:</span>
                <span className="font-semibold text-white">{giftReason}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-400">💝</span>
                <span className="text-gray-300">Отношение:</span>
                <span className="font-semibold text-white">{relation}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-400">🎨</span>
                <span className="text-gray-300">Стиль:</span>
                <span className="font-semibold text-white">{style}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-400">📖</span>
                <span className="text-gray-300">Формат:</span>
                <span className="font-semibold text-white">{data.format || (data.product === "Песня" ? "💌 Персональная песня" : "Не указан")}</span>
              </div>
              {data.product === "Песня" && (
                <div className="flex items-center gap-2">
                  <span className="text-gray-400">🎤</span>
                  <span className="text-gray-300">Голос:</span>
                  <span className="font-semibold text-white">{voice}</span>
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* Дополнительная информация о заказе */}
        <div className="mt-6 pt-4 border-t border-gray-700">
          <h3 className="text-lg font-semibold text-blue-300 border-b border-gray-600 pb-2 mb-3">📚 Дополнительная информация</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-gray-400">🦸</span>
                <span className="text-gray-300">Имя героя:</span>
                <span className="font-semibold text-white">{heroName}</span>
              </div>
              {heroIntro !== "-" && (
                <div className="flex items-start gap-2">
                  <span className="text-gray-400">📝</span>
                  <span className="text-gray-300">Описание героя:</span>
                  <span className="font-semibold text-white">{heroIntro}</span>
                </div>
              )}
              {data.product === "Книга" && data.first_last_design && (
                <div className="flex items-center gap-2">
                  <span className="text-gray-400">📄</span>
                  <span className="text-gray-300">Оформление страниц:</span>
                  <span className="font-semibold text-white">
                    {data.first_last_design === 'text_only' ? '📝 Только текст' : 
                     data.first_last_design === 'text_photo' ? '📸 Текст + фото' : 
                     data.first_last_design}
                  </span>
                </div>
              )}
            </div>
            <div className="space-y-2">
              {data.product === "Книга" && data.first_page_text && (
                <div className="flex items-start gap-2">
                  <span className="text-gray-400">📄</span>
                  <span className="text-gray-300">Текст первой страницы:</span>
                  <span className="font-semibold text-blue-200">"{data.first_page_text}"</span>
                </div>
              )}
              {data.product === "Книга" && data.last_page_text && (
                <div className="flex items-start gap-2">
                  <span className="text-gray-400">📄</span>
                  <span className="text-gray-300">Текст последней страницы:</span>
                  <span className="font-semibold text-blue-200">"{data.last_page_text}"</span>
                </div>
              )}
            </div>
          </div>
          
          {/* Адрес доставки */}
          {data.product !== "Песня" && (
            <div className="mt-4 pt-4 border-t border-gray-600">
              <h4 className="text-md font-semibold text-green-300 mb-3">📦 Адрес доставки</h4>
              {loadingAddress ? (
                <div className="p-3 bg-gray-800 border border-gray-600 rounded-lg">
                  <div className="text-sm text-gray-400">Загрузка адреса доставки...</div>
                </div>
              ) : deliveryAddress ? (
                <div className="p-3 bg-green-900 border border-green-700 rounded-lg">
                  <div className="text-sm text-green-100 space-y-1">
                    <div><strong>Адрес:</strong> {deliveryAddress.address}</div>
                    <div><strong>Получатель:</strong> {deliveryAddress.recipient_name}</div>
                    <div><strong>Телефон:</strong> {deliveryAddress.phone}</div>
                    <div className="text-xs text-green-300 mt-2">
                      Дата добавления: {new Date(deliveryAddress.created_at).toLocaleString('ru-RU')}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-3 bg-gray-800 border border-gray-600 rounded-lg">
                  <div className="text-sm text-gray-400">Адрес доставки не указан</div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="bg-gray-900 rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">📊 Прогресс и управление заказом</h2>
        
        {/* Новый компонент прогресса создания заказа */}
        <OrderProgress 
          status={order.status} 
          product={data.product || "Книга"} 
          isAbandoned={isAbandoned}
          timeSince={timeSince}
        />
        
        {/* Подсказки для менеджера */}
        {order.status === "created" && data.product === "Книга" && (
          <div className="mb-4 p-3 bg-yellow-900 border border-yellow-700 rounded-lg">
            <div className="font-bold text-yellow-300 mb-1">💡 Подсказка для менеджера</div>
            <div className="text-sm text-yellow-200">
              Пользователь только что создал заказ. Отправьте демо-контент с примерами страниц, чтобы показать качество работы.
              <br />
              <strong>Рекомендуемые файлы:</strong> PDF с примерами страниц, изображения обложек
            </div>
          </div>
        )}
        
        {order.status === "waiting_manager" && data.product === "Песня" && (
          <div className="mb-4 p-3 bg-yellow-900 border border-yellow-700 rounded-lg">
            <div className="font-bold text-yellow-300 mb-1">💡 Подсказка для менеджера</div>
            <div className="text-sm text-yellow-200">
              Пользователь ожидает демо-версию песни. Отправьте аудио-файл с примером стиля и голоса.
              <br />
              <strong>Рекомендуемые файлы:</strong> MP3 с демо-версией, примеры стилей
            </div>
          </div>
        )}
        
        {order.status === "waiting_payment" && (
          <div className="mb-4 p-3 bg-orange-900 border border-orange-700 rounded-lg">
            <div className="font-bold text-orange-300 mb-1">💰 Ожидание оплаты</div>
            <div className="text-sm text-orange-200">
              Пользователь должен выбрать формат и оплатить заказ. Дождитесь подтверждения оплаты.
            </div>
          </div>
        )}

        {data.product !== "Песня" && (
        <div className="mb-4">
          <h4 className="font-semibold mb-2 text-blue-200">📸 Фотографии заказа</h4>
          
          {/* Главный герой */}
          <div className="mb-3">
            <div className="text-sm text-gray-300 mb-2">
              Главный герой: {heroName !== "-" && <span className="text-white font-medium">{heroName}</span>}
            </div>
            {heroIntro !== "-" && (
              <div className="text-xs text-gray-400 mb-2">{heroIntro}</div>
            )}
            <div className="flex gap-2 flex-wrap">
              {photosLoading ? (
                <span className="text-gray-400">Загрузка фотографий...</span>
              ) : orderPhotos.filter(photo => photo.type.startsWith('main_hero')).length > 0 ? (
                orderPhotos
                  .filter(photo => photo.type.startsWith('main_hero'))
                  .map((photo, i) => (
                    <div key={i} className="relative group">
                      <img 
                        src={getProtectedImageUrl(`uploads/${photo.filename}`)} 
                        alt="hero" 
                        className="w-20 h-20 object-cover rounded cursor-pointer hover:opacity-80 transition-opacity"
                        style={{ cursor: 'pointer', position: 'relative', zIndex: 1 }}
                        onError={(e) => {
                          console.error(`❌ Ошибка загрузки изображения: ${photo.filename}`);
                          console.error(`   URL: ${getProtectedImageUrl(`uploads/${photo.filename}`)}`);
                          console.error(`   Элемент:`, e.currentTarget);
                          e.currentTarget.style.display = 'none';
                        }}
                        onLoad={() => console.log(`✅ Изображение загружено: ${photo.filename}`)}
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          openPhotoModal(`uploads/${photo.filename}`);
                        }}
                      />
                      <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 rounded flex items-center justify-center transition-all pointer-events-none">
                        <span className="text-white text-xs opacity-0 group-hover:opacity-100">👁️</span>
                      </div>
                    </div>
                  ))
              ) : (
                <span className="text-gray-400">Нет фото</span>
              )}
            </div>
          </div>

          {/* Совместное фото */}
          <div className="mb-3">
            <div className="text-sm text-gray-300 mb-2">Совместное фото:</div>
            {orderPhotos.filter(photo => photo.type === 'joint_photo').length > 0 ? (
              <div className="flex gap-2 flex-wrap">
                {orderPhotos
                  .filter(photo => photo.type === 'joint_photo')
                  .map((photo, i) => (
                    <div key={i} className="relative group">
                      <img 
                        src={getProtectedImageUrl(`uploads/${photo.filename}`)} 
                        alt="joint_photo" 
                        className="w-20 h-20 object-cover rounded cursor-pointer hover:opacity-80 transition-opacity"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          openPhotoModal(`uploads/${photo.filename}`);
                        }}
                        onError={(e) => {
                          console.error(`Ошибка загрузки изображения: ${photo.filename}`);
                          e.currentTarget.style.display = 'none';
                        }}
                      />
                      <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 rounded flex items-center justify-center transition-all pointer-events-none">
                        <span className="text-white text-xs opacity-0 group-hover:opacity-100">👁️</span>
                      </div>
                    </div>
                  ))}
              </div>
            ) : (
              <div className="text-sm text-gray-400 italic">Не загружено (необязательно)</div>
            )}
          </div>

          {/* Другие герои */}
          {otherHeroes.length > 0 && (
            <div className="mb-3">
              <div className="text-sm text-gray-300 mb-2">Другие герои:</div>
              {otherHeroes.map((hero, heroIndex) => (
                <div key={hero.id} className="mb-3 p-3 bg-gray-800 rounded border border-gray-700">
                  <div className="text-sm font-medium text-white mb-2">
                    {hero.hero_name || `Герой ${heroIndex + 1}`}
                  </div>
                  {hero.hero_intro && (
                    <div className="text-xs text-gray-400 mb-2">{hero.hero_intro}</div>
                  )}
                  <div className="flex gap-2 flex-wrap">
                    {(() => {
                      const heroName = hero.hero_name || `hero_${heroIndex + 1}`;
                      const filteredPhotos = orderPhotos.filter(photo => {
                        const photoType = photo.type || '';
                        const matches = photoType.toLowerCase().includes(heroName.toLowerCase()) || 
                                       photoType.toLowerCase().includes(`hero_${heroIndex + 1}`);
                        
                        // Отладочная информация
                        console.log(`🔍 Фильтрация фото для героя "${heroName}":`, {
                          photoType,
                          heroName,
                          matches
                        });
                        
                        return matches;
                      });
                      
                      console.log(`📸 Найдено ${filteredPhotos.length} фото для героя "${heroName}"`);
                      
                      return filteredPhotos.map((photo, photoIndex) => (
                        <div key={photoIndex} className="relative group">
                          <img 
                            src={getProtectedImageUrl(`uploads/${photo.filename}`)} 
                            alt={`${hero.hero_name} - ${photo.type}`} 
                            className="w-16 h-16 object-cover rounded cursor-pointer hover:opacity-80 transition-opacity"
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              openPhotoModal(`uploads/${photo.filename}`);
                            }}
                            onError={(e) => {
                              console.error(`Ошибка загрузки изображения: ${photo.filename}`);
                              e.currentTarget.style.display = 'none';
                            }}
                          />
                          <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 rounded flex items-center justify-center transition-all pointer-events-none">
                            <span className="text-white text-xs opacity-0 group-hover:opacity-100">👁️</span>
                          </div>
                        </div>
                      ));
                    })()}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Фотографии первой и последней страницы */}
          <div className="mb-3">
            <div className="text-sm text-gray-300 mb-2">Первая и последняя страница:</div>
            {orderPhotos.filter(photo => photo.type === 'first_page_photo' || photo.type === 'last_page_photo').length > 0 ? (
              <div className="flex gap-2 flex-wrap">
                {orderPhotos
                  .filter(photo => photo.type === 'first_page_photo' || photo.type === 'last_page_photo')
                  .map((photo, i) => (
                    <div key={i} className="relative group">
                      <img 
                        src={getProtectedImageUrl(`uploads/${photo.filename}`)} 
                        alt={photo.type === 'first_page_photo' ? 'first_page' : 'last_page'} 
                        className="w-20 h-20 object-cover rounded cursor-pointer hover:opacity-80 transition-opacity"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          openPhotoModal(`uploads/${photo.filename}`);
                        }}
                        onError={(e) => {
                          console.error(`Ошибка загрузки изображения: ${photo.filename}`);
                          e.currentTarget.style.display = 'none';
                        }}
                      />
                      <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 rounded flex items-center justify-center transition-all pointer-events-none">
                        <span className="text-white text-xs opacity-0 group-hover:opacity-100">👁️</span>
                      </div>
                      <div className="absolute bottom-0 left-0 right-0 bg-black bg-opacity-50 text-white text-xs p-1 text-center">
                        {photo.type === 'first_page_photo' ? 'Первая' : 'Последняя'}
                      </div>
                    </div>
                  ))}
              </div>
            ) : (
              <div className="text-sm text-gray-400 italic">Не загружено</div>
            )}
            
            {/* Оформление первой и последней страницы */}
            {(selectedContent?.first_last_design || selectedContent?.first_page_text || selectedContent?.last_page_text) && (
              <div className="mt-3 p-3 bg-blue-900 rounded border border-blue-700">
                <div className="text-sm font-medium text-white mb-2">
                  📝 Оформление первой и последней страницы
                </div>
                {selectedContent?.first_last_design && (
                  <div className="text-sm text-gray-300 mb-2">
                    {selectedContent.first_last_design === 'text_only' ? '📝 Только текст' : 
                     selectedContent.first_last_design === 'text_photo' ? '📸 Текст + фото' : 
                     selectedContent.first_last_design}
                  </div>
                )}
                {selectedContent?.first_page_text && (
                  <div className="text-sm text-blue-200 mb-1">
                    <strong>Текст первой страницы:</strong> "{selectedContent.first_page_text}"
                  </div>
                )}
                {selectedContent?.last_page_text && (
                  <div className="text-sm text-blue-200 mb-1">
                    <strong>Текст последней страницы:</strong> "{selectedContent.last_page_text}"
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Фотографии обложки */}
          <div className="mb-3">
            <div className="text-sm text-gray-300 mb-2">Фотографии обложки:</div>
            {orderPhotos.filter(photo => photo.type === 'cover_photo').length > 0 ? (
              <div className="flex gap-2 flex-wrap">
                {orderPhotos
                  .filter(photo => photo.type === 'cover_photo')
                  .map((photo, i) => (
                    <div key={i} className="relative group">
                      <img 
                        src={getProtectedImageUrl(`uploads/${photo.filename}`)} 
                        alt="cover_photo" 
                        className="w-20 h-20 object-cover rounded cursor-pointer hover:opacity-80 transition-opacity"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          openPhotoModal(`uploads/${photo.filename}`);
                        }}
                        onError={(e) => {
                          console.error(`Ошибка загрузки изображения: ${photo.filename}`);
                          e.currentTarget.style.display = 'none';
                        }}
                      />
                      <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 rounded flex items-center justify-center transition-all pointer-events-none">
                        <span className="text-white text-xs opacity-0 group-hover:opacity-100">👁️</span>
                      </div>
                    </div>
                  ))}
              </div>
            ) : (
              <div className="text-sm text-gray-400 italic">Не загружено</div>
            )}
            

          </div>

          {/* Пользовательские фотографии */}
          
        </div>
        )}

        {/* Выбранный контент */}
        {data.product !== "Песня" && (
          <div className="mb-4">
            <h4 className="font-semibold mb-2 text-green-200">📖 Выбранный контент</h4>
            
            {selectedContentLoading ? (
              <div className="text-center text-gray-400">Загрузка выбранного контента...</div>
            ) : selectedContentError ? (
              <div className="text-red-400 text-sm">{selectedContentError}</div>
            ) : selectedContent ? (
              <div className="space-y-4">
                {/* Выбранные страницы */}
                <div className="p-3 bg-gray-800 rounded border border-gray-700">
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-sm font-medium text-white">
                      📄 Выбранные страницы
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="text-sm text-gray-300">
                        {selectedContent.total_selected || 0} из 24
                      </div>
                      {selectedPagesFiles.length > 0 && (
                        <button
                          onClick={downloadSelectedPagesArchive}
                          className="text-xs bg-green-600 hover:bg-green-700 text-white px-2 py-1 rounded transition-colors"
                          title="Скачать все выбранные страницы архивом"
                        >
                          📦 Скачать все
                        </button>
                      )}
                    </div>
                  </div>
                  {selectedContent.selected_pages && selectedContent.selected_pages.length > 0 ? (
                    <div>
                      {/* Сетка с номерами страниц */}
                      <div className="grid grid-cols-6 gap-2 mb-3">
                        {selectedContent.selected_pages.map((pageNum: number, index: number) => (
                          <div key={index} className="bg-green-900 text-green-200 text-xs p-2 rounded text-center">
                            Страница {pageNum}
                          </div>
                        ))}
                      </div>
                      
                      {/* Файлы страниц для просмотра и скачивания */}
                      {selectedPagesFilesLoadingStable ? (
                        <div className="text-center text-gray-400 text-sm">Загрузка файлов страниц...</div>
                      ) : selectedPagesFilesErrorStable ? (
                        <div className="text-red-400 text-sm">{selectedPagesFilesErrorStable}</div>
                      ) : selectedPagesFilesStable && selectedPagesFilesStable.length > 0 ? (
                        <div>
                          <div className="text-sm text-gray-300 mb-2">Файлы для просмотра и скачивания:</div>
                                                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                                {selectedPagesFilesStable.map((pageFile, index) => (
                              <div key={index} className="bg-gray-700 rounded border border-gray-600 p-2">
                                <div className="relative group">
                                  <img 
                                    src={getProtectedImageUrl(pageFile.file_path)} 
                                    alt={`Страница ${pageFile.page_num}`} 
                                    className="w-full h-24 object-cover rounded cursor-pointer hover:opacity-80 transition-opacity"
                                    onClick={(e) => {
                                      e.preventDefault();
                                      e.stopPropagation();
                                      openPhotoModal(pageFile.file_path);
                                    }}
                                    onError={(e) => {
                                      console.error(`Ошибка загрузки изображения: ${pageFile.filename}`);
                                      e.currentTarget.style.display = 'none';
                                    }}
                                  />
                                  <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 rounded flex items-center justify-center transition-all pointer-events-none">
                                    <span className="text-white text-xs opacity-0 group-hover:opacity-100">👁️</span>
                                  </div>
                                </div>
                                <div className="mt-2 text-center">
                                  <div className="text-xs text-gray-300 mb-1">
                                    Страница {pageFile.page_num}
                                  </div>
                                  <button
                                    onClick={() => downloadFile(pageFile.file_path, pageFile.filename)}
                                    className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded transition-colors"
                                    title="Скачать файл"
                                  >
                                    📥 Скачать
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <div className="text-sm text-gray-400 italic">Файлы страниц не найдены</div>
                      )}
                    </div>
                  ) : (
                    <div className="text-sm text-gray-400 italic">Страницы не выбраны</div>
                  )}
                </div>

                {/* Вкладыши */}
                {selectedContent.inserts && selectedContent.inserts.length > 0 && (
                  <div className="p-3 bg-gray-800 rounded border border-gray-700">
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-sm font-medium text-white">
                        📎 Вкладыши
                      </div>
                      <div className="text-sm text-gray-300">
                        {selectedContent.total_inserts || 0} шт.
                      </div>
                    </div>
                    <div className="space-y-2">
                      {selectedContent.inserts.map((insert: string, index: number) => {
                        const insertText = selectedContent.insert_texts?.[insert];
                        return (
                          <div key={index} className="border-b border-gray-700 pb-2 last:border-b-0">
                            <div className="text-sm text-purple-200 mb-1">
                              📄 {insert}
                            </div>
                            {insertText && (
                              <div className="text-xs text-gray-300 bg-gray-700 p-2 rounded">
                                {insertText}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Свои фотографии */}
                {selectedContent.custom_photos && selectedContent.custom_photos.length > 0 && (
                  <div className="p-3 bg-gray-800 rounded border border-gray-700">
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-sm font-medium text-white">
                        📷 Свои фотографии
                      </div>
                      <div className="text-sm text-gray-300">
                        {selectedContent.total_custom_photos || 0} шт.
                      </div>
                    </div>
                    <div className="flex gap-2 flex-wrap">
                      {selectedContent.custom_photos.map((photo: string, index: number) => (
                        <div key={index} className="relative group">
                          <img 
                            src={getProtectedImageUrl(`uploads/${photo}`)} 
                            alt="custom_photo" 
                            className="w-16 h-16 object-cover rounded cursor-pointer hover:opacity-80 transition-opacity"
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              openPhotoModal(photo);
                            }}
                            onError={(e) => {
                              console.error(`Ошибка загрузки изображения: ${photo}`);
                              e.currentTarget.style.display = 'none';
                            }}
                          />
                          <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 rounded flex items-center justify-center transition-all pointer-events-none">
                            <span className="text-white text-xs opacity-0 group-hover:opacity-100">👁️</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Оформление обложки */}
                {(selectedContent?.cover_design || selectedContent?.selected_cover || selectedContent?.cover_photos) && (
                  <div className="p-3 bg-gray-800 rounded border border-gray-700">
                    <div className="text-sm font-medium text-white mb-2">
                      🎨 Оформление обложки
                    </div>
                    {selectedContent?.cover_design && (
                      <div className="text-sm text-gray-300 mb-2">
                        {selectedContent.cover_design}
                      </div>
                    )}
                    {selectedContent?.selected_cover && (
                      <div className="text-sm text-blue-200 mb-2">
                        <strong>Выбранная обложка:</strong> {selectedContent.selected_cover.name || selectedContent.selected_cover.filename}
                      </div>
                    )}
                    {selectedContent?.cover_photos && selectedContent.cover_photos.length > 0 && (
                      <div className="flex gap-2 flex-wrap">
                        {selectedContent.cover_photos.map((photo: string, index: number) => (
                          <div key={index} className="relative group">
                            <img 
                              src={getProtectedImageUrl(`uploads/${photo}`)} 
                              alt="cover_photo" 
                              className="w-16 h-16 object-cover rounded cursor-pointer hover:opacity-80 transition-opacity"
                              onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                openPhotoModal(photo);
                              }}
                              onError={(e) => {
                                console.error(`Ошибка загрузки изображения: ${photo}`);
                                e.currentTarget.style.display = 'none';
                              }}
                            />
                            <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 rounded flex items-center justify-center transition-all pointer-events-none">
                              <span className="text-white text-xs opacity-0 group-hover:opacity-100">👁️</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}


              </div>
            ) : (
              <div className="text-center text-gray-400 p-4 bg-gray-700 rounded border border-gray-600">
                Нет данных о выбранном контенте
              </div>
            )}
          </div>
        )}
        <div className="mb-4">Ответы на анкеты:
          <ul className="list-disc ml-6 mt-2">
            {Array.isArray(answers) && answers.length > 0 ? answers.map((a: string, i: number) => {
              // Проверяем, что ответ не пустой и является строкой
              if (!a || typeof a !== 'string') {
                console.warn(`⚠️ Некорректный ответ ${i + 1}:`, a);
                return (
                  <li key={i} className="text-red-400">
                    Некорректный ответ: {JSON.stringify(a)}
                  </li>
                );
              }
              
              const translatedAnswer = i === 0 ? translateAnswer(a, 'q1', relation) : 
                                     i === 1 ? translateAnswer(a, 'q2', relation) : 
                                     i === 2 ? translateAnswer(a, 'q3', relation) : 
                                     translateAnswer(a, undefined, relation);
              
              // Отладочная информация
              console.log(`🔍 Перевод ответа ${i + 1}:`, {
                original: a,
                translated: translatedAnswer,
                questionType: i === 0 ? 'q1' : i === 1 ? 'q2' : i === 2 ? 'q3' : 'unknown',
                relation: relation
              });
              
              return (
                <li key={i}>
                  {translatedAnswer}
                </li>
              );
            }) : <li className="text-gray-400">Нет ответов</li>}
          </ul>
        </div>

        {/* Вкладыши */}
        {data.inserts && Array.isArray(data.inserts) && data.inserts.length > 0 && (
          <div className="mb-4">
            <h4 className="font-semibold mb-2 text-purple-200">📄 Вкладыши</h4>
            <div className="p-3 bg-gray-800 rounded border border-gray-700">
              <div className="space-y-3">
                {data.inserts.map((insert: string, i: number) => {
                  // Получаем текст вкладыша из данных
                  const insertTexts = data.insert_texts || {};
                  
                  // Ищем соответствующий текст для этого вкладыша
                  // Создаем маппинг названий вкладышей к ключам
                  const insertMapping: { [key: string]: string } = {
                    "Поздравительная открытка": "insert_card",
                    "Персональное письмо": "insert_letter",
                    "Аудио-пожелание": "insert_audio",
                    "Рисунок ребенка": "insert_drawing",
                    "Стихотворение": "insert_poem",
                    "Подарочный сертификат": "insert_certificate"
                  };
                  
                  const insertKey = insertMapping[insert];
                  const insertText = insertKey ? insertTexts[insertKey] : null;
                  
                  return (
                    <div key={i} className="border-b border-gray-700 pb-3 last:border-b-0">
                      <div className="font-medium text-white mb-2">
                        📄 {insert}
                      </div>
                      {insertText ? (
                        <div className="ml-4">
                          <div className="text-sm text-gray-300 mb-1">
                            <strong>Текст:</strong>
                          </div>
                          <div className="text-sm text-gray-200 bg-gray-700 p-2 rounded border border-gray-600">
                            {insertText === "На усмотрение сценаристов" ? (
                              <span className="text-blue-300 italic">
                                🎭 {insertText}
                              </span>
                            ) : (
                              <span className="text-green-300">
                                ✍️ {insertText}
                              </span>
                            )}
                          </div>
                        </div>
                      ) : (
                        <div className="ml-4">
                          <div className="text-sm text-gray-400 italic">
                            ⚠️ Текст не указан
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Согласие на обработку персональных данных */}
        {data.personal_data_consent !== undefined && (
          <div className="mb-4">
            <h4 className="font-semibold mb-2 text-orange-200">📋 Согласие на обработку персональных данных</h4>
            <div className="p-3 bg-gray-800 rounded border border-gray-700">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className={`text-lg ${data.personal_data_consent ? 'text-green-400' : 'text-red-400'}`}>
                    {data.personal_data_consent ? '✅' : '❌'}
                  </span>
                  <span className="text-white">
                    {data.personal_data_consent ? 'Согласен' : 'Не согласен'}
                  </span>
                </div>
                {data.personal_data_consent_date && (
                  <span className="text-sm text-gray-400">
                    {new Date(data.personal_data_consent_date).toLocaleString('ru-RU')}
                  </span>
                )}
              </div>
              {data.personal_data_consent && (
                <div className="mt-2 text-sm text-gray-300">
                  <a 
                    href="https://docs.google.com/document/d/12-3hLtgU6tSrRI4tR5tOBxIvJSuNB9eQMZF8SKzjUcc/edit?tab=t.0" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-blue-400 hover:text-blue-300 underline"
                  >
                    📄 Просмотреть документ
                  </a>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Секция триггерных сообщений */}
        <div className="mb-4">
          <h4 className="font-semibold mb-2 text-blue-200">🔔 Триггерные сообщения</h4>
          {triggerMessagesLoading ? (
            <div className="text-center text-gray-400">Загрузка триггерных сообщений...</div>
          ) : triggerMessagesError ? (
            <div className="text-red-400 text-sm">{triggerMessagesError}</div>
          ) : triggerMessages.length > 0 ? (
            <div className="space-y-3">
              {triggerMessages.map((message, index) => (
                <div key={index} className="p-3 bg-gray-700 rounded border border-gray-600">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex-1">
                      <div className="font-medium text-white mb-1">
                        {message.message_type === "payment_reminder" && "💰 Напоминание об оплате"}
                        {message.message_type === "abandoned_cart" && "🛒 Напоминание о брошенной корзине"}
                        {message.message_type === "delivery_reminder" && "📦 Напоминание о доставке"}
                        {message.message_type === "feedback_reminder" && "💬 Напоминание об отзыве"}
                        {message.message_type === "completion_reminder" && "✅ Напоминание о завершении"}
                        {message.message_type === "custom" && "📝 Пользовательское сообщение"}
                        {!["payment_reminder", "abandoned_cart", "delivery_reminder", "feedback_reminder", "completion_reminder", "custom"].includes(message.message_type) && message.message_type}
                      </div>
                      <div className="text-sm text-gray-300">
                        Количество: {message.count} | ID: {message.message_ids}
                      </div>
                      <div className="text-sm text-gray-400">
                        Следующая отправка: {message.next_scheduled}
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      <Button
                        onClick={() => handleDeleteTriggerMessages([message.message_type])}
                        className="text-xs bg-red-600 hover:bg-red-700 text-white"
                        title="Удалить все сообщения этого типа"
                      >
                        🗑️ Удалить
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
              <div className="mt-3 p-2 bg-blue-900 border border-blue-700 rounded text-sm text-blue-200">
                💡 <strong>Подсказка:</strong> Триггерные сообщения автоматически удаляются при изменении статуса заказа. 
                Например, сообщения об оплате удаляются после получения оплаты.
              </div>
            </div>
          ) : (
            <div className="text-center text-gray-400 p-4 bg-gray-700 rounded border border-gray-600">
              Нет активных триггерных сообщений для этого заказа
            </div>
          )}
        </div>

        {/* Секция прогревочных сообщений */}
        <div className="mb-4">
          <h4 className="font-semibold mb-2 text-green-200">🎵 Прогревочные сообщения</h4>
          {warmingMessagesLoading ? (
            <div className="text-center text-gray-400">Загрузка прогревочных сообщений...</div>
          ) : warmingMessagesError ? (
            <div className="text-red-400 text-sm">{warmingMessagesError}</div>
          ) : warmingMessages.length > 0 ? (
            <div className="space-y-3">
              {warmingMessages.map((message, index) => (
                <div key={index} className="p-3 bg-gray-700 rounded border border-gray-600">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex-1">
                      <div className="font-medium text-white mb-1">
                        {message.message_type === "song_warming_example" && "🎵 Прогревочное (пример)"}
                        {message.message_type === "song_warming_motivation" && "💪 Прогревочное (мотивация)"}
                        {!["song_warming_example", "song_warming_motivation"].includes(message.message_type) && message.message_type}
                      </div>
                      <div className="text-sm text-gray-300">
                        Количество: {message.count} | ID: {message.message_ids}
                      </div>
                      <div className="text-sm text-gray-400">
                        Следующая отправка: {message.next_scheduled}
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      <Button
                        onClick={() => handleDeleteTriggerMessages([message.message_type])}
                        className="text-xs bg-red-600 hover:bg-red-700 text-white"
                        title="Удалить все сообщения этого типа"
                      >
                        🗑️ Удалить
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
              <div className="mt-3 p-2 bg-green-900 border border-green-700 rounded text-sm text-green-200">
                💡 <strong>Подсказка:</strong> Прогревочные сообщения отправляются для поддержания интереса пользователя к проекту песни.
              </div>
            </div>
          ) : (
            <div className="text-center text-gray-400 p-4 bg-gray-700 rounded border border-gray-600">
              Нет активных прогревочных сообщений для этого заказа
            </div>
          )}
        </div>

        {/* История взаимодействия */}
        <div className="mb-4">
          <h4 className="font-semibold mb-2 text-blue-200">📋 История взаимодействия</h4>
          <div className="bg-gray-700 p-3 rounded">
            <div className="text-sm text-gray-300 mb-1">Создан: {order.created_at ? new Date(order.created_at).toLocaleString('ru-RU', { timeZone: 'Europe/Moscow' }) : 'неизвестно'}</div>
            <div className="text-sm text-gray-300 mb-1">Последнее изменение: {order.updated_at ? new Date(order.updated_at).toLocaleString('ru-RU') : 'неизвестно'}</div>
                          <div className="text-sm text-gray-300 mb-2">Текущий статус: <span className="text-white font-semibold">{translateStatus(order.status)}</span></div>
            
            {/* Следующий шаг */}
            <div className="text-sm text-blue-300">
              <strong>Следующий шаг:</strong> {
                order.status === "demo_content" ? "Ожидание перехода к оплате" :
                order.status === "waiting_payment" ? "Ожидание оплаты" :
                order.status === "paid" ? "Подготовка финальной версии" :
                order.status === "waiting_final" ? "Отправка финальной версии" :
                order.status === "completed" ? "Заказ завершен" :
                "Определяется автоматически"
              }
            </div>
          </div>
        </div>
        
        {/* Структурированные действия по этапам удалены по запросу пользователя */}
        
        {/* Формы для работы с заказом в порядке плана */}
        <div className="mb-6 p-4 bg-gray-800 rounded-lg">
          <h3 className="font-bold mb-4 text-lg text-blue-300">📤 Отправка сообщений и файлов</h3>
          
          {/* История взаимодействия */}
          <div className="mb-6 p-4 bg-gray-700 rounded-lg border border-gray-600">
            <h4 className="font-semibold mb-3 text-yellow-200">📋 История взаимодействия</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-gray-400">Создан:</span>
                <div className="text-white">{data.created_at ? new Date(data.created_at).toLocaleString('ru-RU', { timeZone: 'Europe/Moscow' }) : 'неизвестно'}</div>
              </div>
              <div>
                <span className="text-gray-400">Статус:</span>
                <div className="text-white">{translateStatus(data.status)}</div>
              </div>
              <div>
                <span className="text-gray-400">Следующий шаг:</span>
                <div className="text-white">
                  {data.status === "demo_content" ? "Ожидает перехода к оплате" : 
                   data.status === "waiting_payment" ? "Ожидает оплаты (глава 9)" :
                   data.status === "paid" ? "Оплачен, ожидает финальной версии" :
                   "В процессе создания"}
                </div>
              </div>
            </div>

            {/* История сообщений пользователя */}
            <div className="mt-4 p-3 bg-gray-600 rounded border border-gray-500">
              <h5 className="font-semibold mb-2 text-green-200">💬 История сообщений</h5>
              {messages.length > 0 ? (
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {messages.map((msg, index) => (
                    <div key={index} className="text-xs p-2 bg-gray-700 rounded">
                      <div className="text-gray-300">
                        <span className="font-medium text-white">{msg.sender === 'user' ? 'Пользователь' : 'Менеджер'}:</span> {msg.message}
                      </div>
                      <div className="text-gray-400 text-xs mt-1">
                        {new Date(msg.sent_at).toLocaleString('ru-RU')}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-gray-400 text-sm italic">
                  Сообщений пока нет
                </div>
              )}
            </div>

          </div>
          
          {/* 1. Демо-контент (для книг) / Демо-аудио (для песен) */}
          <div className="mb-4">
            <h4 className="font-semibold mb-2 text-blue-200">
              <span className="bg-blue-600 text-white px-2 py-1 rounded text-xs mr-2">
                {data.product === "Песня" ? "Глава 2" : "Глава 4"}
              </span>
              {data.product === "Песня" ? "🎧 Демо-аудио" : "📖 Демо-контент"}
            </h4>
                          <p className="text-sm text-gray-300 mb-2">
                {data.product === "Песня" 
                  ? "Отправка демо-версии песни с кнопкой. Используется после создания заказа песни." 
                  : "Отправка примеров страниц книги. Используется после создания персонажей."
                }
              </p>
            <form onSubmit={handleSendDemoContent} className="space-y-2">
              <div>
                <input
                  type="file"
                  accept={data.product === "Песня" ? allowedAudioTypes.join(',') : allAllowedTypes.join(',')}
                  multiple
                  onChange={(e) => {
                    const files = Array.from(e.target.files || []);
                    setDemoFiles(files);
                    setImageFile(files[0] || null); // Для обратной совместимости
                    
                    // Создаем превью для каждого файла
                    const previews: string[] = [];
                    files.forEach((file) => {
                      if (file.type.startsWith('image/')) {
                        const reader = new FileReader();
                        reader.onload = (e) => {
                          const result = e.target?.result as string;
                          previews.push(result);
                          setDemoFilePreviews([...previews]);
                        };
                        reader.readAsDataURL(file);
                      } else {
                        previews.push('');
                      }
                    });
                  }}
                  className="text-sm"
                />
                <p className="text-xs text-gray-400 mt-1">
                  Можно выбрать несколько файлов для демо-контента
                </p>
                {demoFiles.length > 0 && (
                  <div className="mt-2 p-2 bg-gray-800 rounded border border-gray-600">
                    <p className="text-sm text-white mb-1">
                      Выбрано файлов: {demoFiles.length}
                    </p>
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
                      {demoFilePreviews.map((preview, index) => (
                        preview && (
                          <div key={index} className="relative group">
                            <img
                              src={preview}
                              alt={`Превью ${index + 1}`}
                              className="w-full h-20 object-cover rounded border border-gray-600 cursor-pointer hover:opacity-80 transition-opacity"
                              onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                console.log(`🔍 Клик на превью демо ${index}`);
                                // Открываем модальное окно с превью
                                setSelectedPreviewIndex(index);
                                setSelectedPhoto(`preview_${index}`);
                                setIsPhotoModalOpen(true);
                                console.log(`✅ Модальное окно должно открыться`);
                              }}
                            />
                            <div className="absolute inset-0 bg-black bg-opacity-50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                              <span className="text-white text-xs font-medium">
                                Демо {index + 1}
                              </span>
                            </div>
                          </div>
                        )
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <div className="text-sm text-gray-400 p-2 bg-gray-800 rounded border border-gray-600">
                <strong>Демо-контент:</strong> {data.product === "Песня" 
                  ? '"Спасибо за ожидание ✨\nДемо-версия твоей песни готова 💌\nМы собрали её первые ноты с теплом и уже знаем, как превратить их в полную мелодию, которая тронет до мурашек.\n\nЧтобы создать по-настоящему авторскую историю с твоими деталями, моментами и чувствами, нам нужно чуть больше информации 🧩\n\nТвоя история достойна того, чтобы зазвучать полностью и стать запоминающимся подарком для тебя и получателя ❤️‍🔥"' 
                  : '"Пробные страницы вашей книги готовы ☑️\nМы старались, чтобы они были тёплыми и живыми.\n\nНо впереди ещё больше — иллюстратор вдохновился вашей историей и собрал десятки сюжетов для полной версии книги."'
                }
              </div>
              <div className="text-sm text-gray-400 p-2 bg-gray-800 rounded border border-gray-600">
                <strong>Кнопка:</strong> {data.product === "Песня" 
                  ? '"Узнать цену" → переход к оплате' 
                  : '"Узнать цену" → переход к оплате'
                }
              </div>
              <div className="flex gap-2">
                <Button type="submit" disabled={sendingImage} className="bg-blue-600 hover:bg-blue-700">
                  {sendingImage ? "Отправка..." : `Отправить ${data.product === "Песня" ? "демо-аудио" : "демо-контент"}`}
                </Button>
                {data.product === "Книга" && data.status === "demo_content" && (
                  <Button 
                    type="button" 
                    onClick={() => handleContinueToPayment()}
                    disabled={sending}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    {sending ? "Переход..." : "Перейти к оплате"}
                  </Button>
                )}
              </div>
              {imageSuccess && (
                <div className={`text-green-400 text-sm p-2 rounded border ${smoothTransitionClasses.success}`}>
                  {imageSuccess}
                </div>
              )}
              {imageError && (
                <div className={`text-red-400 text-sm mt-2 p-2 rounded border ${smoothTransitionClasses.error}`}>
                  ❌ {imageError}
                </div>
              )}
              {sendSuccess && (
                <div className={`text-green-400 text-sm p-2 rounded border ${smoothTransitionClasses.success}`}>
                  ✅ Заказ успешно переведен к оплате!
                </div>
              )}
              {sendError && (
                <div className={`text-red-400 text-sm p-2 rounded border ${smoothTransitionClasses.error}`}>
                  ❌ {sendError}
                </div>
              )}
            </form>
          </div>



          {/* Загрузка индивидуальных страниц */}
          {data.product === "Книга" && (
            <div className="mb-4">
              <h4 className="font-semibold mb-2 text-purple-200">
                <span className="bg-purple-600 text-white px-2 py-1 rounded text-xs mr-2">Глава 5</span>
                🖼️ Индивидуальные страницы
              </h4>
              <p className="text-sm text-gray-300 mb-2">
                Загрузка индивидуальных фотографий страниц для выбора пользователем. 
                Каждая страница будет отправлена пользователю с описанием.
                <br />
                <span className="text-blue-300 font-medium">Используется после демо-контента, когда пользователь готов выбирать сюжеты.</span>
              </p>
              
              {/* Быстрая загрузка */}
              <div className="mb-4 p-3 bg-gray-800 rounded border border-gray-600">
                <h5 className="font-medium text-white mb-2">⚡ Быстрая загрузка (до 10 фото)</h5>
                <p className="text-xs text-gray-400 mb-3">
                  Выберите несколько файлов сразу для быстрой загрузки. Файлы будут пронумерованы автоматически.
                </p>
                <form onSubmit={handleBulkUpload} className="space-y-3">
                  <div>
                    <input
                      type="file"
                      accept="image/*"
                      multiple
                      onChange={(e) => handleBulkFileChange(e.target.files)}
                      className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white text-sm"
                    />
                    {bulkFiles.length > 0 && (
                      <div className="mt-3">
                        <div className="text-sm text-gray-300 mb-2">
                          Выбрано файлов: {bulkFiles.length}
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
                          {bulkFilePreviews.map((preview, index) => (
                            preview && (
                              <div key={index} className="relative group">
                                <img
                                  src={preview}
                                  alt={`Превью ${index + 1}`}
                                  className="w-full h-20 object-cover rounded border border-gray-600 cursor-pointer hover:opacity-80 transition-opacity"
                                  onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    // Открываем модальное окно с превью страницы
                                    setSelectedPreviewIndex(index);
                                    setSelectedPhoto(`page_preview_${index}`);
                                    setIsPhotoModalOpen(true);
                                  }}
                                />
                                <div className="absolute inset-0 bg-black bg-opacity-50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                  <span className="text-white text-xs font-medium">
                                    Страница {index + 1}
                                  </span>
                                </div>
                              </div>
                            )
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      type="submit"
                      disabled={uploadingBulk || bulkFiles.length === 0}
                      className="bg-orange-600 hover:bg-orange-700"
                    >
                      {uploadingBulk ? "Загрузка..." : `Быстро загрузить ${bulkFiles.length} файлов`}
                    </Button>
                  </div>
                  {bulkSuccess && (
                    <div className={`text-green-400 text-sm p-2 rounded border ${smoothTransitionClasses.success}`}>
                      {bulkSuccess}
                    </div>
                  )}
                  {bulkError && (
                    <div className={`text-red-400 text-sm p-2 rounded border ${smoothTransitionClasses.error}`}>
                      ❌ {bulkError}
                    </div>
                  )}
                </form>
              </div>
              
              <div className="border-t border-gray-600 pt-4 mb-4">
                <h5 className="font-medium text-white mb-2">📝 Детальная загрузка</h5>
                <p className="text-xs text-gray-400 mb-3">
                  Загружайте файлы по одному с индивидуальными описаниями.
                </p>
              <form onSubmit={handleUploadPages} className="space-y-4">
                {pageFiles.map((file, index) => (
                  <div key={index} className="border border-gray-600 rounded p-3 bg-gray-800">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm text-gray-300">Страница {index + 1}</span>
                      <Button
                        type="button"
                        onClick={() => removePageSlot(index)}
                        className="bg-red-600 hover:bg-red-700 text-xs px-2 py-1"
                      >
                        Удалить
                      </Button>
                    </div>
                    <div className="space-y-2">
                      <input
                        type="file"
                        accept="image/*"
                        onChange={(e) => handlePageFileChange(index, e.target.files?.[0] || null)}
                        className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white text-sm"
                      />
                      {pageFilePreviews[index] && (
                        <div className="mt-2">
                          <img
                            src={pageFilePreviews[index]}
                            alt={`Превью страницы ${index + 1}`}
                            className="w-full max-w-xs h-32 object-cover rounded border border-gray-600 cursor-pointer hover:opacity-80 transition-opacity"
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              // Открываем модальное окно с превью страницы
                              setSelectedPreviewIndex(index);
                              setSelectedPhoto(`detail_page_preview_${index}`);
                              setIsPhotoModalOpen(true);
                            }}
                          />
                        </div>
                      )}
                      <input
                        type="text"
                        placeholder={`Описание страницы ${index + 1} (например: "Дочка и мама пьют чай")`}
                        value={pageDescriptions[index] || ""}
                        onChange={(e) => handlePageDescriptionChange(index, e.target.value)}
                        className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white text-sm"
                      />
                    </div>
                  </div>
                ))}
                
                <div className="flex gap-2">
                  <Button
                    type="button"
                    onClick={addPageSlot}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    + Добавить страницу
                  </Button>
                  <Button 
                    type="submit" 
                    disabled={uploadingPages || pageFiles.length === 0}
                    className="bg-purple-600 hover:bg-purple-700"
                  >
                    {uploadingPages ? "Загрузка..." : `Отправить ${pageFiles.length} страниц`}
                  </Button>
                </div>
                
                {pagesSuccess && (
                  <div className={`text-green-400 text-sm p-2 rounded border ${smoothTransitionClasses.success}`}>
                    {pagesSuccess}
                  </div>
                )}
                {pagesError && (
                  <div className={`text-red-400 text-sm p-2 rounded border ${smoothTransitionClasses.error}`}>
                    ❌ {pagesError}
                  </div>
                )}
              </form>
              </div>
            </div>
          )}

          {/* Раздел "Выбор обложки" удален - обложки отправляются автоматически */}

          {/* 4. Черновик */}
          <div className="mb-4">
            <h4 className="font-semibold mb-2 text-blue-200">
              <span className="bg-blue-600 text-white px-2 py-1 rounded text-xs mr-2">
                {data.product === "Песня" ? "Глава 5" : "Глава 6"}
              </span>
              📝 {data.product === "Песня" ? "Предфинальная версия" : "Черновик"}
            </h4>
            {order?.status === "editing" && (
              <div className="bg-yellow-900 border border-yellow-600 rounded p-2 mb-3">
                <p className="text-yellow-200 text-sm font-medium">⚠️ Требуются правки</p>
                <p className="text-yellow-300 text-xs">Пользователь отправил комментарии. Проверьте историю сообщений ниже.</p>
              </div>
            )}
            <p className="text-sm text-gray-300 mb-2">
              {order?.status === "editing" ? 
                "Отправьте обновленный черновик с учетом правок:" : 
                "Отправка черновика для проверки"
              }
              <br />
              <span className="text-blue-300 font-medium">
                {data.product === "Песня" 
                  ? "Используется после одобрения демо-аудио пользователем. Автоматически добавит кнопки 'Всё супер' и 'Внести правки'." 
                  : "Используется после выбора обложки пользователем. Автоматически добавит кнопки 'Всё супер' и 'Внести правки'."
                }
              </span>
            </p>
            
            {/* Форма для отправки черновика */}
            <form onSubmit={handleSendImageWithButton} className="space-y-2">
              <div>
                <input
                  type="file"
                  accept={data.product === "Песня" ? allowedAudioTypes.join(',') : allAllowedTypes.join(',')}
                  onChange={(e) => handleImageFileChange(e.target.files?.[0] || null)}
                  className="text-sm"
                />
                {imageFilePreview && data.product !== "Песня" && (
                  <div className="mt-2">
                    <img
                      src={imageFilePreview}
                      alt="Превью черновика"
                      className="w-full max-w-xs h-32 object-cover rounded border border-gray-600"
                    />
                  </div>
                )}
              </div>
              <Button type="submit" disabled={sendingImage} className="bg-blue-600 hover:bg-blue-700 w-full">
                {sendingImage ? "Отправка..." : `Отправить ${data.product === "Песня" ? "предфинальную версию" : "черновик"}`}
              </Button>
              {imageSuccess && <div className="text-green-400 text-sm">✅ Отправлено!</div>}
              {imageError && <div className="text-red-400 text-sm">{imageError}</div>}
            </form>
          </div>


          {/* 6. Финальная версия */}
          <div className="mb-4">
            <h4 className="font-semibold mb-2 text-blue-200">
              <span className="bg-green-600 text-white px-2 py-1 rounded text-xs mr-2">
                {data.product === "Песня" ? "Глава 7" : "Глава 8"}
              </span>
              🎉 Финальная версия
            </h4>
            <p className="text-sm text-gray-300 mb-2">Отправка готовой работы</p>
            <form onSubmit={handleFinalUpload} className="space-y-2">
              <div>
                <input
                  type="file"
                  accept={data.product === "Песня" ? allowedAudioTypes.join(',') : allAllowedTypes.join(',')}
                  onChange={(e) => setFinalFile(e.target.files?.[0] || null)}
                  className="text-sm"
                />
              </div>
              <Button type="submit" disabled={uploading} className="bg-green-600 hover:bg-green-700">
                {uploading ? "Загрузка..." : "Отправить финальную версию"}
              </Button>
              {finalSuccess && <div className="text-green-400 text-sm">{finalSuccess}</div>}
              {uploadError && <div className="text-red-400 text-sm">{uploadError}</div>}
            </form>
          </div>

          {/* 7. Общие сообщения */}
          <div className="mb-4">
            <h4 className="font-semibold mb-2 text-blue-200">💬 Общие сообщения</h4>
            <p className="text-sm text-gray-300 mb-2">Отправка текстовых сообщений с возможностью прикрепления файлов</p>
            <form onSubmit={handleSendMessage} className="space-y-3">
              {/* Поле для текста сообщения */}
              <div>
                <textarea
                  placeholder="Текст сообщения"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white"
                  rows={3}
                />
              </div>

              {/* Поле для загрузки файла */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Прикрепить файл (необязательно):</label>
                <input
                  type="file"
                  onChange={(e) => setMessageFile(e.target.files?.[0] || null)}
                  className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700"
                  accept=".pdf,.jpg,.jpeg,.png,.gif,.bmp,.webp,.mp4,.avi,.mov,.mkv,.webm,.mp3,.wav,.ogg,.m4a,.aac,.doc,.docx,.txt"
                />
                {messageFile && (
                  <div className="mt-2 text-sm text-green-400">
                    ✅ Прикреплен файл: {messageFile.name} ({(messageFile.size / 1024 / 1024).toFixed(2)} МБ)
                  </div>
                )}
              </div>

              <Button type="submit" disabled={sending} className="bg-blue-600 hover:bg-blue-700">
                {sending ? "Отправка..." : "Отправить сообщение"}
              </Button>
              {sendSuccess && <div className="text-green-400 text-sm">✅ Сообщение отправлено!</div>}
              {sendError && <div className="text-red-400 text-sm">{sendError}</div>}
            </form>
          </div>
        </div>
      </div>

      {/* Модальное окно для просмотра фотографий */}
      {isPhotoModalOpen && selectedPhoto && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-[9999]" 
          style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.8)' }}
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              closePhotoModal();
            }
          }}
        >
          <div 
            className="bg-gray-800 p-8 rounded-lg max-w-6xl max-h-[95vh] w-[95vw] overflow-auto relative z-[10000]"
            onClick={(e) => e.stopPropagation()}
            style={{ backgroundColor: '#374151', borderRadius: '8px', padding: '32px' }}
          >
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-white">Просмотр фотографии</h3>
              <button
                onClick={closePhotoModal}
                className="text-gray-400 hover:text-white text-2xl font-bold"
              >
                ×
              </button>
            </div>
            <div className="mb-4">
              {(() => { console.log(`🔍 Модальное окно: selectedPhoto=${selectedPhoto}, selectedPreviewIndex=${selectedPreviewIndex}`); return null; })()}
              {selectedPhoto.startsWith('preview_') && selectedPreviewIndex !== null ? (
                <img
                  src={demoFilePreviews[selectedPreviewIndex]}
                  alt="Превью изображения"
                  className="max-w-full max-h-[70vh] object-contain mx-auto"
                />
              ) : selectedPhoto.startsWith('page_preview_') && selectedPreviewIndex !== null ? (
                <img
                  src={bulkFilePreviews[selectedPreviewIndex]}
                  alt="Превью страницы"
                  className="max-w-full max-h-[70vh] object-contain mx-auto"
                />
              ) : selectedPhoto.startsWith('detail_page_preview_') && selectedPreviewIndex !== null ? (
                <img
                  src={pageFilePreviews[selectedPreviewIndex]}
                  alt="Превью детальной страницы"
                  className="max-w-full max-h-[70vh] object-contain mx-auto"
                />
              ) : (
                <img
                  src={getProtectedImageUrl(selectedPhoto)}
                  alt="Фотография"
                  className="max-w-full max-h-[70vh] object-contain mx-auto"
                />
              )}
            </div>
            <div className="flex gap-2 justify-center">
              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  if (selectedPhoto.startsWith('preview_') && selectedPreviewIndex !== null) {
                    // Скачиваем превью изображение
                    const link = document.createElement('a');
                    link.href = demoFilePreviews[selectedPreviewIndex];
                    link.download = `demo_preview_${selectedPreviewIndex + 1}.jpg`;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                  } else if (selectedPhoto.startsWith('page_preview_') && selectedPreviewIndex !== null) {
                    // Скачиваем превью страницы
                    const link = document.createElement('a');
                    link.href = bulkFilePreviews[selectedPreviewIndex];
                    link.download = `page_preview_${selectedPreviewIndex + 1}.jpg`;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                  } else if (selectedPhoto.startsWith('detail_page_preview_') && selectedPreviewIndex !== null) {
                    // Скачиваем превью детальной страницы
                    const link = document.createElement('a');
                    link.href = pageFilePreviews[selectedPreviewIndex];
                    link.download = `detail_page_preview_${selectedPreviewIndex + 1}.jpg`;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                  } else {
                    // Скачиваем обычное изображение
                    const downloadImage = async () => {
                      try {
                        const token = localStorage.getItem("token");
                        const url = `/admin/files/${selectedPhoto}${token ? `?token=${token}` : ''}`;
                        
                        const response = await fetch(url);
                        if (!response.ok) {
                          throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        
                        const blob = await response.blob();
                        const downloadUrl = window.URL.createObjectURL(blob);
                        
                        const link = document.createElement('a');
                        link.href = downloadUrl;
                        link.download = selectedPhoto.split('/').pop() || 'photo';
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                        
                        // Очищаем URL объект
                        window.URL.revokeObjectURL(downloadUrl);
                      } catch (error) {
                        console.error('Ошибка при скачивании изображения:', error);
                        // Fallback: попробуем открыть в новой вкладке
                        window.open(getProtectedImageUrl(selectedPhoto), '_blank');
                      }
                    };
                    
                    downloadImage();
                  }
                }}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded"
              >
                📥 Скачать
              </button>
              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  closePhotoModal();
                }}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded"
              >
                Закрыть
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Модальное окно для подтверждения выбора обложки */}
      {showCoverSelection && selectedCover !== null && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-[9999]" 
          style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.8)' }}
          onClick={() => setShowCoverSelection(false)}
        >
          <div 
            className="bg-gray-800 p-8 rounded-lg max-w-4xl max-h-[95vh] w-[90vw] overflow-auto relative z-[10000]"
            onClick={(e) => e.stopPropagation()}
            style={{ backgroundColor: '#374151', borderRadius: '8px', padding: '32px' }}
          >
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-white">Подтверждение выбора обложки</h3>
              <button
                onClick={() => setShowCoverSelection(false)}
                className="text-gray-400 hover:text-white text-2xl font-bold"
              >
                ×
              </button>
            </div>
            
            <div className="mb-6">
              <div className="text-center mb-4">
                <img
                  src={`/covers/${selectedCover?.filename || ''}`}
                  alt={selectedCover?.name || 'Обложка'}
                  className="max-w-full max-h-[70vh] object-contain mx-auto rounded"
                  onError={(e) => {
                    e.currentTarget.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200' viewBox='0 0 200 200'%3E%3Crect width='200' height='200' fill='%23f3f4f6'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%236b7280'%3EОбложка не найдена%3C/text%3E%3C/svg%3E";
                  }}
                />
              </div>
              
              <div className="text-center mb-4">
                <h4 className="text-lg font-semibold text-white mb-2">{selectedCover?.name || 'Обложка'}</h4>
                <p className="text-gray-300">Категория: {selectedCover?.category || 'Не указана'}</p>
                <p className="text-gray-400 text-sm">Создана: {selectedCover?.created_at ? new Date(selectedCover.created_at).toLocaleDateString() : 'Не указана'}</p>
              </div>
              
              <div className="bg-blue-900 border border-blue-700 rounded-lg p-3 mb-4">
                <p className="text-blue-200 text-sm">
                  <strong>ℹ️ Информация:</strong> Эта обложка будет добавлена в заказ как выбранный вариант. 
                  Пользователь получит уведомление о выборе обложки.
                </p>
              </div>
            </div>
            
            <div className="flex gap-2 justify-center">
              <Button
                onClick={() => {
                  if (selectedCover) {
                    confirmCoverSelection();
                  }
                }}
                className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 text-sm"
              >
                ✅ Подтвердить
              </Button>
              <Button
                onClick={() => setShowCoverSelection(false)}
                className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 text-sm"
              >
                Отмена
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Модальное окно для просмотра обложек */}
      {isCoverModalOpen && selectedCoverImage !== null && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-[9999]" 
          style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.8)' }}
          onClick={closeCoverModal}
        >
          <div 
            className="bg-gray-800 p-6 rounded-lg max-w-4xl max-h-[90vh] overflow-auto relative z-[10000]"
            onClick={(e) => e.stopPropagation()}
            style={{ backgroundColor: '#374151', borderRadius: '8px', padding: '24px' }}
          >
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-white">Просмотр обложки</h3>
              <button
                onClick={closeCoverModal}
                className="text-gray-400 hover:text-white text-2xl font-bold"
              >
                ×
              </button>
            </div>
            <div className="mb-4">
              <img
                src={`/covers/${selectedCoverImage}`}
                alt="Обложка"
                className="max-w-full max-h-[70vh] object-contain mx-auto"
              />
            </div>
            <div className="flex gap-2 justify-center">
              <button
                onClick={() => selectedCoverImage && window.open(`/covers/${selectedCoverImage}`, '_blank')}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded"
              >
                📥 Скачать
              </button>
              <button
                onClick={closeCoverModal}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded"
              >
                Закрыть
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};





