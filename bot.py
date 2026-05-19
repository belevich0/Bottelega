"""
🎵 MusicBot — Telegram бот для поиска топовых плейлистов
Источники: Last.fm, iTunes Charts, Deezer, YouTube Music (через ytmusicapi)
"""

import os
import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    BotCommand
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from music_sources import MusicSources
from config import BOT_TOKEN

# ─── Логирование ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ─── FSM ────────────────────────────────────────────────────────────────────
class SearchState(StatesGroup):
    waiting_for_query = State()

# ─── Константы ──────────────────────────────────────────────────────────────
GENRES = [
    ("🎸 Rock",        "rock"),
    ("🎵 Pop",         "pop"),
    ("🎤 Hip-Hop",     "hip-hop"),
    ("🎷 Jazz",        "jazz"),
    ("🎻 Classical",   "classical"),
    ("⚡ Electronic",  "electronic"),
    ("🌊 R&B/Soul",    "rnb"),
    ("🤠 Country",     "country"),
    ("🔥 Metal",       "metal"),
    ("🌿 Indie",       "indie"),
    ("💃 Latin",       "latin"),
    ("🎺 Blues",       "blues"),
]

MOODS = [
    ("😊 Happy",       "happy"),
    ("😢 Sad",         "sad"),
    ("💪 Workout",     "workout"),
    ("😌 Chill",       "chill"),
    ("🌙 Night",       "night vibes"),
    ("☀️ Morning",    "morning"),
    ("🎉 Party",       "party"),
    ("🧘 Relax",       "relax"),
]

# ─── Клавиатуры ─────────────────────────────────────────────────────────────
def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎸 По жанру",   callback_data="menu_genre"),
            InlineKeyboardButton(text="😊 По настроению", callback_data="menu_mood"),
        ],
        [
            InlineKeyboardButton(text="🔍 Свой запрос", callback_data="menu_search"),
            InlineKeyboardButton(text="🔥 Топ сегодня",  callback_data="menu_top"),
        ],
        [
            InlineKeyboardButton(text="📡 Источники",   callback_data="menu_sources"),
        ],
    ])

def genre_kb() -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(GENRES), 2):
        row = [InlineKeyboardButton(text=GENRES[i][0], callback_data=f"genre_{GENRES[i][1]}")]
        if i + 1 < len(GENRES):
            row.append(InlineKeyboardButton(text=GENRES[i+1][0], callback_data=f"genre_{GENRES[i+1][1]}"))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def mood_kb() -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(MOODS), 2):
        row = [InlineKeyboardButton(text=MOODS[i][0], callback_data=f"mood_{MOODS[i][1]}")]
        if i + 1 < len(MOODS):
            row.append(InlineKeyboardButton(text=MOODS[i+1][0], callback_data=f"mood_{MOODS[i+1][1]}"))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def source_filter_kb(genre: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎵 All Sources",   callback_data=f"src_all_{genre}"),
        ],
        [
            InlineKeyboardButton(text="Last.fm",          callback_data=f"src_lastfm_{genre}"),
            InlineKeyboardButton(text="iTunes",           callback_data=f"src_itunes_{genre}"),
        ],
        [
            InlineKeyboardButton(text="Deezer",           callback_data=f"src_deezer_{genre}"),
            InlineKeyboardButton(text="YouTube Music",    callback_data=f"src_ytmusic_{genre}"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_genre")],
    ])

def back_kb(callback: str = "back_main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
    ])

# ─── Форматирование плейлиста ────────────────────────────────────────────────
def format_playlist(tracks: list[dict], title: str, source: str) -> str:
    today = datetime.now().strftime("%d.%m.%Y")
    lines = [
        f"🎵 <b>{title}</b>",
        f"📅 Актуально на <b>{today}</b> · Источник: <i>{source}</i>",
        "─" * 32,
    ]
    for i, t in enumerate(tracks[:20], 1):
        name   = t.get("name", "Unknown Track")
        artist = t.get("artist", "Unknown Artist")
        link   = t.get("url", "")
        play   = t.get("playcount", "")
        extra  = f" · <i>{int(play):,} прослушиваний</i>".replace(",", " ") if play else ""
        if link:
            lines.append(f"{i:02d}. <a href='{link}'>{artist} — {name}</a>{extra}")
        else:
            lines.append(f"{i:02d}. {artist} — {name}{extra}")
    lines += ["─" * 32, f"🔢 Треков показано: {min(len(tracks), 20)}"]
    return "\n".join(lines)

