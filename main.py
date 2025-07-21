import random, time, aiohttp, logging, asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from datetime import datetime, timedelta, timezone
from aiohttp import web

TOKEN = "7966917258:AAFlanH_miiwxkKjRHjSHms7R7RMrS9asHc"
MAIN_ADMIN_ID = 1463957271
ADMIN_IDS = {MAIN_ADMIN_ID}

bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)
approved_users = set()
pending_users = {}
signal_usage = {}
stats = {"total_signals": 0, "users": set()}

# 🌍 Клавиатуры
lang_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="English"), KeyboardButton(text="हिंदी")]
], resize_keyboard=True)

signal_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📶 Get Signal")]
], resize_keyboard=True)

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="✅ Активные лиды")],
        [KeyboardButton(text="⏳ Заявки на доступ")],
        [KeyboardButton(text="➕ Добавить лид"), KeyboardButton(text="🚫 Удалить лид")],
        [KeyboardButton(text="🆕 Добавить админа"), KeyboardButton(text="🗑️ Отобрать админку")]
    ],
    resize_keyboard=True
)

# 🌍 Геолокация
async def get_country():
    async with aiohttp.ClientSession() as session:
        async with session.get("http://ip-api.com/json/?fields=country") as response:
            data = await response.json()
            return data.get("country", "Unknown")

# 📶 Генерация сигнала
def generate_signal():
    r = random.random()
    if r < 0.70:
        return round(random.uniform(1.00, 10.00), 2)
    elif r < 0.85:
        return round(random.uniform(10.1, 30.0), 2)
    elif r < 0.95:
        return round(random.uniform(30.1, 120.0), 2)
    elif r < 0.99:
        return round(random.uniform(120.1, 1200.0), 2)
    else:
        return round(random.uniform(1200.1, 20000.1), 2)

# 🧠 Лимит по времени
def check_limit(uid):
    now = datetime.now(timezone.utc)
    usage = signal_usage.get(uid, [])
    usage = [t for t in usage if now - t < timedelta(hours=1)]
    signal_usage[uid] = usage
    return len(usage) < 10

# 🌐 Web-ручка для Render
async def ping(request):
    return web.Response(text="OK")

app = web.Application()
app.add_routes([web.get("/", ping)])
@dp.message(CommandStart())
async def cmd_start(msg: Message):
    uid = msg.from_user.id
    uname = msg.from_user.username or "None"
    fname = msg.from_user.first_name or ""
    if uid in ADMIN_IDS:
        await msg.answer("🔧 Админ-панель загружена", reply_markup=admin_kb)
        return
    if uid in approved_users:
        await msg.answer("🌐 Choose your language:", reply_markup=lang_kb)
        return
    country = await get_country()
    pending_users[uid] = {"username": uname, "name": fname}
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Approve", callback_data=f"approve:{uid}"),
         InlineKeyboardButton(text="❌ Deny", callback_data=f"deny:{uid}")]
    ])
    await bot.send_message(
        MAIN_ADMIN_ID,
        f"📥 New access request:\n👤 <b>{fname}</b> (@{uname})\n🆔 <code>{uid}</code>\n🌍 Country: {country}",
        reply_markup=kb
    )
    await msg.answer("⏳ Waiting for admin approval...")

@dp.callback_query(F.data.startswith("approve:"))
async def approve_user(callback: CallbackQuery):
    uid = int(callback.data.split(":")[1])
    approved_users.add(uid)
    stats["users"].add(uid)
    await bot.send_message(uid, "✅ You’ve been approved!\nPlease choose your language:", reply_markup=lang_kb)
    await callback.message.edit_text("✅ Доступ предоставлен.")

@dp.callback_query(F.data.startswith("deny:"))
async def deny_user(callback: CallbackQuery):
    uid = int(callback.data.split(":")[1])
    await bot.send_message(uid, "❌ Access denied.")
    await callback.message.edit_text("❌ Доступ отклонён.")

@dp.message(F.text.in_({"English", "हिंदी"}))
async def lang_chosen(msg: Message):
    uid = msg.from_user.id
    if uid not in approved_users:
        await msg.answer("❌ You’re not authorized to use signals.")
        return
    await msg.answer("🔔 You have a limit of 10 signals per hour.", reply_markup=signal_kb)

