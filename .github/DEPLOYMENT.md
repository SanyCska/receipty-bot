# Настройка GitHub Actions для деплоя

## Необходимые секреты в GitHub

Добавьте следующие секреты в настройках репозитория:
**Settings → Secrets and variables → Actions → New repository secret**

### Обязательные секреты для SSH деплоя:

| Имя секрета | Значение | Пример |
|------------|----------|--------|
| `SERVER_HOST` | IP адрес вашего сервера | `192.168.1.100` или `example.com` |
| `SERVER_USER` | Имя пользователя для SSH | `root` или `ubuntu` |
| `SERVER_PATH` | Путь к проекту на сервере | `/root/receipty-bot` или `/home/ubuntu/receipty-bot` |
| `SSH_PRIVATE_KEY` | Приватный SSH ключ | Содержимое файла `~/.ssh/id_ed25519` |

### Секреты для переменных окружения бота:

| Имя секрета | Значение | Пример |
|------------|----------|--------|
| `TELEGRAM_BOT_TOKEN` | Токен Telegram бота | `123456789:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `OPENAI_API_KEY` | API ключ OpenAI | `sk-...` |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | ID Google таблицы (опционально) | `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms` |
| `GOOGLE_SHEETS_TAB_NAME` | Название листа (опционально) | `november_2025` |

## Как получить SSH_PRIVATE_KEY:

1. На вашем локальном компьютере выполните:
   ```bash
   cat ~/.ssh/id_ed25519
   ```
   
2. Скопируйте весь вывод (включая строки `-----BEGIN OPENSSH PRIVATE KEY-----` и `-----END OPENSSH PRIVATE KEY-----`)

3. Если у вас нет SSH ключа, создайте его:
   ```bash
   ssh-keygen -t ed25519 -C "github-actions"
   ```

4. Скопируйте публичный ключ на сервер:
   ```bash
   ssh-copy-id user@your-server-ip
   ```

## Проверка подключения:

После настройки секретов проверьте подключение:
```bash
ssh SERVER_USER@SERVER_HOST
```

## Что делает workflow:

1. При пуше в ветку `main` или `master`:
   - Собирает Docker образ
   - Копирует файлы на сервер через SSH
   - Останавливает старый контейнер
   - Собирает новый образ на сервере
   - Запускает новый контейнер с переменными окружения

## Важно:

- Убедитесь, что на сервере установлен Docker
- Убедитесь, что пользователь `SERVER_USER` имеет права на выполнение Docker команд
- Файл `config/gs_creds.json` должен быть скопирован на сервер вручную перед первым запуском

