# main.py

import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web
import requests

# === НАСТРОЙКИ (ПОМЕНЯЕМ В RAILWAY!) ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "1234567890:ABCdefGhiJKLmnoPQR...")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "123456789")

# Green API
WA_ID = os.getenv("WA_ID", "1105385800")
WA_TOKEN = os.getenv("WA_TOKEN", "c404bd51a3134509924f9707787c6e7e48b80298e590408c93")
WA_URL = f"https://api.green-api.com/waInstance{WA_ID}"

MAX_ID = os.getenv("MAX_ID", "3100385801")
MAX_TOKEN = os.getenv("MAX_TOKEN", "7fba5820362f4714bf67b3a7ed49b0ff63a0a6b83bbe4eb8b4")
MAX_URL = f"https://api.green-api.com/maxInstance{MAX_ID}"

WA_TARGET = os.getenv("WA_TARGET", "79782404490@c.us")
MAX_TARGET = os.getenv("MAX_TARGET", "79782404490")

# === Инициализация ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === Список разрешённых пользователей (в памяти) ===
allowed_users = set()

# === Команда /start — запрос на доступ ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name

    if user_id in allowed_users:
        await message.answer("✅ Доступ разрешён! Пишите — сообщения будут синхронизированы.")
    else:
        # Отправляем админу уведомление с кнопкой
        markup = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="✅ Разрешить", callback_data=f"allow_{user_id}")]
        ])
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"🔔 Новый запрос на доступ:\nИмя: {user_name}\nID: {user_id}",
            reply_markup=markup
        )
        await message.answer("⏳ Ваш запрос отправлен администратору. Ожидайте подтверждения.")

# === Обработка нажатия кнопки "Разрешить" ===
@dp.callback_query(lambda c: c.data.startswith("allow_"))
async def allow_user(callback: types.CallbackQuery):
    user_id = callback.data.split("_")[1]
    user_name = "неизвестный пользователь"

    try:
        user_info = await bot.get_chat(user_id)
        user_name = user_info.first_name
    except:
        pass

    allowed_users.add(user_id)

    await callback.message.edit_text(f"✅ Доступ разрешён пользователю: {user_name} (ID: {user_id})")

    try:
        await bot.send_message(
            chat_id=user_id,
            text="✅ Администратор разрешил вам использовать бота. Теперь вы можете синхронизировать сообщения."
        )
    except:
        pass

# === Обработка обычных сообщений (только для разрешённых) ===
@dp.message()
async def handle_message(message: types.Message):
    user_id = str(message.from_user.id)
    user_name = message.from_user.first_name
    text = message.text or "[медиа/файл]"

    if user_id not in allowed_users:
        await message.answer("🔒 У вас нет доступа к этому боту. Напишите /start для запроса.")
        return

    full_text = f"[Telegram] {user_name}:\n{text}"

    # Отправляем в WhatsApp
    requests.post(f"{WA_URL}/sendMessage/{WA_TOKEN}", json={
        "chatId": WA_TARGET,
        "message": full_text
    })

    # Отправляем в Max
    requests.post(f"{MAX_URL}/sendMessage/{MAX_TOKEN}", json={
        "chatId": MAX_TARGET,
        "message": full_text
    })

# === Вебхук для WhatsApp ===
async def webhook_wa(request):
    data = await request.json()
    if data.get("typeWebhook") == "incomingMessageReceived":
        name = data["senderData"]["senderName"]
        phone = data["senderData"]["chatId"].split("@")[0]
        msg = data["messageData"]["textMessageData"]["textMessage"]
        text = f"[WhatsApp] {name} ({phone}):\n{msg}"
        await bot.send_message(ADMIN_CHAT_ID, text)
    return web.Response(status=200)

# === Вебхук для Max ===
async def webhook_max(request):
    data = await request.json()
    if data.get("typeWebhook") == "incomingMessageReceived":
        name = data["senderData"]["senderName"]
        phone = data["senderData"]["chatId"]
        msg = data["messageData"]["textMessageData"]["textMessage"]
        text = f"[Max] {name} ({phone}):\n{msg}"
        await bot.send_message(ADMIN_CHAT_ID, text)
    return web.Response(status=200)

# === Запуск ===
app = web.Application()
app.router.add_post("/webhook/whatsapp", webhook_wa)
app.router.add_post("/webhook/max", webhook_max)

async def main():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
