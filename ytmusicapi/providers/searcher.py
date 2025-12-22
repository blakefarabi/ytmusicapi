"""Main lyrics searcher that aggregates multiple providers."""

import re
from typing import Optional, List, Tuple
from ytmusicapi.providers.base import LyricsProvider, LyricLine, SyncedLyrics
from ytmusicapi.providers.lrclib import LrcLibProvider
from ytmusicapi.providers.netease import NetEaseProvider
from ytmusicapi.providers.megalobiz import MegalobizProvider


class SyncedLyricsSearcher:
    """
    Search for synced lyrics across multiple providers.

    Providers are tried in order until lyrics are found.
    Default order: lrclib -> netease -> megalobiz
    """

    PROVIDERS = {
        "lrclib": LrcLibProvider,
        "netease": NetEaseProvider,
        "megalobiz": MegalobizProvider,
    }

    DEFAULT_ORDER = ["lrclib", "netease", "megalobiz"]

    def __init__(self, providers: Optional[List[str]] = None):
        """
        Initialize the searcher.

        Args:
            providers: List of provider names to use in order.
                      If None, uses all providers in default order.
        """
        if providers is None:
            providers = self.DEFAULT_ORDER

        self._providers: List[Tuple[str, LyricsProvider]] = []
        for name in providers:
            if name in self.PROVIDERS:
                self._providers.append((name, self.PROVIDERS[name]()))

    def search(
        self,
        track: str,
        artist: str,
        synced_only: bool = True
    ) -> Optional[SyncedLyrics]:
        """
        Search for lyrics across all configured providers.

        Args:
            track: Song title
            artist: Artist name
            synced_only: If True, only return synced (timestamped) lyrics

        Returns:
            SyncedLyrics object or None if not found
        """
        for provider_name, provider in self._providers:
            try:
                lrc = provider.get_lyrics(track, artist)
                if lrc:
                    is_synced = self._is_synced(lrc)
                    if synced_only and not is_synced:
                        continue

                    lines = self._parse_lrc(lrc) if is_synced else []
                    return SyncedLyrics(
                        track=track,
                        artist=artist,
                        lrc=lrc,
                        lines=lines,
                        source=provider_name
                    )
            except Exception:
                continue

        return None

    def search_all(self, track: str, artist: str) -> List[SyncedLyrics]:
        """
        Search all providers and return all results.

        Useful for comparing lyrics from different sources.
        """
        results = []
        for provider_name, provider in self._providers:
            try:
                lrc = provider.get_lyrics(track, artist)
                if lrc:
                    lines = self._parse_lrc(lrc) if self._is_synced(lrc) else []
                    results.append(SyncedLyrics(
                        track=track,
                        artist=artist,
                        lrc=lrc,
                        lines=lines,
                        source=provider_name
                    ))
            except Exception:
                continue
        return results

    def _is_synced(self, lrc: str) -> bool:
        """Check if lyrics contain timestamps."""
        return bool(re.search(r'\[\d{2}:\d{2}', lrc))

    def _parse_lrc(self, lrc: str) -> List[LyricLine]:
        """Parse LRC format into structured LyricLine objects."""
        lines = []
        # Pattern matches [mm:ss.xx] or [mm:ss:xx] format
        pattern = r'\[(\d{2}):(\d{2})[\.:]+(\d{2,3})\](.*)'

        for line in lrc.split('\n'):
            line = line.strip()
            if not line:
                continue

            match = re.match(pattern, line)
            if match:
                mins, secs, ms, text = match.groups()
                # Normalize milliseconds to 3 digits
                ms = ms.ljust(3, '0')[:3]
                total_ms = int(mins) * 60000 + int(secs) * 1000 + int(ms)
                timestamp = f"[{mins}:{secs}.{ms[:2]}]"
                lines.append(LyricLine(
                    timestamp=timestamp,
                    text=text.strip(),
                    milliseconds=total_ms
                ))

        # Sort by timestamp
        return sorted(lines, key=lambda x: x.milliseconds)

    @classmethod
    def available_providers(cls) -> List[str]:
        """Return list of available provider names."""
        return list(cls.PROVIDERS.keys())
