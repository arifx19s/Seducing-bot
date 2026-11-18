# --- 4. MAIN CHAT HANDLER ---
@dp.message()
@dp.business_message()
async def smart_seducing_funnel(message: types.Message):
    # ==== 1 LINE FIX ====
    # Agar chat ki type "private" hai (yani kisi ne direct bot ki profile par msg kiya hai), to ignore (return) kar do.
    # Bot sirf tab chalega jab business connection (apke naye number) ke zariye message aye.
    if message.chat.type == "private" and not getattr(message, 'business_connection_id', None):
        return
    # ====================

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
