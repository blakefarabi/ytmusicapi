#!/usr/bin/env python3
"""
Run this script from your ytmusicapi repo root:
    python patch_lyrics.py

It will automatically patch the get_lyrics method in ytmusicapi/mixins/browsing.py
"""

import re

NEW_GET_LYRICS = '''    def get_lyrics(self, browseId: str) -> dict:
        """
        Returns lyrics of a song or video, including timestamps if available.

        :param browseId: Lyrics browse id obtained from `get_watch_playlist`
        :return: Dictionary with lyrics, source, and optional timed lyrics
        """
        if not browseId:
            raise YTMusicUserError("Invalid browseId provided.")

        response = self._send_request("browse", {"browseId": browseId})

        results = {
            "lyrics": None,
            "source": None,
            "hasTimestamps": False,
            "timedLyrics": None
        }

        contents = nav(response, ["contents", "sectionListRenderer", "contents", 0], True)

        if contents is None:
            return results

        # Try timed/synced lyrics path first (elementRenderer)
        if "elementRenderer" in contents:
            timed_data = nav(contents, [
                "elementRenderer",
                "newElement",
                "type",
                "componentType",
                "model",
                "timedLyricsModel",
                "lyricsData"
            ], True)

            if timed_data and "timedLyricsData" in timed_data:
                timed_lyrics = []
                for line in timed_data["timedLyricsData"]:
                    cue = line.get("cueRange", {})
                    timed_lyrics.append({
                        "text": line.get("lyricLine", ""),
                        "startTimeMs": int(cue.get("startTimeMilliseconds", 0)),
                        "endTimeMs": int(cue.get("endTimeMilliseconds", 0)),
                    })

                results["lyrics"] = "\\n".join([l["text"] for l in timed_lyrics])
                results["source"] = timed_data.get("sourceMessage", "")
                results["hasTimestamps"] = True
                results["timedLyrics"] = timed_lyrics
                return results

        # Fall back to plain lyrics (musicDescriptionShelfRenderer)
        if "musicDescriptionShelfRenderer" in contents:
            shelf = contents["musicDescriptionShelfRenderer"]
            results["lyrics"] = nav(shelf, ["description", "runs", 0, "text"], True)
            results["source"] = nav(shelf, ["footer", "runs", 0, "text"], True)
            return results

        return results

'''

def patch_file():
    filepath = "ytmusicapi/mixins/browsing.py"

    try:
        with open(filepath, "r") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: {filepath} not found. Run this from the ytmusicapi repo root.")
        return False

    # Pattern to match the entire get_lyrics method
    pattern = r'(    def get_lyrics\(self.*?)(?=\n    def |\nclass |\Z)'

    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print("Error: Could not find get_lyrics method in file.")
        return False

    # Replace the old method with the new one
    new_content = content[:match.start()] + NEW_GET_LYRICS + content[match.end():]

    # Backup original
    with open(filepath + ".bak", "w") as f:
        f.write(content)
    print(f"Backup saved to {filepath}.bak")

    # Write patched file
    with open(filepath, "w") as f:
        f.write(new_content)

    print(f"Successfully patched {filepath}")
    print("New get_lyrics method now supports timed lyrics!")
    return True

if __name__ == "__main__":
    patch_file()
