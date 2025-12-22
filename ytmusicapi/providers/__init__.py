"""Lyrics providers for fetching synced lyrics from various sources."""

from ytmusicapi.providers.base import LyricsProvider, LyricLine, SyncedLyrics
from ytmusicapi.providers.lrclib import LrcLibProvider
from ytmusicapi.providers.netease import NetEaseProvider
from ytmusicapi.providers.megalobiz import MegalobizProvider
from ytmusicapi.providers.searcher import SyncedLyricsSearcher

__all__ = [
    "LyricsProvider",
    "LyricLine",
    "SyncedLyrics",
    "LrcLibProvider",
    "NetEaseProvider",
    "MegalobizProvider",
    "SyncedLyricsSearcher",
]
