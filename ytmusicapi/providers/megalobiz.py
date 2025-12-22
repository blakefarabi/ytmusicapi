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
