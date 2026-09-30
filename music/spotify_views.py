import random
import secrets
from django.db import transaction
from django.db.models import F
from .services import record_swipe, build_playlist, validate_played
from django.utils.timezone import now

from rest_framework.decorators import api_view, permission_classes
from .services import provider_errors
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import UserTrackLike, Track
from django.shortcuts import redirect
from django.conf import settings
import math
from collections import Counter
from django.contrib.auth import login as dj_login



FRONTEND_URL = getattr(settings, "FRONTEND_URL", "http://localhost:8080")

from .itunes import itunes_song_search
from .models import (
    User,
    Track,
    SwipeEvent,
    Playlist,
    PlaylistItem,
    UserProfile,
    ProviderToken,
    UserTrackLike,
)
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    UserWithProvidersSerializer,
    TrackSerializer,
    SwipeSerializer,
    PlaylistSerializer,
)

from . import reccomendations as ph



# Firebase Admin SDK initialization (graceful fallback if not configured)
try:
    from .firebase_config import verify_firebase_token
    FIREBASE_ENABLED = True
except ImportError:
    FIREBASE_ENABLED = False
    verify_firebase_token = None

import base64
import datetime
import json
import requests
from urllib.parse import urlencode

from django.conf import settings
from django.utils import timezone
from django.shortcuts import redirect

from .spotify_playlist_export import create_spotify_playlist

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API = "https://api.spotify.com/v1"


import math
from math import sqrt
# --- Genre + label quantification helpers ---

GENRE_POSITION = {
    # very rough examples – tweak later as you like
    "hip hop": 0.15,
    "rap": 0.17,
    "trap": 0.18,
    "r&b": 0.25,
    "soul": 0.27,
    "pop": 0.50,
    "dance pop": 0.55,
    "edm": 0.65,
    "house": 0.68,
    "techno": 0.72,
    "rock": 0.40,
    "alt rock": 0.42,
    "indie rock": 0.45,
    "metal": 0.10,
    "k-pop": 0.52,
    "latin": 0.35,
}

MAJOR_KEYWORDS = [
    "universal", "sony", "warner", "atlantic", "columbia",
    "republic", "rca", "def jam", "interscope", "island",
]

#helpers for our reco algo

def dot(a, b): 
    return sum(x * y for x, y in zip(a, b))

def norm(a): 
    return math.sqrt(sum(x * x for x in a)) or 1.0

def cosine_sim(a, b):
    return dot(a, b) / (norm(a) * norm(b))

def average_vectors(vectors):
    n = len(vectors)
    if n == 0:
        return None
    dim = len(vectors[0])
    acc = [0.0] * dim
    for v in vectors:
        for i, x in enumerate(v):
            acc[i] += x
    return [x / n for x in acc]




def compute_genre_position(genres):
    """
    Map a list of genre strings to a single scalar in [0,1].
    We average over any genres we know, otherwise default 0.5.
    """
    if not genres:
        return 0.5
    vals = []
    for g in genres:
        low = g.lower()
        # try exact match
        if low in GENRE_POSITION:
            vals.append(GENRE_POSITION[low])
        else:
            # fuzzy-ish: check if any known key is contained
            for key, pos in GENRE_POSITION.items():
                if key in low:
                    vals.append(pos)
                    break
    if not vals:
        return 0.5
    return sum(vals) / len(vals)


def compute_label_score(label: str) -> float:
    """
    1.0 = clearly major label
    0.0 = indie/other
    0.5 = unknown
    """
    if not label:
        return 0.5
    low = label.lower()
    if any(k in low for k in MAJOR_KEYWORDS):
        return 1.0
    return 0.0





@api_view(["GET"])
@permission_classes([AllowAny])  # flip to AllowAny after demo
def spotify_login(request):
    if not settings.SPOTIFY_CLIENT_ID or not settings.SPOTIFY_CLIENT_SECRET:
        return Response({"error": "Spotify is not configured"}, status=503)
    state = secrets.token_urlsafe(32)
    request.session['spotify_oauth_state'] = state
    params = {"state": state,
        "client_id": settings.SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
        "scope": settings.SPOTIFY_SCOPES,
        "show_dialog": "true",
    }
    return redirect(f"{SPOTIFY_AUTH_URL}?{urlencode(params)}")


