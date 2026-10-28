import asyncio
import time
import os
import json
import random
from typing import Optional, Union
import aiohttp
import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup,
    InlineKeyboardButton, LabeledPrice, PreCheckoutQuery, FSInputFile
)
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "9180721087:AAGgUGZx13d8UQyTUkjSqVVDUHNaZ-t3S1Q"
PAYMENT_TOKEN = "ТОКЕН_ЮKASSA_ОТ_BOTFATHER"      # Токен ЮKassa (из @BotFather -> Payments)
CRYPTO_PAY_TOKEN = "661096:AAdCCcfYSM28jCK7hLG8omgtkIjdsHxJmgB"          # API-токен из @CryptoBot -> Crypto Pay -> Create App
CLUB_CHAT_ID = -1004324447753                    # ID твоей закрытой группы AURA (начинается с -100)

TRIAL_DURATION = 3600           # 1 час в секундах
GRACE_PERIOD = 3 * 86400        # 3 дня (72 часа) отсрочки перед киком

# Цены в рублях и эквивалент в Telegram Stars (примерно 1 Star = 2 рубля)
TARIFFS = {
    "1m": {"title": "1 месяц", "price": 799, "stars": 400, "days": 30},
    "3m": {"title": "3 месяца", "price": 1799, "stars": 900, "days": 90},
    "6m": {"title": "6 месяцев", "price": 2999, "stars": 1600, "days": 180},
    "12m": {"title": "12 месяцев (ВЫГОДНЫЙ)", "price": 4999, "stars": 2500, "days": 365},
}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
DB_NAME = "aura_club.db"
MAIN_IMAGE = "club_main.jpg"
CRYPTO_API_URL = "https://pay.crypt.bot/api"

# ================= ЖЕСТКИЕ ДОЖИМЫ В СТИЛЕ КЛУБА =================
REMINDER_MESSAGES = [
    "Тебя бросила малая? Сиди дальше страдай в подушку, пока другие забирают своё. Вступай в Орден, разберём ситуацию по фактам.",
    "Хочешь пойти к психологу? Брось ты эту херню. Лучший психолог — это наш орден. Здесь тебе быстро мозги на место поставят.",
    "Ты думаешь мы секта? Мы семья. А семья и есть секта. Добро пожаловать домой.",
    "Че ты заднюю даешь? Даже бесплатный пробный час забрать испугался. Хватит быть наблюдателем в собственной жизни.",
    "799 рублей — это стоимость одного похода в фастфуд. Но ты до сих пор думаешь, стоит ли вложиться в свои мозги и окружение.",
    "Сколько еще будешь терпеть манипуляции и выносить себе мозг? В клубе уже лежат разборы десятков таких историй.",
    "Сильная позиция — признать, что ты пробуксовываешь и тебе нужна база. Слабая — делать вид, что ты справляешься сам.",
    "Опять закрыл бота и пошел листать ленту тиктока? Дешевый дофамин не вытащит тебя из ямы.",
    "В клубе нет воды, сказок про успех и розовых соплей. Только жесткая практика, дисциплина и мужской рассудок.",
    "Твои проблемы сами себя не решат. Либо ты берешь контроль, либо продолжаешь плыть по течению. Выбор за тобой.",
    "Ты заглянул в AURA и слился. Пока ты откладываешь решения на завтра, ничего в твоей жизни не поменяется.",
    "Ты слабак, если боишься даже посмотреть правде в глаза. Тебе нужно вступить к нам и навести порядок в голове.",
    "Пока ты сомневаешься, другие пацаны уже разбирают свои кейсы, ставят цели и двигаются дальше.",
    "Бесплатный тест на 1 час открыт специально для тех, кто не верит на слово. Зайди и проверь сам.",
    "Хватит вариться в своих мыслях в одиночку. В закрытом клубе можно разобрать любую ситуацию без розовых очков.",
    "Ты можешь дальше оправдывать чужие манипуляции, а можешь зайти в AURA и научиться считывать их за минуту.",
    "Каждый раз, когда ты откладываешь действие, ты выбираешь остаться на том же месте. Выбирай тариф.",
    "Мужской стержень строится на решениях, а не на раздумьях. Прими решение.",
    "Думаешь, проблема рассосется сама? Не рассосется. Заходи в клуб, разберем твою ситуацию по полочкам.",
    "Окружение либо тянет тебя на дно, либо заставляет расти. В AURA собрались те, кто выбрал второе.",
    "Слиться проще всего — для этого вообще ничего делать не надо. Попробуй сделать наоборот.",
    "Твой пробный доступ все еще ждет. Один час внутри клуба даст тебе больше понимания, чем месяц чтения пабликов.",
    "Не жди, пока прижмет окончательно. Заходи сейчас, изучай базу и ставь фильтр на деструктивных людей.",
    "Время идет в любом случае. Вопрос только в том, проведешь ты этот месяц с пользой или как обычно.",
    "Последнее предупреждение: хватит смотреть со стороны. Жми кнопку и заходи в AURA."
]

