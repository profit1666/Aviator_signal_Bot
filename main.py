import os, random, time, aiohttp, logging
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Update
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiohttp import web
from datetime import datetime, timedelta, timezone

TOKEN = os.getenv("BOT_TOKEN")
MAIN_ADMIN_ID = 1463957271

bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

approved_users = set()
pending_users = {}
signal_usage = {}

user_lang_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="English"), KeyboardButton(text="हिंदी")]
], resize_keyboard=True)

signal_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📶 Get Signal")]
], resize_keyboard=True)

def approval_buttons(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve:{uid}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"deny:{uid}")
        ]
    ])

def check_limit(uid):
    now = datetime.now(timezone.utc)
    usage = signal_usage.get(uid, [])
    usage = [t for t in usage if now - t < timedelta(hours=1)]
    signal_usage[uid] = usage
    return len(usage) < 10

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

@dp.message(CommandStart())
async def start_handler(msg: Message):
    uid = msg.from_user.id
    uname = msg.from_user.username or "—"
    fname = msg.from_user.first_name or "—"

    if uid == MAIN_ADMIN_ID:
        await msg.answer("🔧 Админ-панель загружена.", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📥 Заявки на доступ")]],
            resize_keyboard=True
        ))
        return

    if uid in approved_users:
        await msg.answer("🌐 Choose your language:", reply_markup=user_lang_kb)
        return

    pending_users[uid] = {"username": uname, "name": fname}
    await msg.answer("⏳ Waiting for admin approval...")

    await bot.send_message(
        MAIN_ADMIN_ID,
        f"📥 Заявка на доступ:\n👤 <b>{fname}</b> (@{uname})\n🆔 <code>{uid}</code>",
        reply_markup=approval_buttons(uid)
    )

@dp.callback_query(F.data.startswith("approve:"))
async def approve_handler(callback: CallbackQuery):
    uid = int(callback.data.split(":")[1])
    approved_users.add(uid)
    await bot.send_message(uid, "✅ You’ve been approved!\nChoose your language:", reply_markup=user_lang_kb)
    await callback.message.edit_text("✅ Доступ одобрен.")

@dp.callback_query(F.data.startswith("deny:"))
async def deny_handler(callback: CallbackQuery):
    uid = int(callback.data.split(":")[1])
    await bot.send_message(uid, "❌ Access denied.")
    await callback.message.edit_text("❌ Доступ отклонён.")

@dp.message(F.text.in_({"English", "हिंदी"}))
async def language_handler(msg: Message):
    if msg.from_user.id not in approved_users:
        await msg.answer("❌ You’re not authorized to use this bot.")
        return
    await msg.answer("🔔 You can receive up to 10 signals per hour.", reply_markup=signal_kb)

@dp.message(F.text == "📶 Get Signal")
async def signal_handler(msg: Message):
    uid = msg.from_user.id
    if uid not in approved_users:
        await msg.answer("❌ You’re not authorized yet.")
        return
    if not check_limit(uid):
        await msg.answer("⚠ Signal limit reached. Try again in 1 hour.")
        return
    signal_usage.setdefault(uid, []).append(datetime.now(timezone.utc))
    await msg.answer("📡 Signal incoming...")
    time.sleep(1)
    await msg.answer(f"📶 Your signal: <b>{generate_signal()}</b>")

@dp.message(F.text == "📥 Заявки на доступ", F.from_user.id == MAIN_ADMIN_ID)
async def view_requests(msg: Message):
    if not pending_users:
        await msg.answer("📭 Нет заявок на доступ.")
        return
    txt = [
        f"🆔 <code>{uid}</code> — @{info['username']} ({info['name']})"
        for uid, info in pending_users.items()
    ]
    await msg.answer("\n".join(txt))

async def ping(request):
    return web.Response(text="OK")

async def telegram_webhook(request):
    data = await request.json()
    update = Update.model_validate(data)  # ✅ исправлено: больше не to_object
    await dp.feed_update(bot, update)
    return web.Response()

async def on_startup(app):
    webhook_url = "https://aviator-signal-bot-5eqk.onrender.com"
    await bot.delete_webhook()
    await bot.set_webhook(webhook_url)

app = web.Application()
app.router.add_get("/", ping)
app.router.add_post("/", telegram_webhook)
app.on_startup.append(on_startup)

if __name__ == "__main__":
    web.run_app(app, port=8080)
