"""Murojaat yuborish jarayoni (ConversationHandler).

Qadamlar: soha → ism → telefon → email (ixtiyoriy) → murojaat matni → tasdiqlash.
To'ldirilayotgan murojaat faqat context.user_data ichida (RAM) turadi.
"""

from __future__ import annotations

import logging
import warnings
from datetime import datetime, timedelta
from html import escape
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.error import ChatMigrated, TelegramError
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    TypeHandler,
    filters,
)
from telegram.warnings import PTBUserWarning

import keyboards as kb
import messages as msg
from handlers import common
from handlers.utils import (
    PRIVATE,
    get_admin_chat_id,
    get_settings,
    get_store,
    set_admin_chat_id,
)
from storage import Appeal
from validators import TEXT_MAX, check_text, clean_email, clean_name, normalize_phone

logger = logging.getLogger(__name__)

CATEGORY, NAME, PHONE, EMAIL, TEXT, CONFIRM = range(6)
END = ConversationHandler.END

DRAFT = "appeal_draft"
SUBMITTED = common.SUBMITTED

# Tugma matnlari foydalanuvchi ma'lumoti sifatida qabul qilinmasligi kerak.
_BUTTON_TEXTS = filters.Text(
    [
        msg.BTN_APPEAL,
        msg.BTN_ABOUT,
        msg.BTN_FAQ,
        msg.BTN_MENU,
        msg.BTN_CANCEL,
        msg.BTN_SKIP,
        msg.BTN_SHARE_CONTACT,
        *msg.CATEGORIES,
    ]
)
USER_TEXT = PRIVATE & filters.TEXT & ~filters.COMMAND & ~_BUTTON_TEXTS
# /admin murojaat to'ldirilayotganda ham o'z handleriga o'tishi kerak.
_ADMIN_COMMAND = filters.Regex(r"^/admin(@\w+)?(\s|$)")

_PROMPTS = {
    CATEGORY: (msg.ASK_CATEGORY, kb.categories),
    NAME: (msg.ASK_NAME, kb.cancel_only),
    PHONE: (msg.ASK_PHONE, kb.share_contact),
    EMAIL: (msg.ASK_EMAIL, kb.skip_email),
    TEXT: (msg.ASK_TEXT, kb.cancel_only),
}


def _draft(context: ContextTypes.DEFAULT_TYPE) -> dict:
    return context.user_data.setdefault(DRAFT, {})


async def _ask(update: Update, context: ContextTypes.DEFAULT_TYPE, step: int) -> int:
    text, keyboard = _PROMPTS[step]
    _draft(context)["step"] = step
    await update.effective_message.reply_text(text, reply_markup=keyboard())
    return step


async def _reply_safely(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, **kwargs
) -> None:
    """Javob yuborishga ikki marta urinadi; xato bo'lsa faqat log'ga yozadi.

    Suhbatni yakunlovchi javoblar uchun: xabar yuborilmay qolsa ham suhbat
    baribir END holatiga o'tishi kerak.
    """
    try:
        await update.effective_message.reply_text(text, **kwargs)
        return
    except TelegramError:
        logger.warning("Javobni yuborib bo'lmadi, qayta urinilmoqda", exc_info=True)
    try:
        await context.bot.send_message(update.effective_chat.id, text, **kwargs)
    except TelegramError:
        logger.exception("Javobni yuborib bo'lmadi (chat %s)", update.effective_chat.id)


