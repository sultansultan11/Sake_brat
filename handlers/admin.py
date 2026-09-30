"""Administrator bo'limi: /admin — xotiradagi murojaatlarni ko'rish."""

from __future__ import annotations

from html import escape

from telegram import InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import keyboards as kb
import messages as msg
from handlers.utils import get_settings, get_store, safe_edit

PER_PAGE = 5


def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """ADMIN_CHAT_ID — admin foydalanuvchi ID'si yoki admin guruh ID'si.

    Guruh ID'si berilgan bo'lsa, /admin shu guruh ichida ishlaydi.
    """
    admin_id = get_settings(context).admin_chat_id
    chat, user = update.effective_chat, update.effective_user
    return (chat is not None and chat.id == admin_id) or (user is not None and user.id == admin_id)


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
        page = int(raw_page) if raw_page.isdigit() else 1
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
        page = int(raw_page) if raw_page.isdigit() else 1
        text = msg.render_appeal(appeal, get_settings(context).timezone)
        await safe_edit(query, text, kb.admin_back(page))
        return

    await query.answer(msg.STALE_BUTTON)