# ─── Инициализация ───────────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp  = Dispatcher(storage=MemoryStorage())
ms  = MusicSources()

# ─── Handlers: команды ───────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(msg: Message):
    await msg.answer(
        "👋 Привет! Я <b>MusicBot</b> — твой персональный DJ 🎧\n\n"
        "Я каждый день подтягиваю актуальные чарты из:\n"
        "• 🎵 <b>Last.fm</b> — живые прослушивания\n"
        "• 🍎 <b>iTunes Charts</b> — топ Apple Music\n"
        "• 🟣 <b>Deezer</b> — европейские чарты\n"
        "• ▶️ <b>YouTube Music</b> — тренды YouTube\n\n"
        "Выбери, что ищешь 👇",
        reply_markup=main_menu_kb(),
    )

@dp.message(Command("top"))
async def cmd_top(msg: Message):
    await show_global_top(msg)

@dp.message(Command("help"))
async def cmd_help(msg: Message):
    await msg.answer(
        "📖 <b>Команды бота:</b>\n\n"
        "/start — главное меню\n"
        "/top — глобальный топ прямо сейчас\n"
        "/help — эта справка\n\n"
        "<b>Как пользоваться:</b>\n"
        "1️⃣ Выбери жанр или настроение\n"
        "2️⃣ Или напиши любой запрос (исполнитель, стиль, эпоха)\n"
        "3️⃣ Получай свежий плейлист каждый день!\n\n"
        "💡 Примеры запросов:\n"
        "• <i>90s hip hop</i>\n"
        "• <i>lofi chill beats</i>\n"
        "• <i>Taylor Swift похожие</i>\n"
        "• <i>русский рок 2024</i>",
        reply_markup=back_kb(),
    )

# ─── Handlers: меню ──────────────────────────────────────────────────────────
@dp.callback_query(F.data == "back_main")
async def cb_back_main(cb: CallbackQuery):
    await cb.message.edit_text(
        "🎧 <b>Главное меню</b> — выбери режим:",
        reply_markup=main_menu_kb(),
    )

@dp.callback_query(F.data == "menu_genre")
async def cb_menu_genre(cb: CallbackQuery):
    await cb.message.edit_text("🎸 Выбери жанр:", reply_markup=genre_kb())

@dp.callback_query(F.data == "menu_mood")
async def cb_menu_mood(cb: CallbackQuery):
    await cb.message.edit_text("😊 Выбери настроение:", reply_markup=mood_kb())

@dp.callback_query(F.data == "menu_search")
async def cb_menu_search(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SearchState.waiting_for_query)
    await cb.message.edit_text(
        "🔍 <b>Напиши запрос</b> — жанр, исполнитель, эпоха, настроение...\n\n"
        "Примеры:\n"
        "• <i>lofi hip hop</i>\n"
        "• <i>2000s pop hits</i>\n"
        "• <i>aggressive metal</i>\n"
        "• <i>русский рэп 2024</i>",
    )

@dp.callback_query(F.data == "menu_top")
async def cb_menu_top(cb: CallbackQuery):
    await cb.answer("Загружаю глобальный топ...")
    await show_global_top(cb.message, edit=True)

@dp.callback_query(F.data == "menu_sources")
async def cb_menu_sources(cb: CallbackQuery):
    await cb.message.edit_text(
        "📡 <b>Источники данных:</b>\n\n"
        "🎵 <b>Last.fm</b>\n"
        "   Крупнейшая база прослушиваний. Реальные данные от миллионов пользователей.\n\n"
        "🍎 <b>iTunes / Apple Music Charts</b>\n"
        "   Официальные чарты Apple Music по всем жанрам и странам.\n\n"
        "🟣 <b>Deezer Charts</b>\n"
        "   Европейские и мировые чарты. Обновляются ежедневно.\n\n"
        "▶️ <b>YouTube Music Trends</b>\n"
        "   Самые горячие треки YouTube Music прямо сейчас.\n\n"
        "📊 Бот агрегирует все источники и убирает дубли — "
        "ты получаешь <b>самый полный актуальный плейлист</b>!",
        reply_markup=back_kb(),
    )

