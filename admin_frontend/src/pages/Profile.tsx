import React, { useState, useEffect } from "react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { translateStatus } from "../utils/statusTranslations";
import { useNavigate } from "react-router-dom";
import { validateEmail, cleanEmail, ValidationResult } from "../utils/validation";

interface ManagerProfile {
  id: number;
  email: string;
  full_name: string;
}

interface ManagerOrder {
  id: number;
  user_id: number;
  status: string;
  order_data: string;
  pdf_path?: string;
  mp3_path?: string;
  assigned_manager_id?: number;
  manager_email?: string;
  manager_name?: string;
  created_at: string;
  updated_at: string;
}

export const ProfilePage: React.FC = () => {
  const [profile, setProfile] = useState<ManagerProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState("");
  
  // Состояние для заказов менеджера
  const [orders, setOrders] = useState<ManagerOrder[]>([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [ordersError, setOrdersError] = useState("");
  
  // Функция для парсинга данных заказа
  const parseOrderData = (order_data: string) => {
    try {
      return JSON.parse(order_data);
    } catch {
      return {};
    }
  };
  
  // Форма редактирования
  const [editForm, setEditForm] = useState({
    full_name: "",
    current_password: "",
    new_password: "",
    confirm_password: ""
  });

  const navigate = useNavigate();

  useEffect(() => {
    fetchProfile();
    fetchOrders();
  }, []);

  const fetchProfile = async () => {
    setLoading(true);
    setError("");
    try {
      const token = localStorage.getItem("token");
      const response = await fetch("/admin/profile", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        throw new Error("Ошибка загрузки профиля");
      }
      const data = await response.json();
      setProfile(data);
      setEditForm({
        full_name: data.full_name || "",
        current_password: "",
        new_password: "",
        confirm_password: ""
      });
    } catch (err: any) {
      setError(err.message || "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  };

  const fetchOrders = async () => {
    setOrdersLoading(true);
    setOrdersError("");
    try {
      const token = localStorage.getItem("token");
      const response = await fetch("/admin/profile/orders", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        throw new Error("Ошибка загрузки заказов");
      }
      const data = await response.json();
      setOrders(data);
    } catch (err: any) {
      setOrdersError(err.message || "Ошибка загрузки заказов");
    } finally {
      setOrdersLoading(false);
    }
  };

  const handleEdit = () => {
    setEditing(true);
    setSaveSuccess(false);
    setSaveError("");
  };

  const handleCancel = () => {
    setEditing(false);
    setEditForm({
      full_name: profile?.full_name || "",
      current_password: "",
      new_password: "",
      confirm_password: ""
    });
    setSaveSuccess(false);
    setSaveError("");
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveSuccess(false);
    setSaveError("");

    try {
      // Валидация ФИО
      if (!editForm.full_name.trim()) {
        throw new Error("ФИО обязательно для заполнения");
      }

      // Валидация паролей
      if (editForm.new_password && editForm.new_password !== editForm.confirm_password) {
        throw new Error("Новые пароли не совпадают");
      }

      if (editForm.new_password && !editForm.current_password) {
        throw new Error("Введите текущий пароль для изменения");
      }

      if (editForm.new_password && editForm.new_password.length < 6) {
        throw new Error("Новый пароль должен содержать минимум 6 символов");
      }

      const token = localStorage.getItem("token");
      const response = await fetch("/admin/profile", {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          full_name: editForm.full_name,
          current_password: editForm.current_password || undefined,
          new_password: editForm.new_password || undefined,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Ошибка сохранения");
      }

      const updatedProfile = await response.json();
      setProfile(updatedProfile);
      setEditing(false);
      setSaveSuccess(true);
      
      // Очищаем поля паролей
      setEditForm(prev => ({
        ...prev,
        current_password: "",
        new_password: "",
        confirm_password: ""
      }));
    } catch (err: any) {
      setSaveError(err.message || "Ошибка сохранения");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8">
        <div className="text-white">Загрузка профиля...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="text-red-500 mb-4">{error}</div>
        <Button onClick={fetchProfile}>Повторить</Button>
      </div>
    );
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-6">Личный кабинет</h1>
      
      <div className="bg-gray-900 rounded-lg shadow p-6 max-w-2xl">
        <h2 className="text-xl font-bold mb-4">Профиль менеджера</h2>
        
        {saveSuccess && (
          <div className="text-green-400 mb-4">
            ✅ Профиль успешно обновлен
          </div>
        )}
        
        {saveError && (
          <div className="text-red-400 mb-4">{saveError}</div>
        )}

        <div className="space-y-4">
          {/* Email (только для чтения) */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Email (логин)
            </label>
            <Input
              type="email"
              value={profile?.email || ""}
              disabled
              className="bg-gray-800 text-gray-400"
            />
            <p className="text-xs text-gray-400 mt-1">
              Email нельзя изменить
            </p>
          </div>

          {/* ФИО */}
          <div>
            <label className="block text-sm font-medium mb-2">
              ФИО
            </label>
            {editing ? (
              <form onSubmit={handleSave} className="space-y-4">
                <div className="form-group">
                  <label className="form-label">ФИО:</label>
                  <input
                    type="text"
                    value={editForm.full_name}
                    onChange={(e) => setEditForm({...editForm, full_name: e.target.value})}
                    className="w-full p-3 border border-gray-600 rounded bg-gray-800 text-white"
                    placeholder="Иванов Иван Иванович"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Текущий пароль:</label>
                  <input
                    type="password"
                    value={editForm.current_password}
                    onChange={(e) => setEditForm({...editForm, current_password: e.target.value})}
                    className="w-full p-3 border border-gray-600 rounded bg-gray-800 text-white"
                    placeholder="Введите текущий пароль"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Новый пароль:</label>
                  <input
                    type="password"
                    value={editForm.new_password}
                    onChange={(e) => setEditForm({...editForm, new_password: e.target.value})}
                    className="w-full p-3 border border-gray-600 rounded bg-gray-800 text-white"
                    placeholder="Введите новый пароль"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Подтвердите новый пароль:</label>
                  <input
                    type="password"
                    value={editForm.confirm_password}
                    onChange={(e) => setEditForm({...editForm, confirm_password: e.target.value})}
                    className="w-full p-3 border border-gray-600 rounded bg-gray-800 text-white"
                    placeholder="Повторите новый пароль"
                  />
                </div>
                <div className="flex gap-2">
                  <Button type="submit" disabled={saving} className="btn-medium bg-blue-500 hover:bg-blue-700">
                    {saving ? "Сохранение..." : "Сохранить"}
                  </Button>
                  <Button 
                    type="button" 
                    onClick={() => setEditing(false)}
                    className="btn-medium bg-gray-500 hover:bg-gray-700"
                  >
                    Отмена
                  </Button>
                </div>
              </form>
            ) : (
              <div className="text-white p-3 bg-gray-800 rounded">
                {profile?.full_name || "Не указано"}
              </div>
            )}
          </div>

          {/* Кнопки */}
          <div className="flex space-x-4 pt-4">
            {editing ? (
              <>
                <Button 
                  onClick={handleSave}
                  disabled={saving}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  {saving ? "Сохранение..." : "Сохранить"}
                </Button>
                <Button 
                  onClick={handleCancel}
                  disabled={saving}
                  className="bg-gray-600 hover:bg-gray-700"
                >
                  Отмена
                </Button>
              </>
            ) : (
              <Button 
                onClick={handleEdit}
                className="bg-blue-600 hover:bg-blue-700"
              >
                Редактировать
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Список заказов менеджера */}
      <div className="bg-gray-900 rounded-lg shadow p-6 mt-6">
        <h2 className="text-xl font-bold mb-4">Мои заказы</h2>
        
        {ordersLoading && <div className="text-white">Загрузка заказов...</div>}
        {ordersError && <div className="text-red-500 mb-4">{ordersError}</div>}
        
        {orders.length === 0 && !ordersLoading ? (
          <div className="text-gray-400 text-center py-8">
            У вас пока нет назначенных заказов
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full border text-sm">
              <thead>
                <tr className="table-header">
                  <th className="border px-4 py-2">№ заказа</th>
                  <th className="border px-4 py-2">Username</th>
                  <th className="border px-4 py-2">Тип заказа</th>
                  <th className="border px-4 py-2">Дата создания</th>
                  <th className="border px-4 py-2">Статус</th>
                  <th className="border px-4 py-2">Действия</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => {
                  const parsed = parseOrderData(order.order_data);
                  const type = parsed.product || "-";
                  const username = parsed.username || parsed.user_name || "-";
                  return (
                    <tr key={order.id} className="hover:bg-gray-800">
                      <td className="table-cell">#{order.id.toString().padStart(4, "0")}</td>
                      <td className="table-cell">{username}</td>
                      <td className="table-cell">{type}</td>
                      <td className="table-cell">{order.created_at.slice(0, 10)}</td>
                      <td className="table-cell">{translateStatus(order.status)}</td>
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
        )}
      </div>
    </div>
  );
}; 