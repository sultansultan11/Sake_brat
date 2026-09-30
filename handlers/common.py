"""Umumiy bo'limlar: /start, bosh menyu, "Biz haqimizda", FAQ, yordam."""

from __future__ import annotations

from html import escape

from telegram import Update
from telegram.ext import ContextTypes

import keyboards as kb
import messages as msg
from handlers.utils import remove_inline_keyboard, safe_edit

# handlers.appeal bilan kelishilgan kalit (aylanma importdan qochish uchun shu yerda).
SUBMITTED = "appeal_last_submitted"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    name = escape(user.first_name) if user and user.first_name else msg.DEFAULT_USER_NAME
    await update.effective_message.reply_text(
        msg.WELCOME.format(name=name, clinic=escape(msg.CLINIC_NAME)),
        reply_markup=kb.main_menu(),
    )


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(msg.MAIN_MENU, reply_markup=kb.main_menu())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(msg.HELP, reply_markup=kb.main_menu())


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(msg.ABOUT, reply_markup=kb.main_menu())


async def faq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(msg.FAQ_INTRO, reply_markup=kb.faq_list())


async def faq_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data or ""

    if data == kb.CB_FAQ_LIST:
        await query.answer()
        await safe_edit(query, msg.FAQ_INTRO, kb.faq_list())
        return

    raw_index = data.removeprefix(kb.CB_FAQ_ITEM)
    if not raw_index.isdecimal() or int(raw_index) >= len(msg.FAQ):
        await query.answer(msg.STALE_BUTTON)
        return

    await query.answer()
    question, answer = msg.FAQ[int(raw_index)]
    await safe_edit(query, f"❓ <b>{escape(question)}</b>\n\n{answer}", kb.faq_answer())


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    # Reply-klaviaturani faqat yangi xabar bilan ko'rsatish mumkin.
    await query.message.reply_text(msg.MAIN_MENU, reply_markup=kb.main_menu())


async def stale_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Hech bir handler qabul qilmagan (eskirgan) inline tugma bosilganda."""
    query = update.callback_query
    if not (query.data or "").startswith("appeal:"):
        await query.answer(msg.STALE_BUTTON)
        return

    # Murojaatni tasdiqlash tugmasi, lekin faol murojaat yo'q.
    submitted = context.user_data.get(SUBMITTED) if context.user_data is not None else None
    message_id = query.message.message_id if query.message is not None else None
    if submitted and submitted.get("message_id") == message_id:
        # Tugma ikki marta bosildi — murojaat allaqachon qabul qilingan.
        await query.answer(msg.ALREADY_SENT.format(appeal_id=submitted["appeal_id"]))
        return

    # Qoralama yo'qolgan (muddat tugagan yoki bot qayta ishga tushirilgan).
    await query.answer()
    await remove_inline_keyboard(query)
    await context.bot.send_message(
        update.effective_chat.id, msg.SESSION_LOST, reply_markup=kb.main_menu()
    )


# Murojaat qadamlariga tegishli tugmalar: suhbatdan tashqarida kelsa, demak
# qoralama yo'qolgan (masalan, bot qayta ishga tushirilgan).
_FORM_BUTTONS = {msg.BTN_SKIP, msg.BTN_SHARE_CONTACT}


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message.contact is not None or message.text in _FORM_BUTTONS:
        text = msg.SESSION_LOST
    elif message.text:
        text = msg.UNKNOWN
    else:
        text = msg.ONLY_TEXT
    await message.reply_text(text, reply_markup=kb.main_menu())
