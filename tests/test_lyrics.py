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
