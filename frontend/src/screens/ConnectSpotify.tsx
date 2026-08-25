import { useEffect, useState } from 'react';
import { Loader2, Music2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useFeedStore } from '@/store/feed';
import { useNavigate } from 'react-router-dom';
import type { Track } from '@/api/types';
import { useAuthStore } from '@/store/auth';



const API_BASE =
  (import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8000';

type LikedTrack = {
  id: string;
  title: string | null;
  artist: string | null;
  album_art_url: string | null;
  preview_url: string | null;
  added_at: string | null;
};

type MetaFeature = {
  id: string;

  // raw
  popularity_raw: number | null;
  explicit: number | null;
  release_year: number | null;
  duration_ms: number | null;
  artist_popularity_raw: number | null;
  artist_followers_raw: number | null;
  label: string | null;
  genres: string[] | null;

  // scaled / numeric vector fields
  popularity_scaled: number | null;
  is_explicit: number | null;
  release_year_scaled: number | null;
  duration_scaled: number | null;
  artist_popularity_scaled: number | null;
  artist_followers_scaled: number | null;
  genre_position: number | null;
  label_score: number | null;
};

type RecommendedTrack = {
  id: string;
  title: string | null;
  artist: string | null;
  album_art_url: string | null;
  preview_url: string | null;
  similarity: number;
};

export const ConnectSpotify = () => {
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tracks, setTracks] = useState<LikedTrack[]>([]);
  const [features, setFeatures] = useState<MetaFeature[]>([]);
  const [recommended, setRecommended] = useState<RecommendedTrack[]>([]);
  const [recoLoading, setRecoLoading] = useState(false);
  const [recoError, setRecoError] = useState<string | null>(null);
  const loadProfile = useAuthStore((s) => s.loadProfile);


  const setExternalQueue = useFeedStore((s) => s.setExternalQueue);
  const navigate = useNavigate();

  const loadLikes = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/spotify/liked-debug`, {
        credentials: 'include',
      });

      if (!res.ok) {
        throw new Error(`Failed to load likes (${res.status})`);
      }

      const data = await res.json();
      setTracks(data.tracks || []);
      setFeatures(data.meta_features || []);
    } catch (err: any) {
      setError(err?.message || 'Failed to load Spotify likes');
    } finally {
      setLoading(false);
    }
  };

  const syncAndLoad = async () => {
    setSyncing(true);
    try {
      await fetch(`${API_BASE}/api/spotify/sync-likes`, {
        method: 'POST',
        credentials: 'include',
      });
    } catch {
      // ignore errors for demo
    } finally {
      setSyncing(false);
      loadLikes();
    }
  };

    const loadRecommendations = async () => {
    setRecoLoading(true);
    setRecoError(null);

    try {
      const res = await fetch(`${API_BASE}/api/spotify/recommend-next`, {
        credentials: 'include',
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(
          `Failed to load recommendations (${res.status}): ${text}`,
        );
      }

      const data = await res.json();
      const recs: RecommendedTrack[] = data.recommendations || [];
      setRecommended(recs);

      // Transform recommendations into feed-compatible Track objects
      const feedTracks: Track[] = recs.map((t) => ({
        id: t.id,
        title: t.title ?? 'Unknown title',
        artist: t.artist ?? 'Unknown artist',
        album: '', // no album name from backend yet
        artworkUrl: t.album_art_url ?? '',
        previewUrl: t.preview_url ?? null,
        reasons: [], // optional; SwipeCard reads track.reasons
      }));

      // Inject them into the feed store
      setExternalQueue(feedTracks);


      await loadProfile().catch(() => {});
      navigate('/');

    } catch (err: any) {
      setRecoError(err?.message || 'Failed to load recommendations');
      setRecommended([]);
    } finally {
      setRecoLoading(false);
    }
  };


  useEffect(() => {
    syncAndLoad();
  }, []);

  const featuresById = features.reduce<Record<string, MetaFeature>>(
    (acc, feat) => {
      acc[feat.id] = feat;
      return acc;
    },
    {},
  );

  const formatDuration = (ms?: number | null) => {
    if (!ms) return '–';
    const totalSec = Math.floor(ms / 1000);
    const m = Math.floor(totalSec / 60);
    const s = totalSec % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const fmt = (val: number | null | undefined, digits = 2) =>
    typeof val === 'number' ? val.toFixed(digits) : '–';

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl bg-black/30 backdrop-blur-xl rounded-3xl border border-white/10 p-6 shadow-xl">
        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-emerald-500 flex items-center justify-center">
            <Music2 className="w-6 h-6 text-neutral-900" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-white">
              Spotify connected ✅
            </h1>
            <p className="text-sm text-blue-200">
              Here are your liked songs and the numeric features we’ll use for
              recommendations.
            </p>
          </div>
        </div>

        {/* Controls (single block) */}
        <div className="flex flex-wrap gap-3 mb-4">
          <Button
            onClick={syncAndLoad}
            disabled={syncing}
            className="bg-emerald-500 hover:bg-emerald-400 text-neutral-900"
          >
            {syncing ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Syncing from Spotify…
              </>
            ) : (
              <>
                <Music2 className="w-4 h-4 mr-2" />
                Resync likes from Spotify
              </>
            )}
          </Button>

          <Button
            onClick={loadLikes}
            variant="outline"
            className="border-white/30 text-white hover:bg-white/10"
          >
            Refresh view
          </Button>

          <Button
            onClick={loadRecommendations}
            variant="outline"
            disabled={recoLoading}
            className="border-purple-300 text-purple-100 hover:bg-purple-500/20"
          >
            {recoLoading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Getting recs…
              </>
            ) : (
              <>Get personalized recommendations</>
            )}
          </Button>
        </div>

        {error && <p className="text-sm text-red-300 mb-1">{error}</p>}
        {recoError && <p className="text-sm text-red-300 mb-3">{recoError}</p>}

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-white" />
          </div>
        ) : (
          <div className="space-y-6">
            {tracks.length === 0 ? (
              <p className="text-sm text-blue-100">
                We couldn’t find any liked tracks yet. Try resyncing from
                Spotify.
              </p>
            ) : (
              <>
                {/* Spotlight: first two liked songs with vector features */}
                <div>
                  <h2 className="text-sm font-semibold text-white mb-2">
                    Spotlight: feature vectors for first{' '}
                    {Math.min(2, tracks.length)} liked songs
                  </h2>
                  <div className="grid gap-4 md:grid-cols-2">
                    {tracks.slice(0, 2).map((track) => {
                      const feat = featuresById[track.id];
                      return (
                        <div
                          key={track.id}
                          className="flex flex-col gap-3 rounded-2xl bg-white/5 border border-white/10 p-3"
                        >
                          <div className="flex gap-3">
                            {track.album_art_url ? (
                              <img
                                src={track.album_art_url}
                                alt={track.title ?? 'Album art'}
                                className="w-16 h-16 rounded-xl object-cover flex-shrink-0"
                              />
                            ) : (
                              <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-emerald-500 to-blue-500 flex items-center justify-center flex-shrink-0">
                                <Music2 className="w-7 h-7 text-neutral-900" />
                              </div>
                            )}

                            <div className="flex-1">
                              <p className="font-semibold text-white line-clamp-1">
                                {track.title ?? 'Unknown title'}
                              </p>
                              <p className="text-xs text-blue-200 mb-2 line-clamp-1">
                                {track.artist ?? 'Unknown artist'}
                              </p>

                              {feat ? (
                                <p className="text-[10px] text-blue-200">
                                  Genres:{' '}
                                  {feat.genres && feat.genres.length
                                    ? feat.genres.join(', ')
                                    : '–'}
                                </p>
                              ) : null}
                            </div>
                          </div>

                          {feat ? (
                            <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-[11px] text-blue-100">
                              {/* Raw-ish high-level */}
                              <div>
                                <dt className="uppercase tracking-wide text-[10px] text-blue-300">
                                  Popularity (raw / scaled)
                                </dt>
                                <dd>
                                  {feat.popularity_raw ?? '–'} /{' '}
                                  {fmt(feat.popularity_scaled)}
                                </dd>
                              </div>
                              <div>
                                <dt className="uppercase tracking-wide text-[10px] text-blue-300">
                                  Explicit / is_explicit
                                </dt>
                                <dd>
                                  {feat.explicit ? 'Yes' : 'No'} /{' '}
                                  {fmt(feat.is_explicit)}
                                </dd>
                              </div>
                              <div>
                                <dt className="uppercase tracking-wide text-[10px] text-blue-300">
                                  Release year (raw / scaled)
                                </dt>
                                <dd>
                                  {feat.release_year ?? '–'} /{' '}
                                  {fmt(feat.release_year_scaled)}
                                </dd>
                              </div>
                              <div>
                                <dt className="uppercase tracking-wide text-[10px] text-blue-300">
                                  Duration (mm:ss / scaled)
                                </dt>
                                <dd>
                                  {formatDuration(feat.duration_ms)} /{' '}
                                  {fmt(feat.duration_scaled)}
                                </dd>
                              </div>

                              {/* Artist-level */}
                              <div>
                                <dt className="uppercase tracking-wide text-[10px] text-blue-300">
                                  Artist popularity (raw / scaled)
                                </dt>
                                <dd>
                                  {feat.artist_popularity_raw ?? '–'} /{' '}
                                  {fmt(feat.artist_popularity_scaled)}
                                </dd>
                              </div>
                              <div>
                                <dt className="uppercase tracking-wide text-[10px] text-blue-300">
                                  Followers (raw / scaled)
                                </dt>
                                <dd>
                                  {feat.artist_followers_raw
                                    ? feat.artist_followers_raw.toLocaleString()
                                    : '–'}{' '}
                                  / {fmt(feat.artist_followers_scaled)}
                                </dd>
                              </div>

                              {/* Genre + label scores */}
                              <div>
                                <dt className="uppercase tracking-wide text-[10px] text-blue-300">
                                  Genre position
                                </dt>
                                <dd>{fmt(feat.genre_position)}</dd>
                              </div>
                              <div>
                                <dt className="uppercase tracking-wide text-[10px] text-blue-300">
                                  Label score
                                </dt>
                                <dd>
                                  {fmt(feat.label_score)}{' '}
                                  <span className="text-[9px] text-blue-300">
                                    (0=indie, 1=major)
                                  </span>
                                </dd>
                              </div>
                            </div>
                          ) : (
                            <p className="text-[11px] text-blue-200 italic">
                              No metadata available for this track.
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Liked songs list */}
                <div>
                  <h2 className="text-sm font-semibold text-white mb-2">
                    Liked songs (first {Math.min(20, tracks.length)})
                  </h2>
                  <div className="max-h-64 overflow-y-auto pr-1 space-y-2">
                    {tracks.slice(0, 20).map((track) => (
                      <div
                        key={track.id}
                        className="flex items-center gap-3 rounded-xl bg-white/5 border border-white/5 px-3 py-2"
                      >
                        {track.album_art_url ? (
                          <img
                            src={track.album_art_url}
                            alt={track.title ?? 'Album art'}
                            className="w-10 h-10 rounded-lg object-cover flex-shrink-0"
                          />
                        ) : (
                          <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center flex-shrink-0">
                            <Music2 className="w-5 h-5 text-blue-100" />
                          </div>
                        )}

                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-white truncate">
                            {track.title ?? 'Unknown title'}
                          </p>
                          <p className="text-[11px] text-blue-200 truncate">
                            {track.artist ?? 'Unknown artist'}
                          </p>
                        </div>

                        {track.added_at && (
                          <p className="text-[10px] text-blue-300 whitespace-nowrap">
                            {new Date(track.added_at).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* New: Recommendations based on your vibe */}
                <div>
                  <h2 className="text-sm font-semibold text-white mb-2 mt-4">
                    Swave picks for you (top {recommended.length || 0})
                  </h2>

                  {recoLoading && (
                    <div className="flex items-center gap-2 text-blue-100 text-sm mb-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Scoring your next tracks…</span>
                    </div>
                  )}

                  {recommended.length === 0 && !recoLoading ? (
                    <p className="text-xs text-blue-200">
                      Hit “Get personalized recommendations” to see your next
                      songs.
                    </p>
                  ) : (
                    <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                      {recommended.map((track) => (
                        <div
                          key={track.id}
                          className="flex items-center gap-3 rounded-xl bg-emerald-500/5 border border-emerald-300/40 px-3 py-2"
                        >
                          {track.album_art_url ? (
                            <img
                              src={track.album_art_url}
                              alt={track.title ?? 'Album art'}
                              className="w-10 h-10 rounded-lg object-cover flex-shrink-0"
                            />
                          ) : (
                            <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                              <Music2 className="w-5 h-5 text-emerald-200" />
                            </div>
                          )}

                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-white truncate">
                              {track.title ?? 'Unknown title'}
                            </p>
                            <p className="text-[11px] text-emerald-200 truncate">
                              {track.artist ?? 'Unknown artist'}
                            </p>
                          </div>

                          <div className="flex flex-col items-end gap-1">
                            <span className="text-[10px] text-emerald-300 font-semibold">
                              match {(track.similarity * 100).toFixed(1)}%
                            </span>

                            {track.preview_url && (
                              <audio
                                controls
                                className="w-24"
                                preload="none"
                              >
                                <source src={track.preview_url} />
                              </audio>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
