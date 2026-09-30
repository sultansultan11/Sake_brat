"""Yuridik klinika murojaatlari uchun Telegram bot — kirish nuqtasi.

Ishga tushirish:  python main.py
"""

from __future__ import annotations

import logging
import sys

from telegram import (
    BotCommand,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    LinkPreviewOptions,
    Update,
)
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import Application, ApplicationBuilder, Defaults
from telegram.request import BaseRequest

from config import ConfigError, Settings, load_settings
from handlers import register_handlers
from storage import AppealStore

logger = logging.getLogger("bot")

USER_COMMANDS = [
    BotCommand("start", "Botni ishga tushirish"),
    BotCommand("murojaat", "Yangi murojaat yuborish"),
    BotCommand("cancel", "Murojaatni bekor qilish"),
    BotCommand("help", "Yordam"),
]
ADMIN_COMMANDS = [BotCommand("admin", "Murojaatlar roʻyxati")]


def setup_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        level=logging.INFO,
        stream=sys.stdout,
    )
    # httpx har bir so'rov URL'ini (ichida BOT_TOKEN bor) INFO darajasida
    # yozadi — token log'ga tushmasligi uchun o'chiramiz.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


async def post_init(application: Application) -> None:
    settings: Settings = application.bot_data["settings"]
    bot = application.bot
    me = await bot.get_me()
    logger.info("Bot ishga tushdi: @%s (id=%s)", me.username, me.id)

    await bot.set_my_commands(USER_COMMANDS, scope=BotCommandScopeAllPrivateChats())
    try:
        await bot.get_chat(settings.admin_chat_id)
        await bot.set_my_commands(
            USER_COMMANDS + ADMIN_COMMANDS
            if settings.admin_chat_id > 0
            else ADMIN_COMMANDS,
            scope=BotCommandScopeChat(settings.admin_chat_id),
        )
    except TelegramError as exc:
        logger.warning(
            "ADMIN_CHAT_ID=%s chatiga kirib bo'lmadi (%s). Admin avval botga /start "
            "yozishi yoki botni admin guruhiga qo'shishi kerak — aks holda yangi "
            "murojaatlar admin'ga yetib bormaydi.",
            settings.admin_chat_id,
            exc,
        )


def build_application(settings: Settings, request: BaseRequest | None = None) -> Application:
    """Application'ni yig'adi. `request` — faqat testlar uchun (soxta Telegram API)."""
    builder = ApplicationBuilder().token(settings.bot_token)
    if request is not None:
        builder = builder.request(request).get_updates_request(request)
    application = (
        builder
        .defaults(
            Defaults(
                parse_mode=ParseMode.HTML,
                link_preview_options=LinkPreviewOptions(is_disabled=True),
            )
        )
        .post_init(post_init)
        .build()
    )
    application.bot_data["settings"] = settings
    application.bot_data["store"] = AppealStore(
        counter_file=settings.counter_file,
        max_items=settings.max_appeals_in_memory,
    )
    register_handlers(application, settings.conversation_timeout)
    return application


def main() -> None:
    setup_logging()
    try:
        settings = load_settings()
    except ConfigError as exc:
        logger.error("Sozlamalar xatosi: %s", exc)
        sys.exit(1)

    application = build_application(settings)
    logger.info("Long-polling boshlanmoqda. To'xtatish uchun Ctrl+C.")
    # Faqat kerakli update turlarini olamiz (tahrirlangan xabarlar va h.k. kelmaydi).
    application.run_polling(allowed_updates=[Update.MESSAGE, Update.CALLBACK_QUERY])


if __name__ == "__main__":
    main()
