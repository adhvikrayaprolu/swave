import { useEffect, useState, useCallback, useRef } from 'react';
import { useFeedStore } from '@/store/feed';
import { useUIStore } from '@/store/ui';
import { useAuthStore } from '@/store/auth';
import { api } from '@/api/client';
import { SwipeCard } from '@/components/SwipeCard';
import { Button } from '@/components/ui/button';
import { Loader2, LogOut, User } from 'lucide-react';

export const Feed = () => {
  const { queue, loading, fetchIfLow, consumeTop } = useFeedStore();
  const { user, logout, isDemoMode } = useAuthStore();
  const toast = useUIStore((state) => state.toast);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const progressInterval = useRef<NodeJS.Timeout | null>(null);
  const [swipeCount, setSwipeCount] = useState(0);
  const [playlistBusy, setPlaylistBusy] = useState(false);
  const [playlistOpen, setPlaylistOpen] = useState(false);
  const [playlistData, setPlaylistData] = useState<any | null>(null);

  const API_BASE =
  (import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8000';



  const handleLogout = async () => {
    try {
      await logout();
      toast('Logged out successfully');
    } catch (error) {
      console.error('Logout error:', error);
      toast('Error logging out');
    }
  };

  useEffect(() => {
    if (!isDemoMode && !user) return;
    if (queue.length === 0) fetchIfLow();
  }, [fetchIfLow, queue.length, user, isDemoMode]);



  const handlePlayPreview = useCallback((url: string | null) => {
    // Stop current audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
      setIsPlaying(false);
      setProgress(0);
    }

    if (progressInterval.current) {
      clearInterval(progressInterval.current);
      progressInterval.current = null;
    }

    if (!url) {
      toast('No preview available for this track');
      return;
    }

    // Create and play new audio
    const audio = new Audio(url);
    audioRef.current = audio;

    audio.play().then(() => {
      setIsPlaying(true);

      // Update progress
      progressInterval.current = setInterval(() => {
        if (audio.duration) {
          const prog = (audio.currentTime / audio.duration) * 100;
          setProgress(prog);

          if (audio.ended) {
            setIsPlaying(false);
            setProgress(0);
            if (progressInterval.current) {
              clearInterval(progressInterval.current);
            }
          }
        }
      }, 100);
    }).catch(() => {
      toast('Failed to play preview');
    });

    return () => {
      audio.pause();
      if (progressInterval.current) {
        clearInterval(progressInterval.current);
      }
    };
  }, [toast]);

  const handleGeneratePlaylist = async () => {
    setPlaylistBusy(true);
    try {
      const res = await fetch(`${API_BASE}/playlist/daily/build/`, {
        method: 'POST',
        credentials: 'include',
      });
      if (!res.ok) throw new Error(`Failed (${res.status})`);
      const data = await res.json();

      setPlaylistData(data);
      setPlaylistOpen(true);
    } catch (e: any) {
      toast(e?.message || 'Failed to generate playlist');
    } finally {
      setPlaylistBusy(false);
    }
  };



  const handlePlayPause = () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  const handleSwipe = async (type: 'like' | 'reject') => {
    consumeTop(async (track) => {
      await api.events.save(track.id, type);
      setSwipeCount((c) => c + 1);
      toast(type === 'like' ? '❤️ Liked!' : '✕ Passed');
    });
  };

  if (loading && queue.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="w-12 h-12 text-primary animate-spin" />
      </div>
    );
  }

  if (queue.length === 0) {
    return (
      <div className="min-h-screen flex flex-col bg-background">
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center space-y-4">
            <h2 className="text-2xl font-bold text-foreground">No more tracks!</h2>
            <p className="text-muted-foreground">Check back later for new recommendations</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="p-6 text-center border-b border-border">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <User className="w-5 h-5 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">
              {user?.display_name || user?.username}
              {isDemoMode && (
                <span className="ml-2 px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                  Demo Mode
                </span>
              )}
            </span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleLogout}
            className="flex items-center space-x-2"
          >
            <LogOut className="w-4 h-4" />
            <span>{isDemoMode ? 'Exit Demo' : 'Logout'}</span>
          </Button>
        </div>
        <h1 className="text-2xl font-bold text-foreground">Discover</h1>
      </header>

      {/* Card Stack */}
      <div className="flex-1 relative px-4 pb-8">
        {queue.slice(0, 3).map((track, index) => (
          <div
            key={track.id}
            className="absolute inset-0"
            style={{
              zIndex: 3 - index,
              transform: `scale(${1 - index * 0.05}) translateY(${index * -10}px)`,
              opacity: index === 0 ? 1 : 0.5,
              pointerEvents: index === 0 ? 'auto' : 'none',
            }}
          >
            {index === 0 && (
              <SwipeCard
                track={track}
                onSwipeLeft={() => handleSwipe('reject')}
                onSwipeRight={() => handleSwipe('like')}
                onPlayPreview={handlePlayPreview}
              />
            )}
            {index > 0 && (
              <div className="w-full max-w-md h-[600px] mx-auto bg-card rounded-3xl shadow-card" />
            )}
          </div>
        ))}
      </div>

      {swipeCount >= 10 && (
      <div className="p-4 flex justify-center">
        <Button onClick={handleGeneratePlaylist} disabled={playlistBusy}>
          {playlistBusy ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
          Generate Playlist
        </Button>
      </div>
    )}

      {playlistOpen && playlistData && (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
      <div className="w-full max-w-md rounded-2xl bg-card border border-border p-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold">Playlist created ✅</h3>
            <p className="text-sm text-muted-foreground">{playlistData.name}</p>
          </div>
          <Button variant="outline" size="sm" onClick={() => setPlaylistOpen(false)}>
            Close
          </Button>
        </div>

        <div className="mt-4 space-y-2 max-h-72 overflow-y-auto">
          {(playlistData.items || []).map((it: any) => (
            <div key={it.id} className="flex items-center gap-3 rounded-xl bg-muted/30 p-2">
              <img
                src={it.track?.album_art_url || ''}
                className="w-10 h-10 rounded-lg object-cover"
              />
              <div className="min-w-0">
                <div className="text-sm font-medium truncate">{it.track?.title}</div>
                <div className="text-xs text-muted-foreground truncate">{it.track?.artist}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )}


    </div>
    
    
  );
};
