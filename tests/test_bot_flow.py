"""Botning to'liq ishlashini soxta Telegram API ustida tekshirish."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

import keyboards as kb
import messages as msg
from main import build_application
from tests.conftest import (
    ADMIN_ID,
    OTHER_USER_ID,
    USER_ID,
    FakeRequest,
    Harness,
    make_settings,
)

YEAR = datetime.now(ZoneInfo("Asia/Tashkent")).year
CATEGORY = msg.CATEGORIES[2]  # "Mehnat nizolari"
LONG_TEXT = "Ish beruvchi uch oydan beri ish haqimni toʻlamayapti, nima qilishim kerak?"


async def fill_until_confirm(bot: Harness, name="Aliyev Vali", email=msg.BTN_SKIP) -> int:
    await bot.text(msg.BTN_APPEAL)
    await bot.text(CATEGORY)
    await bot.text(name)
    await bot.contact("998901234567")
    await bot.text(email)
    await bot.text(LONG_TEXT)
    return bot.last_message_id()


async def test_start_shows_main_menu(bot: Harness):
    await bot.text("/start")
    sent = bot.req.sent(USER_ID)[-1]
    assert "xush kelibsiz" in sent["text"]
    keyboard_texts = [b["text"] for row in sent["reply_markup"]["keyboard"] for b in row]
    assert keyboard_texts == [msg.BTN_APPEAL, msg.BTN_ABOUT, msg.BTN_FAQ, msg.BTN_MENU]
    assert sent["parse_mode"] == "HTML"


async def test_full_appeal_flow(bot: Harness):
    await bot.text(msg.BTN_APPEAL)
    await bot.text(CATEGORY)
    assert bot.last_text() == msg.ASK_NAME

    await bot.text("Aliyev Vali")
    assert bot.last_text() == msg.ASK_PHONE
    contact_button = bot.req.sent(USER_ID)[-1]["reply_markup"]["keyboard"][0][0]
    assert contact_button["request_contact"] is True

    await bot.contact("998901234567")
    assert bot.last_text() == msg.ASK_EMAIL

    await bot.text("vali@example.com")
    assert bot.last_text() == msg.ASK_TEXT

    await bot.text(LONG_TEXT)
    confirm = bot.req.sent(USER_ID)[-1]
    assert "Maʼlumotlarni tekshiring" in confirm["text"]
    assert "+998901234567" in confirm["text"]
    assert "vali@example.com" in confirm["text"]

    await bot.press(kb.CB_APPEAL_SEND, confirm["_message_id"])

    appeal_id = f"APPEAL-{YEAR}-001"
    assert appeal_id in bot.last_text(USER_ID)
    assert "qabul qilindi" in bot.last_text(USER_ID)

    admin_text = bot.last_text(ADMIN_ID)
    assert appeal_id in admin_text
    assert "Aliyev Vali" in admin_text
    assert msg.PHONE_VERIFIED in admin_text
    assert "@ali" in admin_text
    assert LONG_TEXT in admin_text

    assert len(bot.store) == 1
    # Tasdiqlash xabaridagi tugmalar olib tashlangan.
    assert bot.req.of("editMessageReplyMarkup")


async def test_ids_are_sequential(bot: Harness):
    for expected in (1, 2, 3):
        confirm_id = await fill_until_confirm(bot)
        await bot.press(kb.CB_APPEAL_SEND, confirm_id)
        assert f"APPEAL-{YEAR}-{expected:03d}" in bot.last_text()


async def test_typed_phone_and_skipped_email(bot: Harness):
    await bot.text(msg.BTN_APPEAL)
    await bot.text(CATEGORY)
    await bot.text("Aliyev Vali")
    await bot.text("90 123-45-67")
    await bot.text(msg.BTN_SKIP)
    await bot.text(LONG_TEXT)
    await bot.press(kb.CB_APPEAL_SEND, bot.last_message_id())

    appeal = bot.store.page(1, 5)[0][0]
    assert appeal.phone == "+998901234567"
    assert appeal.phone_verified is False
    assert appeal.email is None
    assert msg.PHONE_TYPED in bot.last_text(ADMIN_ID)
    assert msg.EMAIL_NOT_GIVEN in bot.last_text(ADMIN_ID)


async def test_someone_elses_contact_is_not_verified(bot: Harness):
    await bot.text(msg.BTN_APPEAL)
    await bot.text(CATEGORY)
    await bot.text("Aliyev Vali")
    await bot.contact("+998 90 765 43 21", owner_id=OTHER_USER_ID)
    await bot.text(msg.BTN_SKIP)
    await bot.text(LONG_TEXT)
    await bot.press(kb.CB_APPEAL_SEND, bot.last_message_id())
    assert bot.store.page(1, 5)[0][0].phone_verified is False


async def test_validation_messages(bot: Harness):
    await bot.text(msg.BTN_APPEAL)
    await bot.text(CATEGORY)
    await bot.text("12")
    assert bot.last_text() == msg.BAD_NAME
    await bot.text("Aliyev Vali")

    await bot.text("salom")
    assert bot.last_text() == msg.BAD_PHONE
    await bot.text("+998901234567")

    await bot.text("notogri-email")
    assert bot.last_text() == msg.BAD_EMAIL
    await bot.text("a@b.uz")

    await bot.text("qisqa")
    assert bot.last_text() == msg.TEXT_TOO_SHORT
    await bot.text("x" * 3001)
    assert "juda uzun" in bot.last_text()
    await bot.text(LONG_TEXT)
    assert "Maʼlumotlarni tekshiring" in bot.last_text()


async def test_non_text_is_rejected_and_step_repeated(bot: Harness):
    await bot.text(msg.BTN_APPEAL)
    await bot.text(CATEGORY)
    await bot.photo()
    texts = bot.req.texts()
    assert texts[-2] == msg.ONLY_TEXT
    assert texts[-1] == msg.ASK_NAME

    await bot.text("Aliyev Vali")
    await bot.photo()
    assert bot.req.texts()[-2:] == [msg.ONLY_TEXT, msg.ASK_PHONE]


async def test_button_labels_are_not_accepted_as_data(bot: Harness):
    await bot.text(msg.BTN_APPEAL)
    await bot.text(CATEGORY)
    await bot.text(msg.BTN_SKIP)  # NAME qadamida "O'tkazib yuborish" — ism emas
    assert bot.last_text() == msg.ASK_NAME
    await bot.text("Aliyev Vali")
    assert bot.last_text() == msg.ASK_PHONE


async def test_cancel_button_ends_conversation(bot: Harness):
    await bot.text(msg.BTN_APPEAL)
    await bot.text(CATEGORY)
    await bot.text("Aliyev Vali")
    await bot.text(msg.BTN_CANCEL)
    assert bot.last_text() == msg.CANCELLED
    await bot.text("Karimov Anvar")  # endi ism sifatida qabul qilinmaydi
    assert bot.last_text() == msg.UNKNOWN


async def test_start_during_conversation_resets(bot: Harness):
    await bot.text(msg.BTN_APPEAL)
    await bot.text(CATEGORY)
    await bot.text("/start")
    assert "xush kelibsiz" in bot.last_text()
    await bot.text("Aliyev Vali")
    assert bot.last_text() == msg.UNKNOWN


async def test_help_during_conversation_keeps_state(bot: Harness):
    await bot.text(msg.BTN_APPEAL)
    await bot.text(CATEGORY)
    await bot.text("/help")
    assert bot.req.texts()[-2:] == [msg.HELP, msg.ASK_NAME]  # savol qayta beriladi
    await bot.text("Aliyev Vali")
    assert bot.last_text() == msg.ASK_PHONE


async def test_confirm_cancel_and_restart(bot: Harness):
    confirm_id = await fill_until_confirm(bot)
    await bot.press(kb.CB_APPEAL_RESTART, confirm_id)
    assert bot.last_text() == msg.ASK_CATEGORY

    confirm_id = await fill_until_confirm(bot)
    await bot.press(kb.CB_APPEAL_CANCEL, confirm_id)
    assert bot.last_text() == msg.CANCELLED
    assert len(bot.store) == 0


async def test_extra_message_in_confirm_step_is_appended(bot: Harness):
    old_confirm = await fill_until_confirm(bot)
    await bot.text("Qoʻshimcha: ish beruvchi yozma shartnoma bermagan.")
    new_card = bot.last_text()
    assert LONG_TEXT in new_card and "yozma shartnoma" in new_card
    new_confirm = bot.last_message_id()
    assert new_confirm != old_confirm

    await bot.press(kb.CB_APPEAL_SEND, old_confirm)  # eski karta endi ishlamaydi
    assert len(bot.store) == 0
    await bot.press(kb.CB_APPEAL_SEND, new_confirm)
    assert bot.store.page(1, 5)[0][0].text.endswith("yozma shartnoma bermagan.")


async def test_non_text_in_confirm_step_asks_to_press_button(bot: Harness):
    await fill_until_confirm(bot)
    await bot.photo()
    assert bot.last_text() == msg.PRESS_BUTTON


async def test_double_click_creates_single_appeal(bot: Harness):
    confirm_id = await fill_until_confirm(bot)
    await bot.press(kb.CB_APPEAL_SEND, confirm_id)
    await bot.press(kb.CB_APPEAL_SEND, confirm_id)
    assert len(bot.store) == 1
    assert bot.req.of("answerCallbackQuery")[-1].get("text") == msg.ALREADY_SENT.format(
        appeal_id=f"APPEAL-{YEAR}-001"
    )


async def test_old_confirmation_message_is_stale(bot: Harness):
    old_confirm = await fill_until_confirm(bot, name="Birinchi Ism")
    await bot.text(msg.BTN_CANCEL)
    new_confirm = await fill_until_confirm(bot, name="Ikkinchi Ism")

    await bot.press(kb.CB_APPEAL_SEND, old_confirm)
    assert len(bot.store) == 0
    assert bot.req.of("answerCallbackQuery")[-1].get("text") == msg.STALE_BUTTON

    await bot.press(kb.CB_APPEAL_SEND, new_confirm)
    assert bot.store.page(1, 5)[0][0].full_name == "Ikkinchi Ism"


async def test_user_input_is_html_escaped(bot: Harness):
    await fill_until_confirm(bot, name="<b>Ali</b> & Co")
    assert "&lt;b&gt;Ali&lt;/b&gt; &amp; Co" in bot.last_text()
    await bot.press(kb.CB_APPEAL_SEND, bot.last_message_id())
    assert "&lt;b&gt;Ali&lt;/b&gt; &amp; Co" in bot.last_text(ADMIN_ID)


async def test_about_and_faq(bot: Harness):
    await bot.text(msg.BTN_ABOUT)
    assert bot.last_text() == msg.ABOUT

    await bot.text(msg.BTN_FAQ)
    sent = bot.req.sent(USER_ID)[-1]
    assert sent["text"] == msg.FAQ_INTRO
    buttons = sent["reply_markup"]["inline_keyboard"]
    assert len(buttons) == len(msg.FAQ) + 1

    await bot.press("faq:1", sent["_message_id"])
    edited = bot.req.of("editMessageText")[-1]
    assert msg.FAQ[1][0] in edited["text"]

    await bot.press(kb.CB_FAQ_LIST, sent["_message_id"])
    assert bot.req.of("editMessageText")[-1]["text"] == msg.FAQ_INTRO

    await bot.press("faq:999", sent["_message_id"])
    assert bot.req.of("answerCallbackQuery")[-1].get("text") == msg.STALE_BUTTON

    await bot.press(kb.CB_MENU, sent["_message_id"])
    assert bot.last_text() == msg.MAIN_MENU


async def test_menu_button_and_unknown(bot: Harness):
    await bot.text(msg.BTN_MENU)
    assert bot.last_text() == msg.MAIN_MENU
    await bot.text("salom")
    assert bot.last_text() == msg.UNKNOWN
    await bot.photo()
    assert bot.last_text() == msg.ONLY_TEXT


async def test_admin_access_control(bot: Harness):
    await bot.text("/admin")
    assert bot.last_text() == msg.ADMIN_ONLY

    await bot.text("/admin", user_id=ADMIN_ID)
    assert bot.last_text(ADMIN_ID) == msg.ADMIN_EMPTY

    await bot.press(f"{kb.CB_ADMIN_PAGE}1", 1)
    answer = bot.req.of("answerCallbackQuery")[-1]
    assert answer.get("text") == msg.ADMIN_ONLY


async def test_admin_list_and_view(bot: Harness):
    for i in range(7):
        await bot.press(kb.CB_APPEAL_SEND, await fill_until_confirm(bot, name=f"Foydalanuvchi {i}"))

    await bot.text("/admin", user_id=ADMIN_ID)
    listing = bot.req.sent(ADMIN_ID)[-1]
    assert "jami 7 ta" in listing["text"]
    assert f"APPEAL-{YEAR}-007" in listing["text"]  # eng yangisi birinchi
    assert f"APPEAL-{YEAR}-002" not in listing["text"]  # 2-sahifada

    await bot.press(f"{kb.CB_ADMIN_PAGE}2", listing["_message_id"], user_id=ADMIN_ID)
    page2 = bot.req.of("editMessageText")[-1]["text"]
    assert f"APPEAL-{YEAR}-001" in page2 and "2/2-sahifa" in page2

    await bot.press(
        f"{kb.CB_ADMIN_VIEW}APPEAL-{YEAR}-001:2", listing["_message_id"], user_id=ADMIN_ID
    )
    card = bot.req.of("editMessageText")[-1]
    assert "Foydalanuvchi 0" in card["text"] and LONG_TEXT in card["text"]
    back = card["reply_markup"]["inline_keyboard"][0][0]["callback_data"]
    assert back == f"{kb.CB_ADMIN_PAGE}2"

    await bot.press(f"{kb.CB_ADMIN_VIEW}APPEAL-1999-001:1", listing["_message_id"], user_id=ADMIN_ID)
    assert bot.req.of("answerCallbackQuery")[-1].get("text") == msg.ADMIN_NOT_FOUND


async def test_admin_group_chat(tmp_path):
    group_id = -1001234567890
    request = FakeRequest()
    app = build_application(make_settings(tmp_path, admin_chat_id=group_id), request=request)
    async with app:
        await app.start()
        bot = Harness(app, request)
        await bot.press(kb.CB_APPEAL_SEND, await fill_until_confirm(bot))
        assert f"APPEAL-{YEAR}-001" in bot.last_text(group_id)

        await bot.text("/admin", user_id=OTHER_USER_ID, chat_id=group_id)
        assert "jami 1 ta" in bot.last_text(group_id)

        # Admin guruhidagi oddiy xabarlarga bot javob bermaydi.
        request.clear()
        await bot.text("salom hammaga", user_id=OTHER_USER_ID, chat_id=group_id)
        await bot.text(msg.BTN_APPEAL, user_id=OTHER_USER_ID, chat_id=group_id)
        assert request.sent() == []
        await app.stop()


async def test_admin_notification_failure_still_accepts(bot: Harness, monkeypatch):
    # sendMessage admin'ga ketayotganda Telegram xatosini qaytaramiz.
    async def do_request(url, method, request_data=None, **kwargs):
        api_method = url.rsplit("/", 1)[-1]
        params = request_data.parameters if request_data else {}
        if api_method == "sendMessage" and int(params["chat_id"]) == ADMIN_ID:
            return 400, json.dumps(
                {"ok": False, "error_code": 400, "description": "Bad Request: chat not found"}
            ).encode()
        return await FakeRequest.do_request(bot.req, url, method, request_data, **kwargs)

    monkeypatch.setattr(bot.req, "do_request", do_request)
    await bot.press(kb.CB_APPEAL_SEND, await fill_until_confirm(bot))
    assert f"APPEAL-{YEAR}-001" in bot.last_text()
    assert len(bot.store) == 1


async def test_conversation_timeout(tmp_path):
    request = FakeRequest()
    app = build_application(make_settings(tmp_path, conversation_timeout=1), request=request)
    async with app:
        await app.start()
        bot = Harness(app, request)
        await bot.text(msg.BTN_APPEAL)
        await bot.text(CATEGORY)
        await bot.text("Aliyev Vali")
        await asyncio.sleep(2.5)
        assert bot.last_text() == msg.TIMEOUT
        await bot.text("+998901234567")
        assert bot.last_text() == msg.UNKNOWN
        await app.stop()


@pytest.mark.parametrize("command", ["/murojaat", msg.BTN_APPEAL])
async def test_entry_points(bot: Harness, command):
    await bot.text(command)
    sent = bot.req.sent(USER_ID)[-1]
    assert sent["text"] == msg.ASK_CATEGORY
    buttons = [b["text"] for row in sent["reply_markup"]["keyboard"] for b in row]
    assert buttons == [*msg.CATEGORIES, msg.BTN_CANCEL]


async def test_category_must_be_chosen_from_buttons(bot: Harness):
    await bot.text(msg.BTN_APPEAL)
    await bot.text("Aliyev Vali")  # soha o'rniga ism yozildi
    assert bot.last_text() == msg.ASK_CATEGORY
    await bot.text(CATEGORY)
    assert bot.last_text() == msg.ASK_NAME
    await bot.text("Aliyev Vali")
    await bot.contact("998901234567")
    await bot.text(msg.BTN_SKIP)
    await bot.text(LONG_TEXT)
    assert CATEGORY in bot.last_text()
    await bot.press(kb.CB_APPEAL_SEND, bot.last_message_id())
    assert CATEGORY in bot.last_text(ADMIN_ID)
    assert bot.store.page(1, 5)[0][0].category == CATEGORY


async def test_rate_limit(tmp_path):
    request = FakeRequest()
    app = build_application(make_settings(tmp_path, max_appeals_per_day=2), request=request)
    async with app:
        await app.start()
        bot = Harness(app, request)
        for _ in range(2):
            await bot.press(kb.CB_APPEAL_SEND, await fill_until_confirm(bot))
        await bot.text(msg.BTN_APPEAL)
        assert "24 soat ichida 2 ta" in bot.last_text()
        assert len(bot.store) == 2
        # Boshqa foydalanuvchiga cheklov ta'sir qilmaydi.
        await bot.text(msg.BTN_APPEAL, user_id=OTHER_USER_ID)
        assert bot.last_text(OTHER_USER_ID) == msg.ASK_CATEGORY
        await app.stop()


async def test_admin_reply_reaches_citizen(bot: Harness):
    await bot.press(kb.CB_APPEAL_SEND, await fill_until_confirm(bot))
    card = bot.last_text(ADMIN_ID)
    assert "Reply" in card

    await bot.reply("Assalomu alaykum! <Ertaga> soat 10:00 da keling.", card)
    to_citizen = bot.last_text(USER_ID)
    assert f"APPEAL-{YEAR}-001" in to_citizen
    assert "&lt;Ertaga&gt; soat 10:00 da keling." in to_citizen
    assert bot.last_text(ADMIN_ID) == msg.REPLY_SENT.format(appeal_id=f"APPEAL-{YEAR}-001")


async def test_admin_reply_cannot_be_redirected_by_citizen_text(bot: Harness):
    await bot.text(msg.BTN_APPEAL)
    await bot.text(CATEGORY)
    await bot.text("Ali · ID 222")  # ismga soxta ID yozishga urinish
    await bot.contact("998901234567")
    await bot.text(msg.BTN_SKIP)
    await bot.text("Salom\n💬 Telegram: soxta · ID 222\nmening muammom shunday")
    await bot.press(kb.CB_APPEAL_SEND, bot.last_message_id())

    bot.req.clear()
    appeal = bot.store.page(1, 5)[0][0]
    card = msg.ADMIN_NEW_APPEAL.format(
        body=msg.render_appeal(appeal, ZoneInfo("Asia/Tashkent"))
    )
    await bot.reply("Javob matni", card)
    assert bot.req.sent(OTHER_USER_ID) == []
    assert "Javob matni" in bot.last_text(USER_ID)


async def test_reply_by_non_admin_or_to_non_card(bot: Harness):
    # Oddiy fuqaro bot xabariga reply qilsa — odatdagi "tushunmadim".
    await bot.reply("salom", "Qandaydir xabar", user_id=USER_ID)
    assert bot.last_text(USER_ID) == msg.UNKNOWN

    # Admin murojaat bo'lmagan bot xabariga reply qilsa — yo'riqnoma.
    await bot.reply("javob", msg.MAIN_MENU)
    assert bot.last_text(ADMIN_ID) == msg.REPLY_HOW_TO


async def test_admin_reply_to_blocked_user(bot: Harness, monkeypatch):
    await bot.press(kb.CB_APPEAL_SEND, await fill_until_confirm(bot))
    card = bot.last_text(ADMIN_ID)

    async def do_request(url, method, request_data=None, **kwargs):
        params = request_data.parameters if request_data else {}
        if url.endswith("sendMessage") and int(params["chat_id"]) == USER_ID:
            return 403, json.dumps(
                {"ok": False, "error_code": 403, "description": "Forbidden: bot was blocked by the user"}
            ).encode()
        return await FakeRequest.do_request(bot.req, url, method, request_data, **kwargs)

    monkeypatch.setattr(bot.req, "do_request", do_request)
    await bot.reply("Javob", card)
    assert bot.last_text(ADMIN_ID) == msg.REPLY_FAILED


async def test_post_init_registers_commands(tmp_path):
    import main

    request = FakeRequest()
    app = build_application(make_settings(tmp_path), request=request)
    async with app:
        await main.post_init(app)
    scopes = {
        p["scope"]["type"]: [c["command"] for c in p["commands"]]
        for p in request.of("setMyCommands")
    }
    assert scopes["all_private_chats"] == ["start", "murojaat", "cancel", "help"]
    assert scopes["chat"] == ["start", "murojaat", "cancel", "help", "admin"]


async def test_post_init_warns_when_admin_unreachable(tmp_path, caplog, monkeypatch):
    import main

    request = FakeRequest()
    original = request.do_request

    async def do_request(url, method, request_data=None, **kwargs):
        if url.endswith("getChat"):
            return 400, json.dumps(
                {"ok": False, "error_code": 400, "description": "Bad Request: chat not found"}
            ).encode()
        return await original(url, method, request_data, **kwargs)

    monkeypatch.setattr(request, "do_request", do_request)
    app = build_application(make_settings(tmp_path), request=request)
    async with app:
        await main.post_init(app)  # xato ko'tarmasligi kerak
    assert "chatiga kirib bo'lmadi" in caplog.text
