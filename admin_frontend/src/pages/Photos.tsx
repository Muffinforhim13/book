import React, { useEffect, useState } from "react";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { translateStatus } from "../utils/statusTranslations";

interface Photo {
  id: number;
  order_id: number;
  filename: string;
  type: string;
  created_at: string;
  path: string;  // Добавляем поле path
  order_data?: string;
  user_id?: number;
}

interface Order {
  id: number;
  user_id: number;
  order_data: string;
  status: string;
  username?: string;
  created_at: string;
}

interface CoverTemplate {
  id: number;
  name: string;
  filename: string;
  category: string;
  created_at: string;
}

interface BookStyle {
  id: number;
  name: string;
  description: string;
  filename: string;
  category: string;
  created_at: string;
}

interface VoiceStyle {
  id: number;
  name: string;
  description: string;
  filename: string;
  gender: string;
  category: string;
  created_at: string;
}

const PhotosPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'orders' | 'covers' | 'styles' | 'voices'>('orders');
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [coverTemplates, setCoverTemplates] = useState<CoverTemplate[]>([]);
  const [bookStyles, setBookStyles] = useState<BookStyle[]>([]);
  const [voiceStyles, setVoiceStyles] = useState<VoiceStyle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedOrder, setSelectedOrder] = useState<number | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [userPermissions, setUserPermissions] = useState<{is_super_admin: boolean} | null>(null);
  
  // Состояния для добавления обложек
  const [showAddCoverForm, setShowAddCoverForm] = useState(false);
  const [newCover, setNewCover] = useState({
    name: '',
    category: '',
    file: null as File | null
  });
  const [addingCover, setAddingCover] = useState(false);
  const [addCoverError, setAddCoverError] = useState('');
  const [addCoverSuccess, setAddCoverSuccess] = useState('');
  
  // Состояния для добавления стилей
  const [showAddStyleForm, setShowAddStyleForm] = useState(false);
  const [newStyle, setNewStyle] = useState({
    name: 'Pixar 🌈 — доступен',
    description: 'Pixar 🌈\n\n«Стиль Pixar — кинематографично-мультяшный, яркий и эмоциональный.\nКнига получится красочной и живой, с выразительными героями и насыщенными деталями. Книга будет как добрый мультфильм, который вызывает улыбку и слёзы одновременно слезы🥲»',
    file: null as File | null
  });
  const [addingStyle, setAddingStyle] = useState(false);
  const [addStyleError, setAddStyleError] = useState('');
  const [addStyleSuccess, setAddStyleSuccess] = useState('');
  
  // Состояния для редактирования стилей
  const [editingStyle, setEditingStyle] = useState<BookStyle | null>(null);
  const [showEditStyleForm, setShowEditStyleForm] = useState(false);
  const [editingStyleData, setEditingStyleData] = useState({
    name: '',
    description: '',
    file: null as File | null
  });
  const [editingStyleLoading, setEditingStyleLoading] = useState(false);
  
  // Состояния для добавления голосов
  const [showAddVoiceForm, setShowAddVoiceForm] = useState(false);
  const [newVoice, setNewVoice] = useState({
    gender: 'male',
    category: 'gentle',
    file: null as File | null
  });
  const [addingVoice, setAddingVoice] = useState(false);
  const [addVoiceError, setAddVoiceError] = useState('');
  const [addVoiceSuccess, setAddVoiceSuccess] = useState('');
  
  // Состояния для редактирования голосов
  const [editingVoice, setEditingVoice] = useState<VoiceStyle | null>(null);
  const [showEditVoiceForm, setShowEditVoiceForm] = useState(false);
  const [editingVoiceData, setEditingVoiceData] = useState({
    gender: 'male',
    file: null as File | null
  });
  const [editingVoiceLoading, setEditingVoiceLoading] = useState(false);

  // Состояния для модальных окон
  const [showCoverModal, setShowCoverModal] = useState(false);
  const [selectedCover, setSelectedCover] = useState<CoverTemplate | null>(null);
  const [showStyleModal, setShowStyleModal] = useState(false);
  const [selectedStyle, setSelectedStyle] = useState<BookStyle | null>(null);
  const [showVoiceModal, setShowVoiceModal] = useState(false);
  const [selectedVoice, setSelectedVoice] = useState<VoiceStyle | null>(null);

  useEffect(() => {
    fetchUserPermissions();
    fetchPhotos();
    fetchOrders();
    fetchCoverTemplates();
    fetchBookStyles();
    fetchVoiceStyles();
  }, []);

  const fetchUserPermissions = async () => {
    try {
      const token = localStorage.getItem("token");
      console.log("🔍 Загружаем права пользователя...");
      const response = await fetch("/admin/profile/permissions", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      console.log("📡 Ответ сервера для прав:", response.status, response.statusText);
      if (response.ok) {
        const data = await response.json();
        console.log("👤 Полученные права пользователя:", data);
        setUserPermissions(data);
      } else {
        console.error("❌ Ошибка получения прав пользователя:", response.status);
      }
    } catch (err) {
      console.error("❌ Ошибка загрузки прав доступа:", err);
    }
  };

  const fetchPhotos = async () => {
    try {
      const token = localStorage.getItem("token");
      if (!token) {
        setError("Токен авторизации не найден");
        return;
      }
      
      console.log("🔍 Загружаем фотографии...");
      const response = await fetch("/admin/photos", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      console.log("📡 Ответ сервера для фотографий:", response.status, response.statusText);
      
      if (response.status === 401) {
        setError("Ошибка авторизации. Пожалуйста, войдите снова.");
        // Перенаправляем на страницу входа
        window.location.href = "/admin/login";
        return;
      }
      
      if (response.ok) {
        const data = await response.json();
        console.log("📸 Полученные фотографии:", data);
        setPhotos(data);
        setError(""); // Очищаем ошибки при успешной загрузке
      } else {
        const errorText = await response.text();
        console.error("❌ Ошибка загрузки фотографий:", response.status, errorText);
        setError(`Ошибка загрузки фотографий: ${response.status}`);
      }
    } catch (err) {
      console.error("❌ Исключение при загрузке фотографий:", err);
      setError("Ошибка загрузки фотографий");
    } finally {
      setLoading(false);
    }
  };

  const fetchOrders = async () => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch("/admin/orders", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setOrders(data);
      }
    } catch (err) {
      console.error("Ошибка загрузки заказов:", err);
    }
  };

  const fetchCoverTemplates = async () => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch("/admin/cover-templates", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setCoverTemplates(data);
      }
    } catch (err) {
      console.error("Ошибка загрузки шаблонов обложек:", err);
    }
  };

  const fetchBookStyles = async () => {
    try {
      const token = localStorage.getItem("token");
      console.log("🔍 Загружаем стили книг...");
      const response = await fetch("/admin/book-styles", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      console.log("📡 Ответ сервера для стилей книг:", response.status, response.statusText);
      if (response.ok) {
        const data = await response.json();
        console.log("📊 Получены стили книг:", data);
        setBookStyles(data);
      } else {
        console.error("❌ Ошибка ответа сервера для стилей книг:", response.status);
        setError("Ошибка загрузки стилей книг");
      }
    } catch (err) {
      console.error("❌ Ошибка загрузки стилей книг:", err);
      setError("Ошибка загрузки стилей книг");
    }
  };

  const fetchVoiceStyles = async () => {
    try {
      const token = localStorage.getItem("token");
      console.log("🔍 Загружаем стили голоса...");
      const response = await fetch("/admin/voice-styles", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      console.log("📡 Ответ сервера:", response.status, response.statusText);
      if (response.ok) {
        const data = await response.json();
        console.log("✅ Получены стили голоса:", data);
        setVoiceStyles(data);
      } else {
        console.error("❌ Ошибка загрузки стилей голоса:", response.status, response.statusText);
      }
    } catch (err) {
      console.error("❌ Ошибка загрузки стилей голоса:", err);
    }
  };

  // Функция для удаления обложки
  const deleteCover = async (template: CoverTemplate) => {
    if (!window.confirm(`Вы уверены, что хотите удалить обложку "${template.name}"?`)) {
      return;
    }
    
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/covers/${template.id}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        setAddCoverSuccess(`✅ Обложка "${template.name}" удалена!`);
        // Обновляем список обложек
        fetchCoverTemplates();
        // Автоматически скрываем сообщение об успехе через 3 секунды
        setTimeout(() => setAddCoverSuccess(''), 3000);
      } else {
        throw new Error("Ошибка удаления обложки");
      }
    } catch (error: any) {
      setAddCoverError(`Ошибка: ${error.message}`);
    }
  };

  const handleAddCover = async () => {
    if (!newCover.name || !newCover.category || !newCover.file) {
      setAddCoverError('Заполните все поля');
      return;
    }

    setAddingCover(true);
    setAddCoverError('');

    try {
      const token = localStorage.getItem("token");
      const formData = new FormData();
      formData.append('name', newCover.name);
      formData.append('category', newCover.category);
      formData.append('file', newCover.file);

      const response = await fetch("/admin/cover-templates", {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (response.ok) {
        setAddCoverSuccess('Обложка успешно добавлена!');
        setNewCover({ name: '', category: '', file: null });
        setShowAddCoverForm(false);
        // Обновляем список обложек
        fetchCoverTemplates();
        
        // Автоматически скрываем сообщение об успехе через 3 секунды
        setTimeout(() => setAddCoverSuccess(''), 3000);
      } else {
        const errorData = await response.json();
        setAddCoverError(errorData.detail || 'Ошибка при добавлении обложки');
      }
    } catch (err) {
      setAddCoverError('Ошибка при добавлении обложки');
    } finally {
      setAddingCover(false);
    }
  };

  const clearAddCoverForm = () => {
    setNewCover({ name: '', category: '', file: null });
    setAddCoverError('');
    setShowAddCoverForm(false);
  };

  const handleAddStyle = async () => {
    if (!newStyle.name || !newStyle.description || !newStyle.file) {
      setAddStyleError('Заполните все поля');
      return;
    }

    setAddingStyle(true);
    setAddStyleError('');

    try {
      const token = localStorage.getItem("token");
      const formData = new FormData();
      formData.append('name', newStyle.name);
      formData.append('description', newStyle.description);
      formData.append('category', 'Основные'); // Устанавливаем категорию по умолчанию
      formData.append('file', newStyle.file);

      const response = await fetch("/admin/book-styles", {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (response.ok) {
        setAddStyleSuccess('Стиль успешно добавлен!');
        setNewStyle({ 
          name: 'Pixar 🌈 — доступен', 
          description: 'Pixar 🌈\n\n«Стиль Pixar — кинематографично-мультяшный, яркий и эмоциональный.\nКнига получится красочной и живой, с выразительными героями и насыщенными деталями. Книга будет как добрый мультфильм, который вызывает улыбку и слёзы одновременно слезы🥲»', 
          file: null 
        });
        setShowAddStyleForm(false);
        // Обновляем список стилей
        fetchBookStyles();
        
        // Автоматически скрываем сообщение об успехе через 3 секунды
        setTimeout(() => setAddStyleSuccess(''), 3000);
      } else {
        const errorData = await response.json();
        setAddStyleError(errorData.detail || 'Ошибка при добавлении стиля');
      }
    } catch (err) {
      setAddStyleError('Ошибка при добавлении стиля');
    } finally {
      setAddingStyle(false);
    }
  };

  const clearAddStyleForm = () => {
    setNewStyle({ 
      name: 'Pixar 🌈 — доступен', 
      description: 'Pixar 🌈\n\n«Стиль Pixar — кинематографично-мультяшный, яркий и эмоциональный.\nКнига получится красочной и живой, с выразительными героями и насыщенными деталями. Книга будет как добрый мультфильм, который вызывает улыбку и слёзы одновременно слезы🥲»', 
      file: null 
    });
    setAddStyleError('');
    setShowAddStyleForm(false);
  };

  const handleAddVoice = async () => {
    if (!newVoice.file) {
      setAddVoiceError('Выберите аудиофайл');
      return;
    }

    setAddingVoice(true);
    setAddVoiceError('');

    try {
      const token = localStorage.getItem("token");
      const formData = new FormData();
      formData.append('name', newVoice.gender === 'male' ? 'Мужской' : 'Женский');
      formData.append('description', newVoice.gender === 'male' ? 'Мужской голос' : 'Женский голос');
      formData.append('gender', newVoice.gender);
      formData.append('category', newVoice.category);
      formData.append('file', newVoice.file);

      const response = await fetch("/admin/voice-styles", {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (response.ok) {
        setAddVoiceSuccess('Голос успешно добавлен!');
        setNewVoice({ gender: 'male', category: 'gentle', file: null });
        setShowAddVoiceForm(false);
        // Обновляем список голосов
        fetchVoiceStyles();
        
        // Автоматически скрываем сообщение об успехе через 3 секунды
        setTimeout(() => setAddVoiceSuccess(''), 3000);
      } else {
        const errorData = await response.json();
        setAddVoiceError(errorData.detail || 'Ошибка при добавлении голоса');
      }
    } catch (err) {
      setAddVoiceError('Ошибка при добавлении голоса');
    } finally {
      setAddingVoice(false);
    }
  };

  const clearAddVoiceForm = () => {
    setNewVoice({ gender: 'male', category: 'gentle', file: null });
    setAddVoiceError('');
    setShowAddVoiceForm(false);
  };

  // Функция для начала редактирования голоса
  const startEditVoice = (voice: VoiceStyle) => {
    setEditingVoice(voice);
    setEditingVoiceData({
      gender: voice.gender,
      file: null
    });
    setShowEditVoiceForm(true);
  };

  // Функция для сохранения редактирования голоса
  const saveEditVoice = async () => {
    if (!editingVoice) return;

    setEditingVoiceLoading(true);
    setAddVoiceError('');

    try {
      const token = localStorage.getItem("token");
      const formData = new FormData();
      formData.append('name', editingVoiceData.gender === 'male' ? 'Мужской' : 'Женский');
      formData.append('description', editingVoiceData.gender === 'male' ? 'Мужской голос' : 'Женский голос');
      formData.append('gender', editingVoiceData.gender);
      if (editingVoiceData.file) {
        formData.append('file', editingVoiceData.file);
      }

      const response = await fetch(`/admin/voice-styles/${editingVoice.id}`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (response.ok) {
        setAddVoiceSuccess('Голос успешно обновлен!');
        setShowEditVoiceForm(false);
        setEditingVoice(null);
        // Обновляем список голосов
        fetchVoiceStyles();
        
        // Автоматически скрываем сообщение об успехе через 3 секунды
        setTimeout(() => setAddVoiceSuccess(''), 3000);
      } else {
        const errorData = await response.json();
        setAddVoiceError(errorData.detail || 'Ошибка при обновлении голоса');
      }
    } catch (err) {
      setAddVoiceError('Ошибка при обновлении голоса');
    } finally {
      setEditingVoiceLoading(false);
    }
  };

  // Функция для отмены редактирования голоса
  const cancelEditVoice = () => {
    setShowEditVoiceForm(false);
    setEditingVoice(null);
    setEditingVoiceData({ gender: 'male', file: null });
  };

  // Функция для удаления голоса
  const deleteVoice = async (voice: VoiceStyle) => {
    if (!window.confirm(`Вы уверены, что хотите удалить голос "${voice.name}"?`)) {
      return;
    }
    
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/voice-styles/${voice.id}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        setAddVoiceSuccess(`✅ Голос "${voice.name}" удален!`);
        // Обновляем список голосов
        fetchVoiceStyles();
        // Автоматически скрываем сообщение об успехе через 3 секунды
        setTimeout(() => setAddVoiceSuccess(''), 3000);
      } else {
        throw new Error("Ошибка удаления голоса");
      }
    } catch (error: any) {
      setAddVoiceError(`Ошибка: ${error.message}`);
    }
  };

  // Функция для начала редактирования стиля
  const startEditStyle = (style: BookStyle) => {
    setEditingStyle(style);
    setEditingStyleData({
      name: style.name,
      description: style.description,
      file: null
    });
    setShowEditStyleForm(true);
  };

  // Функция для сохранения изменений стиля
  const saveEditStyle = async () => {
    if (!editingStyle || !editingStyleData.name || !editingStyleData.description) {
      setAddStyleError('Заполните все обязательные поля');
      return;
    }

    setEditingStyleLoading(true);
    setAddStyleError('');

    try {
      const token = localStorage.getItem("token");
      const formData = new FormData();
      formData.append('name', editingStyleData.name);
      formData.append('description', editingStyleData.description);
      formData.append('category', 'Основные'); // Устанавливаем категорию по умолчанию
      if (editingStyleData.file) {
        formData.append('file', editingStyleData.file);
      }

      const response = await fetch(`/admin/book-styles/${editingStyle.id}`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (response.ok) {
        setAddStyleSuccess('Стиль успешно обновлен!');
        setShowEditStyleForm(false);
        setEditingStyle(null);
        // Обновляем список стилей
        fetchBookStyles();
        
        // Автоматически скрываем сообщение об успехе через 3 секунды
        setTimeout(() => setAddStyleSuccess(''), 3000);
      } else {
        const errorData = await response.json();
        setAddStyleError(errorData.detail || 'Ошибка при обновлении стиля');
      }
    } catch (err) {
      setAddStyleError('Ошибка при обновлении стиля');
    } finally {
      setEditingStyleLoading(false);
    }
  };

  // Функция для отмены редактирования
  const cancelEditStyle = () => {
    setShowEditStyleForm(false);
    setEditingStyle(null);
    setEditingStyleData({ name: '', description: '', file: null });
  };

  // Функция для удаления стиля
  const deleteStyle = async (style: BookStyle) => {
    if (!window.confirm(`Вы уверены, что хотите удалить стиль "${style.name}"?`)) {
      return;
    }
    
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/book-styles/${style.id}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        setAddStyleSuccess(`✅ Стиль "${style.name}" удален!`);
        // Обновляем список стилей
        fetchBookStyles();
        // Автоматически скрываем сообщение об успехе через 3 секунды
        setTimeout(() => setAddStyleSuccess(''), 3000);
      } else {
        throw new Error("Ошибка удаления стиля");
      }
    } catch (error: any) {
      setAddStyleError(`Ошибка: ${error.message}`);
    }
  };

  const getOrderInfo = (orderId: number) => {
    const order = orders.find(o => o.id === orderId);
    if (order) {
      try {
        const orderData = JSON.parse(order.order_data);
        return {
          user_id: order.user_id,
          product: orderData.product || "Не указан",
          relation: orderData.relation || "Не указано",
          status: translateStatus(order.status),
          created_at: order.created_at
        };
      } catch {
        return { 
          user_id: order.user_id, 
          product: "Ошибка парсинга", 
          relation: "Ошибка парсинга",
          status: translateStatus(order.status),
          created_at: order.created_at
        };
      }
    }
    return null;
  };

  const getPhotoTypeLabel = (type: string) => {
    switch (type) {
      case "main_face_1": return "Лицо 1";
      case "main_face_2": return "Лицо 2";
      case "main_full": return "Полный рост";
      case "main_hero": return "Главный герой";
      case "main_hero_1": return "Главный герой - Фото 1";
      case "main_hero_2": return "Главный герой - Фото 2";
      case "main_hero_3": return "Главный герой - Фото 3";
      case "joint_photo": return "Совместное фото";
      case "hero_photo": return "Другой герой";
      case "uploaded": return "Загруженный файл";
      default:
        if (type.startsWith("page_")) {
          return `Страница ${type.split("_")[1]}`;
        }
        // Обработка фотографий других героев
        if (type.includes("_face_1")) {
          const heroName = type.split("_face_1")[0];
          return `${heroName} - Лицо 1`;
        }
        if (type.includes("_face_2")) {
          const heroName = type.split("_face_2")[0];
          return `${heroName} - Лицо 2`;
        }
        if (type.includes("_full")) {
          const heroName = type.split("_full")[0];
          return `${heroName} - Полный рост`;
        }
        return type;
    }
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

  // Группируем фотографии по заказам
  const photosByOrder = photos.reduce((acc, photo) => {
    if (!acc[photo.order_id]) {
      acc[photo.order_id] = [];
    }
    acc[photo.order_id].push(photo);
    return acc;
  }, {} as Record<number, Photo[]>);

  // Фильтруем заказы в зависимости от прав доступа
  const filteredOrders = userPermissions?.is_super_admin 
    ? orders 
    : orders.filter(order => {
        // Здесь должна быть логика проверки доступа к заказу
        // Пока оставляем все заказы для обычных менеджеров
        return true;
      });

  const filteredPhotos = selectedOrder 
    ? photos.filter(photo => photo.order_id === selectedOrder)
    : photos;


  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-center">Загрузка...</div>
      </div>
    );
  }

  const handleFileUpload = async (files: FileList | null, orderId: number) => {
    if (!files || files.length === 0) return;
    
    const formData = new FormData();
    formData.append('order_id', orderId.toString());
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      
      // Проверяем тип файла
      if (!allAllowedTypes.includes(file.type)) {
        alert(`Неподдерживаемый тип файла: ${file.name} (${file.type})`);
        continue;
      }
      
      formData.append('files', file);
    }
    
    try {
      const token = localStorage.getItem("token");
      const response = await fetch("/admin/photos/upload", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });
      
      if (response.ok) {
        alert("Файлы успешно загружены!");
        fetchPhotos();
      } else {
        const error = await response.json();
        alert(`Ошибка загрузки: ${error.detail}`);
      }
    } catch (error) {
      console.error("Ошибка загрузки файлов:", error);
      alert("Ошибка загрузки файлов");
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-4">Управление фотографиями/аудио</h1>
        
        {/* Переключатель вкладок */}
        <div className="flex space-x-4 mb-6">
          <button
            onClick={() => setActiveTab('orders')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'orders'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-600 text-gray-200 hover:bg-gray-500'
            }`}
          >
            📸 Фотографии по заказам ({photos.length})
          </button>
          <button
            onClick={() => setActiveTab('covers')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'covers'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-600 text-gray-200 hover:bg-gray-500'
            }`}
          >
            📚 Библиотека обложек
          </button>
          <button
            onClick={() => setActiveTab('styles')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'styles'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-600 text-gray-200 hover:bg-gray-500'
            }`}
          >
            🎨 Стили книг ({bookStyles.length})
          </button>
          <button
            onClick={() => setActiveTab('voices')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'voices'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-600 text-gray-200 hover:bg-gray-500'
            }`}
          >
            🎤 Стили голоса
          </button>
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}
      </div>

      {/* Вкладка "Фотографии по заказам" */}
      {activeTab === 'orders' && (
        <div>
          {/* Фильтр по заказу */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Фильтр по заказу:</label>
            <select
              value={selectedOrder || ""}
              onChange={(e) => setSelectedOrder(e.target.value ? Number(e.target.value) : null)}
              className="border border-gray-300 rounded px-3 py-2 w-full max-w-xs"
            >
              <option value="">Все заказы</option>
              {filteredOrders.map(order => {
                const orderInfo = getOrderInfo(order.id);
                return (
                  <option key={order.id} value={order.id}>
                    Заказ #{order.id} - {orderInfo?.product} ({orderInfo?.relation})
                  </option>
                );
              })}
            </select>
          </div>

          {/* Отображение состояния загрузки и ошибок */}
          {loading && (
            <div className="text-center py-8">
              <div className="text-gray-600">Загрузка фотографий...</div>
            </div>
          )}
          
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}
          
          {!loading && !error && photos.length === 0 && (
            <div className="text-center py-8">
              <div className="text-gray-600">Фотографии не найдены</div>
              <div className="text-sm text-gray-500 mt-2">
                Возможно, заказы еще не содержат загруженных фотографий
              </div>
            </div>
          )}

          {/* Группированные фотографии по заказам */}
          {!loading && !error && selectedOrder ? (
            // Показываем фотографии выбранного заказа
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredPhotos.map((photo) => {
                const orderInfo = getOrderInfo(photo.order_id);
                return (
                  <Card key={photo.id} className="p-4">
                    <div className="mb-3">
                      <img
                        src={`/${photo.path}`}
                        alt={`Фото заказа ${photo.order_id}`}
                        className="w-full h-48 object-cover rounded"
                        onError={(e) => {
                          e.currentTarget.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200' viewBox='0 0 200 200'%3E%3Crect width='200' height='200' fill='%23f3f4f6'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%236b7280'%3EФото не найдено%3C/text%3E%3C/svg%3E";
                        }}
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-sm font-medium">Заказ #{photo.order_id}</span>
                        <span className="text-xs text-gray-500">
                          {new Date(photo.created_at).toLocaleDateString('ru-RU', { timeZone: 'Europe/Moscow' })}
                        </span>
                      </div>
                      
                      <div className="text-sm">
                        <div><strong>Тип:</strong> {getPhotoTypeLabel(photo.type)}</div>
                        {orderInfo && (
                          <>
                            <div><strong>Продукт:</strong> {orderInfo.product}</div>
                            <div><strong>Отношение:</strong> {orderInfo.relation}</div>
                            <div><strong>Пользователь:</strong> {orderInfo.user_id}</div>
                          </>
                        )}
                      </div>

                      <div className="flex space-x-2 mt-3">
                        <Button
                          onClick={() => window.open(`/${photo.path}`, '_blank')}
                          className="text-xs"
                        >
                          Открыть
                        </Button>
                        <Button
                          onClick={async () => {
                            try {
                              const response = await fetch(`/${photo.path}`);
                              if (!response.ok) {
                                throw new Error(`HTTP error! status: ${response.status}`);
                              }
                              
                              const blob = await response.blob();
                              const downloadUrl = window.URL.createObjectURL(blob);
                              
                              const link = document.createElement('a');
                              link.href = downloadUrl;
                              link.download = photo.filename;
                              document.body.appendChild(link);
                              link.click();
                              document.body.removeChild(link);
                              
                              // Очищаем URL объект
                              window.URL.revokeObjectURL(downloadUrl);
                            } catch (error) {
                              console.error('Ошибка при скачивании изображения:', error);
                              // Fallback: попробуем открыть в новой вкладке
                              window.open(`/${photo.path}`, '_blank');
                            }
                          }}
                          className="text-xs bg-blue-500 hover:bg-blue-600 text-white"
                        >
                          Скачать
                        </Button>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          ) : (
            // Показываем заказы с их фотографиями
            <div className="space-y-6">
              {filteredOrders.map(order => {
                const orderInfo = getOrderInfo(order.id);
                const orderPhotos = photosByOrder[order.id] || [];
                console.log(`📸 Фотографии для заказа ${order.id}:`, orderPhotos);
                
                if (orderPhotos.length === 0) return null;

                return (
                  <Card key={order.id} className="p-6">
                    <div className="mb-4">
                      <h3 className="text-lg font-semibold mb-2">
                        Заказ #{order.id} - {orderInfo?.product} ({orderInfo?.relation})
                      </h3>
                      <div className="text-sm text-gray-600">
                        <div>Статус: {orderInfo?.status}</div>
                        <div>Создан: {new Date(orderInfo?.created_at || '').toLocaleDateString('ru-RU', { timeZone: 'Europe/Moscow' })}</div>
                        <div>Фотографий: {orderPhotos.length}</div>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                      {orderPhotos.map((photo) => (
                        <div key={photo.id} className="relative group">
                          <img
                            src={`/${photo.path}`}
                            alt={`Фото заказа ${photo.order_id}`}
                            className="w-full h-24 object-cover rounded cursor-pointer hover:opacity-80 transition-opacity"
                            onClick={() => window.open(`/${photo.path}`, '_blank')}
                            onError={(e) => {
                              console.log(`❌ Ошибка загрузки фото: ${photo.path}`);
                              e.currentTarget.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200' viewBox='0 0 200 200'%3E%3Crect width='200' height='200' fill='%23f3f4f6'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%236b7280'%3EФото не найдено%3C/text%3E%3C/svg%3E";
                            }}
                          />
                          <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 rounded flex items-center justify-center transition-all pointer-events-none">
                            <span className="text-white text-xs opacity-0 group-hover:opacity-100">👁️</span>
                          </div>
                          <div className="text-xs text-gray-500 mt-1 text-center">
                            {getPhotoTypeLabel(photo.type)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>
                );
              })}
            </div>
          )}

          {filteredPhotos.length === 0 && selectedOrder && (
            <div className="text-center text-gray-500 mt-8">
              Нет фотографий для выбранного заказа
            </div>
          )}
        </div>
      )}

      {/* Вкладка "Библиотека обложек" */}
      {activeTab === 'covers' && (
        <div>
          <div className="mb-4">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Готовые шаблоны обложек</h2>
              {userPermissions?.is_super_admin && (
                <Button
                  onClick={() => setShowAddCoverForm(!showAddCoverForm)}
                  className="bg-green-600 hover:bg-green-700 text-white"
                >
                  {showAddCoverForm ? 'Отмена' : '➕ Добавить обложку'}
                </Button>
              )}
            </div>
            <p className="text-gray-600 mb-4">
              Выберите обложку и добавьте её в заказ одним кликом
            </p>
          </div>

          {/* Форма добавления обложки для главного админа */}
          {showAddCoverForm && userPermissions?.is_super_admin && (
            <Card className="p-6 mb-6 bg-gray-50">
              <h3 className="text-lg font-semibold mb-4">Добавить новую обложку</h3>
              
              {addCoverError && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                  {addCoverError}
                </div>
              )}
              
              {addCoverSuccess && (
                <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
                  {addCoverSuccess}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Название обложки</label>
                  <Input
                    type="text"
                    value={newCover.name}
                    onChange={(e) => setNewCover({ ...newCover, name: e.target.value })}
                    placeholder="Введите название"
                    className="w-full"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-2">Категория</label>
                  <Input
                    type="text"
                    value={newCover.category}
                    onChange={(e) => setNewCover({ ...newCover, category: e.target.value })}
                    placeholder="Например: Романтика, Детектив"
                    className="w-full"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-2">Файл обложки</label>
                  <Input
                    type="file"
                    accept="image/*"
                    onChange={(e) => setNewCover({ ...newCover, file: e.target.files?.[0] || null })}
                    className="w-full"
                  />
                </div>
              </div>

              <div className="flex space-x-3">
                <Button
                  onClick={handleAddCover}
                  disabled={addingCover}
                  className="bg-green-600 hover:bg-green-700 text-white"
                >
                  {addingCover ? 'Добавление...' : 'Добавить обложку'}
                </Button>
                <Button
                  onClick={clearAddCoverForm}
                  className="border border-gray-300 text-gray-700 hover:bg-gray-50 bg-white"
                >
                  Очистить
                </Button>
              </div>
            </Card>
          )}


          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {coverTemplates.map((template) => (
              <Card key={template.id} className="p-4">
                <div className="mb-3">
                  <img
                    src={`/covers/${template.filename}`}
                    alt={template.name}
                    className="w-full h-48 object-cover rounded cursor-pointer hover:opacity-80 transition-opacity"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setSelectedCover(template);
                      setShowCoverModal(true);
                    }}
                    onError={(e) => {
                      e.currentTarget.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200' viewBox='0 0 200 200'%3E%3Crect width='200' height='200' fill='%23f3f4f6'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%236b7280'%3EОбложка не найдена%3C/text%3E%3C/svg%3E";
                    }}
                  />
                </div>
                
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">{template.name}</span>
                    <span className="text-xs text-gray-500">
                      {template.category}
                    </span>
                  </div>
                  
                  <div className="text-sm text-gray-600">
                    {template.category}
                  </div>

                  <div className="flex space-x-2 mt-3">
                    <Button
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        // Открываем в модальном окне вместо новой страницы
                        const modal = document.createElement('div');
                        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
                        modal.innerHTML = `
                          <div class="bg-white p-6 rounded-lg max-w-4xl max-h-[90vh] w-[90vw]">
                            <div class="flex justify-between items-center mb-4">
                              <h3 class="text-xl font-semibold">${template.name}</h3>
                              <button onclick="this.closest('.fixed').remove()" class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
                            </div>
                            <img src="/covers/${template.filename}" alt="${template.name}" class="w-full h-auto max-h-[70vh] object-contain" />
                          </div>
                        `;
                        document.body.appendChild(modal);
                        modal.addEventListener('click', (e) => {
                          if (e.target === modal) modal.remove();
                        });
                      }}
                      className="text-xs"
                    >
                      Просмотр
                    </Button>
                    <Button
                      onClick={() => {
                        // TODO: Добавить логику выбора заказа и добавления обложки
                        alert('Функция добавления обложки в заказ будет реализована позже');
                      }}
                      className="text-xs bg-green-500 hover:bg-green-600 text-white"
                    >
                      Добавить в заказ
                    </Button>
                    <Button
                      onClick={() => deleteCover(template)}
                      className="text-xs bg-red-500 hover:bg-red-600 text-white"
                    >
                      Удалить
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>

          {coverTemplates.length === 0 && (
            <div className="text-center text-gray-500 mt-8">
              Нет доступных шаблонов обложек
            </div>
          )}
        </div>
      )}

      {/* Вкладка "Стили книг" */}
      {activeTab === 'styles' && (
        <div>
          <div className="mb-4">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Примеры стилей книг</h2>
              <Button
                onClick={() => setShowAddStyleForm(!showAddStyleForm)}
                className="bg-green-600 hover:bg-green-700 text-white"
              >
                {showAddStyleForm ? 'Отмена' : '➕ Добавить стиль'}
              </Button>
            </div>
            <p className="text-gray-600 mb-4">
              Стили книг, которые будут показываться пользователям при выборе оформления
            </p>
          </div>

          {/* Форма добавления стиля */}
          {showAddStyleForm && (
            <Card className="p-6 mb-6 bg-gray-50">
              <h3 className="text-lg font-semibold mb-4">Добавить новый стиль книги</h3>
              
              {addStyleError && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                  {addStyleError}
                </div>
              )}
              
              {addStyleSuccess && (
                <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
                  {addStyleSuccess}
                </div>
              )}

              <div className="space-y-4 mb-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Выберите стиль</label>
                  <select
                    value={newStyle.name}
                    onChange={(e) => {
                      const selectedStyle = e.target.value;
                      let description = '';
                      
                      // Устанавливаем описание в зависимости от выбранного стиля
                      switch (selectedStyle) {
                        case 'Pixar 🌈 — доступен':
                          description = 'Pixar 🌈\n\n«Стиль Pixar — кинематографично-мультяшный, яркий и эмоциональный.\nКнига получится красочной и живой, с выразительными героями и насыщенными деталями. Книга будет как добрый мультфильм, который вызывает улыбку и слёзы одновременно слезы🥲»';
                          break;
                        case 'Love is 👩‍❤️‍👨 — заглушка':
                          description = 'Love is👩‍❤️‍👨\n\n«Стиль Love is — это романтичная атмосфера и особая близость.\nОн передаёт чувство заботы, трогательности и искренней любви. Иллюстрации будут светлыми и душевными, словно открытка с признанием💘»';
                          break;
                        case 'Ghibli 🏡 — заглушка':
                          description = 'Ghibli 🏡\n\n«Стиль Ghibli — сказочный, мечтательный, уютный.\nКнига получится атмосферной, уникальной, волшебной природой, магией в мелочах и ощущением, что чудо рядом. Книга станет сказкой для души, где магия переплетается с реальностью ✨»';
                          break;
                        default:
                          description = '';
                      }
                      
                      setNewStyle({ ...newStyle, name: selectedStyle, description });
                    }}
                    className="w-full border border-gray-300 rounded px-3 py-2"
                  >
                    <option value="Pixar">Pixar 🌈 — доступен</option>
                    <option value="Ghibli">Ghibli 🏡 — заглушка</option>
                    <option value="Love is">Love is 👩‍❤️‍👨 — заглушка</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-2">Описание стиля</label>
                  <textarea
                    value={newStyle.description}
                    onChange={(e) => setNewStyle({ ...newStyle, description: e.target.value })}
                    placeholder="Описание будет заполнено автоматически..."
                    className="w-full border border-gray-300 rounded px-3 py-2 h-20"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-2">Фотография стиля</label>
                  <Input
                    type="file"
                    accept="image/*"
                    onChange={(e) => setNewStyle({ ...newStyle, file: e.target.files?.[0] || null })}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Загрузите изображение, которое будет показываться пользователям при выборе стиля
                  </p>
                </div>
              </div>

              <div className="flex space-x-3">
                <Button
                  onClick={handleAddStyle}
                  disabled={addingStyle}
                  className="bg-green-600 hover:bg-green-700 text-white"
                >
                  {addingStyle ? 'Добавление...' : 'Добавить стиль'}
                </Button>
                <Button
                  onClick={clearAddStyleForm}
                  className="border border-gray-300 text-gray-700 hover:bg-gray-50 bg-white"
                >
                  Очистить
                </Button>
              </div>
            </Card>
          )}

          {loading && (
            <div className="text-center py-8">
              <div className="text-gray-600">Загрузка стилей книг...</div>
            </div>
          )}
          
          {!loading && bookStyles.length === 0 && (
            <div className="text-center py-8">
              <div className="text-gray-600">Стили книг не найдены</div>
              <div className="text-sm text-gray-500 mt-2">
                Добавьте первый стиль с помощью кнопки "Добавить стиль книги" выше
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="styles-container">
            {!loading && bookStyles.map((style) => (
              <Card key={style.id} className="p-4">
                <div className="mb-3">
                  <img
                    src={`/styles/${style.filename}`}
                    alt={style.name}
                    className="w-full h-48 object-cover rounded"
                    onError={(e) => {
                      e.currentTarget.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200' viewBox='0 0 200 200'%3E%3Crect width='200' height='200' fill='%23f3f4f6'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%236b7280'%3EСтиль не найден%3C/text%3E%3C/svg%3E";
                    }}
                  />
                </div>
                
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">{style.name}</span>
                    <span className="text-xs text-gray-500">
                      {style.category}
                    </span>
                  </div>
                  
                  <div className="text-sm text-gray-600">
                    {style.description}
                  </div>

                  <div className="flex space-x-2 mt-3">
                    <Button
                      onClick={() => {
                        setSelectedStyle(style);
                        setShowStyleModal(true);
                      }}
                      className="text-xs"
                    >
                      Просмотр
                    </Button>
                    <Button
                      onClick={() => startEditStyle(style)}
                      className="text-xs bg-yellow-500 hover:bg-yellow-600 text-white"
                    >
                      Редактировать
                    </Button>
                    {userPermissions?.is_super_admin && (
                    <Button
                      onClick={() => deleteStyle(style)}
                      className="text-xs bg-red-500 hover:bg-red-600 text-white"
                    >
                      Удалить
                    </Button>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>

          {bookStyles.length === 0 && (
            <div className="text-center text-gray-500 mt-8">
              Нет доступных стилей книг
            </div>
          )}
        </div>
      )}

      {/* Вкладка "Стили голоса" */}
      {activeTab === 'voices' && (
        <div>
          <div className="mb-4">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Примеры стилей голоса</h2>
              {userPermissions?.is_super_admin && (
                <Button
                  onClick={() => setShowAddVoiceForm(!showAddVoiceForm)}
                  className="bg-green-600 hover:bg-green-700 text-white"
                >
                  {showAddVoiceForm ? 'Отмена' : '➕ Добавить голос'}
                </Button>
              )}
            </div>
            <p className="text-gray-600 mb-4">
              Стили голоса, которые будут показываться пользователям при выборе исполнителя песни
            </p>
          </div>

          {/* Форма добавления голоса для главного админа */}
          {showAddVoiceForm && userPermissions?.is_super_admin && (
            <Card className="p-6 mb-6 bg-gray-50">
              <h3 className="text-lg font-semibold mb-4">Добавить новый стиль голоса</h3>
              
              {addVoiceError && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                  {addVoiceError}
                </div>
              )}
              
              {addVoiceSuccess && (
                <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
                  {addVoiceSuccess}
                </div>
              )}

              <div className="space-y-4 mb-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Пол</label>
                  <select
                    value={newVoice.gender}
                    onChange={(e) => setNewVoice({ ...newVoice, gender: e.target.value })}
                    className="w-full border border-gray-300 rounded px-3 py-2"
                  >
                    <option value="male">Мужской</option>
                    <option value="female">Женский</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-2">Эмоциональная окраска</label>
                  <select
                    value={newVoice.category}
                    onChange={(e) => setNewVoice({ ...newVoice, category: e.target.value })}
                    className="w-full border border-gray-300 rounded px-3 py-2"
                  >
                    <option value="gentle">Нежный / романтичный</option>
                    <option value="bright">Яркий / позитивный</option>
                    <option value="artist">На усмотрение артиста</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-2">Пример голоса (аудио)</label>
                  <Input
                    type="file"
                    accept="audio/*"
                    onChange={(e) => setNewVoice({ ...newVoice, file: e.target.files?.[0] || null })}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Загрузите аудиофайл с примером голоса (MP3, WAV, OGG)
                  </p>
                </div>
              </div>

              <div className="flex space-x-3">
                <Button
                  onClick={handleAddVoice}
                  disabled={addingVoice}
                  className="bg-green-600 hover:bg-green-700 text-white"
                >
                  {addingVoice ? 'Добавление...' : 'Добавить голос'}
                </Button>
                <Button
                  onClick={clearAddVoiceForm}
                  className="border border-gray-300 text-gray-700 hover:bg-gray-50 bg-white"
                >
                  Очистить
                </Button>
              </div>
            </Card>
          )}

          {/* Форма редактирования голоса */}
          {showEditVoiceForm && editingVoice && userPermissions?.is_super_admin && (
            <Card className="p-6 mb-6 bg-gray-50">
              <h3 className="text-lg font-semibold mb-4">Редактировать голос</h3>
              
              {addVoiceError && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                  {addVoiceError}
                </div>
              )}
              
              {addVoiceSuccess && (
                <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
                  {addVoiceSuccess}
                </div>
              )}

              <div className="space-y-4 mb-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Пол</label>
                  <select
                    value={editingVoiceData.gender}
                    onChange={(e) => setEditingVoiceData({ ...editingVoiceData, gender: e.target.value })}
                    className="w-full border border-gray-300 rounded px-3 py-2"
                  >
                    <option value="male">Мужской</option>
                    <option value="female">Женский</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-2">Новый пример голоса (аудио)</label>
                  <Input
                    type="file"
                    accept="audio/*"
                    onChange={(e) => setEditingVoiceData({ ...editingVoiceData, file: e.target.files?.[0] || null })}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Оставьте пустым, чтобы сохранить текущий файл
                  </p>
                </div>
              </div>

              <div className="flex space-x-3">
                <Button
                  onClick={saveEditVoice}
                  disabled={editingVoiceLoading}
                  className="bg-yellow-600 hover:bg-yellow-700 text-white"
                >
                  {editingVoiceLoading ? 'Сохранение...' : 'Сохранить'}
                </Button>
                <Button
                  onClick={cancelEditVoice}
                  className="border border-gray-300 text-gray-700 hover:bg-gray-50 bg-white"
                >
                  Отмена
                </Button>
              </div>
            </Card>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {voiceStyles.map((voice) => (
              <Card key={voice.id} className="p-4">
                <div className="mb-3">
                  <div className="w-full h-48 bg-gray-200 rounded flex items-center justify-center">
                    <span className="text-gray-500 text-lg">🎤</span>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <div className="flex justify-center">
                    <span className="text-lg font-medium">
                      {voice.gender === 'male' ? 'Мужской' : 'Женский'}
                    </span>
                  </div>
                  
                  <div className="flex justify-center">
                    <span className="text-sm text-gray-600">
                      {voice.category === 'gentle' ? 'Нежный / романтичный' :
                       voice.category === 'bright' ? 'Яркий / позитивный' :
                       voice.category === 'artist' ? 'На усмотрение артиста' :
                       voice.category || 'Не указан'}
                    </span>
                  </div>

                  <div className="flex space-x-2 mt-3">
                    <Button
                      onClick={() => {
                        setSelectedVoice(voice);
                        setShowVoiceModal(true);
                      }}
                      className="text-xs"
                    >
                      Прослушать
                    </Button>
                    {userPermissions?.is_super_admin && (
                      <Button
                        onClick={() => startEditVoice(voice)}
                        className="text-xs bg-yellow-500 hover:bg-yellow-600 text-white"
                      >
                        Редактировать
                      </Button>
                    )}
                    {userPermissions?.is_super_admin && (
                      <Button
                        onClick={() => deleteVoice(voice)}
                        className="text-xs bg-red-500 hover:bg-red-600 text-white"
                      >
                        Удалить
                      </Button>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>

          {voiceStyles.length === 0 && (
            <div className="text-center text-gray-500 mt-8">
              Нет доступных стилей голоса
            </div>
          )}
        </div>
      )}

      {/* Модальное окно для просмотра обложки */}
      {showCoverModal && selectedCover && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
          <div className="modal-content bg-gray-900 rounded-lg max-w-4xl w-full">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-semibold text-white">{selectedCover.name}</h3>
              <button 
                onClick={() => setShowCoverModal(false)}
                className="text-gray-400 hover:text-white text-2xl"
              >
                &times;
              </button>
            </div>
            <div className="flex justify-center">
              <img 
                src={`/covers/${selectedCover.filename}`} 
                alt={selectedCover.name}
                className="file-preview-video max-h-[70vh] object-contain"
                onError={(e) => {
                  console.error(`Ошибка загрузки обложки: ${selectedCover.filename}`);
                  e.currentTarget.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200' viewBox='0 0 200 200'%3E%3Crect width='200' height='200' fill='%23f3f4f6'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%236b7280'%3EОбложка не найдена%3C/text%3E%3C/svg%3E";
                }}
              />
            </div>
            <div className="mt-4 text-sm text-gray-300">
              <p><strong>Категория:</strong> {selectedCover.category}</p>
              <p><strong>Файл:</strong> {selectedCover.filename}</p>
              <p><strong>Создано:</strong> {new Date(selectedCover.created_at).toLocaleDateString('ru-RU', { timeZone: 'Europe/Moscow' })}</p>
            </div>
          </div>
        </div>
      )}

      {/* Модальное окно для просмотра стиля */}
      {showStyleModal && selectedStyle && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
          <div className="modal-content bg-gray-900 rounded-lg max-w-4xl w-full">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-semibold text-white">{selectedStyle.name}</h3>
              <button 
                onClick={() => setShowStyleModal(false)}
                className="text-gray-400 hover:text-white text-2xl"
              >
                &times;
              </button>
            </div>
            <div className="flex justify-center">
              <img 
                src={`/styles/${selectedStyle.filename}`} 
                alt={selectedStyle.name}
                className="file-preview-video max-h-[70vh] object-contain"
                onError={(e) => {
                  console.error(`Ошибка загрузки стиля: ${selectedStyle.filename}`);
                  e.currentTarget.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200' viewBox='0 0 200 200'%3E%3Crect width='200' height='200' fill='%23f3f4f6'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%236b7280'%3EСтиль не найден%3C/text%3E%3C/svg%3E";
                }}
              />
            </div>
            <div className="mt-4 text-sm text-gray-300">
              <p><strong>Описание:</strong> {selectedStyle.description}</p>
              <p><strong>Категория:</strong> {selectedStyle.category}</p>
              <p><strong>Файл:</strong> {selectedStyle.filename}</p>
              <p><strong>Создано:</strong> {new Date(selectedStyle.created_at).toLocaleDateString('ru-RU', { timeZone: 'Europe/Moscow' })}</p>
            </div>
          </div>
        </div>
      )}

      {/* Модальное окно для воспроизведения голоса */}
      {showVoiceModal && selectedVoice && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
          <div className="modal-content bg-gray-900 rounded-lg max-w-2xl w-full">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-semibold text-white">
                Пример голоса: {selectedVoice.name}
              </h3>
              <button 
                onClick={() => setShowVoiceModal(false)}
                className="text-gray-400 hover:text-white text-2xl"
              >
                &times;
              </button>
            </div>
            <div className="flex flex-col items-center space-y-4">
              <div className="w-full">
                <audio 
                  controls 
                  className="w-full"
                  src={`/voices/${selectedVoice.filename}`}
                  onError={(e) => {
                    console.error(`Ошибка загрузки аудио: ${selectedVoice.filename}`);
                  }}
                >
                  Ваш браузер не поддерживает воспроизведение аудио.
                </audio>
              </div>
              <div className="text-sm text-gray-300 text-center">
                <p><strong>Пол:</strong> {selectedVoice.gender === 'male' ? 'Мужской' : 'Женский'}</p>
                <p><strong>Стиль:</strong> {selectedVoice.category === 'gentle' ? 'Нежный / романтичный' :
                   selectedVoice.category === 'bright' ? 'Яркий / позитивный' :
                   selectedVoice.category === 'artist' ? 'На усмотрение артиста' :
                   selectedVoice.category || 'Не указан'}</p>
                <p><strong>Описание:</strong> {selectedVoice.description}</p>
                <p><strong>Файл:</strong> {selectedVoice.filename}</p>
                <p><strong>Создано:</strong> {new Date(selectedVoice.created_at).toLocaleDateString('ru-RU', { timeZone: 'Europe/Moscow' })}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Модальное окно редактирования стиля */}
      {showEditStyleForm && editingStyle && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-6 border-b">
              <h3 className="text-lg font-semibold text-gray-900">
                ✏️ Редактировать стиль
              </h3>
              <button 
                onClick={cancelEditStyle}
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >
                &times;
              </button>
            </div>
            
            <div className="p-6">
              {addStyleError && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                  {addStyleError}
                </div>
              )}
              
              {addStyleSuccess && (
                <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
                  {addStyleSuccess}
                </div>
              )}

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2 text-gray-700">
                    Название стиля
                  </label>
                  <Input
                    type="text"
                    value={editingStyleData.name}
                    onChange={(e) => setEditingStyleData({ ...editingStyleData, name: e.target.value })}
                    placeholder="Введите название стиля"
                    className="w-full"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-2 text-gray-700">
                    Описание стиля
                  </label>
                  <textarea
                    value={editingStyleData.description}
                    onChange={(e) => setEditingStyleData({ ...editingStyleData, description: e.target.value })}
                    placeholder="Описание стиля..."
                    className="w-full border border-gray-300 rounded px-3 py-2 h-24 resize-none"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-2 text-gray-700">
                    Новая фотография (необязательно)
                  </label>
                  <Input
                    type="file"
                    accept="image/*"
                    onChange={(e) => setEditingStyleData({ ...editingStyleData, file: e.target.files?.[0] || null })}
                    className="w-full"
                  />
                  <p className="text-sm text-gray-500 mt-1">
                    Оставьте пустым, чтобы сохранить текущую фотографию
                  </p>
                </div>
              </div>
            </div>
            
            <div className="flex space-x-3 p-6 border-t">
              <Button
                onClick={saveEditStyle}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
              >
                💾 Сохранить изменения
              </Button>
              <Button
                onClick={cancelEditStyle}
                className="flex-1 border border-gray-300 text-gray-700 hover:bg-gray-50 bg-white"
              >
                ❌ Отмена
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export { PhotosPage };
export default PhotosPage;