# ================= ТЕКСТЫ ИНТЕРФЕЙСА =================
MAIN_TEXT = "\n".join([
    "🏴 <b>AURA | Закрытый мужской клуб «Талион»</b>",
    "",
    "• Разборы реальных ситуаций и переписок без иллюзий",
    "• Психология отношений и фильтр красных флагов",
    "• Дисциплина, деньги и мужское братство",
    "",
    "Выбирай свой формат входа:"
])

ABOUT_TEXT = "\n".join([
    "🏴 <b>ЧТО ВНУТРИ КЛУБА «AURA»?</b>",
    "",
    "Закрытая территория здравого смысла для мужчин:",
    "",
    "• <b>Разбор ситуаций (SOS):</b> анонимный разбор твоих историй и переписок.",
    "• <b>Знакомства и Переписки:</b> как общаться с позиции силы.",
    "• <b>Психология и Манипуляции:</b> снимаем розовые очки.",
    "• <b>Дисциплина и Деньги:</b> режим, спорт, карьера и связи.",
    "",
    "Никакого нытья — только конкретика и решения."
])

# ================= БАЗА ДАННЫХ =================
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            "user_id INTEGER PRIMARY KEY, "
            "trial_used INTEGER DEFAULT 0, "
            "sub_end INTEGER DEFAULT 0, "
            "grace_notified INTEGER DEFAULT 0, "
            "in_club INTEGER DEFAULT 0, "
            "started_at INTEGER DEFAULT 0, "
            "last_activity INTEGER DEFAULT 0, "
            "reminder_stage INTEGER DEFAULT 0, "
            "reminders_enabled INTEGER DEFAULT 1)"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS crypto_invoices ("
            "invoice_id INTEGER PRIMARY KEY, "
            "user_id INTEGER, "
            "tariff_code TEXT, "
            "status TEXT DEFAULT 'active', "
            "created_at INTEGER)"
        )
        async with db.execute("PRAGMA table_info(users)") as cursor:
            columns = {row[1] for row in await cursor.fetchall()}
        extra_cols = {
            "started_at": "INTEGER DEFAULT 0",
            "last_activity": "INTEGER DEFAULT 0",
            "reminder_stage": "INTEGER DEFAULT 0",
            "reminders_enabled": "INTEGER DEFAULT 1",
        }
        for name, declaration in extra_cols.items():
            if name not in columns:
                await db.execute(f"ALTER TABLE users ADD COLUMN {name} {declaration}")
        await db.commit()

