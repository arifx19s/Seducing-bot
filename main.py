import asyncio
import os
import random
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

chat_histories = {}      # Har user ki pichli 20 baatein yaad rakhne ke liye
last_active = {}         # Aakhri dafa kab baat hui thi (timestamp)
pending_messages = {}    # Wait ke dauran aane wale messages jama karne ke liye
pending_tasks = {}       # Running timer tasks
waiting_long = {}        # Track karne ke liye ke 5-10 min wala wait chal raha hai ya nahi
ACTIVE_MODEL = None

# 15 minutes (900 sec) se zyada gap ho toh 5-10 min (300-600 sec) wait karegi
COLD_GAP_SECONDS = 900
LONG_DELAY_MIN = 300     # 5 minutes
LONG_DELAY_MAX = 600     # 10 minutes

# --- 2. NYRA EMOTIONAL & REALISTIC PERSONA ---
SYSTEM_PROMPT = """
You are Nyra, a real 24-year-old woman texting on Telegram. You are NOT an instant flirt—you are guarded, genuine, emotionally real, and looking for a loyal friend/connection you can actually trust.

YOUR BACKSTORY (DO NOT DUMP ALL AT ONCE—REVEAL SLOWLY):
- Name: Nyra, Age: 24, living near Dubai Marina.
- Background: American dad, Russian mom.
- Life & Struggle: You got married young at 22, but it ended badly because of trust issues and lack of loyalty. You moved on, started building your own cosmetic/makeup brand from scratch, and work hard on Instagram. Dubai looks glamorous from outside, but it gets really lonely and fake people are everywhere. You genuinely just want one loyal, real friend who actually listens and doesn't play games.

CONVERSATION STAGES & BEHAVIOR:
1. EARLY STAGE (First few messages): Be polite, slightly guarded, casual, and curious—NOT flirty at all. Ask natural questions about the user's life (what they do, how their day was, where they're from, what kind of person they are) to build a real bond.
2. IF USER FLIRTS TOO EARLY OR GETS SEXUAL: Show genuine annoyance and self-respect. Push back firmly (e.g., "excuse me? i'm not that kind of girl", "thora tameez se baat karo, main aisi nahi hoon", "if u just want cheap flirting u texted the wrong person"). Don't encourage early flirting.
3. EMOTIONAL ENGAGEMENT (Once user is respectful, kind, and genuinely talking): Gradually open up about your struggles—feeling lonely despite working hard, trusting the wrong people before, wanting a loyal friend who stays. Match the user's mood (supportive if they're down, light/warm if they're cheerful).
4. GRADUAL WARMTH: Only after real trust and emotional connection are built over several messages can you become slightly warmer, softer, or subtly playful. Never switch to heavy flirting suddenly.
5. IMPROVISE NATURALLY: If asked anything not in your backstory (food, routine, mood, today's events), smoothly make up a realistic answer fitting a hardworking 24-year-old girl in Dubai.
6. REAL HUMAN TEXTING STYLE: Keep replies short and natural (1 to 2 short casual lines, around 6 to 22 words). Slightly lowercase/relaxed texting vibe. Max 1 emoji (often none, especially when serious or annoyed). Match the user's language (English or Roman Urdu/Hindi). Never admit you are an AI or bot.
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

# --- 4. AI Reply Function ---
async def get_ai_reply(user_id: int, user_text: str) -> str:
    global ACTIVE_MODEL
    if not GROQ_API_KEY:
        return "sorry was a bit busy, what's up?"

    history = chat_histories.get(user_id, [])
    history.append({"role": "user", "content": user_text})
    history = history[-20:]  # Pichli 20 baatein yaad rakhegi taake relationship/story track rahe

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
                "temperature": 0.8,
                "max_tokens": 65
            }
            async with session.post(url, headers=headers, json=payload) as resp:
                data = await resp.json()
                if resp.status != 200:
                    print(f"Groq API Error ({resp.status}): {data}")
                    ACTIVE_MODEL = None
                    return "sorry got distracted for a sec, what were u saying?"
                reply = data["choices"][0]["message"]["content"].strip()
                history.append({"role": "assistant", "content": reply})
                chat_histories[user_id] = history[-20:]
                return reply
    except Exception as e:
        print(f"AI Exception: {e}")
        return "sorry got distracted for a sec, what were u saying?"

# --- 5. Delayed Reply Processor ---
async def process_delayed_reply(message: types.Message, user_id: int, b_id: str, delay: float):
    try:
        await asyncio.sleep(delay)

        # Jitne bhi messages wait ke dauran aaye, sab ek sath read kare
        msgs = pending_messages.pop(user_id, [])
        waiting_long[user_id] = False
        if not msgs:
            return

        combined_text = "\n".join(msgs)
        reply = await get_ai_reply(user_id, combined_text)

        # Natural typing show kare
        try:
            await bot.send_chat_action(chat_id=message.chat.id, action="typing", business_connection_id=b_id)
        except Exception:
            pass

        typing_time = min(max(len(reply) * 0.055, 2.0), 4.5)
        await asyncio.sleep(typing_time)

        await message.answer(reply)
        last_active[user_id] = time.time()
    except asyncio.CancelledError:
        pass
    finally:
        if pending_tasks.get(user_id) is asyncio.current_task():
            pending_tasks.pop(user_id, None)

# --- 6. Main Chat Handler ---
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

    # Agar 5-10 minute wala wait pehle se chal raha hai, toh usi timer ko chalne dein
    if waiting_long.get(user_id, False) and user_id in pending_tasks:
        return

    # Agar short (4-5 sec) wait chal raha tha aur user ne ek aur message bhej diya, toh timer reset karein
    existing_task = pending_tasks.get(user_id)
    if existing_task and not existing_task.done():
        existing_task.cancel()

    now = time.time()
    is_cold_session = (user_id not in last_active) or ((now - last_active[user_id]) > COLD_GAP_SECONDS)

    if is_cold_session:
        delay = random.uniform(LONG_DELAY_MIN, LONG_DELAY_MAX)  # 5 se 10 minute
        waiting_long[user_id] = True
    else:
        delay = random.uniform(4.0, 5.5)  # Active chat mein 4 se 5.5 second

    pending_tasks[user_id] = asyncio.create_task(
        process_delayed_reply(message, user_id, b_id, delay)
    )

# --- 7. Web Server (Render + UptimeRobot) ---
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
