"""Test muhiti: haqiqiy Telegram API o'rniga soxta (fake) so'rov obyekti.

Bot Application to'liq yig'iladi va update'lar process_update() orqali
beriladi — handlerlar, ConversationHandler va filtrlar haqiqiy holatda
ishlaydi, faqat tarmoq so'rovlari yozib olinadi.
"""

from __future__ import annotations

import html
import itertools
import re
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from telegram import Update
from telegram.request import BaseRequest, RequestData


from config import Settings
from main import build_application

BOT_ID = 777
ADMIN_ID = 555000
USER_ID = 111
OTHER_USER_ID = 222


class FakeRequest(BaseRequest):
    """Bot API chaqiruvlarini yozib oladi va minimal to'g'ri javob qaytaradi."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._message_ids = itertools.count(1000)

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    @property
    def read_timeout(self) -> float | None:
        return None

    async def do_request(self, url, method, request_data: RequestData | None = None, **kwargs):
        api_method = url.rsplit("/", 1)[-1]
        params = request_data.parameters if request_data else {}
        result = self._result(api_method, params)
        if isinstance(result, dict) and "message_id" in result:
            params = {**params, "_message_id": result["message_id"]}
        self.calls.append((api_method, params))
        return 200, json.dumps({"ok": True, "result": result}).encode()

    def _result(self, api_method: str, params: dict[str, Any]) -> Any:
        if api_method == "getMe":
            return {"id": BOT_ID, "is_bot": True, "first_name": "Bot", "username": "clinic_bot"}
        if api_method in {"sendMessage", "editMessageText", "editMessageReplyMarkup"}:
            chat_id = int(params.get("chat_id", USER_ID))
            return {
                "message_id": params.get("message_id") or next(self._message_ids),
                "date": 0,
                "chat": {"id": chat_id, "type": "private" if chat_id > 0 else "supergroup"},
                "from": {"id": BOT_ID, "is_bot": True, "first_name": "Bot"},
                "text": params.get("text", ""),
            }
        if api_method == "getChat":
            return {"id": int(params["chat_id"]), "type": "private"}
        return True

    # --- Tekshiruv uchun yordamchilar --------------------------------------

    def sent(self, chat_id: int | None = None) -> list[dict[str, Any]]:
        return [
            p
            for m, p in self.calls
            if m == "sendMessage" and (chat_id is None or int(p["chat_id"]) == chat_id)
        ]

    def last_text(self, chat_id: int = USER_ID) -> str:
        return self.sent(chat_id)[-1]["text"]

    def texts(self, chat_id: int = USER_ID) -> list[str]:
        return [p["text"] for p in self.sent(chat_id)]

    def of(self, api_method: str) -> list[dict[str, Any]]:
        return [p for m, p in self.calls if m == api_method]

    def clear(self) -> None:
        self.calls.clear()


class Harness:
    """Foydalanuvchi harakatlarini simulyatsiya qiladi."""

    def __init__(self, app, request: FakeRequest) -> None:
        self.app = app
        self.req = request
        self._update_ids = itertools.count(1)
        self._msg_ids = itertools.count(1)

    @staticmethod
    def _user(user_id: int, username: str | None = "ali") -> dict:
        user = {"id": user_id, "is_bot": False, "first_name": "Ali"}
        if username:
            user["username"] = username
        return user

    @staticmethod
    def _chat(chat_id: int) -> dict:
        if chat_id > 0:
            return {"id": chat_id, "type": "private", "first_name": "Ali"}
        return {"id": chat_id, "type": "supergroup", "title": "Admin"}

    async def _process(self, data: dict) -> None:
        data["update_id"] = next(self._update_ids)
        await self.app.process_update(Update.de_json(data, self.app.bot))

    def _message(self, user_id: int, chat_id: int | None, **extra) -> dict:
        return {
            "message_id": next(self._msg_ids),
            "date": 0,
            "chat": self._chat(chat_id if chat_id is not None else user_id),
            "from": self._user(user_id),
            **extra,
        }

    async def text(self, text: str, user_id: int = USER_ID, chat_id: int | None = None) -> None:
        extra: dict[str, Any] = {"text": text}
        if text.startswith("/"):
            extra["entities"] = [
                {"type": "bot_command", "offset": 0, "length": len(text.split()[0])}
            ]
        await self._process({"message": self._message(user_id, chat_id, **extra)})

    async def reply(
        self, text: str, to_html: str, user_id: int = ADMIN_ID, chat_id: int | None = None,
        from_bot: bool = True,
    ) -> None:
        """Bot yuborgan xabarga (HTML matni `to_html`) "Reply" qilib yozish."""
        chat_id = chat_id if chat_id is not None else user_id
        sender = (
            {"id": BOT_ID, "is_bot": True, "first_name": "Bot"} if from_bot else self._user(user_id)
        )
        replied = {
            "message_id": 999,
            "date": 0,
            "chat": self._chat(chat_id),
            "from": sender,
            # Telegram reply_to_message.text da HTML teglarsiz oddiy matn qaytaradi.
            "text": html.unescape(re.sub(r"<[^>]+>", "", to_html)),
        }
        await self._process(
            {"message": self._message(user_id, chat_id, text=text, reply_to_message=replied)}
        )

    async def contact(self, phone: str, owner_id: int | None = USER_ID, user_id: int = USER_ID):
        contact = {"phone_number": phone, "first_name": "Ali"}
        if owner_id is not None:
            contact["user_id"] = owner_id
        await self._process({"message": self._message(user_id, None, contact=contact)})

    async def photo(self, user_id: int = USER_ID) -> None:
        photo = [{"file_id": "f", "file_unique_id": "u", "width": 1, "height": 1}]
        await self._process({"message": self._message(user_id, None, photo=photo)})

    async def press(
        self, data: str, message_id: int, user_id: int = USER_ID, chat_id: int | None = None
    ) -> None:
        chat_id = chat_id if chat_id is not None else user_id
        await self._process(
            {
                "callback_query": {
                    "id": str(next(self._update_ids)),
                    "from": self._user(user_id),
                    "chat_instance": "ci",
                    "data": data,
                    "message": {
                        "message_id": message_id,
                        "date": 0,
                        "chat": self._chat(chat_id),
                        "from": {"id": BOT_ID, "is_bot": True, "first_name": "Bot"},
                        "text": "...",
                    },
                }
            }
        )

    def last_text(self, chat_id: int = USER_ID) -> str:
        return self.req.last_text(chat_id)

    def last_message_id(self, chat_id: int = USER_ID) -> int:
        """Bot shu chatga yuborgan oxirgi xabarning message_id'si."""
        return self.req.sent(chat_id)[-1]["_message_id"]

    @property
    def store(self):
        return self.app.bot_data["store"]


def make_settings(tmp_path: Path, **overrides) -> Settings:
    values = dict(
        bot_token="123456:TEST-TOKEN",
        admin_chat_id=ADMIN_ID,
        timezone=ZoneInfo("Asia/Tashkent"),
        counter_file=tmp_path / "counter.json",
        max_appeals_in_memory=500,
        conversation_timeout=1800,
    )
    values.update(overrides)
    return Settings(**values)


@pytest_asyncio.fixture
async def bot(tmp_path):
    request = FakeRequest()
    app = build_application(make_settings(tmp_path), request=request)
    async with app:
        await app.start()
        yield Harness(app, request)
        await app.stop()


@pytest.fixture
def settings_factory(tmp_path):
    return lambda **kw: make_settings(tmp_path, **kw)