# ================= ФУНКЦИЯ АКТИВАЦИИ ПОДПИСКИ =================
async def grant_subscription(user_id: int, tariff_code: str) -> str:
    days = TARIFFS[tariff_code]["days"]
    now = int(time.time())

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT sub_end FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            current_end = row[0] if row and row[0] > now else now

        new_end = current_end + (days * 86400)
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, started_at, last_activity) VALUES (?, ?, ?)",
            (user_id, now, now)
        )
        await db.execute(
            "UPDATE users SET sub_end = ?, grace_notified = 0, in_club = 1, reminder_stage = 99, last_activity = ? WHERE user_id = ?",
            (new_end, now, user_id)
        )
        await db.commit()

    try:
        invite = await bot.create_chat_invite_link(chat_id=CLUB_CHAT_ID, member_limit=1)
        return invite.invite_link
    except Exception as e:
        print(f"Ошибка генерации ссылки после оплаты: {e}")
        return "https://t.me/"

# ================= CRYPTOBOT API =================
async def create_crypto_invoice(user_id: int, tariff_code: str) -> Optional[dict]:
    t = TARIFFS[tariff_code]
    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
    payload = {
        "currency_type": "fiat",
        "fiat": "RUB",
        "accepted_assets": "USDT,TON,BTC,ETH,LTC,BNB",
        "amount": str(t["price"]),
        "description": f"Подписка на закрытый мужской клуб AURA ({t['title']})",
        "payload": f"sub_{tariff_code}_{user_id}",
        "expires_in": 3600
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{CRYPTO_API_URL}/createInvoice", headers=headers, json=payload) as resp:
            data = await resp.json()
            if data.get("ok"):
                return data["result"]
            print(f"Ошибка CryptoBot createInvoice: {data}")
            return None

async def get_crypto_invoice_status(invoice_id: int) -> Optional[str]:
    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
    params = {"invoice_ids": str(invoice_id)}
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{CRYPTO_API_URL}/getInvoices", headers=headers, params=params) as resp:
            data = await resp.json()
            if data.get("ok") and data["result"].get("items"):
                return data["result"]["items"][0]["status"]
            return None

# ================= УНИВЕРСАЛЬНАЯ ФУНКЦИЯ РЕДАКТИРОВАНИЯ =================
async def render_screen(target: Union[Message, CallbackQuery], text: str, reply_markup: InlineKeyboardMarkup):
    if isinstance(target, CallbackQuery):
        msg = target.message
        if isinstance(msg, Message):
            try:
                if msg.photo:
                    await msg.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="HTML")
                else:
                    await msg.edit_text(text=text, reply_markup=reply_markup, parse_mode="HTML")
            except TelegramBadRequest:
                if os.path.exists(MAIN_IMAGE):
                    await msg.answer_photo(FSInputFile(MAIN_IMAGE), caption=text, reply_markup=reply_markup, parse_mode="HTML")
                else:
                    await msg.answer(text=text, reply_markup=reply_markup, parse_mode="HTML")
        await target.answer()
    else:
        if os.path.exists(MAIN_IMAGE):
            await target.answer_photo(FSInputFile(MAIN_IMAGE), caption=text, reply_markup=reply_markup, parse_mode="HTML")
        else:
            await target.answer(text=text, reply_markup=reply_markup, parse_mode="HTML")

