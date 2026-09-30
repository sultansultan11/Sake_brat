"""Reply va inline klaviaturalar."""

from __future__ import annotations

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

import messages as msg
from storage import Appeal

# Callback data prefikslari (Telegram cheklovi: 64 bayt).
CB_MENU = "menu"
CB_FAQ_LIST = "faq:list"
CB_FAQ_ITEM = "faq:"  # + savol indeksi
CB_APPEAL_SEND = "appeal:send"
CB_APPEAL_RESTART = "appeal:restart"
CB_APPEAL_CANCEL = "appeal:cancel"
CB_ADMIN_PAGE = "adm:page:"  # + sahifa
CB_ADMIN_VIEW = "adm:view:"  # + murojaat ID + ":" + sahifa


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [msg.BTN_APPEAL],
            [msg.BTN_ABOUT, msg.BTN_FAQ],
            [msg.BTN_MENU],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def cancel_only() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[msg.BTN_CANCEL]], resize_keyboard=True)


def share_contact() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(msg.BTN_SHARE_CONTACT, request_contact=True)],
            [msg.BTN_CANCEL],
        ],
        resize_keyboard=True,
    )


def skip_email() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[msg.BTN_SKIP], [msg.BTN_CANCEL]],
        resize_keyboard=True,
    )


def confirm_appeal() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(msg.BTN_SEND, callback_data=CB_APPEAL_SEND)],
            [
                InlineKeyboardButton(msg.BTN_RESTART, callback_data=CB_APPEAL_RESTART),
                InlineKeyboardButton(msg.BTN_CANCEL, callback_data=CB_APPEAL_CANCEL),
            ],
        ]
    )


def faq_list() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(question, callback_data=f"{CB_FAQ_ITEM}{i}")]
        for i, (question, _) in enumerate(msg.FAQ)
    ]
    rows.append([InlineKeyboardButton(msg.BTN_MENU, callback_data=CB_MENU)])
    return InlineKeyboardMarkup(rows)


def faq_answer() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(msg.BTN_FAQ_BACK, callback_data=CB_FAQ_LIST)],
            [InlineKeyboardButton(msg.BTN_MENU, callback_data=CB_MENU)],
        ]
    )


def admin_list(appeals: list[Appeal], page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                f"🔍 {a.appeal_id}",
                callback_data=f"{CB_ADMIN_VIEW}{a.appeal_id}:{page}",
            )
        ]
        for a in appeals
    ]
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(msg.BTN_PREV, callback_data=f"{CB_ADMIN_PAGE}{page - 1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(msg.BTN_NEXT, callback_data=f"{CB_ADMIN_PAGE}{page + 1}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(rows)


def admin_back(page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(msg.BTN_ADMIN_BACK, callback_data=f"{CB_ADMIN_PAGE}{page}")]]
    )
