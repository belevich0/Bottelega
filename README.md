# 🎵 MusicBot — Telegram бот для актуальных плейлистов

Агрегирует чарты из **4 источников** и выдаёт свежий плейлист каждый день.

## 📡 Источники

|Источник                |Что даёт                                |
|------------------------|----------------------------------------|
|**Last.fm**             |Реальные прослушивания по тегам и жанрам|
|**iTunes / Apple Music**|Официальные чарты по жанрам и странам   |
|**Deezer**              |Европейские и мировые ежедневные чарты  |
|**YouTube Music**       |Тренды и поиск через `ytmusicapi`       |

-----

## 🚀 Быстрый старт

### 1. Получи API ключи

**Telegram Bot Token:**

1. Открой [@BotFather](https://t.me/BotFather) в Telegram
1. `/newbot` → введи имя → скопируй токен

**Last.fm API Key (бесплатно):**

1. Регистрация: <https://www.last.fm/api/account/create>
1. Скопируй `API key`

### 2. Установи зависимости

```bash
pip install -r requirements.txt
```

### 3. Задай переменные окружения

**Linux / macOS:**

```bash
export BOT_TOKEN="твой_telegram_token"
export LASTFM_API_KEY="твой_lastfm_key"
```

**Windows (cmd):**

```cmd
set BOT_TOKEN=твой_telegram_token
set LASTFM_API_KEY=твой_lastfm_key
```

**Или через `.env` файл** (создай рядом с `bot.py`):

```
BOT_TOKEN=твой_telegram_token
LASTFM_API_KEY=твой_lastfm_key
```

Тогда добавь в `config.py`:

```python
from dotenv import load_dotenv
load_dotenv()
```

И установи: `pip install python-dotenv`

### 4. Запуск

```bash
python bot.py
```

-----

## 🗂 Структура проекта

```
music_bot/
├── bot.py            # Основной файл бота (хендлеры, меню)
├── music_sources.py  # Агрегатор источников (Last.fm, iTunes, Deezer, YT)
├── config.py         # Настройки и ключи
├── requirements.txt  # Зависимости
└── README.md
```

-----

## 🎮 Команды бота

|Команда |Описание                   |
|--------|---------------------------|
|`/start`|Главное меню               |
|`/top`  |Глобальный топ прямо сейчас|
|`/help` |Справка и примеры          |

**Или просто пиши текстом:** `lofi chill`, `90s hip hop`, `русский рок` — бот найдёт!

-----

## ⚙️ Кэширование

Данные кэшируются на **6 часов** в памяти — бот быстро отвечает и не перегружает API. При перезапуске кэш сбрасывается.

-----

## 🐳 Docker (опционально)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
```

```bash
docker build -t musicbot .
docker run -d \
  -e BOT_TOKEN=... \
  -e LASTFM_API_KEY=... \
  musicbot
```

-----

## 📝 Лицензия

MIT — используй свободно.