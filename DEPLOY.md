# Развёртывание на VPS

Подходит для Ubuntu/Debian. **Caddy не используется** — домен и HTTPS настраиваете сами (nginx или другой прокси). Бот просто слушает порт из `.env` (по умолчанию 8000).

## Быстрый старт (пара команд)

На сервере, где уже привязан домен и настроен nginx (или другой прокси):

**1)** Клонировать и развернуть одной командой (подставьте свой репозиторий):

```bash
curl -sSL https://raw.githubusercontent.com/sotnev2024-code/pay/main/scripts/deploy-vps.sh | bash -s -- https://github.com/sotnev2024-code/pay.git /opt/pay
```

**2)** Отредактировать `.env` и в nginx добавить прокси на порт бота:

```bash
nano /opt/pay/.env
# Заполнить: BOT_TOKEN, ADMIN_IDS, WEBAPP_URL, WEBHOOK_URL, CHANNEL_IDS, PORT (например 8001)
```

В конфиге nginx для вашего домена добавьте (порт должен совпадать с `PORT` из `.env`):

```nginx
location / {
    proxy_pass http://127.0.0.1:8001;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Перезапустить бота:

```bash
sudo systemctl restart pay-bot
```

Готово. Mini App: `https://ваш-домен/mini_app/`.

---

## Подробно

### 1. Репозиторий на GitHub

- Проект в GitHub, в репозитории есть `.env.example`, файла `.env` в репо нет.

### 2. Подключение к VPS

```bash
ssh root@ВАШ_IP
# или
ssh ubuntu@ВАШ_IP
```

### 3. Запуск скрипта деплоя

**Вариант A — одной командой (скрипт сам клонирует):**

Запускайте от обычного пользователя; скрипт запросит `sudo` для пакетов и systemd.

```bash
curl -sSL https://raw.githubusercontent.com/sotnev2024-code/pay/main/scripts/deploy-vps.sh | bash -s -- https://github.com/sotnev2024-code/pay.git /opt/pay
```

**Вариант B — клонировать вручную, потом скрипт:**

```bash
sudo mkdir -p /opt && sudo chown "$USER" /opt
git clone https://github.com/sotnev2024-code/pay.git /opt/pay
cd /opt/pay && chmod +x scripts/deploy-vps.sh && ./scripts/deploy-vps.sh
```

Скрипт:
- ставит Python 3, venv, pip, git (без Caddy);
- создаёт `.venv` и ставит зависимости;
- создаёт `.env` из `.env.example` (USE_POLLING=false), предлагает редактирование;
- создаёт и включает systemd-сервис `pay-bot`;
- по желанию сразу запускает бота.

### 4. Настройка .env

```bash
nano /opt/pay/.env
```

Обязательно:
- `BOT_TOKEN` — токен от @BotFather  
- `ADMIN_IDS` — ваш Telegram ID (несколько через запятую)  
- `WEBAPP_URL` — например `https://pay.plus-shop.ru/mini_app/`  
- `WEBHOOK_URL` — например `https://pay.plus-shop.ru`  
- `CHANNEL_IDS` — ID канала (например `-1001234567890`)  
- `PORT` — порт приложения (например `8001`), на него будет проксировать nginx  

### 5. Проксирование домена на бота

У вас уже есть домен и веб-сервер (nginx и т.п.). Нужно направить запросы на порт бота.

Пример для nginx (порт должен совпадать с `PORT` в `.env`):

```nginx
server {
    server_name pay.plus-shop.ru;
    # ... ваш ssl и прочее ...

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Перезагрузите nginx и перезапустите бота:

```bash
sudo nginx -t && sudo systemctl reload nginx
sudo systemctl restart pay-bot
```

### 6. Полезные команды

| Действие                | Команда |
|-------------------------|--------|
| Статус бота             | `sudo systemctl status pay-bot` |
| Логи в реальном времени | `journalctl -u pay-bot -f` |
| Перезапуск              | `sudo systemctl restart pay-bot` |
| Остановка               | `sudo systemctl stop pay-bot` |

### 7. Обновление с GitHub

```bash
cd /opt/pay
git pull
/opt/pay/.venv/bin/pip install -r requirements.txt
sudo systemctl restart pay-bot
```

### 8. DNS и порты

- В DNS для домена — A-запись на IP VPS.
- Порты 80/443 открыты для nginx (или вашего прокси). Сертификаты и HTTPS настраиваете вы (например certbot для nginx).
- Бот слушает только localhost:PORT, наружу его не пробрасывайте.
