import React, { useEffect, useState } from "react";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";

interface ContentStep {
  id: number;
  step_key: string;
  step_name: string;
  content_type: string;
  content: string;
  materials: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface OrderSummaryTemplate {
  // Названия полей для книги
  gender_label: string;
  recipient_name_label: string;
  gift_reason_label: string;
  relation_label: string;
  style_label: string;
  format_label: string;
  sender_name_label: string;
  
  // Названия полей для песни
  song_gender_label: string;
  song_recipient_name_label: string;
  song_gift_reason_label: string;
  song_relation_label: string;
  song_style_label: string;
  song_voice_label: string;
}

interface SongQuiz {
  id: number;
  relation_key: string;
  author_gender: string;
  title: string;
  intro: string;
  phrases_hint: string;
  questions_json: string;
  outro: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export const ContentPage: React.FC = () => {
  const [contentSteps, setContentSteps] = useState<ContentStep[]>([]);
  const [botMessages, setBotMessages] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingStep, setEditingStep] = useState<ContentStep | null>(null);
  const [editingMessage, setEditingMessage] = useState<any | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [userPermissions, setUserPermissions] = useState<{is_super_admin: boolean} | null>(null);
  const [activeTab, setActiveTab] = useState<'book-path' | 'song-path' | 'common-messages' | 'song-quiz'>('book-path');
  const [songQuiz, setSongQuiz] = useState<SongQuiz[]>([]);
  const [editingQuiz, setEditingQuiz] = useState<SongQuiz | null>(null);
  const [editingFullText, setEditingFullText] = useState<string>('');
  const [relationFilter, setRelationFilter] = useState<string>('');
  const [showCreateQuizForm, setShowCreateQuizForm] = useState(false);

  // Функция для перевода типов связей на русский
  const getRelationDisplayName = (relationKey: string): string => {
    const relationMap: { [key: string]: string } = {
      'husband': 'Мужу',
      'wife': 'Жене', 
      'mom': 'Маме',
      'dad': 'Папе',
      'grandma': 'Бабушке',
      'grandpa': 'Дедушке',
      'friend': 'Подруге',
      'sister': 'Сестре',
      'brother': 'Брату',
      'son': 'Сыну',
      'daughter': 'Дочери',
      'boyfriend': 'Парню'
    };
    return relationMap[relationKey] || relationKey;
  };

  // Функция для получения полного текста квиза
  const getFullQuizText = (quiz: SongQuiz): string => {
    let fullText = '';
    
    // Добавляем вступительное сообщение
    if (quiz.intro) fullText += quiz.intro;
    
    // Добавляем подсказку для фраз
    if (quiz.phrases_hint) {
      if (fullText && !fullText.endsWith('\n')) fullText += '\n';
      fullText += 'Словосочетания: "' + quiz.phrases_hint + '"';
    }
    
    // Добавляем вопросы
    try {
      const questions = JSON.parse(quiz.questions_json || '[]');
      if (questions.length > 0) {
        if (fullText && !fullText.endsWith('\n')) fullText += '\n';
        questions.forEach((question: string, index: number) => {
          fullText += `${index + 1}.${question}\n`;
        });
      }
    } catch (e) {
      console.warn("Ошибка парсинга вопросов:", e);
    }
    
    // Добавляем заключительную часть
    if (quiz.outro) {
      if (fullText && !fullText.endsWith('\n')) fullText += '\n';
      fullText += quiz.outro;
    }
    
    return fullText;
  };

  // Функция для разделения полного текста обратно на части
  const parseFullText = (fullText: string) => {
    let intro = '';
    let phrases_hint = '';
    let outro = '';
    let questions: string[] = [];
    
    // Разбиваем текст на строки
    const lines = fullText.split('\n');
    let currentSection = 'intro';
    let introLines: string[] = [];
    let outroLines: string[] = [];
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]; // Сохраняем оригинальную строку с форматированием
      const trimmedLine = line.trim();
      
