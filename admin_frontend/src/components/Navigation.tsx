import React, { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Button } from "./ui/button";

export const Navigation: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [userPermissions, setUserPermissions] = useState<{is_super_admin: boolean} | null>(null);

  useEffect(() => {
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

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/login");
  };

  return (
    <nav className="bg-gray-800 text-white p-4">
      <div className="max-w-7xl mx-auto flex justify-between items-center">
        <div className="flex items-center space-x-4 lg:space-x-6">
          <h1 className="text-xl font-bold">Админ панель</h1>
          <div className="flex flex-wrap space-x-2 lg:space-x-4">
            <Button
              onClick={() => navigate("/admin/orders")}
              className={`nav-item ${
                location.pathname.startsWith("/admin/orders") 
                  ? "bg-blue-600 hover:bg-blue-700" 
                  : "bg-transparent hover:bg-gray-700"
              }`}
            >
              {userPermissions?.is_super_admin ? "Все заказы" : "Мои заказы"}
            </Button>
            <Button
              onClick={() => navigate("/admin/photos")}
              className={`nav-item ${
                location.pathname.startsWith("/admin/photos") 
                  ? "bg-blue-600 hover:bg-blue-700" 
                  : "bg-transparent hover:bg-gray-700"
              }`}
            >
              Фотографии/аудио
            </Button>
            <Button
              onClick={() => navigate("/admin/delayed-messages")}
              className={`nav-item ${
                location.pathname.startsWith("/admin/delayed-messages") 
                  ? "bg-blue-600 hover:bg-blue-700" 
                  : "bg-transparent hover:bg-gray-700"
              }`}
            >
              Отложенные сообщения
            </Button>
            <Button
              onClick={() => navigate("/admin/content")}
              className={`nav-item ${
                location.pathname.startsWith("/admin/content") 
                  ? "bg-blue-600 hover:bg-blue-700" 
                  : "bg-transparent hover:bg-gray-700"
              }`}
            >
              Контент
            </Button>
            <Button
              onClick={() => navigate("/admin/metrics")}
              className={`nav-item ${
                location.pathname.startsWith("/admin/metrics") 
                  ? "bg-blue-600 hover:bg-blue-700" 
                  : "bg-transparent hover:bg-gray-700"
              }`}
            >
              Метрики
            </Button>

            {userPermissions?.is_super_admin && (
              <>
                <Button
                  onClick={() => navigate("/admin/managers")}
                  className={`nav-item ${
                    location.pathname.startsWith("/admin/managers") 
                      ? "bg-blue-600 hover:bg-blue-700" 
                      : "bg-transparent hover:bg-gray-700"
                  }`}
                >
                  Менеджеры
                </Button>
                <Button
                  onClick={() => navigate("/admin/pricing")}
                  className={`nav-item ${
                    location.pathname.startsWith("/admin/pricing") 
                      ? "bg-blue-600 hover:bg-blue-700" 
                      : "bg-transparent hover:bg-gray-700"
                  }`}
                >
                  Цены
                </Button>
              </>
            )}
            <Button
              onClick={() => navigate("/admin/profile")}
              className={`nav-item ${
                location.pathname.startsWith("/admin/profile") 
                  ? "bg-blue-600 hover:bg-blue-700" 
                  : "bg-transparent hover:bg-gray-700"
              }`}
            >
              Личный кабинет
            </Button>
          </div>
        </div>
        <Button
          onClick={handleLogout}
          className="nav-item border border-white hover:bg-white hover:text-gray-800"
        >
          Выйти
        </Button>
      </div>
    </nav>
  );
}; 