from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.conf import settings
import json


class User(AbstractUser):
    """Custom User model"""
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # User preferences
    display_name = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.username or self.email


class ProviderToken(models.Model):
    """Store OAuth tokens for music providers (Spotify, Apple Music, etc.)"""
    PROVIDER_CHOICES = [
        ('spotify', 'Spotify'),
        ('apple', 'Apple Music'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='provider_tokens')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)

    # OAuth tokens
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True, null=True)
    token_type = models.CharField(max_length=50, default='Bearer')
    expires_at = models.DateTimeField()

    # Provider-specific data
    provider_user_id = models.CharField(max_length=100, blank=True)
    scope = models.TextField(blank=True)  # JSON string of granted scopes

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'provider']

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def get_scopes(self):
        """Parse scope JSON string into list"""
        if not self.scope:
            return []
        try:
            return json.loads(self.scope)
        except json.JSONDecodeError:
            return []

    def set_scopes(self, scopes):
        """Set scopes as JSON string"""
        self.scope = json.dumps(scopes)

    def __str__(self):
        return f"{self.user.username} - {self.provider}"


class UserTrackLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='liked_tracks')
    provider = models.CharField(max_length=32)  # 'spotify' | 'apple' | 'internal'
    provider_track_id = models.CharField(max_length=128)
    added_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = (('user', 'provider', 'provider_track_id'),)
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['provider', 'provider_track_id']),
        ]


class UserProfile(models.Model):
    """Extended user profile information"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    # Music preferences
    favorite_genres = models.JSONField(default=list, blank=True)
    favorite_artists = models.JSONField(default=list, blank=True)

    # App settings
    auto_play_previews = models.BooleanField(default=True)
    swipe_sensitivity = models.FloatField(default=0.5)  # 0.0 to 1.0

    # Statistics
    total_swipes = models.PositiveIntegerField(default=0)
    total_likes = models.PositiveIntegerField(default=0)
    total_rejects = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


# Music-related data models

class Track(models.Model):
    # external_id = ID from the iTunes API (or other provider)
    external_id = models.CharField(max_length=100, unique=True)

    title = models.CharField(max_length=255)
    artist = models.CharField(max_length=255)

    # preview/audio + artwork
    preview_url = models.URLField(blank=True, null=True)
    artwork = models.URLField(blank=True, null=True)

    # provider/source metadata
    source = models.CharField(max_length=50, default="itunes")
    duration_ms = models.IntegerField(blank=True, null=True)

    # compatibility fields used across the app
    album_art_url = models.URLField(blank=True, null=True)
    provider = models.CharField(max_length=32, default="itunes")
    provider_track_id = models.CharField(max_length=64, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["provider", "provider_track_id"]),
        ]
        unique_together = (("provider", "provider_track_id"),)

    def __str__(self):
        return f"{self.artist} - {self.title}"


class SwipeEvent(models.Model):
    ACTION_CHOICES = [
        ('like', 'Like'),
        ('dislike', 'Dislike'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='swipes')
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='swipes')
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    played_ms = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} {self.action}d {self.track.title}"


class Playlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='playlists')
    name = models.CharField(max_length=100)
    date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class PlaylistItem(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='items')
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    position = models.IntegerField(default=0)

    class Meta:
        unique_together = ('playlist', 'track')