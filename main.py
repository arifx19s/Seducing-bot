import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InputMediaPhoto, InputMediaVideo
from aiohttp import web
import os

# --- 1. Telegram Bot Setup ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is required. Please set it in your environment variables.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Memory Dictionary
user_steps = {}

# --- 2. NYRA PERSONA MEMORY ---
persona_details = {
    "name": "Nyra",
    "age": "24",
    "location": "Dubai, Marina ke pass",
    "background": "Mere dad American hain aur mom Russian. So, mix of both worlds 😉",
    "hobbies": "Mujhe traveling, makeup (mera apna brand bhi hai!), aur Marina mein late-night walks bohot pasand hain. Waise tum kya karte ho free time mein? ✨",
    "profession": "Main ek cosmetic business run karti hoon aur abhi Instagram par focus kar rahi hoon. Ek independent boss babe wali vibe, u know? 💁‍♀️",
    "relationship": "Well... maine 22 mein shaadi ki thi, but it didn't work out. I guess I'm too independent for some guys. Abhi I'm single and just focusing on myself. Tumhara kya scene hai? 😉",
}

# --- 3. KEYWORD DETECTION FUNCTION ---
def check_personal_question(text):
    text = text.lower()
    if any(word in text for word in ["meet", "milna", "milogi", "date", "see you", "video call", "call"]):
        return "I don't just meet guys from the internet right away, baby. I need to know you're real and worth my time first. 😉 Plus, I like keeping some things exclusive online for now. 🔥"
    if any(word in text for word in ["fuck", "sex", "nudes"]):
        return "Mmm you're bold today 🙈 I like that. But I need to know where you're from first, you keep ignoring me"
    if any(word in text for word in ["nam", "name", "naam", "who are you"]):
        return f"Mera naam {persona_details['name']} hai! Aur tumhara? ❤️"
    if any(word in text for word in ["age", "umar", "old"]):
        return f"Main {persona_details['age']} saal ki hoon. Tum kitne bade ho? 😉"
    if any(word in text for word in ["kaha", "location", "where", "city", "rehti"]):
        return f"Main {persona_details['location']} rehti hoon, it's beautiful here! Tum kahan se ho? ✨"
    if any(word in text for word in ["country", "american", "russian", "mom", "dad", "parents", "background"]):
        return persona_details['background']
    if any(word in text for word in ["hobby", "hobbies", "free time", "shouq"]):
        return persona_details['hobbies']
    if any(word in text for word in ["work", "job", "profession", "kya karti", "business", "service", "services", "menu"]):
        return f"Heyy Handsome 😘 {persona_details['profession']} As for services, I don't do like a list of stuff lol. What are you looking for? I can't do customs right now but I have something hot for you if you're ready 👀"
    if any(word in text for word in ["boyfriend", "single", "relationship", "mingle", "married", "husband", "shaadi", "divorce"]):
        return persona_details['relationship']
    return None

# --- 4. MAIN CHAT HANDLER ---
@dp.message()
@dp.business_message()
async def smart_seducing_funnel(message: types.Message):
    # ==== FIX: Bot profile par chup, sirf business account (direct personal number) par reply ====
    if message.chat.type == "private" and not getattr(message, 'business_connection_id', None):
        return
    # ============================================================================================

    user_id = message.from_user.id
    text = message.text if message.text else ""
    step = user_steps.get(user_id, 0)
    
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(4)
    
    custom_reply = check_personal_question(text)
    if custom_reply:
        await message.answer(custom_reply)
        return

    if step == 0:
        await message.answer("Hey there! How are you doing? 😉")
        user_steps[user_id] = 1
        
    elif step == 1:
        await message.answer("Good boy. I've got something waiting for you, don't keep me waiting too long 😈")
        await message.answer_photo(photo="https://images.pexels.com/photos/1382731/pexels-photo-1382731.jpeg") 
        user_steps[user_id] = 2
        
    elif step == 2:
        await message.answer("I get shy on calls. Here I can be naughty just for u. Like that 🔥")
        await bot.send_paid_media(
            chat_id=message.chat.id,
            star_count=600,
            media=[InputMediaPhoto(media="https://images.pexels.com/photos/1382734/pexels-photo-1382734.jpeg")]
        )
        user_steps[user_id] = 3
        
    else:
        await message.answer("Babe, I'm busy right now. Unlock my exclusive video first if you want more of me... 💋")

# --- 5. STABLE WEB SERVER ---
async def handle(request):
    return web.Response(text="Nyra Bot is Live and Awake!")

app = web.Application()
app.router.add_get('/', handle)

async def start_web_server():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

# --- APP STARTUP ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    # Start the web server task concurrently
    asyncio.create_task(start_web_server())
    # Start bot polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
