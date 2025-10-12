// Типы для результата валидации
export interface ValidationResult {
  isValid: boolean;
  error: string;
}

// Функция валидации email
export const validateEmail = (email: string): ValidationResult => {
  if (!email) {
    return { isValid: false, error: "Email обязателен" };
  }
  
  // Приводим к нижнему регистру и убираем пробелы
  const cleanEmail = email.toLowerCase().trim();
  
  // Проверяем базовый формат email
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(cleanEmail)) {
    return { isValid: false, error: "Неверный формат email" };
  }
  
  // Проверяем длину
  if (cleanEmail.length > 254) {
    return { isValid: false, error: "Email слишком длинный (максимум 254 символа)" };
  }
  
  // Проверяем, что домен не слишком короткий
  const parts = cleanEmail.split('@');
  if (parts[1].length < 3) {
    return { isValid: false, error: "Неверный домен email" };
  }
  
  // Проверяем, что нет двойных точек
  if (cleanEmail.includes('..')) {
    return { isValid: false, error: "Email не может содержать двойные точки" };
  }
  
  return { isValid: true, error: "" };
};

// Функция валидации номера телефона
export const validatePhone = (phone: string): ValidationResult => {
  if (!phone) {
    return { isValid: false, error: "Номер телефона обязателен" };
  }
  
  // Убираем все пробелы, скобки, дефисы и плюсы для проверки
  const cleanPhone = phone.replace(/[\s\(\)\-\+]/g, '');
  
  // Проверяем, что остались только цифры
  if (!/^\d+$/.test(cleanPhone)) {
    return { isValid: false, error: "Номер телефона должен содержать только цифры, пробелы, скобки и дефисы" };
  }
  
  // Проверяем длину (для России: 10-15 цифр)
  if (cleanPhone.length < 10 || cleanPhone.length > 15) {
    return { isValid: false, error: "Номер телефона должен содержать от 10 до 15 цифр" };
  }
  
  // Проверяем российские номера
  if (cleanPhone.length === 11) {
    // Номер с кодом страны +7 или 8
    if (!['7', '8'].includes(cleanPhone[0])) {
      return { isValid: false, error: "Номер должен начинаться с 7 или 8 (код России)" };
    }
    
    // Проверяем код оператора (второй символ должен быть 9)
    if (cleanPhone[1] !== '9') {
      return { isValid: false, error: "Неверный код оператора (должен начинаться с 9)" };
    }
  } else if (cleanPhone.length === 10) {
    // Номер без кода страны, должен начинаться с 9
    if (cleanPhone[0] !== '9') {
      return { isValid: false, error: "Номер должен начинаться с 9 (код оператора)" };
    }
  }
  
  return { isValid: true, error: "" };
};

// Функция для очистки email (приведение к нижнему регистру и удаление пробелов)
export const cleanEmail = (email: string): string => {
  return email.toLowerCase().trim();
};

// Функция для форматирования номера телефона (приведение к стандартному виду)
export const formatPhone = (phone: string): string => {
  const cleanPhone = phone.replace(/[\s\(\)\-\+]/g, '');
  
  if (cleanPhone.length === 11 && cleanPhone[0] === '8') {
    // Заменяем 8 на +7
    return `+7 (${cleanPhone.slice(1, 4)}) ${cleanPhone.slice(4, 7)}-${cleanPhone.slice(7, 9)}-${cleanPhone.slice(9)}`;
  } else if (cleanPhone.length === 11 && cleanPhone[0] === '7') {
    // Добавляем +
    return `+7 (${cleanPhone.slice(1, 4)}) ${cleanPhone.slice(4, 7)}-${cleanPhone.slice(7, 9)}-${cleanPhone.slice(9)}`;
  } else if (cleanPhone.length === 10) {
    // Добавляем +7
    return `+7 (${cleanPhone.slice(0, 3)}) ${cleanPhone.slice(3, 6)}-${cleanPhone.slice(6, 8)}-${cleanPhone.slice(8)}`;
  }
  
  // Возвращаем как есть, если формат неизвестен
  return phone;
};

// Примеры использования:
/*
const emailResult = validateEmail("user@example.com");
if (!emailResult.isValid) {
  console.error(emailResult.error);
}

const phoneResult = validatePhone("+7 (999) 123-45-67");
if (!phoneResult.isValid) {
  console.error(phoneResult.error);
}

const formattedPhone = formatPhone("89991234567"); // "+7 (999) 123-45-67"
const cleanedEmail = cleanEmail("  User@EXAMPLE.COM  "); // "user@example.com"
*/



