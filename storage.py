"""Murojaatlarni operativ xotirada (RAM) ushlab turish.

Ma'lumotlar bazasi ishlatilmaydi: murojaatlar faqat bot ishlab turgan vaqtda
xotirada bo'ladi va qayta ishga tushirilganda o'chib ketadi. Doimiy nusxa —
admin chatiga yuborilgan xabarlar va terminal log'i.

Yagona istisno — murojaat raqamlari hisoblagichi (masalan, {"year": 2026,
"last": 17}). U faylga yoziladi, aks holda bot qayta ishga tushganda raqamlar
yana APPEAL-2026-001 dan boshlanib, admin chatida takrorlanib qoladi.
Hisoblagichda hech qanday shaxsiy ma'lumot yo'q.
"""

from __future__ import annotations

import json
import logging
import math
import os
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Appeal:
    appeal_id: str
    created_at: datetime
    user_id: int
    username: str | None
    full_name: str
    phone: str
    phone_verified: bool
    email: str | None
    text: str


class AppealStore:
    def __init__(self, counter_file: Path | None = None, max_items: int = 500) -> None:
        self._appeals: OrderedDict[str, Appeal] = OrderedDict()
        self._max_items = max_items
        self._counter_file = counter_file
        self._year, self._last = self._load_counter()

    # --- Hisoblagich -----------------------------------------------------

    def _load_counter(self) -> tuple[int, int]:
        if self._counter_file is None or not self._counter_file.exists():
            return 0, 0
        try:
            data = json.loads(self._counter_file.read_text(encoding="utf-8"))
            return int(data["year"]), int(data["last"])
        except (OSError, ValueError, KeyError, TypeError):
            logger.exception(
                "Hisoblagich faylini o'qib bo'lmadi (%s), raqamlash noldan boshlanadi",
                self._counter_file,
            )
            return 0, 0

    def _save_counter(self) -> None:
        if self._counter_file is None:
            return
        tmp = self._counter_file.with_name(self._counter_file.name + ".tmp")
        try:
            self._counter_file.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(
                json.dumps({"year": self._year, "last": self._last}), encoding="utf-8"
            )
            os.replace(tmp, self._counter_file)
        except OSError:
            # Hisoblagichni yozolmaslik murojaatni qabul qilishga to'sqinlik
            # qilmasligi kerak — faqat log'ga yozamiz.
            logger.exception("Hisoblagich faylini yozib bo'lmadi: %s", self._counter_file)

    def _next_id(self, now: datetime) -> str:
        if now.year != self._year:
            self._year, self._last = now.year, 0
        self._last += 1
        self._save_counter()
        return f"APPEAL-{self._year}-{self._last:03d}"

    # --- Murojaatlar -----------------------------------------------------

    def create(
        self,
        *,
        now: datetime,
        user_id: int,
        username: str | None,
        full_name: str,
        phone: str,
        phone_verified: bool,
        email: str | None,
        text: str,
    ) -> Appeal:
        appeal = Appeal(
            appeal_id=self._next_id(now),
            created_at=now,
            user_id=user_id,
            username=username,
            full_name=full_name,
            phone=phone,
            phone_verified=phone_verified,
            email=email,
            text=text,
        )
        self._appeals[appeal.appeal_id] = appeal
        while len(self._appeals) > self._max_items:
            dropped_id, _ = self._appeals.popitem(last=False)
            logger.info("Xotira chegarasi: %s /admin ro'yxatidan chiqarildi", dropped_id)
        return appeal

    def get(self, appeal_id: str) -> Appeal | None:
        return self._appeals.get(appeal_id)

    def __len__(self) -> int:
        return len(self._appeals)

    def page(self, page: int, per_page: int) -> tuple[list[Appeal], int, int]:
        """Eng yangilari birinchi. (elementlar, joriy sahifa, sahifalar soni)."""
        newest_first = list(reversed(self._appeals.values()))
        total_pages = max(1, math.ceil(len(newest_first) / per_page))
        page = min(max(page, 1), total_pages)
        start = (page - 1) * per_page
        return newest_first[start : start + per_page], page, total_pages