      // Проверяем, начинается ли строка со "Словосочетания:"
      if (trimmedLine.startsWith('Словосочетания:')) {
        currentSection = 'phrases';
        // Извлекаем текст после двоеточия и кавычек
        const match = trimmedLine.match(/Словосочетания:\s*"([^"]*)/);
        if (match) {
          phrases_hint = match[1];
        }
        continue;
      }
      
      // Проверяем, является ли строка вопросом (начинается с цифры и точки)
      if (/^\d+\./.test(trimmedLine)) {
        currentSection = 'questions';
        questions.push(trimmedLine.replace(/^\d+\./, '').trim());
        continue;
      }
      
      // Если мы в секции вопросов и встретили не-вопрос, переходим к outro
      if (currentSection === 'questions' && !/^\d+\./.test(trimmedLine)) {
        currentSection = 'outro';
      }
      
      // Добавляем строки в соответствующие секции (включая пустые строки)
      if (currentSection === 'intro') {
        introLines.push(line);
      } else if (currentSection === 'outro') {
        outroLines.push(line);
      }
    }
    
    // Соединяем строки, сохраняя все переносы строк
    intro = introLines.join('\n');
    outro = outroLines.join('\n');
    
    return {
      intro,
      phrases_hint,
      outro,
      questions_json: JSON.stringify(questions)
    };
  };
  const [newQuiz, setNewQuiz] = useState({
    relation_key: '',
    author_gender: 'female',
    title: '',
    intro: '',
    phrases_hint: '',
    questions_json: '[]',
    outro: '',
    is_active: true
  });
  const [filterContext, setFilterContext] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Состояния для редактирования сводки заказа
  const [orderSummary, setOrderSummary] = useState<OrderSummaryTemplate | null>(null);
  const [editingSummary, setEditingSummary] = useState<OrderSummaryTemplate>({
    gender_label: "Пол отправителя",
    recipient_name_label: "Имя получателя",
    gift_reason_label: "Повод",
    relation_label: "Отношение",
    style_label: "Стиль",
    format_label: "Формат",
    sender_name_label: "От кого",
    song_gender_label: "Пол отправителя",
    song_recipient_name_label: "Имя получателя",
    song_gift_reason_label: "Повод",
    song_relation_label: "Отношение",
    song_style_label: "Стиль",
    song_voice_label: "Голос"
  });
  const [isEditingSummary, setIsEditingSummary] = useState(false);
  const [savingSummary, setSavingSummary] = useState(false);
  const [summarySuccess, setSummarySuccess] = useState("");
  const [summaryError, setSummaryError] = useState("");

  const [newStep, setNewStep] = useState({
    step_key: "",
    step_name: "",
    content_type: "text",
    content: "",
    materials: "",
    is_active: true
  });

  useEffect(() => {
    fetchContentSteps();
    fetchBotMessages();
    fetchUserPermissions();
    fetchOrderSummary();
    fetchSongQuiz();
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

  const fetchContentSteps = async () => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch("/admin/content", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setContentSteps(data);
      } else {
        setError("Ошибка загрузки контента");
      }
    } catch (err) {
      setError("Ошибка загрузки контента");
    } finally {
      setLoading(false);
    }
  };

  const fetchBotMessages = async () => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch("/admin/bot-messages", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setBotMessages(data);
      } else {
        console.error("Ошибка загрузки сообщений бота");
      }
    } catch (err) {
      console.error("Ошибка загрузки сообщений бота:", err);
    }
  };

  const fetchSongQuiz = async () => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch("/admin/song-quiz", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        console.log("🔍 fetchSongQuiz: Загружены квизы:", data.length, "штук");
        // Логируем каждый квиз для отладки
        data.forEach((quiz: any, index: number) => {
          console.log(`🔍 fetchSongQuiz: Квиз ${index} (ID: ${quiz.id}):`, {
            intro: JSON.stringify(quiz.intro),
            outro: JSON.stringify(quiz.outro),
            phrases_hint: quiz.phrases_hint
          });
        });
        console.log("🔍 fetchSongQuiz: Устанавливаем новое состояние...");
        setSongQuiz(data);
        console.log("🔍 fetchSongQuiz: Состояние установлено");
      }
    } catch (err) {
      console.error("Ошибка загрузки квиза песни:", err);
    }
  };

  const createAllQuizTypes = async () => {
    setCreating(true);
    setError("");
    
    const relationMap = {
      'Любимому': 'husband',
      'Любимой': 'wife', 
      'Маме': 'mom',
      'Папе': 'dad',
      'Бабушке': 'grandma',
      'Дедушке': 'grandpa',
      'Подруге': 'friend',
      'Сестре': 'sister',
      'Брату': 'brother',
      'Сыну': 'son',
      'Дочери': 'daughter'
    };

    let createdCount = 0;
    let errorCount = 0;

    try {
      const token = localStorage.getItem("token");
      
      for (const [relationName, relationKey] of Object.entries(relationMap)) {
        const quizData = {
          relation_key: relationKey,
          author_gender: 'female', // По умолчанию женский пол
          title: `Квиз для ${relationName}`,
          intro: `Привет! Давайте создадим персональную песню для ${relationName.toLowerCase()}.`,
          phrases_hint: 'Вспомните особенные моменты, которые вас связывают.',
          questions_json: '[]',
          outro: 'Спасибо за ответы! Мы создадим уникальную песню специально для вас.',
          is_active: true
        };

        try {
          const response = await fetch("/admin/song-quiz", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(quizData),
          });

          if (response.ok) {
            createdCount++;
          } else {
            errorCount++;
          }
        } catch (err) {
          errorCount++;
        }
      }

      // Обновляем список квизов
      await fetchSongQuiz();
      
      if (createdCount > 0) {
        setSuccessMessage(`✅ Создано ${createdCount} квизов! ${errorCount > 0 ? `Ошибок: ${errorCount}` : ''}`);
        setTimeout(() => setSuccessMessage(""), 5000);
      } else {
        setError("Не удалось создать ни одного квиза");
      }
    } catch (err) {
      setError("Ошибка при создании квизов");
    } finally {
      setCreating(false);
    }
  };

  const handleCreateQuiz = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newQuiz.relation_key || !newQuiz.title) {
      setError("Заполните обязательные поля: тип связи и заголовок");
      return;
    }

    setCreating(true);
    try {
      const token = localStorage.getItem("token");
      const response = await fetch("/admin/song-quiz", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(newQuiz),
      });

      if (response.ok) {
        setShowCreateQuizForm(false);
        setNewQuiz({
          relation_key: '',
          author_gender: 'female',
          title: '',
          intro: '',
          phrases_hint: '',
          questions_json: '[]',
          outro: '',
          is_active: true
        });
        fetchSongQuiz();
        setSuccessMessage("✅ Квиз песни успешно создан!");
        setTimeout(() => setSuccessMessage(""), 3000);
      } else {
        setError("Ошибка создания квиза песни");
      }
    } catch (err) {
      setError("Ошибка создания квиза песни");
    } finally {
      setCreating(false);
    }
  };

  const handleUpdateQuiz = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingQuiz) return;

    setSaving(true);
    try {
      const token = localStorage.getItem("token");
      
      // Разделяем полный текст обратно на части для API
      const textParts = parseFullText(editingFullText);
      const updatedQuiz = {
        ...editingQuiz,
        intro: textParts.intro,
        phrases_hint: textParts.phrases_hint,
        outro: textParts.outro,
        questions_json: textParts.questions_json
      };

      console.log("🔍 Исходный текст для парсинга:", editingFullText);
      console.log("🔍 Исходный текст (с символами):", JSON.stringify(editingFullText));
      console.log("🔍 Результат парсинга:", textParts);
      console.log("🔍 Intro после парсинга:", JSON.stringify(textParts.intro));
      console.log("🔍 Outro после парсинга:", JSON.stringify(textParts.outro));
      console.log("🔍 Отправляем обновленный квиз:", updatedQuiz);
      console.log("🔍 URL:", `/admin/song-quiz/${editingQuiz.id}`);
      console.log("🔍 ID квиза:", editingQuiz.id);

      const response = await fetch(`/admin/song-quiz/${editingQuiz.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(updatedQuiz),
      });

      console.log("🔍 Ответ сервера:", response.status, response.statusText);

      if (response.ok) {
        const result = await response.json();
        console.log("✅ Квиз успешно обновлен:", result);
        console.log("🔍 Обновленный квиз intro:", JSON.stringify(result.intro));
        console.log("🔍 Обновленный квиз outro:", JSON.stringify(result.outro));
        setEditingQuiz(null);
        setEditingFullText('');
        console.log("🔍 Вызываем fetchSongQuiz для перезагрузки данных...");
        await fetchSongQuiz();
        console.log("🔍 fetchSongQuiz завершен");
        
        // Обновляем конкретный квиз в состоянии
        console.log("🔍 Обновляем конкретный квиз в состоянии...");
        setSongQuiz(prevQuiz => {
          const updatedQuiz = prevQuiz.map(quiz => 
            quiz.id === editingQuiz.id 
              ? { ...quiz, intro: result.intro, outro: result.outro, phrases_hint: result.phrases_hint, questions_json: result.questions_json }
              : quiz
          );
          console.log("🔍 Обновленное состояние квизов:", updatedQuiz.length);
          return updatedQuiz;
        });
        
        setSuccessMessage("✅ Квиз обновлен!");
        setTimeout(() => setSuccessMessage(""), 3000);
      } else {
        const errorText = await response.text();
        console.error("❌ Ошибка обновления квиза:", response.status, errorText);
        setError(`Ошибка обновления квиза: ${response.status} ${errorText}`);
      }
    } catch (err) {
      console.error("❌ Исключение при обновлении квиза:", err);
      setError("Ошибка обновления квиза");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteQuiz = async (quizId: number) => {
    if (!window.confirm("Вы уверены, что хотите удалить этот квиз?")) return;

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/song-quiz/${quizId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        fetchSongQuiz();
        setSuccessMessage("✅ Квиз удален!");
        setTimeout(() => setSuccessMessage(""), 3000);
      } else {
        setError("Ошибка удаления квиза");
      }
    } catch (err) {
      setError("Ошибка удаления квиза");
    }
  };

  const handleCreateStep = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newStep.step_key || !newStep.step_name || !newStep.content) {
      setError("Заполните все обязательные поля");
      return;
    }

    setCreating(true);
    try {
      const token = localStorage.getItem("token");
      const response = await fetch("/admin/content", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(newStep),
      });

      if (response.ok) {
        setShowCreateForm(false);
        setNewStep({
          step_key: "",
          step_name: "",
          content_type: "text",
          content: "",
          materials: "",
          is_active: true
        });
        fetchContentSteps();
      } else {
        setError("Ошибка создания шага контента");
      }
    } catch (err) {
      setError("Ошибка создания шага контента");
    } finally {
      setCreating(false);
    }
  };

  const handleUpdateStep = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingStep) return;

    setSaving(true);
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/content/${editingStep.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(editingStep),
      });

      if (response.ok) {
        setEditingStep(null);
        fetchContentSteps();
      } else {
        setError("Ошибка обновления шага контента");
      }
    } catch (err) {
      setError("Ошибка обновления шага контента");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteStep = async (stepId: number) => {
    if (!window.confirm("Вы уверены, что хотите удалить этот шаг контента?")) {
      return;
    }

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/content/${stepId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        fetchContentSteps();
      } else {
        setError("Ошибка удаления шага контента");
      }
    } catch (err) {
      setError("Ошибка удаления шага контента");
    }
  };

  const handleToggleActive = async (step: ContentStep) => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/content/${step.id}/toggle`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ is_active: !step.is_active }),
      });

      if (response.ok) {
        fetchContentSteps();
      } else {
        setError("Ошибка изменения статуса");
      }
    } catch (err) {
      setError("Ошибка изменения статуса");
    }
  };

  const handleUpdateBotMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingMessage) return;

    setSaving(true);
    setError(""); // Очищаем предыдущие ошибки
    setSuccessMessage(""); // Очищаем предыдущие сообщения об успехе
    
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/bot-messages/${editingMessage.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          content: editingMessage.content,
          is_active: editingMessage.is_active
        }),
      });

      if (response.ok) {
        // Обновляем сообщение в локальном состоянии
        setBotMessages(prevMessages => 
          prevMessages.map(msg => 
            msg.id === editingMessage.id 
              ? { ...msg, content: editingMessage.content, is_active: editingMessage.is_active, updated_at: new Date().toISOString() }
              : msg
          )
        );
        
        setEditingMessage(null);
        setSuccessMessage("✅ Сообщение успешно обновлено!");
        console.log("✅ Сообщение успешно обновлено");
        
        // Автоматически скрываем сообщение об успехе через 3 секунды
        setTimeout(() => setSuccessMessage(""), 3000);
      } else {
        const errorData = await response.json();
        setError(`Ошибка обновления сообщения бота: ${errorData.detail || 'Неизвестная ошибка'}`);
      }
    } catch (err) {
      console.error("Ошибка обновления сообщения:", err);
      setError("Ошибка обновления сообщения бота");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteBotMessage = async (messageId: number) => {
    if (!window.confirm("Вы уверены, что хотите удалить это сообщение? Это действие нельзя отменить.")) {
      return;
    }

    setSaving(true);
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/admin/bot-messages/${messageId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        fetchBotMessages();
      } else {
        setError("Ошибка удаления сообщения бота");
      }
    } catch (err) {
      setError("Ошибка удаления сообщения бота");
    } finally {
      setSaving(false);
    }
  };

  // Функции для работы со сводкой заказа
  const fetchOrderSummary = async () => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch("/admin/order-summary-template", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setOrderSummary(data);
      }
    } catch (err) {
      console.error("Ошибка загрузки шаблона сводки заказа:", err);
    }
  };

  const startEditingSummary = () => {
    setEditingSummary({
      gender_label: orderSummary?.gender_label || "Пол отправителя",
      recipient_name_label: orderSummary?.recipient_name_label || "Имя получателя",
      gift_reason_label: orderSummary?.gift_reason_label || "Повод",
      relation_label: orderSummary?.relation_label || "Отношение",
      style_label: orderSummary?.style_label || "Стиль",
      format_label: orderSummary?.format_label || "Формат",
      sender_name_label: orderSummary?.sender_name_label || "От кого",
      song_gender_label: orderSummary?.song_gender_label || "Пол отправителя",
      song_recipient_name_label: orderSummary?.song_recipient_name_label || "Имя получателя",
      song_gift_reason_label: orderSummary?.song_gift_reason_label || "Повод",
      song_relation_label: orderSummary?.song_relation_label || "Отношение",
      song_style_label: orderSummary?.song_style_label || "Стиль",
      song_voice_label: orderSummary?.song_voice_label || "Голос"
    });
    setIsEditingSummary(true);
    setSummarySuccess("");
    setSummaryError("");
  };

  const cancelEditingSummary = () => {
    setIsEditingSummary(false);
    setEditingSummary({
      gender_label: "Пол отправителя",
      recipient_name_label: "Имя получателя",
      gift_reason_label: "Повод",
      relation_label: "Отношение",
      style_label: "Стиль",
      format_label: "Формат",
      sender_name_label: "От кого",
      song_gender_label: "Пол отправителя",
      song_recipient_name_label: "Имя получателя",
      song_gift_reason_label: "Повод",
      song_relation_label: "Отношение",
      song_style_label: "Стиль",
      song_voice_label: "Голос"
    });
    setSummarySuccess("");
    setSummaryError("");
  };

  const saveSummaryChanges = async () => {
    setSavingSummary(true);
    setSummaryError("");
    
    try {
      const token = localStorage.getItem("token");
      const response = await fetch("/admin/order-summary-template", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(editingSummary),
      });
      
      if (!response.ok) {
        throw new Error("Ошибка сохранения изменений");
      }
      
      setSummarySuccess("✅ Изменения сохранены успешно!");
      setIsEditingSummary(false);
      
      // Обновляем данные
      await fetchOrderSummary();
      
      // Автоматически скрываем сообщение об успехе через 3 секунды
      setTimeout(() => setSummarySuccess(""), 3000);
      
    } catch (error: any) {
      setSummaryError(`Ошибка: ${error.message}`);
    } finally {
      setSavingSummary(false);
    }
  };

  const getContentTypeLabel = (type: string) => {
    switch (type) {
      case "text": return "Текст";
      case "image": return "Изображение";
      case "video": return "Видео";
      case "audio": return "Аудио";
      case "file": return "Файл";
      default: return type;
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-center">Загрузка контента...</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-2xl font-bold text-gray-900">Управление контентом</h1>
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}
        
        {successMessage && (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
            {successMessage}
          </div>
        )}
        
        {!userPermissions?.is_super_admin && (
          <div className="bg-blue-900 border border-blue-500 text-white px-4 py-3 rounded mb-4">
            <strong>ℹ️ Информация:</strong> Вы можете только просматривать контент. Для редактирования контента требуются права главного администратора.
          </div>
        )}

        {/* Вкладки */}
        <div className="flex space-x-1 mb-6">
          <button
            onClick={() => setActiveTab('book-path')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'book-path'
                ? 'bg-indigo-600 text-white shadow-lg'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600 hover:text-white'
            }`}
          >
            📖 Путь книги ({botMessages.filter(message => 
              ['product', 'relation', 'hero', 'photo', 'question', 'payment', 'page_selection', 'demo', 'draft', 'cover', 'delivery', 'completion'].includes(message.context)
            ).length})
          </button>
          <button
            onClick={() => setActiveTab('song-path')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'song-path'
                ? 'bg-indigo-600 text-white shadow-lg'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600 hover:text-white'
            }`}
          >
            🎵 Путь песни ({botMessages.filter(message => 
              message.context === 'song'
            ).length})
          </button>
          <button
            onClick={() => setActiveTab('common-messages')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'common-messages'
                ? 'bg-indigo-600 text-white shadow-lg'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600 hover:text-white'
            }`}
          >
            🔧 Общие сообщения ({botMessages.filter(message => 
              ['welcome', 'registration', 'common', 'error', 'info', 'reminder', 'button'].includes(message.context)
            ).length})
          </button>
          <button
            onClick={() => setActiveTab('song-quiz')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'song-quiz'
                ? 'bg-indigo-600 text-white shadow-lg'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600 hover:text-white'
            }`}
          >
            📝 Квиз песни ({songQuiz.length})
          </button>
        </div>

        {/* Фильтры для сообщений бота */}
        {(activeTab === 'book-path' || activeTab === 'song-path' || activeTab === 'common-messages') && (
          <div className="flex flex-wrap gap-3 mb-4">
            <select
              className="filter-input border rounded bg-gray-800 text-white"
              value={activeTab}
              onChange={(e) => setActiveTab(e.target.value as any)}
            >
              <option value="book-path">Путь книги</option>
              <option value="song-path">Путь песни</option>
              <option value="common-messages">Общие сообщения</option>
            </select>
            <select
              className="filter-input border rounded bg-gray-800 text-white"
              value={filterContext}
              onChange={(e) => setFilterContext(e.target.value)}
            >
              <option value="all">Все контексты</option>
              <option value="book">Книга</option>
              <option value="song">Песня</option>
              <option value="common">Общие</option>
            </select>
            <input
              type="text"
              placeholder="Поиск по названию или ключу..."
              className="filter-input border rounded bg-gray-800 text-white"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        )}

        {/* Секция квизов песни */}
        {activeTab === 'song-quiz' && (
          <div className="space-y-4">

            {/* Фильтр по типу связи */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Фильтр по типу связи:
              </label>
              <select
                value={relationFilter}
                onChange={(e) => setRelationFilter(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-md bg-white text-gray-900"
              >
                <option value="">Все типы связей</option>
                {Array.from(new Set(songQuiz.map(q => q.relation_key))).map(relation => (
                  <option key={relation} value={relation}>{getRelationDisplayName(relation)}</option>
                ))}
              </select>
            </div>

            {/* Список квизов в виде карточек */}
            <div className="grid gap-4">
              {songQuiz
                .filter(quiz => !relationFilter || quiz.relation_key === relationFilter)
                .map((quiz) => (
                <Card key={quiz.id} className="p-6">
                  {editingQuiz?.id === quiz.id ? (
                    /* Форма редактирования */
                    <form onSubmit={handleUpdateQuiz} className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Тип связи
                          </label>
                          <input
                            type="text"
                            value={editingQuiz.relation_key}
                            onChange={(e) => setEditingQuiz({...editingQuiz, relation_key: e.target.value})}
                            className="w-full p-2 border border-gray-300 rounded-md"
                            required
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Пол автора
                          </label>
                          <select
                            value={editingQuiz.author_gender}
                            onChange={(e) => setEditingQuiz({...editingQuiz, author_gender: e.target.value})}
                            className="w-full p-2 border border-gray-300 rounded-md"
                          >
                            <option value="female">Женский</option>
                            <option value="male">Мужской</option>
                          </select>
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Заголовок
                        </label>
                        <input
                          type="text"
                          value={editingQuiz.title}
                          onChange={(e) => setEditingQuiz({...editingQuiz, title: e.target.value})}
                          className="w-full p-2 border border-gray-300 rounded-md"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Сообщение квиза
                        </label>
                        <textarea
                          value={editingFullText}
                          onChange={(e) => setEditingFullText(e.target.value)}
                          className="w-full p-3 border border-gray-300 rounded-md h-40"
                          placeholder="Введите полный текст сообщения квиза..."
                          required
                        />
                      </div>

                      <div className="flex items-center">
                        <input
                          type="checkbox"
                          id={`active-${quiz.id}`}
                          checked={editingQuiz.is_active}
                          onChange={(e) => setEditingQuiz({...editingQuiz, is_active: e.target.checked})}
                          className="mr-2"
                        />
                        <label htmlFor={`active-${quiz.id}`} className="text-sm text-gray-700">
                          Активен
                        </label>
                      </div>

                      <div className="flex space-x-2 pt-4">
                        <Button type="submit" disabled={saving} className="bg-blue-500 hover:bg-blue-600 text-white">
                          {saving ? "Сохранение..." : "Сохранить"}
                        </Button>
                        <Button 
                          type="button" 
                          onClick={() => {
                            setEditingQuiz(null);
                            setEditingFullText('');
                          }}
                          className="bg-gray-500 hover:bg-gray-600 text-white"
                        >
                          Отмена
                        </Button>
                      </div>
                    </form>
                  ) : (
                    /* Отображение квиза */
                    <>
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h3 className="text-xl font-semibold text-gray-900">
                            {getRelationDisplayName(quiz.relation_key)}
                          </h3>
                          <div className="text-sm text-gray-600 mt-1">
                            Пол автора: {quiz.author_gender === 'female' ? 'Женский' : 'Мужской'}
                          </div>
                          {quiz.title && (
                            <div className="text-sm text-gray-700 mt-1">
                              {quiz.title}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                            quiz.is_active 
                              ? "bg-green-100 text-green-800" 
                              : "bg-gray-100 text-gray-800"
                          }`}>
                            {quiz.is_active ? "Активен" : "Неактивен"}
                          </span>
                        </div>
                      </div>

                      <div className="space-y-3">
                        <div>
                          <div className="text-sm font-medium text-gray-700 mb-1">Сообщение квиза:</div>
                          <div className="bg-gray-50 p-4 rounded-lg text-sm text-gray-800 border">
                            <div className="whitespace-pre-wrap">{getFullQuizText(quiz) || '—'}</div>
                          </div>
                        </div>
                      </div>

                      <div className="flex space-x-2 mt-4 pt-4 border-t border-gray-200">
                        <Button
                          onClick={() => {
                            setEditingQuiz(quiz);
                            setEditingFullText(getFullQuizText(quiz));
                          }}
                          className="bg-blue-500 hover:bg-blue-600 text-white"
                        >
                          Редактировать
                        </Button>
                        {userPermissions?.is_super_admin && (
                          <Button
                            onClick={() => handleDeleteQuiz(quiz.id)}
                            className="bg-red-500 hover:bg-red-600 text-white"
                          >
                            Удалить
                          </Button>
                        )}
                      </div>
                    </>
                  )}
                </Card>
              ))}
            </div>

            {songQuiz.filter(quiz => !relationFilter || quiz.relation_key === relationFilter).length === 0 && (
              <div className="text-center text-gray-500 py-8">
                {relationFilter ? 
                  `Нет квизов для типа связи "${getRelationDisplayName(relationFilter)}"` : 
                  "Нет настроенных квизов песни"
                }
              </div>
            )}
          </div>
        )}
      </div>

      {/* Форма создания нового шага */}
      {showCreateForm && (
        <Card className="p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">Добавить новый шаг контента</h2>
          <form onSubmit={handleCreateStep} className="space-y-4">
            <div className="form-group">
              <label className="form-label">Ключ шага:</label>
              <input
                type="text"
                value={newStep.step_key}
                onChange={(e) => setNewStep({...newStep, step_key: e.target.value})}
                className="w-full p-3 border border-gray-600 rounded bg-gray-800 text-white"
                placeholder="Например: welcome_message"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Название шага:</label>
              <input
                type="text"
                value={newStep.step_name}
                onChange={(e) => setNewStep({...newStep, step_name: e.target.value})}
                className="w-full p-3 border border-gray-600 rounded bg-gray-800 text-white"
                placeholder="Например: Приветственное сообщение"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Тип контента:</label>
              <select
                value={newStep.content_type}
                onChange={(e) => setNewStep({...newStep, content_type: e.target.value})}
                className="w-full p-3 border border-gray-600 rounded bg-gray-800 text-white"
              >
                <option value="text">Текст</option>
                <option value="image">Изображение</option>
                <option value="audio">Аудио</option>
                <option value="video">Видео</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Контент:</label>
              <textarea
                value={newStep.content}
                onChange={(e) => setNewStep({...newStep, content: e.target.value})}
                className="w-full p-3 border border-gray-600 rounded bg-gray-800 text-white h-32"
                placeholder="Введите текст сообщения..."
              />
            </div>
            <div className="form-group">
              <label className="form-label">Материалы (опционально):</label>
              <textarea
                value={newStep.materials}
                onChange={(e) => setNewStep({...newStep, materials: e.target.value})}
                className="w-full p-3 border border-gray-600 rounded bg-gray-800 text-white h-24"
                placeholder="Описание необходимых материалов..."
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_active"
                checked={newStep.is_active}
                onChange={(e) => setNewStep({...newStep, is_active: e.target.checked})}
                className="w-4 h-4 text-blue-600 bg-gray-800 border-gray-600 rounded focus:ring-blue-500"
              />
              <label htmlFor="is_active" className="text-sm text-gray-300">Активен</label>
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={creating} className="btn-medium bg-blue-500 hover:bg-blue-700">
                {creating ? "Создание..." : "Создать шаг"}
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

      {/* Список сообщений бота */}
      {(activeTab === 'book-path' || activeTab === 'song-path' || activeTab === 'common-messages') && (
        <div className="space-y-4">
          {botMessages
            .filter(message => {
              // Фильтр по активной вкладке
              let tabMatch = false;
              if (activeTab === 'book-path') {
                tabMatch = ['product', 'relation', 'hero', 'photo', 'question', 'payment', 'page_selection', 'demo', 'draft', 'cover', 'delivery', 'completion'].includes(message.context);
              } else if (activeTab === 'song-path') {
                tabMatch = message.context === 'song';
              } else if (activeTab === 'common-messages') {
                tabMatch = ['welcome', 'registration', 'common', 'error', 'info', 'reminder', 'button'].includes(message.context);
              }
              
              // Фильтр по контексту (если выбран)
              const contextMatch = filterContext === 'all' || message.context === filterContext;
              
              // Поиск по тексту (в названии, ключе и содержимом)
              const searchMatch = !searchQuery || 
                message.message_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                message.message_key.toLowerCase().includes(searchQuery.toLowerCase()) ||
                message.content.toLowerCase().includes(searchQuery.toLowerCase());
              
              return tabMatch && contextMatch && searchMatch;
            })
            .map((message) => (
            <Card key={message.id} className="p-4">
              <div className="flex justify-between items-start mb-3">
                              <div>
                <h3 className="text-lg font-semibold text-gray-900">
                  {searchQuery ? (
                    <span dangerouslySetInnerHTML={{
                      __html: message.message_name.replace(
                        new RegExp(`(${searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'),
                        '<mark class="bg-yellow-200">$1</mark>'
                      )
                    }} />
                  ) : (
                    message.message_name
                  )}
                </h3>
                <div className="text-sm text-gray-700">
                  Ключ: {searchQuery ? (
                    <span dangerouslySetInnerHTML={{
                      __html: message.message_key.replace(
                        new RegExp(`(${searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'),
                        '<mark class="bg-yellow-200">$1</mark>'
                      )
                    }} />
                  ) : (
                    message.message_key
                  )}
                </div>
                <div className="text-xs text-gray-500">
                  Этап: {message.stage} | Контекст: {message.context}
                </div>
              </div>
                <div className="flex items-center space-x-2">
                  <span className={`px-2 py-1 rounded text-xs ${
                    message.is_active 
                      ? "bg-green-100 text-green-800" 
                      : "bg-gray-100 text-gray-800"
                  }`}>
                    {message.is_active ? "Активен" : "Неактивен"}
                  </span>
                  <span className="px-2 py-1 rounded text-xs bg-purple-100 text-purple-800">
                    Использовано: {message.usage_count || 0}
                  </span>
                </div>
              </div>

              <div className="mb-3">
                <div className="text-sm font-medium mb-1 text-gray-900">Сообщение:</div>
                <div className="bg-gray-50 p-3 rounded text-sm text-gray-800">
                  <div className="whitespace-pre-wrap">
                    {searchQuery ? (
                      <span dangerouslySetInnerHTML={{
                        __html: message.content.replace(
                          new RegExp(`(${searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'),
                          '<mark class="bg-yellow-200">$1</mark>'
                        )
                      }} />
                    ) : (
                      message.content
                    )}
                  </div>
                </div>
              </div>

              <div className="text-xs text-gray-600 mb-3">
                <div>Создано: {new Date(message.created_at).toLocaleDateString()}</div>
                <div>Обновлено: {new Date(message.updated_at).toLocaleDateString()}</div>
                {message.last_used && (
                  <div>Последнее использование: {new Date(message.last_used).toLocaleDateString()}</div>
                )}
              </div>

              {userPermissions?.is_super_admin && (
                <div className="flex space-x-2">
                  <Button
                    onClick={() => setEditingMessage(message)}
                    className="text-sm bg-blue-500 hover:bg-blue-600 text-white"
                  >
                    Редактировать
                  </Button>
                  <Button
                    onClick={() => handleDeleteBotMessage(message.id)}
                    className="text-sm bg-red-500 hover:bg-red-600 text-white"
                    disabled={saving}
                  >
                    {saving ? "Удаление..." : "Удалить"}
                  </Button>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}

      {/* Список шагов контента — скрыто */}

      {/* Вкладка "Сводка заказа" — скрыто */}

      {(activeTab === 'book-path' || activeTab === 'song-path' || activeTab === 'common-messages') && botMessages.filter(message => {
        // Фильтр по активной вкладке
        let tabMatch = false;
        if (activeTab === 'book-path') {
          tabMatch = ['welcome', 'registration', 'product', 'relation', 'hero', 'photo', 'question', 'payment', 'page_selection', 'demo', 'draft', 'cover', 'delivery', 'completion'].includes(message.context);
        } else if (activeTab === 'song-path') {
          tabMatch = message.context === 'song';
        } else if (activeTab === 'common-messages') {
          tabMatch = ['common', 'error', 'info', 'reminder', 'button'].includes(message.context);
        }
        return tabMatch;
      }).length === 0 && (
        <div className="text-center text-gray-700 mt-8">
          Нет сообщений для выбранной вкладки
        </div>
      )}

      {/* Плашка пустого контента — скрыто */}

      {/* Модальное окно редактирования */}
      {editingStep && (
        <div className="fixed inset-0 bg-black flex items-center justify-center p-4">
          <Card className="p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-semibold mb-4 text-gray-900">Редактировать шаг контента</h2>
            <form onSubmit={handleUpdateStep} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2 text-gray-900">Ключ шага:</label>
                  <input
                    type="text"
                    value={editingStep.step_key}
                    onChange={(e) => setEditingStep({...editingStep, step_key: e.target.value})}
                    className="border border-gray-300 rounded px-3 py-2 w-full"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2 text-gray-900">Название шага:</label>
                  <input
                    type="text"
                    value={editingStep.step_name}
                    onChange={(e) => setEditingStep({...editingStep, step_name: e.target.value})}
                    className="border border-gray-300 rounded px-3 py-2 w-full"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2 text-gray-900">Тип контента:</label>
                  <select
                    value={editingStep.content_type}
                    onChange={(e) => setEditingStep({...editingStep, content_type: e.target.value})}
                    className="border border-gray-300 rounded px-3 py-2 w-full"
                  >
                    <option value="text">Текст</option>
                    <option value="image">Изображение</option>
                    <option value="video">Видео</option>
                    <option value="audio">Аудио</option>
                    <option value="file">Файл</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2 text-gray-900">Статус:</label>
                  <select
                    value={editingStep.is_active ? "true" : "false"}
                    onChange={(e) => setEditingStep({...editingStep, is_active: e.target.value === "true"})}
                    className="border border-gray-300 rounded px-3 py-2 w-full"
                  >
                    <option value="true">Активен</option>
                    <option value="false">Неактивен</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-gray-900">Контент:</label>
                <textarea
                  value={editingStep.content}
                  onChange={(e) => setEditingStep({...editingStep, content: e.target.value})}
                  className="border border-gray-300 rounded px-3 py-2 w-full h-32"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-gray-900">Материалы:</label>
                <textarea
                  value={editingStep.materials}
                  onChange={(e) => setEditingStep({...editingStep, materials: e.target.value})}
                  className="border border-gray-300 rounded px-3 py-2 w-full h-24"
                />
              </div>

              <div className="flex space-x-2">
                <Button type="submit" disabled={saving}>
                  {saving ? "Сохранение..." : "Сохранить"}
                </Button>
                                <Button
                  type="button"
                  className="bg-gray-500 hover:bg-gray-600 text-white"
                  onClick={() => setEditingStep(null)}
                >
                  Отмена
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Модальное окно редактирования сообщения бота */}
      {editingMessage && (
        <div className="fixed inset-0 bg-black flex items-center justify-center p-4 z-50">
          <Card className="p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-semibold mb-4 text-gray-900">Редактировать сообщение бота</h2>
            <form onSubmit={handleUpdateBotMessage} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2 text-gray-900">Название сообщения:</label>
                <input
                  type="text"
                  value={editingMessage.message_name}
                  disabled
                  className="border border-gray-300 rounded px-3 py-2 w-full bg-gray-100"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-gray-900">Ключ сообщения:</label>
                <input
                  type="text"
                  value={editingMessage.message_key}
                  disabled
                  className="border border-gray-300 rounded px-3 py-2 w-full bg-gray-100"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-gray-900">Контекст и этап:</label>
                <input
                  type="text"
                  value={`${editingMessage.context} / ${editingMessage.stage}`}
                  disabled
                  className="border border-gray-300 rounded px-3 py-2 w-full bg-gray-100"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-gray-900">Сообщение:</label>
                <textarea
                  value={editingMessage.content}
                  onChange={(e) => setEditingMessage({...editingMessage, content: e.target.value})}
                  className="border border-gray-300 rounded px-3 py-2 w-full h-32"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-gray-900">Статус:</label>
                <select
                  value={editingMessage.is_active ? "true" : "false"}
                  onChange={(e) => setEditingMessage({...editingMessage, is_active: e.target.value === "true"})}
                  className="border border-gray-300 rounded px-3 py-2 w-full"
                >
                  <option value="true">Активен</option>
                  <option value="false">Неактивен</option>
                </select>
              </div>

              <div className="flex space-x-2">
                <Button type="submit" disabled={saving}>
                  {saving ? "Сохранение..." : "Сохранить"}
                </Button>
                <Button
                  type="button"
                  className="bg-gray-500 hover:bg-gray-600 text-white"
                  onClick={() => setEditingMessage(null)}
                >
                  Отмена
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
};
