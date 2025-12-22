#!/bin/bash

# ============================================================================
# YTMusicAPI + SyncedLyrics Integration Build Script
# Run from the root of the ytmusicapi repository
# Usage: chmod +x build_lyrics_integration.sh && ./build_lyrics_integration.sh
# ============================================================================

set -e

echo "🎵 Building SyncedLyrics integration for ytmusicapi..."

# Check if we're in the right directory
if [ ! -d "ytmusicapi" ]; then
    echo "❌ Error: ytmusicapi directory not found."
    echo "   Please run this script from the root of the ytmusicapi repository."
    exit 1
fi

# ============================================================================
# Create providers directory
# ============================================================================
echo "📁 Creating providers directory..."
mkdir -p ytmusicapi/providers

# ============================================================================
# Create ytmusicapi/providers/__init__.py
# ============================================================================
echo "📄 Creating providers/__init__.py..."
cat > ytmusicapi/providers/__init__.py << 'EOF'
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
EOF

# ============================================================================
# Create ytmusicapi/providers/base.py
# ============================================================================
echo "📄 Creating providers/base.py..."
cat > ytmusicapi/providers/base.py << 'EOF'
"""Base classes and data structures for lyrics providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List
import re


@dataclass
class LyricLine:
    """Represents a single line of synced lyrics."""
    timestamp: str  # "[mm:ss.xx]" format
    text: str
    milliseconds: int

    def __repr__(self) -> str:
        return f"{self.timestamp} {self.text}"


@dataclass
class SyncedLyrics:
    """Container for synced lyrics data."""
    track: str
    artist: str
    lrc: str  # Full LRC format string
    lines: List[LyricLine] = field(default_factory=list)
    source: str = ""

    def to_lrc(self) -> str:
        """Return the raw LRC format string."""
        return self.lrc

    def to_plain_text(self) -> str:
        """Return lyrics as plain text without timestamps."""
        return "\n".join(line.text for line in self.lines if line.text)

    def get_line_at(self, milliseconds: int) -> Optional[LyricLine]:
        """Get the lyric line at a specific timestamp."""
        current_line = None
        for line in self.lines:
            if line.milliseconds <= milliseconds:
                current_line = line
            else:
                break
        return current_line


class LyricsProvider(ABC):
    """Abstract base class for lyrics providers."""

    name: str = "base"

    @abstractmethod
    def get_lyrics(self, track: str, artist: str) -> Optional[str]:
        """
        Fetch lyrics for a given track and artist.

        Args:
            track: The song title
            artist: The artist name

        Returns:
            LRC format lyrics string or None if not found
        """
        pass

    def _clean_query(self, text: str) -> str:
        """Clean up search query text."""
        # Remove common suffixes and special characters
        text = re.sub(r'\s*[\(\[].*?[\)\]]', '', text)
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
EOF

# ============================================================================
# Create ytmusicapi/providers/lrclib.py
# ============================================================================
echo "📄 Creating providers/lrclib.py..."
cat > ytmusicapi/providers/lrclib.py << 'EOF'
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
EOF

# ============================================================================
# Create ytmusicapi/providers/netease.py
# ============================================================================
echo "📄 Creating providers/netease.py..."
cat > ytmusicapi/providers/netease.py << 'EOF'
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
EOF

# ============================================================================
# Create ytmusicapi/providers/megalobiz.py
# ============================================================================
echo "📄 Creating providers/megalobiz.py..."
cat > ytmusicapi/providers/megalobiz.py << 'EOF'
"""Megalobiz lyrics provider - web scraping fallback."""

import re
import requests
from typing import Optional
from ytmusicapi.providers.base import LyricsProvider


class MegalobizProvider(LyricsProvider):
    """
    Fetch lyrics from Megalobiz via web scraping.

    This is a fallback provider when other APIs don't have results.
    """

    name = "megalobiz"
    BASE_URL = "https://www.megalobiz.com"
    SEARCH_URL = f"{BASE_URL}/search/all"
    TIMEOUT = 15

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

    def get_lyrics(self, track: str, artist: str) -> Optional[str]:
        """Fetch lyrics from Megalobiz."""
        lrc_url = self._search(track, artist)
        if not lrc_url:
            return None
        return self._get_lrc_content(lrc_url)

    def _search(self, track: str, artist: str) -> Optional[str]:
        """Search for LRC file URL."""
        try:
            query = self._clean_query(f"{artist} {track}")
            response = self.session.get(
                self.SEARCH_URL,
                params={
                    "qry": query,
                    "display": "more"
                },
                timeout=self.TIMEOUT
            )
            if response.status_code != 200:
                return None

            # Find LRC links in search results
            lrc_pattern = r'href="(/lrc/maker/[^"]+\.megalobiz)"'
            matches = re.findall(lrc_pattern, response.text)

            if not matches:
                # Try alternate pattern
                lrc_pattern = r'href="(/lrc/[^"]+)"'
                matches = re.findall(lrc_pattern, response.text)

            if matches:
                return f"{self.BASE_URL}{matches[0]}"

        except requests.RequestException:
            pass
        return None

    def _get_lrc_content(self, url: str) -> Optional[str]:
        """Extract LRC content from the page."""
        try:
            response = self.session.get(url, timeout=self.TIMEOUT)
            if response.status_code != 200:
                return None

            # Try multiple patterns to extract LRC content
            patterns = [
                r'<div[^>]*id="lrc_\d+_lyrics"[^>]*>([\s\S]*?)</div>',
                r'<pre[^>]*class="[^"]*lyrics[^"]*"[^>]*>([\s\S]*?)</pre>',
                r'<div[^>]*class="[^"]*lrc-content[^"]*"[^>]*>([\s\S]*?)</div>',
            ]

            for pattern in patterns:
                match = re.search(pattern, response.text, re.IGNORECASE)
                if match:
                    lrc = match.group(1)
                    return self._clean_lrc(lrc)

            # Try to find any timestamped content
            timestamp_pattern = r'(\[\d{2}:\d{2}[\.:]\d{2,3}\][^\[]+)'
            timestamps = re.findall(timestamp_pattern, response.text)
            if timestamps:
                return "\n".join(timestamps)

        except requests.RequestException:
            pass
        return None

    def _clean_lrc(self, lrc: str) -> str:
        """Clean up extracted LRC content."""
        # Replace HTML line breaks
        lrc = re.sub(r'<br\s*/?>', '\n', lrc)
        # Remove remaining HTML tags
        lrc = re.sub(r'<[^>]+>', '', lrc)
        # Decode HTML entities
        lrc = lrc.replace('&nbsp;', ' ')
        lrc = lrc.replace('&amp;', '&')
        lrc = lrc.replace('&lt;', '<')
        lrc = lrc.replace('&gt;', '>')
        lrc = lrc.replace('&#39;', "'")
        lrc = lrc.replace('&quot;', '"')
        # Clean up whitespace
        lines = [line.strip() for line in lrc.split('\n')]
        return '\n'.join(line for line in lines if line)
EOF

# ============================================================================
# Create ytmusicapi/providers/searcher.py
# ============================================================================
echo "📄 Creating providers/searcher.py..."
cat > ytmusicapi/providers/searcher.py << 'EOF'
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
EOF

# ============================================================================
# Create ytmusicapi/mixins/lyrics.py
# ============================================================================
echo "📄 Creating mixins/lyrics.py..."
cat > ytmusicapi/mixins/lyrics.py << 'EOF'
"""Lyrics mixin for YTMusic class - adds synced lyrics functionality."""

import re
from typing import Optional, List, Dict, Any
from ytmusicapi.providers import SyncedLyricsSearcher, SyncedLyrics


class LyricsMixin:
    """
    Mixin class that adds synced lyrics functionality to YTMusic.

    This integrates external lyrics providers (lrclib, netease, megalobiz)
    with the YouTube Music API.
    """

    _lyrics_searcher: Optional[SyncedLyricsSearcher] = None

    @property
    def lyrics_searcher(self) -> SyncedLyricsSearcher:
        """Lazy-loaded lyrics searcher instance."""
        if self._lyrics_searcher is None:
            self._lyrics_searcher = SyncedLyricsSearcher()
        return self._lyrics_searcher

    def configure_lyrics_providers(self, providers: List[str]) -> None:
        """
        Configure which lyrics providers to use and their order.

        Args:
            providers: List of provider names.
                      Available: "lrclib", "netease", "megalobiz"

        Example:
            ytmusic.configure_lyrics_providers(["lrclib", "netease"])
        """
        self._lyrics_searcher = SyncedLyricsSearcher(providers)

    def get_synced_lyrics(
        self,
        video_id: str,
        synced_only: bool = True
    ) -> Optional[SyncedLyrics]:
        """
        Get synced lyrics for a YouTube Music track.

        Args:
            video_id: YouTube video ID of the track
            synced_only: If True, only return timestamped lyrics

        Returns:
            SyncedLyrics object with LRC data, or None if not found

        Example:
            lyrics = ytmusic.get_synced_lyrics("dQw4w9WgXcQ")
            if lyrics:
                print(lyrics.lrc)  # Full LRC format
                for line in lyrics.lines:
                    print(f"{line.timestamp} {line.text}")
        """
        try:
            song = self.get_song(video_id)
            video_details = song.get("videoDetails", {})

            title = video_details.get("title", "")
            artist = video_details.get("author", "")

            # Clean the title for better matching
            title = self._clean_song_title(title)
            artist = self._clean_artist_name(artist)

            if not title:
                return None

            return self.lyrics_searcher.search(title, artist, synced_only)

        except Exception:
            return None

    def get_synced_lyrics_from_search(
        self,
        query: str,
        synced_only: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Search for a song on YouTube Music and get its synced lyrics.

        Args:
            query: Search query (e.g., "Shape of You Ed Sheeran")
            synced_only: If True, only return timestamped lyrics

        Returns:
            Dict with 'song' (YTM result) and 'lyrics' (SyncedLyrics or None)

        Example:
            result = ytmusic.get_synced_lyrics_from_search("Bohemian Rhapsody Queen")
            if result and result["lyrics"]:
                print(f"Source: {result['lyrics'].source}")
                print(result["lyrics"].lrc)
        """
        try:
            results = self.search(query, filter="songs", limit=1)
            if not results:
                return None

            song = results[0]
            title = song.get("title", "")
            artists = ", ".join([a.get("name", "") for a in song.get("artists", [])])

            lyrics = self.lyrics_searcher.search(title, artists, synced_only)

            return {
                "song": song,
                "lyrics": lyrics
            }
        except Exception:
            return None

    def get_lyrics_for_playlist(
        self,
        playlist_id: str,
        synced_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get synced lyrics for all tracks in a playlist.

        Args:
            playlist_id: YouTube Music playlist ID
            synced_only: If True, only return timestamped lyrics

        Returns:
            List of dicts, each with 'track' and 'lyrics' keys

        Example:
            results = ytmusic.get_lyrics_for_playlist("PLxxxxx")
            for item in results:
                if item["lyrics"]:
                    print(f"{item['track']['title']}: {item['lyrics'].source}")
        """
        results = []
        try:
            playlist = self.get_playlist(playlist_id)

            for track in playlist.get("tracks", []):
                title = track.get("title", "")
                artists = ", ".join([a.get("name", "") for a in track.get("artists", [])])

                lyrics = self.lyrics_searcher.search(title, artists, synced_only)
                results.append({
                    "track": track,
                    "lyrics": lyrics
                })
        except Exception:
            pass

        return results

    def get_lyrics_for_album(
        self,
        browse_id: str,
        synced_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get synced lyrics for all tracks in an album.

        Args:
            browse_id: YouTube Music album browse ID
            synced_only: If True, only return timestamped lyrics

        Returns:
            List of dicts, each with 'track' and 'lyrics' keys
        """
        results = []
        try:
            album = self.get_album(browse_id)
            album_artist = ", ".join([a.get("name", "") for a in album.get("artists", [])])

            for track in album.get("tracks", []):
                title = track.get("title", "")
                # Use track artists if available, otherwise album artist
                artists = track.get("artists")
                if artists:
                    artist = ", ".join([a.get("name", "") for a in artists])
                else:
                    artist = album_artist

                lyrics = self.lyrics_searcher.search(title, artist, synced_only)
                results.append({
                    "track": track,
                    "lyrics": lyrics
                })
        except Exception:
            pass

        return results

    def search_lyrics(
        self,
        track: str,
        artist: str,
        synced_only: bool = True
    ) -> Optional[SyncedLyrics]:
        """
        Search for lyrics directly by track and artist name.

        Args:
            track: Song title
            artist: Artist name
            synced_only: If True, only return timestamped lyrics

        Returns:
            SyncedLyrics object or None

        Example:
            lyrics = ytmusic.search_lyrics("Bohemian Rhapsody", "Queen")
        """
        return self.lyrics_searcher.search(track, artist, synced_only)

    def _clean_song_title(self, title: str) -> str:
        """Clean up song title for better lyrics matching."""
        # Remove common video suffixes
        patterns = [
            r'\s*[\(\[](Official\s*)?(Music\s*)?(Video|Audio|Lyrics?|MV|M/V|HD|HQ|4K)[\)\]]',
            r'\s*[\(\[](Visualizer|Lyric Video|Audio Only)[\)\]]',
            r'\s*[\(\[]feat\.?[^\)\]]+[\)\]]',
            r'\s*[\(\[]ft\.?[^\)\]]+[\)\]]',
            r'\s*[\(\[]with\s+[^\)\]]+[\)\]]',
            r'\s*[\(\[]Remaster(ed)?[^\)\]]*[\)\]]',
            r'\s*[\(\[]\d{4}[^\)\]]*[\)\]]',
            r'\s*-\s*(Official\s*)?(Music\s*)?(Video|Audio)',
            r'\s*\|\s*.*$',
        ]

        result = title
        for pattern in patterns:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)

        # Clean up extra whitespace and trailing dashes
        result = re.sub(r'\s+', ' ', result)
        result = re.sub(r'\s*[-–—]\s*$', '', result)

        return result.strip()

    def _clean_artist_name(self, artist: str) -> str:
        """Clean up artist name for better lyrics matching."""
        # Remove "- Topic" suffix from YouTube Music auto-generated channels
        artist = re.sub(r'\s*-\s*Topic$', '', artist, flags=re.IGNORECASE)
        # Remove "VEVO" suffix
        artist = re.sub(r'VEVO$', '', artist, flags=re.IGNORECASE)
        return artist.strip()
