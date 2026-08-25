# music/recommendations.py

from math import sqrt

# ---------- low-level math helpers ----------------

def dot(a, b):
    return sum(x * y for x, y in zip(a, b))

def norm(a):
    n = sqrt(sum(x * x for x in a))
    return n if n != 0 else 1.0

def cosine_sim(a, b):
    return dot(a, b) / (norm(a) * norm(b))

def average_vectors(vectors):
    if not vectors:
        return None
    dim = len(vectors[0])
    avg = [0.0] * dim
    for v in vectors:
        for i, x in enumerate(v):
            avg[i] += x
    return [x / len(vectors) for x in avg]

# ---------- feature extraction for Spotify tracks ---------

def _scale_01(x, lo, hi, default=0.5):
    """Safely scale x ∈ [lo, hi] to [0,1]."""
    if x is None:
        return default
    if hi == lo:
        return default
    val = (x - lo) / (hi - lo)
    return max(0.0, min(1.0, val))

def vector_from_spotify_track(track_obj):
    """
    track_obj: full Spotify Track object from /v1/tracks or /v1/recommendations.
    Returns a numeric feature vector.
    """

    # 1. Track popularity (0–100)
    popularity_raw = track_obj.get("popularity", 50)
    popularity_scaled = _scale_01(popularity_raw, 0, 100, default=0.5)

    # 2. Explicit flag
    is_explicit = 1.0 if track_obj.get("explicit") else 0.0

    # 3. Duration in minutes, clamp between 2 and 6 min
    duration_ms = track_obj.get("duration_ms") or 180_000  # default 3 min
    duration_min = duration_ms / 60000.0
    duration_scaled = _scale_01(duration_min, 2.0, 6.0, default=0.5)

    # 4. Release year
    album = track_obj.get("album") or {}
    raw_date = album.get("release_date")
    release_year = None
    if raw_date:
        try:
            release_year = int(raw_date.split("-")[0])
        except Exception:
            release_year = None
    # scale roughly from 1960–2025
    release_year_scaled = _scale_01(release_year, 1960, 2025, default=0.7)

    # (Later you can add genre_position, label_score, artist_popularity, etc.)

    return [
        popularity_scaled,
        is_explicit,
        release_year_scaled,
        duration_scaled,
    ]

# ---------- user + candidate recommender ------------------

def build_user_vector_from_liked_tracks(spotify_tracks):
    """
    spotify_tracks: list of full Spotify Track objects that the user likes.
    """
    vecs = [vector_from_spotify_track(t) for t in spotify_tracks]
    return average_vectors(vecs)

def rank_candidates_for_user(user_vec, candidate_tracks, k=10):
    """
    user_vec: numeric vibe vector for the user.
    candidate_tracks: list of Spotify Track objects to choose from.
    Returns top-k list of (score, track_obj).
    """
    scored = []
    for t in candidate_tracks:
        v = vector_from_spotify_track(t)
        s = cosine_sim(user_vec, v)
        scored.append((s, t))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:k]
