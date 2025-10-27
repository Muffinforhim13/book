import React, { useState, useEffect } from "react";
import { Card } from "../components/ui/card";
import { translateStatus } from "../utils/statusTranslations";
import { getMSKDateRange, getMSKToday, formatDateTime } from '../utils/timeUtils';

interface MetricsData {
  totalOrders: number;
  paidOrders: number;
  upsellOrders: number;
  completedOrders: number;
  pendingOrders: number;
  totalRevenue: number;
  averageOrderValue: number;
  ordersByStatus: { [key: string]: number };
  ordersByProduct: { [key: string]: number };
  ordersByMonth: { [key: string]: number };
  conversionRate: number;
  topManagers: Array<{
    name: string;
    email: string;
    ordersCount: number;
    revenue: number;
  }>;
  
  // Новые метрики из трекинга событий
  funnelMetrics: {
    funnel_data: { 
      [key: string]: {
        unique_users: number;
        total_clicks: number;
      }
    };
    conversions: { [key: string]: number };
    song_demo_users?: number;
    book_demo_users?: number;
  };
  abandonmentMetrics: Array<{
    step_name: string;
    abandonment_count: number;
    unique_users: number;
  }>;
  revenueMetrics: {
    main_purchases: {
      count: number;
      revenue: number;
      avg_value: number;
    };
    upsells: {
      count: number;
      revenue: number;
    };
  };
  detailedRevenueMetrics: {
    [key: string]: {
      count: number;
      revenue: number;
      avg_value: number;
    };
    'Книга (общее)': {
      count: number;
      revenue: number;
      avg_value: number;
    };
    'Книга печатная': {
      count: number;
      revenue: number;
      avg_value: number;
    };
    'Книга электронная': {
      count: number;
      revenue: number;
      avg_value: number;
    };
    'Песня (общее)': {
      count: number;
      revenue: number;
      avg_value: number;
    };
    'Песня': {
      count: number;
      revenue: number;
      avg_value: number;
    };
  };
  
  // Дополнительные метрики
  uniqueUsers: number;
  startRate: number;
  productSelectionRate: number;
  orderCreationRate: number;
  purchaseRate: number;
  
  // Детальные метрики по продуктам
  bookSelections: number;
  songSelections: number;
  bookPurchases: number;
  songPurchases: number;
  uniqueBookPurchasers: number;
  uniqueSongPurchasers: number;
  uniqueUpsellPurchasers: number;
  totalUniqueUsers: number;
}

interface AnalyticsData {
  order_id: string;
  source: string;
  utm_source: string;
  utm_medium: string;
  utm_campaign: string;
  username: string;
  product_type: string;
  created_at: string;
  purchase_status: string;
  upsell_status: string;
  progress: string;
  manager: string;
  phone: string;
  email: string;
}

interface AnalyticsResponse {
  status: string;
  data: AnalyticsData[];
  total: number;
  start_date: string;
  end_date: string;
}

interface UtmFiltersResponse {
  status: string;
  data: {
    utm_sources: string[];
    utm_mediums: string[];
    utm_campaigns: string[];
  };
}

