// Утилиты для работы с московским временем

export const formatDateTime = (dateString: string): string => {
  if (!dateString) return 'неизвестно';
  
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'неизвестно';
    
    // Форматируем в московском времени
    return date.toLocaleString('ru-RU', {
      timeZone: 'Europe/Moscow',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  } catch (error) {
    console.error('Ошибка форматирования даты:', error);
    return 'неизвестно';
  }
};

export const formatDate = (dateString: string): string => {
  if (!dateString) return 'неизвестно';
  
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'неизвестно';
    
    // Форматируем только дату в московском времени
    return date.toLocaleDateString('ru-RU', {
      timeZone: 'Europe/Moscow',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
  } catch (error) {
    console.error('Ошибка форматирования даты:', error);
    return 'неизвестно';
  }
};

export const getTimeSince = (dateString: string): string => {
  if (!dateString) return "неизвестно";
  
  try {
    const now = new Date();
    const date = new Date(dateString);
    
    if (isNaN(date.getTime())) return "неизвестно";
    
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000); // seconds
    
    if (diff < 60) return `${diff} сек назад`;
    if (diff < 3600) return `${Math.floor(diff / 60)} мин назад`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} ч назад`;
    if (diff < 2592000) return `${Math.floor(diff / 86400)} дн назад`;
    if (diff < 31536000) return `${Math.floor(diff / 2592000)} мес назад`;
    return `${Math.floor(diff / 31536000)} г назад`;
  } catch (error) {
    console.error('Ошибка вычисления времени:', error);
    return "неизвестно";
  }
};

export const getMSKDateRange = () => {
  const now = new Date();
  const mskNow = new Date(now.toLocaleString("en-US", {timeZone: "Europe/Moscow"}));
  
  const startOfMonth = new Date(mskNow.getFullYear(), mskNow.getMonth(), 1);
  const endOfMonth = new Date(mskNow.getFullYear(), mskNow.getMonth() + 1, 0);
  
  return {
    start: startOfMonth.toISOString().split('T')[0],
    end: endOfMonth.toISOString().split('T')[0]
  };
};

export const getMSKToday = (): string => {
  const now = new Date();
  const mskNow = new Date(now.toLocaleString("en-US", {timeZone: "Europe/Moscow"}));
  return mskNow.toISOString().split('T')[0];
};















