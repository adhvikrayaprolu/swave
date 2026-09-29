import { useEffect, useState, useCallback, useRef } from 'react';
import { useFeedStore } from '@/store/feed';
import { useUIStore } from '@/store/ui';
import { useAuthStore } from '@/store/auth';
import { api } from '@/api/client';
import type {PlaylistDetail} from '@/api/types';
import {Dialog,DialogContent,DialogTitle,DialogDescription} from '@/components/ui/dialog';
import { SwipeCard } from '@/components/SwipeCard';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Loader2, LogOut, User } from 'lucide-react';

export const Feed = () => {
  const { queue, loading, error, fetchIfLow, consumeTop, reset } = useFeedStore();
  const { user, logout, isDemoMode } = useAuthStore();
  const toast = useUIStore((state) => state.toast);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const progressInterval = useRef<NodeJS.Timeout | null>(null);
  const [swipeCount, setSwipeCount] = useState(0);
  const [playlistBusy, setPlaylistBusy] = useState(false);
  const [playlistOpen, setPlaylistOpen] = useState(false);
  const [playlistData, setPlaylistData] = useState<PlaylistDetail | null>(null);

  const [query,setQuery]=useState('');
  const [searching,setSearching]=useState(false);
  const search = async () => {
    setSearching(true);
    try { const result=await api.catalog.search(query); reset(); await fetchIfLow(); toast(`Imported ${result.imported} tracks`); }
    catch(error) { toast(error instanceof Error ? error.message : 'Search failed'); }
    finally { setSearching(false); }
  };
  const searchForm = !isDemoMode && <form onSubmit={e=>{e.preventDefault();void search();}} className="flex gap-2 max-w-md mx-auto p-4"><Input aria-label="Search music" placeholder="Search artist or song" value={query} onChange={e=>setQuery(e.target.value)} maxLength={100} required/><Button disabled={searching}>{searching?'Searching…':'Search'}</Button></form>;

  const handleLogout = async () => {
    try {
      await logout();
      reset();
      toast('Logged out successfully');
    } catch (error) {
      console.error('Logout error:', error);
      toast('Error logging out');
    }
  };

  useEffect(() => {
    if (!isDemoMode && !user) return;
    void fetchIfLow();
  }, [fetchIfLow, user, isDemoMode]);



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
      const data = await api.playlists.generateDaily();
      setPlaylistData(data);
      setPlaylistOpen(true);
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Failed to generate playlist');

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

  const [saving, setSaving] = useState(false);
  const handleSwipe = async (type: 'like' | 'reject') => {
    if (saving) return;
    setSaving(true);
    try {
      await consumeTop(async (track) => {
        await api.events.save(track.id, type);
        setSwipeCount((c) => c + 1);
        toast(type === 'like' ? 'Liked!' : 'Passed');
      });
    } catch (error) { toast(error instanceof Error ? error.message : 'Could not save swipe. Try again.'); }
    finally { setSaving(false); }
  };
  useEffect(() => () => {
    audioRef.current?.pause();
    if (progressInterval.current) clearInterval(progressInterval.current);
  }, []);

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
            <h2 className="text-2xl font-bold text-foreground">{error ? "Could not load tracks" : "No more tracks"}</h2>
            <p role="status" className="text-muted-foreground">{error || "Search for music to add previews to your catalog."}</p><Button onClick={() => void fetchIfLow()}>Retry</Button><Button variant="outline" onClick={handleLogout}>Logout</Button>{searchForm}<Button onClick={handleGeneratePlaylist} disabled={playlistBusy}>Generate Playlist</Button><Dialog open={playlistOpen} onOpenChange={setPlaylistOpen}><DialogContent><DialogTitle>Daily playlist</DialogTitle><DialogDescription>Your liked tracks</DialogDescription>{playlistData?.tracks.map(t=><p key={t.id}>{t.title} — {t.artist}</p>)}</DialogContent></Dialog>
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

      {searchForm}
      {/* Card Stack */}
      <div className="relative h-[460px] px-4 pb-8">
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
              <div className="w-full max-w-md h-[420px] mx-auto bg-card rounded-3xl shadow-card" />
            )}
          </div>
        ))}
      </div>

      <div className="flex flex-wrap justify-center gap-3 p-4"><Button variant="outline" disabled={saving} onClick={()=>void handleSwipe('reject')}>Pass</Button><Button disabled={saving} onClick={()=>void handleSwipe('like')}>{saving?'Saving…':'Like'}</Button><Button variant="outline" disabled={!queue[0]?.previewUrl} onClick={()=>handlePlayPreview(queue[0]?.previewUrl || null)}>Play preview</Button></div>
      {(swipeCount > 0 || !isDemoMode) && (
      <div className="p-4 flex justify-center">
        <Button onClick={handleGeneratePlaylist} disabled={playlistBusy}>
          {playlistBusy ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
          Generate Playlist
        </Button>
      </div>
    )}

      <Dialog open={playlistOpen} onOpenChange={setPlaylistOpen}>
        <DialogContent><DialogTitle>Daily playlist</DialogTitle><DialogDescription>{playlistData?.name || 'Your liked tracks'}</DialogDescription>
          {!playlistData?.tracks.length && <p>No liked tracks yet. Like a song and try again.</p>}
          <div className="max-h-72 overflow-y-auto space-y-2">{playlistData?.tracks.map(track => <div key={track.id} className="rounded-xl bg-muted p-3"><p className="font-medium">{track.title}</p><p>{track.artist}</p></div>)}</div>
        </DialogContent>
      </Dialog>
    </div>
  );
};
