import React, { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { translateStatus } from "../utils/statusTranslations";

// Компонент для отображения прогресса в таблице
const OrderProgressBadge: React.FC<{ status: string; product: string }> = ({ status, product }) => {
  const getCurrentStep = () => {
    // Если доплата получена, показываем этап доплаты
    if (status === "upsell_paid") {
      return product === "Песня" ? 7 : 7;
    }
    
    // Если заказ завершен, возвращаем последний шаг
    if (status === "completed" || status === "delivered" || status === "final_sent" || status === "ready") {
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
        "pages_selected": 4,
        "waiting_story_options": 4,
        "waiting_story_choice": 4,
        "story_selected": 4,
        "story_options_sent": 4,
        "covers_sent": 5,
        "waiting_cover_choice": 5,
        "cover_selected": 5,
        "waiting_draft": 6,
        "draft_sent": 6,
        "editing": 6,
        "upsell_payment_created": 7,
        "upsell_payment_pending": 7,
        "upsell_paid": 7,
        "waiting_final": 8,
        "ready": 8,
        "delivered": 9,
        "final_sent": 9,
        "completed": 9,
      };
      return bookStepMap[status] || 1;
    }
  };

  const getStepTitle = (step: number, product: string) => {
    if (product === "Песня") {
      const songSteps = [
        "Создание заказа",
        "Демо-версия",
        "Оплата",
        "Сбор фактов",
        "Предфинальная",
        "Правки",
        "Финальная"
      ];
      return songSteps[step - 1] || "Неизвестно";
    } else {
      const bookSteps = [
        "Создание заказа",
        "Демо-контент",
        "Оплата",
        "Выбор сюжетов",
        "Выбор обложки",
        "Черновик",
        "Доплата",
        "Финальная",
        "Завершение"
      ];
      return bookSteps[step - 1] || "Неизвестно";
    }
  };

  const currentStep = getCurrentStep();
  const totalSteps = product === "Песня" ? 7 : 9;
  const percentage = Math.round((currentStep / totalSteps) * 100);
  const stepTitle = getStepTitle(currentStep, product);

  // Проверяем, завершен ли заказ
  const isCompleted = status === "completed" || status === "delivered" || status === "final_sent";



  return (
    <div className="flex items-center gap-1" key={`${status}-${product}-${isCompleted}`}>
      <div className="text-xs font-bold text-blue-400">
        {isCompleted ? "Готов" : `Гл.${currentStep}`}
      </div>
      <div className="w-12 h-1.5 bg-gray-600 rounded-full overflow-hidden">
        <div 
          className={`h-full transition-all duration-300 ${
            isCompleted 
              ? "bg-gradient-to-r from-green-500 to-green-600" 
              : "bg-gradient-to-r from-blue-500 to-green-500"
          }`}
          style={{ width: `${isCompleted ? 100 : percentage}%` }}
        />
      </div>
      <div className="text-xs text-gray-400">
        {isCompleted ? "100%" : `${percentage}%`}
      </div>
    </div>
  );
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
  assigned_manager_id?: number;
  manager_email?: string;
  manager_name?: string;
  username?: string;
  created_at: string;
  updated_at: string;
  notification_id?: number;
  notification_is_read?: boolean;
  notification_last_message_at?: string;
}

function parseOrderData(order_data: string) {
  try {
    return JSON.parse(order_data);
  } catch {
    return {};
  }
}

// Функция для определения, является ли заказ новым (создан в течение последних 24 часов)
function isNewOrder(createdAt: string): boolean {
  const now = new Date();
  const created = new Date(createdAt);
  
  // Учитываем разницу в часовых поясах
  const nowMSK = new Date(now.toLocaleString("en-US", {timeZone: "Europe/Moscow"}));
  const createdMSK = new Date(created.toLocaleString("en-US", {timeZone: "Europe/Moscow"}));
  
  const diffInHours = (nowMSK.getTime() - createdMSK.getTime()) / (1000 * 60 * 60);
  return diffInHours <= 24;
}

const statusOrder = ["Создание", "Ожидание оплаты", "Оплачен", "Отправлен"];

