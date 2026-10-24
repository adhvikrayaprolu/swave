"""Offline contracts for the optional provider; unexpected HTTP always fails the test."""
import base64
import datetime
import json
from urllib.parse import parse_qs, urlsplit
from unittest.mock import call, patch

import requests
from django.conf import settings
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from .models import ProviderToken, User, UserProfile, UserTrackLike
from .spotify_playlist_export import create_spotify_playlist
from .spotify_views import SPOTIFY_API, SPOTIFY_TOKEN_URL


@override_settings(
    SPOTIFY_CLIENT_ID="offline-client",
    SPOTIFY_CLIENT_SECRET="offline-secret",
    SPOTIFY_REDIRECT_URI="http://127.0.0.1:8000/auth/spotify/callback",
    SPOTIFY_SCOPES="user-library-read playlist-modify-private",
)
class SpotifyContractTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username="alice", email="alice@example.test")
        cls.bob = User.objects.create_user(username="bob", email="bob@example.test")

    def setUp(self):
        # Protect even calls outside the expected GET/POST boundary from live HTTP.
        guard = patch("requests.sessions.Session.request", side_effect=AssertionError("Unexpected HTTP"))
        guard.start()
        self.addCleanup(guard.stop)
        for method in ("get", "post"):
            stub = patch(f"requests.{method}", side_effect=AssertionError(f"Unexpected {method}"))
            setattr(self, method, stub.start())
            self.addCleanup(stub.stop)

    @staticmethod
    def response(payload, status=200):
        response = requests.Response()
        response.status_code = status
        response._content = json.dumps(payload).encode()
        response.headers["Content-Type"] = "application/json"
        return response

    def replies(self, method, *responses):
        getattr(self, method).side_effect = list(responses)

    def start_login(self, client=None):
        client = client or self.client
        response = client.get("/auth/spotify/login")
        self.assertEqual(response.status_code, 302)
        query = parse_qs(urlsplit(response.url).query)
        self.assertEqual(query["client_id"], [settings.SPOTIFY_CLIENT_ID])
        self.assertEqual(query["redirect_uri"], [settings.SPOTIFY_REDIRECT_URI])
        self.assertEqual(query["response_type"], ["code"])
        self.assertEqual(query["scope"], [settings.SPOTIFY_SCOPES])
        state = query["state"][0]
        self.assertEqual(client.session["spotify_oauth_state"], state)
        return state

    def callback(self, state, client=None, **params):
        return (client or self.client).get(
            "/auth/spotify/callback", {"state": state, "code": "offline-code", **params}
        )

    def token(self, user=None, *, expires_in=3600, refresh="refresh-original"):
        user = user or self.alice
        return ProviderToken.objects.create(
            user=user, provider="spotify", provider_user_id=f"provider-{user.username}",
            access_token=f"access-{user.username}", refresh_token=refresh,
            expires_at=timezone.now() + datetime.timedelta(seconds=expires_in),
        )

    def sync(self, user=None):
        self.client.force_authenticate(user or self.alice)
        return self.client.post("/api/spotify/sync-likes", {}, format="json")

    def test_callback_consumes_state_logs_in_and_stores_only_provider_identity(self):
        state = self.start_login()
        before = timezone.now()
        self.replies("post", self.response({"access_token": "callback-access", "refresh_token": "callback-refresh", "expires_in": 1800}))
        self.replies("get", self.response({"id": "listener", "email": "listener@example.test", "display_name": "Listener"}))
        result = self.callback(state)
        self.assertEqual(result.status_code, 302)
        self.assertEqual(result.url, f"{settings.FRONTEND_URL}/connect-spotify")
        self.assertNotIn("spotify_oauth_state", self.client.session)
        user = User.objects.get(username="sp_listener")
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        token = ProviderToken.objects.get(user=user, provider="spotify")
        self.assertEqual((token.access_token, token.refresh_token, token.provider_user_id),
                         ("callback-access", "callback-refresh", "listener"))
        self.assertEqual(token.get_scopes(), settings.SPOTIFY_SCOPES.split())
        self.assertGreaterEqual(token.expires_at, before + datetime.timedelta(seconds=1800))
        basic = base64.b64encode(b"offline-client:offline-secret").decode()
        self.post.assert_called_once_with(
            SPOTIFY_TOKEN_URL, data={"grant_type": "authorization_code", "code": "offline-code", "redirect_uri": settings.SPOTIFY_REDIRECT_URI},
            headers={"Authorization": f"Basic {basic}"}, timeout=15,
        )
        self.get.assert_called_once_with(f"{SPOTIFY_API}/me", headers={"Authorization": "Bearer callback-access"}, timeout=15)
        self.assertEqual(self.callback(state).status_code, 400)
        self.assertEqual(self.post.call_count, 1)
        self.assertEqual(self.get.call_count, 1)

    def test_missing_forged_and_other_browser_states_never_reach_provider(self):
        state = self.start_login()
        other = APIClient()
        self.start_login(other)
        self.assertEqual(self.callback(state, other).status_code, 400)
        self.assertEqual(self.client.session["spotify_oauth_state"], state)
        self.assertEqual(self.callback("forged").status_code, 400)
        self.assertEqual(self.callback(state).status_code, 400)  # invalid attempt consumed this browser's state
        self.assertEqual(self.client.get("/auth/spotify/callback", {"code": "offline-code"}).status_code, 400)
        self.post.assert_not_called()
        self.get.assert_not_called()
        self.assertEqual(ProviderToken.objects.count(), 0)

    def test_missing_code_consumes_state_without_provider_call(self):
        state = self.start_login()
        result = self.client.get("/auth/spotify/callback", {"state": state})
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result.data, {"error": "missing_code"})
        self.assertNotIn("spotify_oauth_state", self.client.session)
        self.post.assert_not_called()
        self.get.assert_not_called()

    def test_token_exchange_rejection_is_safe_and_not_replayable(self):
        state = self.start_login()
        self.replies("post", self.response({"error_description": "private-provider-detail"}, 401))
        result = self.callback(state)
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result.data, {"error": "token_exchange_failed", "detail": "Provider request failed"})
        self.assertEqual(self.callback(state).status_code, 400)
        self.assertEqual(self.post.call_count, 1)
        self.get.assert_not_called()
        self.assertEqual(ProviderToken.objects.count(), 0)

    def test_callback_timeout_returns_safe_error_and_consumes_state(self):
        state = self.start_login()
        self.post.side_effect = requests.Timeout("private-provider-detail")
        result = self.callback(state)
        self.assertEqual(result.status_code, 504)
        self.assertNotIn("private-provider-detail", str(result.data))
        self.assertNotIn("spotify_oauth_state", self.client.session)
        self.assertEqual(self.callback(state).status_code, 400)
        self.assertEqual(self.post.call_count, 1)
        self.get.assert_not_called()

    def test_profile_rejection_never_saves_token_or_session(self):
        state = self.start_login()
        self.replies("post", self.response({"access_token": "private-token"}))
        self.replies("get", self.response({"error": "private-provider-detail"}, 403))
        result = self.callback(state)
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result.data, {"error": "me_failed", "detail": "Provider request failed"})
        self.assertEqual(ProviderToken.objects.count(), 0)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_malformed_callback_payload_returns_safe_error(self):
        state = self.start_login()
        self.replies("post", self.response({"expires_in": 3600}))
        result = self.callback(state)
        self.assertEqual(result.status_code, 502)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertNotIn("spotify_oauth_state", self.client.session)
        self.assertEqual(ProviderToken.objects.count(), 0)

    def test_refresh_rotates_only_current_users_token(self):
        token = self.token(expires_in=-1)
        other = self.token(self.bob)
        before = timezone.now()
        self.replies("post", self.response({"access_token": "refreshed", "refresh_token": "rotated", "expires_in": 1800}))
        self.replies("get", self.response({"items": [], "next": None}))
        self.assertEqual(self.sync().data, {"ok": True, "imported": 0})
        token.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual((token.access_token, token.refresh_token), ("refreshed", "rotated"))
        self.assertGreaterEqual(token.expires_at, before + datetime.timedelta(seconds=1800))
        self.assertEqual(other.access_token, "access-bob")
        self.assertEqual(self.post.call_args.kwargs["data"], {"grant_type": "refresh_token", "refresh_token": "refresh-original"})
        self.assertEqual(self.post.call_args.kwargs["timeout"], 15)
        self.assertEqual(self.get.call_args.kwargs["headers"], {"Authorization": "Bearer refreshed"})

    def test_refresh_preserves_original_refresh_token_when_not_rotated(self):
        token = self.token(expires_in=10)
        self.replies("post", self.response({"access_token": "refreshed", "expires_in": 1800}))
        self.replies("get", self.response({"items": [], "next": None}))
        self.assertEqual(self.sync().status_code, 200)
        token.refresh_from_db()
        self.assertEqual(token.refresh_token, "refresh-original")

    def test_unexpired_token_does_not_refresh(self):
        self.token()
        self.replies("get", self.response({"items": [], "next": None}))
        self.assertEqual(self.sync().status_code, 200)
        self.post.assert_not_called()
        self.assertEqual(self.get.call_args.kwargs["headers"], {"Authorization": "Bearer access-alice"})

    def test_failed_refresh_leaves_tokens_unchanged_and_does_not_sync(self):
        token = self.token(expires_in=-1)
        self.replies("post", self.response({"error": "private-provider-detail"}, 401))
        result = self.sync()
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result.data, {"error": "not_connected"})
        token.refresh_from_db()
        self.assertEqual(token.access_token, "access-alice")
        self.get.assert_not_called()

    def test_refresh_timeout_and_malformed_json_are_safe(self):
        token = self.token(expires_in=-1)
        for error, status in [(requests.Timeout("private-provider-detail"), 504), (ValueError("private-provider-detail"), 502)]:
            with self.subTest(status=status):
                self.post.side_effect = error
                result = self.sync()
                self.assertEqual(result.status_code, status)
                self.assertNotIn("private-provider-detail", str(result.data))
        token.refresh_from_db()
        self.assertEqual(token.access_token, "access-alice")
        self.get.assert_not_called()

    def test_expired_token_without_refresh_is_not_sent_to_provider(self):
        self.token(expires_in=-1, refresh=None)
        result = self.sync()
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result.data, {"error": "not_connected"})
        self.post.assert_not_called()
        self.get.assert_not_called()

    def test_sync_pagination_is_repeatable_and_user_scoped(self):
        self.token()
        next_page = f"{SPOTIFY_API}/me/tracks?offset=50&limit=50"
        def item(track_id):
            return {"added_at": "2026-01-01T12:00:00Z", "track": {
                "id": track_id, "name": f"Track {track_id}", "artists": [{"name": "Artist"}],
                "album": {"images": [{"url": "https://example.test/art"}]}, "preview_url": None,
            }}
        for _ in range(2):
            self.replies("get", self.response({"items": [item("first")], "next": next_page}),
                         self.response({"items": [item("second")], "next": None}))
            self.assertEqual(self.sync().data, {"ok": True, "imported": 2})
        self.assertEqual(UserTrackLike.objects.filter(user=self.alice).count(), 2)
        self.assertFalse(UserTrackLike.objects.filter(user=self.bob).exists())
        self.assertEqual([c.args[0] for c in self.get.call_args_list],
                         [f"{SPOTIFY_API}/me/tracks?limit=50", next_page] * 2)
        self.assertTrue(all(c.kwargs == {"headers": {"Authorization": "Bearer access-alice"}, "timeout": 20}
                            for c in self.get.call_args_list))
        self.post.assert_not_called()

    def test_other_users_connection_is_never_used(self):
        self.token(self.bob)
        result = self.sync()
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result.data, {"error": "not_connected"})
        self.post.assert_not_called()
        self.get.assert_not_called()

    def test_sync_rejection_and_timeout_are_safe(self):
        self.token()
        for reply, status in [(self.response({"error": "private-provider-detail"}, 401), 400), (requests.Timeout("private-provider-detail"), 504)]:
            with self.subTest(status=status):
                self.replies("get", reply)
                result = self.sync()
                self.assertEqual(result.status_code, status)
                self.assertNotIn("private-provider-detail", str(result.data))
        self.assertEqual(UserTrackLike.objects.count(), 0)

    def test_export_uses_current_users_private_playlist_and_ordered_tracks(self):
        self.token()
        self.token(self.bob)
        playlist = {"id": "new-playlist", "external_urls": {"spotify": "https://open.spotify.com/playlist/new-playlist"}}
        self.replies("post", self.response(playlist, 201), self.response({"snapshot_id": "snapshot"}, 201))
        result = create_spotify_playlist(self.alice, "My picks", ["spotify:track:first", "spotify:track:second"])
        self.assertEqual(result, playlist)
        headers = {"Authorization": "Bearer access-alice", "Content-Type": "application/json"}
        self.assertEqual(self.post.call_args_list, [
            call(f"{SPOTIFY_API}/users/provider-alice/playlists", headers=headers,
                 json={"name": "My picks", "description": "Created by Swave playlist export test.", "public": False}, timeout=15),
            call(f"{SPOTIFY_API}/playlists/new-playlist/tracks", headers=headers,
                 json={"uris": ["spotify:track:first", "spotify:track:second"]}, timeout=15),
        ])
        self.get.assert_not_called()

    def test_export_without_own_connection_does_not_use_another_users(self):
        self.token(self.bob)
        with self.assertRaisesRegex(ValueError, "not connected"):
            create_spotify_playlist(self.alice, "My picks", ["spotify:track:first"])
        self.post.assert_not_called()
        self.get.assert_not_called()

    def test_export_refreshes_before_creating_playlist(self):
        self.token(expires_in=-1)
        self.replies("post", self.response({"access_token": "refreshed"}),
                     self.response({"id": "new-playlist"}, 201), self.response({"snapshot_id": "snapshot"}, 201))
        self.assertEqual(create_spotify_playlist(self.alice, "My picks", ["spotify:track:first"]), {"id": "new-playlist"})
        self.assertEqual(self.post.call_count, 3)
        self.assertEqual(self.post.call_args_list[1].kwargs["headers"]["Authorization"], "Bearer refreshed")

    def test_export_creation_rejection_stops_before_track_write(self):
        self.token()
        self.replies("post", self.response({"id": "must-not-use", "error": "private-provider-detail"}, 403))
        with self.assertRaises(requests.HTTPError):
            create_spotify_playlist(self.alice, "My picks", ["spotify:track:first"])
        self.assertEqual(self.post.call_count, 1)

    def test_export_track_rejection_is_not_reported_as_success(self):
        self.token()
        self.replies("post", self.response({"id": "new-playlist"}, 201), self.response({"error": "private-provider-detail"}, 401))
        with self.assertRaises(requests.HTTPError):
            create_spotify_playlist(self.alice, "My picks", ["spotify:track:first"])
        self.assertEqual(self.post.call_count, 2)

    def test_export_timeout_does_not_retry_remote_writes(self):
        self.token()
        for replies, calls in [([requests.Timeout("private-provider-detail")], 1),
                               ([self.response({"id": "new-playlist"}, 201), requests.Timeout("private-provider-detail")], 2)]:
            with self.subTest(calls=calls):
                self.post.reset_mock()
                self.replies("post", *replies)
                with self.assertRaises(requests.Timeout):
                    create_spotify_playlist(self.alice, "My picks", ["spotify:track:first"])
                self.assertEqual(self.post.call_count, calls)

    @override_settings(SPOTIFY_CLIENT_ID="", SPOTIFY_CLIENT_SECRET="")
    def test_missing_credentials_do_not_block_core_application(self):
        result = self.client.get("/auth/spotify/login")
        self.assertEqual(result.status_code, 503)
        self.assertNotIn("spotify_oauth_state", self.client.session)
        self.assertEqual(self.client.get("/api/feed/next").status_code, 200)
        self.client.force_authenticate(self.alice)
        self.assertEqual(self.client.get("/auth/profile/").status_code, 200)
        self.assertEqual(self.sync().data, {"error": "not_connected"})
        self.post.assert_not_called()
        self.get.assert_not_called()
