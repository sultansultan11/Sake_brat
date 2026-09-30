"""Handlerlar uchun umumiy yordamchi funksiyalar."""

from __future__ import annotations

from telegram import CallbackQuery, InlineKeyboardMarkup
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes, filters

from config import Settings
from storage import AppealStore

# Faqat shaxsiy chatdagi yangi (tahrirlanmagan) xabarlar.
PRIVATE = filters.ChatType.PRIVATE & filters.UpdateType.MESSAGE


def get_settings(context: ContextTypes.DEFAULT_TYPE) -> Settings:
    return context.bot_data["settings"]


def get_store(context: ContextTypes.DEFAULT_TYPE) -> AppealStore:
    return context.bot_data["store"]


ADMIN_CHAT_OVERRIDE = "admin_chat_id_override"


def get_admin_chat_id(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Amaldagi admin chat ID'si.

    Admin guruhi superguruhga aylantirilsa, Telegram unga yangi ID beradi; bot
    buni sezganda yangi ID'ni xotirada eslab qoladi (qayta ishga tushguncha).
    """
    return context.bot_data.get(ADMIN_CHAT_OVERRIDE) or get_settings(context).admin_chat_id


def set_admin_chat_id(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    context.bot_data[ADMIN_CHAT_OVERRIDE] = chat_id


async def safe_edit(
    query: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup | None = None
) -> None:
    """Xabarni tahrirlaydi; tugma ikki marta bosilganda chiqadigan
    "Message is not modified" xatosini e'tiborsiz qoldiradi."""
    try:
        await query.edit_message_text(text, reply_markup=reply_markup)
    except BadRequest as exc:
        if "not modified" not in str(exc).lower():
            raise


async def remove_inline_keyboard(query: CallbackQuery) -> None:
    """Xabardagi inline tugmalarni olib tashlaydi (xatoga chidamli, kosmetik amal)."""
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except TelegramError:
        pass
