# 🔧 Настройка Email Automation Platform

## 📧 Настройка IMAP подключения

1. **Скопируйте и отредактируйте файл окружения:**

   ```bash
   cp .env.example .env
   nano .env  # или используйте ваш любимый редактор
   ```

2. **Настройте IMAP parameters в .env файле:**
   ```env
   # Замените на ваши реальные настройки
   IMAP_HOST=imap.gmail.com                    # Ваш IMAP сервер
   IMAP_USER=your-email@gmail.com              # Ваш email
   IMAP_PASSWORD=your-app-specific-password    # Пароль приложения
   IMAP_MAILBOX=INBOX                          # Папка для сканирования
   ```

## 🔑 Получение credentials для различных провайдеров

### Gmail:

1. Включите 2FA в Google аккаунте
2. Создайте App Password: https://support.google.com/accounts/answer/185833
3. Используйте App Password вместо обычного пароля

### Outlook/Hotmail:

```env
IMAP_HOST=outlook.office365.com
IMAP_USER=your-email@outlook.com
IMAP_PASSWORD=your-password
```

### Yahoo:

```env
IMAP_HOST=imap.mail.yahoo.com
IMAP_USER=your-email@yahoo.com
IMAP_PASSWORD=your-app-password
```

### Пользовательские серверы:

```env
IMAP_HOST=mail.yourdomain.com
IMAP_USER=your-email@yourdomain.com
IMAP_PASSWORD=your-password
```

## 🏃‍♂️ Быстрый тест подключения

```bash
# Запустите приложение
make run

# В другом терминале протестируйте подключение
curl -X POST "http://localhost:8000/api/v1/system/test-connection"
```

## ⚠️ Безопасность

- ❌ **НЕ коммитьте .env файл в git**
- ✅ **Используйте App Passwords вместо основных паролей**
- ✅ **Регулярно меняйте credentials**
- ✅ **Ограничьте IMAP доступ по IP если возможно**

## 📝 Дополнительные настройки

Другие параметры в .env файле:

```env
# API настройки
API_ENDPOINT=https://your-api.example.com/invoices
API_KEY=your-secret-api-key

# База данных
DATABASE_URL=sqlite:///./automation.db

# Хранилище файлов
SAFE_STORAGE_DIR=./storage/safe
QUARANTINE_DIR=./storage/quarantine
MAX_FILE_SIZE_MB=50

# Режим отладки
DEBUG=false
```

Готово! 🚀 Ваш Email Automation Platform настроен и готов к работе.
