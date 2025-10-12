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

export const PhotosPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'orders' | 'covers' | 'styles'>('orders');
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [coverTemplates, setCoverTemplates] = useState<CoverTemplate[]>([]);
  const [bookStyles, setBookStyles] = useState<BookStyle[]>([]);
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
    name: '',
    description: '',
    category: '',
    file: null as File | null
  });
  const [addingStyle, setAddingStyle] = useState(false);
  const [addStyleError, setAddStyleError] = useState('');
  const [addStyleSuccess, setAddStyleSuccess] = useState('');

  useEffect(() => {
    fetchUserPermissions();
    fetchPhotos();
    fetchOrders();
    fetchCoverTemplates();
    fetchBookStyles();
  }, []);

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
      console.error("Ошибка загрузки прав доступа:", err);
    }
  };

  const fetchPhotos = async () => {
    try {
      const token = localStorage.getItem("token");
      if (!token) {
        setError("Токен авторизации не найден");
        return;
      }
      
      const response = await fetch("/admin/photos", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
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
      } else {
        setError("Ошибка загрузки фотографий");
      }
    } catch (err) {
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
      const response = await fetch("/admin/book-styles", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setBookStyles(data);
      }
    } catch (err) {
      console.error("Ошибка загрузки стилей книг:", err);
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
    if (!newStyle.name || !newStyle.description || !newStyle.category || !newStyle.file) {
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
      formData.append('category', newStyle.category);
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
        setNewStyle({ name: '', description: '', category: '', file: null });
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
    setNewStyle({ name: '', description: '', category: '', file: null });
    setAddStyleError('');
    setShowAddStyleForm(false);
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

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-4">Управление фотографиями</h1>
        
        {/* Переключатель вкладок */}
        <div className="flex space-x-4 mb-6">
          <button
            onClick={() => setActiveTab('orders')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'orders'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            📸 Фотографии по заказам
          </button>
          <button
            onClick={() => setActiveTab('covers')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'covers'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            📚 Библиотека обложек
          </button>
          <button
            onClick={() => setActiveTab('styles')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'styles'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            🎨 Стили книг
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

          {/* Группированные фотографии по заказам */}
          {selectedOrder ? (
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
                          {new Date(photo.created_at).toLocaleDateString()}
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
                          onClick={() => {
                            const link = document.createElement('a');
                            link.href = `/${photo.path}`;
                            link.download = photo.filename;
                            link.click();
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
                        <div>Создан: {new Date(orderInfo?.created_at || '').toLocaleDateString()}</div>
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
                    className="w-full h-48 object-cover rounded"
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
                      onClick={() => window.open(`/covers/${template.filename}`, '_blank')}
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
              {userPermissions?.is_super_admin && (
                <Button
                  onClick={() => setShowAddStyleForm(!showAddStyleForm)}
                  className="bg-green-600 hover:bg-green-700 text-white"
                >
                  {showAddStyleForm ? 'Отмена' : '➕ Добавить стиль'}
                </Button>
              )}
            </div>
            <p className="text-gray-600 mb-4">
              Примеры стилей книг, которые будут показываться пользователям перед выбором
            </p>
          </div>

          {/* Форма добавления стиля для главного админа */}
          {showAddStyleForm && userPermissions?.is_super_admin && (
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

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Название стиля</label>
                  <Input
                    type="text"
                    value={newStyle.name}
                    onChange={(e) => setNewStyle({ ...newStyle, name: e.target.value })}
                    placeholder="Введите название стиля"
                    className="w-full"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-2">Категория</label>
                  <Input
                    type="text"
                    value={newStyle.category}
                    onChange={(e) => setNewStyle({ ...newStyle, category: e.target.value })}
                    placeholder="Например: Романтика, Детектив, Фантастика"
                    className="w-full"
                  />
                </div>
                
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium mb-2">Описание стиля</label>
                  <textarea
                    value={newStyle.description}
                    onChange={(e) => setNewStyle({ ...newStyle, description: e.target.value })}
                    placeholder="Опишите особенности стиля, настроение, жанр..."
                    className="w-full border border-gray-300 rounded px-3 py-2 h-24"
                  />
                </div>
                
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium mb-2">Пример изображения</label>
                  <Input
                    type="file"
                    accept="image/*"
                    onChange={(e) => setNewStyle({ ...newStyle, file: e.target.files?.[0] || null })}
                    className="w-full"
                  />
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

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {bookStyles.map((style) => (
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
                      onClick={() => window.open(`/styles/${style.filename}`, '_blank')}
                      className="text-xs"
                    >
                      Просмотр
                    </Button>
                    <Button
                      onClick={() => {
                        // TODO: Добавить логику выбора заказа и добавления стиля
                        alert('Функция добавления стиля в заказ будет реализована позже');
                      }}
                      className="text-xs bg-green-500 hover:bg-green-600 text-white"
                    >
                      Добавить в заказ
                    </Button>
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
    </div>
  );
}; 