EOF

# ============================================================================
# Create examples directory and example file
# ============================================================================
echo "📁 Creating examples directory..."
mkdir -p examples

echo "📄 Creating examples/synced_lyrics_example.py..."
cat > examples/synced_lyrics_example.py << 'EOF'
"""
Example usage of the synced lyrics feature in ytmusicapi.
"""

from ytmusicapi import YTMusic

# Initialize YTMusic (no auth needed for lyrics)
ytmusic = YTMusic()

# Example 1: Get lyrics by video ID
print("=== Get Lyrics by Video ID ===")
lyrics = ytmusic.get_synced_lyrics("dQw4w9WgXcQ")
if lyrics:
    print(f"Found lyrics from: {lyrics.source}")
    print(f"Track: {lyrics.track}")
    print(f"Artist: {lyrics.artist}")
    print("\nFirst 5 lines:")
    for line in lyrics.lines[:5]:
        print(f"  {line.timestamp} {line.text}")
else:
    print("No lyrics found")

# Example 2: Search and get lyrics
print("\n=== Search and Get Lyrics ===")
result = ytmusic.get_synced_lyrics_from_search("Bohemian Rhapsody Queen")
if result:
    song = result["song"]
    print(f"Found song: {song['title']} by {song['artists'][0]['name']}")
    if result["lyrics"]:
        print(f"Lyrics source: {result['lyrics'].source}")

