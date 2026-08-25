from django.urls import path
from music import views
from .views import (
    test_itunes,
    register,
    login_view,
    refresh_token,
    profile,
    update_profile,
    logout,
    verify_firebase_token_view,

    # music / swipe / playlist
    swipe,
    likes,
    build_daily_playlist,
    get_daily_playlist,

    # feed / recommendation style
    feed_next,
    swipe_event,

    # spotify related
    spotify_login,
    spotify_callback,
    spotify_sync_likes, 
    spotify_test_playlist,
    spotify_test_playlist_browser,
    spotify_likes_debug,
)

urlpatterns = [
    path("test-itunes/", test_itunes),

    # Authentication
    path("auth/register/", register, name="register"),
    path("auth/login/", login_view, name="login"),
    path("auth/refresh/", refresh_token, name="refresh"),
    path("auth/logout/", logout, name="logout"),
    path("auth/verify-firebase/", verify_firebase_token_view, name="verify_firebase"),
    
    # User profile
    path("auth/profile/", profile, name="profile"),
    path("auth/profile/update/", update_profile, name="update_profile"),

    # Music interactions on the app
    path("swipes/", swipe),
    path("likes/", likes),
    path("playlist/daily/build/", build_daily_playlist),
    path("playlist/daily/", get_daily_playlist),

    
    path("api/feed/next", feed_next),
    path("api/feed/next/", feed_next),

    path("api/event/swipe", swipe_event),
    path("api/event/swipe/", swipe_event),


    # spotify
    path("auth/spotify/login", spotify_login, name="spotify_login"),
    path("auth/spotify/callback", spotify_callback, name="spotify_callback"),
    path("api/spotify/sync-likes", spotify_sync_likes, name="spotify_sync_likes"),
    path("spotify/test-playlist/", spotify_test_playlist),
    path("spotify/test-playlist-browser/", spotify_test_playlist_browser),
    path("api/spotify/liked-debug", spotify_likes_debug, name="spotify_likes_debug"),
    path("api/spotify/recommend-next", views.spotify_recommend_next),

]
from django.http import JsonResponse

def __ping(request):
    return JsonResponse({"ok": True, "loaded": "music.urls"})
urlpatterns += [path("__ping__", __ping)]


