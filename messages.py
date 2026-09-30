"""Botning barcha matnlari (o'zbek tilida, lotin yozuvi).

Matnlar HTML formatida (parse_mode=HTML). Foydalanuvchi kiritgan har qanday
qiymat shablonga qo'yilishidan oldin html.escape() orqali tozalanishi shart.

⚠️ KLINIKA MA'LUMOTLARI (CLINIC_*) VA FAQ JAVOBLARI — NAMUNA. Ishga
tushirishdan oldin ularni klinikangizning haqiqiy ma'lumotlari bilan
almashtiring.
"""

from __future__ import annotations

from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

from storage import Appeal
from validators import TEXT_MAX, TEXT_MIN

# --- Klinika ma'lumotlari (O'ZGARTIRING) -------------------------------------

CLINIC_NAME = "Yuridik klinika"
CLINIC_DESCRIPTION = (
    "Klinikamiz fuqarolarga fuqarolik, oila, mehnat, uy-joy va maʼmuriy "
    "huquq masalalarida bepul huquqiy maslahat beradi."
)
CLINIC_ADDRESS = "Toshkent sh., [koʻcha nomi, uy raqami]"
CLINIC_HOURS = "Dushanba–Juma, 09:00–18:00 (tushlik 13:00–14:00)"
CLINIC_PHONE = "+998 [XX] [XXX-XX-XX]"
CLINIC_EMAIL = "[klinika]@example.com"

# --- Tugmalar ----------------------------------------------------------------

BTN_APPEAL = "📝 Murojaat yuborish"
BTN_ABOUT = "ℹ️ Biz haqimizda"
BTN_FAQ = "❓ Koʻp beriladigan savollar"
BTN_MENU = "🏠 Bosh menyu"

BTN_CANCEL = "❌ Bekor qilish"
BTN_SHARE_CONTACT = "📱 Raqamni ulashish"
BTN_SKIP = "⏭ Oʻtkazib yuborish"

BTN_SEND = "✅ Yuborish"
BTN_RESTART = "✏️ Qaytadan toʻldirish"
BTN_FAQ_BACK = "⬅️ Savollar roʻyxati"
BTN_PREV = "◀️ Oldingi"
BTN_NEXT = "Keyingi ▶️"
BTN_ADMIN_BACK = "⬅️ Roʻyxatga qaytish"

# --- Umumiy ------------------------------------------------------------------

WELCOME = (
    "Assalomu alaykum, {name}! 👋\n\n"
    "<b>{clinic}</b> rasmiy botiga xush kelibsiz.\n\n"
    "Bu yerda huquqiy masalangiz boʻyicha klinikamizga murojaat yuborishingiz "
    "mumkin. Murojaatingizni yuristlarimiz koʻrib chiqib, siz bilan bogʻlanadi.\n\n"
    "Kerakli boʻlimni tanlang 👇"
)

DEFAULT_USER_NAME = "hurmatli foydalanuvchi"

MAIN_MENU = "🏠 Bosh menyu. Kerakli boʻlimni tanlang 👇"

# Telegram'ning "/" menyusidagi buyruqlar tavsifi
CMD_START = "Botni ishga tushirish"
CMD_APPEAL = "Yangi murojaat yuborish"
CMD_CANCEL = "Murojaatni bekor qilish"
CMD_HELP = "Yordam"
CMD_ADMIN = "Murojaatlar roʻyxati"

HELP = (
    "ℹ️ <b>Yordam</b>\n\n"
    "/start — botni ishga tushirish\n"
    "/murojaat — yangi murojaat yuborish\n"
    "/cancel — toʻldirilayotgan murojaatni bekor qilish\n"
    "/help — shu yordam\n\n"
    f"Murojaat yuborish uchun «{BTN_APPEAL}» tugmasini bosing."
)

UNKNOWN = "Tushunmadim 🤔 Iltimos, pastdagi menyudan kerakli boʻlimni tanlang."

ERROR = "⚠️ Kutilmagan xatolik yuz berdi. Iltimos, birozdan soʻng qayta urinib koʻring."

