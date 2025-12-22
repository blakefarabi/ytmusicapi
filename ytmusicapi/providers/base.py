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
