"""
music_sources.py — агрегатор музыкальных источников
Источники: Last.fm · iTunes RSS · Deezer API · YouTube Music (ytmusicapi)
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

import aiohttp

from config import LASTFM_API_KEY

logger = logging.getLogger(__name__)

# ─── Кэш (сбрасывается каждые 6 часов) ──────────────────────────────────────
_cache: dict[str, tuple[list, str, datetime]] = {}
CACHE_TTL = timedelta(hours=6)

def _cache_get(key: str) -> Optional[tuple[list, str]]:
    if key in _cache:
        data, src, ts = _cache[key]
        if datetime.now() - ts < CACHE_TTL:
            return data, src
    return None

def _cache_set(key: str, data: list, src: str):
    _cache[key] = (data, src, datetime.now())

# ─── Маппинг жанров ──────────────────────────────────────────────────────────
GENRE_ALIASES = {
    "hip-hop": "hip hop",
    "rnb":     "r&b",
    "electronic": "electronic",
    "classical": "classical",
    "workout":  "workout",
    "chill":    "chill",
    "happy":    "happy",
    "sad":      "sad",
    "night vibes": "night",
    "morning":  "morning",
    "party":    "party",
    "relax":    "relax",
}

DEEZER_GENRE_IDS = {
    "pop":        132,
    "rock":       152,
    "hip hop":    116,
    "hip-hop":    116,
    "electronic": 106,
    "jazz":       129,
    "classical":  98,
    "r&b":        165,
    "rnb":        165,
    "country":    84,
    "metal":      464,
    "indie":      76,
    "latin":      67,
    "blues":      113,
    "reggae":     144,
    "soul":       165,
}

ITUNES_GENRE_IDS = {
    "pop":        14,
    "rock":       21,
    "hip hop":    18,
    "hip-hop":    18,
    "electronic": 7,
    "jazz":       11,
    "classical":  5,
    "r&b":        15,
    "rnb":        15,
    "country":    6,
    "metal":      21,
    "indie":      22,
    "latin":      12,
    "blues":      2,
    "reggae":     24,
    "soul":       15,
}

# ─── Основной класс ──────────────────────────────────────────────────────────
class MusicSources:

    # ── Last.fm ──────────────────────────────────────────────────────────────
    async def _lastfm_top_tracks(
        self, session: aiohttp.ClientSession, tag: str = "", limit: int = 50
    ) -> list[dict]:
        try:
            if tag:
                url    = "https://ws.audioscrobbler.com/2.0/"
                params = {
                    "method":  "tag.getTopTracks",
                    "tag":     tag,
                    "api_key": LASTFM_API_KEY,
                    "format":  "json",
                    "limit":   limit,
                }
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    data = await r.json()
                tracks_raw = data.get("tracks", {}).get("track", [])
            else:
                url    = "https://ws.audioscrobbler.com/2.0/"
                params = {
                    "method":  "chart.getTopTracks",
                    "api_key": LASTFM_API_KEY,
                    "format":  "json",
                    "limit":   limit,
                }
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    data = await r.json()
                tracks_raw = data.get("tracks", {}).get("track", [])

            result = []
            for t in tracks_raw:
                result.append({
                    "name":      t.get("name", ""),
                    "artist":    t.get("artist", {}).get("name", "") if isinstance(t.get("artist"), dict) else t.get("artist", ""),
                    "url":       t.get("url", ""),
                    "playcount": t.get("playcount", ""),
                    "source":    "Last.fm",
                })
            return result
        except Exception as e:
            logger.warning(f"Last.fm error: {e}")
            return []

    # ── iTunes RSS ────────────────────────────────────────────────────────────
    async def _itunes_top_songs(
        self, session: aiohttp.ClientSession, genre_id: int = 0, limit: int = 50
    ) -> list[dict]:
        try:
            if genre_id:
                url = f"https://itunes.apple.com/us/rss/topsongs/genre={genre_id}/limit={limit}/json"
            else:
                url = f"https://itunes.apple.com/us/rss/topsongs/limit={limit}/json"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json(content_type=None)
            entries = data.get("feed", {}).get("entry", [])
            result = []
            for e in entries:
                result.append({
                    "name":   e.get("im:name", {}).get("label", ""),
                    "artist": e.get("im:artist", {}).get("label", ""),
                    "url":    e.get("id", {}).get("label", ""),
                    "source": "iTunes",
                })
            return result
        except Exception as e:
            logger.warning(f"iTunes error: {e}")
            return []

    # ── Deezer ───────────────────────────────────────────────────────────────
    async def _deezer_chart(
        self, session: aiohttp.ClientSession, genre_id: int = 0, limit: int = 50
    ) -> list[dict]:
        try:
            if genre_id:
                url = f"https://api.deezer.com/chart/{genre_id}/tracks?limit={limit}"
            else:
                url = f"https://api.deezer.com/chart/0/tracks?limit={limit}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json()
            result = []
            for t in data.get("data", []):
                result.append({
                    "name":   t.get("title", ""),
                    "artist": t.get("artist", {}).get("name", ""),
                    "url":    t.get("link", ""),
                    "source": "Deezer",
                })
            return result
        except Exception as e:
            logger.warning(f"Deezer error: {e}")
            return []

    # ── YouTube Music (ytmusicapi) ────────────────────────────────────────────
    async def _ytmusic_top(self, query: str = "", limit: int = 30) -> list[dict]:
        """Асинхронная обёртка над синхронным ytmusicapi."""
        try:
            from ytmusicapi import YTMusic
            loop = asyncio.get_event_loop()

            def _fetch():
                yt = YTMusic()
                if query:
                    results = yt.search(query, filter="songs", limit=limit)
                    tracks = []
                    for r in results[:limit]:
                        artists = r.get("artists", [{}])
                        artist  = artists[0].get("name", "") if artists else ""
                        vid_id  = r.get("videoId", "")
                        tracks.append({
                            "name":   r.get("title", ""),
                            "artist": artist,
                            "url":    f"https://music.youtube.com/watch?v={vid_id}" if vid_id else "",
                            "source": "YouTube Music",
                        })
                    return tracks
                else:
                    # Charts / trending
                    charts = yt.get_charts(country="US")
                    items  = charts.get("songs", {}).get("items", [])
                    tracks = []
                    for item in items[:limit]:
                        artists = item.get("artists", [{}])
                        artist  = artists[0].get("name", "") if artists else ""
                        vid_id  = item.get("videoId", "")
                        tracks.append({
                            "name":   item.get("title", ""),
                            "artist": artist,
                            "url":    f"https://music.youtube.com/watch?v={vid_id}" if vid_id else "",
                            "source": "YouTube Music",
                        })
                    return tracks

            return await loop.run_in_executor(None, _fetch)
        except Exception as e:
            logger.warning(f"YTMusic error: {e}")
            return []

    # ── Агрегация и дедупликация ──────────────────────────────────────────────
    def _merge(self, *track_lists: list[dict]) -> list[dict]:
        seen   = set()
        merged = []
        for lst in track_lists:
            for t in lst:
                key = (t.get("name", "").lower(), t.get("artist", "").lower())
                if key not in seen and key != ("", ""):
                    seen.add(key)
                    merged.append(t)
        return merged

    def _source_label(self, sources: list[str]) -> str:
        return " · ".join(dict.fromkeys(s for s in sources if s))

    # ── Публичные методы ──────────────────────────────────────────────────────
    async def get_playlist(self, genre: str, source: str = "all") -> tuple[list[dict], str]:
        cache_key = f"{genre}_{source}"
        cached    = _cache_get(cache_key)
        if cached:
            return cached

        tag        = GENRE_ALIASES.get(genre, genre)
        deezer_id  = DEEZER_GENRE_IDS.get(tag, DEEZER_GENRE_IDS.get(genre, 0))
        itunes_id  = ITUNES_GENRE_IDS.get(tag, ITUNES_GENRE_IDS.get(genre, 0))

        async with aiohttp.ClientSession() as session:
            if source == "lastfm":
                tracks   = await self._lastfm_top_tracks(session, tag=tag)
                src_name = "Last.fm"
            elif source == "itunes":
                tracks   = await self._itunes_top_songs(session, genre_id=itunes_id)
                src_name = "iTunes Charts"
            elif source == "deezer":
                tracks   = await self._deezer_chart(session, genre_id=deezer_id)
                src_name = "Deezer"
            elif source == "ytmusic":
                tracks   = await self._ytmusic_top(query=tag)
                src_name = "YouTube Music"
            else:
                # Все источники параллельно
                lf, it, dz, yt = await asyncio.gather(
                    self._lastfm_top_tracks(session, tag=tag),
                    self._itunes_top_songs(session, genre_id=itunes_id),
                    self._deezer_chart(session, genre_id=deezer_id),
                    self._ytmusic_top(query=tag),
                )
                tracks   = self._merge(lf, it, dz, yt)
                src_name = self._source_label(["Last.fm", "iTunes", "Deezer", "YouTube Music"])

        _cache_set(cache_key, tracks, src_name)
        return tracks, src_name

    async def get_global_top(self) -> tuple[list[dict], str]:
        cache_key = "global_top"
        cached    = _cache_get(cache_key)
        if cached:
            return cached

        async with aiohttp.ClientSession() as session:
            lf, it, dz, yt = await asyncio.gather(
                self._lastfm_top_tracks(session),
                self._itunes_top_songs(session),
                self._deezer_chart(session),
                self._ytmusic_top(),
            )
        tracks   = self._merge(lf, it, dz, yt)
        src_name = "Last.fm · iTunes · Deezer · YouTube Music"
        _cache_set(cache_key, tracks, src_name)
        return tracks, src_name

    async def search_all(self, query: str) -> tuple[list[dict], str]:
        cache_key = f"search_{query.lower()}"
        cached    = _cache_get(cache_key)
        if cached:
            return cached

        async with aiohttp.ClientSession() as session:
            lf, it, yt = await asyncio.gather(
                self._lastfm_top_tracks(session, tag=query),
                self._itunes_top_songs(session),        # iTunes без фильтра по запросу
                self._ytmusic_top(query=query),
            )
        tracks   = self._merge(lf, yt, it)
        src_name = self._source_label(
            (["Last.fm"] if lf else []) +
            (["YouTube Music"] if yt else []) +
            (["iTunes"] if it else [])
        ) or "Нет данных"
        _cache_set(cache_key, tracks, src_name)
        return tracks, src_name
