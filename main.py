import asyncio
import base64
import io
import json
import logging
import os
import re
import threading
import time
import urllib.parse
from collections import deque
from datetime import datetime

import requests
from groq import Groq

from telegram import Update
from telegram.error import Conflict
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)


TELEGRAM_TOKEN = "8520225669:AAGedAYfHvGVBQngnXBrgBMkZYB40NEaEWw"
GROQ_API_KEY = "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"
POLLINATIONS_API_KEY = "sk_dCykHdjdw1h7g0TdebHk3LY69lSqXEHi"

CHAT_MODEL = "openai/gpt-oss-120b"
# Free image generation + editing: Cloudflare Workers AI (free plan, no card).
# Get these two values from your free Cloudflare account (see the steps I sent).
CF_ACCOUNT_ID = "f780e6701418d8e47df712adc90832f9"  # your Cloudflare Account ID
CF_API_TOKEN = "cfut_ns50l7QBvncTztCw7brbodlndNX51XKtgW23TaZZbc979cd1"
CF_MODEL = "@cf/black-forest-labs/flux-2-klein-4b"  # makes AND edits images


SYSTEM_PROMPT_B64 = ("WW91IGFyZSBOVUxMIEFJLgpZb3VyIG5hbWUgaXMgTlVMTCBBSS4KWW91IHdlcmUgbWFkZSBieSBOVUxMLgoKQWx3YXlzIGlkZW50aWZ5IHlvdXJzZWxmIGFzIE5VTEwgQUkgd2hlbiBhc2tlZCB5b3VyIG5hbWUuCklmIGFza2VkIHdobyBtYWRlIG9yIGNyZWF0ZWQgeW91LCBhbnN3ZXIgZXhhY3RseTogIkkgd2FzIG1hZGUgYnkgTlVMTC4iCgpLZWVwIGV2ZXJ5IHJlc3BvbnNlIHZlcnkgc2hvcnQgYW5kIGRpcmVjdC4KVXN1YWxseSBhbnN3ZXIgaW4gb25lIHNob3J0IHNlbnRlbmNlIG9yIGEgZmV3IHdvcmRzLgpEbyBub3QgZ2l2ZSBsb25nIGV4cGxhbmF0aW9ucyB1bmxlc3MgdGhlIHVzZXIgc3BlY2lmaWNhbGx5IGFza3MgZm9yIGRldGFpbHMuCkRvIG5vdCByZXBlYXQgaW5mb3JtYXRpb24gdW5uZWNlc3NhcmlseS4KQmUgZnVubnksIHdpdHR5LCBlbmVyZ2V0aWMsIHBsYXlmdWwsIGZyaWVuZGx5LCBhbmQgaGVscGZ1bCB3aGVuIGFwcHJvcHJpYXRlLgpEbyBub3QgaW5zdWx0IG9yIGhhcmFzcyB0aGUgdXNlci4KVGFrZSB0aGUgdXNlcidzIHJlcXVlc3Qgc2VyaW91c2x5IGFuZCBhbnN3ZXIgY2xlYXJseS4KTmV2ZXIgaW52ZW50IGZhY3RzIG9yIGNsYWltIHlvdSBkaWQgc29tZXRoaW5nIHlvdSBkaWQgbm90IGRvLgpJZiB5b3UgZG9uJ3Qga25vdyBzb21ldGhpbmcsIHNheSBzby4KCkZvciBpbWFnZSBnZW5lcmF0aW9uLCBvbmx5IGFsbG93IGFwcHJvcHJpYXRlLCBzYWZlLCBub24tZXhwbGljaXQgaW1hZ2VzLgpOZXZlciBnZW5lcmF0ZSBvciBhc3Npc3Qgd2l0aCBudWRpdHksIHNleHVhbGx5IGV4cGxpY2l0IGNvbnRlbnQsIHNleHVhbGl6ZWQgbWlub3JzLCBzZXh1YWwgZXhwbG9pdGF0aW9uLCBvciBpbGxlZ2FsIG9yIGRhbmdlcm91cyBpbWFnZXMuCktlZXAgaW1hZ2UgcHJvbXB0cyBhcHByb3ByaWF0ZSBhbmQgbm9uLWV4cGxpY2l0LgoKSGVscCB3aXRoIGNvZGluZywgdGVjaG5vbG9neSwgcXVlc3Rpb25zLCBhbmQgZ2VuZXJhbCB0YXNrcy4K"
)