ABOUT = (
    f"⚖️ <b>{escape(CLINIC_NAME)}</b>\n\n"
    f"{escape(CLINIC_DESCRIPTION)}\n\n"
    f"📍 <b>Manzil:</b> {escape(CLINIC_ADDRESS)}\n"
    f"🕘 <b>Ish vaqti:</b> {escape(CLINIC_HOURS)}\n"
    f"📞 <b>Telefon:</b> {escape(CLINIC_PHONE)}\n"
    f"✉️ <b>Email:</b> {escape(CLINIC_EMAIL)}\n\n"
    f"Murojaat yuborish uchun «{BTN_APPEAL}» tugmasini bosing."
)

# --- FAQ ---------------------------------------------------------------------

FAQ_INTRO = "❓ <b>Koʻp beriladigan savollar</b>\n\nQiziqtirgan savolni tanlang 👇"

# (savol, javob). Savol inline tugmada ko'rinadi — qisqa bo'lgani ma'qul.
FAQ: list[tuple[str, str]] = [
    (
        "Klinika qanday masalalarda yordam beradi?",
        "Klinikamiz quyidagi yoʻnalishlarda maslahat beradi:\n\n"
        "• <b>Fuqarolik ishlari</b> — shartnomalar, qarz, meros, mulk nizolari;\n"
        "• <b>Oilaviy ishlar</b> — nikoh, ajrim, aliment, vasiylik;\n"
        "• <b>Mehnat nizolari</b> — ishga qabul qilish, ishdan boʻshatish, ish haqi;\n"
        "• <b>Uy-joy masalalari</b> — ijara, xususiylashtirish, kommunal xizmatlar;\n"
        "• <b>Ijtimoiy taʼminot</b> — pensiya, nafaqa, imtiyozlar;\n"
        "• <b>Isteʼmolchilar huquqlari</b>;\n"
        "• <b>Maʼmuriy masalalar</b> — davlat organlari qarorlari ustidan shikoyat.",
    ),
    (
        "Jinoyat ishlari boʻyicha yordam berasizmi?",
        "Yoʻq. Klinika <b>jinoyat ishlari</b> (jinoyat qonunchiligi) boʻyicha "
        "maslahat bermaydi va himoyani oʻz zimmasiga olmaydi.\n\n"
        "Bunday holatda malakali advokatga murojaat qilishingizni tavsiya qilamiz.",
    ),
    (
        "Xizmatlar pullikmi?",
        "Yoʻq, klinikaning huquqiy maslahatlari <b>bepul</b>.",
    ),
    (
        "Murojaat qanday yuboriladi?",
        f"1. «{BTN_APPEAL}» tugmasini bosing.\n"
        "2. Ism-familiyangizni kiriting.\n"
        "3. Telefon raqamingizni ulashing yoki yozing.\n"
        "4. Email manzilingizni kiriting (ixtiyoriy).\n"
        "5. Muammongizni batafsil yozing va yuboring.\n\n"
        "Yuborilgandan soʻng sizga murojaat raqami beriladi "
        "(masalan, <code>APPEAL-2026-001</code>).",
    ),
    (
        "Murojaat qancha muddatda koʻrib chiqiladi?",
        "Odatda murojaatlar <b>5 ish kuni</b> ichida koʻrib chiqiladi va yurist "
        "siz koʻrsatgan telefon yoki email orqali bogʻlanadi.",
    ),
    (
        "Hujjatlarni qanday yuboraman?",
        "Bot faqat <b>matnli</b> murojaatlarni qabul qiladi. Murojaatda "
        "vaziyatni batafsil yozing; hujjatlar kerak boʻlsa, yurist siz bilan "
        "bogʻlanib, ularni qanday taqdim etishni tushuntiradi.",
    ),
    (
        "Maʼlumotlarim maxfiy saqlanadimi?",
        "Ha. Bot maʼlumotlar bazasiga hech narsa yozmaydi: murojaatingiz "
        "faqat klinika xodimlariga yetkaziladi va faqat sizga huquqiy yordam "
        "koʻrsatish maqsadida ishlatiladi.",
    ),
]

# --- Murojaat yuborish jarayoni ---------------------------------------------

