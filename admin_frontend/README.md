# Getting Started with Create React App

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## 📋 Отложенные сообщения

### Обзор
Система отложенных сообщений позволяет автоматически отправлять сообщения пользователям в определенные моменты их взаимодействия с ботом.

### Типы сообщений

#### Личные сообщения (для конкретных заказов)
- **Демо-пример** - отправляется сразу после завершения вопросов о книге
- **Напоминание об оплате** - первое напоминание через указанное время
- **Финальное напоминание** - финальное напоминание через указанное время
- **Предложение сюжетов** - после одобрения демо-примера пользователем
- **Выбор сюжетов** - после отправки предложений сюжетов менеджером
- **Обратная связь по песне** - после одобрения черновика песни пользователем
- **Прогревочные сообщения** - во время создания песни для поддержания интереса
- **Заглушка сюжетов** - заглушка после завершения вопросов о книге

#### Общие сообщения (для всех пользователей)
- **Напоминание об оплате 1** - общее напоминание через 24 часа
- **Напоминание об оплате 2** - общее напоминание через 48 часов

### Как работают
1. **Автоматическая отправка** - система проверяет готовые к отправке сообщения каждые 10 секунд
2. **Условия отправки** - сообщение отправляется только если заказ не отменен и не оплачен (для напоминаний)
3. **Файлы** - поддерживаются фото и аудио файлы (максимум 15 файлов на сообщение)
4. **Статусы** - pending (ожидает), sent (отправлено), failed (ошибка), cancelled (отменено)

### Технические детали
- **Время отправки**: scheduled_at = created_at + delay_minutes
- **Проверка статуса**: система автоматически отменяет напоминания для оплаченных заказов
- **Обработка ошибок**: при ошибке отправки статус меняется на "failed"
- **Медиафайлы**: фото отправляются группой, аудио - отдельными сообщениями

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

The page will reload if you make edits.\
You will also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can’t go back!**

If you aren’t satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you’re on your own.

You don’t have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn’t feel obligated to use this feature. However we understand that this tool wouldn’t be useful if you couldn’t customize it when you are ready for it.

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).
