"""Global xatolik handleri: bot to'xtab qolmasligi uchun barcha xatolar log'ga yoziladi."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

import messages as msg

logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Update'ni qayta ishlashda xatolik: %r", update, exc_info=context.error)

    if isinstance(update, Update) and update.effective_chat is not None:
        try:
            await context.bot.send_message(update.effective_chat.id, msg.ERROR)
        except TelegramError:
            logger.warning("Foydalanuvchiga xatolik haqida xabar yuborib bo'lmadi")
