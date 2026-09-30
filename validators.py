"""Foydalanuvchi kiritgan ma'lumotlarni tekshirish va normallashtirish."""

from __future__ import annotations

import re

NAME_MIN, NAME_MAX = 2, 100
TEXT_MIN, TEXT_MAX = 20, 3000
EMAIL_MAX = 254

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
_PHONE_JUNK_RE = re.compile(r"[\s\-()]")


def clean_name(raw: str) -> str | None:
    name = " ".join(raw.split())
    if not NAME_MIN <= len(name) <= NAME_MAX:
        return None
    if not any(ch.isalpha() for ch in name):
        return None
    return name


def normalize_phone(raw: str) -> str | None:
    """Telefon raqamini +XXXXXXXXXXX ko'rinishiga keltiradi.

    9 xonali mahalliy raqamlar (masalan, 90 123 45 67) O'zbekiston kodi +998
    bilan to'ldiriladi.
    """
    phone = _PHONE_JUNK_RE.sub("", raw.strip())
    if phone.startswith("00"):
        phone = "+" + phone[2:]
    digits = phone[1:] if phone.startswith("+") else phone
    if not digits.isdigit():
        return None
    if len(digits) == 9 and not phone.startswith("+"):
        digits = "998" + digits
    if not 10 <= len(digits) <= 15:
        return None
    return "+" + digits


def clean_email(raw: str) -> str | None:
    email = raw.strip()
    if len(email) > EMAIL_MAX or not _EMAIL_RE.match(email):
        return None
    return email


def check_text(raw: str) -> tuple[str | None, str | None]:
    """(matn, xato turi) qaytaradi. Xato turi: 'short' yoki 'long'."""
    text = raw.strip()
    if len(text) < TEXT_MIN:
        return None, "short"
    if len(text) > TEXT_MAX:
        return None, "long"
    return text, None
