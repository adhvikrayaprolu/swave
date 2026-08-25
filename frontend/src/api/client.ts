import * as mocks from './mocks';
import type { 
  FeedResponse, 
  Playlist, 
  PlaylistDetail, 
  AuthProvider,
  AuthResponse,
  LoginRequest,
  RegisterRequest,
  User,
  AuthTokens
} from './types';

// Base API URL - change this to your backend URL
const API_BASE_URL = 'http://localhost:8000';

// Token management
const getStoredTokens = (): AuthTokens | null => {
  const tokens = localStorage.getItem('auth_tokens');
  return tokens ? JSON.parse(tokens) : null;
};

const setStoredTokens = (tokens: AuthTokens) => {
  localStorage.setItem('auth_tokens', JSON.stringify(tokens));
};

const clearStoredTokens = () => {
  localStorage.removeItem('auth_tokens');
};

// Helper function to make authenticated requests
const makeAuthenticatedRequest = async (url: string, options: RequestInit = {}) => {
  const tokens = getStoredTokens();
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (tokens?.access) {
    headers['Authorization'] = `Bearer ${tokens.access}`;
  }

  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers,
  });

  // If token expired, try to refresh
  if (response.status === 401 && tokens?.refresh) {
    try {
      const refreshResponse = await fetch(`${API_BASE_URL}/auth/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: tokens.refresh }),
      });

      if (refreshResponse.ok) {
        const { access } = await refreshResponse.json();
        const newTokens = { ...tokens, access };
        setStoredTokens(newTokens);
        
        // Retry original request with new token
        headers['Authorization'] = `Bearer ${access}`;
        return fetch(`${API_BASE_URL}${url}`, {
          ...options,
          headers,
        });
      }
    } catch (error) {
      // Refresh failed, clear tokens
      clearStoredTokens();
      throw new Error('Authentication failed');
    }
  }

  return response;
};

export const api = {
  // Authentication endpoints
  auth: {
    register: async (data: RegisterRequest): Promise<AuthResponse> => {
      const response = await fetch(`${API_BASE_URL}/auth/register/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        const error = await response.json();
        if (error.password) {
          throw new Error(`Password: ${error.password.join(', ')}`);
        }
        if (error.email) {
          throw new Error(`Email: ${error.email.join(', ')}`);
        }
        if (error.username) {
          throw new Error(`Username: ${error.username.join(', ')}`);
        }
        
        throw new Error(error.detail || error.message || 'Registration failed');
      }
      
      const result = await response.json();
      setStoredTokens(result.tokens);
      return result;
    },

    login: async (data: LoginRequest): Promise<AuthResponse> => {
      const response = await fetch(`${API_BASE_URL}/auth/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || error.message || 'Login failed');
      }
      
      const result = await response.json();
      setStoredTokens(result.tokens);
      return result;
    },

    logout: async (): Promise<void> => {
      const tokens = getStoredTokens();
      if (tokens?.refresh) {
        try {
          await fetch(`${API_BASE_URL}/auth/logout/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh: tokens.refresh }),
          });
        } catch (error) {
          console.error('Logout error:', error);
        }
      }
      clearStoredTokens();
    },

    verifyFirebaseToken: async (firebaseToken: string): Promise<AuthResponse> => {
      const response = await fetch(`${API_BASE_URL}/auth/verify-firebase/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ firebase_token: firebaseToken }),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || error.detail || 'Token verification failed');
      }
      
      const result = await response.json();
      setStoredTokens(result.tokens);
      return result;
    },

    getProfile: async (): Promise<User> => {
      const response = await makeAuthenticatedRequest('/auth/profile/');
      
      if (!response.ok) {
        throw new Error('Failed to fetch profile');
      }
      
      return response.json();
    },

    updateProfile: async (data: Partial<User>): Promise<User> => {
      const response = await makeAuthenticatedRequest('/auth/profile/update/', {
        method: 'PUT',
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        throw new Error('Failed to update profile');
      }
      
      return response.json();
    },

    // Future OAuth integration
    connectProvider: async (provider: AuthProvider): Promise<{ ok: true }> => 
      mocks.mockAuthConnect(provider),
    refreshTaste: async (): Promise<{ ok: true }> => mocks.mockRefreshTaste(),
  },

  feed: {
    getNext: async (): Promise<FeedResponse> => {
      const res = await fetch(`${API_BASE_URL}/api/feed/next`);
      if (!res.ok) {
        return mocks.mockFetchNextFeed();
      }
      const data = await res.json() as {
        batch_id: string | null;
        clips: Array<{
          id: string | number;
          title: string;
          artist: string;
          album_art_url: string | null;
          preview_url: string | null;
          provider?: string | null;
          provider_track_id?: string | null;
        }>;
      };
  
      return {
        batchId: data.batch_id ?? null,
        tracks: data.clips.map(c => ({
          id: String(c.id),
          title: c.title,
          artist: c.artist,
          album: '', 
          artworkUrl: c.album_art_url ?? '',
          previewUrl: (c.preview_url ?? '') || null,
        })),
      };
    },
  },
  
  events: {
    save: async (trackId: string, type: 'like' | 'reject'): Promise<void> => {
      const body = JSON.stringify({
        track_id: trackId,
        direction: type === 'like' ? 'right' : 'left',
        batch_id: null,
      });
  
      const res = await makeAuthenticatedRequest(`/api/event/swipe/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
      });
  
      if (!res.ok) {
        // Swipe events are non-critical, fail silently
      }
    },
  },  
  
  // Playlist endpoints
  playlists: {
    list: (): Promise<Playlist[]> => mocks.mockListPlaylists(),
    get: (id: string): Promise<PlaylistDetail> => mocks.mockGetPlaylist(id),
    generateDaily: (): Promise<PlaylistDetail> => mocks.mockGenerateDailyPlaylist(),
    export: (id: string): Promise<{ ok: true }> => mocks.mockExportPlaylist(id),
  },
};
