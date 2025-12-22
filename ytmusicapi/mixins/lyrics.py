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