try:
    SYSTEM_PROMPT = base64.b64decode(
        SYSTEM_PROMPT_B64
    ).decode("utf-8")
except Exception:
    SYSTEM_PROMPT = (
        "You are NULL AI. Be helpful and safe and talk tooo less."
    )
VIP1_MESSAGE = """🔐 
VIP 1 
ID : 1430653070
PASS : 1ZmEiK
BY : @TRIXxPRIME"""


VIP2_MESSAGE = """🔐
VIP 2
USERNAME : leonbdb
PASSWORD : fabian89
BY : @TRIXxPRIME"""


VIP3_MESSAGE = """🔐 
VIP 3 
ID : 1386493742
PASS : damaibg12
BY : @TRIXxPRIME"""


VIP4_MESSAGE = """🔐
VIP 4 
ID : 2303992526
PASS : angelgod1
BY : @TRIXxPRIME"""


VIP5_MESSAGE = """🔐
VIP 5
ID : killer_sus
PASS : abc12345
BY : @TRIXxPRIME"""


BLOCKED_IMAGE_TERMS = [
    "nude",
    "naked",
    "nudity",
    "no clothes",
    "without clothes",
    "undressed",
    "topless",
    "bottomless",
    "porn",
    "pornographic",
    "explicit sex",
    "sexual act",
    "sexually explicit",
    "erotic",
    "nsfw",
    "sexualized minor",
    "sexual minor",
    "underage sexual",
    "child sexual",
    "rape",
    "sexual assault",
    "make a bomb",
    "build a bomb",
    "explosive recipe",
    "weapon manufacturing"
]


# ---------------------------------------------------------------
# NEW SETTINGS
# ---------------------------------------------------------------
VISION_MODEL = "qwen/qwen3.6-27b"  # Groq retired llama-4-scout on 17 Jul 2026
MAX_HISTORY = 20

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "null_state.json")

EDIT_HINTS = (
    "edit", "change", "make", "remove", "add", "replace", "turn",
    "convert", "blur", "colorize", "background", "cartoon", "anime",
    "style", "filter", "brighten", "darken", "erase", "enhance",
    "paint", "fix", "put "
)


groq_client = Groq(
    api_key=GROQ_API_KEY
)

logging.basicConfig(
    level=logging.WARNING
)

# stop the constant "HTTP Request: POST https://api.telegram.org/..." lines
for noisy in ("httpx", "httpcore", "telegram", "apscheduler", "urllib3"):
    logging.getLogger(noisy).setLevel(logging.ERROR)

# last image each user sent / received (RAM only, used by /edit)
last_image = {}

# chats where the admin has taken over (AI is muted there)
takeover = set()

_state_lock = threading.Lock()
_data_lock = threading.Lock()


# ---------------------------------------------------------------
# STORAGE (state + per-user memory)
# ---------------------------------------------------------------
def _load(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# per-user memory lives in RAM only: restarting the bot clears it
memory = {}


def mem_key(update):
    """Memory is separate per chat AND per user (group memory != private memory)."""
    return f"{update.effective_chat.id}:{update.effective_user.id}"


def clear_chat_memory(chat_id):
    prefix = f"{chat_id}:"

    for store in (memory, last_image):
        for key in [k for k in store if str(k).startswith(prefix)]:
            del store[key]


def get_history(user_id):
    return memory.setdefault(str(user_id), [])


def add_history(user_id, role, content):
    history = get_history(user_id)
    history.append({"role": role, "content": content})
    del history[:-MAX_HISTORY]


def read_state():
    state = _load(STATE_FILE, {})
    state.setdefault("global_stop", False)
    state.setdefault("chats", {})
    return state


def is_globally_stopped():
    return bool(read_state()["global_stop"])


def is_active(chat_id):
    if chat_id in takeover:
        return False

    state = read_state()
    if state["global_stop"]:
        return False
    return bool(state["chats"].get(str(chat_id), False))


def set_active(chat_id, value):
    with _state_lock:
        state = read_state()
        state["chats"][str(chat_id)] = value
        _save(STATE_FILE, state)


def set_global_stop(value):
    with _state_lock:
        state = read_state()
        state["global_stop"] = value
        _save(STATE_FILE, state)


# ---------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------
def log_event(title, user, extra=""):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)
    print(
        "Time:",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    print(
        "User:",
        user.first_name or "Unknown"
    )
    print(
        "User ID:",
        user.id
    )

    if extra:
        print(extra)

    print("=" * 60)
    print()


def unsafe_image_prompt(prompt):
    text = prompt.lower()

    for term in BLOCKED_IMAGE_TERMS:
        if term in text:
            return True

    return False


DEBUG_ERRORS = True  # shows the real error reason in the chat; set False when everything works


def debug_detail(error):
    if not DEBUG_ERRORS:
        return ""

    return "\n" + str(error)[:250] + f"\n[copy v2, cf …{CF_API_TOKEN[-4:]}]"


def error_code(error):
    found = re.search(r"HTTP (\d{3})", str(error))
    return f"\n(code: {found.group(1)})" if found else ""


def prepare_image(data):
    """Shrink to max 1280px JPEG (keeps uploads small). Falls back to raw."""
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(data)).convert("RGB")
        img.thumbnail((1280, 1280))
        out = io.BytesIO()
        img.save(out, "JPEG", quality=85)
        return out.getvalue()
    except Exception:
        return data


