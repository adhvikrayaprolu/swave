import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useAuthStore } from "@/store/auth";
import { auth } from "@/lib/firebase";
import { onAuthStateChanged } from "firebase/auth";

import { AuthScreen } from "./screens/AuthScreen";
import { ConnectSpotify } from "./screens/ConnectSpotify";
import { Feed } from "./screens/Feed";

import { Navigate, useLocation } from "react-router-dom";
import { Loader2 } from "lucide-react";

const RequireAuth = ({ children }: { children: JSX.Element }) => {
  const { isAuthenticated, isLoading, isDemoMode } = useAuthStore();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-10 h-10 animate-spin" />
      </div>
    );
  }

  if (isDemoMode) return children;

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace state={{ from: location }} />;
  }

  return children;
};


const queryClient = new QueryClient();

const AppShell = () => {
  const { isAuthenticated, loadProfile } = useAuthStore();

  // Listen to Firebase auth state changes
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (firebaseUser) {
        try {
          await loadProfile();
        } catch (error) {
          console.error('Failed to load profile:', error);
        }
      } else {
        useAuthStore.setState({
          firebaseUser: null,
          user: null,
          isAuthenticated: false,
          isDemoMode: false,
        });
      }
    });

    return () => unsubscribe();
  }, [loadProfile]);

  return (
    <Routes>
      {/* Always reachable */}
      <Route path="/connect-spotify" element={<ConnectSpotify />} />
      <Route path="/auth" element={<AuthScreen />} />

      {/* Protected feed */}
      <Route
        path="/"
        element={
          <RequireAuth>
            <Feed />
          </RequireAuth>
        }
      />

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );

};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
