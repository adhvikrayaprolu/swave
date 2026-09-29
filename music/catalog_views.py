from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.utils.timezone import now
from .models import Track, SwipeEvent, Playlist
from .serializers import SwipeSerializer, PlaylistSerializer
from .itunes import itunes_song_search
from .services import provider_errors, record_swipe, build_playlist, validate_played


@api_view(["GET"])
@permission_classes([AllowAny])
@provider_errors
def feed_next(request):
    """
    GET /api/feed/next?k=20&liked=id1,id2,...
    Return catalog tracks not yet swiped by the authenticated user.
    """
    try:
        k = int(request.query_params.get("k", 20))
        if not 1 <= k <= 50:
            raise ValueError
    except (TypeError, ValueError):
        return Response({"error": "k must be an integer from 1 to 50"}, status=400)
    qs = Track.objects.all()
    if request.user.is_authenticated:
        qs = qs.exclude(swipes__user=request.user)
    qs = qs.order_by("?")[:k]
    clips = [{"id": t.external_id, "title": t.title, "artist": t.artist,
              "album_art_url": t.album_art_url or t.artwork or "",
              "preview_url": t.preview_url or ""} for t in qs]

    return Response({"batch_id": None, "next_cursor": None, "clips": clips})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def swipe_event(request):
    """
    Record a swipe event. Will map direction->like/dislike and add the Track.

    Body:
    {
        "track_id": "1440843974",
        "direction": "right",  // "right" = like, "left" = dislike
        "played_ms": 8000
    }
    """
    data = request.data or {}
    track_id = data.get("track_id")
    direction = data.get("direction")

    if direction not in ("left", "right") or not track_id:
        return Response(
            {"error": "track_id and direction required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    track_obj = (Track.objects.filter(external_id=track_id).first()
                 or Track.objects.filter(provider_track_id=track_id).first())
    if not track_obj:
        return Response({"error": "Track not found"}, status=404)
    try:
        event = record_swipe(request.user, track_obj, 'like' if direction == 'right' else 'dislike', data.get('played_ms', 0))
    except ValueError as error:
        return Response({"error": str(error)}, status=400)
    return Response({"ok": True, "id": event.id}, status=201)


@api_view(["GET"])
@permission_classes([AllowAny])
@provider_errors
def test_itunes(request):
    q = request.GET.get("q")
    if not q:
        return Response({"error": "Missing 'q' query parameter"}, status=400)
    results = itunes_song_search(q)
    return Response(results)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def swipe(request):
    """
    This is for recording a like/dislike for the logged-in user using normalized Track rows.
    The body of the request should contain:
    {
        "action": "like" | "dislike",
        "played_ms": 12000,
        "track": {
            "external_id": "1440843974",
            "title": "Hotline Bling",
            "artist": "Drake",
            "preview_url": "https://....m4a",
            "artwork": "https://...100x100bb.jpg",
            "source": "itunes",
            "duration_ms": 267024
        }
    }
    """
    data = request.data
    track_data = data.get('track')
    action = data.get('action', 'like')
    try:
        played = validate_played(data.get('played_ms', 0))
        if action not in ('like', 'dislike') or not isinstance(track_data, dict):
            raise ValueError('Valid track and action required')
        for key in ('external_id', 'title', 'artist'):
            if not isinstance(track_data.get(key), str) or not track_data[key].strip():
                raise ValueError(f'{key} is required text')
        with transaction.atomic():
            track, _ = Track.objects.get_or_create(external_id=track_data['external_id'], defaults={
                'title': track_data['title'], 'artist': track_data['artist'],
                'preview_url': track_data.get('preview_url'), 'artwork': track_data.get('artwork'),
                'provider': track_data.get('source', 'itunes'), 'provider_track_id': track_data['external_id'],
            })
            event = record_swipe(request.user, track, action, played)
    except ValueError as error:
        return Response({'error': str(error)}, status=400)
    return Response(SwipeSerializer(event).data, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def likes(request):
    user = request.user

    qs = (
        SwipeEvent.objects
        .filter(user=user, action="like")
        .select_related("track")
        .order_by("-created_at")
    )
    return Response(SwipeSerializer(qs, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def build_daily_playlist(request):
    """Create/refresh today's playlist from today's likes."""
    playlist = build_playlist(request.user)
    return Response(PlaylistSerializer(playlist).data, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_daily_playlist(request):
    """Get today's daily playlist for the authenticated user."""
    user = request.user
    today = now().date()
    try:
        pl = Playlist.objects.get(user=user, date=today)
    except Playlist.DoesNotExist:
        return Response({"error": "no daily playlist yet"}, status=404)
    return Response(PlaylistSerializer(pl).data)



@api_view(["POST"])
@permission_classes([IsAuthenticated])
@provider_errors
def search_catalog(request):
    query = request.data.get("query", "")
    if not isinstance(query, str) or not 1 <= len(query.strip()) <= 100:
        return Response({"error": "Search must contain 1–100 characters"}, status=400)
    results = itunes_song_search(query.strip())
    with transaction.atomic():
        for result in results:
            Track.objects.update_or_create(external_id=result["external_id"], defaults={
                "title": result["title"], "artist": result["artist"],
                "preview_url": result["preview_url"], "artwork": result["artwork"],
                "album_art_url": result["artwork"], "provider": "itunes",
                "provider_track_id": result["external_id"], "duration_ms": result["duration_ms"],
            })
    return Response({"imported": len(results)})