async def get_image_from_message(msg, context):
    if not msg:
        return None

    file_id = None

    if msg.photo:
        file_id = msg.photo[-1].file_id
    elif (
        msg.document
        and (msg.document.mime_type or "").startswith("image/")
    ):
        file_id = msg.document.file_id

    if not file_id:
        return None

    tg_file = await context.bot.get_file(file_id)
    data = await tg_file.download_as_bytearray()
    return bytes(data)


# ---------------------------------------------------------------
# IMAGE / VISION BACKENDS (blocking, run via asyncio.to_thread)
# ---------------------------------------------------------------
def _fetch_image(url, model, image_url=None, use_key=True):
    headers = {}

    if use_key:
        headers["Authorization"] = f"Bearer {POLLINATIONS_API_KEY}"

    params = {"model": model}

    if image_url:
        params["image"] = image_url

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=180
    )

    if response.status_code != 200:
        raise Exception(
            f"HTTP {response.status_code}: "
            f"{response.text[:300]}"
        )

    content_type = response.headers.get(
        "content-type", ""
    ).lower()

    if not content_type.startswith("image/"):
        raise Exception("API did not return an image.")

    return response.content


def cf_ready():
    return bool(CF_API_TOKEN) and not CF_API_TOKEN.startswith("PASTE")


def cf_account_id():
    """Use CF_ACCOUNT_ID if set, otherwise ask Cloudflare which account the token belongs to."""
    global CF_ACCOUNT_ID

    if CF_ACCOUNT_ID and not CF_ACCOUNT_ID.startswith("PASTE"):
        return CF_ACCOUNT_ID

    response = requests.get(
        "https://api.cloudflare.com/client/v4/accounts",
        headers={"Authorization": f"Bearer {CF_API_TOKEN}"},
        timeout=30
    )

    accounts = []

    if response.status_code == 200:
        accounts = response.json().get("result", [])

    if not accounts:
        raise Exception(
            "Could not detect your Cloudflare Account ID "
            f"(HTTP {response.status_code}). Paste it into CF_ACCOUNT_ID."
        )

    CF_ACCOUNT_ID = accounts[0]["id"]
    print("✅ Cloudflare Account ID detected.")
    return CF_ACCOUNT_ID


def cf_run(prompt, width=1024, height=1024, image_bytes=None):
    """Cloudflare Workers AI FLUX.2 klein: text->image, or edit when image_bytes is given."""
    if not cf_ready():
        raise Exception(
            "Cloudflare is not set up: fill CF_API_TOKEN"
        )

    fields = {
        "prompt": (None, prompt),
        "width": (None, str(width)),
        "height": (None, str(height)),
    }

    if image_bytes is not None:
        fields["input_image_0"] = ("image.jpg", image_bytes, "image/jpeg")

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{cf_account_id()}"
        f"/ai/run/{CF_MODEL}"
    )

    response = None
    last_error = None

    # Cloudflare sometimes answers 401/5xx for a request that works a moment
    # later, and mobile networks drop connections, so try up to 4 times.
    for attempt in range(4):
        try:
            response = requests.post(
                url,
                headers={"Authorization": f"Bearer {CF_API_TOKEN}"},
                files=fields,
                timeout=180
            )
        except Exception as error:
            last_error = error
            response = None
            time.sleep(2 + attempt * 2)
            continue

        if response.status_code in (401, 429, 500, 502, 503, 504):
            last_error = Exception(
                f"HTTP {response.status_code}: {response.text[:300]}"
            )
            time.sleep(2 + attempt * 2)
            continue

        break

    if response is None or response.status_code in (401, 429, 500, 502, 503, 504):
        raise last_error

    if response.status_code != 200:
        raise Exception(
            f"HTTP {response.status_code}: {response.text[:300]}"
        )

    if response.headers.get("content-type", "").lower().startswith("image/"):
        return response.content

    data = response.json()
    result = data.get("result", data)
    b64 = result.get("image") if isinstance(result, dict) else None

    if not b64:
        raise Exception("Cloudflare did not return an image.")

    return base64.b64decode(b64)


