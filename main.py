import random, time, aiohttp, logging
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from datetime import datetime, timedelta

TOKEN = "7966917258:AAHB3D1Z8-PwXGiSW6gQe-bPIlnlAjNZdsI"
MAIN_ADMIN_ID = 1463957271
ADMIN_IDS = {MAIN_ADMIN_ID}

bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)
approved_users = set()
pending_users = {}
signal_usage = {}
stats = {"total_signals": 0, "users": set()}

# 🎛 Клавиатуры (админ — русский, лиды — English/Hindi)
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

async def get_country():
    async with aiohttp.ClientSession() as session:
        async with session.get("http://ip-api.com/json/?fields=country") as response:
            data = await response.json()
            return data.get("country", "Unknown")

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

def check_limit(uid):
    now = datetime.utcnow()
    usage = signal_usage.get(uid, [])
    usage = [t for t in usage if now - t < timedelta(hours=1)]
    signal_usage[uid] = usage
    return len(usage) < 10
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
    await callback.message.edit_text("✅ Access granted.")

@dp.callback_query(F.data.startswith("deny:"))
async def deny_user(callback: CallbackQuery):
    uid = int(callback.data.split(":")[1])
    await bot.send_message(uid, "❌ Access denied.")
    await callback.message.edit_text("❌ Access denied.")

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
    signal_usage.setdefault(uid, []).append(datetime.utcnow())
    stats["total_signals"] += 1
    await msg.answer("⌛ Analyzing previous rounds...")
    time.sleep(1)
    await msg.answer("📡 Dispatching signal...")
    time.sleep(1)
    await msg.answer(f"📶 Your signal: <b>{generate_signal()}</b>")
@dp.message(F.text == "📊 Статистика", F.from_user.id.in_(ADMIN_IDS))
async def stats_panel(msg: Message):
    await msg.answer(f"📈 Approved leads: {len(approved_users)}\n📶 Total signals sent: {stats['total_signals']}")

@dp.message(F.text == "✅ Активные лиды", F.from_user.id.in_(ADMIN_IDS))
async def active_panel(msg: Message):
    txt = [f"{uid}" for uid in approved_users]
    await msg.answer("\n".join(txt) if txt else "No active leads found.")

@dp.message(F.text == "⏳ Заявки на доступ", F.from_user.id.in_(ADMIN_IDS))
async def pending_panel(msg: Message):
    txt = [f"{uid} @{info['username']}" for uid, info in pending_users.items()]
    await msg.answer("\n".join(txt) if txt else "No pending access requests.")

@dp.message(F.text == "➕ Добавить лид", F.from_user.id.in_(ADMIN_IDS))
async def ask_add(msg: Message):
    await msg.answer("📩 Send the user ID to grant access to lead:")

@dp.message(F.text == "🚫 Удалить лид", F.from_user.id.in_(ADMIN_IDS))
async def ask_remove(msg: Message):
    await msg.answer("🗑 Send the user ID to revoke access from lead:")

@dp.message(F.text == "🆕 Добавить админа", F.from_user.id.in_(ADMIN_IDS))
async def ask_add_admin(msg: Message):
    await msg.answer("📩 Send the user ID to grant admin privileges:")

@dp.message(F.text == "🗑️ Отобрать админку", F.from_user.id.in_(ADMIN_IDS))
async def ask_remove_admin(msg: Message):
    await msg.answer("🗑 Send the admin ID to revoke admin rights:")

@dp.message(F.from_user.id.in_(ADMIN_IDS))
async def process_ids(msg: Message):
    if msg.text.isdigit():
        uid = int(msg.text)
        reply = msg.reply_to_message
        if reply:
            text = reply.text.lower()
            if "grant access to lead" in text:
                approved_users.add(uid)
                stats["users"].add(uid)
                await msg.answer(f"✅ Access granted to lead: <code>{uid}</code>")
            elif "revoke access from lead" in text:
                approved_users.discard(uid)
                await msg.answer(f"🚫 Access revoked from lead: <code>{uid}</code>")
            elif "grant admin privileges" in text:
                ADMIN_IDS.add(uid)
                await msg.answer(f"✅ Admin privileges granted: <code>{uid}</code>")
            elif "revoke admin rights" in text:
                if uid == MAIN_ADMIN_ID:
                    await msg.answer("⚠ Cannot remove main admin!")
                elif uid in ADMIN_IDS:
                    ADMIN_IDS.discard(uid)
                    await msg.answer(f"🗑 Admin rights revoked: <code>{uid}</code>")
                else:
                    await msg.answer(f"❌ <code>{uid}</code> is not currently an admin.")

# 🚀 Run bot
if __name__ == "__main__":
    dp.run_polling(bot)
