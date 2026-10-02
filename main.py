import logging
import base64
import io
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


groq_client = Groq(
    api_key=GROQ_API_KEY
)

logging.basicConfig(
    level=logging.INFO
)

bot_active = False
conversation_history = {}



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


async def start_null(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    global bot_active

    bot_active = True

    log_event(
        "🚀 BOT STARTED",
        update.effective_user
    )

    await update.message.reply_text(
        "🚀 NULL AI is now ACTIVE!\n\n"
        "💬 Send a message to chat\n"
        "🎨 /image <prompt>\n"
        "🔐 /vip1 - /vip5"
    )


async def end_null(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    global bot_active

    bot_active = False


    log_event(
        "🛑 BOT STOPPED",
        update.effective_user
    )

    await update.message.reply_text(
        "🛑 NULL AI is now INACTIVE."
    )


async def send_vip(
    update: Update,
    message: str
):
    if not bot_active:
        return

    await update.message.reply_text(
        message
    )


async def vip1(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await send_vip(
        update,
        VIP1_MESSAGE
    )


async def vip2(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await send_vip(
        update,
        VIP2_MESSAGE
    )


async def vip3(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await send_vip(
        update,
        VIP3_MESSAGE
    )


async def vip4(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await send_vip(
        update,
        VIP4_MESSAGE
    )


async def vip5(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await send_vip(
        update,
        VIP5_MESSAGE
    )


async def image(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not bot_active:
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
        safe_prompt = (
            prompt
            + ", safe and appropriate, "
            + "non-explicit, fully clothed subjects"
        )

        encoded_prompt = urllib.parse.quote(
            safe_prompt,
            safe=""
        )

        url = (
            "https://gen.pollinations.ai/image/"
            + encoded_prompt
        )

        headers = {
            "Authorization":
            f"Bearer {POLLINATIONS_API_KEY}"
        }

        params = {
            "model": IMAGE_MODEL
        }

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=180
        )

        if response.status_code != 200:
            raise Exception(
                f"HTTP {response.status_code}: "
                f"{response.text[:1000]}"
            )

        content_type = response.headers.get(
            "content-type",
            ""
        ).lower()

        if not content_type.startswith("image/"):
            raise Exception(
                "API did not return an image."
            )

        image_file = io.BytesIO(
            response.content
        )

        image_file.name = "NULL_AI_image.jpg"

        await update.message.reply_photo(
            photo=image_file,
            caption=f"🎨 {prompt}"
        )

        user_id = update.effective_user.id
        if user_id not in conversation_history:
            conversation_history[user_id] = []

        conversation_history[user_id].append({
            "role": "user",
            "content": f"[User requested an image: {prompt}]"
        })
        conversation_history[user_id].append({
            "role": "assistant",
            "content": f"[Generated an image of: {prompt}]"
        })

        print("✅ Image sent successfully")

    except Exception as error:
        print(
            "❌ Image error:",
            error
        )

        await update.message.reply_text(
            "❌ Image generation failed.\n\n"
            f"Reason: {error}"
        )


async def chat(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not bot_active:
        return

    user_msg = update.message.text

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

        if user_id not in conversation_history:
            conversation_history[user_id] = []

        conversation_history[user_id].append({
            "role": "user",
            "content": user_msg
        })

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ] + conversation_history[user_id]

        response = groq_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages
        )

        reply = response.choices[0].message.content

        conversation_history[user_id].append({
            "role": "assistant",
            "content": reply
        })

        await update.message.reply_text(
            reply
        )

        print("✅ AI response sent")

    except Exception as error:
        print(
            "❌ Chat error:",
            error
        )

        await update.message.reply_text(
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

    app.add_handler(
        CommandHandler(
            "STARTnull",
            start_null
        )
    )

    app.add_handler(
        CommandHandler(
            "ENDnull",
            end_null
        )
    )

    app.add_handler(
        CommandHandler(
            "vip1",
            vip1
        )
    )

    app.add_handler(
        CommandHandler(
            "vip2",
            vip2
        )
    )

    app.add_handler(
        CommandHandler(
            "vip3",
            vip3
        )
    )

    app.add_handler(
        CommandHandler(
            "vip4",
            vip4
        )
    )

    app.add_handler(
        CommandHandler(
            "vip5",
            vip5
        )
    )

    app.add_handler(
        CommandHandler(
            "image",
            image
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            chat
        )
    )

    print("✅ Bot is running...")
    print("Use /STARTnull to activate.")
    print()

    app.run_polling()


if __name__ == "__main__":
    main()