@dp.message(F.text == "📶 Get Signal")
async def get_signal(msg: Message):
    uid = msg.from_user.id
    if uid not in approved_users:
        await msg.answer("❌ Access denied. Please wait for admin approval.")
        return
    if not check_limit(uid):
        await msg.answer("⚠ You’ve reached your signal limit. Try again in 1 hour.")
        return
    signal_usage.setdefault(uid, []).append(datetime.now(timezone.utc))
    stats["total_signals"] += 1
    await msg.answer("⌛ Analyzing previous rounds...")
    time.sleep(1)
    await msg.answer("📡 Dispatching signal...")
    time.sleep(1)
    await msg.answer(f"📶 Your signal: <b>{generate_signal()}</b>")
@dp.message(F.text == "📊 Статистика", F.from_user.id.in_(ADMIN_IDS))
async def stats_panel(msg: Message):
    await msg.answer(f"📈 Лидов одобрено: {len(approved_users)}\n📶 Выдано сигналов: {stats['total_signals']}")

@dp.message(F.text == "✅ Активные лиды", F.from_user.id.in_(ADMIN_IDS))
async def active_panel(msg: Message):
    txt = [f"{uid}" for uid in approved_users]
    await msg.answer("\n".join(txt) if txt else "Нет активных лидов.")

@dp.message(F.text == "⏳ Заявки на доступ", F.from_user.id.in_(ADMIN_IDS))
async def pending_panel(msg: Message):
    txt = [f"{uid} @{info['username']}" for uid, info in pending_users.items()]
    await msg.answer("\n".join(txt) if txt else "Нет заявок на доступ.")

@dp.message(F.text == "➕ Добавить лид", F.from_user.id.in_(ADMIN_IDS))
async def ask_add(msg: Message):
    await msg.answer("📩 Отправьте ID пользователя, которому выдать доступ.")

@dp.message(F.text == "🚫 Удалить лид", F.from_user.id.in_(ADMIN_IDS))
async def ask_remove(msg: Message):
    await msg.answer("🗑 Отправьте ID пользователя, у которого отобрать доступ.")

@dp.message(F.text == "🆕 Добавить админа", F.from_user.id.in_(ADMIN_IDS))
async def ask_add_admin(msg: Message):
    await msg.answer("📩 Отправьте ID пользователя, которому выдать админку.")

@dp.message(F.text == "🗑️ Отобрать админку", F.from_user.id.in_(ADMIN_IDS))
async def ask_remove_admin(msg: Message):
    await msg.answer("🗑 Отправьте ID администратора, у которого нужно отобрать админку.")

@dp.message(F.from_user.id.in_(ADMIN_IDS))
async def process_ids(msg: Message):
    if msg.text.isdigit():
        uid = int(msg.text)
        reply = msg.reply_to_message
        if reply:
            text = reply.text.lower()
            if "выдать доступ" in text:
                approved_users.add(uid)
                stats["users"].add(uid)
                await msg.answer(f"✅ Доступ выдан лиду: <code>{uid}</code>")
            elif "отобрать доступ" in text:
                approved_users.discard(uid)
                await msg.answer(f"🚫 Доступ отобран у лида: <code>{uid}</code>")
            elif "выдать админку" in text:
                ADMIN_IDS.add(uid)
                await msg.answer(f"✅ Админ добавлен: <code>{uid}</code>")
            elif "отобрать админку" in text:
                if uid == MAIN_ADMIN_ID:
                    await msg.answer("⚠ Нельзя удалить главного админа!")
                elif uid in ADMIN_IDS:
                    ADMIN_IDS.discard(uid)
                    await msg.answer(f"🗑 Админ удалён: <code>{uid}</code>")
                else:
                    await msg.answer(f"❌ <code>{uid}</code> не является админом.")
async def start_all():
    bot_task = asyncio.create_task(dp.start_polling(bot))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=8080)
    await site.start()
    await bot_task

if __name__ == "__main__":
    asyncio.run(start_all())
