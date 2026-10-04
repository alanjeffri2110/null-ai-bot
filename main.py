import asyncio
import base64
import io
import json
import logging
import os
import urllib.parse
from datetime import datetime

import requests
from groq import Groq

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)


TELEGRAM_TOKEN = "8520225669:AAERew_ylB8Mu55MJU2_zX7hNITKPQJeLp4"
GROQ_API_KEY = "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"
POLLINATIONS_API_KEY = "sk_hv35IevattTrTacC4Os8yR3jBfZMLfFt"

CHAT_MODEL = "openai/gpt-oss-120b"
IMAGE_MODEL = "flux"


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
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
EDIT_MODEL = "kontext"
EDIT_FALLBACK_MODEL = "black-forest-labs/flux.2-klein-4b"
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
    level=logging.INFO
)

# last image each user sent / received (RAM only, used by /edit)
last_image = {}


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
    state = read_state()
    if state["global_stop"]:
        return False
    return bool(state["chats"].get(str(chat_id), False))


def set_active(chat_id, value):
    state = read_state()
    state["chats"][str(chat_id)] = value
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
def _fetch_image(url, model, image_url=None):
    headers = {
        "Authorization": f"Bearer {POLLINATIONS_API_KEY}"
    }

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


def generate_image(prompt):
    safe_prompt = (
        prompt
        + ", safe and appropriate, "
        + "non-explicit, fully clothed subjects"
    )

    url = (
        "https://gen.pollinations.ai/image/"
        + urllib.parse.quote(safe_prompt, safe="")
    )

    return _fetch_image(url, IMAGE_MODEL)


def edit_image(image_bytes, instruction):
    """Edit via Pollinations /v1/images/edits (direct upload, no 3rd-party host)."""
    safe_prompt = (
        instruction[:2000]
        + ", safe and appropriate, non-explicit"
    )

    last_error = None

    for model in (EDIT_MODEL, EDIT_FALLBACK_MODEL):
        try:
            response = requests.post(
                "https://gen.pollinations.ai/v1/images/edits",
                headers={
                    "Authorization": f"Bearer {POLLINATIONS_API_KEY}"
                },
                data={
                    "prompt": safe_prompt,
                    "model": model,
                    "response_format": "b64_json"
                },
                files={
                    "image": ("image.jpg", image_bytes, "image/jpeg")
                },
                timeout=180
            )

            if response.status_code != 200:
                raise Exception(
                    f"HTTP {response.status_code}: "
                    f"{response.text[:300]}"
                )

            item = response.json()["data"][0]

            if item.get("b64_json"):
                return base64.b64decode(item["b64_json"])

            if item.get("url"):
                return requests.get(item["url"], timeout=120).content

            raise Exception("API did not return an image.")

        except Exception as error:
            last_error = error

    raise last_error


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

    return response.choices[0].message.content


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

    log_event(
        "🛑 BOT STOPPED",
        update.effective_user,
        f"Chat: {chat.type} ({chat.id})"
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

        user_id = update.effective_user.id
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
            "❌ Image generation failed.\n\n"
            f"Reason: {error}"
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

        last_image[user.id] = result

        add_history(
            user.id, "user",
            f"[User sent an image and asked to edit it: {instruction}]"
        )
        add_history(
            user.id, "assistant",
            f"[Edited the image: {instruction}]"
        )

        print("✅ Edited image sent")

    except Exception as error:
        print("❌ Edit error:", error)

        await update.message.reply_text(
            "❌ Image edit failed.\n\n"
            f"Reason: {error}"
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
            list(get_history(user.id)),
            question,
            raw
        )

        add_history(
            user.id, "user",
            f"[User sent an image] {question}"
        )
        add_history(user.id, "assistant", reply)

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
    last_image[user.id] = image_bytes

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
        image_bytes = last_image.get(update.effective_user.id)

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
        user_id = update.effective_user.id

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


def main():

    print()
    print("=" * 60)
    print("🤖 NULL AI BOT")
    print("=" * 60)
    print("Starting...")
    print("=" * 60)
    print()

    app = (
        Application
        .builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

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

    print("✅ Bot is running...")
    print("Use /startnull to activate.")
    print()

    app.run_polling()


if __name__ == "__main__":
    main()
