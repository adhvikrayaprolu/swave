export type Track = {
  id: string;
  title: string;
  artist: string;
  album: string;
  artworkUrl: string;
  previewUrl: string | null;
  reasons?: string[];
};

export type FeedResponse = {
  batchId: string;
  tracks: Track[];
};

export type Playlist = {
  id: string;
  name: string;
  trackCount: number;
  updatedAt: string;
};

export type PlaylistDetail = {
  id: string;
  name: string;
  tracks: Track[];
};

export type SwipeEvent = {
  trackId: string;
  type: 'like' | 'reject';
  timestamp: number;
};

export type AuthProvider = 'spotify' | 'apple';

// Authentication Types
export type User = {
  id: number;
  username: string;
  email: string;
  display_name: string;
  date_joined: string;
  profile: UserProfile;
};

export type UserProfile = {
  favorite_genres: string[];
  favorite_artists: string[];
  auto_play_previews: boolean;
  swipe_sensitivity: number;
  total_swipes: number;
  total_likes: number;
  total_rejects: number;
};

export type ProviderToken = {
  provider: 'spotify' | 'apple';
  provider_user_id: string;
  expires_at: string;
  created_at: string;
};

export type UserWithProviders = User & {
  provider_tokens: ProviderToken[];
};

export type AuthTokens = {
  access: string;
  refresh: string;
};

export type AuthResponse = {
  user: User;
  tokens: AuthTokens;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type RegisterRequest = {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
  display_name?: string;
};
