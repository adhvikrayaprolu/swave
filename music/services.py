"""Transactional core music operations and a safe external API error boundary."""
from functools import wraps
import requests
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.response import Response
from .models import UserProfile, SwipeEvent, Playlist, PlaylistItem


def provider_errors(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except requests.Timeout:
            return Response({'error': 'Music provider timed out. Please retry.'}, status=504)
        except (requests.RequestException, ValueError, KeyError):
            return Response({'error': 'Music provider returned an unavailable or invalid response.'}, status=502)
    return wrapped


def validate_played(value):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 3600000:
        raise ValueError('played_ms must be an integer from 0 to 3600000')
    return value


@transaction.atomic
def record_swipe(user, track, action, played_ms):
    played_ms = validate_played(played_ms)
    if action not in ('like', 'dislike'):
        raise ValueError('Invalid swipe action')
    profile, _ = UserProfile.objects.get_or_create(user=user)
    event = SwipeEvent.objects.create(user=user, track=track, action=action, played_ms=played_ms)
    updates = {'total_swipes': F('total_swipes') + 1}
    updates['total_likes' if action == 'like' else 'total_rejects'] = F('total_likes' if action == 'like' else 'total_rejects') + 1
    UserProfile.objects.filter(pk=profile.pk).update(**updates)
    return event


@transaction.atomic
def build_playlist(user):
    today = timezone.localdate()
    # Serialize per-user playlist builds. DB unique constraints protect item identity.
    UserProfile.objects.get_or_create(user=user)
    UserProfile.objects.select_for_update().get(user=user)
    playlist, _ = Playlist.objects.get_or_create(user=user, date=today,
        defaults={'name': f'Daily {today.isoformat()}'})
    ids = SwipeEvent.objects.filter(user=user, action='like', created_at__date=today).order_by('created_at').values_list('track_id', flat=True)
    unique_ids = list(dict.fromkeys(ids))
    playlist.items.all().delete()
    PlaylistItem.objects.bulk_create([PlaylistItem(playlist=playlist, track_id=tid, position=i) for i, tid in enumerate(unique_ids)])
    return playlist
