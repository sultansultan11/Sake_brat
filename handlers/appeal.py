"""Murojaat yuborish jarayoni (ConversationHandler).

Qadamlar: ism → telefon → email (ixtiyoriy) → murojaat matni → tasdiqlash.
To'ldirilayotgan murojaat faqat context.user_data ichida (RAM) turadi.
"""

from __future__ import annotations

import logging
import warnings
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.error import TelegramError
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
from handlers.utils import PRIVATE, get_settings, get_store, remove_inline_keyboard
from storage import Appeal
from validators import check_text, clean_email, clean_name, normalize_phone

logger = logging.getLogger(__name__)

NAME, PHONE, EMAIL, TEXT, CONFIRM = range(5)
END = ConversationHandler.END

DRAFT = "appeal_draft"

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
    ]
)
USER_TEXT = PRIVATE & filters.TEXT & ~filters.COMMAND & ~_BUTTON_TEXTS

_PROMPTS = {
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


# --- Qadamlar ---------------------------------------------------------------


async def start_appeal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[DRAFT] = {}
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
    text, error = check_text(update.message.text)
    if error == "short":
        await update.message.reply_text(msg.TEXT_TOO_SHORT)
        return TEXT
    if error == "long":
        await update.message.reply_text(
            msg.TEXT_TOO_LONG.format(length=len(update.message.text.strip()))
        )
        return TEXT

    draft = _draft(context)
    draft["text"] = text
    draft["step"] = CONFIRM
    sent = await update.message.reply_text(
        msg.CONFIRM.format(
            name=escape(draft["full_name"]),
            phone=escape(draft["phone"]),
            email=escape(draft["email"]) if draft.get("email") else msg.EMAIL_NOT_GIVEN,
            text=escape(text),
        ),
        reply_markup=kb.confirm_appeal(),
    )
    # Faqat eng oxirgi tasdiqlash xabaridagi tugmalar ishlaydi.
    draft["confirm_message_id"] = sent.message_id
    return CONFIRM


async def confirm_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    draft = context.user_data.get(DRAFT) or {}

    if query.message is None or query.message.message_id != draft.get("confirm_message_id"):
        await query.answer(msg.STALE_BUTTON)
        return CONFIRM

    await query.answer()
    await remove_inline_keyboard(query)

    if query.data == kb.CB_APPEAL_CANCEL:
        return await _finish(update, context, msg.CANCELLED)

    if query.data == kb.CB_APPEAL_RESTART:
        await query.message.reply_text(msg.RESTARTED)
        return await start_appeal(update, context)

    if not all(draft.get(key) for key in ("full_name", "phone", "text")):
        return await _finish(update, context, msg.SESSION_LOST)

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
    )
    _log_appeal(appeal, settings.timezone)
    await _notify_admin(context, appeal)

    return await _finish(update, context, msg.ACCEPTED.format(appeal_id=appeal.appeal_id))


# --- Chiqish yo'llari -------------------------------------------------------


async def _finish(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> int:
    context.user_data.pop(DRAFT, None)
    await update.effective_message.reply_text(text, reply_markup=kb.main_menu())
    return END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _finish(update, context, msg.CANCELLED)


async def cancel_and_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop(DRAFT, None)
    await common.start(update, context)
    return END


async def cancel_and_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop(DRAFT, None)
    await update.effective_message.reply_text(msg.CANCELLED)
    await common.about(update, context)
    return END


async def cancel_and_faq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop(DRAFT, None)
    await update.effective_message.reply_text(msg.CANCELLED, reply_markup=kb.main_menu())
    await common.faq(update, context)
    return END


async def reprompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Joriy qadamga mos kelmagan xabar: rasm, ovozli xabar, noto'g'ri tugma..."""
    step = _draft(context).get("step", NAME)
    message = update.effective_message
    if step == CONFIRM:
        await message.reply_text(msg.PRESS_BUTTON)
        return CONFIRM
    if not message.text:
        await message.reply_text(msg.ONLY_TEXT)
    return await _ask(update, context, step)


async def timed_out(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data is not None:
        context.user_data.pop(DRAFT, None)
    chat = update.effective_chat
    if chat is not None:
        await context.bot.send_message(chat.id, msg.TIMEOUT, reply_markup=kb.main_menu())


# --- Admin'ga yetkazish va log ---------------------------------------------


def _log_appeal(appeal: Appeal, tz: ZoneInfo) -> None:
    logger.info(
        "YANGI MUROJAAT %s | %s | ism=%r | tel=%s%s | email=%s | tg_id=%s | username=%s\n%s",
        appeal.appeal_id,
        msg.format_date(appeal.created_at, tz),
        appeal.full_name,
        appeal.phone,
        " (tasdiqlangan)" if appeal.phone_verified else "",
        appeal.email or "-",
        appeal.user_id,
        appeal.username or "-",
        appeal.text,
    )


async def _notify_admin(context: ContextTypes.DEFAULT_TYPE, appeal: Appeal) -> None:
    settings = get_settings(context)
    try:
        await context.bot.send_message(
            settings.admin_chat_id,
            msg.ADMIN_NEW_APPEAL.format(body=msg.render_appeal(appeal, settings.timezone)),
        )
    except TelegramError:
        # Murojaat baribir terminal log'ida va /admin ro'yxatida qoladi.
        logger.exception(
            "Murojaat %s admin chatiga (%s) yuborilmadi", appeal.appeal_id, settings.admin_chat_id
        )


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
            ],
            ConversationHandler.TIMEOUT: [TypeHandler(Update, timed_out)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel, filters=PRIVATE),
            CommandHandler("start", cancel_and_start, filters=PRIVATE),
            MessageHandler(PRIVATE & filters.Text([msg.BTN_CANCEL, msg.BTN_MENU]), cancel),
            MessageHandler(PRIVATE & filters.Text([msg.BTN_ABOUT]), cancel_and_about),
            MessageHandler(PRIVATE & filters.Text([msg.BTN_FAQ]), cancel_and_faq),
            # Qolgan barcha xabarlar (buyruqlar bundan mustasno — /help, /admin
            # suhbatni buzmasdan o'z handlerlariga o'tadi).
            MessageHandler(PRIVATE & ~filters.COMMAND, reprompt),
        ],
        allow_reentry=True,
        conversation_timeout=timeout_seconds,
        name="appeal",
    )