# ================= КЛАВИАТУРЫ =================
def main_menu_kb(trial_used: bool) -> InlineKeyboardMarkup:
    buttons = []
    if not trial_used:
        buttons.append([InlineKeyboardButton(text="🔥 Пробный доступ на 1 час (0 ₽)", callback_data="get_trial")])
    buttons.extend([
        [InlineKeyboardButton(text="🏴 Что внутри AURA?", callback_data="about_club")],
        [InlineKeyboardButton(text="⚔️ 1 месяц — 799 ₽", callback_data="buy_1m")],
        [InlineKeyboardButton(text="⚔️ 3 месяца — 1799 ₽", callback_data="buy_3m")],
        [InlineKeyboardButton(text="⚔️ 6 месяцев — 2999 ₽", callback_data="buy_6m")],
        [InlineKeyboardButton(text="👑 12 месяцев (ВЫГОДНЫЙ) — 4999 ₽", callback_data="buy_12m")],
        [InlineKeyboardButton(text="📊 Мой статус подписки", callback_data="my_status")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def payment_method_kb(tariff_code: str) -> InlineKeyboardMarkup:
    t = TARIFFS[tariff_code]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⭐ Telegram Stars ({t['stars']} ⭐)", callback_data=f"pay_stars_{tariff_code}")],
        [InlineKeyboardButton(text="💳 ЮKassa (Карта РФ / СБП)", callback_data=f"pay_rub_{tariff_code}")],
        [InlineKeyboardButton(text="💎 CryptoBot (USDT / TON / BTC)", callback_data=f"pay_crypto_{tariff_code}")],
        [InlineKeyboardButton(text="🔙 Назад в главное меню", callback_data="back_to_tariffs")]
    ])

def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в главное меню", callback_data="back_to_tariffs")]
    ])

# ================= ОБРАБОТЧИКИ =================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    now = int(time.time())
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, started_at, last_activity) VALUES (?, ?, ?)",
            (user_id, now, now)
        )
        await db.execute(
            "UPDATE users SET last_activity = ?, reminders_enabled = 1 WHERE user_id = ?",
            (now, user_id)
        )
        async with db.execute("SELECT trial_used FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            trial_used = bool(row[0]) if row else False
        await db.commit()

    await render_screen(message, MAIN_TEXT, main_menu_kb(trial_used))

@dp.callback_query(F.data == "back_to_tariffs")
async def back_to_tariffs(call: CallbackQuery):
    user_id = call.from_user.id
    now = int(time.time())
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET last_activity = ? WHERE user_id = ?", (now, user_id))
        async with db.execute("SELECT trial_used FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            trial_used = bool(row[0]) if row else False
        await db.commit()

    await render_screen(call, MAIN_TEXT, main_menu_kb(trial_used))

@dp.callback_query(F.data == "about_club")
async def about_club(call: CallbackQuery):
    await render_screen(call, ABOUT_TEXT, back_kb())

@dp.callback_query(F.data == "my_status")
async def my_status_cb(call: CallbackQuery):
    user_id = call.from_user.id
    now = int(time.time())
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT sub_end, trial_used FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()

    if not row or not row[0]:
        status_text = "\n".join([
            "📊 <b>СТАТУС ПОДПИСКИ</b>",
            "",
            "❌ У тебя пока нет активного доступа.",
            "Выбери тариф или активируй пробный час в главном меню."
        ])
    else:
        sub_end = row[0]
        if sub_end > now:
            rem = sub_end - now
            days = rem // 86400
            hours = (rem % 86400) // 3600
            mins = (rem % 3600) // 60
            status_text = "\n".join([
                "📊 <b>СТАТУС ПОДПИСКИ</b>",
                "",
                "✅ <b>Доступ активен.</b>",
                f"Осталось: <b>{days} дн. {hours} ч. {mins} мин.</b>"
            ])
        elif now < sub_end + GRACE_PERIOD:
            rem = (sub_end + GRACE_PERIOD) - now
            hours = rem // 3600
            status_text = "\n".join([
                "📊 <b>СТАТУС ПОДПИСКИ</b>",
                "",
                "⚠️ <b>Основной срок истек!</b>",
                f"Действует отсрочка: осталось <b>{hours} ч.</b> до автоматического исключения."
            ])
        else:
            status_text = "\n".join([
                "📊 <b>СТАТУС ПОДПИСКИ</b>",
                "",
                "❌ <b>Срок доступа истек.</b>",
                "Выбери тариф в меню, чтобы вернуться в клуб."
            ])

    await render_screen(call, status_text, back_kb())

@dp.callback_query(F.data == "get_trial")
async def process_trial(call: CallbackQuery):
    user_id = call.from_user.id
    now = int(time.time())

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT trial_used FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0] == 1:
                await call.answer("Ты уже использовал пробный период!", show_alert=True)
                return

    try:
        invite = await bot.create_chat_invite_link(
            chat_id=CLUB_CHAT_ID,
            member_limit=1,
            expire_date=now + 3600
        )
    except Exception as e:
        await call.answer(
            "Ошибка создания ссылки! Проверь CLUB_CHAT_ID и права бота (админ в группе).",
            show_alert=True
        )
        print(f"Ошибка создания инвайт-ссылки: {e}")
        return

    sub_end = now + TRIAL_DURATION
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET trial_used = 1, sub_end = ?, grace_notified = 0, in_club = 1, last_activity = ? WHERE user_id = ?",
            (sub_end, now, user_id)
        )
        await db.commit()

    trial_text = "\n".join([
        "⏳ <b>Пробный доступ на 1 час активирован!</b>",
        "",
        "Твоя одноразовая ссылка для входа в клуб:",
        f"👉 {invite.invite_link}",
        "",
        "⚠️ Через 1 час нужно будет выбрать тариф. Если не успеешь — бот даст ещё 3 дня отсрочки перед исключением."
    ])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Войти в AURA", url=invite.invite_link)],
        [InlineKeyboardButton(text="🔙 Назад в главное меню", callback_data="back_to_tariffs")]
    ])
    await render_screen(call, trial_text, kb)