@api_view(["GET"])
@permission_classes([AllowAny])  # flip to AllowAny after demo
@provider_errors
def spotify_callback(request):
    expected = request.session.pop('spotify_oauth_state', None)
    supplied = request.GET.get('state', '')
    if not expected or not secrets.compare_digest(expected, supplied):
        return Response({"error": "Invalid or expired OAuth state"}, status=400)
    code = request.GET.get("code")
    if not code:
        return Response({"error": "missing_code"}, status=400)

    basic = base64.b64encode(
        f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}".encode()
    ).decode()

    resp = requests.post(
        SPOTIFY_TOKEN_URL,
        data={"grant_type": "authorization_code", "code": code, "redirect_uri": settings.SPOTIFY_REDIRECT_URI},
        headers={"Authorization": f"Basic {basic}"},
        timeout=15,
    )
    if resp.status_code != 200:
        return Response({"error": "token_exchange_failed", "detail": "Provider request failed"}, status=400)

    tok = resp.json()
    access = tok["access_token"]
    refresh = tok.get("refresh_token")
    expires_at = timezone.now() + datetime.timedelta(seconds=tok.get("expires_in", 3600))

    me = requests.get(f"{SPOTIFY_API}/me", headers={"Authorization": f"Bearer {access}"}, timeout=15)
    if me.status_code != 200:
        return Response({"error": "me_failed", "detail": "Provider request failed"}, status=400)
    spotify_user_id = me.json()["id"]

    me_json = me.json()
    spotify_user_id = me_json["id"]
    spotify_email = me_json.get("email") or f"{spotify_user_id}@spotify.local"
    spotify_display_name = me_json.get("display_name") or spotify_user_id

    # Create/get a real Django user tied to this Spotify identity
    user, created = User.objects.get_or_create(
        username=f"sp_{spotify_user_id}",
        defaults={
            "email": spotify_email,
            "display_name": spotify_display_name,
        },
    )

    # Keep them updated on every login
    updated = False
    if user.email != spotify_email:
        user.email = spotify_email
        updated = True
    if user.display_name != spotify_display_name:
        user.display_name = spotify_display_name
        updated = True
    if updated:
        user.save()

    # Ensure UserProfile row exists
    UserProfile.objects.get_or_create(user=user)


    scopes = settings.SPOTIFY_SCOPES.split()

    ProviderToken.objects.update_or_create(
        user=user, provider="spotify",
        defaults={
            "access_token": access,
            "refresh_token": refresh,
            "token_type": tok.get("token_type", "Bearer"),
            "expires_at": expires_at,
            "provider_user_id": spotify_user_id,
            "scope": json.dumps(scopes),
        },
    )

    user.backend = "django.contrib.auth.backends.ModelBackend"
    dj_login(request, user)
    return redirect(f"{FRONTEND_URL}/connect-spotify")

def _ensure_access_token(user):
    tok = ProviderToken.objects.filter(user=user, provider="spotify").first()
    if not tok:
        return None
    if tok.expires_at <= timezone.now() + datetime.timedelta(seconds=30) and tok.refresh_token:
        basic = base64.b64encode(
            f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}".encode()
        ).decode()
        r = requests.post(
            SPOTIFY_TOKEN_URL,
            data={"grant_type": "refresh_token", "refresh_token": tok.refresh_token},
            headers={"Authorization": f"Basic {basic}"},
            timeout=15,
        )
        if r.status_code == 200:
            j = r.json()
            tok.access_token = j["access_token"]
            if "refresh_token" in j:
                tok.refresh_token = j["refresh_token"]
            tok.expires_at = timezone.now() + datetime.timedelta(seconds=j.get("expires_in", 3600))
            tok.token_type = j.get("token_type", tok.token_type)
            tok.save()
        else:
            return None
    return tok.access_token


