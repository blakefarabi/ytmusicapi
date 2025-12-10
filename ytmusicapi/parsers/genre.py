"""
Parsers for genre browse pages.
"""

from ._utils import *
from ..navigation import nav, TITLE_TEXT, THUMBNAIL_RENDERER, THUMBNAILS


def parse_genre_contents(response: dict) -> dict:
    """Parse the full genre page response."""
    results = {
        "header": None,
        "songs": [],
        "playlists": [],
        "albums": [],
        "artists": [],
        "sections": []
    }

    results["header"] = parse_genre_header(response)

    contents = nav(response, [
        "contents", "singleColumnBrowseResultsRenderer",
        "tabs", 0, "tabRenderer", "content",
        "sectionListRenderer", "contents"
    ], True)

    if not contents:
        return results

    for section in contents:
        parsed = parse_genre_section(section)
        if parsed:
            results["sections"].append(parsed)
            _categorize_section(results, parsed)

    return results


def parse_genre_header(response: dict) -> dict | None:
    """Parse genre page header."""
    header = response.get("header", {})

    if "musicHeaderRenderer" in header:
        return {
            "title": nav(header, ["musicHeaderRenderer", *TITLE_TEXT], True)
        }

    if "musicImmersiveHeaderRenderer" in header:
        ihr = header["musicImmersiveHeaderRenderer"]
        return {
            "title": nav(ihr, TITLE_TEXT, True),
            "thumbnail": nav(ihr, ["thumbnail", *THUMBNAIL_RENDERER, *THUMBNAILS], True)
        }

    return None


def parse_genre_section(section: dict) -> dict | None:
    """Route section to appropriate parser."""
    if "musicCarouselShelfRenderer" in section:
        return parse_carousel_shelf(section["musicCarouselShelfRenderer"])

    if "musicShelfRenderer" in section:
        return parse_music_shelf(section["musicShelfRenderer"])

    if "gridRenderer" in section:
        return parse_grid_renderer(section["gridRenderer"])

    return None


def parse_carousel_shelf(shelf: dict) -> dict:
    """Parse horizontal carousel (playlists, albums, artists)."""
    result = {
        "title": nav(shelf, [
            "header", "musicCarouselShelfBasicHeaderRenderer", *TITLE_TEXT
        ], True),
        "type": "unknown",
        "items": []
    }

    for item in shelf.get("contents", []):
        parsed = parse_two_row_item(item)
        if parsed:
            result["items"].append(parsed)
            if result["type"] == "unknown":
                result["type"] = parsed.get("resultType", "unknown") + "s"

    return result


def parse_two_row_item(item: dict) -> dict | None:
    """Parse musicTwoRowItemRenderer (playlist/album/artist cards)."""
    if "musicTwoRowItemRenderer" not in item:
        return None

    renderer = item["musicTwoRowItemRenderer"]

    title = nav(renderer, TITLE_TEXT, True)

    subtitle_runs = nav(renderer, ["subtitle", "runs"], True) or []
    subtitle = "".join([r.get("text", "") for r in subtitle_runs])

    browse_id = nav(renderer, [
        "navigationEndpoint", "browseEndpoint", "browseId"
    ], True)

    thumbnails = nav(renderer, [
        "thumbnailRenderer", *THUMBNAIL_RENDERER, *THUMBNAILS
    ], True)

    result_type = _get_type_from_browse_id(browse_id)

    return {
        "resultType": result_type,
        "title": title,
        "subtitle": subtitle,
        "browseId": browse_id,
        "thumbnails": thumbnails
    }


def parse_music_shelf(shelf: dict) -> dict:
    """Parse vertical song list shelf."""
    result = {
        "title": nav(shelf, TITLE_TEXT, True),
        "type": "songs",
        "items": []
    }

    for item in shelf.get("contents", []):
        parsed = parse_genre_song(item)
        if parsed:
            result["items"].append(parsed)

    return result


def parse_genre_song(item: dict) -> dict | None:
    """Parse song from musicResponsiveListItemRenderer."""
    if "musicResponsiveListItemRenderer" not in item:
        return None

    renderer = item["musicResponsiveListItemRenderer"]
    flex_columns = renderer.get("flexColumns", [])

    song = {
        "resultType": "song",
        "title": None,
        "videoId": None,
        "artists": [],
        "album": None,
        "views": None,
        "thumbnails": None
    }

    if len(flex_columns) > 0:
        col = flex_columns[0].get("musicResponsiveListItemFlexColumnRenderer", {})
        runs = nav(col, ["text", "runs"], True) or []
        if runs:
            song["title"] = runs[0].get("text")
            song["videoId"] = nav(runs[0], [
                "navigationEndpoint", "watchEndpoint", "videoId"
            ], True)

    if len(flex_columns) > 1:
        col = flex_columns[1].get("musicResponsiveListItemFlexColumnRenderer", {})
        runs = nav(col, ["text", "runs"], True) or []

        for run in runs:
            text = run.get("text", "")
            browse_id = nav(run, [
                "navigationEndpoint", "browseEndpoint", "browseId"
            ], True)

            if browse_id:
                if browse_id.startswith("UC"):
                    song["artists"].append({"name": text, "id": browse_id})
                elif browse_id.startswith("MPREb"):
                    song["album"] = {"name": text, "id": browse_id}
            elif _is_view_count(text):
                song["views"] = text

    song["thumbnails"] = nav(renderer, [
        "thumbnail", *THUMBNAIL_RENDERER, *THUMBNAILS
    ], True)

    return song


def parse_grid_renderer(grid: dict) -> dict:
    """Parse grid layout."""
    result = {
        "title": nav(grid, ["header", "gridHeaderRenderer", *TITLE_TEXT], True),
        "type": "playlists",
        "items": []
    }

    for item in grid.get("items", []):
        parsed = parse_two_row_item(item)
        if parsed:
            result["items"].append(parsed)

    return result


def _get_type_from_browse_id(browse_id: str | None) -> str:
    """Determine content type from browse ID prefix."""
    if not browse_id:
        return "playlist"
    if browse_id.startswith("MPRE"):
        return "album"
    if browse_id.startswith("UC"):
        return "artist"
    return "playlist"


def _is_view_count(text: str) -> bool:
    """Check if text looks like a view count."""
    text_lower = text.lower()
    return ("view" in text_lower or
            text.rstrip().endswith("M") or
            text.rstrip().endswith("K") or
            text.rstrip().endswith("B"))


def _categorize_section(results: dict, section: dict) -> None:
    """Add section items to appropriate category list."""
    section_type = section.get("type", "")
    items = section.get("items", [])

    if section_type == "songs":
        results["songs"].extend(items)
    elif section_type == "playlists":
        results["playlists"].extend(items)
    elif section_type == "albums":
        results["albums"].extend(items)
    elif section_type == "artists":
        results["artists"].extend(items)
