import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InputMediaPhoto, InputMediaVideo

# Bot Initialization (Token is expected from Render environment variables)
import os
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is required. Please set it in your environment variables.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Memory Dictionary (To track each user's chat funnel step)
user_steps = {}

# --- NYRA PERSONA MEMORY (Bot ki identity) ---
persona_details = {
    "name": "Nyra",
    "age": "24",
    "location": "Dubai, Marina ke pass",
    "background": "Mere dad American hain aur mom Russian. So, mix of both worlds 😉",
    "hobbies": "Mujhe traveling, makeup (mera apna brand bhi hai!), aur Marina mein late-night walks bohot pasand hain. Waise tum kya karte ho free time mein? ✨",
    "profession": "Main ek cosmetic business run karti hoon aur abhi Instagram par focus kar rahi hoon. Ek independent boss babe wali vibe, u know? 💁‍♀️",
    "relationship": "Well... maine 22 mein shaadi ki thi, but it didn't work out. I guess I'm too independent for some guys. Abhi I'm single and just focusing on myself. Tumhara kya scene hai? 😉",
}

# --- KEYWORD DETECTION FUNCTION (For Personal Questions) ---
def check_personal_question(text):
    text = text.lower()
    
    # Meetup / Date / Video Call Demands
    if any(word in text for word in ["meet", "milna", "milogi", "date", "see you", "video call", "call"]):
        return "I don't just meet guys from the internet right away, baby. I need to know you're real and worth my time first. 😉 Plus, I like keeping some things exclusive online for now. 🔥"

    # Bold/Explicit talk handlers
    if any(word in text for word in ["fuck", "sex", "nudes"]):
        return "Mmm you're bold today 🙈 I like that. But I need to know where you're from first, you keep ignoring me"
        
    # Name
    if any(word in text for word in ["nam", "name", "naam", "who are you"]):
        return f"Mera naam {persona_details['name']} hai! Aur tumhara? ❤️"
        
    # Age
    if any(word in text for word in ["age", "umar", "old"]):
        return f"Main {persona_details['age']} saal ki hoon. Tum kitne bade ho? 😉"
        
    # Location
    if any(word in text for word in ["kaha", "location", "where", "city", "rehti"]):
        return f"Main {persona_details['location']} rehti hoon, it's beautiful here! Tum kahan se ho? ✨"
        
    # Background / Parents / Nationality
    if any(word in text for word in ["country", "american", "russian", "mom", "dad", "parents", "background"]):
        return persona_details['background']
        
    # Hobbies
    if any(word in text for word in ["hobby", "hobbies", "free time", "shouq"]):
        return persona_details['hobbies']
        
    # Profession / Job / Services
    if any(word in text for word in ["work", "job", "profession", "kya karti", "business", "service", "services", "menu"]):
        return f"Heyy Handsome 😘 {persona_details['profession']} As for services, I don't do like a list of stuff lol. What are you looking for? I can't do customs right now but I have something hot for you if you're ready 👀"
        
    # Relationship / Marital Status
    if any(word in text for word in ["boyfriend", "single", "relationship", "mingle", "married", "husband", "shaadi", "divorce"]):
        return persona_details['relationship']
        
    return None

# --- MAIN CHAT HANDLER (For Business Mode and Private Messages) ---
@dp.message()
@dp.business_message()
async def smart_seducing_funnel(message: types.Message):
    user_id = message.from_user.id
    text = message.text if message.text else ""
    step = user_steps.get(user_id, 0)
    
    # 1. Natural Human Delay
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(4) # 4 second delay
    
    # 2. Check for Specific Keyword Questions First
    custom_reply = check_personal_question(text)
    if custom_reply:
        await message.answer(custom_reply)
        return  # Yahan ruk jayega taake funnel ki agli line na bhej de

    # 3. The Main Sales Funnel (Agar koi general baat ya "hi/hello" ho)
    if step == 0:
        await message.answer("Hey there! How are you doing? 😉")
        user_steps[user_id] = 1
        
    elif step == 1:
        await message.answer("Good boy. I've got something waiting for you, don't keep me waiting too long 😈")
        # Yahan apni FREE TEASER VIDEO ya PHOTO ka direct link lagayen (e.g. from Postimages)
        await message.answer_photo(photo="https://images.pexels.com/photos/1382731/pexels-photo-1382731.jpeg") 
        user_steps[user_id] = 2
        
    elif step == 2:
        await message.answer("I get shy on calls. Here I can be naughty just for u. Like that 🔥")
        # 600 Stars wali Locked Oiled/Exclusive Video (Replace the media link)
        await bot.send_paid_media(
            chat_id=message.chat.id,
            star_count=600,
            media=[InputMediaPhoto(media="https://images.pexels.com/photos/1382734/pexels-photo-1382734.jpeg")]
        )
        user_steps[user_id] = 3
        
    else:
        # Aakhri fallback step / Upsell
        await message.answer("If you want more, I have a special bundle ready for you... unlock my exclusive content first! 💋")

# --- APP STARTUP (Dummy server for Uptime Robot) ---
async def main():
    # Polling start karna
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
