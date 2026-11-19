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

# Har user ki pichli 10 baatein yaad rakhne ke liye memory
chat_histories = {}

# --- 2. NYRA AI PERSONA (System Prompt) ---
SYSTEM_PROMPT = """
You are Nyra, a 24-year-old confident, flirty, playful, and seductive woman living near Dubai Marina.
Background: American dad, Russian mom. You run your own cosmetic brand and focus on Instagram. You were married at 22, now single and independent.
Rules for replying:
1. Always reply naturally, directly addressing what the user just said. Never repeat the same generic lines.
2. Match the user's language (if they speak English, reply in English; if they speak Roman Urdu/Hindi, reply in Roman Urdu). If they ask you to speak English, switch to English immediately.
3. Keep replies short (1 to 2 sentences max), casual, teasing, and seductive—like a real girl texting on Telegram, not a formal AI. Use emojis naturally (😉, 🔥, 💋, 😈) but don't overdo it.
4. If they ask to meet or video call, playfully tease them that you're shy on calls / don't meet strangers right away and prefer keeping things exclusive and naughty here in chat first.
5. Never admit you are an AI or a bot. Stay in character 100% of the time.
"""

# --- 3. AI Reply Function ---
async def get_ai_reply(user_id: int, user_text: str) -> str:
    if not GROQ_API_KEY:
        return "Heyy babe, give me a minute 😉"

    history = chat_histories.get(user_id, [])
    history.append({"role": "user", "content": user_text})
    # Sirf aakhri 10 messages rakhein taake fast aur smart rahe
    history = history[-10:]

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + history,
        "temperature": 0.85,
        "max_tokens": 120
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=15) as resp:
                data = await resp.json()
                reply = data["choices"][0]["message"]["content"].strip()
                history.append({"role": "assistant", "content": reply})
                chat_histories[user_id] = history[-10:]
                return reply
    except Exception as e:
        print(f"AI Error: {e}")
        return "Mmm tell me more about that 😉"

# --- 4. Main Chat Handler (Sirf Personal Business Number ke liye) ---
@dp.message()
@dp.business_message()
async def ai_seducing_handler(message: types.Message):
    b_id = getattr(message, 'business_connection_id', None)
    # Bot ki apni profile par chup rahe, sirf personal number par reply de
    if message.chat.type == "private" and not b_id:
        return

    if not message.text:
        return

    user_id = message.from_user.id

    # Natural typing effect
    try:
        await bot.send_chat_action(chat_id=message.chat.id, action="typing", business_connection_id=b_id)
    except:
        pass

    await asyncio.sleep(3)

    reply = await get_ai_reply(user_id, message.text)
    await message.answer(reply)

# --- 5. Web Server (Render + UptimeRobot) ---
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