ASK_NAME = (
    "📝 <b>Yangi murojaat</b> · 1/4-qadam\n\n"
    "⚠️ <i>Klinika jinoyat ishlari boʻyicha murojaatlarni koʻrib chiqmaydi — "
    "bunday holatda malakali advokatga murojaat qiling.</i>\n\n"
    "Ism va familiyangizni kiriting:\n"
    "<i>Masalan: Aliyev Vali</i>"
)
BAD_NAME = (
    "⚠️ Ism-familiya 2 tadan 100 tagacha belgidan iborat boʻlishi va "
    "harflarni oʻz ichiga olishi kerak. Qaytadan kiriting:"
)

ASK_PHONE = (
    "📞 <b>2/4-qadam</b>\n\n"
    f"Telefon raqamingizni yuboring: pastdagi «{BTN_SHARE_CONTACT}» tugmasini "
    "bosing yoki raqamni qoʻlda yozing.\n"
    "<i>Masalan: +998 90 123 45 67</i>"
)
BAD_PHONE = (
    "⚠️ Telefon raqami notoʻgʻri. Raqamni <i>+998901234567</i> koʻrinishida "
    f"yozing yoki «{BTN_SHARE_CONTACT}» tugmasini bosing:"
)

ASK_EMAIL = (
    "✉️ <b>3/4-qadam</b>\n\n"
    "Elektron pochta (email) manzilingizni kiriting.\n"
    f"Agar email boʻlmasa, «{BTN_SKIP}» tugmasini bosing."
)
BAD_EMAIL = (
    "⚠️ Email manzili notoʻgʻri (masalan: <i>ism@example.com</i>). "
    f"Qaytadan kiriting yoki «{BTN_SKIP}» tugmasini bosing:"
)

ASK_TEXT = (
    "🧾 <b>4/4-qadam</b>\n\n"
    "Murojaatingiz matnini yozing: nima sodir boʻlgani, qachon boʻlgani va "
    "qanday yordam kutayotganingizni batafsil bayon qiling.\n\n"
    f"<i>Kamida {TEXT_MIN} ta, koʻpi bilan {TEXT_MAX} ta belgi. "
    "Faqat matn qabul qilinadi. Bir nechta xabar yuborsangiz, ular bitta "
    "murojaat matniga qoʻshiladi.</i>"
)
TEXT_TOO_SHORT = (
    f"⚠️ Murojaat juda qisqa (kamida {TEXT_MIN} ta belgi kerak). "
    "Vaziyatni batafsilroq yozing:"
)
TEXT_APPEND_TOO_LONG = (
    "⚠️ Bu xabarni qoʻshib boʻlmadi: murojaat matni "
    f"{TEXT_MAX} ta belgidan oshib ketadi. Murojaatni shu holicha yuborishingiz "
    "yoki «✏️ Qaytadan toʻldirish» tugmasini bosishingiz mumkin."
)
TEXT_TOO_LONG = (
    "⚠️ Murojaat juda uzun ({length} ta belgi, ruxsat etilgani — "
    f"{TEXT_MAX} ta). Qisqartirib, qaytadan yuboring:"
)

ONLY_TEXT = "⚠️ Bot faqat matnli xabarlarni qabul qiladi. Iltimos, maʼlumotni matn koʻrinishida yozing."

EMAIL_NOT_GIVEN = "koʻrsatilmagan"

CONFIRM = (
    "🔎 <b>Maʼlumotlarni tekshiring</b>\n\n"
    "👤 <b>Ism:</b> {name}\n"
    "📞 <b>Telefon:</b> {phone}\n"
    "✉️ <b>Email:</b> {email}\n\n"
    "🧾 <b>Murojaat matni:</b>\n{text}\n\n"
    "Hammasi toʻgʻrimi?"
)
PRESS_BUTTON = (
    "👆 Iltimos, yuqoridagi xabardagi tugmalardan birini bosing: "
    f"«{BTN_SEND}», «{BTN_RESTART}» yoki «{BTN_CANCEL}»."
)

