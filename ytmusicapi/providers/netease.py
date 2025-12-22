"""NetEase Music lyrics provider - good for Asian music."""

import requests
from typing import Optional
from ytmusicapi.providers.base import LyricsProvider


class NetEaseProvider(LyricsProvider):
    """
    Fetch lyrics from NetEase Music (163.com)

    Particularly good for Chinese, Japanese, and Korean music.
    No authentication required.
    """

    name = "netease"
    SEARCH_URL = "https://music.163.com/api/search/get"
    LYRICS_URL = "https://music.163.com/api/song/lyric"
    TIMEOUT = 10

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://music.163.com",
            "Accept": "application/json",
        })

    def get_lyrics(self, track: str, artist: str) -> Optional[str]:
        """Fetch lyrics from NetEase Music."""
        song_id = self._search_song(track, artist)
        if not song_id:
            return None
        return self._get_lyrics_by_id(song_id)

    def _search_song(self, track: str, artist: str) -> Optional[int]:
        """Search for a song and return its ID."""
        try:
            response = self.session.post(
                self.SEARCH_URL,
                data={
                    "s": f"{track} {artist}",
                    "type": 1,  # 1 = songs
                    "limit": 10,
                    "offset": 0
                },
                timeout=self.TIMEOUT
            )
            if response.status_code != 200:
                return None

            data = response.json()
            songs = data.get("result", {}).get("songs", [])

            if not songs:
                return None

            # Try to find best match
            track_lower = track.lower()
            artist_lower = artist.lower()

            for song in songs:
                song_name = song.get("name", "").lower()
                song_artists = [a.get("name", "").lower() for a in song.get("artists", [])]

                # Check for good match
                if track_lower in song_name or song_name in track_lower:
                    if any(artist_lower in a or a in artist_lower for a in song_artists):
                        return song["id"]

            # Return first result if no good match
            return songs[0]["id"]

        except (requests.RequestException, ValueError, KeyError):
            pass
        return None

    def _get_lyrics_by_id(self, song_id: int) -> Optional[str]:
        """Get lyrics by song ID."""
        try:
            response = self.session.get(
                self.LYRICS_URL,
                params={
                    "id": song_id,
                    "lv": 1,  # lyric version
                    "kv": 1,  # karaoke version
                    "tv": -1  # translation version
                },
                timeout=self.TIMEOUT
            )
            if response.status_code != 200:
                return None

            data = response.json()

            # Get synced lyrics (lrc format)
            lrc = data.get("lrc", {}).get("lyric")
            if lrc:
                return lrc

            # Try karaoke lyrics as fallback
            return data.get("klyric", {}).get("lyric")

        except (requests.RequestException, ValueError, KeyError):
            pass
        return None

    def get_translation(self, track: str, artist: str) -> Optional[str]:
        """Get translated lyrics if available (usually Chinese to English)."""
        song_id = self._search_song(track, artist)
        if not song_id:
            return None

        try:
            response = self.session.get(
                self.LYRICS_URL,
                params={"id": song_id, "tv": 1},
                timeout=self.TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("tlyric", {}).get("lyric")
        except (requests.RequestException, ValueError):
            pass
        return None