# Example 3: Direct lyrics search
print("\n=== Direct Lyrics Search ===")
lyrics = ytmusic.search_lyrics("Shape of You", "Ed Sheeran")
if lyrics:
    print(f"Source: {lyrics.source}")
    print("\nPlain text (first 200 chars):")
    print(lyrics.to_plain_text()[:200])

# Example 4: Configure specific providers
print("\n=== Using Specific Providers ===")
ytmusic.configure_lyrics_providers(["lrclib"])
lyrics = ytmusic.search_lyrics("Blinding Lights", "The Weeknd")
if lyrics:
    print(f"Found using: {lyrics.source}")
EOF

# ============================================================================
# Create tests directory and test file
# ============================================================================
echo "📁 Creating tests directory..."
mkdir -p tests

echo "📄 Creating tests/test_lyrics.py..."
cat > tests/test_lyrics.py << 'EOF'
"""Tests for synced lyrics functionality."""

import pytest
from unittest.mock import Mock, patch

from ytmusicapi.providers import (
    SyncedLyricsSearcher,
    LrcLibProvider,
    SyncedLyrics,
    LyricLine,
)
from ytmusicapi.mixins.lyrics import LyricsMixin


class TestLyricLine:
    def test_lyric_line_creation(self):
        line = LyricLine(
            timestamp="[01:23.45]",
            text="Hello world",
            milliseconds=83450
        )
        assert line.timestamp == "[01:23.45]"
        assert line.text == "Hello world"
        assert line.milliseconds == 83450


