# MAX бот (минимальный скелет)

Кратко: минимальный Python-скелет для локальной разработки бота с использованием Long Polling.

Файлы:
- `requirements.txt` — зависимости
- `.env.example` — пример переменных окружения
- `bot.py` — основной скрипт

Запуск (Windows, PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Создайте .env по примеру и вставьте ваш MAX_TOKEN
python bot.py
```

Примечания:
- Скрипт делает базовую проверку токена (`GET /me`) и демонстрационный long-polling (`GET /updates`).
- Перед деплоем в production — используйте Webhook и HTTPS.
 
Webhook (FastAPI)

1) Установите зависимости:

```powershell
pip install -r max_bot\requirements.txt
```

2) Создайте `.env` по примеру и вставьте `MAX_TOKEN`.

3) Запустите локально (для разработки):

```powershell
# в корне проекта
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r max_bot\requirements.txt
python max_bot\webhook_bot.py
```

4) Чтобы получить публичный HTTPS URL для локального сервера используйте `ngrok` или аналог (пример):

```powershell
ngrok http 8000
```

5) В панели партнёров MAX или через API зарегистрируйте ваш HTTPS webhook URL (`https://...ngrok.io/webhook`).

6) После регистрации платформа будет отправлять события на `/webhook`. В `webhook_bot.py` — логирование и отправка эхо‑ответа.

Если хотите — могу добавить endpoint для автоматической регистрации подписки на события через API (нужен доступ к учётной записи партнёра).
Я добавил утилиту `register_webhook.py` для автоматической регистрации и отписки webhook через API.

Пример использования после получения публичного HTTPS URL (ngrok):

```powershell
# Регистрация
python max_bot\register_webhook.py --register https://your-ngrok-id.ngrok.io/webhook

# Отмена по id подписки
python max_bot\register_webhook.py --unregister <subscription_id>
```

Утилита использует `MAX_TOKEN` из `max_bot\.env`.
