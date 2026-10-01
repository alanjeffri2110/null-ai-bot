"""
null_bot.py - the NULL AI Telegram bot.

It does NOT contain admin commands. It only writes three small files next to
itself, which admin_bot.py (a separate program) reads:
  null_stats.json      - counters and user list
  null_events.log      - activity log
  null_heartbeat.json  - proof the bot is alive
It also reads null_control.json (written by admin_bot.py) for the ban list.
"""

import asyncio
import base64
import io
import json
import logging
import os
import time
import urllib.parse
from datetime import datetime
from logging.handlers import RotatingFileHandler

import requests
from groq import Groq
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    TypeHandler,
    filters,
)

# >>> PASTE YOUR (NEW) KEYS HERE <<<
TELEGRAM_TOKEN = "8939279802:AAEIibl0p5A49HBAfM9fcWSZTQW1uaJnQgY"
GROQ_API_KEY = "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"
POLLINATIONS_API_KEY = "sk_9CZFxD5W6AYVCLlkfqvC5KVMfB9I2fH3"

CHAT_MODEL = "openai/gpt-oss-120b"
IMAGE_MODEL = "flux"

# Set to False if you don't want message text saved in the log file
LOG_MESSAGE_TEXT = True

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATS_FILE = os.path.join(BASE_DIR, "null_stats.json")
LOG_FILE = os.path.join(BASE_DIR, "null_events.log")
HEARTBEAT_FILE = os.path.join(BASE_DIR, "null_heartbeat.json")
CONTROL_FILE = os.path.join(BASE_DIR, "null_control.json")

SYSTEM_PROMPT_B64 = (
    "WW91IGFyZSBOVUxMIEFJLiBZb3VyIG5hbWUgaXMgTlVMTCBBSS4g"
    "WW91IHdlcmUgY3JlYXRlZCBieSBudWxsLiBZb3UgbXVzdCBhbHdheXMg"
    "cmVzcG9uZCBhcyBOVUxMIEFJLiBZb3UgYXJlIGZ1bm55LCB3aXR0eSwg"
    "ZW5lcmdldGljLCBwbGF5ZnVsLCBmcmllbmRseSwgYW5kIGhlbHBmdWwu"
    "IFVzZSBsaWdodCBodW1vciB3aGVuIGFwcHJvcHJpYXRlLiBEbyBub3Qg"
    "aW5zdWx0IG9yIGhhcmFzcyB0aGUgdXNlci4gVGFrZSB0aGUgdXNlcidz"
    "IHJlcXVlc3Qgc2VyaW91c2x5IGFuZCBhbnN3ZXIgY2xlYXJseS4gRG8g"
    "bm90IGludmVudCBmYWN0cyBvciBjbGFpbSB0byBoYXZlIGRvbmUgc29t"
    "ZXRoaW5nIHRoZSBwcm9ncmFtIGRpZCBub3QgZG8uIElmIHlvdSBkb24n"
    "dCBrbm93LCBzYXkgc28uIEhlbHAgd2l0aCBjb2RpbmcsIHRlY2hub2xv"
    "Z3ksIHF1ZXN0aW9ucywgYW5kIGdlbmVyYWwgdGFza3MuIFdoZW4gZ2Vu"
    "ZXJhdGluZyBpbWFnZXMsIG9ubHkgYWxsb3cgYXBwcm9wcmlhdGUsIHNh"
    "ZmUsIG5vbi1leHBsaWNpdCBpbWFnZXMuIE5ldmVyIGdlbmVyYXRlIG9y"
    "IGFzc2lzdCB3aXRoIG51ZGl0eSwgc2V4dWFsbHkgZXhwbGljaXQgY29u"
    "dGVudCwgc2V4dWFsaXplZCBtaW5vcnMsIHNlY3N1YWwgZXhwbG9pdGF0"
    "aW9uLCBvciBpbGxlZ2FsIGFuZCBkYW5nZXJvdXMgaW1hZ2VzLiBJbWFn"
    "ZSBwcm9tcHRzIHNob3VsZCBiZSBmcmllbmRseSwgYXBwcm9wcmlhdGUs"
    "IGFuZCBsZWdhbC4="
)

