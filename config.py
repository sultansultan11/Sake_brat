"""Bot sozlamalari.

Barcha qiymatlar muhit o'zgaruvchilaridan (yoki loyiha ildizidagi .env faylidan)
o'qiladi. Majburiy o'zgaruvchilar: BOT_TOKEN va ADMIN_CHAT_ID.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent


class ConfigError(RuntimeError):
    """Sozlamalar noto'g'ri yoki to'liq emas."""


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_chat_id: int
    timezone: ZoneInfo
    # Murojaat raqamlari hisoblagichi saqlanadigan fayl (faqat oxirgi tartib
    # raqami, shaxsiy ma'lumot yo'q). None bo'lsa, hisoblagich faqat xotirada.
    counter_file: Path | None
    # Xotirada saqlanadigan murojaatlarning eng ko'p soni (/admin uchun).
    max_appeals_in_memory: int
    # Murojaat to'ldirilmay qolsa, necha soniyadan keyin bekor qilinadi.
    conversation_timeout: int
    # Bir foydalanuvchi 24 soatda yuborishi mumkin bo'lgan murojaatlar soni.
    max_appeals_per_day: int = 3


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(
            f"{name} o'zgaruvchisi topilmadi. .env.example faylidan nusxa olib, "
            f".env faylini to'ldiring."
        )
    return value


def _int(name: str, default: int, minimum: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} butun son bo'lishi kerak, berilgan: {raw!r}") from exc
    if value < minimum:
        raise ConfigError(f"{name} kamida {minimum} bo'lishi kerak, berilgan: {value}")
    return value


def load_settings(env_file: Path | None = None) -> Settings:
    """.env faylini yuklab, sozlamalarni tekshiradi va qaytaradi."""
    load_dotenv(env_file or BASE_DIR / ".env")

    token = _require("BOT_TOKEN")

    admin_raw = _require("ADMIN_CHAT_ID")
    try:
        admin_chat_id = int(admin_raw)
    except ValueError as exc:
        raise ConfigError(
            f"ADMIN_CHAT_ID butun son bo'lishi kerak (masalan 123456789 yoki "
            f"-1001234567890), berilgan: {admin_raw!r}"
        ) from exc

    tz_name = os.getenv("TIMEZONE", "").strip() or "Asia/Tashkent"
    try:
        timezone = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ConfigError(f"TIMEZONE noto'g'ri: {tz_name!r}") from exc

    # COUNTER_FILE umuman berilmasa — standart fayl; bo'sh qiymat berilsa —
    # hisoblagich faylga yozilmaydi.
    counter_raw = os.getenv("COUNTER_FILE")
    if counter_raw is None:
        counter_file: Path | None = BASE_DIR / "appeal_counter.json"
    elif counter_raw.strip():
        counter_file = Path(counter_raw.strip())
        if not counter_file.is_absolute():
            counter_file = BASE_DIR / counter_file
    else:
        counter_file = None

    return Settings(
        bot_token=token,
        admin_chat_id=admin_chat_id,
        timezone=timezone,
        counter_file=counter_file,
        max_appeals_in_memory=_int("MAX_APPEALS_IN_MEMORY", 500, 1),
        conversation_timeout=_int("CONVERSATION_TIMEOUT", 1800, 60),
        max_appeals_per_day=_int("MAX_APPEALS_PER_DAY", 3, 1),
    )
