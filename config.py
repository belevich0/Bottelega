"""
config.py — настройки бота
Заполни BOT_TOKEN и LASTFM_API_KEY перед запуском!
"""

import os

# ── Обязательно ──────────────────────────────────────────────────────────────
BOT_TOKEN      = os.getenv("BOT_TOKEN", "ВАШ_TELEGRAM_BOT_TOKEN")
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY", "ВАШ_LASTFM_API_KEY")

# ── Необязательно ────────────────────────────────────────────────────────────
# Страна для iTunes чартов (US, RU, GB, DE и т.д.)
ITUNES_COUNTRY = os.getenv("ITUNES_COUNTRY", "US")

# Страна для YouTube Music чартов
YTMUSIC_COUNTRY = os.getenv("YTMUSIC_COUNTRY", "US")