async def _discard_draft(update: Update, context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Qoralamani o'chiradi va eski tasdiqlash xabaridagi tugmalarni olib tashlaydi."""
    draft = context.user_data.pop(DRAFT, None) if context.user_data is not None else None
    draft = draft or {}
    confirm_id = draft.get("confirm_message_id")
    if confirm_id and update.effective_chat is not None:
        try:
            await context.bot.edit_message_reply_markup(
                update.effective_chat.id, confirm_id, reply_markup=None
            )
        except TelegramError:
            pass  # xabar allaqachon tahrirlangan yoki o'chirilgan — muhim emas
    return draft


def _has_contact_data(draft: dict) -> bool:
    return bool(draft.get("full_name") and draft.get("phone"))


async def _send_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    draft = _draft(context)
    draft["step"] = CONFIRM
    sent = await update.effective_message.reply_text(
        msg.CONFIRM.format(
            category=escape(draft.get("category") or "—"),
            name=escape(draft["full_name"]),
            phone=escape(draft["phone"]),
            email=escape(draft["email"]) if draft.get("email") else msg.EMAIL_NOT_GIVEN,
            text=escape(draft["text"]),
        ),
        reply_markup=kb.confirm_appeal(),
    )
    # Faqat eng oxirgi tasdiqlash xabaridagi tugmalar ishlaydi.
    draft["confirm_message_id"] = sent.message_id
    return CONFIRM


# --- Qadamlar ---------------------------------------------------------------


RATE_WINDOW = timedelta(days=1)


def _rate_limited(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    settings = get_settings(context)
    count = get_store(context).recent_count(
        update.effective_user.id, datetime.now(settings.timezone), RATE_WINDOW
    )
    return count >= settings.max_appeals_per_day


async def start_appeal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _discard_draft(update, context)
    if _rate_limited(update, context):
        return await _finish(
            update,
            context,
            msg.RATE_LIMITED.format(
                limit=get_settings(context).max_appeals_per_day,
                phone=escape(msg.CLINIC_PHONE),
            ),
        )
    context.user_data[DRAFT] = {}
    return await _ask(update, context, CATEGORY)


async def got_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    _draft(context)["category"] = update.message.text
    return await _ask(update, context, NAME)


async def got_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = clean_name(update.message.text)
    if name is None:
        await update.message.reply_text(msg.BAD_NAME)
        return NAME
    _draft(context)["full_name"] = name
    return await _ask(update, context, PHONE)


async def got_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    contact = update.message.contact
    phone = normalize_phone(contact.phone_number or "")
    if phone is None:
        await update.message.reply_text(msg.BAD_PHONE)
        return PHONE
    draft = _draft(context)
    draft["phone"] = phone
    # Foydalanuvchi o'z kontaktini ulashgan bo'lsa, raqam Telegram tomonidan
    # tasdiqlangan hisoblanadi; boshqa birovning kontakti — yo'q.
    draft["phone_verified"] = contact.user_id == update.effective_user.id
    return await _ask(update, context, EMAIL)


async def got_phone_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = normalize_phone(update.message.text)
    if phone is None:
        await update.message.reply_text(msg.BAD_PHONE)
        return PHONE
    draft = _draft(context)
    draft["phone"] = phone
    draft["phone_verified"] = False
    return await _ask(update, context, EMAIL)


async def skipped_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    _draft(context)["email"] = None
    return await _ask(update, context, TEXT)


async def got_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    email = clean_email(update.message.text)
    if email is None:
        await update.message.reply_text(msg.BAD_EMAIL)
        return EMAIL
    _draft(context)["email"] = email
    return await _ask(update, context, TEXT)


async def got_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _has_contact_data(_draft(context)):
        return await _finish(update, context, msg.SESSION_LOST)

    text, error = check_text(update.message.text)
    if error == "short":
        await update.message.reply_text(msg.TEXT_TOO_SHORT)
        return TEXT
    if error == "long":
        await update.message.reply_text(
            msg.TEXT_TOO_LONG.format(length=len(update.message.text.strip()))
        )
        return TEXT

    _draft(context)["text"] = text
    return await _send_confirmation(update, context)


async def appended_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Tasdiqlash bosqichida kelgan qo'shimcha xabar murojaat matniga qo'shiladi
    (odamlar ko'pincha bitta fikrni bir nechta xabarda yozadi)."""
    draft = _draft(context)
    if not (_has_contact_data(draft) and draft.get("text")):
        return await _finish(update, context, msg.SESSION_LOST)

    combined = f"{draft['text']}\n{update.message.text.strip()}"
    if len(combined) > TEXT_MAX:
        await update.message.reply_text(msg.TEXT_APPEND_TOO_LONG)
        return CONFIRM

    old_confirm_id = draft.get("confirm_message_id")
    draft["text"] = combined
    if old_confirm_id:
        try:
            await context.bot.edit_message_reply_markup(
                update.effective_chat.id, old_confirm_id, reply_markup=None
            )
        except TelegramError:
            pass
    return await _send_confirmation(update, context)


async def confirm_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    draft = context.user_data.get(DRAFT) or {}

    if query.message is None or query.message.message_id != draft.get("confirm_message_id"):
        await query.answer(msg.STALE_BUTTON)
        return CONFIRM

    await query.answer()

    if query.data == kb.CB_APPEAL_CANCEL:
        return await _finish(update, context, msg.CANCELLED)

    if query.data == kb.CB_APPEAL_RESTART:
        await _discard_draft(update, context)
        await _reply_safely(update, context, msg.RESTARTED)
        return await start_appeal(update, context)

    if not (_has_contact_data(draft) and draft.get("text")):
        return await _finish(update, context, msg.SESSION_LOST)

    # Avval murojaatni ro'yxatga olamiz va adminga yetkazamiz; tugmalarni olib
    # tashlash kabi kosmetik amallar undan keyin va xatoga chidamli bajariladi.
    settings = get_settings(context)
    user = update.effective_user
    appeal = get_store(context).create(
        now=datetime.now(settings.timezone),
        user_id=user.id,
        username=user.username,
        full_name=draft["full_name"],
        phone=draft["phone"],
        phone_verified=bool(draft.get("phone_verified")),
        email=draft.get("email"),
        text=draft["text"],
        category=draft.get("category", ""),
    )
    _log_appeal(appeal, settings.timezone)
    await _notify_admin(context, appeal)

    # Tugma tez-tez ikki marta bosilsa, ikkinchisiga "allaqachon yuborilgan"
    # deb javob berish uchun (qarang: common.stale_callback).
    context.user_data[SUBMITTED] = {
        "message_id": query.message.message_id,
        "appeal_id": appeal.appeal_id,
    }
    return await _finish(update, context, msg.ACCEPTED.format(appeal_id=appeal.appeal_id))


# --- Chiqish yo'llari -------------------------------------------------------


async def _finish(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> int:
    await _discard_draft(update, context)
    await _reply_safely(update, context, text, reply_markup=kb.main_menu())
    return END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _finish(update, context, msg.CANCELLED)


async def cancel_from_inline_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """FAQ xabaridagi inline "Bosh menyu" tugmasi murojaat to'ldirilayotganda bosildi."""
    await update.callback_query.answer()
    return await _finish(update, context, msg.CANCELLED)


async def cancel_and_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _discard_draft(update, context)
    await common.start(update, context)
    return END


async def cancel_and_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _discard_draft(update, context)
    await update.effective_message.reply_text(msg.CANCELLED)
    await common.about(update, context)
    return END


async def cancel_and_faq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _discard_draft(update, context)
    await update.effective_message.reply_text(msg.CANCELLED, reply_markup=kb.main_menu())
    await common.faq(update, context)
    return END


async def reprompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Joriy qadamga mos kelmagan xabar: rasm, ovozli xabar, noma'lum buyruq,
    noto'g'ri tugma... Joriy savol (va uning klaviaturasi) qayta beriladi."""
    step = _draft(context).get("step", CATEGORY)
    message = update.effective_message
    if step == CONFIRM:
        await message.reply_text(msg.PRESS_BUTTON)
        return CONFIRM
    if not message.text:
        await message.reply_text(msg.ONLY_TEXT)
    return await _ask(update, context, step)


async def help_in_form(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """/help murojaat to'ldirilayotganda: yordam matni, so'ng joriy savol."""
    await update.effective_message.reply_text(msg.HELP)
    return await reprompt(update, context)


async def timed_out(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Bu handler hech qachon xato ko'tarmasligi kerak — aks holda PTB suhbatni
    # END holatiga o'tkazmay qoladi.
    await _discard_draft(update, context)
    chat = update.effective_chat
    if chat is None:
        return
    try:
        await context.bot.send_message(chat.id, msg.TIMEOUT, reply_markup=kb.main_menu())
    except TelegramError:
        logger.warning("Timeout xabarini yuborib bo'lmadi (chat %s)", chat.id, exc_info=True)


# --- Admin'ga yetkazish va log ---------------------------------------------


def _log_appeal(appeal: Appeal, tz: ZoneInfo) -> None:
    # Murojaat matni har bir qatori boshiga "    | " qo'yib yoziladi: foydalanuvchi
    # matni ichiga soxta "YANGI MUROJAAT ..." log qatorini joylashtira olmaydi.
    body = "\n".join(f"    | {line}" for line in appeal.text.splitlines())
    logger.info(
        "YANGI MUROJAAT %s | %s | soha=%s | ism=%r | tel=%s%s | email=%r | tg_id=%s | username=%s\n%s",
        appeal.appeal_id,
        msg.format_date(appeal.created_at, tz),
        appeal.category or "-",
        appeal.full_name,
        appeal.phone,
        " (tasdiqlangan)" if appeal.phone_verified else "",
        appeal.email or "-",
        appeal.user_id,
        appeal.username or "-",
        body,
    )


async def _notify_admin(context: ContextTypes.DEFAULT_TYPE, appeal: Appeal) -> None:
    admin_id = get_admin_chat_id(context)
    text = msg.ADMIN_NEW_APPEAL.format(
        body=msg.render_appeal(appeal, get_settings(context).timezone)
    )
    try:
        await context.bot.send_message(admin_id, text)
        return
    except ChatMigrated as exc:
        # Oddiy guruh superguruhga aylantirilganda uning ID'si o'zgaradi.
        new_id = exc.new_chat_id
        logger.error(
            "Admin guruhi superguruhga aylantirilgan: .env dagi ADMIN_CHAT_ID=%s ni %s "
            "ga almashtiring. Hozircha yangi ID ishlatiladi.",
            admin_id,
            new_id,
        )
        set_admin_chat_id(context, new_id)
        admin_id = new_id
    except TelegramError:
        # Murojaat baribir terminal log'ida va /admin ro'yxatida qoladi.
        logger.exception("Murojaat %s admin chatiga (%s) yuborilmadi", appeal.appeal_id, admin_id)
        return

    try:
        await context.bot.send_message(admin_id, text)
    except TelegramError:
        logger.exception("Murojaat %s admin chatiga (%s) yuborilmadi", appeal.appeal_id, admin_id)


# --- ConversationHandler ----------------------------------------------------


def build_conversation(timeout_seconds: int) -> ConversationHandler:
    # CallbackQueryHandler per_message=False rejimida ishlatilganda PTB
    # ogohlantirish chiqaradi; bizning holatda bu kutilgan xatti-harakat.
    warnings.filterwarnings("ignore", message=r".*per_message=False.*", category=PTBUserWarning)

    return ConversationHandler(
        entry_points=[
            MessageHandler(PRIVATE & filters.Text([msg.BTN_APPEAL]), start_appeal),
            CommandHandler("murojaat", start_appeal, filters=PRIVATE),
        ],
        states={
            CATEGORY: [MessageHandler(PRIVATE & filters.Text(msg.CATEGORIES), got_category)],
            NAME: [MessageHandler(USER_TEXT, got_name)],
            PHONE: [
                MessageHandler(PRIVATE & filters.CONTACT, got_contact),
                MessageHandler(USER_TEXT, got_phone_text),
            ],
            EMAIL: [
                MessageHandler(PRIVATE & filters.Text([msg.BTN_SKIP]), skipped_email),
                MessageHandler(USER_TEXT, got_email),
            ],
            TEXT: [MessageHandler(USER_TEXT, got_text)],
            CONFIRM: [
                CallbackQueryHandler(
                    confirm_action,
                    pattern=rf"^({kb.CB_APPEAL_SEND}|{kb.CB_APPEAL_RESTART}|{kb.CB_APPEAL_CANCEL})$",
                ),
                MessageHandler(USER_TEXT, appended_text),
            ],
            ConversationHandler.TIMEOUT: [TypeHandler(Update, timed_out)],
        },
        fallbacks=[
            CommandHandler(["cancel", "menu"], cancel, filters=PRIVATE),
            CommandHandler("start", cancel_and_start, filters=PRIVATE),
            CommandHandler("help", help_in_form, filters=PRIVATE),
            MessageHandler(PRIVATE & filters.Text([msg.BTN_CANCEL, msg.BTN_MENU]), cancel),
            MessageHandler(PRIVATE & filters.Text([msg.BTN_ABOUT]), cancel_and_about),
            MessageHandler(PRIVATE & filters.Text([msg.BTN_FAQ]), cancel_and_faq),
            CallbackQueryHandler(cancel_from_inline_menu, pattern=rf"^{kb.CB_MENU}$"),
            # Qolgan barcha xabarlar va noma'lum buyruqlar joriy savolni qayta
            # beradi. /admin bundan mustasno — u o'z handleriga o'tadi.
            MessageHandler(PRIVATE & ~_ADMIN_COMMAND, reprompt),
        ],
        allow_reentry=True,
        conversation_timeout=timeout_seconds,
        name="appeal",
    )
