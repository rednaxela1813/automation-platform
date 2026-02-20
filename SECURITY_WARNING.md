# 🔐 КРИТИЧЕСКОЕ ЗАМЕЧАНИЕ ПО БЕЗОПАСНОСТИ

⚠️ **ВНИМАНИЕ: В файле .env содержатся реальные credentials!**

## 🚨 Немедленные действия:

1. **Удалите реальные данные из .env:**

   ```bash
   # Замените реальные данные на примеры
   IMAP_HOST=your.mail.server.com
   IMAP_USER=your-email@domain.com
   IMAP_PASSWORD=your-secure-password
   ```

2. **Добавьте .env в .gitignore:**

   ```bash
   echo ".env" >> .gitignore
   git add .gitignore
   git commit -m "feat: add .env to gitignore"
   ```

3. **Используйте .env.example для новых установок:**
   ```bash
   cp .env.example .env
   # Отредактируйте .env с вашими настройками
   ```

## 🔒 Рекомендации по безопасности:

- Никогда не коммитьте файлы с credentials
- Используйте переменные окружения или секреты
- Регулярно меняйте пароли
- Используйте app-specific пароли для email

**Эта проблема должна быть исправлена до любого деплоя!**