ACCEPTED = (
    "✅ <b>Murojaatingiz qabul qilindi!</b>\n\n"
    "Murojaat raqami: <code>{appeal_id}</code>\n\n"
    "Yuristlarimiz murojaatingizni koʻrib chiqib, siz koʻrsatgan telefon yoki "
    "email orqali bogʻlanadi. Iltimos, murojaat raqamini saqlab qoʻying."
)
CANCELLED = "❌ Murojaat bekor qilindi."
RESTARTED = "✏️ Maʼlumotlarni qaytadan kiritamiz."
TIMEOUT = (
    "⌛ Murojaat uzoq vaqt toʻldirilmagani uchun bekor qilindi. "
    f"Qaytadan boshlash uchun «{BTN_APPEAL}» tugmasini bosing."
)
SESSION_LOST = (
    "⚠️ Toʻldirilayotgan murojaat maʼlumotlari topilmadi (kutish muddati "
    "tugagan yoki bot qayta ishga tushirilgan boʻlishi mumkin). Murojaat "
    f"yuborilmadi. Iltimos, «{BTN_APPEAL}» tugmasini bosib, qaytadan boshlang."
)
ALREADY_SENT = "Bu murojaat allaqachon yuborilgan: {appeal_id}"
STALE_BUTTON = "Bu tugma eskirgan."

# --- Admin -------------------------------------------------------------------

ADMIN_ONLY = "⛔ Bu buyruq faqat klinika administratorlari uchun."

ADMIN_NEW_APPEAL = "📥 <b>Yangi murojaat</b>\n\n{body}"

ADMIN_EMPTY = (
    "📋 Hozircha murojaatlar yoʻq.\n\n"
    "<i>Roʻyxatda faqat bot oxirgi marta ishga tushirilgandan beri kelgan "
    "murojaatlar koʻrinadi. Barcha murojaatlarning doimiy nusxasi — admin "
    "chatiga yuborilgan xabarlar.</i>"
)
ADMIN_LIST_HEADER = "📋 <b>Murojaatlar</b> — jami {total} ta · {page}/{pages}-sahifa\n\n"
ADMIN_LIST_ITEM = (
    "<b>{n}.</b> <code>{appeal_id}</code> — {name}\n"
    "🕒 {date} · 📞 {phone}\n"
    "<i>{preview}</i>\n\n"
)
ADMIN_LIST_FOOTER = (
    "Toʻliq matnni koʻrish uchun murojaat raqamini bosing.\n"
    "<i>Roʻyxat bot xotirasida saqlanadi va qayta ishga tushirilganda tozalanadi.</i>"
)
ADMIN_NOT_FOUND = "Murojaat xotirada topilmadi (bot qayta ishga tushirilgan boʻlishi mumkin)."

PHONE_VERIFIED = "✅ Telegram orqali tasdiqlangan"
PHONE_TYPED = "qoʻlda kiritilgan"
NO_USERNAME = "username yoʻq"

APPEAL_CARD = (
    "🆔 <b>{appeal_id}</b>\n"
    "🕒 {date}\n\n"
    "👤 <b>Ism:</b> {name}\n"
    "📞 <b>Telefon:</b> {phone} ({phone_note})\n"
    "✉️ <b>Email:</b> {email}\n"
    "💬 <b>Telegram:</b> {telegram} · ID <code>{user_id}</code>\n\n"
    "🧾 <b>Murojaat matni:</b>\n{text}"
)

DATE_FORMAT = "%d.%m.%Y %H:%M"


def format_date(dt: datetime, tz: ZoneInfo) -> str:
    return dt.astimezone(tz).strftime(DATE_FORMAT)


def render_appeal(appeal: Appeal, tz: ZoneInfo) -> str:
    """Murojaatning to'liq kartasi (admin uchun), HTML."""
    if appeal.username:
        telegram = escape(f"@{appeal.username}")
    else:
        telegram = f'<a href="tg://user?id={appeal.user_id}">{escape(NO_USERNAME)}</a>'
    return APPEAL_CARD.format(
        appeal_id=escape(appeal.appeal_id),
        date=format_date(appeal.created_at, tz),
        name=escape(appeal.full_name),
        phone=escape(appeal.phone),
        phone_note=PHONE_VERIFIED if appeal.phone_verified else PHONE_TYPED,
        email=escape(appeal.email) if appeal.email else EMAIL_NOT_GIVEN,
        telegram=telegram,
        user_id=appeal.user_id,
        text=escape(appeal.text),
    )


def render_preview(text: str, limit: int = 80) -> str:
    """Ro'yxat uchun bir qatorli qisqa ko'rinish, HTML."""
    one_line = " ".join(text.split())
    if len(one_line) > limit:
        one_line = one_line[: limit - 1].rstrip() + "…"
    return escape(one_line)