@dp.callback_query(F.data.startswith("buy_"))
async def select_payment_method(call: CallbackQuery):
    if not call.data:
        return
    now = int(time.time())
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET last_activity = ? WHERE user_id = ?", (now, call.from_user.id))
        await db.commit()
    tariff_code = call.data.split("_")[1]
    t = TARIFFS[tariff_code]
    text = "\n".join([
        f"⚔️ <b>Тариф: {t['title']}</b>",
        f"Стоимость: <b>{t['price']} ₽</b> (или <b>{t['stars']} ⭐</b>)",
        f"Срок доступа: <b>{t['days']} дней</b>.",
        "",
        "Выбери удобный способ оплаты:"
    ])
    await render_screen(call, text, payment_method_kb(tariff_code))

# ================= ОПЛАТА TELEGRAM STARS (⭐) =================
@dp.callback_query(F.data.startswith("pay_stars_"))
async def pay_stars(call: CallbackQuery):
    if not call.data:
        return
    tariff_code = call.data.split("_")[2]
    t = TARIFFS[tariff_code]

    try:
        prices = [LabeledPrice(label=f"Доступ: {t['title']}", amount=t["stars"])]
        await bot.send_invoice(
            chat_id=call.from_user.id,
            title=f"Клуб AURA ({t['title']})",
            description=f"Подписка на закрытый мужской клуб AURA на {t['days']} дней.",
            payload=f"stars_sub_{tariff_code}",
            provider_token="",  # Пустая строка для Telegram Stars (XTR)
            currency="XTR",     # Официальный код валюты Telegram Stars
            prices=prices
        )
        await call.answer()
    except Exception as e:
        await call.answer("Ошибка создания счета Stars.", show_alert=True)
        print(f"Ошибка Stars invoice: {e}")