export const OrdersPage: React.FC = () => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [telegramIdFilter, setTelegramIdFilter] = useState("");
  const [orderIdFilter, setOrderIdFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [newOnlyFilter, setNewOnlyFilter] = useState(false);
  const [sortField, setSortField] = useState<"created_at" | "status" | "progress">("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  
  // Состояние для пагинации
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalOrders, setTotalOrders] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [userPermissions, setUserPermissions] = useState<{is_super_admin: boolean} | null>(null);
  
  // Состояние для отслеживания активного поиска
  const [isSearchActive, setIsSearchActive] = useState(false);
  const navigate = useNavigate();

  // Функция для поиска заказов через API
  const searchOrders = async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      
      // Добавляем параметры поиска только если они заполнены
      if (telegramIdFilter.trim()) {
        params.append('telegram_id', telegramIdFilter.trim());
      }
      if (orderIdFilter.trim()) {
        params.append('order_id', orderIdFilter.trim());
      }
      if (statusFilter) {
        params.append('status', statusFilter);
      }
      if (typeFilter) {
        params.append('order_type', typeFilter);
      }
      
      // Добавляем параметры сортировки
      params.append('sort_by', sortField);
      params.append('sort_dir', sortDir);
      
      const response = await fetch(`/orders/filtered?${params}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });
      
      if (response.status === 401) {
        localStorage.removeItem("token");
        window.location.href = "/admin/login";
        return;
      }
      
      if (!response.ok) {
        throw new Error("Ошибка поиска заказов");
      }
      
      const data = await response.json();
      setOrders(data);
      
      // При поиске показываем все результаты без пагинации
      setTotalOrders(data.length);
      setTotalPages(1);
      setCurrentPage(1);
      setIsSearchActive(true);
      
    } catch (err: any) {
      setError(err.message || "Ошибка поиска");
    } finally {
      setLoading(false);
    }
  };

  // Функция для сброса поиска и возврата к обычному режиму
  const resetSearch = () => {
    setTelegramIdFilter("");
    setOrderIdFilter("");
    setStatusFilter("");
    setTypeFilter("");
    setIsSearchActive(false);
    setCurrentPage(1);
  };

  useEffect(() => {
    // Получаем права доступа пользователя
    const fetchUserPermissions = async () => {
      try {
        const token = localStorage.getItem("token");
        const response = await fetch("/admin/profile/permissions", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        
        if (response.status === 401) {
          localStorage.removeItem("token");
          window.location.href = "/admin/login";
          return;
        }
        
        if (response.ok) {
          const data = await response.json();
          setUserPermissions(data);
        }
      } catch (err) {
        console.error("Ошибка получения прав доступа:", err);
      }
    };

    let interval: NodeJS.Timeout;
    const fetchOrder = async (isInitial = false) => {
      // Если активен поиск, не обновляем данные автоматически
      if (isSearchActive) {
        return;
      }
      
      if (isInitial) setLoading(true);
      setError("");
      try {
        const params = new URLSearchParams({
          page: currentPage.toString(),
          limit: pageSize.toString()
        });
        
        const response = await fetch(`/admin/orders?${params}`, {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        });
        
        if (response.status === 401) {
          localStorage.removeItem("token");
          window.location.href = "/admin/login";
          return;
        }
        
        if (!response.ok) {
          throw new Error("Ошибка загрузки заказов");
        }
        const data = await response.json();
        setOrders(data);
        
        // Обновляем информацию о пагинации
        const totalCount = response.headers.get('X-Total-Count');
        if (totalCount) {
          setTotalOrders(parseInt(totalCount));
          setTotalPages(Math.ceil(parseInt(totalCount) / pageSize));
        }
      } catch (err: any) {
        setError(err.message || "Ошибка загрузки");
      } finally {
        if (isInitial) setLoading(false);
      }
    };
    
    fetchUserPermissions();
    fetchOrder(true); // первый раз с лоадером
    interval = setInterval(() => {
      console.log("🔄 Автообновление списка заказов...");
      fetchOrder(false);
    }, 5000); // далее без лоадера
    
    // Обновляем данные при фокусе на странице (например, при возврате с другой страницы)
    const handleFocus = () => {
      fetchOrder(false);
    };
    
    // Обновляем данные при возврате на вкладку
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        fetchOrder(false);
      }
    };
    
    // Обновляем данные при навигации (возврат с деталей заказа)
    const handlePopState = () => {
      fetchOrder(false);
    };
    
    window.addEventListener('focus', handleFocus);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('popstate', handlePopState);
    
    return () => {
      clearInterval(interval);
      window.removeEventListener('focus', handleFocus);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('popstate', handlePopState);
    };
  }, [currentPage, pageSize, isSearchActive]);

  const handleRefresh = async () => {
    // Если активен поиск, обновляем результаты поиска
    if (isSearchActive) {
      await searchOrders();
      return;
    }
    
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        limit: pageSize.toString()
      });
      
      const response = await fetch(`/admin/orders?${params}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });
      
      if (response.status === 401) {
        localStorage.removeItem("token");
        window.location.href = "/admin/login";
        return;
      }
      
      if (!response.ok) {
        throw new Error("Ошибка загрузки заказов");
      }
      const data = await response.json();
      setOrders(data);
      
      // Обновляем информацию о пагинации
      const totalCount = response.headers.get('X-Total-Count');
      if (totalCount) {
        setTotalOrders(parseInt(totalCount));
        setTotalPages(Math.ceil(parseInt(totalCount) / pageSize));
      }
    } catch (err: any) {
      setError(err.message || "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  };

  const handleAssignManagers = async () => {
    try {
      const response = await fetch("/admin/orders/assign-managers-all", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
          "Content-Type": "application/json",
        },
      });
      
      if (response.status === 401) {
        localStorage.removeItem("token");
        window.location.href = "/admin/login";
        return;
      }
      
      if (response.ok) {
        const result = await response.json();
        alert(`✅ ${result.message}`);
        handleRefresh(); // Обновляем список заказов
      } else {
        const error = await response.json();
        alert(`❌ Ошибка: ${error.detail}`);
      }
    } catch (error) {
      console.error("Ошибка назначения менеджеров:", error);
      alert("❌ Ошибка при назначении менеджеров");
    }
  };

  const filteredOrders = useMemo(() => {
    // Если активен поиск, возвращаем заказы как есть (они уже отфильтрованы на сервере)
    if (isSearchActive) {
      return orders.filter((order) => {
        // Применяем только фильтр "только новые" для результатов поиска
        const newOnlyMatch = newOnlyFilter ? isNewOrder(order.created_at) : true;
        return newOnlyMatch;
      });
    }
    
    // Обычная локальная фильтрация для режима просмотра всех заказов
    return orders
      .filter((order) => {
        const parsed = parseOrderData(order.order_data);
        const type = parsed.product || "";
        const telegramId = order.telegram_id || order.user_id || "";
        const idMatch = orderIdFilter ? order.id.toString().includes(orderIdFilter) : true;
        const typeMatch = typeFilter ? type === typeFilter : true;
        const telegramIdMatch = telegramIdFilter ? telegramId.toString().includes(telegramIdFilter) : true;
        const statusMatch = statusFilter ? order.status === statusFilter : true;
        const newOnlyMatch = newOnlyFilter ? isNewOrder(order.created_at) : true;
        return idMatch && typeMatch && telegramIdMatch && statusMatch && newOnlyMatch;
      })
      .sort((a, b) => {
        if (sortField === "created_at") {
          const cmp = a.created_at.localeCompare(b.created_at);
          return sortDir === "asc" ? cmp : -cmp;
        } else if (sortField === "status") {
          const idxA = statusOrder.indexOf(a.status);
          const idxB = statusOrder.indexOf(b.status);
          return sortDir === "asc" ? idxA - idxB : idxB - idxA;
        } else if (sortField === "progress") {
          const getProgress = (order: Order) => {
            const parsed = parseOrderData(order.order_data);
            const product = parsed.product || "Книга";
            
            // Если заказ завершен, возвращаем последний шаг
            if (order.status === "completed" || order.status === "delivered" || order.status === "final_sent" || order.status === "ready" || order.status === "upsell_paid") {
              return product === "Песня" ? 7 : 8;
            }
            
            const stepMap: { [key: string]: number } = {
              "created": 1,
              "waiting_manager": 2,
              "demo_content": 2,
              "demo_sent": 2,
              "waiting_payment": 3,
              "payment_pending": 3,
              "paid": 3,
              "waiting_story_choice": 4,
              "story_selected": 4,
              "story_options_sent": 4,
              "pages_selected": 4,
              "covers_sent": 5,
              "waiting_cover_choice": 5,
              "cover_selected": 5,
              "waiting_draft": 6,
              "draft_sent": 6,
              "editing": 6,
              "waiting_final": 7,
              "upsell_paid": 7,
              "ready": 7,
              "final_sent": 8,
              "delivered": 8,
              "completed": 8
            };
            return stepMap[order.status] || 1;
          };
          
          const progressA = getProgress(a);
          const progressB = getProgress(b);
          return sortDir === "asc" ? progressA - progressB : progressB - progressA;
        }
        return 0;
      });
  }, [orders, typeFilter, telegramIdFilter, orderIdFilter, statusFilter, newOnlyFilter, sortField, sortDir, isSearchActive]);

  const orderTypes = Array.from(new Set(orders.map(o => parseOrderData(o.order_data).product).filter(Boolean)));
  const orderStatuses = Array.from(new Set(orders.map(o => o.status).filter(Boolean)));

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold">
            {userPermissions?.is_super_admin ? "Все заказы" : "Мои заказы"}
          </h1>
          <div className="text-xs text-gray-500">Автообновление каждые 5 сек</div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-1 px-3 rounded disabled:opacity-50 text-sm"
          >
            {loading ? "Обновление..." : "Обновить"}
          </button>
          {userPermissions?.is_super_admin && (
            <button
              onClick={handleAssignManagers}
              disabled={loading}
              className="bg-green-500 hover:bg-green-700 text-white font-bold py-1 px-3 rounded disabled:opacity-50 text-sm"
            >
              Назначить менеджеров
            </button>
          )}
        </div>
      </div>
      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="text"
          placeholder="Поиск по номеру заказа"
          className="filter-input border rounded bg-gray-800 text-white"
          value={orderIdFilter}
          onChange={e => setOrderIdFilter(e.target.value)}
        />
        <input
          type="text"
          placeholder="Поиск по Telegram ID"
          className="filter-input border rounded bg-gray-800 text-white"
          value={telegramIdFilter}
          onChange={e => setTelegramIdFilter(e.target.value)}
        />
        <select
          className="filter-input border rounded bg-gray-800 text-white"
          value={typeFilter}
          onChange={e => setTypeFilter(e.target.value)}
        >
          <option value="">Все типы</option>
          {orderTypes.map(type => (
            <option key={type} value={type}>{type}</option>
          ))}
        </select>
        <select
          className="filter-input border rounded bg-gray-800 text-white"
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
        >
          <option value="">Все статусы</option>
          {orderStatuses.map(status => (
            <option key={status} value={status}>{translateStatus(status)}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={newOnlyFilter}
            onChange={e => setNewOnlyFilter(e.target.checked)}
            className="rounded"
          />
          <span className="text-blue-400 font-medium">Только новые (24ч)</span>
        </label>
        <select
          className="filter-input border rounded bg-gray-800 text-white"
          value={sortField}
          onChange={e => setSortField(e.target.value as any)}
        >
          <option value="created_at">Сортировать по дате</option>
          <option value="status">Сортировать по статусу</option>
          <option value="progress">Сортировать по прогрессу</option>
        </select>
        <select
          className="filter-input border rounded bg-gray-800 text-white"
          value={sortDir}
          onChange={e => setSortDir(e.target.value as any)}
        >
          <option value="desc">По убыванию</option>
          <option value="asc">По возрастанию</option>
        </select>
        
        {/* Кнопки поиска и сброса */}
        <button
          onClick={searchOrders}
          disabled={loading || (!telegramIdFilter.trim() && !orderIdFilter.trim() && !statusFilter && !typeFilter)}
          className="bg-green-500 hover:bg-green-700 text-white font-bold py-1 px-3 rounded disabled:opacity-50 text-sm"
        >
          🔍 Поиск
        </button>
        
        {isSearchActive && (
          <button
            onClick={resetSearch}
            className="bg-gray-500 hover:bg-gray-700 text-white font-bold py-1 px-3 rounded text-sm"
          >
            ❌ Сбросить поиск
          </button>
        )}
      </div>
      {loading && <div>Загрузка...</div>}
      {error && <div className="text-red-500 mb-4">{error}</div>}
      <div className="overflow-x-auto">
        <table className="min-w-full border text-sm">
          <thead>
            <tr className="table-header">
              <th className="border px-4 py-2">№ заказа</th>
              <th className="border px-4 py-2">Username</th>
              <th className="border px-4 py-2">Telegram ID</th>
              <th className="border px-4 py-2">Тип заказа</th>
              {userPermissions?.is_super_admin && (
                <th className="border px-4 py-2">Менеджер</th>
              )}
              <th className="border px-4 py-2">Дата создания</th>
              <th className="border px-4 py-2">Статус</th>
              <th className="border px-4 py-2">Прогресс</th>
              <th className="border px-4 py-2">Уведомления</th>
              <th className="border px-4 py-2">Детали</th>
            </tr>
          </thead>
          <tbody>
            {filteredOrders.map((order) => {
              const parsed = parseOrderData(order.order_data);
              const type = parsed.product || "-";
              const telegramId = order.telegram_id || order.user_id || "-";
              // Username для связи с пользователем
              const username = order.username || parsed.username || parsed.user_name || "-";
              const managerName = order.manager_name || order.manager_email || "Не назначен";
              const isNew = isNewOrder(order.created_at);
              return (
                <tr key={order.id} className={`hover:bg-gray-800 ${isNew ? 'bg-blue-900/20 border-l-4 border-l-blue-500' : ''}`}>
                  <td className="table-cell">
                    <div className="flex items-center gap-2">
                      #{order.id.toString().padStart(4, "0")}
                      {isNew && (
                        <span className="bg-blue-500 text-white text-xs px-2 py-1 rounded-full font-bold">
                          НОВЫЙ
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="table-cell">{username}</td>
                  <td className="table-cell">{telegramId}</td>
                  <td className="table-cell">{type}</td>
                  {userPermissions?.is_super_admin && (
                    <td className="table-cell">{managerName}</td>
                  )}
                  <td className="table-cell">{new Date(order.created_at).toLocaleDateString('ru-RU', { timeZone: 'Europe/Moscow' })}</td>
                  <td className="table-cell">{translateStatus(order.status)}</td>
                  <td className="table-cell">
                    <OrderProgressBadge status={order.status} product={type} />
                  </td>
                  <td className="table-cell">
                    {order.notification_id && !order.notification_is_read ? (
                      <div className="inline-block px-2 py-1 text-white text-xs font-bold rounded border-2 bg-orange-500 border-orange-400">
                        Пользователь написал сообщение
                      </div>
                    ) : (
                      <span className="text-gray-700 text-xs">
                        Пользователь написал сообщение
                      </span>
                    )}
                  </td>
                  <td className="table-cell">
                    <button
                      onClick={() => navigate(`/admin/orders/${order.id}`)}
                      className="btn-small bg-blue-500 hover:bg-blue-700 text-white font-bold rounded"
                    >
                      Детали
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      
      {/* Информация о результатах поиска */}
      {isSearchActive && (
        <div className="mt-4 px-4">
          <div className="text-sm text-green-600 bg-green-100 p-2 rounded">
            🔍 Результаты поиска: найдено {filteredOrders.length} заказ(ов)
            {telegramIdFilter && ` по Telegram ID: ${telegramIdFilter}`}
            {orderIdFilter && ` по номеру заказа: ${orderIdFilter}`}
            {statusFilter && ` со статусом: ${translateStatus(statusFilter)}`}
            {typeFilter && ` типа: ${typeFilter}`}
          </div>
        </div>
      )}
      
      {/* Компонент пагинации */}
      {totalPages > 1 && !isSearchActive && (
        <div className="flex justify-between items-center mt-4 px-4">
          <div className="text-sm text-gray-600">
            Показано {((currentPage - 1) * pageSize) + 1}-{Math.min(currentPage * pageSize, totalOrders)} из {totalOrders} заказов
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setCurrentPage(1)}
              disabled={currentPage === 1}
              className="px-3 py-1 text-sm border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
            >
              Первая
            </button>
            
            <button
              onClick={() => setCurrentPage(currentPage - 1)}
              disabled={currentPage === 1}
              className="px-3 py-1 text-sm border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
            >
              Предыдущая
            </button>
            
            <span className="px-3 py-1 text-sm">
              Страница {currentPage} из {totalPages}
            </span>
            
            <button
              onClick={() => setCurrentPage(currentPage + 1)}
              disabled={currentPage === totalPages}
              className="px-3 py-1 text-sm border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
            >
              Следующая
            </button>
            
            <button
              onClick={() => setCurrentPage(totalPages)}
              disabled={currentPage === totalPages}
              className="px-3 py-1 text-sm border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
            >
              Последняя
            </button>
          </div>
          
          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-600">Заказов на странице:</label>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
              className="px-2 py-1 text-sm border rounded"
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        </div>
      )}
    </div>
  );
};