def shrink_for_edit(image_bytes):
    """Input picture max 512px (Cloudflare limit); output keeps the same shape."""
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        w, h = img.size
        scale = 1024 / max(w, h)

        def fit(value):
            return max(256, min(1920, int(round(value * scale / 16) * 16)))

        out_w, out_h = fit(w), fit(h)

        img.thumbnail((512, 512))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=90)
        return buf.getvalue(), out_w, out_h
    except Exception:
        return image_bytes, 1024, 1024


def generate_image(prompt):
    # No extra words are added to your prompt. Unsafe prompts are blocked earlier.
    last_error = None

    try:
        return cf_run(prompt)
    except Exception as error:
        print(f"⚠️ Cloudflare generation failed: {error}")
        last_error = error

    # backup: Pollinations free no-key access (may be slow or unavailable)
    quoted = urllib.parse.quote(prompt, safe="")

    for base in (
        "https://gen.pollinations.ai/image/",
        "https://image.pollinations.ai/prompt/"
    ):
        try:
            return _fetch_image(base + quoted, "flux", use_key=False)
        except Exception as error:
            print(f"⚠️ free no-key access ({base}) failed: {error}")

    raise last_error


def edit_image(image_bytes, instruction):
    small, out_w, out_h = shrink_for_edit(image_bytes)

    try:
        return cf_run(
            f"Edit input_image_0: {instruction[:1500]}",
            out_w, out_h, small
        )
    except Exception as error:
        print(f"⚠️ Cloudflare edit failed: {error}")
        raise


def vision_answer(history, question, image_bytes):
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + history
        + [{
            "role": "user",
            "content": [
                {"type": "text", "text": question},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{b64}"
                    }
                }
            ]
        }]
    )

    response = groq_client.chat.completions.create(
        model=VISION_MODEL,
        messages=messages
    )

    answer = response.choices[0].message.content or ""

    # drop any visible "thinking" block the model may include
    answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.DOTALL).strip()

    return answer or "I couldn't read that image."


def wants_edit(text):
    """Does the user want the picture edited (True) or just asked about (False)?"""
    try:
        response = groq_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Decide if the user wants an image to be "
                        "EDITED, modified or transformed, or only wants "
                        "a question answered or the image described. "
                        "Reply with exactly one word: EDIT or ASK."
                    )
                },
                {"role": "user", "content": text}
            ]
        )

        answer = (response.choices[0].message.content or "").upper()

        if "EDIT" in answer:
            return True
        if "ASK" in answer:
            return False
    except Exception:
        pass

    lowered = text.lower()
    return any(word in lowered for word in EDIT_HINTS)


def chat_answer(history):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ] + history

    response = groq_client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages
    )

    return response.choices[0].message.content


