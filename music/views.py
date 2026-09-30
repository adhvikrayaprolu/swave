"""Compatibility exports; implementation lives in focused view modules."""
from .account_views import register, login_view, refresh_token, profile, update_profile, logout, verify_firebase_token_view
from .catalog_views import feed_next, swipe_event, test_itunes, swipe, likes, build_daily_playlist, get_daily_playlist
from .spotify_views import spotify_login, spotify_callback, spotify_sync_likes, spotify_likes_debug, spotify_recommend_next

from .catalog_views import search_catalog