class TestSyncedLyrics:
    def test_to_plain_text(self):
        lyrics = SyncedLyrics(
            track="Test",
            artist="Artist",
            lrc="",
            lines=[
                LyricLine("[00:01.00]", "Line 1", 1000),
                LyricLine("[00:02.00]", "Line 2", 2000),
            ]
        )
        assert lyrics.to_plain_text() == "Line 1\nLine 2"

    def test_get_line_at(self):
        lyrics = SyncedLyrics(
            track="Test",
            artist="Artist",
            lrc="",
            lines=[
                LyricLine("[00:01.00]", "Line 1", 1000),
                LyricLine("[00:05.00]", "Line 2", 5000),
            ]
        )
        assert lyrics.get_line_at(5000).text == "Line 2"
        assert lyrics.get_line_at(7000).text == "Line 2"


class TestSyncedLyricsSearcher:
    def test_available_providers(self):
        providers = SyncedLyricsSearcher.available_providers()
        assert "lrclib" in providers
        assert "netease" in providers

    def test_is_synced(self):
        searcher = SyncedLyricsSearcher()
        assert searcher._is_synced("[00:01.00]Hello") is True
        assert searcher._is_synced("Just plain text") is False


class TestLyricsMixin:
    def test_clean_song_title(self):
        mixin = LyricsMixin()
        assert mixin._clean_song_title("Song (Official Video)") == "Song"
        assert mixin._clean_song_title("Song [Official Audio]") == "Song"

    def test_clean_artist_name(self):
        mixin = LyricsMixin()
        assert mixin._clean_artist_name("Artist - Topic") == "Artist"
        assert mixin._clean_artist_name("ArtistVEVO") == "Artist"
EOF

# ============================================================================
# Print instructions for manual updates
# ============================================================================
echo ""
echo "✅ All new files created successfully!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠️  MANUAL UPDATES REQUIRED:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Edit ytmusicapi/ytmusic.py:"
echo "   - Add import: from ytmusicapi.mixins.lyrics import LyricsMixin"
echo "   - Add LyricsMixin to the YTMusic class inheritance"
echo ""
echo "2. Edit ytmusicapi/mixins/__init__.py:"
echo "   - Add: from ytmusicapi.mixins.lyrics import LyricsMixin"
echo ""
echo "3. Edit ytmusicapi/__init__.py:"
echo "   - Add exports for SyncedLyrics, LyricLine, SyncedLyricsSearcher"
echo ""
echo "4. Ensure 'requests' is in requirements.txt (usually already present)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📦 To test the installation:"
echo "   pip install -e ."
echo "   python -c \"from ytmusicapi import YTMusic; yt = YTMusic(); print(yt.search_lyrics('Bohemian Rhapsody', 'Queen'))\""
echo ""
echo "🎵 Done!"
