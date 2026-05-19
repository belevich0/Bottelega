import os
import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

class SearchState(StatesGroup):
    waiting_for_query = State()

GENRES = [
    ("🎸 Rock","rock"),("🎵 Pop","pop"),("🎤 Hip-Hop","hip-hop"),
    ("🎷 Jazz","jazz"),("🎻 Classical","classical"),("⚡ Electronic","electronic"),
    ("🌊 R&B","rnb"),("🤠 Country","country"),("🔥 Metal","metal"),
    ("🌿 Indie","indie"),("💃 Latin","latin"),("🎺 Blues","blues"),
]
MOODS = [
    ("😊 Happy","happy"),("😢 Sad","sad"),("💪 Workout","workout"),
    ("😌 Chill","chill"),("🌙 Night","night vibes"),("☀️ Morning","morning"),
    ("🎉 Party","party"),("🧘 Relax","relax"),
]

def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎸 По жанру",callback_data="menu_genre"),
         InlineKeyboardButton(text="😊 По настроению",callback_data="menu_mood")],
        [InlineKeyboardButton(text="🔍 Свой запрос",callback_data="menu_search"),
         InlineKeyboardButton(text="🔥 Топ сегодня",callback_data="menu_top")],
        [InlineKeyboardButton(text="📡 Источники",callback_data="menu_sources")],
    ])

def genre_kb():
    rows=[]
    for i in range(0,len(GENRES),2):
        row=[InlineKeyboardButton(text=GENRES[i][0],callback_data=f"genre_{GENRES[i][1]}")]
        if i+1<len(GENRES): row.append(InlineKeyboardButton(text=GENRES[i+1][0],callback_data=f"genre_{GENRES[i+1][1]}"))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Назад",callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def mood_kb():
    rows=[]
    for i in range(0,len(MOODS),2):
        row=[InlineKeyboardButton(text=MOODS[i][0],callback_data=f"mood_{MOODS[i][1]}")]
        if i+1<len(MOODS): row.append(InlineKeyboardButton(text=MOODS[i+1][0],callback_data=f"mood_{MOODS[i+1][1]}"))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Назад",callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def source_filter_kb(genre):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵 Все источники",callback_data=f"src_all_{genre}")],
        [InlineKeyboardButton(text="Last.fm",callback_data=f"src_lastfm_{genre}"),
         InlineKeyboardButton(text="iTunes",callback_data=f"src_itunes_{genre}")],
        [InlineKeyboardButton(text="Deezer",callback_data=f"src_deezer_{genre}"),
         InlineKeyboardButton(text="YouTube Music",callback_data=f"src_ytmusic_{genre}")],
        [InlineKeyboardButton(text="⬅️ Назад",callback_data="menu_genre")],
    ])

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню",callback_data="back_main")]
    ])

def format_playlist(tracks,title,source):
    today=datetime.now().strftime("%d.%m.%Y")
    lines=[f"🎵 <b>{title}</b>",f"📅 {today} · <i>{source}</i>","─"*30]
    for i,t in enumerate(tracks[:20],1):
        name=t.get("name","?"); artist=t.get("artist","?"); link=t.get("url","")
        play=t.get("playcount","")
        extra=f" · <i>{int(play):,} прослуш.</i>".replace(",","") if play else ""
        if link: lines.append(f"{i:02d}. <a href='{link}'>{artist} — {name}</a>{extra}")
        else: lines.append(f"{i:02d}. {artist} — {name}{extra}")
    lines+=["─"*30,f"Треков: {min(len(tracks),20)}"]
    return "\n".join(lines)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp  = Dispatcher(storage=MemoryStorage())
ms  = MusicSources()

@dp.message(CommandStart())
async def cmd_start(msg:Message):
    await msg.answer("👋 Привет! Я <b>MusicBot</b> 🎧\n\nЧарты из Last.fm, iTunes, Deezer, YouTube Music.\n\nВыбери что ищешь 👇",reply_markup=main_menu_kb())

@dp.message(Command("top"))
async def cmd_top(msg:Message): await show_global_top(msg)

@dp.message(Command("help"))
async def cmd_help(msg:Message):
    await msg.answer("📖 /start — меню\n/top — глобальный топ\n\nИли просто напиши: <i>lofi chill</i>, <i>русский рок</i>",reply_markup=back_kb())

@dp.callback_query(F.data=="back_main")
async def cb_back(cb:CallbackQuery): await cb.message.edit_text("🎧 Главное меню:",reply_markup=main_menu_kb())