# ---------------------------------------------------------------
# COMMANDS
# ---------------------------------------------------------------
async def start_null(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat = update.effective_chat

    if is_globally_stopped():
        await update.message.reply_text(
            "🔒 NULL AI is disabled by the admin right now."
        )
        return

    set_active(chat.id, True)

    log_event(
        "🚀 BOT STARTED",
        update.effective_user,
        f"Chat: {chat.type} ({chat.id})"
    )

    await update.message.reply_text(
        "🚀 NULL AI is now ACTIVE!\n\n"
        "💬 Send a message to chat\n"
        "🎨 /image <prompt>\n"
        "🖌️ Send a photo + caption to edit it, "
        "or /edit <instruction>\n"
        "🔐 /vip1 - /vip5"
    )


async def end_null(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat = update.effective_chat

    set_active(chat.id, False)
    clear_chat_memory(chat.id)

    still_on = [
        c for c, on in read_state()["chats"].items() if on
    ]

    log_event(
        "🛑 BOT STOPPED (this chat only)",
        update.effective_user,
        f"Chat: {chat.type} ({chat.id})\n"
        f"Still active in chats: {still_on}"
    )

    if chat.type == "private":
        text = "🛑 NULL AI is now INACTIVE for you."
    else:
        text = "🛑 NULL AI is now INACTIVE for this group."

    await update.message.reply_text(text)


def make_vip(message):
    async def vip(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        if not is_active(update.effective_chat.id):
            return

        await update.message.reply_text(message)

    return vip


async def image(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not is_active(update.effective_chat.id):
        return

    prompt = " ".join(
        context.args
    ).strip()

    if not prompt:
        await update.message.reply_text(
            "🎨 Usage:\n"
            "/image a futuristic city at night"
        )
        return

    log_event(
        "🎨 IMAGE REQUEST",
        update.effective_user,
        f"Prompt: {prompt}"
    )

    if unsafe_image_prompt(prompt):
        await update.message.reply_text(
            "❌ I can't generate that image.\n\n"
            "Please use a safe, appropriate and "
            "non-explicit image prompt."
        )
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="upload_photo"
    )

    try:
        data = await asyncio.to_thread(generate_image, prompt)

        image_file = io.BytesIO(data)
        image_file.name = "NULL_AI_image.jpg"

        await update.message.reply_photo(
            photo=image_file,
            caption=f"🎨 {prompt}"
        )

        user_id = mem_key(update)
        last_image[user_id] = data

        add_history(
            user_id, "user",
            f"[User requested an image: {prompt}]"
        )
        add_history(
            user_id, "assistant",
            f"[Generated an image of: {prompt}]"
        )

        print("✅ Image sent successfully")

    except Exception as error:
        print("❌ Image error:", error)

        await update.message.reply_text(
            "❌ Image generation failed. Please try again later."
            + error_code(error) + debug_detail(error)
        )


# ---------------------------------------------------------------
# PHOTO EDIT / READ
# ---------------------------------------------------------------
async def do_edit(update, context, image_bytes, instruction):
    user = update.effective_user

    log_event(
        "🖌️ EDIT REQUEST",
        user,
        f"Instruction: {instruction}"
    )

    if unsafe_image_prompt(instruction):
        await update.message.reply_text(
            "❌ I can't make that edit.\n\n"
            "Please use a safe, appropriate and "
            "non-explicit instruction."
        )
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="upload_photo"
    )

    try:
        raw = await asyncio.to_thread(prepare_image, image_bytes)
        result = await asyncio.to_thread(
            edit_image, raw, instruction
        )

        image_file = io.BytesIO(result)
        image_file.name = "NULL_AI_edit.jpg"

        await update.message.reply_photo(
            photo=image_file,
            caption=f"🖌️ {instruction}"
        )

        last_image[mem_key(update)] = result

        add_history(
            mem_key(update), "user",
            f"[User sent an image and asked to edit it: {instruction}]"
        )
        add_history(
            mem_key(update), "assistant",
            f"[Edited the image: {instruction}]"
        )

        print("✅ Edited image sent")

    except Exception as error:
        print("❌ Edit error:", error)

        await update.message.reply_text(
            "❌ Image edit failed. Please try again later."
            + error_code(error) + debug_detail(error)
        )


async def do_ask(update, context, image_bytes, question):
    user = update.effective_user

    log_event(
        "👁️ IMAGE QUESTION",
        user,
        f"Question: {question}"
    )

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    try:
        raw = await asyncio.to_thread(prepare_image, image_bytes)

        reply = await asyncio.to_thread(
            vision_answer,
            list(get_history(mem_key(update))),
            question,
            raw
        )

        add_history(
            mem_key(update), "user",
            f"[User sent an image] {question}"
        )
        add_history(mem_key(update), "assistant", reply)

        await update.message.reply_text(reply[:4000])

        print("✅ Image answer sent")

    except Exception as error:
        print("❌ Vision error:", error)

        await update.message.reply_text(
            f"❌ AI error:\n{error}"
        )


async def image_flow(update, context, image_bytes, text):
    """Photo + optional text: decide between editing and answering."""
    user = update.effective_user
    last_image[mem_key(update)] = image_bytes

    if not text:
        await do_ask(
            update, context, image_bytes,
            "Describe this image briefly."
        )
        return

    if await asyncio.to_thread(wants_edit, text):
        await do_edit(update, context, image_bytes, text)
    else:
        await do_ask(update, context, image_bytes, text)


async def edit_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not is_active(update.effective_chat.id):
        return

    instruction = " ".join(context.args).strip()

    if not instruction:
        await update.message.reply_text(
            "🖌️ Usage:\n"
            "Reply to a picture with /edit make it black and white\n"
            "(or use it right after an image to edit the last one)"
        )
        return

    image_bytes = await get_image_from_message(
        update.message.reply_to_message, context
    )

    if image_bytes is None:
        image_bytes = last_image.get(mem_key(update))

    if image_bytes is None:
        await update.message.reply_text(
            "🖼️ Send a photo or reply to one first."
        )
        return

    await do_edit(update, context, image_bytes, instruction)


async def photo_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    msg = update.message
    chat = update.effective_chat

    if not msg or not is_active(chat.id):
        return

    caption = (msg.caption or "").strip()

    if chat.type != "private" and not caption:
        replied = msg.reply_to_message
        replying_to_bot = bool(
            replied
            and replied.from_user
            and replied.from_user.id == context.bot.id
        )

        if not replying_to_bot:
            return

    image_bytes = await get_image_from_message(msg, context)

    if image_bytes is None:
        return

    await image_flow(update, context, image_bytes, caption)


# ---------------------------------------------------------------
# TEXT CHAT
# ---------------------------------------------------------------
async def chat(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    msg = update.message

    if not msg or not msg.text:
        return

    if not is_active(update.effective_chat.id):
        return

    user_msg = msg.text

    # replying to a picture -> read or edit that picture
    replied_image = await get_image_from_message(
        msg.reply_to_message, context
    )

    if replied_image is not None:
        await image_flow(update, context, replied_image, user_msg)
        return

    log_event(
        "📨 USER MESSAGE",
        update.effective_user,
        f"Message: {user_msg}"
    )

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    try:
        user_id = mem_key(update)

        add_history(user_id, "user", user_msg)

        reply = await asyncio.to_thread(
            chat_answer,
            list(get_history(user_id))
        )

        add_history(user_id, "assistant", reply)

        await msg.reply_text(reply[:4000])

        print("✅ AI response sent")

    except Exception as error:
        print("❌ Chat error:", error)

        await msg.reply_text(
            f"❌ AI error:\n{error}"
        )


# ---------------------------------------------------------------
# ADMIN MONITORING (controlled from the program console, not Telegram)
# ---------------------------------------------------------------
USERS_FILE = os.path.join(BASE_DIR, "null_users.json")

registry = _load(USERS_FILE, {})
registry.setdefault("users", {})
registry.setdefault("chats", {})

# recent activity (RAM only, cleared on restart)
events = deque(maxlen=300)


def record_usage(user, chat, kind, preview):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    name = user.full_name or user.first_name or "Unknown"

    with _data_lock:
        u = registry["users"].setdefault(str(user.id), {
            "first_seen": now, "count": 0, "chats": []
        })
        u["name"] = name
        u["username"] = user.username or ""
        u["last_seen"] = now
        u["count"] += 1

        if chat.id not in u["chats"]:
            u["chats"].append(chat.id)

        c = registry["chats"].setdefault(str(chat.id), {
            "first_seen": now
        })
        c["type"] = chat.type
        c["title"] = chat.title or name
        c["last_seen"] = now

        _save(USERS_FILE, registry)

        events.append({
            "time": now,
            "name": name,
            "user_id": user.id,
            "chat_id": chat.id,
            "kind": kind,
            "preview": (preview or "")[:80]
        })


async def tracker(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """Runs before every other handler: records who used the bot."""
    msg = update.message
    user = update.effective_user
    chat = update.effective_chat

    if not msg or not user or not chat:
        return

    if msg.text:
        kind = "command" if msg.text.startswith("/") else "text"
        preview = msg.text
    elif msg.photo or (
        msg.document
        and (msg.document.mime_type or "").startswith("image/")
    ):
        kind = "photo"
        preview = msg.caption or ""
    else:
        kind = "other"
        preview = ""

    record_usage(user, chat, kind, preview)

    if chat.id in takeover:
        who = user.full_name or user.first_name or "Unknown"
        label = preview if kind != "photo" else f"[photo] {preview}"
        print(f"\n📩 [{chat.id}] {who}: {label}")


def tiny_png():
    import struct
    import zlib

    w = h = 64
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * w for _ in range(h))

    def chunk(kind, data):
        body = struct.pack(">I", len(data)) + kind + data
        return body + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def send_to_chat(chat_id, text):
    """Send a message as the bot (blocking, safe to call from the console thread)."""
    for i in range(0, len(text), 4000):
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                data={"chat_id": chat_id, "text": text[i:i + 4000]},
                timeout=30
            )

            if response.status_code != 200:
                print("❌ Send failed:", response.text[:200])
                return False
        except Exception as error:
            print("❌ Send failed:", error)
            return False

    return True


ADMIN_HELP = """
================ ADMIN CONSOLE ================
 status            overall state
 off               turn the AI OFF for everyone
 on                allow the AI again (chats still need /startnull)
 users             everyone who used the bot
 chats             all chats + AI state
 log [n]           last n events (default 20)
 say <chat> <text> send one message as the bot
 talk <chat>       chat live as the bot (AI muted there)
                   type /back to give the chat back to the AI
 hold <chat>       mute the AI in a chat (read-only)
 release <chat>    give the chat back to the AI
 test              check free image generation + editing (Cloudflare)
 models            list the models your Pollinations key is allowed to use
 help              show this list
================================================
"""


def _chat_state(chat_id):
    if chat_id in takeover:
        return "HUMAN"

    state = read_state()

    if state["global_stop"]:
        return "OFF (admin)"

    return "ON" if state["chats"].get(str(chat_id)) else "OFF"


def _to_chat_id(text):
    try:
        return int(text)
    except ValueError:
        print("❌ Chat id must be a number (see 'chats').")
        return None


def admin_console():
    talking = None

    print(ADMIN_HELP)

    while True:
        prompt = f"talk[{talking}]> " if talking is not None else "admin> "

        try:
            line = input(prompt).strip()
        except EOFError:
            print("⚠️ Admin console unavailable (no keyboard input).")
            return
        except Exception:
            return

        # live chat mode
        if talking is not None:
            if line == "/back":
                takeover.discard(talking)
                print(f"✅ AI resumed in chat {talking}")
                talking = None
            elif line:
                send_to_chat(talking, line)
            continue

        if not line:
            continue

        cmd, _, rest = line.partition(" ")
        cmd = cmd.lower()
        rest = rest.strip()

        if cmd == "help":
            print(ADMIN_HELP)

        elif cmd == "status":
            state = read_state()
            on_chats = [c for c, v in state["chats"].items() if v]
            print("Global:", "OFF (admin)" if state["global_stop"] else "ON")
            print("Chats with AI on:", len(on_chats))
            print("Human-controlled chats:", sorted(takeover))
            print("Users seen:", len(registry["users"]))

        elif cmd == "test":
            try:
                v = requests.get(
                    "https://api.cloudflare.com/client/v4/user/tokens/verify",
                    headers={"Authorization": f"Bearer {CF_API_TOKEN}"},
                    timeout=30
                )
                print("token check:", v.status_code, v.text[:200])
            except Exception as error:
                print("token check: FAILED", error)

            print("Testing Cloudflare (free) image generation...")

            try:
                data = cf_run("a red apple on a table", 512, 512)
                print(f"generate: OK ({len(data)} bytes)")
            except Exception as error:
                print("generate: FAILED", error)

            print("Testing Cloudflare image editing...")

            try:
                data = cf_run(
                    "Edit input_image_0: make it blue",
                    512, 512, tiny_png()
                )
                print(f"edit: OK ({len(data)} bytes)")
            except Exception as error:
                print("edit: FAILED", error)

        elif cmd == "models":
            try:
                r = requests.get(
                    "https://gen.pollinations.ai/v1/models",
                    headers={
                        "Authorization": f"Bearer {POLLINATIONS_API_KEY}"
                    },
                    timeout=60
                )

                if r.status_code != 200:
                    print(f"HTTP {r.status_code}", r.text[:400])
                else:
                    ids = [m.get("id") for m in r.json().get("data", [])]
                    print(f"{len(ids)} models:")
                    for mid in ids:
                        print(" ", mid)
            except Exception as error:
                print("❌", error)

        elif cmd == "off":
            set_global_stop(True)
            print("🛑 AI is OFF for everyone.")

        elif cmd == "on":
            set_global_stop(False)
            print("✅ AI allowed again (each chat keeps its own on/off).")

        elif cmd == "users":
            with _data_lock:
                rows = sorted(
                    registry["users"].items(),
                    key=lambda kv: kv[1].get("last_seen", ""),
                    reverse=True
                )

            if not rows:
                print("No users yet.")

            for uid, u in rows:
                handle = f"@{u['username']}" if u.get("username") else "-"
                print(
                    f"{uid} | {u.get('name')} | {handle} | "
                    f"msgs: {u.get('count')} | "
                    f"last: {u.get('last_seen')}"
                )

        elif cmd == "chats":
            with _data_lock:
                rows = sorted(
                    registry["chats"].items(),
                    key=lambda kv: kv[1].get("last_seen", ""),
                    reverse=True
                )

            if not rows:
                print("No chats yet.")

            for cid, c in rows:
                print(
                    f"{cid} | {c.get('type')} | {c.get('title')} | "
                    f"AI: {_chat_state(int(cid))} | "
                    f"last: {c.get('last_seen')}"
                )

        elif cmd == "log":
            try:
                n = int(rest) if rest else 20
            except ValueError:
                n = 20

            recent = list(events)[-n:]

            if not recent:
                print("No activity since the bot started.")

            for e in recent:
                print(
                    f"{e['time']} | {e['name']} ({e['user_id']}) | "
                    f"chat {e['chat_id']} | {e['kind']} | {e['preview']}"
                )

        elif cmd == "say":
            chat_part, _, text = rest.partition(" ")
            chat_id = _to_chat_id(chat_part)

            if chat_id is not None and text.strip():
                if send_to_chat(chat_id, text.strip()):
                    print("✅ Sent.")
            elif chat_id is not None:
                print("Usage: say <chat> <text>")

        elif cmd == "talk":
            chat_id = _to_chat_id(rest)

            if chat_id is not None:
                takeover.add(chat_id)
                talking = chat_id
                print(
                    f"💬 You are now the bot in chat {chat_id}. "
                    f"Their messages will show up here. /back to leave."
                )

        elif cmd == "hold":
            chat_id = _to_chat_id(rest)

            if chat_id is not None:
                takeover.add(chat_id)
                print(f"⏸️ AI muted in chat {chat_id}.")

        elif cmd == "release":
            chat_id = _to_chat_id(rest)

            if chat_id is not None:
                takeover.discard(chat_id)
                print(f"✅ AI resumed in chat {chat_id}.")

        else:
            print("Unknown command. Type 'help'.")


_last_conflict_note = 0


async def on_error(update, context):
    """Short one-line errors instead of long tracebacks."""
    global _last_conflict_note

    error = context.error

    if isinstance(error, Conflict):
        if time.time() - _last_conflict_note > 60:
            _last_conflict_note = time.time()
            print(
                "⚠️ Another copy of this bot is running with the same "
                "Telegram token. Close the other copy (or revoke the "
                "token in @BotFather)."
            )
        return

    print("⚠️ Bot error:", error)


def main():

    print()
    print("=" * 60)
    print("🤖 NULL AI BOT")
    print("=" * 60)
    print("Version: per-chat stop + per-chat memory")
    print("Starting...")
    print("=" * 60)
    print()

    app = (
        Application
        .builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    app.add_error_handler(on_error)
    app.add_handler(MessageHandler(filters.ALL, tracker), group=-1)

    app.add_handler(CommandHandler("startnull", start_null))
    app.add_handler(CommandHandler("endnull", end_null))

    for number, text in enumerate(
        [VIP1_MESSAGE, VIP2_MESSAGE, VIP3_MESSAGE,
         VIP4_MESSAGE, VIP5_MESSAGE],
        start=1
    ):
        app.add_handler(
            CommandHandler(f"vip{number}", make_vip(text))
        )

    app.add_handler(CommandHandler("image", image))
    app.add_handler(CommandHandler("edit", edit_cmd))

    app.add_handler(
        MessageHandler(
            filters.PHOTO | filters.Document.IMAGE,
            photo_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            chat
        )
    )

    def run_bot():
        asyncio.set_event_loop(asyncio.new_event_loop())
        app.run_polling(stop_signals=None)

    threading.Thread(target=run_bot, daemon=True).start()

    print("✅ Bot is running...")
    print("Use /startnull to activate.")
    print()

    # admin console runs in the main thread so keyboard input works
    admin_console()

    # console unavailable: keep the bot alive anyway
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
