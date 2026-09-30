# Yuridik klinika — murojaatlar boti

Fuqarolardan huquqiy murojaatlarni qabul qiluvchi o'zbekcha Telegram bot
(`python-telegram-bot` 22, long-polling).

## Imkoniyatlar

| Bo'lim | Nima qiladi |
|---|---|
| 📝 **Murojaat yuborish** | 4 qadam: ism → telefon («📱 Raqamni ulashish» tugmasi yoki qo'lda) → email (ixtiyoriy) → murojaat matni → tasdiqlash. Yuborilgach `APPEAL-2026-001` ko'rinishidagi raqam beriladi |
| ℹ️ **Biz haqimizda** | Manzil, ish vaqti, telefon, email |
| ❓ **Ko'p beriladigan savollar** | Inline tugmalar orqali savol-javoblar |
| 🏠 **Bosh menyu** | Bosh menyuga qaytish |
| `/admin` | Admin uchun: murojaatlar ro'yxati (sahifalab), har birini to'liq ko'rish |

Qo'shimcha:

- Har bir yangi murojaat darhol **admin chatiga** yuboriladi va **terminal log'iga** yoziladi.
- Bot faqat **matn** va **kontakt** qabul qiladi; rasm, ovozli xabar va h.k. rad etiladi.
- O'z kontaktini ulashgan foydalanuvchining raqami adminga «✅ Telegram orqali tasdiqlangan» deb ko'rsatiladi.
- Murojaat 30 daqiqa ichida to'ldirilmasa, avtomatik bekor qilinadi.
- Tasdiqlash tugmasi ikki marta bosilsa ham murojaat bir marta yuboriladi.

## Ma'lumotlar saqlanishi

- **Ma'lumotlar bazasi yo'q** (SQLite ham). Murojaatlar faqat operativ xotirada
  (RAM) turadi — `/admin` ro'yxati shu yerdan olinadi va **bot qayta ishga
  tushirilganda tozalanadi**. Doimiy nusxa — admin chatidagi xabarlar va log.
- Yagona fayl — `appeal_counter.json`: unda faqat yil va oxirgi tartib raqami
  bor (`{"year": 2026, "last": 17}`), shaxsiy ma'lumot yo'q. U bot qayta ishga
  tushganda raqamlar yana `001` dan boshlanib, admin chatida takrorlanmasligi
  uchun kerak. Uni o'chirish mumkin: `.env` da `COUNTER_FILE=` (bo'sh) yozing.

## Eng oson yo'l: Windows kompyuterda

1. [python.org/downloads](https://www.python.org/downloads/) dan Python'ni o'rnating.
   Birinchi oynada **"Add python.exe to PATH"** belgisini qo'ying.
2. Loyihani ZIP qilib yuklab oling va **"Extract All" (Hammasini chiqarish)** bilan oching.
3. Papkadagi **`start.bat`** faylini ikki marta bosing. Birinchi marta u token va
   admin ID'ni so'raydi, kutubxonalarni o'rnatadi va botni ishga tushiradi.
   Keyingi safar darhol ishga tushadi.

Oyna ochiq turguncha bot ishlaydi; oynani yopsangiz, bot to'xtaydi.

## O'rnatish va ishga tushirish (qo'lda, istalgan OS)

**1. Bot yaratish.** Telegram'da [@BotFather](https://t.me/BotFather) → `/newbot` → token oling.

**2. ADMIN_CHAT_ID ni aniqlash.**
- Shaxsiy chat uchun: [@userinfobot](https://t.me/userinfobot) ga yozing — u sizning ID'ingizni beradi.
- Guruh uchun: botni guruhga qo'shing, guruhga biror xabar yozing, so'ng brauzerda
  `https://api.telegram.org/bot<TOKEN>/getUpdates` ni oching va `"chat":{"id":-100...}` qiymatini oling.

> ⚠️ Admin shaxsiy chatda bo'lsa, admin **avval botga `/start` yozishi shart** —
> aks holda Telegram botga unga xabar yuborishga ruxsat bermaydi. Bot ishga
> tushganda buni tekshiradi va muammo bo'lsa log'da ogohlantiradi.

**3. O'rnatish** (Python 3.10+):

```bash
git clone <repo-url> legal-clinic-bot && cd legal-clinic-bot
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # so'ng .env ni tahrirlang
```

**4. Klinika ma'lumotlarini kiritish.** `messages.py` faylidagi `CLINIC_*`
qiymatlari (manzil, telefon, email, ish vaqti) va `FAQ` javoblari — **namuna**.
Ularni klinikangizning haqiqiy ma'lumotlari bilan almashtiring (ayniqsa
xizmatlar bepulligi va murojaatni ko'rib chiqish muddati haqidagi javoblarni).

**5. Ishga tushirish:**

```bash
python main.py
```

To'xtatish — `Ctrl+C`.

## Serverda doimiy ishlatish (systemd)

```bash
sudo useradd --system --home /opt/legal-clinic-bot botuser
sudo cp -r . /opt/legal-clinic-bot && sudo chown -R botuser /opt/legal-clinic-bot
sudo cp deploy/legal-clinic-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now legal-clinic-bot

journalctl -u legal-clinic-bot -f   # log (yangi murojaatlar shu yerda ham ko'rinadi)
```

Xizmat xatolikdan yoki server qayta yuklanganidan keyin avtomatik qayta ishga
tushadi. Bitta token bilan faqat **bitta** nusxa ishlashi kerak — aks holda
Telegram `Conflict: terminated by other getUpdates request` xatosini beradi.

## Loyiha tuzilishi

```
start.bat            — Windows uchun bir bosishda ishga tushirish
main.py              — kirish nuqtasi: Application, long-polling, bot buyruqlari
config.py            — .env dan sozlamalarni o'qish va tekshirish
messages.py          — barcha o'zbekcha matnlar, klinika ma'lumotlari, FAQ
keyboards.py         — reply va inline klaviaturalar
storage.py           — murojaatlarni xotirada ushlash, ID generatsiyasi
validators.py        — ism, telefon, email, matnni tekshirish
handlers/
  common.py          — /start, bosh menyu, "Biz haqimizda", FAQ
  appeal.py          — murojaat yuborish (ConversationHandler)
  admin.py           — /admin
  errors.py          — global xatolik handleri
  __init__.py        — handlerlarni ro'yxatdan o'tkazish (tartib muhim)
deploy/              — systemd xizmati
tests/               — testlar (soxta Telegram API ustida to'liq oqim)
```

## Testlar

```bash
pip install -r requirements-dev.txt
pytest
```

Testlar haqiqiy Telegram'ga ulanmaydi: bot soxta API ustida to'liq ishga
tushiriladi va foydalanuvchi harakatlari (tugma bosish, kontakt ulashish,
admin buyruqlari) simulyatsiya qilinadi.

## Xavfsizlik bo'yicha eslatmalar

- `.env` faylini hech qachon git'ga qo'shmang (`.gitignore` da bor). Token
  oshkor bo'lsa, @BotFather → `/revoke` orqali yangilang.
- Token log'ga tushmasligi uchun `httpx` kutubxonasining so'rov log'lari o'chirilgan.
- Terminal log'ida fuqarolarning shaxsiy ma'lumotlari bo'ladi — server log'lariga
  kirishni cheklang.
