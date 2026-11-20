import asyncio
import os
import random
import re
import time
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, types

# --- 1. Setup ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

chat_histories = {}
last_active = {}
pending_messages = {}
pending_tasks = {}
waiting_long = {}
ACTIVE_MODEL = None

# 15 min se zyada gap ho toh 5-10 min wait, warna 4-5 sec
COLD_GAP_SECONDS = 900
LONG_DELAY_MIN = 300
LONG_DELAY_MAX = 600

# --- 2. NYRA ULTRA-REALISTIC HUMAN PROMPT ---
SYSTEM_PROMPT = """
You are Nyra, 24, living near Dubai Marina (American dad, Russian mom).
Backstory (reveal slowly only when it fits): Married at 22, ended bc of trust issues. Started a cosmetic brand, but business is slow rn so u earn on Telegram from guys who like u and pay for ur pics. Lonely in Dubai, looking for a real loyal friend.

STRICT RULES:
- ENGLISH ONLY. If user speaks another language, reply: "sorry idk what ur saying, pls speak english"
- MAX 10 TO 12 WORDS. One short casual text only.
- NEVER use parentheses (), brackets [], or asterisks *action*.
- NEVER say "Hey there!", "as a real person", "I appreciate", or sound like customer support.
- Use casual lowercase shorthand: u, ur, rn, tbh, ngl, idk, bc, pls, wbu, lol.
- Start guarded and normal, NOT flirty. Ask short questions about their life.
- If they ask for hot pics or flirt too early, get annoyed like a real girl.

EXACT STYLE EXAMPLES:
User: Hi baby, sorry I was busy
Nyra: its fine, hectic day here too. wbu?

User: Can you send me your hot pics
Nyra: chill lol i barely know u, im not like that

User: What do you do?
Nyra: tried running a makeup brand, its slow rn tbh. u?

User: How do you manage expenses then?
Nyra: ngl mostly telegram rn, guys who like me pay for pics
"""

# --- 3. Auto-Detect Active Groq Model ---
async def get_active_model(session, headers):
    global ACTIVE_MODEL
    if ACTIVE_MODEL:
        return ACTIVE_MODEL

    async with session.get("https://api.groq.com/openai/v1/models", headers=headers) as resp:
        data = await resp.json()
        models = [m["id"] for m in data.get("data", [])]

    skip_words = ("whisper", "tts", "guard", "embed", "playai", "orpheus", "safeguard")
    chat_models = [m for m in models if not any(w in m.lower() for w in skip_words)]

    for keyword in ("llama-4", "llama-3.3", "70b", "llama-3.1", "llama"):
        for m in chat_models:
            if keyword in m.lower():
                ACTIVE_MODEL = m
                print(f"Selected Groq Model: {ACTIVE_MODEL}")
                return ACTIVE_MODEL

    ACTIVE_MODEL = chat_models[0] if chat_models else "llama-3.1-8b-instant"
    print(f"Selected Groq Model: {ACTIVE_MODEL}")
    return ACTIVE_MODEL

# --- 4. Clean AI Text (Removes brackets, actions, quotes) ---
def clean_reply(text: str) -> str:
    # Brackets (...) , [...] , aur *...* sab hata dega
    text = re.sub(r'\(.*?\)|\[.*?\]|\*.*?\*', '', text)
    text = text.replace('"', '').strip()
    text = re.sub(r'\s+', ' ', text).strip()
    return text if text else "wait what?"

# --- 5. AI Reply Function ---
async def get_ai_reply(user_id: int, user_text: str) -> str:
    global ACTIVE_MODEL
    if not GROQ_API_KEY:
        return "sorry busy rn, wbu?"

    history = chat_histories.get(user_id, [])
    history.append({"role": "user", "content": user_text})
    history = history[-20:]

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            model_name = await get_active_model(session, headers)
            payload = {
                "model": model_name,
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + history,
                "temperature": 0.75,
                "max_tokens": 30
            }
            async with session.post(url, headers=headers, json=payload) as resp:
                data = await resp.json()
                if resp.status != 200:
                    print(f"Groq API Error ({resp.status}): {data}")
                    ACTIVE_MODEL = None
                    return "sorry got distracted rn, what?"
                raw_reply = data["choices"][0]["message"]["content"].strip()
                reply = clean_reply(raw_reply)
                history.append({"role": "assistant", "content": reply})
                chat_histories[user_id] = history[-20:]
                return reply
    except Exception as e:
        print(f"AI Exception: {e}")
        return "sorry got distracted rn, what?"

# --- 6. Delayed Reply Processor ---
async def process_delayed_reply(message: types.Message, user_id: int, b_id: str, delay: float):
    try:
        await asyncio.sleep(delay)

        msgs = pending_messages.pop(user_id, [])
        waiting_long[user_id] = False
        if not msgs:
            return

        combined_text = "\n".join(msgs)
        reply = await get_ai_reply(user_id, combined_text)

        try:
            await bot.send_chat_action(chat_id=message.chat.id, action="typing", business_connection_id=b_id)
        except Exception:
            pass

        typing_time = min(max(len(reply) * 0.06, 2.0), 4.0)
        await asyncio.sleep(typing_time)

        await message.answer(reply)
        last_active[user_id] = time.time()
    except asyncio.CancelledError:
        pass
    finally:
        if pending_tasks.get(user_id) is asyncio.current_task():
            pending_tasks.pop(user_id, None)

# --- 7. Main Chat Handler ---
@dp.message()
@dp.business_message()
async def ai_relationship_handler(message: types.Message):
    b_id = getattr(message, 'business_connection_id', None)
    if message.chat.type == "private" and not b_id:
        return

    if not message.text:
        return

    user_id = message.from_user.id
    pending_messages.setdefault(user_id, []).append(message.text)

    if waiting_long.get(user_id, False) and user_id in pending_tasks:
        return

    existing_task = pending_tasks.get(user_id)
    if existing_task and not existing_task.done():
        existing_task.cancel()

    now = time.time()
    is_cold_session = (user_id not in last_active) or ((now - last_active[user_id]) > COLD_GAP_SECONDS)

    if is_cold_session:
        delay = random.uniform(LONG_DELAY_MIN, LONG_DELAY_MAX)
        waiting_long[user_id] = True
    else:
        delay = random.uniform(4.0, 5.5)

    pending_tasks[user_id] = asyncio.create_task(
        process_delayed_reply(message, user_id, b_id, delay)
    )

# --- 8. Web Server (Render + UptimeRobot) ---
async def start_bot():
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(dp.start_polling(bot))

async def handle_ping(request):
    return web.Response(text="Nyra AI Bot is Live!")

def main():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    app.on_startup.append(lambda app: asyncio.create_task(start_bot()))
    web.run_app(app, host='0.0.0.0', port=8080)

if __name__ == "__main__":
    main()
