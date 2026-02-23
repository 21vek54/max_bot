#!/usr/bin/env python3
import os
import time
import atexit
import random
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("MAX_TOKEN")
API_BASE = "https://platform-api.max.ru"
BOT_USER_ID = None
LOCK_PATH = ".bot.lock"
LOCK_FD = None
QUIZ_STATE = {}
QUIZ_TITLE = "🏂🧢 ТЕСТ: «Скуф-сноубордист ты или ещё держишься?»"
QUIZ_START_KEYS = {"опрос", "/quiz", "/test", "тест", "/start", "start"}
QUIZ_QUESTIONS = [
    {
        "q": "1. Ты собираешься на склон. Что важнее?",
        "options": [
            {"text": "Новый трюк выучить", "score": 0},
            {"text": "Чтобы трасса норм была", "score": 1},
            {"text": "Чтобы спина не ныла", "score": 2},
            {"text": "Чтобы кафешка внизу работала и вайфай ловил", "score": 3},
        ],
    },
    {
        "q": "2. Твоя разминка перед каткой?",
        "options": [
            {"text": "Прыжки, растяжка", "score": 0},
            {"text": "Немного покрутился", "score": 1},
            {"text": "Да ладно, аккуратно поеду", "score": 2},
            {"text": "Сижу и морально готовлюсь минут 15", "score": 3},
        ],
    },
    {
        "q": "3. После двух спусков ты…",
        "options": [
            {"text": "Только разогрелся", "score": 0},
            {"text": "Норм, катаю дальше", "score": 1},
            {"text": "Уже присел отдохнуть", "score": 2},
            {"text": "Обсуждаю, как раньше катались по-настоящему", "score": 3},
        ],
    },
    {
        "q": "4. На склоне кто-то прыгает с кикера. Твоя мысль?",
        "options": [
            {"text": "Надо тоже попробовать", "score": 0},
            {"text": "Красиво", "score": 1},
            {"text": "Зачем рисковать", "score": 2},
            {"text": "Пусть колени поберегут, потом поймут", "score": 3},
        ],
    },
    {
        "q": "5. Самая обсуждаемая тема на подъёмнике?",
        "options": [
            {"text": "Новая доска или стиль", "score": 0},
            {"text": "Погода", "score": 1},
            {"text": "Цены на скипасс", "score": 2},
            {"text": "Как в World of Tanks баланс опять сломали", "score": 3},
        ],
    },
    {
        "q": "6. Вечером после катки ты…",
        "options": [
            {"text": "Иду в бар или на движ", "score": 0},
            {"text": "Просто отдыхаю", "score": 1},
            {"text": "Мажу колено и поясницу", "score": 2},
            {"text": "Захожу в World of Tanks на пару боёв до 2 ночи", "score": 3},
        ],
    },
    {
        "q": "7. Твоя экипировка?",
        "options": [
            {"text": "Обновляю, слежу за новинками", "score": 0},
            {"text": "Всё норм", "score": 1},
            {"text": "Куртка ещё 2015, но живая", "score": 2},
            {"text": "Она со мной через всё прошла", "score": 3},
        ],
    },
    {
        "q": "8. После падения ты…",
        "options": [
            {"text": "Вскочил и поехал", "score": 0},
            {"text": "Отряхнулся", "score": 1},
            {"text": "Полежал секунд 10", "score": 2},
            {"text": "Лежу, смотрю в небо и переосмысливаю решения", "score": 3},
        ],
    },
]


def parse_number(text):
    try:
        return float(str(text).strip().replace(",", "."))
    except Exception:
        return None


def menu_keyboard():
    return [
        {
            "type": "inline_keyboard",
            "payload": {"buttons": [[{"type": "callback", "text": "Узнать", "payload": "quiz:start"}]]},
        }
    ]


def answer_keyboard(keys):
    return [
        {
            "type": "inline_keyboard",
            "payload": {
                "buttons": [
                    [{"type": "callback", "text": keys[0], "payload": f"quiz:ans:{keys[0]}"}],
                    [{"type": "callback", "text": keys[1], "payload": f"quiz:ans:{keys[1]}"}],
                    [{"type": "callback", "text": keys[2], "payload": f"quiz:ans:{keys[2]}"}],
                    [{"type": "callback", "text": keys[3], "payload": f"quiz:ans:{keys[3]}"}],
                ]
            },
        }
    ]


