"""Umumiy bo'limlar: /start, bosh menyu, "Biz haqimizda", FAQ, yordam."""

from __future__ import annotations

from html import escape

from telegram import Update
from telegram.ext import ContextTypes

import keyboards as kb
import messages as msg
from handlers.utils import safe_edit


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    name = escape(user.first_name) if user and user.first_name else "hurmatli foydalanuvchi"
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
    if not raw_index.isdigit() or int(raw_index) >= len(msg.FAQ):
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
    await update.callback_query.answer(msg.STALE_BUTTON)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    text = msg.UNKNOWN if message.text else msg.ONLY_TEXT
    await message.reply_text(text, reply_markup=kb.main_menu())
