import { Track, FeedResponse, Playlist, PlaylistDetail, AuthProvider } from './types';

// Mock data storage
const mockTracks: Track[] = [
  {
    id: '1',
    title: 'Midnight Dreams',
    artist: 'Luna Eclipse',
    album: 'Nocturnal',
    artworkUrl: 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=800&q=80',
    previewUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3',
    reasons: ['Because you liked Phoebe Bridgers', 'Similar to Bon Iver'],
  },
  {
    id: '2',
    title: 'Electric Pulse',
    artist: 'The Synthesizers',
    album: 'Digital Dreams',
    artworkUrl: 'https://images.unsplash.com/photo-1511379938547-c1f69419868d?w=800&q=80',
    previewUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3',
    reasons: ['Trending in Electronic'],
  },
  {
    id: '3',
    title: 'Golden Hour',
    artist: 'Sunrise Collective',
    album: 'Morning Light',
    artworkUrl: 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&q=80',
    previewUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3',
    reasons: ['Popular in Indie Folk'],
  },
  {
    id: '4',
    title: 'Neon Nights',
    artist: 'Retrowave',
    album: 'Synthwave City',
    artworkUrl: 'https://images.unsplash.com/photo-1514320291840-2e0a9bf2a9ae?w=800&q=80',
    previewUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3',
    reasons: ['Because you liked CHVRCHES'],
  },
  {
    id: '5',
    title: 'Ocean Waves',
    artist: 'Coastal Dreams',
    album: 'Tides',
    artworkUrl: 'https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=800&q=80',
    previewUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3',
    reasons: ['Relaxing vibes'],
  },
];

let trackIndex = 0;
const mockPlaylists: Playlist[] = [
  {
    id: 'daily-mix',
    name: 'Daily Mix',
    trackCount: 12,
    updatedAt: new Date().toISOString(),
  },
];

const playlistCache = new Map<string, PlaylistDetail>();

export const mockFetchNextFeed = async (): Promise<FeedResponse> => {
  // Simulate network delay
  await new Promise(resolve => setTimeout(resolve, 500));
  
  // Generate next batch with cycling tracks
  const tracks = Array.from({ length: 10 }, (_, i) => {
    const track = mockTracks[trackIndex % mockTracks.length];
    trackIndex++;
    return {
      ...track,
      id: `${track.id}-${trackIndex}`,
    };
  });

  return {
    batchId: `batch-${Date.now()}`,
    tracks,
  };
};

export const mockSaveEvent = async (trackId: string, type: 'like' | 'reject'): Promise<void> => {
  await new Promise(resolve => setTimeout(resolve, 100));
  console.log(`[Mock] Saved event: ${type} for track ${trackId}`);
};

export const mockListPlaylists = async (): Promise<Playlist[]> => {
  await new Promise(resolve => setTimeout(resolve, 300));
  return [...mockPlaylists];
};

export const mockGenerateDailyPlaylist = async (): Promise<PlaylistDetail> => {
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  const tracks = mockTracks.slice(0, 5);
  const playlist: PlaylistDetail = {
    id: 'daily-mix',
    name: 'Daily Mix',
    tracks,
  };
  
  playlistCache.set('daily-mix', playlist);
  
  // Update the playlist in the list
  const existingIndex = mockPlaylists.findIndex(p => p.id === 'daily-mix');
  if (existingIndex >= 0) {
    mockPlaylists[existingIndex] = {
      ...mockPlaylists[existingIndex],
      trackCount: tracks.length,
      updatedAt: new Date().toISOString(),
    };
  }
  
  return playlist;
};

export const mockGetPlaylist = async (id: string): Promise<PlaylistDetail> => {
  await new Promise(resolve => setTimeout(resolve, 300));
  
  if (playlistCache.has(id)) {
    return playlistCache.get(id)!;
  }
  
  // Generate a mock playlist if not found
  const playlist: PlaylistDetail = {
    id,
    name: 'Daily Mix',
    tracks: mockTracks.slice(0, 3),
  };
  
  playlistCache.set(id, playlist);
  return playlist;
};

export const mockExportPlaylist = async (id: string): Promise<{ ok: true }> => {
  await new Promise(resolve => setTimeout(resolve, 500));
  console.log(`[Mock] Exported playlist ${id}`);
  return { ok: true };
};

export const mockAuthConnect = async (provider: AuthProvider): Promise<{ ok: true }> => {
  await new Promise(resolve => setTimeout(resolve, 800));
  console.log(`[Mock] Connected to ${provider}`);
  return { ok: true };
};

export const mockRefreshTaste = async (): Promise<{ ok: true }> => {
  await new Promise(resolve => setTimeout(resolve, 1500));
  console.log('[Mock] Refreshed taste profile');
  trackIndex = 0; // Reset to show different tracks
  return { ok: true };
};
