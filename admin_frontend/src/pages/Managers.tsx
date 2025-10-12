import React, { useState, useEffect } from "react";
import { Button } from "../components/ui/button";
import { validateEmail, cleanEmail, ValidationResult } from "../utils/validation";

interface Manager {
  id: number;
  email: string;
  full_name: string | null;
  is_super_admin: boolean;
}

export const ManagersPage: React.FC = () => {
  const [managers, setManagers] = useState<Manager[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [file, setFile] = useState<File | null>(null);
  const [userPermissions, setUserPermissions] = useState<{is_super_admin: boolean} | null>(null);
  
  // Состояния для создания менеджера по одному
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");
  const [createSuccess, setCreateSuccess] = useState(false);
  const [emailValidationError, setEmailValidationError] = useState("");
  const [newManager, setNewManager] = useState({
    email: "",
    password: "",
    full_name: "",
    is_super_admin: false
  });

  // Состояния для редактирования менеджера
  const [editingManager, setEditingManager] = useState<Manager | null>(null);
  const [showEditForm, setShowEditForm] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editError, setEditError] = useState("");
  const [editSuccess, setEditSuccess] = useState(false);
  const [editForm, setEditForm] = useState({
    full_name: "",
    is_super_admin: false
  });

  // Состояние для фильтрации
  const [roleFilter, setRoleFilter] = useState("all");

  // Фильтрованные менеджеры
  const filteredManagers = managers.filter(manager => {
    if (roleFilter === "all") return true;
    if (roleFilter === "admin") return manager.is_super_admin;
    if (roleFilter === "manager") return !manager.is_super_admin;
    return true;
  });

  useEffect(() => {
    fetchUserPermissions();
    fetchManagers();
  }, []);

  // Автоматически скрываем сообщение об успехе через 3 секунды
  useEffect(() => {
    if (createSuccess) {
      const timer = setTimeout(() => {
        setCreateSuccess(false);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [createSuccess]);

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

  const fetchManagers = async () => {
    setLoading(true);
    setError("");
    try {
      const token = localStorage.getItem("token");
      const response = await fetch("/admin/managers", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        throw new Error("Ошибка загрузки менеджеров");
      }
      const data = await response.json();
      setManagers(data);
    } catch (err: any) {
      setError(err.message || "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setUploadError("Выберите файл");
      return;
    }

         setUploading(true);
     setUploadSuccess(false);
     setUploadError("");
     setUploadResult(null);
    
    try {
      // Определяем тип файла
      const isExcel = file.name.toLowerCase().endsWith('.xlsx') || file.name.toLowerCase().endsWith('.xls');
      
             if (isExcel) {
         // Для Excel файлов отправляем на сервер
         console.log("Отправляем Excel файл на сервер:", file.name);
         const formData = new FormData();
         formData.append('file', file);
         
         const token = localStorage.getItem("token");
         console.log("Токен:", token ? "есть" : "нет");
         
         const response = await fetch("/admin/managers/upload", {
           method: "POST",
           headers: {
             Authorization: `Bearer ${token}`,
           },
           body: formData,
         });
         
         console.log("Ответ сервера:", response.status, response.statusText);
        
                 if (!response.ok) {
           let errorMessage = "Ошибка загрузки Excel файла";
           try {
             const errorData = await response.json();
             errorMessage = errorData.detail || errorMessage;
           } catch (e) {
             errorMessage = `HTTP ${response.status}: ${response.statusText}`;
           }
           throw new Error(errorMessage);
         }
        
                 const result = await response.json();
         console.log("Результат загрузки:", result);
         setUploadResult(result);
         setUploadSuccess(true);
         setFile(null);
         await fetchManagers();
         return;
      } else {
        // Для CSV файлов читаем на фронтенде
        const reader = new FileReader();
        reader.onload = async (event) => {
          try {
            const csv = event.target?.result as string;
            const lines = csv.split('\n');
            const headers = lines[0].split(',');
            
            // Проверяем заголовки
            const requiredHeaders = ['Email', 'Пароль', 'ФИО'];
            const missingHeaders = requiredHeaders.filter(h => !headers.includes(h));
            if (missingHeaders.length > 0) {
              throw new Error(`Отсутствуют колонки: ${missingHeaders.join(', ')}`);
            }
            
            const newManagers: { email: string; password: string; full_name: string }[] = [];
            
            // Обрабатываем каждую строку (начиная со второй)
            for (let i = 1; i < lines.length; i++) {
              const line = lines[i].trim();
              if (!line) continue;
              
              const values = line.split(',');
              if (values.length < 3) continue;
              
              const email = values[0].trim();
              const password = values[1].trim();
              const fullName = values[2].trim();
              
              if (!email || !password || !fullName) {
                continue;
              }
              
                             if (!email.includes('@') || email.split('@')[0].length < 1) {
                 continue;
               }
              
              newManagers.push({
                email,
                password,
                full_name: fullName
              });
            }
            
            // Добавляем менеджеров через API
            const token = localStorage.getItem("token");
            for (const manager of newManagers) {
              const response = await fetch("/admin/managers", {
                method: "POST",
                headers: {
                  Authorization: `Bearer ${token}`,
                  "Content-Type": "application/json",
                },
                body: JSON.stringify(manager),
              });
              
              if (!response.ok) {
                const errorData = await response.json();
                throw new Error(`Ошибка добавления ${manager.email}: ${errorData.detail}`);
              }
            }
            
            setUploadSuccess(true);
            setFile(null);
            // Обновляем список менеджеров после успешной загрузки
            await fetchManagers();
          } catch (err: any) {
            setUploadError(err.message || "Ошибка обработки файла");
          } finally {
            setUploading(false);
          }
        };
        
        reader.readAsText(file);
      }
    } catch (err: any) {
      setUploadError(err.message || "Ошибка чтения файла");
      setUploading(false);
    }
  };

  // Функция для создания менеджера по одному
  const handleCreateManager = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!newManager.email || !newManager.password || !newManager.full_name) {
      setCreateError("Все поля обязательны для заполнения");
      return;
    }

    // Валидация email с помощью новой функции
    const emailValidation: ValidationResult = validateEmail(newManager.email);
    if (!emailValidation.isValid) {
      setCreateError(emailValidation.error);
      return;
    }

    if (newManager.password.length < 6) {
      setCreateError("Пароль должен содержать минимум 6 символов");
      return;
    }

    setCreating(true);
    setCreateError("");
    setCreateSuccess(false);

    try {
      const token = localStorage.getItem("token");
      const response = await fetch("/admin/managers", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: cleanEmail(newManager.email),
          password: newManager.password,
          full_name: newManager.full_name,
          is_super_admin: newManager.is_super_admin
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Ошибка создания менеджера");
      }

      setCreateSuccess(true);
      clearCreateForm();
      setShowCreateForm(false);
      
      // Обновляем список менеджеров
      await fetchManagers();
    } catch (err: any) {
      setCreateError(err.message || "Ошибка создания менеджера");
    } finally {
      setCreating(false);
    }
  };

  // Функция для валидации email в реальном времени
  const handleEmailChange = (email: string) => {
    setNewManager({...newManager, email});
    
    if (email.trim()) {
      const emailValidation = validateEmail(email);
      setEmailValidationError(emailValidation.isValid ? "" : emailValidation.error);
    } else {
      setEmailValidationError("");
    }
  };

  // Функция для очистки формы создания
  const clearCreateForm = () => {
    setNewManager({
      email: "",
      password: "",
      full_name: "",
      is_super_admin: false
    });
    setCreateError("");
    setCreateSuccess(false);
    setEmailValidationError("");
  };

  // Функция для начала редактирования менеджера
  const startEditManager = (manager: Manager) => {
    setEditingManager(manager);
    setEditForm({
      full_name: manager.full_name || "",
      is_super_admin: manager.is_super_admin
    });
    setShowEditForm(true);
    setEditError("");
    setEditSuccess(false);
  };

  // Функция для отмены редактирования
  const cancelEdit = () => {
    setEditingManager(null);
    setShowEditForm(false);
    setEditForm({
      full_name: "",
      is_super_admin: false
    });
    setEditError("");
    setEditSuccess(false);
  };

  // Функция для сохранения изменений менеджера
  const handleEditManager = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!editForm.full_name.trim()) {
      setEditError("ФИО обязательно для заполнения");
      return;
    }

    if (!editingManager) return;

    setEditing(true);
    setEditError("");
    setEditSuccess(false);

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/managers/${editingManager.id}`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          full_name: editForm.full_name.trim(),
          is_super_admin: editForm.is_super_admin
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Ошибка обновления менеджера");
      }

      setEditSuccess(true);
      
      // Обновляем список менеджеров
      await fetchManagers();
      
      // Автоматически закрываем форму через 2 секунды
      setTimeout(() => {
        cancelEdit();
      }, 2000);
    } catch (err: any) {
      setEditError(err.message || "Ошибка обновления менеджера");
    } finally {
      setEditing(false);
    }
  };

  // Функция для удаления менеджера
  const handleDeleteManager = async (managerId: number) => {
    // Проверяем, не пытается ли пользователь удалить самого себя
    const currentUserEmail = localStorage.getItem("userEmail");
    const managersData = await fetch("/admin/managers", {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    }).then(res => res.json());
    const currentUser = managersData.find((m: any) => m.id === 1); // Предполагаем, что ID 1 - это текущий пользователь

    if (currentUser && currentUser.email === currentUserEmail) {
      alert("Вы не можете удалить самого себя!");
      return;
    }

    if (!window.confirm(`Вы уверены, что хотите удалить менеджера?`)) {
      return;
    }

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/managers/${managerId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Ошибка удаления менеджера");
      }

      // Обновляем список менеджеров
      await fetchManagers();
    } catch (err: any) {
      alert(`Ошибка удаления менеджера: ${err.message}`);
    }
  };

  // Проверяем права доступа
  if (userPermissions && !userPermissions.is_super_admin) {
    return (
      <div className="p-8">
        <div className="bg-red-900 border border-red-700 rounded-lg p-6 text-center">
          <h1 className="text-2xl font-bold text-red-200 mb-4">Доступ запрещен</h1>
          <p className="text-red-300">
            У вас нет прав для доступа к этой странице. 
            Требуются права главного администратора.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Управление менеджерами</h1>
        <div className="text-sm text-gray-400">
          {roleFilter === "all" 
            ? `Всего менеджеров: ${managers.length}`
            : `Показано: ${filteredManagers.length} из ${managers.length}`
          }
        </div>
      </div>
      
      {/* Форма загрузки файла */}
      <div className="bg-gray-900 rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-bold mb-4">Добавление менеджеров из файла</h2>
        <p className="text-sm text-gray-400 mb-4">
          Email используется как логин для входа в систему
        </p>
        <form onSubmit={handleFileUpload} className="flex flex-col gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">
              Выберите файл (.csv, .txt, .xlsx, .xls)
            </label>
            <input
              type="file"
              accept=".csv,.txt,.xlsx,.xls"
              onChange={e => setFile(e.target.files?.[0] || null)}
              className="text-white border border-gray-600 rounded px-3 py-2 w-full"
            />
            <p className="text-sm text-gray-400 mt-1">
              Файл должен содержать колонки: Email (логин), Пароль, ФИО (CSV или Excel формат). Пароли будут рассылаться отдельно.
            </p>
          </div>
          <Button 
            type="submit" 
            disabled={uploading || !file}
            className="w-fit"
          >
            {uploading ? "Добавление..." : "Добавить менеджеров"}
          </Button>
                     {uploadSuccess && uploadResult && (
             <div className="text-green-400">
               ✅ Файл успешно обработан
               <div className="text-sm mt-1">
                 Добавлено: {uploadResult.added_count} менеджеров
                                   {uploadResult.errors && uploadResult.errors.length > 0 && (
                    <div className="text-yellow-400 mt-1">
                      Ошибки: {uploadResult.errors.length}
                      <div className="text-xs mt-1">
                        {uploadResult.errors.map((error: string, index: number) => (
                          <div key={index} className="text-red-400">
                            {error}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
               </div>
             </div>
           )}
          {uploadError && (
            <div className="text-red-400">{uploadError}</div>
          )}
        </form>
      </div>

      {/* Форма создания менеджера по одному */}
      <div className="bg-gray-900 rounded-lg shadow p-6 mb-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">Создание менеджера</h2>
          <Button
            type="button"
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {showCreateForm ? "Скрыть форму" : "Создать менеджера"}
          </Button>
        </div>
        
        {showCreateForm && (
          <form onSubmit={handleCreateManager} className="space-y-4">
            <div className="form-group">
              <label className="form-label">Email (логин):</label>
              <input
                type="email"
                value={newManager.email}
                onChange={(e) => handleEmailChange(e.target.value)}
                className={`w-full p-3 border rounded bg-gray-800 text-white ${
                  emailValidationError ? 'border-red-500' : 'border-gray-600'
                }`}
                placeholder="manager@example.com"
                required
              />
              {emailValidationError && (
                <p className="text-red-400 text-sm mt-1">
                  {emailValidationError}
                </p>
              )}
            </div>
            <div className="form-group">
              <label className="form-label">Пароль:</label>
              <input
                type="password"
                value={newManager.password}
                onChange={(e) => setNewManager({...newManager, password: e.target.value})}
                className="w-full p-3 border border-gray-600 rounded bg-gray-800 text-white"
                placeholder="Минимум 6 символов"
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">ФИО:</label>
              <input
                type="text"
                value={newManager.full_name}
                onChange={(e) => setNewManager({...newManager, full_name: e.target.value})}
                className="w-full p-3 border border-gray-600 rounded bg-gray-800 text-white"
                placeholder="Иванов Иван Иванович"
                required
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_super_admin"
                checked={newManager.is_super_admin}
                onChange={(e) => setNewManager({...newManager, is_super_admin: e.target.checked})}
                className="w-4 h-4 text-blue-600 bg-gray-800 border-gray-600 rounded focus:ring-blue-500"
              />
              <label htmlFor="is_super_admin" className="text-sm text-gray-300">Главный администратор</label>
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={creating} className="btn-medium bg-blue-500 hover:bg-blue-700">
                {creating ? "Создание..." : "Создать менеджера"}
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
        )}
      </div>

      {/* Форма редактирования менеджера */}
      {showEditForm && editingManager && (
        <div className="bg-gray-900 rounded-lg shadow p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold">Редактирование менеджера</h2>
            <Button
              type="button"
              onClick={cancelEdit}
              className="bg-gray-600 hover:bg-gray-700"
            >
              Закрыть
            </Button>
          </div>
          
          <form onSubmit={handleEditManager} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2 text-white">
                  Email (логин)
                </label>
                <input
                  type="email"
                  value={editingManager.email}
                  className="w-full px-3 py-2 border border-gray-600 rounded bg-gray-800 text-white"
                  disabled
                />
                <p className="text-xs text-gray-400 mt-1">
                  Email нельзя изменить
                </p>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2 text-white">
                  ID менеджера
                </label>
                <input
                  type="text"
                  value={editingManager.id}
                  className="w-full px-3 py-2 border border-gray-600 rounded bg-gray-800 text-white"
                  disabled
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2 text-white">
                ФИО *
              </label>
              <input
                type="text"
                value={editForm.full_name}
                onChange={(e) => setEditForm({...editForm, full_name: e.target.value})}
                className="w-full px-3 py-2 border border-gray-600 rounded bg-gray-800 text-white"
                placeholder="Иванов Иван Иванович"
                required
              />
            </div>
            
            <div className="bg-blue-900 border border-blue-700 rounded p-3">
              <p className="text-sm text-blue-200">
                💡 <strong>Смена пароля:</strong> Менеджер может изменить свой пароль в разделе "Личный кабинет" → "Профиль"
              </p>
            </div>
            
            <div className="flex items-center">
              <input
                type="checkbox"
                id="edit_is_super_admin"
                checked={editForm.is_super_admin}
                onChange={(e) => setEditForm({...editForm, is_super_admin: e.target.checked})}
                className="mr-2"
              />
              <label htmlFor="edit_is_super_admin" className="text-sm text-white">
                Главный администратор
              </label>
            </div>
            
            <div className="flex gap-3">
              <Button
                type="submit"
                disabled={editing}
                className="bg-green-600 hover:bg-green-700"
              >
                {editing ? "Сохранение..." : "Сохранить изменения"}
              </Button>
              
              <Button
                type="button"
                onClick={cancelEdit}
                className="bg-gray-600 hover:bg-gray-700"
              >
                Отмена
              </Button>
            </div>
            
            {editSuccess && (
              <div className="text-green-400 text-sm">
                ✅ Изменения успешно сохранены
              </div>
            )}
            
            {editError && (
              <div className="text-red-400 text-sm">
                ❌ {editError}
              </div>
            )}
          </form>
        </div>
      )}

      {/* Список менеджеров */}
      <div className="bg-gray-900 rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">Список менеджеров</h2>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <label className="text-sm text-white">Фильтр по роли:</label>
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="px-3 py-1 border border-gray-600 rounded bg-gray-800 text-white text-sm"
              >
                <option value="all">Все роли</option>
                <option value="admin">Главные админы</option>
                <option value="manager">Менеджеры</option>
              </select>
              {roleFilter !== "all" && (
                <Button
                  type="button"
                  onClick={() => setRoleFilter("all")}
                  className="px-2 py-1 text-xs bg-gray-600 hover:bg-gray-700"
                >
                  Сбросить
                </Button>
              )}
            </div>
            <div className="text-sm text-gray-400">
              Показано: {filteredManagers.length} из {managers.length}
            </div>
          </div>
        </div>
        
        {loading && <div className="text-white">Загрузка...</div>}
        {error && <div className="text-red-500 mb-4">{error}</div>}
        
        <div className="overflow-x-auto">
          <table className="min-w-full border text-sm">
            <thead>
              <tr className="table-header">
                <th className="border px-4 py-2">ID</th>
                <th className="border px-4 py-2">Email (логин)</th>
                <th className="border px-4 py-2">ФИО</th>
                <th className="border px-4 py-2">Роль</th>
                <th className="border px-4 py-2">Действия</th>
              </tr>
            </thead>
            <tbody>
              {filteredManagers.map((manager) => (
                <tr key={manager.id} className="hover:bg-gray-800">
                  <td className="table-cell">{manager.id}</td>
                  <td className="table-cell">{manager.email}</td>
                  <td className="table-cell">{manager.full_name || "-"}</td>
                  <td className="table-cell">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      manager.is_super_admin 
                        ? "bg-red-100 text-red-800" 
                        : "bg-blue-100 text-blue-800"
                    }`}>
                      {manager.is_super_admin ? "Администратор" : "Менеджер"}
                    </span>
                  </td>
                  <td className="table-cell">
                    <div className="flex space-x-2">
                      <button
                        onClick={() => startEditManager(manager)}
                        className="btn-small bg-blue-500 hover:bg-blue-700 text-white rounded"
                      >
                        Редактировать
                      </button>
                      {userPermissions?.is_super_admin && manager.id !== 1 && (
                        <button
                          onClick={() => handleDeleteManager(manager.id)}
                          className="btn-small bg-red-500 hover:bg-red-700 text-white rounded"
                        >
                          Удалить
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}; 