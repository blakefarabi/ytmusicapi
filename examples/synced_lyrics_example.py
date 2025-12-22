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