# ================= ОПЛАТА ЮKASSA (РУБЛИ) =================
@dp.callback_query(F.data.startswith("pay_rub_"))
async def pay_rub(call: CallbackQuery):
    if not call.data:
        return
    tariff_code = call.data.split("_")[2]
    t = TARIFFS[tariff_code]

    if not PAYMENT_TOKEN or "ТОКЕН" in PAYMENT_TOKEN:
        await call.answer("Укажи рабочий PAYMENT_TOKEN от ЮKassa в настройках кода!", show_alert=True)
        return

    provider_data = json.dumps({
        "receipt": {
            "items": [
                {
                    "description": f"Подписка на клуб AURA ({t['title']})",
                    "quantity": "1.00",
                    "amount": {"value": f"{t['price']}.00", "currency": "RUB"},
                    "vat_code": 1
                }
            ]
        }
    })

    try:
        await bot.send_invoice(
            chat_id=call.from_user.id,
            title=f"Доступ в клуб AURA ({t['title']})",
            description=f"Подписка на закрытый мужской клуб AURA на {t['days']} дней.",
            payload=f"sub_{tariff_code}",
            provider_token=PAYMENT_TOKEN,
            currency="RUB",
            prices=[LabeledPrice(label=f"Подписка на {t['title']}", amount=t["price"] * 100)],
            need_email=True,
            send_email_to_provider=True,
            provider_data=provider_data
        )
        await call.answer()
    except Exception as e:
        await call.answer("Ошибка выставления счета ЮKassa.", show_alert=True)
        print(f"Ошибка ЮKassa: {e}")

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    if not message.successful_payment or not message.from_user:
        return
    payload = message.successful_payment.invoice_payload
    
    if payload.startswith("stars_sub_"):
        tariff_code = payload.replace("stars_sub_", "")
    else:
        tariff_code = payload.split("_")[1]

    days = TARIFFS[tariff_code]["days"]
    user_id = message.from_user.id

    invite_link = await grant_subscription(user_id, tariff_code)
    msg_text = "\n".join([
        f"✅ <b>Оплата прошла успешно! Подписка продлена на {days} дн.</b>",
        "",
        "Твоя персональная ссылка для входа в клуб:",
        f"👉 {invite_link}"
    ])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Войти в AURA", url=invite_link)],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_tariffs")]
    ])
    await message.answer(msg_text, reply_markup=kb, parse_mode="HTML")

# ================= ОПЛАТА CRYPTOBOT =================
@dp.callback_query(F.data.startswith("pay_crypto_"))
async def pay_crypto(call: CallbackQuery):
    if not call.data:
        return
    tariff_code = call.data.split("_")[2]
    t = TARIFFS[tariff_code]
    user_id = call.from_user.id

    if not CRYPTO_PAY_TOKEN or "ТОКЕН" in CRYPTO_PAY_TOKEN:
        await call.answer("Вставь свой API-токен от @CryptoBot в CRYPTO_PAY_TOKEN!", show_alert=True)
        return

    invoice = await create_crypto_invoice(user_id, tariff_code)
    if not invoice:
        await call.answer("Не удалось создать счет в @CryptoBot.", show_alert=True)
        return

    invoice_id = invoice["invoice_id"]
    pay_url = invoice.get("bot_invoice_url") or invoice.get("pay_url")
    now = int(time.time())

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO crypto_invoices (invoice_id, user_id, tariff_code, status, created_at) VALUES (?, ?, ?, 'active', ?)",
            (invoice_id, user_id, tariff_code, now)
        )
        await db.commit()

    text = "\n".join([
        "💎 <b>Счет в @CryptoBot создан!</b>",
        "",
        f"• Тариф: <b>{t['title']} ({t['price']} ₽)</b>",
        "• Валюта: <b>USDT, TON, BTC, ETH, LTC</b>",
        "",
        "1. Нажми кнопку <b>«💎 Оплатить в CryptoBot»</b> ниже.",
        "2. Доступ откроется автоматически после оплаты."
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Оплатить в CryptoBot", url=pay_url)],
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_crypto_{invoice_id}")],
        [InlineKeyboardButton(text="🔙 Назад к способам оплаты", callback_data=f"buy_{tariff_code}")]
    ])
    await render_screen(call, text, kb)