def result_keyboard():
    return [
        {
            "type": "inline_keyboard",
            "payload": {
                "buttons": [[
                    {"type": "callback", "text": "Поделиться", "payload": "quiz:share"},
                    {"type": "callback", "text": "Пройти ещё раз", "payload": "quiz:restart"},
                ]]
            },
        }
    ]


def render_result(total_score):
    if total_score <= 6:
        grade = "Молодой райдер. Скуф не обнаружен."
    elif total_score <= 14:
        grade = "Лёгкий скуф-налёт. Уже ценишь комфорт."
    elif total_score <= 20:
        grade = "Уверенный скуф-сноубордист. Твой главный трюк — аккуратный спуск."
    else:
        grade = "Верховный скуф склона. Катка — повод выйти из дома. Настоящий движ — в танках."
    return f"🎉 Поздравляю, ты прошёл тест!\n🧮 Результат: {total_score} баллов.\n{grade}"


def render_question(state):
    q = QUIZ_QUESTIONS[state["index"]]
    options = list(q["options"])
    random.shuffle(options)
    keys = ["C", "K", "U", "F"]
    mapped = {k: options[i] for i, k in enumerate(keys)}
    state["current_options"] = mapped
    lines = [q["q"], ""]
    for key in keys:
        lines.append(f"{key}) {mapped[key]['text']}")
    return "\n".join(lines), answer_keyboard(keys)


def handle_quiz_message(user_key, text, callback_payload=None):
    normalized = text.strip().lower()
    payload = (callback_payload or "").strip().lower()
    if user_key not in QUIZ_STATE:
        if normalized in QUIZ_START_KEYS or payload == "quiz:start":
            QUIZ_STATE[user_key] = {"stage": "menu"}
            intro = f"{QUIZ_TITLE}\nНажми кнопку, чтобы узнать результат."
            return intro, menu_keyboard()
        return None

    state = QUIZ_STATE[user_key]
    if state["stage"] == "menu":
        if normalized == "узнать" or payload == "quiz:start":
            state["stage"] = "quiz"
            state["index"] = 0
            state["score"] = 0
            return render_question(state)
        return "Нажми кнопку «Узнать».", menu_keyboard()

    if state["stage"] == "finished":
        if normalized == "поделиться" or payload == "quiz:share":
            share = (
                f"Я прошёл тест «Скуф-сноубордист» и набрал {state['score']} баллов.\n"
                f"Итог: {state['grade']}\n"
                "Тоже попробуй: напиши боту «опрос»."
            )
            return share, result_keyboard()
        if normalized in {"пройти ещё раз", "пройти еще раз", "узнать"} or payload == "quiz:restart":
            state["stage"] = "quiz"
            state["index"] = 0
            state["score"] = 0
            return render_question(state)
        return "Нажми «Поделиться» или «Пройти ещё раз».", result_keyboard()

    if state["stage"] != "quiz":
        QUIZ_STATE[user_key] = {"stage": "menu"}
        return "Нажми кнопку «Узнать».", menu_keyboard()

    selected_key = None
    if payload.startswith("quiz:ans:"):
        selected_key = payload.split(":")[-1].strip().upper()
    else:
        normalized_text = text.strip().upper()
        if normalized_text in {"C", "K", "U", "F"}:
            selected_key = normalized_text

    current_options = state.get("current_options", {})
    if selected_key not in current_options:
        if len(current_options) == 4:
            return render_question(state)
        return "Нажми кнопку «Узнать».", menu_keyboard()

    state["score"] += current_options[selected_key]["score"]
    state["index"] += 1
    if state["index"] >= len(QUIZ_QUESTIONS):
        result_text = render_result(state["score"])
        if state["score"] <= 6:
            grade = "Молодой райдер"
        elif state["score"] <= 14:
            grade = "Лёгкий скуф-налёт"
        elif state["score"] <= 20:
            grade = "Уверенный скуф-сноубордист"
        else:
            grade = "Верховный скуф склона"
        state["stage"] = "finished"
        state["grade"] = grade
        return result_text, result_keyboard()

    return render_question(state)


