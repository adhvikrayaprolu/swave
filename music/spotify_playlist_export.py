import requests
from .models import ProviderToken


SPOTIFY_API = "https://api.spotify.com/v1"


def get_spotify_token(user):
    """
    Returns a valid Spotify access token for the user.
    Refreshes automatically using your existing logic (_ensure_access_token).
    """
    from .spotify_views import _ensure_access_token

    token = _ensure_access_token(user)
    if not token:
        raise ValueError("Spotify not connected for this user.")

    return token


def create_spotify_playlist(user, name, track_uris):
    """
    Creates a private playlist and adds tracks; provider failures propagate.

    No automatic retries: a failed track write may leave an empty remote playlist.
    This is an internal helper, not a public export API.
    """
    access_token = get_spotify_token(user)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    token_row = ProviderToken.objects.get(user=user, provider="spotify")
    spotify_user_id = token_row.provider_user_id

    payload = {
        "name": name,
        "description": "Created by Swave playlist export test.",
        "public": False,
    }

    playlist_response = requests.post(
        f"{SPOTIFY_API}/users/{spotify_user_id}/playlists",
        headers=headers,
        json=payload,
        timeout=15,
    )
    playlist_response.raise_for_status()
    playlist = playlist_response.json()

    playlist_id = playlist["id"]

    tracks_response = requests.post(
        f"{SPOTIFY_API}/playlists/{playlist_id}/tracks",
        headers=headers,
        json={"uris": track_uris},
        timeout=15,
    )

    tracks_response.raise_for_status()

    return playlist
