# Sabil El Rashad Telegram Bot

Telegram workflow for uploading Quran, Hadith, and Q&A content to Airtable and publishing only after an explicit Telegram approval.

## Publishing safety

Every approved item is rendered into the fixed 1080x1350 Arabic card before Buffer is called. Raw text is never sent to Facebook or TikTok. The bot reports success only after Buffer returns a real post ID. YouTube is intentionally skipped for image-only cards because Shorts requires a video asset.

## Environment

Set `TELEGRAM_BOT_TOKEN`, `AIRTABLE_PAT`, `AIRTABLE_BASE_ID`, `BUFFER_API_KEY`, `BUFFER_FACEBOOK_CHANNEL_ID`, `BUFFER_TIKTOK_CHANNEL_ID`, and `BUFFER_YOUTUBE_CHANNEL_ID`. Never commit `.env` or tokens.

## Run

```bash
cd bot
PYTHONPATH=. python3 telegram_approval_bot.py
```