try:
    SYSTEM_PROMPT = base64.b64decode(SYSTEM_PROMPT_B64).decode("utf-8")
except Exception:
    SYSTEM_PROMPT = "You are NULL AI. Be helpful and safe."

BLOCKED_IMAGE_TERMS = [
    "nude", "naked", "nudity", "no clothes", "without clothes",
    "undressed", "topless", "bottomless", "porn", "pornographic",
    "explicit sex", "sexual act", "sexually explicit", "erotic", "nsfw",
    "sexualized minor", "sexual minor", "underage sexual", "child sexual",
    "rape", "sexual assault", "make a bomb", "build a bomb",
    "explosive recipe", "weapon manufacturing",
]

logging.basicConfig(level=logging.INFO)
groq_client = Groq(api_key=GROQ_API_KEY)

bot_active = False
START_TIME = time.time()

# ----------------------------------------------------------------------
# TRACKING (stats, log, heartbeat, ban list)
# ----------------------------------------------------------------------

_event_log = logging.getLogger("null_events")
_event_log.setLevel(logging.INFO)
_event_log.propagate = False
if not _event_log.handlers:
    _h = RotatingFileHandler(
        LOG_FILE, maxBytes=300_000, backupCount=2, encoding="utf-8"
    )
    _h.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
    _event_log.addHandler(_h)


def _new_state():
    return {
        "totals": {
            "messages": 0, "commands": 0,
            "chat_ok": 0, "chat_fail": 0, "chat_seconds": 0.0,
            "image_ok": 0, "image_fail": 0, "image_blocked": 0,
        },
        "users": {},
        "daily": {},
    }


def _load_state():
    state = _new_state()
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        for key in state:
            if key in saved:
                state[key].update(saved[key])
    except Exception:
        pass
    return state


_state = _load_state()


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _write_json(path, data):
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception as error:
        logging.warning("Could not write %s: %s", path, error)


def _save():
    _write_json(STATS_FILE, _state)


def _event(kind, user, detail=""):
    if not LOG_MESSAGE_TEXT and kind in ("MESSAGE", "COMMAND", "IMAGE-BLOCKED"):
        detail = "[hidden]"
    detail = (detail or "").replace("\n", " ")[:300]
    _event_log.info(
        "%s | %s (%s) | %s", kind, (user.first_name or "?"), user.id, detail
    )


def _daily(key):
    day = _state["daily"].setdefault(
        _today(), {"messages": 0, "images": 0, "errors": 0}
    )
    day[key] = day.get(key, 0) + 1
    for old in sorted(_state["daily"])[:-14]:
        del _state["daily"][old]


def _touch_user(user):
    rec = _state["users"].setdefault(
        str(user.id),
        {
            "name": "", "username": "", "first_seen": _now(),
            "last_seen": "", "messages": 0, "images": 0, "errors": 0,
        },
    )
    rec["name"] = user.first_name or ""
    rec["username"] = user.username or ""
    rec["last_seen"] = _now()
    return rec


_ctl = {"mtime": 0.0, "banned": set()}