@dp.callback_query(F.data=="menu_genre")
async def cb_genre_menu(cb:CallbackQuery): await cb.message.edit_text("🎸 Выбери жанр:",reply_markup=genre_kb())

@dp.callback_query(F.data=="menu_mood")
async def cb_mood_menu(cb:CallbackQuery): await cb.message.edit_text("😊 Выбери настроение:",reply_markup=mood_kb())

@dp.callback_query(F.data=="menu_search")
async def cb_search(cb:CallbackQuery,state:FSMContext):
    await state.set_state(SearchState.waiting_for_query)
    await cb.message.edit_text("🔍 Напиши запрос — жанр, исполнитель, эпоха...\n\nПример: <i>90s hip hop</i>, <i>русский рэп</i>")

@dp.callback_query(F.data=="menu_top")
async def cb_top(cb:CallbackQuery):
    await cb.answer("Загружаю..."); await show_global_top(cb.message,edit=True)

@dp.callback_query(F.data=="menu_sources")
async def cb_sources(cb:CallbackQuery):
    await cb.message.edit_text("📡 <b>Источники:</b>\n\n🎵 Last.fm\n🍎 iTunes\n🟣 Deezer\n▶️ YouTube Music\n\nДанные обновляются каждые 6 часов!",reply_markup=back_kb())

@dp.callback_query(F.data.startswith("genre_"))
async def cb_genre(cb:CallbackQuery):
    genre=cb.data.removeprefix("genre_")
    await cb.message.edit_text(f"🎵 <b>{genre.title()}</b> — источник:",reply_markup=source_filter_kb(genre))

@dp.callback_query(F.data.startswith("src_"))
async def cb_src(cb:CallbackQuery):
    parts=cb.data.split("_",2); source=parts[1]; genre=parts[2] if len(parts)>2 else "pop"
    await cb.answer("⏳ Собираю..."); await _send_playlist(cb.message,genre=genre,source=source,edit=True)

@dp.callback_query(F.data.startswith("mood_"))
async def cb_mood(cb:CallbackQuery):
    mood=cb.data.removeprefix("mood_"); await cb.answer("⏳ Подбираю...")
    await _send_playlist(cb.message,genre=mood,source="all",edit=True)

@dp.message(SearchState.waiting_for_query)
async def handle_search(msg:Message,state:FSMContext):
    await state.clear(); query=msg.text.strip()
    wait=await msg.answer(f"🔍 Ищу: <b>{query}</b>...")
    tracks,source=await ms.search_all(query)
    if not tracks: await wait.edit_text("😔 Ничего не нашлось.",reply_markup=back_kb()); return
    await wait.edit_text(format_playlist(tracks,f"🔍 «{query}»",source),reply_markup=back_kb(),disable_web_page_preview=True)

@dp.message(F.text & ~F.text.startswith("/"))
async def handle_text(msg:Message):
    query=msg.text.strip(); wait=await msg.answer(f"🔍 Ищу: <b>{query}</b>...")
    tracks,source=await ms.search_all(query)
    if not tracks: await wait.edit_text("😔 Ничего не нашёл.",reply_markup=back_kb()); return
    await wait.edit_text(format_playlist(tracks,f"«{query}»",source),reply_markup=back_kb(),disable_web_page_preview=True)

async def show_global_top(msg:Message,edit=False):
    tracks,source=await ms.get_global_top()
    title=f"🔥 Глобальный топ — {datetime.now().strftime('%d.%m.%Y')}"
    text=format_playlist(tracks,title,source)
    if edit: await msg.edit_text(text,reply_markup=back_kb(),disable_web_page_preview=True)
    else: await msg.answer(text,reply_markup=back_kb(),disable_web_page_preview=True)

async def _send_playlist(msg:Message,genre:str,source:str,edit=False):
    tracks,src_name=await ms.get_playlist(genre=genre,source=source)
    text=format_playlist(tracks,f"🎵 Топ «{genre.title()}»",src_name)
    if edit: await msg.edit_text(text,reply_markup=back_kb(),disable_web_page_preview=True)
    else: await msg.answer(text,reply_markup=back_kb(),disable_web_page_preview=True)

async def main():
    await bot.set_my_commands([
        BotCommand(command="start",description="Главное меню"),
        BotCommand(command="top",description="Глобальный топ"),
        BotCommand(command="help",description="Справка"),
    ])
    logger.info("🎵 MusicBot запущен!")
    await dp.start_polling(bot,skip_updates=True)

if __name__=="__main__":
    asyncio.run(main())
