import { useState, useEffect } from 'react';
import { useAuthStore } from '@/store/auth';
import { Button } from '@/components/ui/button';
import { Loader2, Play, Music2 } from 'lucide-react';

type AuthMode = 'login' | 'register';

const API_BASE =
  (import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8000';



export const AuthScreen = () => {
  const [mode, setMode] = useState<AuthMode>('login');
  const { loadProfile, isLoading, enterDemoMode } = useAuthStore();

  // spotify button state
  const [spotifyBusy, setSpotifyBusy] = useState(false);
  const [spotifyError, setSpotifyError] = useState<string | null>(null);



  // Try to load profile on mount (if tokens exist)
  useEffect(() => {
    loadProfile().catch((error) => {
      console.warn('Failed to load profile on mount:', error);
    });
  }, [loadProfile]);

  const switchMode = (newMode: AuthMode) => {
    setMode(newMode);
  };

  // Redirect to backend to kick off OAuth.
  // Preferred: GET /api/spotify/authorize/ returns { url } to redirect to.
  // Fallbacks: direct redirect to one of the common endpoints that does a 302.
  const connectSpotify = () => {
    setSpotifyBusy(true);
    setSpotifyError(null);
    // this matches your Django urlpattern: path("auth/spotify/login", spotify_login, ...)
    window.location.assign(`${API_BASE}/auth/spotify/login`);
};

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo/Brand */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Swave</h1>
          <p className="text-blue-200">Discover your next favorite song</p>
        </div>

        {/* Auth Forms */}
        {isLoading ? (
          <div className="flex justify-center items-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-white" />
          </div>
        ) : (
          <>

            {/* Divider */}
            <div className="mt-6">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t border-blue-300/30" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 px-2 text-blue-200">
                    Or
                  </span>
                </div>
              </div>

              {/* Connect Spotify */}
              <Button
                onClick={connectSpotify}
                disabled={spotifyBusy}
                className="w-full mt-4 bg-emerald-500 hover:bg-emerald-400 text-neutral-900"
              >
                {spotifyBusy ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Music2 className="w-4 h-4 mr-2" />
                )}
                {spotifyBusy ? 'Opening Spotify…' : 'Login with Spotify'}
              </Button>
              {spotifyError && (
                <p className="text-xs text-red-300 mt-2 text-center">{spotifyError}</p>
              )}

              {/* Demo Mode Button */}
              <Button
                onClick={enterDemoMode}
                variant="outline"
                className="w-full mt-3 bg-white/10 border-white/20 text-white hover:bg-white/20 hover:text-white"
              >
                <Play className="w-4 h-4 mr-2" />
                Try Demo Mode
              </Button>

              <p className="text-xs text-blue-200/70 text-center mt-2">
                Skip login and explore the app
              </p>
            </div>
          </>
        )}

        {/* Footer */}
        <div className="text-center mt-8">
          <p className="text-sm text-blue-200">
            By continuing, you agree to our Terms of Service and Privacy Policy
          </p>
        </div>
      </div>
    </div>
  );
};
