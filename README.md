# Yuridik klinika — murojaatlar boti

Fuqarolardan huquqiy murojaatlarni qabul qiluvchi o'zbekcha Telegram bot
(`python-telegram-bot` 22, long-polling).

## Imkoniyatlar

| Bo'lim | Nima qiladi |
|---|---|
| 📝 **Murojaat yuborish** | 5 qadam: huquq sohasi → ism → telefon («📱 Raqamni ulashish» tugmasi yoki qo'lda) → email (ixtiyoriy) → murojaat matni → tasdiqlash (shaxsga doir ma'lumotlarga rozilik bilan). Yuborilgach `APPEAL-2026-001` ko'rinishidagi raqam beriladi |
| ℹ️ **Biz haqimizda** | Manzil, ish vaqti, telefon, email |
| ❓ **Ko'p beriladigan savollar** | Inline tugmalar orqali savol-javoblar |
| 🏠 **Bosh menyu** | Bosh menyuga qaytish |
| `/admin` | Admin uchun: murojaatlar ro'yxati (sahifalab), har birini to'liq ko'rish |
| ↩️ **Javob** | Admin murojaat xabariga «Reply» qilib yozsa, javob fuqaroga yetkaziladi |

Qo'shimcha:

- Har bir yangi murojaat darhol **admin chatiga** yuboriladi va **terminal log'iga** yoziladi.
- Bot faqat **matn** va **kontakt** qabul qiladi; rasm, ovozli xabar va h.k. rad etiladi.
- O'z kontaktini ulashgan foydalanuvchining raqami adminga «✅ Telegram orqali tasdiqlangan» deb ko'rsatiladi.
- Murojaat 30 daqiqa ichida to'ldirilmasa, avtomatik bekor qilinadi.
- Tasdiqlash tugmasi ikki marta bosilsa ham murojaat bir marta yuboriladi.
- Fuqaro matnni bir nechta xabarda yozsa, ular bitta murojaatga qo'shiladi.
- Spamdan himoya: bir foydalanuvchi 24 soatda ko'pi bilan 3 ta murojaat yuboradi
  (`MAX_APPEALS_PER_DAY`).
- Jinoyat ishlari klinika vakolatiga kirmasligi murojaat boshida ogohlantiriladi.

## Fuqaroga javob berish

Admin chatiga kelgan **📥 Yangi murojaat** xabarini bosing, **«Ответить / Reply»**
ni tanlang va javobni yozing. Bot uni murojaat raqami bilan fuqaroga yuboradi
va «✅ Javob fuqaroga yuborildi» deb tasdiqlaydi. Bir murojaatga bir necha marta
javob yozish mumkin. `/admin` ro'yxatidan ochilgan murojaat kartasiga ham
shunday javob berish mumkin.

Fuqaro botni bloklagan bo'lsa, bot buni aytadi. Unda murojaatdagi telefon yoki
email orqali bog'laning.

## Ma'lumotlar saqlanishi

- **Ma'lumotlar bazasi yo'q** (SQLite ham). Murojaatlar faqat operativ xotirada
  (RAM) turadi — `/admin` ro'yxati shu yerdan olinadi va **bot qayta ishga
  tushirilganda tozalanadi**. Doimiy nusxa — admin chatidagi xabarlar va log.
- Yagona fayl — `appeal_counter.json`: unda faqat yil va oxirgi tartib raqami
  bor (`{"year": 2026, "last": 17}`), shaxsiy ma'lumot yo'q. U bot qayta ishga
  tushganda raqamlar yana `001` dan boshlanib, admin chatida takrorlanmasligi
  uchun kerak. Uni o'chirish mumkin: `.env` da `COUNTER_FILE=` (bo'sh) yozing.

## Eng oson yo'l: Windows kompyuterda