def acquire_single_instance_lock():
    global LOCK_FD
    lock_path = str(Path(__file__).resolve().with_name(LOCK_PATH))
    print(f"Boot: pid={os.getpid()} file={Path(__file__).resolve()} lock={lock_path}")

    def _pid_running(pid):
        if not isinstance(pid, int) or pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except Exception:
            return True

    def _try_lock():
        return os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)

    try:
        LOCK_FD = _try_lock()
        os.write(LOCK_FD, str(os.getpid()).encode("utf-8"))
        os.fsync(LOCK_FD)
    except FileExistsError:
        stale_pid = None
        try:
            raw = Path(lock_path).read_text(encoding="utf-8").strip()
            stale_pid = int(raw) if raw else None
        except Exception:
            stale_pid = None

        if stale_pid is not None and not _pid_running(stale_pid):
            try:
                os.remove(lock_path)
                LOCK_FD = _try_lock()
                os.write(LOCK_FD, str(os.getpid()).encode("utf-8"))
                os.fsync(LOCK_FD)
            except Exception:
                print("Another bot.py instance is already running. Stop it and retry.")
                return False
        else:
            print("Another bot.py instance is already running. Stop it and retry.")
            return False
    except Exception as e:
        print("Failed to acquire process lock:", e)
        return False

    def _cleanup():
        try:
            if LOCK_FD is not None:
                os.close(LOCK_FD)
        except Exception:
            pass
        try:
            if os.path.exists(lock_path):
                os.remove(lock_path)
        except Exception:
            pass

    atexit.register(_cleanup)
    return True


def check_token():
    global BOT_USER_ID
    if not TOKEN:
        print("No token. Set MAX_TOKEN in environment or .env")
        return False

    headers = {"Authorization": TOKEN}
    try:
        r = requests.get(f"{API_BASE}/me", headers=headers, timeout=10)
    except Exception as e:
        print("Token check request failed:", e)
        return False

    if r.status_code == 200:
        me = r.json()
        BOT_USER_ID = me.get("user_id")
        print("Token is valid. /me:", me)
        return True

    print("Token check failed:", r.status_code, r.text)
    return False


def send_message(text, chat_id=None, user_id=None, attachments=None):
    if chat_id is None and user_id is None:
        print("Send skipped: no recipient")
        return

    body = {"text": text}
    if attachments is not None:
        body["attachments"] = attachments
    params = {}
    if user_id is not None:
        params["user_id"] = user_id
    elif chat_id is not None:
        params["chat_id"] = chat_id

    headers = {"Authorization": TOKEN, "Content-Type": "application/json"}
    try:
        r = requests.post(
            f"{API_BASE}/messages",
            headers=headers,
            params=params,
            json=body,
            timeout=10,
        )
        if r.status_code == 200:
            print("Sent:", r.json())
        else:
            print(f"Send failed ({r.status_code}): {r.text}; params={params}")
    except Exception as e:
        print("Exception while sending:", e)


def extract_message_update(update):
    if not isinstance(update, dict):
        return None, None, None, None

    update_type = update.get("update_type") or update.get("type")
    if update_type not in ("message_created", "message"):
        return None, None, None, None

    message = update.get("message") if isinstance(update.get("message"), dict) else {}
    sender = message.get("sender") if isinstance(message.get("sender"), dict) else {}
    recipient = message.get("recipient") if isinstance(message.get("recipient"), dict) else {}
    body = message.get("body") if isinstance(message.get("body"), dict) else {}

    chat_id = (
        update.get("chat_id")
        or (update.get("chat") or {}).get("id")
        or message.get("chat_id")
        or (message.get("chat") or {}).get("id")
        or recipient.get("chat_id")
        or (recipient.get("chat") or {}).get("id")
    )
    text = update.get("text") or message.get("text") or body.get("text") or ""
    sender_id = sender.get("user_id")
    chat_type = (
        update.get("chat_type")
        or (update.get("chat") or {}).get("chat_type")
        or message.get("chat_type")
        or (message.get("chat") or {}).get("chat_type")
        or recipient.get("chat_type")
    )
    return chat_id, text, sender_id, chat_type