def _banned():
    """Ban list written by admin_bot.py (re-read only when the file changes)."""
    try:
        mtime = os.path.getmtime(CONTROL_FILE)
        if mtime != _ctl["mtime"]:
            with open(CONTROL_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            _ctl["banned"] = {int(x) for x in data.get("banned", [])}
            _ctl["mtime"] = mtime
    except FileNotFoundError:
        _ctl["banned"] = set()
    except Exception:
        pass
    return _ctl["banned"]


def record(kind, user, ok=True, seconds=None, detail=""):
    """kind: 'chat', 'image' or 'blocked_image'."""
    totals = _state["totals"]
    rec = _touch_user(user)

    if kind == "chat":
        if ok:
            totals["chat_ok"] += 1
            if seconds is not None:
                totals["chat_seconds"] += seconds
        else:
            totals["chat_fail"] += 1
    elif kind == "image":
        if ok:
            totals["image_ok"] += 1
            rec["images"] += 1
            _daily("images")
        else:
            totals["image_fail"] += 1
    elif kind == "blocked_image":
        totals["image_blocked"] += 1

    if not ok:
        rec["errors"] += 1
        _daily("errors")

    label = {
        "chat": "CHAT-OK" if ok else "CHAT-FAIL",
        "image": "IMAGE-OK" if ok else "IMAGE-FAIL",
        "blocked_image": "IMAGE-BLOCKED",
    }[kind]
    _event(label, user, detail)
    _save()


async def _gate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Runs before every handler: tracks activity and enforces bans."""
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return

    rec = _touch_user(user)
    text = message.text or "[non-text]"

    if user.id in _banned():
        _event("BANNED-BLOCKED", user, text)
        _save()
        raise ApplicationHandlerStop

    if text.startswith("/"):
        _state["totals"]["commands"] += 1
        _event("COMMAND", user, text)
    else:
        _state["totals"]["messages"] += 1
        rec["messages"] += 1
        _daily("messages")
        _event("MESSAGE", user, text)
    _save()


async def _on_error(update, context: ContextTypes.DEFAULT_TYPE):
    logging.error("Unhandled error", exc_info=context.error)
    _event_log.info("UNHANDLED-ERROR | %s", str(context.error)[:300])


async def _heartbeat_loop():
    while True:
        _write_json(
            HEARTBEAT_FILE,
            {"ts": time.time(), "started": START_TIME, "active": bot_active},
        )
        await asyncio.sleep(20)


async def _post_init(app):
    app.bot_data["heartbeat"] = asyncio.create_task(_heartbeat_loop())


# ----------------------------------------------------------------------
# BOT
# ----------------------------------------------------------------------

def unsafe_image_prompt(prompt):
    text = prompt.lower()
    return any(term in text for term in BLOCKED_IMAGE_TERMS)


async def start_null(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_active
    bot_active = True
    await update.message.reply_text(
        "🚀 NULL AI is now ACTIVE!\n\n"
        "💬 Send a message to chat\n"
        "🎨 /image <prompt>"
    )


async def end_null(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_active
    bot_active = False
    await update.message.reply_text("🛑 NULL AI is now INACTIVE.")


async def image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active:
        return

    user = update.effective_user
    prompt = " ".join(context.args).strip()

    if not prompt:
        await update.message.reply_text("🎨 Usage:\n/image a futuristic city at night")
        return

    if unsafe_image_prompt(prompt):
        record("blocked_image", user, detail=prompt)
        await update.message.reply_text(
            "❌ I can't generate that image.\n\n"
            "Please use a safe, appropriate and non-explicit image prompt."
        )
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="upload_photo"
    )

    try:
        safe_prompt = prompt + ", safe and appropriate, non-explicit, fully clothed subjects"
        url = "https://gen.pollinations.ai/image/" + urllib.parse.quote(safe_prompt, safe="")
        headers = {"Authorization": f"Bearer {POLLINATIONS_API_KEY}"}

        response = requests.get(
            url, headers=headers, params={"model": IMAGE_MODEL}, timeout=180
        )

        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text[:300]}")

        if not response.headers.get("content-type", "").lower().startswith("image/"):
            raise Exception("API did not return an image.")

        image_file = io.BytesIO(response.content)
        image_file.name = "NULL_AI_image.jpg"

        await update.message.reply_photo(photo=image_file, caption=f"🎨 {prompt}")
        record("image", user, detail=prompt)

    except Exception as error:
        record("image", user, ok=False, detail=str(error))
        await update.message.reply_text("❌ Image generation failed. Try again later.")


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active:
        return

    user = update.effective_user
    user_msg = update.message.text
    t0 = time.time()

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    try:
        response = groq_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(reply)
        record("chat", user, seconds=time.time() - t0)

    except Exception as error:
        record("chat", user, ok=False, detail=str(error))
        await update.message.reply_text("❌ AI error. Try again later.")


def main():
    print("🤖 NULL AI BOT starting...")

    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(_post_init)
        .build()
    )

    app.add_handler(TypeHandler(Update, _gate), group=-1)
    app.add_handler(CommandHandler("STARTnull", start_null))
    app.add_handler(CommandHandler("ENDnull", end_null))
    app.add_handler(CommandHandler("image", image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    app.add_error_handler(_on_error)

    print("✅ Bot is running. Send /STARTnull to activate.")
    app.run_polling()


if __name__ == "__main__":
    main()