@dp.callback_query(F.data.startswith("check_crypto_"))
async def check_crypto_manual(call: CallbackQuery):
    if not call.data:
        return
    invoice_id = int(call.data.split("_")[2])

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT user_id, tariff_code, status FROM crypto_invoices WHERE invoice_id = ?", (invoice_id,)
        ) as cursor:
            row = await cursor.fetchone()

    if not row:
        await call.answer("Счет не найден.", show_alert=True)
        return

    user_id, tariff_code, db_status = row
    if db_status == "paid":
        await call.answer("Этот счет уже оплачен!", show_alert=True)
        return

    status = await get_crypto_invoice_status(invoice_id)
    if status == "paid":
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE crypto_invoices SET status = 'paid' WHERE invoice_id = ?", (invoice_id,))
            await db.commit()

        days = TARIFFS[tariff_code]["days"]
        invite_link = await grant_subscription(user_id, tariff_code)
        msg_text = "\n".join([
            f"✅ <b>Оплата через @CryptoBot подтверждена! Подписка продлена на {days} дн.</b>",
            "",
            "Твоя ссылка для входа в клуб:",
            f"👉 {invite_link}"
        ])
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Войти в AURA", url=invite_link)],
            [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_tariffs")]
        ])
        await render_screen(call, msg_text, kb)
    elif status == "active":
        await call.answer("Оплата еще не поступила.", show_alert=True)
    else:
        await call.answer("Время действия счета истекло.", show_alert=True)

@dp.message(F.text == "/stop")
async def stop_reminders(message: Message):
    if not message.from_user:
        return
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET reminders_enabled = 0 WHERE user_id = ?", (message.from_user.id,))
        await db.commit()
    await message.answer("Уведомления отключены. Чтобы вернуться в меню, напиши /start.")

@dp.message(F.text == "/id")
async def get_chat_id(message: Message):
    await message.answer(f"ID этого чата: <code>{message.chat.id}</code>", parse_mode="HTML")

# ================= ФОНОВЫЕ ЦИКЛЫ =================
async def check_crypto_invoices_loop():
    while True:
        try:
            if CRYPTO_PAY_TOKEN and "ТОКЕН" not in CRYPTO_PAY_TOKEN:
                now = int(time.time())
                async with aiosqlite.connect(DB_NAME) as db:
                    async with db.execute(
                        "SELECT invoice_id, user_id, tariff_code FROM crypto_invoices WHERE status = 'active' AND created_at > ?",
                        (now - 7200,)
                    ) as cursor:
                        active_invoices = await cursor.fetchall()

                    for invoice_id, user_id, tariff_code in active_invoices:
                        status = await get_crypto_invoice_status(invoice_id)
                        if status == "paid":
                            await db.execute("UPDATE crypto_invoices SET status = 'paid' WHERE invoice_id = ?", (invoice_id,))
                            await db.commit()
                            days = TARIFFS[tariff_code]["days"]
                            invite_link = await grant_subscription(user_id, tariff_code)
                            msg_text = "\n".join([
                                f"✅ <b>Оплата через @CryptoBot получена! Подписка продлена на {days} дн.</b>",
                                "",
                                "Ссылка для входа в клуб:",
                                f"👉 {invite_link}"
                            ])
                            kb = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="🚀 Войти в AURA", url=invite_link)],
                                [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_tariffs")]
                            ])
                            try:
                                await bot.send_message(user_id, msg_text, reply_markup=kb, parse_mode="HTML")
                            except Exception:
                                pass
                        elif status in ("expired", "cancelled"):
                            await db.execute("UPDATE crypto_invoices SET status = ? WHERE invoice_id = ?", (status, invoice_id))
                            await db.commit()
        except Exception as e:
            print(f"Ошибка фоновой проверки CryptoBot: {e}")
        await asyncio.sleep(15)

