"""LrcLib.net lyrics provider - free, no authentication required."""

import requests
from typing import Optional
from ytmusicapi.providers.base import LyricsProvider


class LrcLibProvider(LyricsProvider):
    """
    Fetch lyrics from lrclib.net

    This is the primary/recommended provider as it's free,
    has no rate limits, and requires no authentication.
    """

    name = "lrclib"
    BASE_URL = "https://lrclib.net/api"
    TIMEOUT = 10

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ytmusicapi (https://github.com/sigma67/ytmusicapi)"
        })

    def get_lyrics(self, track: str, artist: str) -> Optional[str]:
        """Fetch lyrics from LrcLib."""
        # Try exact match first
        lyrics = self._get_exact_match(track, artist)
        if lyrics:
            return lyrics

        # Fallback to search
        return self._search(track, artist)

    def _get_exact_match(self, track: str, artist: str) -> Optional[str]:
        """Try to get an exact match for track and artist."""
        try:
            response = self.session.get(
                f"{self.BASE_URL}/get",
                params={
                    "track_name": track,
                    "artist_name": artist
                },
                timeout=self.TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                # Prefer synced lyrics, fall back to plain
                return data.get("syncedLyrics") or data.get("plainLyrics")
        except (requests.RequestException, ValueError):
            pass
        return None

    def _search(self, track: str, artist: str) -> Optional[str]:
        """Search for lyrics if exact match fails."""
        try:
            response = self.session.get(
                f"{self.BASE_URL}/search",
                params={"q": f"{artist} {track}"},
                timeout=self.TIMEOUT
            )
            if response.status_code == 200:
                results = response.json()
                if results and len(results) > 0:
                    # Return first result with synced lyrics
                    for result in results:
                        if result.get("syncedLyrics"):
                            return result["syncedLyrics"]
                    # Fall back to plain lyrics
                    return results[0].get("plainLyrics")
        except (requests.RequestException, ValueError):
            pass
        return None

    def get_by_duration(self, track: str, artist: str, duration: int) -> Optional[str]:
        """
        Get lyrics with duration matching for better accuracy.

        Args:
            track: Song title
            artist: Artist name
            duration: Song duration in seconds
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/get",
                params={
                    "track_name": track,
                    "artist_name": artist,
                    "duration": duration
                },
                timeout=self.TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("syncedLyrics") or data.get("plainLyrics")
        except (requests.RequestException, ValueError):
            pass
        return None
