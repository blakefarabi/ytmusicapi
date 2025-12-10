from typing import Optional, List, Dict, Any

from ytmusicapi.mixins._protocol import MixinProtocol
from ytmusicapi.parsers.genre import parse_genre_contents


class GenreMixin(MixinProtocol):
    """Mixin class for genre browsing functionality."""

    def browse_genre(self, params: str) -> dict:
        """
        Get contents of a genre page (songs, playlists, etc.).

        Use :py:func:`get_mood_categories` to obtain the params for each genre.

        :param params: The params value from get_mood_categories() results.
            Example: "ggMPOg1uX1JOQWZFczlCblJ3" for Rock
        :return: Dict containing:
            - header: Genre title and optional thumbnail
            - songs: List of song dicts with title, artists, views, album, videoId
            - playlists: List of playlist dicts with title, subtitle, browseId
            - albums: List of album dicts (if present)
            - artists: List of artist dicts (if present)
            - sections: Raw parsed sections for custom handling

        Example::

            # Get genre params
            categories = yt.get_mood_categories()
            rock_params = None
            for cat, items in categories.items():
                for item in items:
                    if item['title'] == 'Rock':
                        rock_params = item['params']
                        break

            # Browse the genre
            genre = yt.browse_genre(rock_params)

            # Access songs
            for song in genre['songs']:
                print(f"{song['title']} - {song['artists'][0]['name']}")

            # Access playlists
            for pl in genre['playlists']:
                print(f"{pl['title']}")
        """
        body = {
            "browseId": "FEmusic_moods_and_genres_category",
            "params": params
        }

        response = self._send_request("browse", body)
        return parse_genre_contents(response)

    def get_genre(self, genre_name: str) -> Optional[dict]:
        """
        Convenience method to browse a genre by name.

        :param genre_name: Name of the genre (e.g., "Rock", "Pop", "Hip-Hop")
        :return: Genre page contents, or None if genre not found

        Example::

            rock = yt.get_genre("Rock")
            if rock:
                print(f"Found {len(rock['songs'])} songs")
        """
        categories = self.get_mood_categories()

        for cat_items in categories.values():
            for item in cat_items:
                if item.get("title", "").lower() == genre_name.lower():
                    return self.browse_genre(item["params"])

        return None

    def list_genres(self) -> List[dict]:
        """
        Get a flat list of all available genres with their params.

        :return: List of dicts with 'category', 'title', and 'params' keys

        Example::

            genres = yt.list_genres()
            for g in genres:
                print(f"{g['title']} ({g['category']})")
        """
        categories = self.get_mood_categories()
        genres = []

        for category_name, items in categories.items():
            for item in items:
                genres.append({
                    "category": category_name,
                    "title": item.get("title"),
                    "params": item.get("params")
                })

        return genres
