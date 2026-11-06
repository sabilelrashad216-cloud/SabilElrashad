@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python غير مثبت. نزّله من https://www.python.org/downloads/windows/ ثم أعد التشغيل.
  pause
  exit /b 1
)
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
echo تم تثبيت المكتبات. افتح ملف .env وضع المفاتيح ثم شغّل start_bot.bat
pause
