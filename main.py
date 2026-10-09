import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InputMediaPhoto
from flask import Flask
from threading import Thread

# 1. Dummy Web Server (Render aur UptimeRobot ke liye 0.0.0.0 par)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Live and Awake!"

def run_web():
    # Port 0.0.0.0 hona zaroori hai taake Render timeout na kare
    app.run(host="0.0.0.0", port=10000)

# 2. Telegram Bot Setup
TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Memory: Users ka step track karne ke liye
user_steps = {}

@dp.message()
async def chat_funnel(message: types.Message):
    user_id = message.from_user.id
    step = user_steps.get(user_id, 0)
    
    # Typing action show karega taake real feel aaye
    await bot.send_chat_action(chat_id=user_id, action="typing")
    await asyncio.sleep(3) # 3 second ka wait

    if step == 0:
        await message.answer("Hey! Kaisi ho? Kahan gaib the itne din... 😉")
        user_steps[user_id] = 1
        
    elif step == 1:
        await message.answer("Waise mere pas ek surprise hai tumhare liye 🔥")
        # Yahan apni free photo ka URL dalen
        await message.answer_photo(photo="https://images.pexels.com/photos/1382731/pexels-photo-1382731.jpeg") 
        user_steps[user_id] = 2
        
    elif step == 2:
        await message.answer("Agar mazeed dekhna hai, toh isko unlock karo! 💋")
        # 600 Stars wali Paid Media
        await bot.send_paid_media(
            chat_id=user_id,
            star_count=600,
            media=[InputMediaPhoto(media="https://images.pexels.com/photos/1382734/pexels-photo-1382734.jpeg")]
        )
        user_steps[user_id] = 3
        
    else:
        # Aakhri step (Fallback)
        await message.answer("Main abhi thoda busy hoon, pehle wo photo unlock karo phir aaram se baat karte hain! ❤️")

async def main():
    # Web server ko background thread mein start karein
    Thread(target=run_web, daemon=True).start()
    
    # Bot ko start karein
    print("Bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())