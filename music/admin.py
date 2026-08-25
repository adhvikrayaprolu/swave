from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User,
    Track,
    SwipeEvent,
    Playlist,
    PlaylistItem,
    UserProfile,
    ProviderToken
)

# ---------------------------
# User Management
# ---------------------------
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "is_staff", "is_active", "date_joined")
    search_fields = ("username", "email")
    ordering = ("-date_joined",)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "total_swipes", "total_likes", "total_rejects", "updated_at")
    search_fields = ("user__username",)
    list_filter = ("auto_play_previews",)

@admin.register(ProviderToken)
class ProviderTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "expires_at", "created_at")
    list_filter = ("provider",)
    search_fields = ("user__username", "provider")

# ---------------------------
# Music Data
# ---------------------------
@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ("title", "artist", "provider", "created_at")
    search_fields = ("title", "artist", "provider")
    list_filter = ("provider",)

@admin.register(SwipeEvent)
class SwipeEventAdmin(admin.ModelAdmin):
    list_display = ("user", "track", "action", "played_ms", "created_at")
    list_filter = ("action",)
    search_fields = ("user__username", "track__title")

@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "date", "created_at")
    search_fields = ("user__username", "name")

@admin.register(PlaylistItem)
class PlaylistItemAdmin(admin.ModelAdmin):
    list_display = ("playlist", "track", "position")
    list_filter = ("playlist",)