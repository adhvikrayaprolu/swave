from unittest.mock import patch
import requests
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APITestCase
from .models import User, Track, SwipeEvent, UserProfile, Playlist


class MusicFlowTests(APITestCase):
    def setUp(self):
        self.a = User.objects.create_user(username='alice', email='a@example.test', password='long-password-123')
        self.b = User.objects.create_user(username='bob', email='b@example.test', password='long-password-123')
        self.track = Track.objects.create(external_id='track-1', title='Track', artist='Artist', provider_track_id='track-1')

    def test_private_endpoints_reject_anonymous_requests(self):
        for method, url in [('get','/auth/profile/'),('put','/auth/profile/update/'),
                            ('get','/likes/'),('post','/swipes/'),('post','/api/event/swipe/'),
                            ('post','/playlist/daily/build/'),('get','/playlist/daily/'),
                            ('post','/api/spotify/sync-likes'),('get','/api/spotify/liked-debug')]:
            self.assertIn(getattr(self.client, method)(url, {}, format='json').status_code, [401,403])
        self.assertFalse(User.objects.filter(username='demo_spotify').exists())

    def test_swipe_playlist_flow_is_isolated_and_repeatable(self):
        self.client.force_authenticate(self.a)
        for _ in range(2):
            response = self.client.post('/api/event/swipe/', {'track_id':'track-1','direction':'right'}, format='json')
            self.assertEqual(response.status_code, 201)
        profile = UserProfile.objects.get(user=self.a)
        self.assertEqual((profile.total_swipes,profile.total_likes), (2,2))
        for _ in range(2):
            playlist = self.client.post('/playlist/daily/build/', {}, format='json')
            self.assertEqual(playlist.status_code,201)
            self.assertEqual(len(playlist.data['items']),1)
        self.assertEqual(Playlist.objects.filter(user=self.a).count(),1)
        self.client.force_authenticate(self.b)
        self.assertEqual(self.client.get('/likes/').data,[])
        self.assertEqual(self.client.get('/playlist/daily/').status_code,404)
        self.client.force_authenticate(self.a)
        self.assertEqual(len(self.client.get('/playlist/daily/').data['items']),1)

    def test_invalid_swipe_does_not_create_track_or_event(self):
        self.client.force_authenticate(self.a)
        for data in [{'action':'invalid','track':{'external_id':'new','title':'X','artist':'Y'}},
                     {'track':{'external_id':'new'}}, {'track':[]},
                     {'track':{'external_id':'new','title':'X','artist':'Y'},'played_ms':'bad'}]:
            self.assertEqual(self.client.post('/swipes/',data,format='json').status_code,400)
        self.assertFalse(Track.objects.filter(external_id='new').exists())
        self.assertEqual(SwipeEvent.objects.count(),0)
        for played in [-1, True, '100']:
            self.assertEqual(self.client.post('/api/event/swipe/',{'track_id':'track-1','direction':'right','played_ms':played},format='json').status_code,400)

    def test_valid_track_payload_persists_and_missing_track_is_404(self):
        self.client.force_authenticate(self.a)
        response=self.client.post('/swipes/',{'action':'dislike','track':{'external_id':'new','title':'New','artist':'Artist'},'played_ms':1000},format='json')
        self.assertEqual(response.status_code,201)
        self.assertEqual(response.data['action'],'dislike')
        self.assertEqual(self.client.post('/api/event/swipe/',{'track_id':'missing','direction':'left'},format='json').status_code,404)

    def test_feed_bounds_and_seed_idempotency(self):
        for k in ['abc','0','-1','51']:
            self.assertEqual(self.client.get('/api/feed/next',{'k':k}).status_code,400)
        call_command('seed_demo_tracks',verbosity=0)
        call_command('seed_demo_tracks',verbosity=0)
        self.assertEqual(Track.objects.filter(provider='demo').count(),4)
        self.assertTrue(self.client.get('/api/feed/next').data['clips'])

    @patch('music.catalog_views.itunes_song_search',side_effect=requests.Timeout('sensitive text'))
    def test_provider_timeout_has_safe_response(self, mock):
        response=self.client.get('/test-itunes/',{'q':'artist'})
        self.assertEqual(response.status_code,504)
        self.assertNotIn('sensitive',str(response.data))

    @patch('music.spotify_views.requests.post')
    def test_oauth_rejects_missing_state_without_provider_call(self, mock):
        response=self.client.get('/auth/spotify/callback',{'code':'code','state':'forged'})
        self.assertEqual(response.status_code,400)
        mock.assert_not_called()

    def test_profile_cannot_change_another_user(self):
        self.client.force_authenticate(self.a)
        response=self.client.put('/auth/profile/update/',{'id':self.b.id,'display_name':'Mine'},format='json')
        self.assertEqual(response.status_code,200)
        self.a.refresh_from_db();self.b.refresh_from_db()
        self.assertEqual(self.a.display_name,'Mine')
        self.assertNotEqual(self.b.display_name,'Mine')

    def test_feed_excludes_own_swipes_but_not_other_users(self):
        SwipeEvent.objects.create(user=self.a, track=self.track, action='like')
        self.client.force_authenticate(self.a)
        self.assertEqual(self.client.get('/api/feed/next').data['clips'], [])
        self.client.force_authenticate(self.b)
        self.assertEqual(len(self.client.get('/api/feed/next').data['clips']), 1)

    @patch('music.catalog_views.itunes_song_search')
    def test_search_imports_repeatably_and_requires_valid_authenticated_query(self, provider):
        self.assertIn(self.client.post('/catalog/search/', {'query':'music'},format='json').status_code,[401,403])
        self.client.force_authenticate(self.a)
        for query in ['', 'x'*101, []]:
            self.assertEqual(self.client.post('/catalog/search/', {'query':query},format='json').status_code,400)
        provider.assert_not_called()
        provider.return_value=[{'external_id':'itunes-1','title':'Song','artist':'Artist','preview_url':'https://example.test/preview','artwork':'','duration_ms':30000}]
        for _ in range(2):
            self.assertEqual(self.client.post('/catalog/search/',{'query':'Song'},format='json').data,{'imported':1})
        self.assertEqual(Track.objects.filter(external_id='itunes-1').count(),1)
        self.assertEqual(Track.objects.get(external_id='itunes-1').preview_url,'https://example.test/preview')


class AuthTests(APITestCase):
    def test_register_login_logout_revokes_refresh(self):
        payload={'username':'new-user','email':'new@example.test','password':'long-password-234','password_confirm':'long-password-234'}
        response=self.client.post('/auth/register/',payload,format='json')
        self.assertEqual(response.status_code,201)
        user=User.objects.get(email=payload['email'])
        self.assertTrue(user.check_password(payload['password']))
        self.assertEqual(self.client.post('/auth/login/',{'email':payload['email'],'password':'wrong'},format='json').status_code,400)
        login=self.client.post('/auth/login/',{'email':payload['email'],'password':payload['password']},format='json')
        self.assertEqual(login.status_code,200)
        refresh=login.data['tokens']['refresh']
        self.assertEqual(self.client.post('/auth/logout/',{'refresh':refresh},format='json').status_code,200)
        self.assertEqual(self.client.post('/auth/refresh/',{'refresh':refresh},format='json').status_code,401)

    def test_weak_or_mismatched_registration_rejected(self):
        for password,confirm in [('1234','1234'),('long-password-234','different')]:
            self.assertEqual(self.client.post('/auth/register/',{'username':'bad','email':'bad@example.test','password':password,'password_confirm':confirm},format='json').status_code,400)
        self.assertFalse(User.objects.filter(username='bad').exists())
