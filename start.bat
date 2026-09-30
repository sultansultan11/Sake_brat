@echo off
rem Yuridik klinika boti - Windows uchun ishga tushirish fayli.
rem Ikki marta bosing: birinchi marta token va admin ID ni so'raydi,
rem kerakli kutubxonalarni o'rnatadi va botni ishga tushiradi.

cd /d "%~dp0"
title Yuridik klinika boti

rem --- 1. Python bormi? ---
set "PY=python"
python --version >nul 2>&1
if not errorlevel 1 goto have_python
set "PY=py -3"
py -3 --version >nul 2>&1
if not errorlevel 1 goto have_python
echo.
echo [XATO] Python topilmadi.
echo https://www.python.org/downloads/ saytidan Python ni yuklab o'rnating.
echo O'rnatishning birinchi oynasida "Add python.exe to PATH" belgisini
echo albatta qo'ying, so'ng shu faylni qayta ishga tushiring.
echo.
pause
exit /b 1

:have_python

rem --- 2. Sozlamalar: .env fayli ---
if exist ".env" goto have_env
echo.
echo ===== Birinchi ishga tushirish: sozlamalar =====

:ask_token
echo.
echo BotFather bergan tokenni nusxalang, shu oynaga sichqonchaning
echo O'NG tugmasini bosib qo'ying va Enter bosing.
set "BOT_TOKEN="
set /p "BOT_TOKEN=Token: "
if not defined BOT_TOKEN goto ask_token

:ask_admin
echo.
echo @userinfobot bergan ID raqamingizni yozing va Enter bosing.
set "ADMIN_CHAT_ID="
set /p "ADMIN_CHAT_ID=ID: "
if not defined ADMIN_CHAT_ID goto ask_admin

> ".env" echo BOT_TOKEN=%BOT_TOKEN%
>> ".env" echo ADMIN_CHAT_ID=%ADMIN_CHAT_ID%
echo.
echo Sozlamalar .env fayliga saqlandi. Keyinchalik o'zgartirish kerak
echo bo'lsa, .env faylini o'chirib, shu faylni qayta ishga tushiring.

:have_env

rem --- 3. Kutubxonalar: faqat birinchi marta o'rnatiladi ---
if exist ".venv\installed.ok" goto run
echo.
echo Kerakli kutubxonalar o'rnatilmoqda, 1-3 daqiqa kuting...
%PY% -m venv .venv
if errorlevel 1 goto install_failed
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto install_failed
> ".venv\installed.ok" echo ok
goto run

:install_failed
echo.
echo [XATO] Kutubxonalarni o'rnatib bo'lmadi. Internet aloqasini tekshirib,
echo shu faylni qayta ishga tushiring.
echo.
pause
exit /b 1

:run
echo.
echo Bot ishga tushmoqda. To'xtatish uchun shu oynani yoping.
echo Oyna ochiq turguncha bot ishlaydi.
echo.
".venv\Scripts\python.exe" main.py
echo.
echo Bot to'xtadi. Yuqorida xato yozilgan bo'lsa, uni menga yuboring
echo (tokenni yubormang).
echo.
pause
