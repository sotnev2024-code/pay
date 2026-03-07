# Развёртывание на VPS

Подходит для Ubuntu/Debian (или аналогичный Linux с `apt`).

## 1. Подготовка репозитория на GitHub

- Залейте проект в GitHub (создайте репозиторий и сделайте `git push`).
- Убедитесь, что в репозитории есть `.env.example` (без секретов), но **нет** файла `.env`.

## 2. Подключение к VPS

```bash
ssh root@ВАШ_IP
# или
ssh ubuntu@ВАШ_IP
```

## 3. Вариант A: Скачать и запустить скрипт одной командой

Подставьте свой репозиторий и папку установки. **Запускайте от обычного пользователя** (не root) — скрипт сам запросит `sudo` для установки пакетов и systemd:

```bash
curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/scripts/deploy-vps.sh | bash -s -- https://github.com/YOUR_USERNAME/YOUR_REPO.git /opt/pay
```

Пример:

```bash
curl -sSL https://raw.githubusercontent.com/username/pay-bot/main/scripts/deploy-vps.sh | bash -s -- https://github.com/username/pay-bot.git /opt/pay
```

Если папка `/opt` не существует, скрипт создаст её через `sudo` и отдаст владение вашему пользователю.

Скрипт сам:
- клонирует репозиторий в `/opt/pay`;
- установит Python, venv, Caddy (если нет);
- создаст `.venv` и поставит зависимости;
- создаст `.env` из `.env.example` и предложит его отредактировать;
- создаст Caddyfile по домену из `.env`;
- создаст и включит systemd-сервис `pay-bot`;
- по желанию запустит Caddy и бота.

Дальше нужно только отредактировать `.env` (BOT_TOKEN, ADMIN_IDS, WEBAPP_URL, WEBHOOK_URL, CHANNEL_IDS) и при необходимости перезапустить сервис.

## 4. Вариант B: Клонировать вручную и запустить скрипт

```bash
sudo mkdir -p /opt
sudo chown "$USER" /opt
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git /opt/pay
cd /opt/pay
chmod +x scripts/deploy-vps.sh
./scripts/deploy-vps.sh
```

(Без аргументов скрипт работает в текущей папке и не клонирует репозиторий.)

## 5. Настройка .env на сервере

После первого запуска скрипта отредактируйте `.env`:

```bash
nano /opt/pay/.env
```

Обязательно укажите:

- `BOT_TOKEN` — токен от @BotFather  
- `ADMIN_IDS` — ваш Telegram ID (можно несколько через запятую)  
- `WEBAPP_URL` — например `https://pay.plus-shop.ru/mini_app/`  
- `WEBHOOK_URL` — например `https://pay.plus-shop.ru`  
- `CHANNEL_IDS` — ID канала (например `-1001234567890`)  
- `USE_POLLING=false` — для продакшена оставьте так  

Сохраните (Ctrl+O, Enter, Ctrl+X), затем перезапустите бота:

```bash
sudo systemctl restart pay-bot
```

## 6. Полезные команды

| Действие              | Команда |
|-----------------------|--------|
| Статус бота           | `sudo systemctl status pay-bot` |
| Логи в реальном времени | `journalctl -u pay-bot -f` |
| Перезапуск бота       | `sudo systemctl restart pay-bot` |
| Остановка             | `sudo systemctl stop pay-bot` |
| Статус Caddy          | `sudo systemctl status caddy` |
| Перезапуск Caddy      | `sudo systemctl restart caddy` |

## 7. Обновление с GitHub

```bash
cd /opt/pay
git pull
/opt/pay/.venv/bin/pip install -r requirements.txt
sudo systemctl restart pay-bot
```

## 8. DNS и порты

- В DNS для вашего домена (например, `pay.plus-shop.ru`) должна быть A-запись на **внешний IP вашего VPS**.
- На VPS порты **80** и **443** должны быть открыты (в панели хостинга / firewall). Caddy сам получит сертификат Let's Encrypt при первом запросе по HTTPS.
