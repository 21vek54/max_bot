from fastapi import FastAPI, Request
import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("MAX_TOKEN")
API_BASE = "https://platform-api.max.ru"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI()


def send_message(chat_id: int, text: str):
    headers = {"Authorization": TOKEN, "Content-Type": "application/json"}
    body = {"chat_id": chat_id, "text": text}
    try:
        r = requests.post(f"{API_BASE}/messages", headers=headers, json=body, timeout=10)
        logging.info("Send message status: %s %s", r.status_code, r.text)
    except Exception as e:
        logging.exception("Failed to send message: %s", e)


@app.on_event("startup")
async def startup_event():
    if not TOKEN:
        logging.error("MAX_TOKEN not set — webhook will accept events but cannot call API")
        return
    try:
        r = requests.get(f"{API_BASE}/me", headers={"Authorization": TOKEN}, timeout=10)
        logging.info("Token check on startup: %s %s", r.status_code, r.text)
    except Exception:
        logging.exception("Token check failed on startup")


@app.post("/webhook")
async def webhook(request: Request):
    payload = await request.json()
    logging.info("Webhook received: %s", payload)

    try:
        updates = payload.get("updates") if isinstance(payload, dict) and "updates" in payload else [payload]
        for u in updates:
            if not isinstance(u, dict):
                continue
            # Простая обработка сообщений: если пришло сообщение — эхо
            if u.get("type") == "message":
                chat_id = u.get("chat_id") or (u.get("chat") or {}).get("id")
                text = u.get("text") or ""
                if chat_id and TOKEN:
                    send_message(chat_id, "Echo: " + text)
    except Exception:
        logging.exception("Error processing webhook payload")

    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("webhook_bot:app", host="0.0.0.0", port=8000, reload=True)