def _upsert_saved_track(user, saved_item):
    track = saved_item["track"]
    tid = track["id"]
    title = track["name"]
    artists = ", ".join(a["name"] for a in track["artists"]) or ""
    album_art = (track.get("album", {}).get("images") or [{}])[0].get("url")
    preview = track.get("preview_url")

    # Upsert Track row
    Track.objects.update_or_create(
        provider="spotify", provider_track_id=tid,
        defaults={
            "external_id": tid,
            "title": title,
            "artist": artists,
            "album_art_url": album_art,
            "preview_url": preview,
        },
    )

    # Upsert UserTrackLike
    added_at = saved_item.get("added_at")
    dt = None
    if added_at:
        try:
            dt = datetime.datetime.fromisoformat(added_at.replace("Z", "+00:00"))
        except Exception:
            pass

    UserTrackLike.objects.update_or_create(
        user=user, provider="spotify", provider_track_id=tid,
        defaults={"added_at": dt},
    )

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@provider_errors
def spotify_sync_likes(request):
    user = request.user
    access = _ensure_access_token(user)
    if not access:
        return Response({"error": "not_connected"}, status=400)

    headers = {"Authorization": f"Bearer {access}"}
    url = f"{SPOTIFY_API}/me/tracks?limit=50"
    total = 0

    while url:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            return Response({"error": "spotify_failed", "detail": "Provider request failed"}, status=400)
        j = r.json()
        for item in j.get("items", []):
            _upsert_saved_track(user, item)
            total += 1
        url = j.get("next")  # Spotify gives a full URL for pagination

    return Response({"ok": True, "imported": total})









# itunes test endpoint


# auth / profile / session














# music interactions using the relational DB