def extract_callback_update(update):
    if not isinstance(update, dict):
        return None, None, None, None
    update_type = update.get("update_type") or update.get("type")
    if update_type != "message_callback":
        return None, None, None, None

    callback = update.get("callback") if isinstance(update.get("callback"), dict) else {}
    message = update.get("message") if isinstance(update.get("message"), dict) else {}
    recipient = message.get("recipient") if isinstance(message.get("recipient"), dict) else {}
    cb_user = callback.get("user") if isinstance(callback.get("user"), dict) else {}
    upd_user = update.get("user") if isinstance(update.get("user"), dict) else {}
    payload = callback.get("payload") or update.get("payload") or ""
    chat_id = (
        update.get("chat_id")
        or recipient.get("chat_id")
        or (callback.get("recipient") or {}).get("chat_id")
    )
    user_id = (
        update.get("user_id")
        or upd_user.get("user_id")
        or cb_user.get("user_id")
        or callback.get("user_id")
    )
    chat_type = (
        update.get("chat_type")
        or recipient.get("chat_type")
        or (callback.get("recipient") or {}).get("chat_type")
    )
    return chat_id, user_id, chat_type, str(payload)


def long_polling_loop(poll_interval=1):
    print("Start long polling (Ctrl+C to stop)")
    marker = None

    while True:
        params = {"timeout": 30}
        if marker is not None:
            params["marker"] = marker

        try:
            r = requests.get(
                f"{API_BASE}/updates",
                headers={"Authorization": TOKEN},
                params=params,
                timeout=60,
            )

            if r.status_code == 200:
                try:
                    data = r.json()
                except Exception:
                    print("Cannot parse JSON:", r.text)
                    time.sleep(poll_interval)
                    continue

                updates = data.get("updates") if isinstance(data, dict) and "updates" in data else data
                if updates:
                    for u in updates:
                        print("Update:", u)
                        if isinstance(u, dict) and u.get("update_type") == "bot_started":
                            chat_id = u.get("chat_id")
                            sender_id = u.get("user_id") or (u.get("user") or {}).get("user_id")
                            if chat_id:
                                user_key = sender_id if sender_id is not None else chat_id
                                QUIZ_STATE[user_key] = {"stage": "menu"}
                                intro = f"{QUIZ_TITLE}\nНажми кнопку, чтобы узнать результат."
                                send_message(intro, chat_id=chat_id, user_id=sender_id, attachments=menu_keyboard())
                            continue
                        if isinstance(u, dict) and u.get("update_type") == "dialog_removed":
                            sender_id = u.get("user_id") or (u.get("user") or {}).get("user_id")
                            chat_id = u.get("chat_id")
                            user_key = sender_id if sender_id is not None else chat_id
                            if user_key in QUIZ_STATE:
                                del QUIZ_STATE[user_key]
                            continue

                        update_type = u.get("update_type") if isinstance(u, dict) else None
                        callback_payload = None
                        if update_type == "message_callback":
                            chat_id, sender_id, chat_type, callback_payload = extract_callback_update(u)
                            text = ""
                        else:
                            chat_id, text, sender_id, chat_type = extract_message_update(u)
                        if not chat_id:
                            continue
                        if BOT_USER_ID is not None and sender_id == BOT_USER_ID:
                            continue

                        incoming_text = str(text or "")
                        user_key = sender_id if sender_id is not None else chat_id
                        send_user_id = sender_id if chat_type == "dialog" else None
                        quiz_result = handle_quiz_message(user_key, incoming_text, callback_payload=callback_payload)
                        quiz_reply = quiz_result[0] if quiz_result is not None else None
                        quiz_attachments = quiz_result[1] if quiz_result is not None else None
                        if quiz_reply is not None:
                            send_message(
                                quiz_reply,
                                chat_id=chat_id,
                                user_id=send_user_id,
                                attachments=quiz_attachments,
                            )
                            continue

                        number = parse_number(incoming_text)
                        if number is not None:
                            result = number * 2
                            if result.is_integer():
                                result = int(result)
                            send_message(str(result), chat_id=chat_id, user_id=send_user_id)
                        else:
                            send_message("Echo: " + text, chat_id=chat_id, user_id=send_user_id)

                if isinstance(data, dict) and "marker" in data:
                    marker = data["marker"]

            elif r.status_code == 401:
                print("Invalid token (401). Stop.")
                break
            else:
                print("HTTP", r.status_code, r.text)

            time.sleep(poll_interval)

        except requests.exceptions.ReadTimeout:
            continue
        except KeyboardInterrupt:
            print("Stopped by user")
            break
        except Exception as e:
            print("Polling loop error:", e)
            time.sleep(5)


if __name__ == '__main__':
    if acquire_single_instance_lock() and check_token():
        long_polling_loop()