1. [@BotFather](https://t.me/BotFather) → `/newbot` orqali token oling.
2. [@userinfobot](https://t.me/userinfobot) dan o'z ID'ingizni oling va yangi
   botingizga **`/start`** yozing (aks holda bot sizga murojaatlarni yubora olmaydi).
3. Python o'rnating: **Win + R** → `python` → Enter → Microsoft Store'da «Получить».
   (Yoki [python.org](https://www.python.org/downloads/) — **"Add python.exe to PATH"** belgisi bilan.)
4. Loyihani ZIP qilib yuklab oling va **"Извлечь все / Extract All"** bilan oching.
5. Klinika ma'lumotlari `messages.py` dagi `CLINIC_*` qatorlarida — kerak bo'lsa,
   Bloknot (Notepad) bilan o'zgartiring.
6. Papkadagi **`start.bat`** faylini ikki marta bosing. Birinchi marta u token va
   admin ID'ni so'raydi, kutubxonalarni o'rnatadi va botni ishga tushiradi.
   Keyingi safar darhol ishga tushadi.

**Yangilash:** botni yoping, yangi ZIP'ni oching, eski papkadan `.env` va
`appeal_counter.json` fayllarini yangi papkaga ko'chiring va `start.bat` ni bosing.

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
cp .env.example .env && chmod 600 .env   # so'ng .env ni tahrirlang
```

**4. Klinika ma'lumotlari.** `messages.py` faylidagi `CLINIC_*` qiymatlari
(manzil, telefon, email, ish vaqti) va `FAQ` javoblarini kerak bo'lsa tahrirlang.
Matnlar HTML formatida: `<`, `>` va `&` belgilarini `&lt;`, `&gt;`, `&amp;` deb yozing.

**5. Ishga tushirish:**

```bash
python main.py
```

To'xtatish — `Ctrl+C`.

## Serverda doimiy ishlatish (systemd)

Birinchi o'rnatish (loyiha papkasida turib):

```bash
sudo useradd --system --home /opt/legal-clinic-bot botuser
# .venv va hisoblagichni ko'chirmaymiz: venv serverning o'zida yaratiladi
sudo rsync -a --exclude .venv --exclude appeal_counter.json ./ /opt/legal-clinic-bot/
sudo chown -R botuser: /opt/legal-clinic-bot
sudo chmod 700 /opt/legal-clinic-bot && sudo chmod 600 /opt/legal-clinic-bot/.env
sudo -u botuser python3 -m venv /opt/legal-clinic-bot/.venv
sudo -u botuser /opt/legal-clinic-bot/.venv/bin/pip install -r /opt/legal-clinic-bot/requirements.txt
sudo cp deploy/legal-clinic-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now legal-clinic-bot

journalctl -u legal-clinic-bot -f   # log (yangi murojaatlar shu yerda ham ko'rinadi)
```

Yangilash (`.env` va `appeal_counter.json` saqlanib qoladi):

```bash
sudo rsync -a --exclude .venv --exclude .env --exclude appeal_counter.json ./ /opt/legal-clinic-bot/
sudo chown -R botuser: /opt/legal-clinic-bot
sudo -u botuser /opt/legal-clinic-bot/.venv/bin/pip install -r /opt/legal-clinic-bot/requirements.txt
sudo systemctl restart legal-clinic-bot
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
  admin.py           — /admin va fuqaroga javob (Reply)
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
- Serverda `.env` faqat bot foydalanuvchisiga o'qiladigan bo'lsin (`chmod 600`).
- Admin chati guruh bo'lsa, u yopiq (faqat taklif bilan) bo'lishi kerak: guruhning
  har bir a'zosi barcha murojaatlarni ko'radi.
- Oddiy guruh superguruhga aylantirilsa, uning ID'si o'zgaradi. Bot buni sezib,
  vaqtincha yangi ID'ni ishlatadi va log'da `.env` ni yangilashni so'raydi.
- Token log'ga tushmasligi uchun `httpx` kutubxonasining so'rov log'lari o'chirilgan.
- Terminal log'ida fuqarolarning shaxsiy ma'lumotlari bo'ladi — server log'lariga
  kirishni cheklang.
