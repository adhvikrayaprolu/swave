import { create } from 'zustand';

interface UIState {
  toastMessage: string | null;
  isLoading: boolean;
  networkError: boolean;
  toast: (message: string) => void;
  setLoading: (loading: boolean) => void;
  setNetworkError: (error: boolean) => void;
  clearToast: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  toastMessage: null,
  isLoading: false,
  networkError: false,
  
  toast: (message) => {
    set({ toastMessage: message });
    setTimeout(() => set({ toastMessage: null }), 3000);
  },
  
  setLoading: (loading) => set({ isLoading: loading }),
  
  setNetworkError: (error) => set({ networkError: error }),
  
  clearToast: () => set({ toastMessage: null }),
}));
