"""Yuridik klinika murojaatlari uchun Telegram bot — kirish nuqtasi.

Ishga tushirish:  python main.py
"""

from __future__ import annotations

import logging
import socket
import sys
from logging.handlers import RotatingFileHandler

from telegram import (
    BotCommand,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    LinkPreviewOptions,
    Update,
)
from telegram.constants import ParseMode
from telegram.error import ChatMigrated, TelegramError
from telegram.ext import Application, ApplicationBuilder, Defaults
from telegram.request import BaseRequest

import messages as msg
from config import BASE_DIR, ConfigError, Settings, load_settings
from handlers import register_handlers
from handlers.utils import ADMIN_CHAT_OVERRIDE
from storage import AppealStore

logger = logging.getLogger("bot")

USER_COMMANDS = [
    BotCommand("start", msg.CMD_START),
    BotCommand("murojaat", msg.CMD_APPEAL),
    BotCommand("cancel", msg.CMD_CANCEL),
    BotCommand("help", msg.CMD_HELP),
]
ADMIN_COMMANDS = [BotCommand("admin", msg.CMD_ADMIN)]


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
# Bir kompyuterda botning ikkinchi nusxasi ishga tushmasligi uchun band qilinadigan port.
SINGLE_INSTANCE_PORT = 47391


def setup_logging() -> None:
    if sys.stdout is not None:
        logging.basicConfig(format=LOG_FORMAT, level=logging.INFO, stream=sys.stdout)
    else:
        # Oynasiz rejim (pythonw.exe, start_hidden.vbs): terminal yo'q, shuning
        # uchun faqat ogohlantirish va xatolar bot.log fayliga yoziladi. Murojaat
        # matnlari (INFO) faylga yozilmaydi — ular admin chatida bor.
        handler = RotatingFileHandler(
            BASE_DIR / "bot.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8"
        )
        logging.basicConfig(format=LOG_FORMAT, level=logging.WARNING, handlers=[handler])
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

    admin_id = settings.admin_chat_id
    try:
        try:
            await bot.get_chat(admin_id)
        except ChatMigrated as exc:
            logger.error(
                "Admin guruhi superguruhga aylantirilgan: .env dagi ADMIN_CHAT_ID=%s ni %s "
                "ga almashtiring. Hozircha yangi ID ishlatiladi.",
                admin_id,
                exc.new_chat_id,
            )
            admin_id = exc.new_chat_id
            application.bot_data[ADMIN_CHAT_OVERRIDE] = admin_id
            await bot.get_chat(admin_id)
        await bot.set_my_commands(
            USER_COMMANDS + ADMIN_COMMANDS if admin_id > 0 else ADMIN_COMMANDS,
            scope=BotCommandScopeChat(admin_id),
        )
    except TelegramError as exc:
        logger.warning(
            "ADMIN_CHAT_ID=%s chatiga kirib bo'lmadi (%s). Admin avval botga /start "
            "yozishi yoki botni admin guruhiga qo'shishi kerak — aks holda yangi "
            "murojaatlar admin'ga yetib bormaydi.",
            admin_id,
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


def acquire_single_instance_lock() -> socket.socket | None:
    """Shu kompyuterda bot allaqachon ishlayotgan bo'lsa, None qaytaradi."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
    except OSError:
        sock.close()
        return None
    return sock


def main() -> None:
    setup_logging()
    lock = acquire_single_instance_lock()
    if lock is None:
        logger.error(
            "Bot shu kompyuterda allaqachon ishlab turibdi (masalan, fonda). "
            "Ikkinchi nusxa ishga tushirilmadi. To'xtatish uchun stop.bat ni bosing."
        )
        sys.exit(1)

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
