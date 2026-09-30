import * as mocks from './mocks';
import type {FeedResponse, Track, AuthResponse, LoginRequest, RegisterRequest, User, AuthTokens, PlaylistDetail} from './types';
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
function isDemo() {
  try { return JSON.parse(localStorage.getItem('auth-storage') || '{}').state?.isDemoMode === true; }
  catch { return false; }
}
function tokens(): AuthTokens | null {
  try { return JSON.parse(localStorage.getItem('auth_tokens') || 'null'); }
  catch { localStorage.removeItem('auth_tokens'); return null; }
}
const saveTokens = (value: AuthTokens) => localStorage.setItem('auth_tokens', JSON.stringify(value));
export const clearTokens = () => localStorage.removeItem('auth_tokens');
async function request(path: string, options: RequestInit = {}, retry = true): Promise<Response> {
  const token = tokens();
  const headers = new Headers(options.headers);
  headers.set('Content-Type', 'application/json');
  if (token?.access) headers.set('Authorization', `Bearer ${token.access}`);
  let response = await fetch(API_BASE_URL + path, {...options, headers});
  if (response.status === 401 && token?.refresh && retry) {
    const refresh = await fetch(API_BASE_URL + '/auth/refresh/', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({refresh:token.refresh})});
    if (!refresh.ok) { clearTokens(); throw new Error('Session expired. Sign in again.'); }
    const result = await refresh.json();
    saveTokens({...token, access:result.access, refresh:result.refresh || token.refresh});
    response = await request(path, options, false);
  }
  return response;
}
async function json<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await request(path,options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || data.detail || Object.values(data).flat().join(' ') || 'Request failed');
  return data as T;
}
const post = (body: unknown): RequestInit => ({method:'POST',body:JSON.stringify(body)});
type BackendTrack = {id:number; external_id:string; title:string; artist:string; artwork?:string; album_art_url?:string; preview_url?:string};
type CatalogClip = {id:string;title:string;artist:string;album_art_url:string;preview_url:string};
const catalogTrack = (c:CatalogClip):Track => ({id:String(c.id),title:c.title,artist:c.artist,album:'',artworkUrl:c.album_art_url || '',previewUrl:c.preview_url || null});
type DailyPlaylist = {id:number;name:string;items:Array<{track:BackendTrack}>};
const track = (t:BackendTrack):Track => ({id:t.external_id || String(t.id),title:t.title,artist:t.artist,album:'',artworkUrl:t.album_art_url || t.artwork || '',previewUrl:t.preview_url || null});
const playlist = (p:DailyPlaylist):PlaylistDetail => ({id:String(p.id),name:p.name,tracks:p.items.map(i=>track(i.track))});
export const api = {
  auth: {
    login: async (data:LoginRequest) => { const result=await json<AuthResponse>('/auth/login/',post(data)); saveTokens(result.tokens); return result; },
    register: async (data:RegisterRequest) => { const result=await json<AuthResponse>('/auth/register/',post(data)); saveTokens(result.tokens); return result; },
    logout: async () => { const token=tokens(); try { if(token?.refresh) await json('/auth/logout/',post({refresh:token.refresh})); } finally { clearTokens(); } },
    getProfile: () => json<User>('/auth/profile/'),
    updateProfile: (data:Partial<User>) => json<User>('/auth/profile/update/',{method:'PUT',body:JSON.stringify(data)}),
  },
  feed: {
    getNext: async ():Promise<FeedResponse> => {
      if(isDemo()) return mocks.mockFetchNextFeed();
      const result=await json<{batch_id:string|null;clips:Array<{id:string;title:string;artist:string;album_art_url:string;preview_url:string}>}>('/api/feed/next');
      return {batchId:result.batch_id || '',tracks:result.clips.map(catalogTrack)};
    },
  },
  catalog: {search: async (query:string) => {
    const result = await json<{imported:number;clips:CatalogClip[]}>('/catalog/search/',post({query}));
    return {imported:result.imported,tracks:result.clips.map(catalogTrack)};
  }},
  events: {
    save: async (trackId:string,type:'like'|'reject') => {
      if(isDemo()) return mocks.mockSaveEvent(trackId,type);
      await json('/api/event/swipe/',post({track_id:trackId,direction:type==='like'?'right':'left',played_ms:0}));
    },
  },
  playlists: {
    generateDaily: async ():Promise<PlaylistDetail> => isDemo() ? mocks.mockGenerateDailyPlaylist() : playlist(await json<DailyPlaylist>('/playlist/daily/build/',post({}))),
    getDaily: async ():Promise<PlaylistDetail> => isDemo() ? mocks.mockGetPlaylist('daily-mix') : playlist(await json<DailyPlaylist>('/playlist/daily/')),
  },
};
