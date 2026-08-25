import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { api } from '@/api/client';
import type { User, LoginRequest, RegisterRequest } from '@/api/types';
import { auth } from '@/lib/firebase';
import { 
  createUserWithEmailAndPassword, 
  signInWithEmailAndPassword, 
  signOut,
  User as FirebaseUser,
  getIdToken
} from 'firebase/auth';

interface AuthState {
  user: User | null;
  firebaseUser: FirebaseUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  isDemoMode: boolean;
  
  // Actions
  login: (credentials: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  loadProfile: () => Promise<void>;
  enterDemoMode: () => void;
  clearError: () => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      firebaseUser: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      isDemoMode: false,

      login: async (credentials: LoginRequest) => {
        set({ isLoading: true, error: null });
        try {
          const userCredential = await signInWithEmailAndPassword(
            auth, 
            credentials.email, 
            credentials.password
          );
          const idToken = await getIdToken(userCredential.user, true);
          const response = await api.auth.verifyFirebaseToken(idToken);
          set({ 
            user: response.user,
            firebaseUser: userCredential.user,
            isAuthenticated: true, 
            isLoading: false 
          });
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Login failed';
          set({ 
            error: errorMessage,
            isLoading: false 
          });
          throw error;
        }
      },

      register: async (data: RegisterRequest) => {
        set({ isLoading: true, error: null });
        try {
          const userCredential = await createUserWithEmailAndPassword(
            auth, 
            data.email, 
            data.password
          );
          const idToken = await getIdToken(userCredential.user, true);
          const response = await api.auth.verifyFirebaseToken(idToken);
          set({ 
            user: response.user,
            firebaseUser: userCredential.user,
            isAuthenticated: true, 
            isLoading: false 
          });
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Registration failed';
          set({ 
            error: errorMessage,
            isLoading: false 
          });
          throw error;
        }
      },

      logout: async () => {
        set({ isLoading: true });
        try {
          if (get().firebaseUser) {
            await signOut(auth);
          }
          if (!get().isDemoMode) {
            try {
              await api.auth.logout();
            } catch (error) {
              // Ignore API errors on logout
            }
          }
        } catch (error) {
          // Ignore errors, still clear state
        } finally {
          set({ 
            user: null,
            firebaseUser: null,
            isAuthenticated: false, 
            isDemoMode: false,
            isLoading: false 
          });
        }
      },

      loadProfile: async () => {
        set({ isLoading: true });
        try {
          const user = await api.auth.getProfile();
          set({ 
            user, 
            isAuthenticated: true, 
            isLoading: false 
          });
        } catch (error) {
          set({ 
            user: null, 
            isAuthenticated: false, 
            isLoading: false 
          });
        }
      },

      enterDemoMode: () => {
        const demoUser: User = {
          id: 999,
          username: 'demo_user',
          email: 'demo@swave.com',
          display_name: 'Demo User',
          date_joined: new Date().toISOString(),
          profile: {
            favorite_genres: ['pop', 'rock', 'electronic'],
            favorite_artists: ['Demo Artist 1', 'Demo Artist 2'],
            auto_play_previews: true,
            swipe_sensitivity: 0.5,
            total_swipes: 0,
            total_likes: 0,
            total_rejects: 0,
          }
        };
        
        set({ 
          user: demoUser, 
          isAuthenticated: true, 
          isDemoMode: true,
          isLoading: false,
          error: null 
        });
      },

      clearError: () => set({ error: null }),
      setLoading: (loading: boolean) => set({ isLoading: loading }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ 
        user: state.user, 
        isAuthenticated: state.isAuthenticated,
        isDemoMode: state.isDemoMode
      }),
    }
  )
);