export const MetricsPage: React.FC = () => {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'metrics' | 'analytics'>('metrics');
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData[]>([]);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    productType: '',
    purchaseStatus: '',
    upsellStatus: '',
    progress: '',
    utmSource: '',
    utmMedium: '',
    utmCampaign: ''
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [dateRange, setDateRange] = useState<{
    start: string;
    end: string;
  }>(getMSKDateRange());
  const [utmFilters, setUtmFilters] = useState<{
    utm_sources: string[];
    utm_mediums: string[];
    utm_campaigns: string[];
  }>({
    utm_sources: [],
    utm_mediums: [],
    utm_campaigns: []
  });

  useEffect(() => {
    fetchMetrics();
  }, [dateRange]);

  useEffect(() => {
    if (activeTab === 'analytics') {
      fetchAnalytics();
      fetchUtmFilters();
    }
  }, [activeTab, dateRange, filters, searchQuery]);

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      setError(null);
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/metrics?start_date=${dateRange.start}&end_date=${dateRange.end}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          // Токен истек или недействителен
          localStorage.removeItem("token");
          window.location.href = "/login";
          return;
        }
        const errorText = await response.text();
        console.error("API Error:", response.status, errorText);
        throw new Error(`Ошибка загрузки метрик: ${response.status} ${errorText}`);
      }

      const data = await response.json();
      console.log("Metrics data:", data);
      
      // ОТЛАДКА: Выводим полученные данные
      console.log('🔍 ОТЛАДКА ФРОНТЕНД - Полученные данные метрик:', {
        totalOrders: data.totalOrders,
        paidOrders: data.paidOrders,
        bookPurchases: data.bookPurchases,
        songPurchases: data.songPurchases,
        totalUniqueUsers: data.totalUniqueUsers
      });
      
      setMetrics(data);
    } catch (err) {
      console.error("Fetch error:", err);
      setError(err instanceof Error ? err.message : "Неизвестная ошибка");
    } finally {
      setLoading(false);
    }
  };

  const fetchAnalytics = async () => {
    try {
      setAnalyticsLoading(true);
      setAnalyticsError(null);
      const token = localStorage.getItem("token");
      
      // Строим URL с фильтрами
      const params = new URLSearchParams({
        start_date: dateRange.start,
        end_date: dateRange.end
      });
      
      if (filters.productType) params.append('product_type', filters.productType);
      if (filters.purchaseStatus) params.append('purchase_status', filters.purchaseStatus);
      if (filters.upsellStatus) params.append('upsell_status', filters.upsellStatus);
      if (filters.progress) params.append('progress', filters.progress);
      if (filters.utmSource) params.append('utm_source', filters.utmSource);
      if (filters.utmMedium) params.append('utm_medium', filters.utmMedium);
      if (filters.utmCampaign) params.append('utm_campaign', filters.utmCampaign);
      if (searchQuery) params.append('search', searchQuery);
      
      const response = await fetch(`/admin/analytics?${params.toString()}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          // Токен истек или недействителен
          localStorage.removeItem("token");
          window.location.href = "/login";
          return;
        }
        const errorText = await response.text();
        console.error("Analytics API Error:", response.status, errorText);
        throw new Error(`Ошибка загрузки аналитики: ${response.status} ${errorText}`);
      }

      const result: AnalyticsResponse = await response.json();
      console.log("Analytics data:", result);
      
      if (result.status === 'success') {
        setAnalyticsData(result.data);
      } else {
        throw new Error('Ошибка получения данных аналитики');
      }
    } catch (err) {
      console.error("Analytics fetch error:", err);
      setAnalyticsError(err instanceof Error ? err.message : "Неизвестная ошибка");
    } finally {
      setAnalyticsLoading(false);
    }
  };

  const fetchUtmFilters = async () => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch('/admin/analytics/utm-filters', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          // Токен истек или недействителен
          localStorage.removeItem("token");
          window.location.href = "/login";
          return;
        }
        const errorText = await response.text();
        console.error("UTM Filters API Error:", response.status, errorText);
        throw new Error(`Ошибка загрузки UTM-фильтров: ${response.status} ${errorText}`);
      }

      const result: UtmFiltersResponse = await response.json();
      console.log("UTM Filters data:", result);
      
      if (result.status === 'success') {
        setUtmFilters(result.data);
      } else {
        throw new Error('Ошибка получения UTM-фильтров');
      }
    } catch (err) {
      console.error("UTM Filters fetch error:", err);
      // Не показываем ошибку пользователю, просто логируем
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Оплачен':
        return 'text-green-600 bg-green-100';
      case 'Не оплачен':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getProgressColor = (progress: string) => {
    if (progress.includes('100%')) {
      return 'text-green-600 bg-green-100';
    } else if (progress.includes('75%')) {
      return 'text-blue-600 bg-blue-100';
    } else if (progress.includes('50%')) {
      return 'text-yellow-600 bg-yellow-100';
    } else {
      return 'text-gray-600 bg-gray-100';
    }
  };

  const resetFilters = () => {
    setFilters({
      productType: '',
      purchaseStatus: '',
      upsellStatus: '',
      progress: '',
      utmSource: '',
      utmMedium: '',
      utmCampaign: ''
    });
    setSearchQuery('');
  };

  const exportData = async (format: 'csv' | 'excel') => {
    try {
      const token = localStorage.getItem("token");
      
      // ОТЛАДКА: Выводим текущие фильтры
      console.log('🔍 ОТЛАДКА экспорта: текущие фильтры:', filters);
      console.log('🔍 ОТЛАДКА экспорта: поиск:', searchQuery);
      console.log('🔍 ОТЛАДКА экспорта: даты:', dateRange);
      
      // Строим URL с фильтрами и поиском
      const params = new URLSearchParams({
        start_date: dateRange.start,
        end_date: dateRange.end,
        format: format
      });
      
      if (filters.productType) params.append('product_type', filters.productType);
      if (filters.purchaseStatus) params.append('purchase_status', filters.purchaseStatus);
      if (filters.upsellStatus) params.append('upsell_status', filters.upsellStatus);
      if (filters.progress) params.append('progress', filters.progress);
      if (filters.utmSource) params.append('utm_source', filters.utmSource);
      if (filters.utmMedium) params.append('utm_medium', filters.utmMedium);
      if (filters.utmCampaign) params.append('utm_campaign', filters.utmCampaign);
      if (searchQuery) params.append('search', searchQuery);
      
      console.log('🔍 ОТЛАДКА экспорта: финальный URL:', `/admin/analytics/export?${params.toString()}`);
      
      const response = await fetch(`/admin/analytics/export?${params.toString()}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          // Токен истек или недействителен
          localStorage.removeItem("token");
          window.location.href = "/login";
          return;
        }
        throw new Error(`Ошибка экспорта: ${response.status}`);
      }

      // Создаем ссылку для скачивания
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      // Правильно определяем расширение файла
      const fileExtension = format === 'excel' ? 'xlsx' : 'csv';
      a.download = `analytics_${dateRange.start}_to_${dateRange.end}.${fileExtension}`;
      
      // Проверяем MIME тип для отладки
      console.log(`Экспорт ${format}: MIME type = ${blob.type}, size = ${blob.size} bytes`);
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
    } catch (err) {
      console.error('Ошибка экспорта:', err);
      const errorMessage = err instanceof Error ? err.message : 'Неизвестная ошибка';
      alert(`Ошибка при экспорте данных: ${errorMessage}`);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex justify-center items-center h-64">
          <div className="text-lg">Загрузка метрик...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          Ошибка: {error}
        </div>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-center">Нет данных для отображения</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">Метрики</h1>
        
        {/* Вкладки */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('metrics')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'metrics'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Основные метрики
            </button>
            <button
              onClick={() => setActiveTab('analytics')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'analytics'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Аналитика
            </button>
          </nav>
        </div>
        
        {/* Фильтр по датам */}
        <div className="flex gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Дата начала
            </label>
            <input
              type="date"
              value={dateRange.start}
              onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
              className="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Дата окончания
            </label>
            <input
              type="date"
              value={dateRange.end}
              onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
              className="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Контент вкладок */}
      {activeTab === 'metrics' && (
        <>
          {/* Основные метрики */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card className="p-6">
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-600">{metrics.totalOrders}</div>
            <div className="text-gray-600">Всего заказов</div>
          </div>
        </Card>
        
        <Card className="p-6">
          <div className="text-center">
            <div className="text-3xl font-bold text-green-600">{metrics.paidOrders || 0}</div>
            <div className="text-gray-600">Оплаченных</div>
          </div>
        </Card>
        
        <Card className="p-6">
          <div className="text-center">
            <div className="text-3xl font-bold text-purple-600">{metrics.upsellOrders || 0}</div>
            <div className="text-gray-600">Доп. продаж</div>
          </div>
        </Card>
        
        <Card className="p-6">
          <div className="text-center">
            <div className="text-3xl font-bold text-orange-600">{metrics.completedOrders}</div>
            <div className="text-gray-600">Завершенных</div>
          </div>
        </Card>
        
        <Card className="p-6">
          <div className="text-center">
            <div className="text-3xl font-bold text-purple-600">{formatCurrency(metrics.totalRevenue)}</div>
            <div className="text-gray-600">Общая выручка</div>
          </div>
        </Card>
      </div>

      {/* Дополнительные метрики */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Card className="p-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-indigo-600">{formatCurrency(metrics.averageOrderValue)}</div>
            <div className="text-gray-600">Средний чек</div>
          </div>
        </Card>
        
        <Card className="p-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-teal-600">{formatPercentage(metrics.conversionRate)}</div>
            <div className="text-gray-600">Конверсия</div>
          </div>
        </Card>
      </div>

      {/* Таблица метрик */}
      <Card className="p-6 mb-8">
        <h3 className="text-lg font-semibold mb-4">Основные метрики</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Метрика
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Значение
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              <tr>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  Количество входов в бот
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {metrics.funnelMetrics?.funnel_data?.bot_entry?.unique_users || 0} уникальных / {metrics.funnelMetrics?.funnel_data?.bot_entry?.total_clicks || 0} нажатий
                </td>
              </tr>
              <tr>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  Нажали "Старт"
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {metrics.funnelMetrics?.funnel_data?.start_clicked?.unique_users || 0} уникальных / {metrics.funnelMetrics?.funnel_data?.start_clicked?.total_clicks || 0} нажатий
                </td>
              </tr>
              <tr>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  Выбор книги
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {metrics.funnelMetrics?.funnel_data?.product_selected?.unique_users || 0} уникальных / {metrics.bookSelections || 0} нажатий
                </td>
              </tr>
              <tr>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  Выбор песни
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {metrics.funnelMetrics?.funnel_data?.product_selected?.unique_users || 0} уникальных / {metrics.songSelections || 0} нажатий
                </td>
              </tr>
              <tr>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  Покупки книги
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {metrics.uniqueBookPurchasers || 0} уникальных / {metrics.bookPurchases || 0} покупок
                </td>
              </tr>
              <tr>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  Покупки песни
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {metrics.uniqueSongPurchasers || 0} уникальных / {metrics.songPurchases || 0} покупок
                </td>
              </tr>
              <tr>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  Общая стоимость заказов
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {formatCurrency((metrics.revenueMetrics?.main_purchases?.revenue || 0) + (metrics.revenueMetrics?.upsells?.revenue || 0))}
                </td>
              </tr>
              <tr>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  Дополнительные продажи
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {formatCurrency(metrics.revenueMetrics?.upsells?.revenue || 0)}
                </td>
              </tr>
              <tr>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  Создание заказов
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {metrics.funnelMetrics?.funnel_data?.order_created?.unique_users || 0} уникальных / {metrics.funnelMetrics?.funnel_data?.order_created?.total_clicks || 0} нажатий
                </td>
              </tr>
              <tr>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  Завершенные покупки
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {(metrics.uniqueBookPurchasers || 0) + (metrics.uniqueSongPurchasers || 0)} уникальных / {(metrics.bookPurchases || 0) + (metrics.songPurchases || 0)} покупок
                </td>
              </tr>
              <tr>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  Перешло во второй заказ
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {metrics.uniqueUpsellPurchasers || 0} уникальных / {metrics.upsellOrders || 0} покупок
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>

      {/* Таблица отвалов по этапам */}
      <Card className="p-6 mb-8">
        <h3 className="text-lg font-semibold mb-4">Отвалы по этапам</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Этап
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Количество отвалившихся
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Всего прошло шаг пользователей
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Процент конверсии к шагу
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {(() => {
                // Функция для расчета метрик для каждого этапа
                const calculateStepMetrics = (stepName: string, stepTitle: string, fallbackAbandonment: number) => {
                  const abandonmentData = metrics.abandonmentMetrics?.find(m => m.step_name === stepName);
                  const abandonmentCount = abandonmentData?.abandonment_count || 0;
                  
                  // Используем данные из abandonment_metrics, которые уже содержат правильные значения
                  // totalUsersReachedStep теперь показывает количество заказов, прошедших этап
                  const totalUsersReachedStep = abandonmentData?.unique_users || 0;
                  
                  // Рассчитываем процент конверсии (процент пользователей, которые НЕ отвалились)
                  const conversionRate = totalUsersReachedStep > 0 
                    ? Math.max(0, ((totalUsersReachedStep - abandonmentCount) / totalUsersReachedStep) * 100).toFixed(1)
                    : '0.0';
                  
                  return {
                    stepTitle,
                    abandonmentCount,
                    totalUsersPassedStep: totalUsersReachedStep,
                    conversionRate: `${conversionRate}%`
                  };
                };
                
                const steps = [
                  { stepName: 'product_selection', stepTitle: 'Глава 1 — Создание заказа песни/книги', fallback: 0 },
                  { stepName: 'demo_sent', stepTitle: 'Глава 2 — Демо-версия песни', fallback: 0 },
                  { stepName: 'demo_sent_book', stepTitle: 'Глава 2 — Демо-версия книги', fallback: 0 },
                  { stepName: 'payment', stepTitle: 'Глава 3 — Оплата заказа', fallback: 0 },
                  { stepName: 'prefinal_sent', stepTitle: 'Глава 4 — Предфинальная версия', fallback: 0 },
                  { stepName: 'editing', stepTitle: 'Глава 5 — Правки и доработки', fallback: 0 },
                  { stepName: 'completed', stepTitle: 'Глава 6 — Завершение проекта', fallback: 0 }
                ];
                
                return steps.map((step, index) => {
                  const metrics = calculateStepMetrics(step.stepName, step.stepTitle, step.fallback);
                  return (
                    <tr key={index}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {metrics.stepTitle}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {metrics.abandonmentCount}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {metrics.totalUsersPassedStep}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {metrics.conversionRate}
                </td>
              </tr>
                  );
                });
              })()}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Детальные метрики выручки */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Основные покупки</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">Количество</span>
              <span className="font-medium">{metrics.revenueMetrics?.main_purchases?.count || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Выручка</span>
              <span className="font-medium">{formatCurrency(metrics.revenueMetrics?.main_purchases?.revenue || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Средний чек</span>
              <span className="font-medium">{formatCurrency(metrics.revenueMetrics?.main_purchases?.avg_value || 0)}</span>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Дополнительные покупки</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">Количество</span>
              <span className="font-medium">{metrics.revenueMetrics?.upsells?.count || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Выручка</span>
              <span className="font-medium">{formatCurrency(metrics.revenueMetrics?.upsells?.revenue || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Доля от общей выручки</span>
              <span className="font-medium">
                {metrics.totalRevenue > 0 
                  ? formatPercentage((metrics.revenueMetrics?.upsells?.revenue || 0) / metrics.totalRevenue)
                  : '0%'
                }
              </span>
            </div>
          </div>
        </Card>
      </div>

      {/* Детализированные метрики по типам продуктов */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Книга печатная</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">Количество</span>
              <span className="font-medium">{metrics.detailedRevenueMetrics?.['Книга печатная']?.count || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Выручка</span>
              <span className="font-medium">{formatCurrency(metrics.detailedRevenueMetrics?.['Книга печатная']?.revenue || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Средний чек</span>
              <span className="font-medium">{formatCurrency(metrics.detailedRevenueMetrics?.['Книга печатная']?.avg_value || 0)}</span>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Книга электронная</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">Количество</span>
              <span className="font-medium">{metrics.detailedRevenueMetrics?.['Книга электронная']?.count || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Выручка</span>
              <span className="font-medium">{formatCurrency(metrics.detailedRevenueMetrics?.['Книга электронная']?.revenue || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Средний чек</span>
              <span className="font-medium">{formatCurrency(metrics.detailedRevenueMetrics?.['Книга электронная']?.avg_value || 0)}</span>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Песня</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">Количество</span>
              <span className="font-medium">{metrics.detailedRevenueMetrics?.['Песня']?.count || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Выручка</span>
              <span className="font-medium">{formatCurrency(metrics.detailedRevenueMetrics?.['Песня']?.revenue || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Средний чек</span>
              <span className="font-medium">{formatCurrency(metrics.detailedRevenueMetrics?.['Песня']?.avg_value || 0)}</span>
            </div>
          </div>
        </Card>
      </div>

      {/* Статистика по статусам */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Заказы по статусам</h3>
          <div className="space-y-2">
            {Object.entries(metrics.ordersByStatus).map(([status, count]) => (
              <div key={status} className="flex justify-between">
                <span className="text-gray-600">{translateStatus(status)}</span>
                <span className="font-medium">{count}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Заказы по продуктам</h3>
          <div className="space-y-2">
            {/* Общее количество - все заказы, выбравшие продукт (не только оплаченные) */}
            <div className="flex justify-between">
              <span className="text-gray-600 font-semibold">Книга (общее)</span>
              <span className="font-medium">{metrics.bookSelections || 0}</span>
            </div>
            <div className="flex justify-between ml-4">
              <span className="text-gray-500">— Книга печатная (оплачено)</span>
              <span className="font-medium">{metrics.detailedRevenueMetrics?.['Книга печатная']?.count || 0}</span>
            </div>
            <div className="flex justify-between ml-4">
              <span className="text-gray-500">— Книга электронная (оплачено)</span>
              <span className="font-medium">{metrics.detailedRevenueMetrics?.['Книга электронная']?.count || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 font-semibold">Песня (общее)</span>
              <span className="font-medium">{metrics.songSelections || 0}</span>
            </div>
            <div className="flex justify-between ml-4">
              <span className="text-gray-500">— Песня (оплачено)</span>
              <span className="font-medium">{metrics.detailedRevenueMetrics?.['Песня']?.count || 0}</span>
            </div>
          </div>
        </Card>
      </div>

      {/* Топ менеджеры */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Топ менеджеры</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Менеджер
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Заказов
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Выручка
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {metrics.topManagers.map((manager, index) => (
                <tr key={index}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">{manager.name}</div>
                      <div className="text-sm text-gray-500">{manager.email}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {manager.ordersCount}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatCurrency(manager.revenue)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
        </>
      )}

      {/* Вкладка Аналитика */}
      {activeTab === 'analytics' && (
        <>
          {/* Статистика */}
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{analyticsData.length}</div>
                <div className="text-sm text-gray-600">Всего заказов</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {analyticsData.filter(item => item.purchase_status === 'Оплачен').length}
                </div>
                <div className="text-sm text-gray-600">Оплаченных</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {analyticsData.filter(item => item.upsell_status === 'Оплачен').length}
                </div>
                <div className="text-sm text-gray-600">Доп. продаж</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">
                  {analyticsData.filter(item => 
                    item.progress === 'Завершено' ||  // Песни - completed
                    item.progress === 'Завершен' ||   // Книги - completed
                    item.progress === 'Готово к доставке' || 
                    item.progress === 'Финальная версия' ||
                    item.progress === 'Готово' ||     // Песни - ready
                    item.progress === 'Готов' ||      // Книги - ready
                    item.progress === 'Доставлен' ||  // delivered
                    item.progress === '✅ Финальная отправлена'  // final_sent
                  ).length}
                </div>
                <div className="text-sm text-gray-600">Завершенных</div>
              </div>
            </div>
          </div>

          {/* Поиск */}
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <div className="flex gap-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Поиск
                </label>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Поиск по пользователю, заказу, дате..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Фильтры */}
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Тип заказа
                </label>
                <select
                  value={filters.productType}
                  onChange={(e) => setFilters(prev => ({ ...prev, productType: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Все типы</option>
                  <option value="Песня">Песня</option>
                  <option value="Книга печатная">Книга печатная</option>
                  <option value="Книга электронная">Книга электронная</option>
                  <option value="Книга">Книга (общее)</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Статус покупки
                </label>
                <select
                  value={filters.purchaseStatus}
                  onChange={(e) => setFilters(prev => ({ ...prev, purchaseStatus: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Все статусы</option>
                  <option value="Оплачен">Оплачен</option>
                  <option value="Не оплачен">Не оплачен</option>
                  <option value="Ждет оплаты">Ждет оплаты</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Доп. продажа
                </label>
                <select
                  value={filters.upsellStatus}
                  onChange={(e) => setFilters(prev => ({ ...prev, upsellStatus: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Все статусы</option>
                  <option value="Оплачен">Оплачен</option>
                  <option value="Не оплачен">Не оплачен</option>
                  <option value="Ждет оплаты">Ждет оплаты</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Прогресс
                </label>
                <select
                  value={filters.progress}
                  onChange={(e) => setFilters(prev => ({ ...prev, progress: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Все этапы</option>
                  <option value="Создание персонажа">Создание персонажа</option>
                  <option value="Сбор фактов">Сбор фактов</option>
                  <option value="Демо контент">Демо контент</option>
                  <option value="Ожидает оплату">Ожидает оплату</option>
                  <option value="Оплачено">Оплачено</option>
                  <option value="Ожидает выбора сюжета">Ожидает выбора сюжета</option>
                  <option value="Сюжет выбран">Сюжет выбран</option>
                  <option value="Ожидает черновика">Ожидает черновика</option>
                  <option value="Ожидает черновика песни">Ожидает черновика песни</option>
                  <option value="Черновик отправлен">Черновик отправлен</option>
                  <option value="Ожидает отзывов">Ожидает отзывов</option>
                  <option value="Правки внесены">Правки внесены</option>
                  <option value="Ожидает выбора обложки">Ожидает выбора обложки</option>
                  <option value="Обложка выбрана">Обложка выбрана</option>
                  <option value="Предфинальная версия отправлена">Предфинальная версия отправлена</option>
                  <option value="Ожидает финальной версии">Ожидает финальной версии</option>
                  <option value="Финальная песня отправлена">Финальная песня отправлена</option>
                  <option value="Финальная книга отправлена">Финальная книга отправлена</option>
                  <option value="Готово к доставке">Готово к доставке</option>
                  <option value="Ожидает доставки">Ожидает доставки</option>
                  <option value="Доплата в обработке">Доплата в обработке</option>
                  <option value="Готово">Готово</option>
                  <option value="Завершено">Завершено</option>
                  {/* Дополненные статусы из аналитики для точного совпадения с колонкой "Прогресс (остановка)" */}
                  <option value="Создан">Создан</option>
                  <option value="Выбран продукт">Выбран продукт</option>
                  <option value="Выбран пол">Выбран пол</option>
                  <option value="Выбран получатель">Выбран получатель</option>
                  <option value="Введено имя получателя">Введено имя получателя</option>
                  <option value="Введено имя">Введено имя</option>
                  <option value="Описание персонажа">Описание персонажа</option>
                  <option value="Указан повод подарка">Указан повод подарка</option>
                  <option value="Выбран стиль">Выбран стиль</option>
                  <option value="Создан персонаж">Создан персонаж</option>
                  <option value="Загружены фото">Загружены фото</option>
                  <option value="Загружены фото основного героя">Загружены фото основного героя</option>
                  <option value="Введено имя второго героя">Введено имя второго героя</option>
                  <option value="Описание второго персонажа">Описание второго персонажа</option>
                  <option value="Загружены фото второго героя">Загружены фото второго героя</option>
                  <option value="Загружено совместное фото">Загружено совместное фото</option>
                  <option value="Выбор голоса">Выбор голоса</option>
                  <option value="Ожидает менеджера">Ожидает менеджера</option>
                  <option value="✅ Отправлено демо">✅ Отправлено демо</option>
                  <option value="✅ Отправлены варианты сюжета">✅ Отправлены варианты сюжета</option>
                  <option value="Ожидает вариантов сюжета">Ожидает вариантов сюжета</option>
                  <option value="Страницы выбраны">Страницы выбраны</option>
                  <option value="Завершены вопросы">Завершены вопросы</option>
                  <option value="Ожидает отзыва">Ожидает отзыва</option>
                  <option value="Обработан отзыв">Обработан отзыв</option>
                  <option value="Внесение правок">Внесение правок</option>
                  <option value="✅ Предфинальная версия отправлена">✅ Предфинальная версия отправлена</option>
                  <option value="Ожидает финала">Ожидает финала</option>
                  <option value="✅ Финальная отправлена">✅ Финальная отправлена</option>
                  <option value="Готов">Готов</option>
                  <option value="Отправка печатной версии">Отправка печатной версии</option>
                  <option value="Доставлен">Доставлен</option>
                  <option value="Оплачен">Оплачен</option>
                  <option value="Ожидает оплаты">Ожидает оплаты</option>
                  <option value="Создан платеж">Создан платеж</option>
                  <option value="Ожидание доплаты">Ожидание доплаты</option>
                  <option value="Доплата получена">Доплата получена</option>
                  <option value="Доплата за печатную версию оплачена">Доплата за печатную версию оплачена</option>
                  <option value="Завершен">Завершен</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  UTM Source
                </label>
                <select
                  value={filters.utmSource}
                  onChange={(e) => setFilters(prev => ({ ...prev, utmSource: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Все источники</option>
                  {utmFilters.utm_sources.map((source) => (
                    <option key={source} value={source}>{source}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  UTM Medium
                </label>
                <select
                  value={filters.utmMedium}
                  onChange={(e) => setFilters(prev => ({ ...prev, utmMedium: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Все каналы</option>
                  {utmFilters.utm_mediums.map((medium) => (
                    <option key={medium} value={medium}>{medium}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  UTM Campaign
                </label>
                <select
                  value={filters.utmCampaign}
                  onChange={(e) => setFilters(prev => ({ ...prev, utmCampaign: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Все кампании</option>
                  {utmFilters.utm_campaigns.map((campaign) => (
                    <option key={campaign} value={campaign}>{campaign}</option>
                  ))}
                </select>
              </div>
              
              <div className="flex items-end">
                <button
                  onClick={resetFilters}
                  className="w-full bg-gray-500 text-white px-4 py-2 rounded-md hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500"
                >
                  Сбросить
                </button>
              </div>
            </div>
          </div>

          {/* Кнопки экспорта */}
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <div className="flex gap-4">
              <button
                onClick={() => exportData('csv')}
                className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
              >
                📊 Экспорт в CSV
              </button>
              <button
                onClick={() => exportData('excel')}
                className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                📈 Экспорт в Excel
              </button>
            </div>
          </div>

          {/* Таблица аналитики */}
          <div className="bg-white rounded-lg shadow-sm overflow-hidden">
            {analyticsLoading ? (
              <div className="p-8 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                <p className="mt-2 text-gray-600">Загрузка данных...</p>
              </div>
            ) : analyticsError ? (
              <div className="p-8 text-center">
                <div className="text-red-600 mb-2">❌ Ошибка загрузки данных</div>
                <p className="text-gray-600">{analyticsError}</p>
                <button
                  onClick={fetchAnalytics}
                  className="mt-4 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
                >
                  Попробовать снова
                </button>
              </div>
            ) : analyticsData.length === 0 ? (
              <div className="p-8 text-center">
                <div className="text-gray-600 mb-2">📊 Нет данных</div>
                <p className="text-gray-500">За выбранный период заказы не найдены</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        UTM Source
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        UTM Medium
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        UTM Campaign
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        № заказа
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Username
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Тип заказа
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Дата создания
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Статус покупки
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Доп. продажа
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Прогресс (остановка)
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {analyticsData.map((item, index) => (
                      <tr key={index} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {item.utm_source}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {item.utm_medium}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {item.utm_campaign}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600">
                          {item.order_id}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {item.username}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {item.product_type}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {formatDateTime(item.created_at)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(item.purchase_status)}`}>
                            {item.purchase_status}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(item.upsell_status)}`}>
                            {item.upsell_status}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getProgressColor(item.progress)}`}>
                            {item.progress}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