async def check_subscriptions_loop():
    while True:
        now = int(time.time())
        try:
            async with aiosqlite.connect(DB_NAME) as db:
                async with db.execute(
                    "SELECT user_id FROM users WHERE in_club = 1 AND sub_end < ? AND grace_notified = 0", (now,)
                ) as cursor:
                    expired_users = await cursor.fetchall()

                for (user_id,) in expired_users:
                    try:
                        exp_msg = "\n".join([
                            "⚠️ <b>Срок твоего доступа в клуб «AURA» истек!</b>",
                            "",
                            "Тебе открыты <b>дополнительные 3 дня</b>, чтобы ты спокойно продлил подписку.",
                            "Если в течение 72 часов оплата не поступит — бот автоматически исключит тебя из группы."
                        ])
                        await bot.send_message(user_id, exp_msg, reply_markup=main_menu_kb(trial_used=True), parse_mode="HTML")
                    except Exception:
                        pass
                    await db.execute("UPDATE users SET grace_notified = 1 WHERE user_id = ?", (user_id,))
                    await db.commit()

                async with db.execute(
                    "SELECT user_id FROM users WHERE in_club = 1 AND (sub_end + ?) < ?", (GRACE_PERIOD, now)
                ) as cursor:
                    kick_users = await cursor.fetchall()

                for (user_id,) in kick_users:
                    try:
                        await bot.ban_chat_member(chat_id=CLUB_CHAT_ID, user_id=user_id)
                        await bot.unban_chat_member(chat_id=CLUB_CHAT_ID, user_id=user_id)
                        kick_msg = "\n".join([
                            "❌ <b>Твои 3 дополнительных дня истекли.</b>",
                            "Ты был исключен из клуба. Выбери тариф, чтобы вернуться:"
                        ])
                        await bot.send_message(user_id, kick_msg, reply_markup=main_menu_kb(trial_used=True), parse_mode="HTML")
                    except Exception as e:
                        print(f"Ошибка при кике {user_id}: {e}")
                    await db.execute("UPDATE users SET in_club = 0 WHERE user_id = ?", (user_id,))
                    await db.commit()
        except Exception as e:
            print(f"Ошибка в цикле проверки подписок: {e}")
        await asyncio.sleep(60)

async def send_marketing_reminders_loop():
    delays = {0: 1800, 1: 3 * 3600, 2: 12 * 3600, 3: 24 * 3600, 4: 48 * 3600, 5: 72 * 3600}
    while True:
        now = int(time.time())
        try:
            async with aiosqlite.connect(DB_NAME) as db:
                async with db.execute(
                    "SELECT user_id, started_at, last_activity, reminder_stage, trial_used, in_club "
                    "FROM users WHERE reminders_enabled = 1 AND reminder_stage < 6"
                ) as cursor:
                    rows = await cursor.fetchall()

                for user_id, started_at, last_activity, stage, trial_used, in_club in rows:
                    if not started_at or in_club:
                        continue
                    anchor = max(started_at, last_activity or started_at)
                    if now - anchor < delays.get(stage, 10**12):
                        continue

                    callout = random.choice(REMINDER_MESSAGES)
                    text = f"🏴 <b>AURA | Напоминание</b>\n\n{callout}"
                    btn_label = "🔥 Забрать 1 час бесплатно" if not trial_used else "⚔️ Выбрать тариф"
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=btn_label, callback_data="back_to_tariffs")]
                    ])
                    try:
                        await bot.send_message(user_id, text, reply_markup=kb, parse_mode="HTML")
                    except Exception:
                        await db.execute("UPDATE users SET reminders_enabled = 0 WHERE user_id = ?", (user_id,))
                        await db.commit()
                        continue

                    await db.execute(
                        "UPDATE users SET reminder_stage = ?, last_activity = ? WHERE user_id = ?",
                        (stage + 1, now, user_id)
                    )
                    await db.commit()
        except Exception as e:
            print(f"Ошибка цикла дожимов: {e}")
        await asyncio.sleep(120)

async def main():
    await init_db()
    asyncio.create_task(check_subscriptions_loop())
    asyncio.create_task(check_crypto_invoices_loop())
    asyncio.create_task(send_marketing_reminders_loop())
    print("✅ Бот AURA успешно запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
