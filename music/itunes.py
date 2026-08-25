import requests

def itunes_song_search(query):
    url = "https://itunes.apple.com/search"
    params = {
        "term": query,
        "country": "US",
        "media": "music",
        "entity": "song",
        "limit": 10,
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    results = []
    for song in data.get("results", []):
        preview = song.get("previewUrl")
        if preview:
            artwork_val = (
                song.get("artworkUrl100")
                or song.get("artworkUrl60")
                or song.get("artworkUrl30")
                or ""
            )

            results.append({
                "external_id": str(song.get("trackId")),
                "title": song.get("trackName"),
                "artist": song.get("artistName"),

                "preview_url": preview,
                "artwork": artwork_val,
                "source": "itunes",
                "duration_ms": song.get("trackTimeMillis"),

                "preview": preview,
                "album_art_url": artwork_val,
            })
    return results