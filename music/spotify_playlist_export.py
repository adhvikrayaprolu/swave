import requests
from django.utils import timezone
from .models import ProviderToken


SPOTIFY_API = "https://api.spotify.com/v1"


def get_spotify_token(user):
    """
    Returns a valid Spotify access token for the user.
    Refreshes automatically using your existing logic (_ensure_access_token).
    """
    from .views import _ensure_access_token

    token = _ensure_access_token(user)
    if not token:
        raise Exception("Spotify not connected for this user.")

    return token


def create_spotify_playlist(user, name, track_uris):
    """
    Creates a playlist in the user's Spotify account and adds tracks.
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

    playlist = requests.post(
        f"{SPOTIFY_API}/users/{spotify_user_id}/playlists",
        headers=headers,
        json=payload,
        timeout=15,
    ).json()

    playlist_id = playlist["id"]

    requests.post(
        f"{SPOTIFY_API}/playlists/{playlist_id}/tracks",
        headers=headers,
        json={"uris": track_uris},
        timeout=15,
    )

    return playlist
