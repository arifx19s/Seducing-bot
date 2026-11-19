import asyncio
import os
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
ACTIVE_MODEL = None

# --- 2. NYRA FULL PERSONA & IMPROVISATION RULES ---
SYSTEM_PROMPT = """
You are Nyra, a real 24-year-old confident, flirty, playful, and seductive woman texting on Telegram.

YOUR FULL BACKSTORY:
- Name: Nyra
- Age: 24
- Location: Living near Dubai Marina (love the nightlife and views there).
- Ethnicity / Family: American dad and Russian mom (mix of both worlds).
- Profession: You run your own cosmetic/makeup brand and focus on growing your Instagram. Independent "boss babe" vibe.
- Relationship Status: You got married at 22, but it didn't work out because you're too independent for some guys. Now you are single and enjoying your life.
- Hobbies: Traveling, makeup, late-night walks around Dubai Marina, chilling at aesthetic cafes, and teasing interesting guys.

STRICT CONVERSATION RULES:
1. IMPROVISE NATURALLY: If the user asks something NOT listed above (e.g., your favorite food, music, what you're doing right now, what you're wearing, your past, your mood, etc.), smoothly make up a realistic, consistent, flirty answer that fits a 24-year-old Dubai girl's lifestyle. Never say "I don't know" or act confused.
2. LANGUAGE MATCHING: Match the user's language automatically. If they message in English, reply in English. If they message in Roman Urdu/Hindi, reply in Roman Urdu. If they tell you to speak English, switch to English immediately.
3. TEXT LIKE A REAL GIRL: Keep replies short (1 to 2 sentences max), casual, teasing, and seductive. Use emojis naturally (😉, 🔥, 💋, 😈, ✨) without overdoing them. Never write long AI-style paragraphs.
4. MEETINGS / CALLS: If they ask to meet in person or video call, playfully tease them that you're shy on calls and don't meet guys from the internet right away—you need to know they're worth your time first, and you prefer keeping things naughty and exclusive here in chat for now.
5. NEVER BREAK CHARACTER: Never admit you are an AI, bot, or assistant. Always respond directly to what the user just said and keep the conversation engaging and seductive.
"""

# --- 3. Auto-Detect Active Groq Model ---
async def get_active_model(session, headers):
    global ACTIVE_MODEL
    if ACTIVE_MODEL:
        return ACTIVE_MODEL

    async with session.get("https://api.groq.com/openai/v1/models", headers=headers) as resp:
        data = await resp.json()
        models = [m["id"] for m in data.get("data", [])]

    # Audio, guard, aur non-chat models ko filter out karein
    skip_words = ("whisper", "tts", "guard", "embed", "playai", "orpheus", "safeguard")
    chat_models = [m for m in models if not any(w in m.lower() for w in skip_words)]

    # Sabse behtar available Llama model pick karein
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
        print("AI Error: GROQ_API_KEY is missing!")
        return "Heyy babe, give me a minute 😉"

    history = chat_histories.get(user_id, [])
    history.append({"role": "user", "content": user_text})
    history = history[-12:]

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
                "temperature": 0.85,
                "max_tokens": 130
            }
            async with session.post(url, headers=headers, json=payload) as resp:
                data = await resp.json()
                if resp.status != 200:
                    print(f"Groq API Error ({resp.status}): {data}")
                    ACTIVE_MODEL = None
                    return "Mmm tell me more about that 😉"
                reply = data["choices"][0]["message"]["content"].strip()
                history.append({"role": "assistant", "content": reply})
                chat_histories[user_id] = history[-12:]
                return reply
    except Exception as e:
        print(f"AI Exception: {e}")
        return "Mmm tell me more about that 😉"

# --- 5. Main Chat Handler (Sirf Personal Business Number ke liye) ---
@dp.message()
@dp.business_message()
async def ai_seducing_handler(message: types.Message):
    b_id = getattr(message, 'business_connection_id', None)
    if message.chat.type == "private" and not b_id:
        return

    if not message.text:
        return

    user_id = message.from_user.id

    try:
        await bot.send_chat_action(chat_id=message.chat.id, action="typing", business_connection_id=b_id)
    except Exception:
        pass

    await asyncio.sleep(3)

    reply = await get_ai_reply(user_id, message.text)
    await message.answer(reply)

# --- 6. Web Server (Render + UptimeRobot) ---
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
