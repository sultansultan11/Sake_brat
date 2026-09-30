"""Administrator bo'limi: /admin — xotiradagi murojaatlarni ko'rish."""

from __future__ import annotations

import logging
import re
from html import escape

from telegram import InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

import keyboards as kb
import messages as msg
from handlers import common
from handlers.utils import get_admin_chat_id, get_settings, get_store, safe_edit

logger = logging.getLogger(__name__)

PER_PAGE = 5

_APPEAL_ID_RE = re.compile(r"APPEAL-\d{4}-\d{3,}")
_TG_LINE_PREFIX = "💬 Telegram:"
_TG_ID_RE = re.compile(r"ID (\d+)\s*$")


def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """/admin faqat ADMIN_CHAT_ID chatining o'zida ishlaydi.

    ADMIN_CHAT_ID foydalanuvchi ID'si bo'lsa — shu admin bilan shaxsiy chatda,
    guruh ID'si bo'lsa — shu guruh ichida. Boshqa har qanday chatda (hatto admin
    o'zi yozsa ham) fuqarolarning ma'lumotlari ko'rsatilmaydi.
    """
    chat = update.effective_chat
    return chat is not None and chat.id == get_admin_chat_id(context)


def _render_page(
    context: ContextTypes.DEFAULT_TYPE, page: int
) -> tuple[str, InlineKeyboardMarkup | None]:
    store = get_store(context)
    if len(store) == 0:
        return msg.ADMIN_EMPTY, None

    tz = get_settings(context).timezone
    appeals, page, total_pages = store.page(page, PER_PAGE)
    first_number = (page - 1) * PER_PAGE + 1
    parts = [msg.ADMIN_LIST_HEADER.format(total=len(store), page=page, pages=total_pages)]
    for n, appeal in enumerate(appeals, start=first_number):
        parts.append(
            msg.ADMIN_LIST_ITEM.format(
                n=n,
                appeal_id=appeal.appeal_id,
                name=escape(appeal.full_name),
                date=msg.format_date(appeal.created_at, tz),
                phone=escape(appeal.phone),
                preview=msg.render_preview(appeal.text),
            )
        )
    parts.append(msg.ADMIN_LIST_FOOTER)
    return "".join(parts), kb.admin_list(appeals, page, total_pages)


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update, context):
        await update.effective_message.reply_text(msg.ADMIN_ONLY)
        return
    text, markup = _render_page(context, 1)
    await update.effective_message.reply_text(text, reply_markup=markup)


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not is_admin(update, context):
        await query.answer(msg.ADMIN_ONLY, show_alert=True)
        return

    data = query.data or ""

    if data.startswith(kb.CB_ADMIN_PAGE):
        raw_page = data.removeprefix(kb.CB_ADMIN_PAGE)
        page = int(raw_page) if raw_page.isdecimal() else 1
        await query.answer()
        text, markup = _render_page(context, page)
        await safe_edit(query, text, markup)
        return

    if data.startswith(kb.CB_ADMIN_VIEW):
        appeal_id, _, raw_page = data.removeprefix(kb.CB_ADMIN_VIEW).rpartition(":")
        appeal = get_store(context).get(appeal_id)
        if appeal is None:
            await query.answer(msg.ADMIN_NOT_FOUND, show_alert=True)
            return
        await query.answer()
        page = int(raw_page) if raw_page.isdecimal() else 1
        text = msg.render_appeal(appeal, get_settings(context).timezone)
        await safe_edit(query, text, kb.admin_back(page))
        return

    await query.answer(msg.STALE_BUTTON)


def _parse_appeal_card(text: str) -> tuple[str, int] | None:
    """Admin chatidagi murojaat kartasidan (murojaat ID, fuqaro Telegram ID) ni oladi.

    Faqat "💬 Telegram:" bilan boshlanadigan BIRINCHI qator ishlatiladi: u ism
    qatoridan keyin va murojaat matnidan oldin keladi, ism esa bir qatorli.
    Shu tufayli fuqaro o'z matniga soxta "ID ..." yozib, javobni boshqa odamga
    yo'naltira olmaydi.
    """
    appeal_match = _APPEAL_ID_RE.search(text)
    if appeal_match is None:
        return None
    for line in text.splitlines():
        if line.startswith(_TG_LINE_PREFIX):
            id_match = _TG_ID_RE.search(line)
            return (appeal_match.group(0), int(id_match.group(1))) if id_match else None
    return None


async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin murojaat xabariga "Reply" qilib yozgan javobni fuqaroga yetkazadi."""
    message = update.effective_message
    replied = message.reply_to_message
    is_reply_to_bot = (
        replied is not None and replied.from_user is not None
        and replied.from_user.id == context.bot.id
    )
    if not (is_admin(update, context) and is_reply_to_bot):
        # Admin'ning javobi emas: shaxsiy chatda odatdagidek javob beramiz,
        # guruhlardagi oddiy yozishmalarga aralashmaymiz.
        if update.effective_chat.type == "private":
            await common.unknown(update, context)
        return

    parsed = _parse_appeal_card(replied.text or "")
    if parsed is None:
        await message.reply_text(msg.REPLY_HOW_TO)
        return
    appeal_id, citizen_id = parsed

    try:
        await context.bot.send_message(
            citizen_id,
            msg.REPLY_TO_CITIZEN.format(
                clinic=escape(msg.CLINIC_NAME), appeal_id=appeal_id, text=escape(message.text)
            ),
        )
    except TelegramError:
        logger.warning("Javob %s fuqaroga (%s) yuborilmadi", appeal_id, citizen_id, exc_info=True)
        await message.reply_text(msg.REPLY_FAILED)
        return

    logger.info("Javob yuborildi: %s -> tg_id=%s", appeal_id, citizen_id)
    await message.reply_text(msg.REPLY_SENT.format(appeal_id=appeal_id))