# ─── Handlers: жанры ────────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("genre_"))
async def cb_genre(cb: CallbackQuery):
    genre = cb.data.removeprefix("genre_")
    await cb.message.edit_text(
        f"🎵 <b>{genre.title()}</b> — выбери источник:",
        reply_markup=source_filter_kb(genre),
    )

@dp.callback_query(F.data.startswith("src_"))
async def cb_source(cb: CallbackQuery):
    parts  = cb.data.split("_", 2)   # src | source | genre
    source = parts[1]
    genre  = parts[2] if len(parts) > 2 else "pop"
    await cb.answer(f"⏳ Собираю плейлист «{genre}»...")
    await _send_playlist(cb.message, genre=genre, source=source, edit=True)

# ─── Handlers: настроения ────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("mood_"))
async def cb_mood(cb: CallbackQuery):
    mood = cb.data.removeprefix("mood_")
    await cb.answer(f"⏳ Подбираю треки для настроения «{mood}»...")
    await _send_playlist(cb.message, genre=mood, source="all", edit=True)

# ─── Handlers: свободный ввод ────────────────────────────────────────────────
@dp.message(SearchState.waiting_for_query)
async def handle_search_query(msg: Message, state: FSMContext):
    await state.clear()
    query = msg.text.strip()
    wait  = await msg.answer(f"🔍 Ищу плейлист по запросу: <b>{query}</b>...")
    tracks, source = await ms.search_all(query)
    if not tracks:
        await wait.edit_text(
            f"😔 По запросу <b>«{query}»</b> ничего не нашлось.\n"
            "Попробуй другой запрос или выбери жанр из меню.",
            reply_markup=back_kb(),
        )
        return
    text = format_playlist(tracks, f"🔍 «{query}»", source)
    await wait.edit_text(text, reply_markup=back_kb(), disable_web_page_preview=True)

@dp.message(F.text & ~F.text.startswith("/"))
async def handle_free_text(msg: Message):
    query = msg.text.strip()
    wait  = await msg.answer(f"🔍 Ищу: <b>{query}</b>...")
    tracks, source = await ms.search_all(query)
    if not tracks:
        await wait.edit_text("😔 Ничего не нашёл. Попробуй другой запрос.", reply_markup=back_kb())
        return
    text = format_playlist(tracks, f"«{query}»", source)
    await wait.edit_text(text, reply_markup=back_kb(), disable_web_page_preview=True)

# ─── Вспомогательные функции ─────────────────────────────────────────────────
async def show_global_top(msg: Message, edit: bool = False):
    tracks, source = await ms.get_global_top()
    title = f"🔥 Глобальный топ — {datetime.now().strftime('%d.%m.%Y')}"
    text  = format_playlist(tracks, title, source)
    kb    = back_kb()
    if edit:
        await msg.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    else:
        await msg.answer(text, reply_markup=kb, disable_web_page_preview=True)

async def _send_playlist(msg: Message, genre: str, source: str, edit: bool = False):
    tracks, src_name = await ms.get_playlist(genre=genre, source=source)
    label = genre.replace("-", " ").title()
    title = f"{'🎸' if source == 'all' else '🎵'} Топ «{label}»"
    text  = format_playlist(tracks, title, src_name)
    kb    = back_kb()
    if edit:
        await msg.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    else:
        await msg.answer(text, reply_markup=kb, disable_web_page_preview=True)

# ─── Запуск ──────────────────────────────────────────────────────────────────
async def main():
    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="top",   description="Глобальный топ сейчас"),
        BotCommand(command="help",  description="Справка"),
    ])
    logger.info("🎵 MusicBot запущен!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