@api_view(["GET"])
@permission_classes([IsAuthenticated])
@provider_errors
def spotify_likes_debug(request):
    """
    Return user's liked Spotify tracks (from DB) + numeric metadata
    we can use as a feature vector for recommendations.

    For now, we compute features for the first 2 liked tracks using:
    - track popularity (raw + scaled)
    - explicit flag
    - release year (raw + scaled)
    - duration (raw ms + scaled)
    - artist popularity (raw + scaled)
    - artist followers (raw + scaled log)
    - genre_position (scalar) from artist genres
    - label_score (major vs indie-ish)
    """
    user = request.user

    # 1) Get liked tracks from our DB
    likes_qs = (
        UserTrackLike.objects
        .filter(user=user, provider="spotify")
        .order_by("-added_at")
    )
    likes = list(likes_qs[:20])  # cap for now

    track_ids = [l.provider_track_id for l in likes]
    tracks = Track.objects.filter(
        provider="spotify",
        provider_track_id__in=track_ids,
    )
    track_map = {t.provider_track_id: t for t in tracks}

    track_items = []
    for l in likes:
        t = track_map.get(l.provider_track_id)
        track_items.append({
            "id": l.provider_track_id,
            "title": getattr(t, "title", None),
            "artist": getattr(t, "artist", None),
            "album_art_url": getattr(t, "album_art_url", None),
            "preview_url": getattr(t, "preview_url", None),
            "added_at": l.added_at.isoformat() if l.added_at else None,
        })

    # 2) Build meta_features for the first 2 tracks via Spotify /tracks + /artists
    meta_features = []
    first_ids = track_ids[:2]

    access = _ensure_access_token(user)
    if access and first_ids:
        headers = {"Authorization": f"Bearer {access}"}

        # --- Fetch detailed track data ---
        r_tracks = requests.get(
            f"{SPOTIFY_API}/tracks",
            headers=headers,
            params={"ids": ",".join(first_ids)},
            timeout=15,
        )
        print("DEBUG /tracks status:", r_tracks.status_code)
        if r_tracks.status_code == 200:
            tracks_data = r_tracks.json().get("tracks") or []

            # Collect primary artist IDs for these tracks
            artist_ids = []
            for t in tracks_data:
                artists = t.get("artists") or []
                if artists:
                    artist_ids.append(artists[0].get("id"))
            # de-duplicate
            artist_ids = [a for a in dict.fromkeys(artist_ids) if a]

            artist_map = {}
            if artist_ids:
                r_artists = requests.get(
                    f"{SPOTIFY_API}/artists",
                    headers=headers,
                    params={"ids": ",".join(artist_ids)},
                    timeout=15,
                )
                print("DEBUG /artists status:", r_artists.status_code)
                if r_artists.status_code == 200:
                    for a in r_artists.json().get("artists") or []:
                        if a and a.get("id"):
                            artist_map[a["id"]] = a

            # --- Build meta_features per track ---
            for t in tracks_data:
                if t is None:
                    continue
                tid = t.get("id")
                if not tid:
                    continue

                # Track-level
                popularity = t.get("popularity", 0) or 0
                popularity_scaled = popularity / 100.0

                explicit_flag = 1 if t.get("explicit") else 0

                duration_ms = t.get("duration_ms") or 0
                # assume 0–8 minutes window for scaling
                max_duration_ms = 8 * 60 * 1000
                duration_scaled = min(
                    max(duration_ms / max_duration_ms, 0.0),
                    1.0
                )

                # Album / year / label
                album_obj = t.get("album") or {}
                raw_date = album_obj.get("release_date")
                release_year = None
                release_year_scaled = None
                if raw_date:
                    try:
                        release_year = int(raw_date.split("-")[0])
                        base = 1960
                        max_year = 2025
                        ry = (release_year - base) / float(max_year - base)
                        release_year_scaled = min(max(ry, 0.0), 1.0)
                    except Exception:
                        pass

                label = album_obj.get("label") or ""
                label_score = compute_label_score(label)

                # Artist-level
                artists = t.get("artists") or []
                primary_artist = artists[0] if artists else None

                artist_popularity_raw = None
                artist_popularity_scaled = None
                artist_followers_raw = None
                artist_followers_scaled = None
                genre_position = None
                genres = []

                if primary_artist and primary_artist.get("id"):
                    aid = primary_artist["id"]
                    a_data = artist_map.get(aid)
                    if a_data:
                        artist_popularity_raw = a_data.get("popularity", 0) or 0
                        artist_popularity_scaled = artist_popularity_raw / 100.0

                        followers_obj = a_data.get("followers") or {}
                        artist_followers_raw = followers_obj.get("total") or 0
                        # log-scale, assume ~10^7 as top-tier-ish
                        artist_followers_scaled = (
                            math.log10(artist_followers_raw + 1) / 7.0
                        )

                        genres = a_data.get("genres") or []
                        genre_position = compute_genre_position(genres)

                meta_features.append({
                    "id": tid,

                    # raw values
                    "popularity_raw": popularity,
                    "explicit": explicit_flag,
                    "release_year": release_year,
                    "duration_ms": duration_ms,
                    "artist_popularity_raw": artist_popularity_raw,
                    "artist_followers_raw": artist_followers_raw,
                    "label": label or None,
                    "genres": genres,

                    # scaled / numeric vector fields
                    "popularity_scaled": popularity_scaled,
                    "is_explicit": float(explicit_flag),
                    "release_year_scaled": release_year_scaled,
                    "duration_scaled": duration_scaled,
                    "artist_popularity_scaled": artist_popularity_scaled,
                    "artist_followers_scaled": artist_followers_scaled,
                    "genre_position": genre_position,
                    "label_score": label_score,
                })
        else:
            print("SPOTIFY /tracks error:", r_tracks.status_code, repr(r_tracks.text[:400]))

    return Response({
        "tracks": track_items,
        "meta_features": meta_features,
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
@provider_errors
def spotify_recommend_next(request):
    """
    Search-based recommendations:

    1. Use user's Spotify likes to build a 'vibe vector' from track/artist metadata.
    2. Derive search queries from the user's top genres + era.
    3. Use Spotify /search to fetch candidate tracks.
    4. Build feature vectors for candidates and rank by cosine similarity.
    5. Return top 10 tracks with similarity scores.
    """
    user = request.user

    # --- Step 0: fetch likes from our DB --------------------------------------
    likes_qs = (
        UserTrackLike.objects
        .filter(user=user, provider="spotify")
        .order_by("-added_at")
    )
    likes = list(likes_qs[:50])  # up to 50 likes for now

    if not likes:
        return Response({"error": "no_likes"}, status=400)

    liked_ids_raw = [l.provider_track_id for l in likes if l.provider_track_id]
    liked_ids_raw = list(dict.fromkeys(liked_ids_raw))  # de-dupe

    if not liked_ids_raw:
        return Response({"error": "no_valid_liked_ids"}, status=400)

    # Some apps accidentally store "spotify:track:<id>" URIs; normalize.
    def normalize_spotify_track_id(s: str) -> str:
        if s.startswith("spotify:track:"):
            return s.split(":")[-1]
        return s

    liked_ids = [normalize_spotify_track_id(tid) for tid in liked_ids_raw]

    access = _ensure_access_token(user)
    if not access:
        return Response({"error": "not_connected"}, status=400)

    headers = {"Authorization": f"Bearer {access}"}

    # --- Step 1: Build user 'vibe' vector from liked tracks -------------------
    # Use at most 20 liked tracks for the profile.
    liked_for_vec = liked_ids[:20]

    r_tracks = requests.get(
        f"{SPOTIFY_API}/tracks",
        headers=headers,
        params={"ids": ",".join(liked_for_vec)},
        timeout=15,
    )
    if r_tracks.status_code != 200:
        print("SPOTIFY /tracks (liked) error:", r_tracks.status_code, r_tracks.text[:400])
        return Response({"error": "spotify_tracks_failed"}, status=502)

    liked_tracks_data = r_tracks.json().get("tracks") or []

    # Collect primary artist IDs for liked tracks
    liked_artist_ids = []
    for t in liked_tracks_data:
        artists = t.get("artists") or []
        if artists:
            aid = artists[0].get("id")
            if aid:
                liked_artist_ids.append(aid)
    liked_artist_ids = list(dict.fromkeys(liked_artist_ids))

    artist_map = {}
    if liked_artist_ids:
        r_artists = requests.get(
            f"{SPOTIFY_API}/artists",
            headers=headers,
            params={"ids": ",".join(liked_artist_ids)},
            timeout=15,
        )
        if r_artists.status_code == 200:
            for a in r_artists.json().get("artists") or []:
                if a and a.get("id"):
                    artist_map[a["id"]] = a
        else:
            print("SPOTIFY /artists (liked) error:",
                  r_artists.status_code, r_artists.text[:400])

    # For building user profile stats (top genres, era)
    genre_counts: Counter[str] = Counter()
    years: list[int] = []

    def build_vector_from_track(track_obj, artist_obj, update_profile: bool = False):
        """
        Turn (track, artist) into our numeric vector.
        If update_profile=True, also update genre_counts and years for the user profile.
        """
        if track_obj is None:
            return None

        # Track-level
        popularity = track_obj.get("popularity", 0) or 0
        popularity_scaled = popularity / 100.0

        explicit_flag = 1 if track_obj.get("explicit") else 0

        duration_ms = track_obj.get("duration_ms") or 0
        max_duration_ms = 8 * 60 * 1000  # 8 min cap
        duration_scaled = min(max(duration_ms / max_duration_ms, 0.0), 1.0)

        # Album info
        album_obj = track_obj.get("album") or {}
        raw_date = album_obj.get("release_date")
        release_year = None
        release_year_scaled = None
        if raw_date:
            try:
                release_year = int(raw_date.split("-")[0])
                base = 1960
                max_year = 2025
                ry = (release_year - base) / float(max_year - base)
                release_year_scaled = min(max(ry, 0.0), 1.0)
            except Exception:
                pass

        label = album_obj.get("label") or ""
        label_score = compute_label_score(label)

        # Artist-level
        artist_popularity_scaled = None
        artist_followers_scaled = None
        genre_position = None
        artist_genres = []

        if artist_obj:
            ap_raw = artist_obj.get("popularity", 0) or 0
            artist_popularity_scaled = ap_raw / 100.0

            followers_obj = artist_obj.get("followers") or {}
            followers_raw = followers_obj.get("total") or 0
            artist_followers_scaled = math.log10(followers_raw + 1) / 7.0

            artist_genres = artist_obj.get("genres") or []
            genre_position = compute_genre_position(artist_genres)

        # Update profile stats (genres + era)
        if update_profile:
            if artist_genres:
                for g in artist_genres:
                    genre_counts[g.lower()] += 1
            if release_year:
                years.append(release_year)

        # Final numeric vector (order matters!)
        vec = [
            popularity_scaled or 0.5,
            float(explicit_flag),  # 0.0 or 1.0
            release_year_scaled if release_year_scaled is not None else 0.5,
            duration_scaled,
            artist_popularity_scaled if artist_popularity_scaled is not None else 0.5,
            artist_followers_scaled if artist_followers_scaled is not None else 0.5,
            genre_position if genre_position is not None else 0.5,
            label_score,
        ]
        return vec

    liked_vectors = []
    for t in liked_tracks_data:
        if t is None:
            continue
        artists = t.get("artists") or []
        primary_artist = artists[0] if artists else None
        a_obj = artist_map.get(primary_artist["id"]) if primary_artist and primary_artist.get("id") else None
        vec = build_vector_from_track(t, a_obj, update_profile=True)
        if vec is not None:
            liked_vectors.append(vec)

    if not liked_vectors:
        return Response({"error": "no_featured_likes"}, status=400)

    user_vec = average_vectors(liked_vectors)

    # --- Step 2: Derive search queries from user profile ----------------------
    def build_search_queries_from_profile(
        genre_counts: Counter[str],
        years: list[int],
        max_queries: int = 4,
    ) -> list[str]:
        queries: list[str] = []

        if genre_counts:
            top_genres = [g for g, _ in genre_counts.most_common(3)]
        else:
            top_genres = []

        if years:
            min_year = max(min(years) - 2, 1960)
            max_year = min(max(years) + 2, 2025)
        else:
            min_year, max_year = 2000, 2025

        for g in top_genres:
            g_clean = g.replace('"', "")
            q = f'genre:"{g_clean}" year:{min_year}-{max_year}'
            queries.append(q)
            if len(queries) >= max_queries:
                break

        # Fallback if we have no genres
        if not queries:
            queries.append(f"year:{min_year}-{max_year}")

        return queries

    search_queries = build_search_queries_from_profile(genre_counts, years)

    # --- Step 3: Use Spotify /search to get candidate tracks ------------------
    candidate_tracks: dict[str, dict] = {}

    for q in search_queries:
        r_search = requests.get(
            f"{SPOTIFY_API}/search",
            headers=headers,
            params={
                "q": q,
                "type": "track",
                "limit": 25,
                "market": "US",
            },
            timeout=15,
        )
        if r_search.status_code != 200:
            print("SPOTIFY /search error:", r_search.status_code, r_search.text[:200])
            continue

        items = (r_search.json()
                 .get("tracks", {})
                 .get("items", []))
        for item in items:
            tid = item.get("id")
            if not tid:
                continue
            if tid in candidate_tracks:
                continue
            if tid in liked_ids:
                # avoid recommending something they already liked
                continue
            candidate_tracks[tid] = item

    if not candidate_tracks:
        return Response({"error": "no_candidates"}, status=404)

    # --- Step 4: Fetch artist info for candidates -----------------------------
    cand_artist_ids: list[str] = []
    for t in candidate_tracks.values():
        artists = t.get("artists") or []
        if artists:
            aid = artists[0].get("id")
            if aid:
                cand_artist_ids.append(aid)
    cand_artist_ids = list(dict.fromkeys(cand_artist_ids))

    cand_artist_map: dict[str, dict] = {}

    # /artists supports up to 50 IDs per call, so chunk if necessary
    for i in range(0, len(cand_artist_ids), 50):
        chunk = cand_artist_ids[i : i + 50]
        r_cand_artists = requests.get(
            f"{SPOTIFY_API}/artists",
            headers=headers,
            params={"ids": ",".join(chunk)},
            timeout=15,
        )
        if r_cand_artists.status_code == 200:
            for a in r_cand_artists.json().get("artists") or []:
                if a and a.get("id"):
                    cand_artist_map[a["id"]] = a
        else:
            print("SPOTIFY /artists (candidates) error:",
                  r_cand_artists.status_code, r_cand_artists.text[:200])

    scored = []
    for tid, t in candidate_tracks.items():
        if t is None:
            continue

        artists = t.get("artists") or []
        primary_artist = artists[0] if artists else None
        a_obj = (
            cand_artist_map.get(primary_artist["id"])
            if primary_artist and primary_artist.get("id")
            else None
        )

        vec = build_vector_from_track(t, a_obj, update_profile=False)
        if vec is None:
            continue

        sim = cosine_sim(user_vec, vec)

        album_obj = t.get("album") or {}
        images = album_obj.get("images") or []
        preview_url = t.get("preview_url")
        album_art_url = images[0]["url"] if images else None

        if not preview_url:
            res = itunes_song_search(f"{t.get('name','')} {', '.join(a.get('name','') for a in (t.get('artists') or []))}")
            if res:
                preview_url = res[0].get("preview_url") or preview_url
                album_art_url = res[0].get("artwork") or album_art_url


        scored.append({
            "id": tid,
            "title": t.get("name"),
            "artist": ", ".join(
                a.get("name")
                for a in (t.get("artists") or [])
                if a.get("name")
            ),
            "album_art_url": album_art_url,
            "preview_url": t.get("preview_url"),
            "similarity": sim,
        })

    if not scored:
        return Response({"error": "no_scored_candidates"}, status=404)

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    top_k = scored[:10]

    return Response({"recommendations": top_k})
