import React, { useEffect, useState } from "react";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";

interface PricingItem {
  id: number;
  product: string;
  price: number;
  currency: string;
  description: string;
  upgrade_price_difference: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export const PricingPage: React.FC = () => {
  const [pricingItems, setPricingItems] = useState<PricingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingItem, setEditingItem] = useState<PricingItem | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [userPermissions, setUserPermissions] = useState<{is_super_admin: boolean} | null>(null);

  const [newItem, setNewItem] = useState({
    product: "",
    price: "",
    currency: "RUB",
    description: "",
    upgrade_price_difference: "",
    is_active: true
  });

  useEffect(() => {
    fetchPricingItems();
    fetchUserPermissions();
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
      console.error("Ошибка получения прав доступа:", err);
    }
  };

  const fetchPricingItems = async () => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch("/admin/pricing", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setPricingItems(data);
      } else {
        setError("Ошибка загрузки цен");
      }
    } catch (err) {
      setError("Ошибка загрузки цен");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newItem.product || !newItem.price) {
      setError("Заполните все обязательные поля");
      return;
    }

    setCreating(true);
    try {
      const token = localStorage.getItem("token");
      const response = await fetch("/admin/pricing", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          ...newItem,
          price: parseFloat(newItem.price.replace(',', '.')) || 0,
          upgrade_price_difference: parseFloat(newItem.upgrade_price_difference.replace(',', '.')) || 0
        }),
      });

      if (response.ok) {
        setShowCreateForm(false);
        setNewItem({
          product: "",
          price: "",
          currency: "RUB",
          description: "",
          upgrade_price_difference: "",
          is_active: true
        });
        fetchPricingItems();
      } else {
        setError("Ошибка создания цены");
      }
    } catch (err) {
      setError("Ошибка создания цены");
    } finally {
      setCreating(false);
    }
  };

  const handleUpdateItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingItem) return;

    setSaving(true);
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/pricing/${editingItem.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(editingItem),
      });

      if (response.ok) {
        setEditingItem(null);
        fetchPricingItems();
      } else {
        setError("Ошибка обновления цены");
      }
    } catch (err) {
      setError("Ошибка обновления цены");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteItem = async (itemId: number) => {
    if (!window.confirm("Вы уверены, что хотите удалить эту цену?")) {
      return;
    }

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/pricing/${itemId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        fetchPricingItems();
      } else {
        setError("Ошибка удаления цены");
      }
    } catch (err) {
      setError("Ошибка удаления цены");
    }
  };

  const handleToggleActive = async (item: PricingItem) => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/pricing/${item.id}/toggle`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ is_active: !item.is_active }),
      });

      if (response.ok) {
        fetchPricingItems();
      } else {
        setError("Ошибка изменения статуса");
      }
    } catch (err) {
      setError("Ошибка изменения статуса");
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-center">Загрузка цен...</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-2xl font-bold">Управление ценами</h1>
          <div className="flex space-x-2">
            <Button 
              onClick={() => {
                // Перезагружаем страницу для применения изменений
                window.location.reload();
              }}
              className="bg-green-500 hover:bg-green-600 text-white"
            >
              🔄 Применить изменения
            </Button>
            {userPermissions?.is_super_admin && (
              <>
                <Button 
                  onClick={async () => {
                    try {
                      const token = localStorage.getItem("token");
                      const response = await fetch("/admin/pricing/populate", {
                        method: "POST",
                        headers: {
                          Authorization: `Bearer ${token}`,
                        },
                      });
                      if (response.ok) {
                        fetchPricingItems();
                        alert("✅ Цены заполнены начальными данными!");
                      } else {
                        alert("❌ Ошибка заполнения цен");
                      }
                    } catch (err) {
                      alert("❌ Ошибка заполнения цен");
                    }
                  }}
                  className="bg-purple-500 hover:bg-purple-600 text-white"
                >
                  💰 Заполнить цены
                </Button>
                <Button onClick={() => setShowCreateForm(true)}>
                  Добавить цену
                </Button>
              </>
            )}
          </div>
        </div>

        {error && (
          <div className="bg-red-900 border border-red-500 text-red-100 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}
        
        <div className="bg-blue-900 border border-blue-500 text-blue-100 px-4 py-3 rounded mb-4">
          <strong>ℹ️ Информация:</strong> Изменения цен в админ панели автоматически применяются в боте и ЮKassa. 
          После изменения цены нажмите кнопку "🔄 Применить изменения" для обновления интерфейса.
        </div>
        
        {!userPermissions?.is_super_admin && (
          <div className="bg-yellow-900 border border-yellow-500 text-white px-4 py-3 rounded mb-4">
            <strong>⚠️ Ограничение:</strong> Вы можете только просматривать цены. Для редактирования цен требуются права главного администратора.
          </div>
        )}
      </div>

      {/* Форма создания новой цены */}
      {showCreateForm && (
        <Card className="p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Добавить новую цену</h2>
          <form onSubmit={handleCreateItem} className="space-y-4">
            <div className="form-group">
              <label className="form-label">Продукт:</label>
              <input
                type="text"
                value={newItem.product}
                onChange={(e) => setNewItem({...newItem, product: e.target.value})}
                className="w-full p-3 border border-gray-600 rounded bg-gray-800 text-white"
                placeholder="Например: Книга, Песня"
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Цена:</label>
              <input
                type="number"
                step="0.01"
                value={newItem.price}
                onChange={(e) => setNewItem({...newItem, price: e.target.value})}
                className="w-full p-3 border border-gray-600 rounded bg-gray-800 text-white"
                placeholder="0.00"
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Валюта:</label>
              <select
                value={newItem.currency}
                onChange={(e) => setNewItem({...newItem, currency: e.target.value})}
                className="w-full p-3 border border-gray-600 rounded bg-gray-800 text-white"
              >
                <option value="RUB">RUB</option>
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Описание:</label>
              <textarea
                value={newItem.description}
                onChange={(e) => setNewItem({...newItem, description: e.target.value})}
                className="w-full p-3 border border-gray-600 rounded bg-gray-800 text-white h-24"
                placeholder="Описание продукта..."
              />
            </div>
            <div className="form-group">
              <label className="form-label">Разница в цене при апгрейде:</label>
              <input
                type="number"
                step="0.01"
                value={newItem.upgrade_price_difference}
                onChange={(e) => setNewItem({...newItem, upgrade_price_difference: e.target.value})}
                className="w-full p-3 border border-gray-600 rounded bg-gray-800 text-white"
                placeholder="0.00"
              />
              <div className="text-xs text-blue-300 mt-1">
                Разница в цене при апгрейде с базовой версии на эту. Например, для "📦 Электронная + Печатная версия" это разница с "📄 Электронная книга".
              </div>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_active"
                checked={newItem.is_active}
                onChange={(e) => setNewItem({...newItem, is_active: e.target.checked})}
                className="w-4 h-4 text-blue-600 bg-gray-800 border-gray-600 rounded focus:ring-blue-500"
              />
              <label htmlFor="is_active" className="text-sm text-gray-300">Активна</label>
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={creating} className="btn-medium bg-blue-500 hover:bg-blue-700">
                {creating ? "Создание..." : "Создать цену"}
              </Button>
              <Button 
                type="button" 
                onClick={() => setShowCreateForm(false)}
                className="btn-medium bg-gray-500 hover:bg-gray-700"
              >
                Отмена
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* Список цен */}
      <div className="grid gap-4">
        {pricingItems.map((item) => (
          <Card key={item.id} className="p-4">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <h3 className="text-lg font-semibold mb-2">{item.product}</h3>
                <p className="text-gray-400 mb-2">{item.description}</p>
                <div className="flex items-center gap-4">
                  <span className="text-xl font-bold text-green-500">
                    {item.price} {item.currency}
                  </span>
                  {item.upgrade_price_difference > 0 && (
                    <span className="text-sm text-blue-400">
                      Апгрейд: +{item.upgrade_price_difference} {item.currency}
                    </span>
                  )}
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    item.is_active 
                      ? "bg-green-100 text-green-800" 
                      : "bg-gray-100 text-gray-800"
                  }`}>
                    {item.is_active ? "Активна" : "Неактивна"}
                  </span>
                </div>
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={() => setEditingItem(item)}
                  className="btn-small bg-blue-500 hover:bg-blue-700 text-white rounded"
                >
                  Редактировать
                </button>
                <button
                  onClick={() => handleToggleActive(item)}
                  className={`btn-small rounded ${
                    item.is_active 
                      ? "bg-yellow-500 hover:bg-yellow-700 text-white" 
                      : "bg-green-500 hover:bg-green-700 text-white"
                  }`}
                >
                  {item.is_active ? "Деактивировать" : "Активировать"}
                </button>
                <button
                  onClick={() => handleDeleteItem(item.id)}
                  className="btn-small bg-red-500 hover:bg-red-700 text-white rounded"
                >
                  Удалить
                </button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {pricingItems.length === 0 && (
        <div className="text-center text-gray-300 mt-8">
          Нет настроенных цен
        </div>
      )}

      {/* Модальное окно редактирования */}
      {editingItem && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4">
          <Card className="p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold mb-4">Редактировать цену</h2>
            <form onSubmit={handleUpdateItem} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2 text-white">Продукт:</label>
                <input
                  type="text"
                  value={editingItem.product}
                  onChange={(e) => setEditingItem({...editingItem, product: e.target.value})}
                  className="border border-gray-300 rounded px-3 py-2 w-full bg-gray-800 text-white"
                  placeholder="📄 Электронная книга"
                  required
                />
                <div className="text-xs text-blue-300 mt-1">
                  Примеры: 📄 Электронная книга, 📦 Электронная + Печатная версия, 💌 Песня
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2 text-white">Цена:</label>
                  <input
                    type="text"
                    value={editingItem.price.toString()}
                    onChange={(e) => {
                      const value = e.target.value;
                      // Разрешаем только цифры, точку и запятую
                      if (value === '' || /^[0-9.,]*$/.test(value)) {
                        setEditingItem({...editingItem, price: parseFloat(value.replace(',', '.')) || 0});
                      }
                    }}
                    className="border border-gray-300 rounded px-3 py-2 w-full bg-gray-800 text-white"
                    placeholder="Введите цену"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2 text-white">Валюта:</label>
                  <select
                    value={editingItem.currency}
                    onChange={(e) => setEditingItem({...editingItem, currency: e.target.value})}
                    className="border border-gray-300 rounded px-3 py-2 w-full bg-gray-800 text-white"
                  >
                    <option value="RUB">RUB (₽)</option>
                    <option value="USD">USD ($)</option>
                    <option value="EUR">EUR (€)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-white">Описание:</label>
                <textarea
                  value={editingItem.description}
                  onChange={(e) => setEditingItem({...editingItem, description: e.target.value})}
                  className="border border-gray-300 rounded px-3 py-2 w-full h-24 bg-gray-800 text-white"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-white">Разница в цене при апгрейде:</label>
                <input
                  type="number"
                  step="0.01"
                  value={editingItem.upgrade_price_difference.toString()}
                  onChange={(e) => setEditingItem({...editingItem, upgrade_price_difference: parseFloat(e.target.value) || 0})}
                  className="border border-gray-300 rounded px-3 py-2 w-full bg-gray-800 text-white"
                  placeholder="0.00"
                />
                <div className="text-xs text-blue-300 mt-1">
                  Разница в цене при апгрейде с базовой версии на эту. Например, для "📦 Электронная + Печатная версия" это разница с "📄 Электронная книга".
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-white">Статус:</label>
                <select
                  value={editingItem.is_active ? "true" : "false"}
                  onChange={(e) => setEditingItem({...editingItem, is_active: e.target.value === "true"})}
                  className="border border-gray-300 rounded px-3 py-2 w-full bg-gray-800 text-white"
                >
                  <option value="true">Активна</option>
                  <option value="false">Неактивна</option>
                </select>
              </div>

              <div className="flex space-x-2">
                <Button type="submit" disabled={saving} className="bg-blue-500 hover:bg-blue-600 text-white">
                  {saving ? "⏳ Сохранение..." : "💾 Сохранить"}
                </Button>
                <Button
                  type="button"
                  className="bg-gray-600 hover:bg-gray-700 text-white"
                  onClick={() => setEditingItem(null)}
                >
                  ❌ Отмена
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
}; 