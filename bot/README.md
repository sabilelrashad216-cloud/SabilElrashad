# تشغيل بوت سبيل الرشاد على Windows

هذا المجلد يشغّل البوت على اللاب بدل Sandbox. سيعمل البوت طالما Windows والإنترنت يعملان.

## التشغيل الأول

1. ثبّت Python 3.11 أو أحدث من: https://www.python.org/downloads/windows/ مع تفعيل **Add Python to PATH**.
2. ثبّت FFmpeg وأضف مجلد `bin` إلى PATH؛ الفيديو العمودي يحتاج `ffmpeg.exe`.
3. شغّل `setup_windows.bat`.
4. افتح ملف `.env` في Notepad وضع القيم السرية، ثم احفظه. لا ترفعه إلى GitHub.
5. شغّل `start_bot.bat`.

ملف `start_bot.bat` يعيد تشغيل البوت تلقائيًا بعد أي توقف. لإيقافه أغلق نافذة التشغيل أو اضغط Ctrl+C.

## التشغيل بعد إغلاق النافذة

ضع اختصارًا إلى `start_bot.bat` داخل مجلد Startup في Windows عبر:

```text
Win + R ثم اكتب: shell:startup
```

بعد ذلك سيبدأ البوت تلقائيًا عند تسجيل الدخول إلى Windows.

## أين تحفظ الأشياء؟

- الكود: GitHub.
- المحتوى: Airtable.
- التشغيل: اللاب.
- الأسرار: ملف `.env` على اللاب فقط.
- لا تشغّل نسخة Sandbox ونسخة اللاب في الوقت نفسه بنفس Telegram Bot Token.
