"""Barcha handlerlarni Application'ga ro'yxatdan o'tkazish.

Tartib muhim: ConversationHandler birinchi turadi, shunda murojaat
to'ldirilayotganda /start va menyu tugmalari suhbatni to'g'ri yakunlaydi.
"""

from __future__ import annotations

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

import keyboards as kb
import messages as msg
from handlers import admin, appeal, common, errors
from handlers.utils import PRIVATE


def register_handlers(application: Application, conversation_timeout: int) -> None:
    add = application.add_handler

    add(appeal.build_conversation(conversation_timeout))

    add(CommandHandler("start", common.start, filters=PRIVATE))
    add(CommandHandler("help", common.help_command, filters=PRIVATE))
    add(CommandHandler(["menu", "cancel"], common.show_menu, filters=PRIVATE))
    add(CommandHandler("admin", admin.admin_command, filters=filters.UpdateType.MESSAGE))

    add(MessageHandler(PRIVATE & filters.Text([msg.BTN_ABOUT]), common.about))
    add(MessageHandler(PRIVATE & filters.Text([msg.BTN_FAQ]), common.faq))
    add(MessageHandler(PRIVATE & filters.Text([msg.BTN_MENU, msg.BTN_CANCEL]), common.show_menu))

    add(CallbackQueryHandler(common.faq_callback, pattern=r"^faq:"))
    add(CallbackQueryHandler(common.menu_callback, pattern=rf"^{kb.CB_MENU}$"))
    add(CallbackQueryHandler(admin.admin_callback, pattern=r"^adm:"))
    add(CallbackQueryHandler(common.stale_callback))

    add(MessageHandler(PRIVATE, common.unknown))

    application.add_error_handler(errors.error_handler)
