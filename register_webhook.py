import os
import requests
from dotenv import load_dotenv
from pathlib import Path

# Load .env from the script directory (max_bot/.env) if present
HERE = Path(__file__).resolve().parent
load_dotenv(HERE / '.env')
TOKEN = os.getenv("MAX_TOKEN")
API_BASE = "https://platform-api.max.ru"


def register_webhook(webhook_url: str):
    if not TOKEN:
        print("MAX_TOKEN не найден в окружении (проверьте max_bot/.env)")
        return
    headers = {"Authorization": TOKEN, "Content-Type": "application/json"}
    body = {"url": webhook_url}
    try:
        r = requests.post(f"{API_BASE}/subscriptions", headers=headers, json=body, timeout=10)
    except Exception as e:
        print("Ошибка запроса:", e)
        return
    if r.status_code in (200, 201):
        data = r.json()
        print("Webhook успешно зарегистрирован:", data)
        # try to save subscription id to a file for later unregister
        sub_id = None
        if isinstance(data, dict):
            sub_id = data.get('id') or data.get('subscription_id')
        if sub_id:
            out = HERE / 'subscription_id.txt'
            try:
                out.write_text(str(sub_id))
                print(f"Subscription id сохранён в {out}")
            except Exception as e:
                print("Не удалось сохранить subscription id:", e)
    else:
        print("Не удалось зарегистрировать webhook:", r.status_code, r.text)


def unregister_webhook(sub_id: str):
    if not TOKEN:
        print("MAX_TOKEN не найден в окружении (проверьте max_bot/.env)")
        return
    headers = {"Authorization": TOKEN}
    try:
        r = requests.delete(f"{API_BASE}/subscriptions/{sub_id}", headers=headers, timeout=10)
    except Exception as e:
        print("Ошибка запроса:", e)
        return
    if r.status_code == 200:
        print("Webhook отписан")
    else:
        print("Не удалось отписать webhook:", r.status_code, r.text)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='Register/unregister MAX webhook')
    p.add_argument('--register', '-r', help='Webhook public HTTPS URL to register (POST /subscriptions)')
    p.add_argument('--unregister', '-u', help='Subscription id to unregister (DELETE /subscriptions/{id})')
    args = p.parse_args()
    if args.register:
        register_webhook(args.register)
    elif args.unregister:
        unregister_webhook(args.unregister)
    else:
        p.print_help()
