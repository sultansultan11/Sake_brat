"""Storage, validators va config uchun unit-testlar."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

import config
from config import ConfigError, load_settings
from storage import AppealStore
from validators import check_text, clean_email, clean_name, normalize_phone

TZ = ZoneInfo("Asia/Tashkent")


def _create(store: AppealStore, when: datetime, name: str = "Ali"):
    return store.create(
        now=when,
        user_id=1,
        username=None,
        full_name=name,
        phone="+998901234567",
        phone_verified=False,
        email=None,
        text="x" * 30,
    )


# --- storage ----------------------------------------------------------------


def test_id_format_and_sequence():
    store = AppealStore()
    now = datetime(2026, 9, 30, tzinfo=TZ)
    assert _create(store, now).appeal_id == "APPEAL-2026-001"
    assert _create(store, now).appeal_id == "APPEAL-2026-002"


def test_counter_resets_on_new_year():
    store = AppealStore()
    _create(store, datetime(2026, 12, 31, 23, 59, tzinfo=TZ))
    assert _create(store, datetime(2027, 1, 1, tzinfo=TZ)).appeal_id == "APPEAL-2027-001"


def test_counter_survives_restart(tmp_path):
    counter = tmp_path / "sub" / "counter.json"
    now = datetime(2026, 5, 1, tzinfo=TZ)
    first = AppealStore(counter_file=counter)
    _create(first, now)
    _create(first, now)

    second = AppealStore(counter_file=counter)  # "qayta ishga tushirish"
    assert len(second) == 0  # murojaatlarning o'zi saqlanmaydi
    assert _create(second, now).appeal_id == "APPEAL-2026-003"
    assert "Ali" not in counter.read_text()  # faylda shaxsiy ma'lumot yo'q


def test_corrupt_counter_file_does_not_crash(tmp_path):
    counter = tmp_path / "counter.json"
    counter.write_text("{buzilgan")
    store = AppealStore(counter_file=counter)
    assert _create(store, datetime(2026, 1, 1, tzinfo=TZ)).appeal_id == "APPEAL-2026-001"


def test_memory_cap_drops_oldest():
    store = AppealStore(max_items=3)
    now = datetime(2026, 1, 1, tzinfo=TZ)
    ids = [_create(store, now).appeal_id for _ in range(5)]
    assert len(store) == 3
    assert store.get(ids[0]) is None and store.get(ids[-1]) is not None


def test_pagination_newest_first_and_clamped():
    store = AppealStore()
    now = datetime(2026, 1, 1, tzinfo=TZ)
    for _ in range(7):
        _create(store, now)
    items, page, pages = store.page(1, 5)
    assert (page, pages) == (1, 2)
    assert items[0].appeal_id == "APPEAL-2026-007"
    items, page, _ = store.page(99, 5)
    assert page == 2 and [a.appeal_id for a in items] == ["APPEAL-2026-002", "APPEAL-2026-001"]
    assert AppealStore().page(1, 5) == ([], 1, 1)


# --- validators ------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("+998 90 123-45-67", "+998901234567"),
        ("998901234567", "+998901234567"),
        ("901234567", "+998901234567"),
        ("(90) 123 45 67", "+998901234567"),
        ("00998901234567", "+998901234567"),
        ("+7 912 345 67 89", "+79123456789"),
        ("12345", None),
        ("+99890abc4567", None),
        ("", None),
        ("+", None),
    ],
)
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("  Aliyev   Vali ", "Aliyev Vali"),
        ("Oʻgʻiloy", "Oʻgʻiloy"),
        ("Ы", None),
        ("12345", None),
        ("A" * 101, None),
    ],
)
def test_clean_name(raw, expected):
    assert clean_name(raw) == expected


@pytest.mark.parametrize(
    "raw, ok",
    [("ali@mail.uz", True), (" ali@mail.uz ", True), ("ali@mail", False), ("a li@x.uz", False)],
)
def test_clean_email(raw, ok):
    assert (clean_email(raw) is not None) is ok


def test_check_text():
    assert check_text("qisqa") == (None, "short")
    assert check_text("x" * 3001) == (None, "long")
    assert check_text("  " + "x" * 25 + "  ") == ("x" * 25, None)


# --- config ------------------------------------------------------------------


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    for name in (
        "BOT_TOKEN",
        "ADMIN_CHAT_ID",
        "TIMEZONE",
        "COUNTER_FILE",
        "MAX_APPEALS_IN_MEMORY",
        "CONVERSATION_TIMEOUT",
    ):
        monkeypatch.delenv(name, raising=False)
    return tmp_path / "missing.env"


def test_config_requires_token(clean_env, monkeypatch):
    monkeypatch.setenv("ADMIN_CHAT_ID", "1")
    with pytest.raises(ConfigError, match="BOT_TOKEN"):
        load_settings(clean_env)


def test_config_rejects_bad_admin_id(clean_env, monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "t")
    monkeypatch.setenv("ADMIN_CHAT_ID", "@admin")
    with pytest.raises(ConfigError, match="ADMIN_CHAT_ID"):
        load_settings(clean_env)


def test_config_defaults(clean_env, monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "t")
    monkeypatch.setenv("ADMIN_CHAT_ID", "-1001234567890")
    settings = load_settings(clean_env)
    assert settings.admin_chat_id == -1001234567890
    assert settings.timezone.key == "Asia/Tashkent"
    assert settings.counter_file == config.BASE_DIR / "appeal_counter.json"
    assert settings.conversation_timeout == 1800


def test_config_counter_file_can_be_disabled(clean_env, monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "t")
    monkeypatch.setenv("ADMIN_CHAT_ID", "1")
    monkeypatch.setenv("COUNTER_FILE", "")
    assert load_settings(clean_env).counter_file is None
